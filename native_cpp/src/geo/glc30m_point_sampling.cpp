#include "cteas/geo/glc30m_point_sampling.hpp"
#include <ogr_spatialref.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::reconstruction::geo {
namespace {
void need(bool ok,const char* error){if(!ok)throw std::runtime_error(error);}
std::size_t usgs_column(int id) {
  const auto pos=std::find(kGlccUsgs92Classes.begin(),kGlccUsgs92Classes.end(),id);
  need(pos!=kGlccUsgs92Classes.end(),"P2C_30M_USGS_NOT_IN_38_CLASSES");
  return std::size_t(pos-kGlccUsgs92Classes.begin());
}
} // namespace
OriginalSamplingRecount sample_glc30m_original_mesh(
    GDALDataset& ds, const P2Grid& g, int epsg,
    const std::map<int,int>& fixed, int mesh,
    const IsGshhgFullLandPoint& is_land, bool inland,
    Glc30mSamplingStats& st) {
  need(mesh==10,"P2C_30M_MESHGLAZ10_REQUIRED");
  need(fixed.size()==34 && fixed.count(210)==0 &&
       fixed.at(183)==77 && fixed.at(184)==77 &&
       fixed.at(52)==42 && fixed.at(220)==91,
       "P2C_30M_FROZEN_USER_MAPPING_NOT_APPROVED");
  for(const auto& [raw,mapped]:fixed){
    need(raw>0&&raw!=210&&mapped>=1&&mapped<=92,
         "P2C_30M_MAP_CLASS_RANGE");
    (void)usgs_column(mapped);
  }
  need(!inland || !is_land,"P2C_30M_INLAND_MUST_NOT_LOAD_COAST_GEOMETRY");
  need(inland || bool(is_land),"P2C_30M_COAST_REQUIRES_GSHHG_FULL_L1");
  need(epsg==32650||epsg==32652,"P2C_30M_SITE_UTM_EPSG_ONLY");
  need(ds.GetRasterCount()==1 && ds.GetRasterXSize()>0 && ds.GetRasterYSize()>0,
       "P2C_30M_SINGLE_BAND_SOURCE");
  need(ds.GetRasterXSize()<=2048 && ds.GetRasterYSize()<=2048,
       "P2C_30M_SOURCE_PIXEL_BUDGET");
  OGRSpatialReference crs, expected;
  need(ds.GetSpatialRef()!=nullptr && expected.importFromEPSG(epsg)==OGRERR_NONE,
       "P2C_30M_CRS_MISSING");
  crs=*ds.GetSpatialRef();
  crs.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  expected.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  need(crs.IsSame(&expected),"P2C_30M_SOURCE_CRS_WRONG_FOR_CASE");
  double t[6]{};
  need(ds.GetGeoTransform(t)==CE_None && std::isfinite(t[0])&&
       std::isfinite(t[3])&&std::abs(t[1]-30.)<1e-8&&
       std::abs(t[5]+30.)<1e-8&&
       std::abs(t[2])<1e-12&&std::abs(t[4])<1e-12,
       "P2C_30M_NORTH_UP_30M_UTM_REQUIRED");
  need(g.nx>0&&g.ny>0&&g.nx<=250000/g.ny&&
       std::isfinite(g.x0_m)&&std::isfinite(g.y0_m)&&
       std::abs(g.dx_m-100.)<1e-9,
       "P2C_30M_ORIGINAL_100M_GRID_ONLY");
  need(g.nx*g.ny<=40000,"P2C_30M_20KM_BUDGET");
  // All model points must be representable by actual 30m source pixels.
  const auto xmax=t[0]+30.*ds.GetRasterXSize();
  const auto ymin=t[3]-30.*ds.GetRasterYSize();
  need(t[0]<=g.x0_m&&xmax>=g.x0_m+g.nx*g.dx_m&&
       ymin<=g.y0_m&&t[3]>=g.y0_m+g.ny*g.dx_m,
       "P2C_30M_TIFF_DOES_NOT_COVER_FULL_20KM");
  auto* band=ds.GetRasterBand(1);
  need(band!=nullptr && band->GetRasterDataType()==GDT_Byte,
       "P2C_30M_GLC_SOURCE_MUST_BE_CATEGORICAL_BYTE");
  const int width=ds.GetRasterXSize(),height=ds.GetRasterYSize();
  std::vector<std::uint8_t> pixels(std::size_t(width)*height);
  need(band->RasterIO(GF_Read,0,0,width,height,pixels.data(),width,height,
                      GDT_Byte,0,0,nullptr)==CE_None,"P2C_30M_RASTER_READ");
  std::vector<std::uint8_t> mask(std::size_t(width)*height,255);
  auto* mb=band->GetMaskBand();
  need(mb!=nullptr && mb->RasterIO(GF_Read,0,0,width,height,
                   mask.data(),width,height,GDT_Byte,0,0,nullptr)==CE_None,
       "P2C_30M_MASK_READ");
  constexpr double kMetersPerKm=static_cast<double>(0.001f);
  const float x0=static_cast<float>(g.x0_m/1000.);
  const float y0=static_cast<float>(g.y0_m/1000.);
  const float dx=static_cast<float>(g.dx_m/1000.);
  OriginalSamplingRecount out{
      g,std::vector<std::uint32_t>(g.nx*g.ny*38,0),
      std::vector<std::uint32_t>(g.nx*g.ny,0),
      std::vector<std::uint8_t>(g.nx*g.ny,0),55,0,0,0};
  st=Glc30mSamplingStats{};
  st.source_pixels=pixels.size();
  // Original GLAZAS structure: per SOURCE pixel, MESHGLAZ×MESHGLAZ
  // evenly spaced subpoints, REAL*4 projected coordinates in km, original
  // trunc-toward-zero + positive 1-based LUGRID binning.
  for(int row=0;row<height;++row)for(int col=0;col<width;++col) {
    const auto p=std::size_t(row)*width+col;
    const int raw=pixels[p];
    const bool invalid=(mask[p]==0||raw==0||raw==250);
    if(!invalid && raw!=210 && fixed.count(raw)==0)
      throw std::runtime_error("P2C_30M_UNRECOGNIZED_GLC_SOURCE_CLASS");
    if(invalid)++st.invalid_source_pixels;
    for(int im=0;im<mesh;++im)for(int jm=0;jm<mesh;++jm) {
      const double x=t[0]+(double(col)+(double(im)+.5)/mesh)*30.;
      const double y=t[3]-(double(row)+(double(jm)+.5)/mesh)*30.;
      const float fx=static_cast<float>(x*kMetersPerKm);
      const float fy=static_cast<float>(y*kMetersPerKm);
      const float vx=fx-x0,vy=fy-y0;
      need(std::isfinite(vx)&&std::isfinite(vy)&&
           std::abs(vx)<1e6f&&std::abs(vy)<1e6f,
           "P2C_30M_INVALID_PROJECTED_MESH");
      const int ix=static_cast<int>(vx/dx)+(vx>=0?1:0);
      const int jy=static_cast<int>(vy/dx)+(vy>=0?1:0);
      ++st.generated_subpoints;
      if(ix<1||jy<1||ix>int(g.nx)||jy>int(g.ny)) {
        ++st.outside_subpoints;continue;
      }
      if(invalid) {++st.invalid_subpoints;continue;}
      const int mapped=raw==210?(inland||is_land(x,y)?52:55):fixed.at(raw);
      const auto cell=std::size_t(jy-1)*g.nx+std::size_t(ix-1);
      ++out.counts[cell*38+usgs_column(mapped)];
      ++out.samples[cell];
      ++st.included_subpoints;
      if(raw==210) {
        if(mapped==52)++st.water52_hits;else ++st.water55_hits;
      }
    }
  }
  out.included=st.included_subpoints;
  out.outside=st.outside_subpoints;
  for(auto n:out.samples)st.missing_cells+=(n==0);
  need(st.generated_subpoints==std::uint64_t(width)*height*mesh*mesh &&
       st.included_subpoints+st.outside_subpoints+st.invalid_subpoints==
           st.generated_subpoints,
       "P2C_30M_SUBPOINT_CONSERVATION");
  need(st.water55_hits==0||!inland,"P2C_30M_INLAND_SEA_FORBIDDEN");
  return out;
}
} // namespace cteas::reconstruction::geo
