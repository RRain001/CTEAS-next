#include "cteas/geo/glc_area_fractions.hpp"
#include <gdal_priv.h>
#include <ogr_spatialref.h>
#include <array>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace cteas::reconstruction::geo;
namespace {
void expect(bool v,const char* m){if(!v)throw std::runtime_error(m);}
template<class F> void rejects(F f,const char* m){bool ok=false;try{f();}catch(const std::exception&){ok=true;}expect(ok,m);}
void fixture(const std::filesystem::path& name,const std::array<unsigned char,16>& data,
             int epsg=32650,bool rotated=false) {
  GDALAllRegister();
  auto* drv=GetGDALDriverManager()->GetDriverByName("GTiff");
  auto* ds=drv->Create(name.string().c_str(),4,4,1,GDT_Byte,nullptr);
  expect(ds!=nullptr,"cannot create fixture");
  double gt[]={-10.,30.,rotated?1.:0.,110.,0.,-30.};
  expect(ds->SetGeoTransform(gt)==CE_None,"fixture GT");
  OGRSpatialReference srs; expect(srs.importFromEPSG(epsg)==OGRERR_NONE,"fixture EPSG");
  expect(ds->SetSpatialRef(&srs)==CE_None,"fixture CRS");
  auto* b=ds->GetRasterBand(1);
  expect(b->SetNoDataValue(0.)==CE_None,"fixture nodata");
  expect(b->RasterIO(GF_Write,0,0,4,4,const_cast<unsigned char*>(data.data()),4,4,GDT_Byte,0,0,nullptr)==CE_None,"fixture pixel");
  GDALClose(ds);
}
} // namespace
int main() {
  const auto root=std::filesystem::temp_directory_path() / "cteas-p2-glc-area-test";
  std::filesystem::remove_all(root);std::filesystem::create_directories(root);
  try {
    std::array<unsigned char,16> a{};a.fill(20);a[0]=10;a[15]=210;
    fixture(root/"ok.tif",a);
    auto r=compute_glc_area_fractions((root/"ok.tif").string(),{0,0,100,1,1},32650);
    expect(std::abs(r.fraction(0,0,0)-0.04)<1e-12,"400m2 rainfed corner");
    expect(std::abs(r.fraction(0,0,3)-0.92)<1e-12,"9200m2 irrigated middle");
    expect(std::abs(r.fraction(0,0,33)-0.04)<1e-12,"400m2 water corner");
    expect(r.valid_m2[0]==10000.,"complete exact area");
    rejects([&]{(void)compute_glc_area_fractions((root/"ok.tif").string(),{0,0,100,2,1},32650);},"incomplete area accepted");
    rejects([&]{(void)compute_glc_area_fractions((root/"ok.tif").string(),{0,0,100,1,1},32649);},"CRS mismatch accepted");
    a[0]=0;fixture(root/"nodata.tif",a);
    rejects([&]{(void)compute_glc_area_fractions((root/"nodata.tif").string(),{0,0,100,1,1},32650);},"nodata accepted");
    a[0]=99;fixture(root/"unknown.tif",a);
    rejects([&]{(void)compute_glc_area_fractions((root/"unknown.tif").string(),{0,0,100,1,1},32650);},"illegal category accepted");
    a[0]=10;fixture(root/"rotated.tif",a,32650,true);
    rejects([&]{(void)compute_glc_area_fractions((root/"rotated.tif").string(),{0,0,100,1,1},32650);},"rotation accepted");
    std::cout<<"P2_GLC_RAW_AREA_SYNTHETIC=PASS MAPPING=REVIEW_REQUIRED\n";
  }catch(...){std::filesystem::remove_all(root);throw;}
  std::filesystem::remove_all(root);
}
