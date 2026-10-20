#include "cteas/geo/p2c_glc30m_sampling.hpp"
#include "cteas/geo/glcc_raw_fractions.hpp"
#include <cpl_json.h>
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
void need(bool v,const char* error) { if(!v)throw std::runtime_error(error); }
constexpr std::array<int,35> kSourceCodes{{
  10,11,12,20,51,52,61,62,71,72,81,82,91,92,120,121,122,130,
  140,150,152,153,181,182,183,184,185,186,187,190,200,201,202,210,220
}};
std::size_t usgs_index(int id) {
  auto it=std::find(kGlccUsgs92Classes.begin(),kGlccUsgs92Classes.end(),id);
  need(it!=kGlccUsgs92Classes.end(),"P2C_POLICY_UNSUPPORTED_USGS_TARGET");
  return std::size_t(it-kGlccUsgs92Classes.begin());
}
int assign(float x_km,float y_km,float x0_km,float y0_km,
           float spacing_km,std::size_t n,int which) {
  const float delta = (which==0 ? x_km-x0_km : y_km-y0_km);
  need(std::isfinite(delta),"P2C_NONFINITE_SAMPLE_COORDINATE");
  const double quotient=double(delta)/double(spacing_km);
  need(quotient>-1000000.&&quotient<1000000.,"P2C_SAMPLE_INDEX_OVERFLOW");
  // Faithful original GLOBE/LUGRID REAL*4 binning, including negative
  // signed coordinate behavior. No floor() or round() substitution.
  const int index=static_cast<int>(delta/spacing_km)+(delta>=0.f?1:0);
  return (index>=1&&std::size_t(index)<=n)?index:0;
}
} // namespace

P2cGlc30mPolicy load_p2c_glc30m_policy(const std::filesystem::path& path) {
  CPLJSONDocument d;
  need(d.Load(path.string()),"P2C_POLICY_JSON_UNREADABLE");
  const auto root=d.GetRoot();
  need(root.GetString("schema","")==
       "cteas.p2b.glc35_usgs38_user_selected_mapping.v1",
       "P2C_POLICY_SCHEMA_DRIFT");
  need(root.GetString("decision","")==
       "USER_SELECTED_34_FIXED_CLASSES_AND_GLC210_L1_LAND_TO_52_SEA_TO_55",
       "P2C_USER_SELECTED_MAPPING_DECISION_DRIFT");
  need(root.GetString("output_contract","")=="USGS92_38_CLASS_LU_DAT_V2_1",
       "P2C_POLICY_USGS38_CONTRACT");
  need(!root.GetBool("production_authorized",true),
       "P2C_POLICY_SCIENCE_STATUS_MUST_REMAIN_UNCHANGED");
  const auto fixed=root.GetArray("fixed_classes");
  need(fixed.IsValid()&&fixed.Size()==34,"P2C_FIXED_CLASSES_NOT_34");
  P2cGlc30mPolicy policy;
  policy.source_to_usgs.fill(-1);
  for(const auto& entry:fixed) {
    const int code=entry.GetInteger("glc_code",-1);
    const int dest=entry.GetInteger("usgs_code",-1);
    need(code>=0&&code<256&&code!=210&&
         policy.source_to_usgs[std::size_t(code)]==-1,
         "P2C_DUPLICATE_SOURCE_CLASS");
    (void)usgs_index(dest);
    policy.source_to_usgs[std::size_t(code)]=dest;
  }
  const auto conditional=root.GetArray("conditional_classes");
  need(conditional.IsValid()&&conditional.Size()==1&&
       conditional[0].GetInteger("glc_code",-1)==210,
       "P2C_SINGLE_CONDITIONAL_GLC210_REQUIRED");
  const auto outcomes=conditional[0].GetArray("outcomes");
  need(outcomes.IsValid()&&outcomes.Size()==2&&
       outcomes[0].GetInteger("usgs_code",-1)==52&&
       outcomes[1].GetInteger("usgs_code",-1)==55,
       "P2C_GLC210_USER_52_55_DRIFT");
  const auto source=root.GetObj("source_authentication");
  need(source.IsValid()&&source.GetString("selected_resolution","")=="f"&&
       source.GetString("primary_land_sea_polygon","")==
         "GSHHS_shp/f/GSHHS_f_L1.shp",
       "P2C_FULL_L1_REQUIRED");
  for(int code:kSourceCodes) {
    if(code==210)continue;
    need(policy.source_to_usgs[std::size_t(code)]>=0,
         "P2C_USER_POLICY_MISSING_FIXED_CLASS");
  }
  int fixed_count=0;
  for(int v:policy.source_to_usgs) fixed_count+=(v>=0);
  need(fixed_count==34&&policy.source_to_usgs[52]==42&&
       policy.source_to_usgs[183]==77&&policy.source_to_usgs[184]==77,
       "P2C_USER_SELECTED_FIXED_MAP_DRIFT");
  return policy;
}

