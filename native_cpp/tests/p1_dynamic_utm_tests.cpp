#include "cteas/geo/terrain_grid.hpp"
#include <cpl_conv.h>
#include <ogr_spatialref.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>

using namespace cteas::reconstruction::geo;

TerrainRaster make_source(double lon,double lat) {
  OGRSpatialReference wgs;
  if(wgs.SetWellKnownGeogCS("WGS84")!=OGRERR_NONE)
    throw std::runtime_error("test WGS84 initialization failed");
  char* text=nullptr;
  if(wgs.exportToWkt(&text)!=OGRERR_NONE || !text)
    throw std::runtime_error("test WKT export failed");
  std::string wkt(text);
  CPLFree(text);
  const cteas::atmos::Shape2D shape(1,1);
  TerrainRaster raster{cteas::atmos::Array2D<std::int16_t>(shape),
                       cteas::atmos::ValidityMask2D(shape),
                       {lon-0.0005,0.001,0.0,lat+0.0005,0.0,-0.001},
                       wkt,-32768};
  raster.raw_elevation_m(0,0)=123;
  raster.valid.set_valid(0,0);
  return raster;
}
TerrainGridSpec make_grid(double lon,double lat,const UtmProjection& projection) {
  OGRSpatialReference wgs, utm;
  if(wgs.SetWellKnownGeogCS("WGS84")!=OGRERR_NONE ||
     utm.importFromEPSG((projection.southern_hemisphere?32700:32600)+projection.zone)!=OGRERR_NONE)
    throw std::runtime_error("test CRS creation failed");
  wgs.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  utm.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  OGRCoordinateTransformation* transformation=OGRCreateCoordinateTransformation(&wgs,&utm);
  if(!transformation)throw std::runtime_error("test UTM transform creation failed");
  double x=lon,y=lat;
  const bool transformed=transformation->Transform(1,&x,&y);
  OCTDestroyCoordinateTransformation(transformation);
  if(!transformed)throw std::runtime_error("test UTM projection failed");
  // Integer-metre-origin is a valid three-decimal kilometre origin.
  const double x0=std::floor(x/100.0)*100.0-150.0;
  const double y0=std::floor(y/100.0)*100.0-150.0;
  return {x0,y0,100.0,5,5};
}
void check_case(double lon,double lat,UtmProjection projection) {
  auto raster=make_source(lon,lat);
  const auto grid=make_grid(lon,lat,projection);
  const auto computed=grid_geotiff_terrain_utm(raster,grid,projection);
  const auto hits=std::accumulate(computed.point_count.begin(),
                                 computed.point_count.end(),std::uint32_t{0});
  if(hits!=1 || computed.accepted_points!=1 ||
     computed.rejected_outside!=0 || computed.rejected_missing!=0)
    throw std::runtime_error("generic projection failed to bin synthetic source pixel");
  const auto hit=std::find(computed.point_count.begin(),computed.point_count.end(),1);
  if(hit==computed.point_count.end() ||
     computed.elevation_m[static_cast<std::size_t>(hit-computed.point_count.begin())]!=123.0f)
    throw std::runtime_error("generic terrain aggregation mismatch");
  if(projection.zone==50 && !projection.southern_hemisphere) {
    const auto legacy=grid_geotiff_terrain_utm50n(raster,grid);
    if(legacy.point_count!=computed.point_count ||
       legacy.elevation_m!=computed.elevation_m ||
       legacy.accepted_points!=computed.accepted_points ||
       legacy.rejected_outside!=computed.rejected_outside)
      throw std::runtime_error("frozen 50N wrapper not bitwise-equivalent to general path");
  }
}
int main() {
  // Two northern zones, one southern zone; no real DEM or original TERREL claim.
  check_case(117.0,31.0,{50,false});
  check_case(111.0,31.0,{49,false});
  check_case(117.0,-31.0,{50,true});
  auto source=make_source(117.0,31.0);
  const auto grid=make_grid(117.0,31.0,{50,false});
  for(const int zone: {0,61}) {
    bool rejected=false;
    try {(void)grid_geotiff_terrain_utm(source,grid,{zone,false});}
    catch(const std::invalid_argument&) {rejected=true;}
    if(!rejected)throw std::runtime_error("invalid UTM zone accepted");
  }
  std::cout<<"P1_DYNAMIC_UTM_SOFTWARE_ONLY=PASS; ORIGINAL_PARITY=NOT_RUN; REAL_DEM=NOT_RUN\n";
}
