#include "cteas/geo/source_inputs.hpp"
#include "cteas_atmos/core/regular_grid.hpp"
#include <gdal_priv.h>
#include <ogr_spatialref.h>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
namespace fs = std::filesystem;
namespace geo = cteas::reconstruction::geo;
template<class F> void must_throw(F f) {
  bool caught=false; try { f(); } catch(const std::exception&) { caught=true; }
  if(!caught) throw std::runtime_error("expected P1 input rejection");
}
void fixture(const fs::path& path, bool set_nodata, int epsg=4326) {
  GDALAllRegister();
  auto* driver=GetGDALDriverManager()->GetDriverByName("GTiff");
  auto* ds=driver->Create(path.string().c_str(),2,2,1,GDT_Int16,nullptr);
  if(!ds) throw std::runtime_error("fixture creation failed");
  double tr[6]={117.,0.001,0.,32.,0.,-0.001};
  if(ds->SetGeoTransform(tr)!=CE_None) throw std::runtime_error("fixture transform failed");
  OGRSpatialReference srs; if(srs.importFromEPSG(epsg)!=OGRERR_NONE) throw std::runtime_error("fixture EPSG failed");
  if(ds->SetSpatialRef(&srs)!=CE_None) throw std::runtime_error("fixture CRS failed");
  auto* band=ds->GetRasterBand(1);
  if(set_nodata && band->SetNoDataValue(-32768.)!=CE_None) throw std::runtime_error("fixture nodata failed");
  std::int16_t pixels[4]={100,-32768,0,-12};
  if(band->RasterIO(GF_Write,0,0,2,2,pixels,2,2,GDT_Int16,0,0,nullptr)!=CE_None)
    throw std::runtime_error("fixture write failed");
  GDALClose(ds);
}
int main() {
  const auto dir=fs::temp_directory_path()/"cteas_p1_input_unit";
  fs::create_directories(dir);
  try {
    fixture(dir/"elevation.tif",true);
    auto raster=geo::read_srtm_geotiff(dir/"elevation.tif");
    if(raster.raw_elevation_m.nx()!=2 || raster.raw_elevation_m.ny()!=2 ||
       raster.raw_elevation_m(0,0)!=100 || raster.raw_elevation_m(0,1)!=0 ||
       raster.raw_elevation_m(1,1)!=-12 || !raster.valid.is_missing(1,0) ||
       !raster.valid.is_valid(0,1) || std::abs(raster.geo_transform[1]-0.001)>1e-12)
      throw std::runtime_error("P1 fixture mismatch");
    fixture(dir/"no_nodata.tif",false);
    must_throw([&]{ (void)geo::read_srtm_geotiff(dir/"no_nodata.tif"); });
    fixture(dir/"wrong_crs.tif",true,4267);
    must_throw([&]{ (void)geo::read_srtm_geotiff(dir/"wrong_crs.tif"); });
    {std::ofstream f(dir/"tile.bbox"); f<<"# comment\n117.1 31.8 117.2 32.0\n";}
    if(std::abs(geo::read_bbox(dir/"tile.bbox").east_deg-117.2)>1e-12) throw std::runtime_error("P1 bbox mismatch");
    {std::ofstream f(dir/"tile.bbox"); f<<"0 100 -1 101\n";}
    must_throw([&]{ (void)geo::read_bbox(dir/"tile.bbox"); });
    cteas::atmos::RegularHorizontalGrid grid(cteas::atmos::Shape2D(50,50),
      513384.6439571-2500.,3533768.9269678-2500.,100.,100.);
    if(grid.nx()!=50 || grid.ny()!=50 || std::abs(grid.x_face(50)-grid.x_face(0)-5000.)>1e-9)
      throw std::runtime_error("50x50 grid mismatch");
    cteas::atmos::VerticalGrid vertical({0,20,40,80,160,320,640,1200,2000,3000});
    if(vertical.nz()!=9) throw std::runtime_error("nine-layer mismatch");
    fs::remove_all(dir);
    std::cout<<"PASS P1 input contracts; Fortran parity NOT TESTED\n";
    return 0;
  }catch(...){fs::remove_all(dir);throw;}
}
