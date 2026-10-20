#include "cteas/geo/glc30m_point_sampling.hpp"
#include "cteas/geo/ctgproc_original_sampling_lu_writer.hpp"
#include <ogr_spatialref.h>
#include <array>
#include <cstdint>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace cteas::reconstruction::geo;
namespace {
void require(bool v,const char* error){if(!v)throw std::runtime_error(error);}
template<class F>void rejects(F fn,const char* label){
  bool thrown=false;
  try{fn();}catch(const std::exception&){thrown=true;}
  require(thrown,label);
}
const std::map<int,int> kUserMap{
 {10,21},{11,21},{12,22},{20,21},{51,42},{52,42},{61,41},{62,41},
 {71,42},{72,42},{81,41},{82,41},{91,43},{92,43},{120,32},{121,32},
 {122,32},{130,31},{140,83},{150,77},{152,77},{153,77},{181,61},
 {182,62},{183,77},{184,77},{185,61},{186,62},{187,72},{190,16},
 {200,77},{201,74},{202,73},{220,91}};
struct Raster {
  std::unique_ptr<GDALDataset,decltype(&GDALClose)> ds;
  std::vector<std::uint8_t> pixels;
  Raster():ds(nullptr,GDALClose),pixels(16,210){
    GDALAllRegister();
    auto* driver=GetGDALDriverManager()->GetDriverByName("MEM");
    require(driver!=nullptr,"GLC30M_GDAL_MEM_DRIVER");
    ds.reset(driver->Create("",4,4,1,GDT_Byte,nullptr));
    require(bool(ds),"GLC30M_SYNTHETIC_SOURCE");
    const double transform[6]{-10.,30.,0.,110.,0.,-30.};
    require(ds->SetGeoTransform(const_cast<double*>(transform))==CE_None,
            "GLC30M_GDAL_TRANSFORM");
    OGRSpatialReference crs;
    require(crs.importFromEPSG(32650)==OGRERR_NONE&&
            ds->SetSpatialRef(&crs)==CE_None,"GLC30M_SET_CRS");
    flush();
  }
  void flush(){
    require(ds->GetRasterBand(1)->RasterIO(GF_Write,0,0,4,4,
            pixels.data(),4,4,GDT_Byte,0,0,nullptr)==CE_None,
            "GLC30M_WRITE_TEST_PIXELS");
  }
};
}
int main(){
  try{
    Raster sample;
    require(kUserMap.size()==34,"GLC30M_TEST_MAP_WRONG");
    const P2Grid grid{0.,0.,100.,1,1};
    Glc30mSamplingStats st{};
    const auto land=[](double x,double){return x<50.;};
    const auto coast=sample_glc30m_original_mesh(
        *sample.ds,grid,32650,kUserMap,10,land,false,st);
    require(st.source_pixels==16 && st.generated_subpoints==1600 &&
            st.outside_subpoints==444 && st.included_subpoints==1156 &&
            st.missing_cells==0 && st.water52_hits==578 &&
            st.water55_hits==578,
            "GLC30M_INDEPENDENT_34X34_POINT_COUNT_AND_50_50_COAST");
    require(coast.samples[0]==1156 && coast.included==1156,
            "GLC30M_POINT_ACCOUNTING");
    const auto find=[](int usgs){
      for(std::size_t k=0;k<kGlccUsgs92Classes.size();++k)
        if(kGlccUsgs92Classes[k]==usgs)return k;
      throw std::runtime_error("GLC30M_BAD_CLASS");
    };
    require(coast.counts[find(52)]==578&&coast.counts[find(55)]==578,
            "GLC30M_WATER_INDEPENDENT_POINTS_ONLY");
    std::ostringstream lu;
    const auto stats=write_original_sampling_lu(
        lu,coast,false,50,"30m synthetic",
        "synthetic input, not original GLCC");
    require(stats.total_hits==1156 && stats.fraction_fields==38 &&
            lu.str().find("  50N   ")!=std::string::npos &&
            lu.str().find("0.500")!=std::string::npos,
            "GLC30M_SYNTHETIC_LU_DAT_F63_38_CLASS");
    const auto inland=sample_glc30m_original_mesh(
        *sample.ds,grid,32650,kUserMap,10,{},true,st);
    require(st.water52_hits==1156&&st.water55_hits==0&&
            inland.counts[find(52)]==1156,
            "GLC30M_INLAND_210_ONLY_52");
    rejects([&]{
      (void)sample_glc30m_original_mesh(
          *sample.ds,grid,32650,kUserMap,10,{},false,st);
    },"GLC30M_REJECT_UNCLASSIFIED_COASTAL_WATER");
    rejects([&]{
      (void)sample_glc30m_original_mesh(
          *sample.ds,grid,32650,kUserMap,10,land,true,st);
    },"GLC30M_REJECT_INLAND_SHORELINE_DEPENDENCY");
    sample.pixels[0]=0;
    sample.flush();
    const auto missing=sample_glc30m_original_mesh(
        *sample.ds,grid,32650,kUserMap,10,{},true,st);
    require(st.invalid_source_pixels==1 && st.invalid_subpoints>0 &&
            st.included_subpoints<1156 && st.water55_hits==0 &&
            missing.included==st.included_subpoints,
            "GLC30M_ZERO_NODATA_NEVER_TURNS_INTO_SEA");
    sample.pixels[0]=99;
    sample.flush();
    rejects([&]{
      (void)sample_glc30m_original_mesh(
          *sample.ds,grid,32650,kUserMap,10,{},true,st);
    },"GLC30M_REJECT_UNKNOWN_SOURCE_CODE");
    sample.pixels[0]=210;
    sample.flush();
    rejects([&]{
      (void)sample_glc30m_original_mesh(
          *sample.ds,P2Grid{0.,0.,100.,2,2},32650,
          kUserMap,10,{},true,st);
    },"GLC30M_REJECT_UNCOVERED_GRID");
    std::cout<<"P2C_30M_SYNTHETIC_REAL4_38_HITS_AND_LU=PASS"
             <<" ORIGINAL_SAMPLING_GLCC=UNCHANGED"
             <<" REAL_WOLSONG_ORACLE=NOT_RUN\n";
    return 0;
  }catch(const std::exception& e){
    std::cerr<<"P2C_30M_SYNTHETIC_FAIL:"<<e.what()<<"\n";return 2;
  }
}
