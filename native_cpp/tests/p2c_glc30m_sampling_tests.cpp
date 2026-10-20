// Issue #160 C4 source-pixel 30m GLAZAS synthetic counterexamples.
#include "cteas/geo/p2c_glc30m_sampling.hpp"
#include "cteas/geo/glcc_raw_fractions.hpp"
#include <gdal_priv.h>
#include <ogr_spatialref.h>
#include <array>
#include <chrono>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace cteas::reconstruction::geo;
namespace {
namespace fs=std::filesystem;
void check(bool value,const char* reason){if(!value)throw std::runtime_error(reason);}
template<typename Func>void rejects(Func f,const char* reason){
  bool caught=false;
  try{f();}catch(const std::exception&){caught=true;}
  check(caught,reason);
}
std::size_t category(int cls){
  for(std::size_t n=0;n<38;++n)if(kGlccUsgs92Classes[n]==cls)return n;
  throw std::runtime_error("unknown test class");
}
void make_tiff(const fs::path& path,std::uint8_t injected) {
  GDALAllRegister();
  auto* driver=GetGDALDriverManager()->GetDriverByName("GTiff");
  check(driver!=nullptr,"GDAL_GTiff_MISSING");
  auto* ds=driver->Create(path.string().c_str(),4,4,1,GDT_Byte,nullptr);
  check(ds!=nullptr,"GDAL_TEST_SOURCE_CREATE");
  const double gt[6]{0.,30.,0.,120.,0.,-30.};
  check(ds->SetGeoTransform(const_cast<double*>(gt))==CE_None,"SOURCE_AFFINE");
  OGRSpatialReference ref;
  ref.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  check(ref.importFromEPSG(32650)==OGRERR_NONE,"TEST_EPSG");
  char* wkt=nullptr;
  check(ref.exportToWkt(&wkt)==OGRERR_NONE,"TEST_WKT");
  check(ds->SetProjection(wkt)==CE_None,"TEST_PROJECTION");
  CPLFree(wkt);
  std::array<std::uint8_t,16> v{{
      injected,52,210,210,
      52,52,210,210,
      52,52,210,210,
      52,52,210,210
  }};
  check(ds->GetRasterBand(1)->SetNoDataValue(0.)==CE_None,"TEST_NODATA");
  check(ds->GetRasterBand(1)->RasterIO(GF_Write,0,0,4,4,
           v.data(),4,4,GDT_Byte,0,0,nullptr)==CE_None,"TEST_RASTER_WRITE");
  GDALClose(ds);
}
} // namespace

int main(int argc,char** argv){
  check(argc==2,"policy path required");
  const auto policy=load_p2c_glc30m_policy(fs::path(argv[1]));
  check(policy.source_to_usgs[52]==42 &&
        policy.source_to_usgs[183]==77 &&
        policy.source_to_usgs[184]==77,
        "P2C_USER_SELECTED_FIXED_POLICY_MUST_MATCH");
  check(policy.source_to_usgs[210]==-1,
        "WATER_MUST_STAY_CONDITIONAL_NOT_FIXED");
  const auto seed=std::chrono::steady_clock::now().time_since_epoch().count();
  const auto dir=fs::temp_directory_path()/("cteas-p2c-synthetic-"+std::to_string(seed));
  check(fs::create_directory(dir),"TEMP_CREATE");
  try {
    const auto tif=dir/"synthetic.tif";
    make_tiff(tif,0);
    const P2Grid g{0.,0.,100.,1,1};
    const auto actual=sample_p2c_glc30m(tif,g,32650,policy,nullptr,10);
    // Independently counted from 30m source pixels: within 0..100m,
    // 33 of 40 subpoint offsets each axis remain in domain. First
    // upper-left 10x10 masked; valid 52 forest: 20*33-100=560;
    // valid 210 water: 13*33=429; 560+429=989 exact integer votes.
    check(actual.hits.included==989&&actual.hits.samples[0]==989,
          "P2C_INDEPENDENT_SYNTHETIC_SUBPOINT_HITS");
    check(actual.hits.counts[category(42)]==560&&
          actual.hits.counts[category(52)]==429&&
          actual.hits.counts[category(55)]==0,
          "P2C_GLC52_FOREST_VS_GLC210_INLAND_WATER");
    check(actual.water_land_hits==429&&actual.water_sea_hits==0,
          "P2C_INLAND_WATER_52_ONLY");
    check(actual.hits.outside==511&&actual.hits.rejected_coast==0,
          "P2C_VALID_SOURCE_SUBPOINT_CONSERVATION");
    check(actual.masked_pixels==1 &&
          actual.source_pixel_histogram[52]==7 &&
          actual.source_pixel_histogram[210]==8,
          "P2C_NODATA_NOT_SILENT_MARINE_FILL");
    rejects([&]{(void)sample_p2c_glc30m(tif,g,32650,policy,nullptr,5);},
            "P2C_MESHGLAZ10_FROZEN");
    rejects([&]{(void)sample_p2c_glc30m(tif,
                  P2Grid{0,0,100,2,1},32650,policy,nullptr,10);},
            "P2C_NO_CROPPED_INPUT_COVERAGE");
    // A different class code must never be silently mapped by number.
    make_tiff(tif,99);
    rejects([&]{(void)sample_p2c_glc30m(tif,g,32650,policy,nullptr,10);},
            "P2C_REJECT_UNKNOWN_VALID_SOURCE_CLASS");
  }catch(...){fs::remove_all(dir);throw;}
  fs::remove_all(dir);
  std::cout<<"P2C_C4_GLC30M_SOURCE_SUBPOINT=PASS_SYNTHETIC_ONLY "
              "FIRST_VALID_REAL_INPUT=NOT_RUN INDEPENDENT_40K_HITS=NOT_RUN\n";
  return 0;
}
