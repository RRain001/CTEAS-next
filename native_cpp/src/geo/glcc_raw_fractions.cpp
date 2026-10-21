#include "cteas/geo/glcc_raw_fractions.hpp"
#include "cteas/geo/glcc_direct_laea_probe.hpp"
#include <ogr_spatialref.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
namespace cteas::reconstruction::geo {
namespace {
constexpr int kNx=13000,kNy=12000;
constexpr std::uintmax_t kBytes=156000000;
constexpr double kRadius=6370997.,kLat0=45.,kLon0=100.,kPi=3.14159265358979323846;
constexpr std::array<int,24> kRawToUsgs{{16,21,21,21,21,21,31,32,33,33,41,41,
                                         42,42,43,52,62,61,77,82,81,85,83,91}};
void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
using Transform=std::unique_ptr<OGRCoordinateTransformation,decltype(&OCTDestroyCoordinateTransformation)>;
Transform transform(OGRSpatialReference& source,OGRSpatialReference& dest) {
  source.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  dest.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  Transform out(OGRCreateCoordinateTransformation(&source,&dest),OCTDestroyCoordinateTransformation);
  require(bool(out),"P2_GLCC_TRANSFORM_UNAVAILABLE");return out;
}
void validate_grid(P2Grid g,int epsg,int mesh) {
  require((epsg>=32601&&epsg<=32660)||(epsg>=32701&&epsg<=32760),"P2_GLCC_WGS84_UTM_ONLY");
  require(mesh>=1&&mesh<=50,"P2_GLCC_INVALID_MESH");
  require(std::isfinite(g.x0_m)&&std::isfinite(g.y0_m)&&std::isfinite(g.dx_m)&&
          g.dx_m>0&&g.nx>0&&g.ny>0,"P2_GLCC_INVALID_GRID");
  require(g.nx<=std::numeric_limits<std::size_t>::max()/g.ny&&
          g.nx*g.ny<=250000,"P2_GLCC_GRID_BUDGET");
  require(std::isfinite(g.x0_m+g.nx*g.dx_m)&&std::isfinite(g.y0_m+g.ny*g.dx_m),
          "P2_GLCC_GRID_OVERFLOW");
  // Larger footprints cannot inherit the nine-point-window assumption
  // unexamined. window_from_grid performs a dense independent 5-km
  // projection coverage audit BEFORE any source pixels are processed.
  // Existing 250000-cell and source-pixel/mesh budgets remain unchanged.
}
std::pair<double,double> laea_forward(double lon,double lat) {
  const double lam=lon*kPi/180.,phi=lat*kPi/180.;
  const double p0=kLat0*kPi/180.,l0=kLon0*kPi/180.;
  const double g=std::sin(p0)*std::sin(phi)+std::cos(p0)*std::cos(phi)*std::cos(lam-l0);
  require(g>-1.+1e-12,"P2_GLCC_LAEA_ANTIPODE");
  const double k=std::sqrt(2./(1.+g));
  return {kRadius*k*std::cos(phi)*std::sin(lam-l0)/1000.,
          kRadius*k*(std::cos(p0)*std::sin(phi)-std::sin(p0)*std::cos(phi)*std::cos(lam-l0))/1000.};
}
std::pair<double,double> laea_inverse(double x_km,double y_km) {
  const double x=x_km*1000.,y=y_km*1000.,rho=std::hypot(x,y);
  if(rho==0)return {kLon0,kLat0};
  require(rho<=2.*kRadius,"P2_GLCC_LAEA_OUT_OF_DOMAIN");
  const double z=2.*std::asin(std::min(1.,rho/(2.*kRadius)));
  const double sinz=std::sin(z),cosz=std::cos(z);
  const double p0=kLat0*kPi/180.;
  const double lat=std::asin(cosz*std::sin(p0)+y*sinz*std::cos(p0)/rho);
  const double con=cosz-std::sin(p0)*std::sin(lat);
  const double lon=kLon0*kPi/180.+std::atan2(x*sinz*std::cos(p0),con*rho);
  return {lon*180./kPi,lat*180./kPi};
}
GlccWindow window_from_grid(P2Grid grid,OGRCoordinateTransformation* to_geographic) {
  const double x0=grid.x0_m,y0=grid.y0_m;
  const double x1=x0+grid.nx*grid.dx_m,y1=y0+grid.ny*grid.dx_m;
  const std::array<double,3> xs{{x0,(x0+x1)/2.,x1}},ys{{y0,(y0+y1)/2.,y1}};
  double minx=std::numeric_limits<double>::infinity(),maxx=-minx;
  double miny=minx,maxy=-minx;
  double lo_min=360.,lo_max=-360.;
  for(double xx:xs)for(double yy:ys) {
    double lon=xx,lat=yy;
    require(to_geographic->Transform(1,&lon,&lat)!=0,"P2_GLCC_UTM_TO_GEO_FAILED");
    require(std::isfinite(lon)&&std::isfinite(lat),"P2_GLCC_INVALID_GEO");
    lo_min=std::min(lo_min,lon);lo_max=std::max(lo_max,lon);
    auto [x,y]=laea_forward(lon,lat);
    minx=std::min(minx,x);maxx=std::max(maxx,x);
    miny=std::min(miny,y);maxy=std::max(maxy,y);
  }
  require(lo_max-lo_min<180.,"P2_GLCC_ANTIMERIDIAN_UNSUPPORTED");
  // Same 3x3 UTM-to-LAEA plus 1.5km margin as Python source-only reference.
  // On footprints above the formerly certified 50km side length, audit
  // independently projected samples spanning the WHOLE rectangle at <=5km
  // spacing against the unchanged nine-point window. Reject if an
  // extreme is not contained. This is source-custody validation ONLY:
  // it never changes grid sampling, original 20x20 pixel subpoints,
  // original GLCC 24->38 categories or the selected physical algorithm.
  constexpr double buffer=1.5;
  if(grid.nx*grid.dx_m>50000.||grid.ny*grid.dx_m>50000.) {
    const auto nxi=static_cast<std::size_t>(std::ceil(grid.nx*grid.dx_m/5000.));
    const auto nyi=static_cast<std::size_t>(std::ceil(grid.ny*grid.dx_m/5000.));
    require(nxi>0&&nyi>0&&nxi<=512&&nyi<=512,
            "P2_GLCC_LARGE_DOMAIN_PROJECTION_AUDIT_BUDGET");
    for(std::size_t ii=0;ii<=nxi;++ii)for(std::size_t jj=0;jj<=nyi;++jj) {
      double lon=x0+(x1-x0)*double(ii)/double(nxi);
      double lat=y0+(y1-y0)*double(jj)/double(nyi);
      require(to_geographic->Transform(1,&lon,&lat)!=0,
              "P2_GLCC_LARGE_DOMAIN_AUDIT_PROJECTION_FAILED");
      const auto [projected_x,projected_y]=laea_forward(lon,lat);
      require(std::isfinite(projected_x)&&std::isfinite(projected_y)&&
              projected_x>=minx-buffer&&projected_x<=maxx+buffer&&
              projected_y>=miny-buffer&&projected_y<=maxy+buffer,
              "P2_GLCC_LARGE_DOMAIN_SOURCE_WINDOW_UNCOVERED");
    }
  }
  const int i0=static_cast<int>(std::floor((minx-buffer+8000.)))+1;
  const int i1=static_cast<int>(std::ceil ((maxx+buffer+8000.)));
  const int j0=static_cast<int>(std::floor((miny-buffer+5499.)))+1;
  const int j1=static_cast<int>(std::ceil ((maxy+buffer+5499.)));
  require(i0>=1&&i1<=kNx&&j0>=1&&j1<=kNy&&i0<=i1&&j0<=j1,
          "P2_GLCC_OUTSIDE_EURASIA_SOURCE");
  const std::uint64_t count=static_cast<std::uint64_t>(i1-i0+1)*(j1-j0+1);
  require(count<=3000000,"P2_GLCC_SOURCE_WINDOW_BUDGET");
  return {i0,i1,j0,j1};
}
} // namespace

double GlccRawResult::fraction(std::size_t i,std::size_t j,std::size_t k) const {
  if(i>=grid.nx||j>=grid.ny||k>=kGlccUsgs92Classes.size())
    throw std::out_of_range("P2_GLCC_BAD_INDEX");
  const auto cell=j*grid.nx+i;
  if(!cell_samples.at(cell))throw std::domain_error("P2_GLCC_EMPTY_CELL");
  return double(counts.at(cell*kGlccUsgs92Classes.size()+k))/double(cell_samples.at(cell));
}
namespace {
GlccRawResult compute_glcc_raw_selected(const std::string& path,P2Grid grid,int epsg,int mesh,
                                        bool diagnostic_mesh,bool direct_laea) {
  // All WGS84 UTM zones are permitted by the existing bounded source
  // window and grid validator. Exact original science is evidenced only
  // for the pinned Hefei UTM50N configuration, never inferred here.
  validate_grid(grid,epsg,mesh);
  const std::filesystem::path source(path);
  require(!std::filesystem::is_symlink(std::filesystem::symlink_status(source))&&
          std::filesystem::is_regular_file(source),"P2_GLCC_SOURCE_MISSING_OR_SYMLINK");
  require(std::filesystem::file_size(source)==kBytes,"P2_GLCC_NOT_156MB_RAW_IMG_OR_LFS_POINTER");
  std::ifstream in(source,std::ios::binary);
  require(bool(in),"P2_GLCC_OPEN_FAILED");
  OGRSpatialReference utm,sphere,geographic;
  require(utm.importFromEPSG(epsg)==OGRERR_NONE&&
          sphere.importFromProj4("+proj=longlat +a=6370997 +b=6370997 +no_defs +type=crs")==OGRERR_NONE&&
          geographic.importFromEPSG(4326)==OGRERR_NONE,"P2_GLCC_CRS_INIT_FAILED");
  auto to_geo=transform(utm,geographic);
  auto to_utm=transform(sphere,utm);
  const GlccWindow win=window_from_grid(grid,to_geo.get());
  const std::uint64_t pixels=std::uint64_t(win.i1-win.i0+1)*(win.j1-win.j0+1);
  // The pre-existing 3M-point historical budget is unchanged for already
  // accepted <=50km domains. A *larger* true regional source is separately
  // admitted only after the dense full-domain projected window containment
  // audit above, with a still bounded 5M original subpoint traversal budget.
  // This is a resource preflight only, not an altered MESHGLAZ or cell bin.
  const bool independently_audited_regional_grid =
      grid.nx*grid.dx_m>50000.||grid.ny*grid.dx_m>50000.;
  constexpr std::uint64_t kExistingMeshBudget=3000000ULL;
  constexpr std::uint64_t kAuditedRegionalMeshBudget=5000000ULL;
  const auto mesh_budget=independently_audited_regional_grid
      ?kAuditedRegionalMeshBudget:kExistingMeshBudget;
  require(pixels<=mesh_budget/std::uint64_t(mesh*mesh),"P2_GLCC_MESH_POINT_BUDGET");
  const std::size_t ncell=grid.nx*grid.ny;
  GlccRawResult out{grid,epsg,mesh,win,
     std::vector<std::uint32_t>(ncell*kGlccUsgs92Classes.size(),0),
     std::vector<std::uint32_t>(ncell,0),{},0,0,{}};
  std::vector<unsigned char> row(std::size_t(win.i1-win.i0+1));
  const float x0=static_cast<float>(grid.x0_m/1000.);
  const float y0=static_cast<float>(grid.y0_m/1000.);
  const float step=static_cast<float>(grid.dx_m/1000.);
  const double xm=static_cast<double>(0.001f);
  std::unique_ptr<DirectLaeaProbe> direct;
  if(direct_laea) direct=std::make_unique<DirectLaeaProbe>(epsg);
  for(int j=win.j1;j>=win.j0;--j) {
    const std::uint64_t offset=std::uint64_t(kNy-j)*kNx+(win.i0-1);
    in.seekg(static_cast<std::streamoff>(offset),std::ios::beg);
    require(bool(in),"P2_GLCC_IMG_SEEK_FAILURE");
    in.read(reinterpret_cast<char*>(row.data()),static_cast<std::streamsize>(row.size()));
    require(in.gcount()==static_cast<std::streamsize>(row.size()),"P2_GLCC_IMG_SHORT_READ");
    for(int i=win.i0;i<=win.i1;++i) {
      const unsigned raw=row[std::size_t(i-win.i0)];
      require(raw<=24,"P2_GLCC_INVALID_RAW_CATEGORY");
      ++out.raw_pixels[raw];
      if(raw==0)continue; // raw 0 is missing, not water; raw16 maps to USGS52.
      const int mapped=kRawToUsgs[raw-1];
      const auto cat=std::find(kGlccUsgs92Classes.begin(),kGlccUsgs92Classes.end(),mapped);
      require(cat!=kGlccUsgs92Classes.end(),"P2_GLCC_INTERNAL_CLASS_MAP");
      const std::size_t category=std::size_t(cat-kGlccUsgs92Classes.begin());
      const double xc=-8000.+double(i-1),yc=-5499.+double(j-1);
      for(int im=0;im<mesh;++im)for(int jm=0;jm<mesh;++jm) {
        float x_km=0.f,y_km=0.f;
        int ix=0,jy=0;
        if(direct_laea) {
          // Independently verified against untouched original GLAZAS:
          // 95,000 integer HITS exact on Hefei case (Run #39187178797).
          // The source-pixel and MESHGLAZ subpoint arithmetic is REAL*4;
          // inverse LAEA / UTM is GDAL, then COORDLIB XMULTO is REAL*4
          // promoted to REAL*8, GLOBE result REAL*4, LUGRID bins REAL*4.
          const auto q=direct->project(i,j,im+1,jm+1,mesh,x0,y0,step);
          x_km=q.x_km;y_km=q.y_km;
          ix=q.i;jy=q.j;
        } else {
          auto [lon,lat]=laea_inverse(xc-.5+(im+.5)/mesh,yc-.5+(jm+.5)/mesh);
          // Historical GEN: seven decimal digits then REAL*4.
          char buf[96]{};
          std::snprintf(buf,sizeof(buf),"%.7f",lon);lon=double(static_cast<float>(std::stod(buf)));
          std::snprintf(buf,sizeof(buf),"%.7f",lat);lat=double(static_cast<float>(std::stod(buf)));
          require(to_utm->Transform(1,&lon,&lat)!=0,"P2_GLCC_GEO_TO_UTM_FAILED");
          x_km=static_cast<float>(lon*xm);
          y_km=static_cast<float>(lat*xm);
          const float dx=x_km-x0;
          const float dy=y_km-y0;
          const double rx=double(dx)/step,ry=double(dy)/step;
          require(std::isfinite(rx)&&std::isfinite(ry)&&std::abs(rx)<1e8&&std::abs(ry)<1e8,
                  "P2_GLCC_INDEX_OVERFLOW");
          ix=static_cast<int>(dx/step)+(dx>=0?1:0);
          jy=static_cast<int>(dy/step)+(dy>=0?1:0);
        }
        if(diagnostic_mesh) {
          require(out.diagnostic_mesh.size()<3000000,"P2_GLCC_DIAGNOSTIC_BUDGET");
          // GLOBE's corresponding xgrid/ygrid arguments are Fortran REAL*4 km.
          // No altered coordinate path: record the existing production calculation.
          out.diagnostic_mesh.push_back({i,j,im+1,jm+1,mapped,
             x_km,y_km,ix,jy});
        }
        if(ix<1||jy<1||std::size_t(ix)>grid.nx||std::size_t(jy)>grid.ny){++out.outside;continue;}
        const auto cell=(std::size_t(jy)-1)*grid.nx+(std::size_t(ix)-1);
        require(out.cell_samples[cell]<std::numeric_limits<std::uint32_t>::max(),"P2_GLCC_COUNT_OVERFLOW");
        ++out.cell_samples[cell];
        ++out.counts[cell*kGlccUsgs92Classes.size()+category];
        ++out.included;
      }
    }
  }
  require(out.included>0,"P2_GLCC_NO_INCLUDED_SAMPLES");
  return out;
}
} // anonymous namespace

GlccRawResult compute_glcc_gen_replay(
    const std::string& path,P2Grid grid,int epsg,int mesh,bool diagnostic_mesh) {
  return compute_glcc_raw_selected(path,grid,epsg,mesh,diagnostic_mesh,false);
}

GlccRawResult compute_glcc_direct_laea(
    const std::string& path,P2Grid grid,int epsg,int mesh,bool diagnostic_mesh) {
  return compute_glcc_raw_selected(path,grid,epsg,mesh,diagnostic_mesh,true);
}
} // namespace cteas::reconstruction::geo
