#include "cteas/geo/glc_area_fractions.hpp"
#include <gdal_priv.h>
#include <ogr_spatialref.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
namespace cteas::reconstruction::geo {
namespace {
constexpr std::array<int,35> kGLC{{10,11,12,20,51,52,61,62,71,72,81,82,
  91,92,120,121,122,130,140,150,152,153,181,182,183,184,185,186,187,
  190,200,201,202,210,220}};
int category_index(int code) {
  const auto it=std::lower_bound(kGLC.begin(),kGLC.end(),code);
  return it==kGLC.end()||*it!=code ? -1 : static_cast<int>(it-kGLC.begin());
}
void require(bool condition,const char* message) {
  if(!condition)throw std::runtime_error(message);
}
std::size_t checked_cells(P2Grid grid) {
  require(std::isfinite(grid.x0_m)&&std::isfinite(grid.y0_m)&&
          std::isfinite(grid.dx_m)&&grid.dx_m>0&&grid.nx>0&&grid.ny>0,
          "P2_GLC_INVALID_GRID");
  require(grid.nx<=std::numeric_limits<std::size_t>::max()/grid.ny,
          "P2_GLC_GRID_OVERFLOW");
  const std::size_t cells=grid.nx*grid.ny;
  require(cells<=std::numeric_limits<std::size_t>::max()/kGLC.size(),
          "P2_GLC_CLASSES_OVERFLOW");
  require(cells<=2'000'000,"P2_GLC_CELL_BUDGET_EXCEEDED");
  require(std::isfinite(grid.x0_m+grid.nx*grid.dx_m)&&
          std::isfinite(grid.y0_m+grid.ny*grid.dx_m),"P2_GLC_GRID_OVERFLOW");
  return cells;
}
using Dataset=std::unique_ptr<GDALDataset,decltype(&GDALClose)>;
} // namespace

double GLCAreaFractions::fraction(std::size_t i,std::size_t j,std::size_t k) const {
  if(i>=grid.nx||j>=grid.ny||k>=raw_codes.size())
    throw std::out_of_range("P2_GLC_FRACTION_INDEX");
  const auto cell=j*grid.nx+i;
  if(valid_m2.at(cell)<=0)throw std::domain_error("P2_GLC_MISSING_CELL");
  return area_m2.at(cell*raw_codes.size()+k)/valid_m2.at(cell);
}

GLCAreaFractions compute_glc_area_fractions(
    const std::string& path,P2Grid grid,int epsg) {
  const auto nc=checked_cells(grid);
  require((epsg>=32601&&epsg<=32660)||(epsg>=32701&&epsg<=32760),
          "P2_GLC_EXPECTED_CRS_MUST_BE_WGS84_UTM");
  GDALAllRegister();
  Dataset ds(static_cast<GDALDataset*>(GDALOpenEx(path.c_str(),GDAL_OF_RASTER|GDAL_OF_READONLY,
      nullptr,nullptr,nullptr)),GDALClose);
  require(bool(ds),"P2_GLC_CANNOT_OPEN_TIFF");
  require(ds->GetDriver()&&std::string(ds->GetDriver()->GetDescription())=="GTiff",
          "P2_GLC_SOURCE_NOT_GEOTIFF");
  require(ds->GetRasterCount()==1,"P2_GLC_EXPECTED_ONE_BAND");
  auto* band=ds->GetRasterBand(1);
  require(band&&band->GetRasterDataType()==GDT_Byte,"P2_GLC_EXPECTED_UINT8_CATEGORIES");
  const OGRSpatialReference* actual=ds->GetSpatialRef();
  OGRSpatialReference expected;
  require(actual&&expected.importFromEPSG(epsg)==OGRERR_NONE&&actual->IsSame(&expected),
          "P2_GLC_CRS_MISMATCH");
  double gt[6]{};
  require(ds->GetGeoTransform(gt)==CE_None&&std::isfinite(gt[0])&&std::isfinite(gt[3])&&
          std::isfinite(gt[1])&&std::isfinite(gt[5])&&gt[1]>0&&gt[5]<0&&
          gt[2]==0&&gt[4]==0,"P2_GLC_ROTATED_OR_INVALID_TRANSFORM");
  // The fixed source has 30m cells. An arbitrary different-resolution input
  // is not silently admitted as an already-approved GLC_FCS30D source.
  require(std::abs(gt[1]-30.)<1e-8&&std::abs(gt[5]+30.)<1e-8,
          "P2_GLC_EXPECTED_30M_PIXELS");
  const int width=ds->GetRasterXSize(),height=ds->GetRasterYSize();
  require(width>0&&height>0,"P2_GLC_EMPTY_RASTER");
  const double xmin=gt[0], xmax=gt[0]+width*gt[1];
  const double ymax=gt[3], ymin=gt[3]+height*gt[5];
  const double gx1=grid.x0_m+grid.nx*grid.dx_m;
  const double gy1=grid.y0_m+grid.ny*grid.dx_m;
  const double tol=1e-7;
  require(grid.x0_m>=xmin-tol&&gx1<=xmax+tol&&grid.y0_m>=ymin-tol&&gy1<=ymax+tol,
          "P2_GLC_SOURCE_DOES_NOT_COVER_GRID");
  int start_col=std::max(0,static_cast<int>(std::floor((grid.x0_m-xmin)/gt[1])));
  int end_col=std::min(width,static_cast<int>(std::ceil((gx1-xmin)/gt[1])));
  int start_row=std::max(0,static_cast<int>(std::floor((ymax-gy1)/(-gt[5]))));
  int end_row=std::min(height,static_cast<int>(std::ceil((ymax-grid.y0_m)/(-gt[5]))));
  require(start_col<end_col&&start_row<end_row,"P2_GLC_NO_SOURCE_INTERSECTION");
  const int span=end_col-start_col;
  std::vector<std::uint8_t> values(static_cast<std::size_t>(span));
  std::vector<std::uint8_t> masks(static_cast<std::size_t>(span));
  int has_nodata=0;
  const double nodata=band->GetNoDataValue(&has_nodata);
  if(has_nodata)require(std::isfinite(nodata),"P2_GLC_INVALID_NODATA");
  auto* mask=band->GetMaskBand();
  require(mask,"P2_GLC_MISSING_MASK");
  GLCAreaFractions out{grid,std::vector<int>(kGLC.begin(),kGLC.end()),
      std::vector<double>(nc*kGLC.size(),0.),std::vector<double>(nc,0.)};
  for(int r=start_row;r<end_row;++r) {
    require(band->RasterIO(GF_Read,start_col,r,span,1,values.data(),span,1,
                          GDT_Byte,0,0,nullptr)==CE_None,"P2_GLC_RASTER_READ_FAILED");
    require(mask->RasterIO(GF_Read,start_col,r,span,1,masks.data(),span,1,
                          GDT_Byte,0,0,nullptr)==CE_None,"P2_GLC_MASK_READ_FAILED");
    const double py1=ymax-r*(-gt[5]);
    const double py0=py1+gt[5];
    for(int c=start_col;c<end_col;++c) {
      const double px0=xmin+c*gt[1],px1=px0+gt[1];
      const double xlo=std::max(grid.x0_m,px0),xhi=std::min(gx1,px1);
      const double ylo=std::max(grid.y0_m,py0),yhi=std::min(gy1,py1);
      if(xhi<=xlo||yhi<=ylo)continue;
      const auto offset=static_cast<std::size_t>(c-start_col);
      const int code=values[offset];
      const int k=category_index(code);
      require(masks[offset]!=0&&code!=0&&code!=250&&
              !(has_nodata&&static_cast<double>(code)==nodata),
              "P2_GLC_NODATA_OR_MASKED_INTERSECTION");
      require(k>=0,"P2_GLC_ILLEGAL_RAW_CLASS");
      const std::size_t i0=static_cast<std::size_t>(std::max(0.,std::floor((xlo-grid.x0_m)/grid.dx_m)));
      const std::size_t i1=std::min(grid.nx,static_cast<std::size_t>(std::ceil((xhi-grid.x0_m)/grid.dx_m)));
      const std::size_t j0=static_cast<std::size_t>(std::max(0.,std::floor((ylo-grid.y0_m)/grid.dx_m)));
      const std::size_t j1=std::min(grid.ny,static_cast<std::size_t>(std::ceil((yhi-grid.y0_m)/grid.dx_m)));
      for(std::size_t j=j0;j<j1;++j)for(std::size_t i=i0;i<i1;++i) {
        const double a=std::max(0.,std::min(xhi,grid.x0_m+(i+1)*grid.dx_m)-
                    std::max(xlo,grid.x0_m+i*grid.dx_m))*
                       std::max(0.,std::min(yhi,grid.y0_m+(j+1)*grid.dx_m)-
                    std::max(ylo,grid.y0_m+j*grid.dx_m));
        if(a==0)continue;
        const std::size_t cell=j*grid.nx+i;
        out.area_m2[cell*kGLC.size()+static_cast<std::size_t>(k)]+=a;
        out.valid_m2[cell]+=a;
      }
    }
  }
  const double full=grid.dx_m*grid.dx_m;
  for(std::size_t cell=0;cell<nc;++cell) {
    const double difference=std::abs(out.valid_m2[cell]-full);
    require(difference<=std::max(1e-7,full*1e-10),"P2_GLC_INCOMPLETE_CELL_COVERAGE");
    double sum=0;
    for(std::size_t k=0;k<kGLC.size();++k)sum+=out.area_m2[cell*kGLC.size()+k];
    require(std::abs(sum-out.valid_m2[cell])<=std::max(1e-7,full*1e-10),
            "P2_GLC_AREA_CONSERVATION_FAILURE");
  }
  return out;
}
} // namespace cteas::reconstruction::geo