P2cGlc30mStatistics sample_p2c_glc30m(
    const std::filesystem::path& tif, const P2Grid& grid,int epsg,
    const P2cGlc30mPolicy& policy,
    const OriginalBlnIptypeR4* coast,int mesh) {
  need(mesh==10,"P2C_MESHGLAZ_MUST_BE_10");
  need(grid.nx>0&&grid.ny>0&&grid.nx<=250000/grid.ny&&
       std::isfinite(grid.x0_m)&&std::isfinite(grid.y0_m)&&
       std::isfinite(grid.dx_m)&&grid.dx_m==100.,
       "P2C_MODEL_GRID_INVALID");
  need(epsg==32650||epsg==32652,"P2C_ONLY_TWO_REVIEWED_UTM_ZONES");
  // Only the Wolsong coastal model grid is permitted to use a coast BLN;
  // inland must not load or invoke any shoreline geometry.
  need((epsg==32652)==(coast!=nullptr),"P2C_COAST_MODE_MUST_MATCH_SITE");
  GDALAllRegister();
  using Ds=std::unique_ptr<GDALDataset,decltype(&GDALClose)>;
  Ds ds(static_cast<GDALDataset*>(GDALOpenEx(tif.string().c_str(),
        GDAL_OF_RASTER|GDAL_OF_READONLY,nullptr,nullptr,nullptr)),GDALClose);
  need(bool(ds)&&ds->GetRasterCount()==1,"P2C_SINGLE_BAND_GLC_TIFF_REQUIRED");
  const auto* srs=ds->GetSpatialRef();
  OGRSpatialReference target;
  target.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  need(target.importFromEPSG(epsg)==OGRERR_NONE && srs && srs->IsSame(&target),
       "P2C_2022_GLC_SOURCE_WRONG_UTM");
  double tr[6]{};
  need(ds->GetGeoTransform(tr)==CE_None&&
       tr[1]==30.&&tr[2]==0.&&tr[4]==0.&&tr[5]==-30.&&
       std::isfinite(tr[0])&&std::isfinite(tr[3]),
       "P2C_30M_NORTH_UP_AFFINE_REQUIRED");
  const int width=ds->GetRasterXSize(),height=ds->GetRasterYSize();
  need(width>0&&height>0&&std::uint64_t(width)*height<=1500000ULL,
       "P2C_30M_SITE_RASTER_BUDGET");
  const double xmax=grid.x0_m+grid.dx_m*double(grid.nx);
  const double ymax=grid.y0_m+grid.dx_m*double(grid.ny);
  need(tr[0]<=grid.x0_m&&tr[3]>=ymax&&
       tr[0]+double(width)*30.>=xmax&&tr[3]-double(height)*30.<=grid.y0_m,
       "P2C_REAL_20KM_RASTER_COVERAGE_REQUIRED");
  auto* band=ds->GetRasterBand(1);
  need(band!=nullptr&&band->GetRasterDataType()==GDT_Byte,
       "P2C_2022_SOURCE_UINT8_REQUIRED");
  int has_nodata=0;
  const double nodata=band->GetNoDataValue(&has_nodata);
  need(!has_nodata||nodata==0.||nodata==250.,
       "P2C_UNEXPECTED_SOURCE_NODATA");
  const std::size_t pixels=std::size_t(width)*height;
  std::vector<std::uint8_t> raw(pixels),mask(pixels);
  need(band->RasterIO(GF_Read,0,0,width,height,raw.data(),width,height,
                      GDT_Byte,0,0,nullptr)==CE_None,"P2C_TIFF_READ_FAILED");
  auto* mb=band->GetMaskBand();
  need(mb!=nullptr && mb->RasterIO(GF_Read,0,0,width,height,mask.data(),
                                  width,height,GDT_Byte,0,0,nullptr)==CE_None,
       "P2C_TIFF_MASK_READ_FAILED");
  const std::size_t cells=grid.nx*grid.ny;
  P2cGlc30mStatistics result{
      OriginalSamplingRecount{
          grid,std::vector<std::uint32_t>(cells*38,0),
          std::vector<std::uint32_t>(cells,0),
          std::vector<std::uint8_t>(cells,0),55,0,0,0}};
  result.mesh=mesh;
  const float xmin=static_cast<float>(grid.x0_m/1000.);
  const float ymin=static_cast<float>(grid.y0_m/1000.);
  const float step=static_cast<float>(grid.dx_m/1000.);
  // Per-source-30m pixel GLAZAS 10×10 evenly-spaced subpoints:
  // (subindex+.5)/MESHGLAZ. Iterate pixels in original north→south order.
  // The source is ALREADY in the model UTM, so no LAEA projection is applied
  // to a raster which does not use historical GLCC LAEA coordinates.
  for(int row=0;row<height;++row) for(int col=0;col<width;++col) {
    const auto index=std::size_t(row)*width+std::size_t(col);
    const auto code=raw[index];
    ++result.source_pixels;
    if(mask[index]==0) {++result.masked_pixels;continue;}
    if(code==0||code==250) {++result.no_data_pixels;continue;}
    const bool water=code==210;
    const int fixed=policy.source_to_usgs[std::size_t(code)];
    need(water||fixed>=0,"P2C_UNKNOWN_VALID_GLC_CLASS_FAIL_CLOSED");
    ++result.source_pixel_histogram[std::size_t(code)];
    const auto fixed_k=water?std::size_t(0):usgs_index(fixed);
    for(int im=0;im<mesh;++im)for(int jm=0;jm<mesh;++jm) {
      const double x_m=tr[0]+(double(col)+(double(im)+.5)/mesh)*30.;
      const double y_m=tr[3]-(double(row)+(double(jm)+.5)/mesh)*30.;
      // Retain original REAL*4 model-km coordinate rounding and signed
      // integer assignment. The raster pixel-to-UTM affine is exact double.
      const float x_km=static_cast<float>(x_m*double(0.001f));
      const float y_km=static_cast<float>(y_m*double(0.001f));
      const int i=assign(x_km,y_km,xmin,ymin,step,grid.nx,0);
      const int j=assign(x_km,y_km,xmin,ymin,step,grid.ny,1);
      if(i==0||j==0){++result.hits.outside;continue;}
      const auto cell=std::size_t(j-1)*grid.nx+std::size_t(i-1);
      std::size_t category=fixed_k;
      if(water) {
        const bool terrestrial=!coast||coast->iptype(x_km,y_km)!=0;
        category=usgs_index(terrestrial?52:55);
        if(terrestrial) ++result.water_land_hits;
        else ++result.water_sea_hits;
      }
      need(result.hits.samples[cell]<std::numeric_limits<std::uint32_t>::max(),
           "P2C_SAMPLES_OVERFLOW");
      ++result.hits.samples[cell];
      ++result.hits.counts[cell*38+category];
      ++result.hits.included;
      ++result.classified_sample_histogram[std::size_t(code)];
    }
  }
  std::uint64_t eligible=0, included=0;
  for(std::size_t k=0;k<256;++k)eligible+=result.source_pixel_histogram[k];
  need(eligible*std::uint64_t(mesh*mesh)==result.hits.included+result.hits.outside,
       "P2C_GLAZAS_SAMPLE_TOTAL_CONSERVATION");
  for(const auto c:result.hits.samples)included+=c;
  need(included==result.hits.included && result.hits.rejected_coast==0,
       "P2C_LUGRID_CLASSIFIED_SAMPLE_CONSERVATION");
  if(!coast)need(result.water_sea_hits==0,"P2C_HEFEI_FORBIDS_USGS55");
  return result;
}
