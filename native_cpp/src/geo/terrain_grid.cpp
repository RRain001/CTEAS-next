#include "cteas/geo/terrain_grid.hpp"
#include <ogr_spatialref.h>
#include <algorithm>
#include <cmath>
#include <limits>
#include <memory>
#include <stdexcept>
namespace cteas::reconstruction::geo {
namespace {
void check_spec(const TerrainGridSpec& spec) {
  if(!std::isfinite(spec.southwest_x_m)||!std::isfinite(spec.southwest_y_m)||
     !std::isfinite(spec.cell_size_m)||spec.cell_size_m<=0.0||
     spec.nx==0||spec.ny==0||spec.nx>100000||spec.ny>100000||
     spec.nx>std::numeric_limits<std::size_t>::max()/spec.ny)
    throw std::invalid_argument("P1 invalid terrain grid");
}
}
std::optional<std::pair<std::size_t,std::size_t>>
cell_index_terrel(float east_m,float north_m,const TerrainGridSpec& spec) {
  check_spec(spec);
  if(!std::isfinite(east_m)||!std::isfinite(north_m)) return std::nullopt;
  // Original GRID real*4: km control coordinates converted to meters.
  const float xll=static_cast<float>(spec.southwest_x_m/1000.0f)*1000.0f;
  const float yll=static_cast<float>(spec.southwest_y_m/1000.0f)*1000.0f;
  const float scale=1.0f/static_cast<float>(spec.cell_size_m);
  const float xi=(east_m-xll)*scale;
  const float yi=(north_m-yll)*scale;
  if(!std::isfinite(xi)||!std::isfinite(yi) ||
     xi < -1.0f || yi < -1.0f ||
     xi >= static_cast<float>(spec.nx) || yi >= static_cast<float>(spec.ny))
    return std::nullopt;
  // TERREL CELLIND: INT(xi), then increment iff xi >= 0.
  const int ix=static_cast<int>(xi)+(xi>=0?1:0);
  const int iy=static_cast<int>(yi)+(yi>=0?1:0);
  if(ix<1||iy<1||static_cast<std::size_t>(ix)>spec.nx||
     static_cast<std::size_t>(iy)>spec.ny) return std::nullopt;
  return std::pair<std::size_t,std::size_t>{static_cast<std::size_t>(ix-1),
                                            static_cast<std::size_t>(iy-1)};
}
TerrainGridResult grid_geotiff_terrain_utm50n(
    const TerrainRaster& source,const TerrainGridSpec& spec) {
  check_spec(spec);
  if(source.crs_wkt.empty())
    throw std::invalid_argument("P1 GeoTIFF missing CRS identity");
  const auto nx=source.raw_elevation_m.nx(), ny=source.raw_elevation_m.ny();
  if(nx==0||ny==0)
    throw std::invalid_argument("P1 empty terrain image");
  // The current subset has no source-NoData policy equivalent to legacy
  // LOADTIFF's special elevation replacement/void-filling switches.
  // Refuse to generate apparently complete science output if any are present.
  for(std::size_t j=0;j<ny;++j)
    for(std::size_t i=0;i<nx;++i)
      if(source.valid.is_missing(i,j))
        throw std::invalid_argument("P1 GeoTIFF source contains unsupported NoData; no filling or dropping permitted");
  const auto& t=source.geo_transform;
  if(t[2]!=0.0 || t[4]!=0.0 || t[1]<=0.0 || t[5]>=0.0)
    throw std::invalid_argument("P1 subset only supports north-up geographic GeoTIFF");
  // GET_IFD returns approximate center of pixel (1,1); x/y/deltas
  // are stored as original Fortran default REAL*4.
  const float xorg=static_cast<float>(t[0]+t[1]*0.5);
  const float yorg=static_cast<float>(t[3]+t[5]*0.5);
  const float ddx=static_cast<float>(t[1]);
  const float ddy=static_cast<float>(t[5]);
  OGRSpatialReference srs,utm;
  OGRSpatialReference wgs84;
  if(srs.importFromWkt(source.crs_wkt.c_str())!=OGRERR_NONE||
     utm.importFromEPSG(32650)!=OGRERR_NONE ||
     wgs84.SetWellKnownGeogCS("WGS84")!=OGRERR_NONE ||
     !srs.IsGeographic() || !srs.IsSameGeogCS(&wgs84))
    throw std::runtime_error("P1 subset requires WGS84 geographic GeoTIFF to UTM50N");
  srs.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  utm.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  const auto cleanup=[](OGRCoordinateTransformation* p){if(p)OCTDestroyCoordinateTransformation(p);};
  std::unique_ptr<OGRCoordinateTransformation,decltype(cleanup)> transformation(
      OGRCreateCoordinateTransformation(&srs,&utm),cleanup);
  if(!transformation)
    throw std::runtime_error("P1 cannot create geographic-to-UTM transform");
  const auto cells=spec.nx*spec.ny;
  TerrainGridResult out{spec,std::vector<std::uint32_t>(cells,0),
                        std::vector<float>(cells,-999.0f),0,0,0};
  std::vector<float> sum(cells,0.0f);
  // Raster row 0 is north; model row 0 is south.
  for(std::size_t j=0;j<ny;++j) for(std::size_t i=0;i<nx;++i) {
    const float lon=xorg+static_cast<float>(i)*ddx;
    const float lat=yorg+static_cast<float>(j)*ddy;
    double x=lon,y=lat;
    if(!transformation->Transform(1,&x,&y))
      throw std::runtime_error("P1 coordinate transform failed");
    // COORDLIB/COORDS declares XMULTO implicitly as default REAL*4
    // and stores XMULTO=0.001 before evaluating CRDIO*DBLE(XMULTO).
    // The float32 value is 0.0010000000474974513, NOT exact 1/1000.
    // GLOBE writes the result to REAL*4 km, and LOADTIFF multiplies by
    // REAL*4 1000.0 before its SAVEELEV/CELLIND steps. This factor is
    // required for the 10 near-cell-boundary Hefei discrepancies.
    const double legacy_metres_to_km=static_cast<double>(0.001f);
    const float projected_x=static_cast<float>(x*legacy_metres_to_km)*1000.0f;
    const float projected_y=static_cast<float>(y*legacy_metres_to_km)*1000.0f;
    const auto cell=cell_index_terrel(projected_x,projected_y,spec);
    if(!cell) {++out.rejected_outside;continue;}
    const auto offset=cell->second*spec.nx+cell->first;
    ++out.point_count[offset];
    sum[offset]+=static_cast<float>(source.raw_elevation_m(i,j));
    ++out.accepted_points;
  }
  for(std::size_t cell=0;cell<cells;++cell) {
    if(out.point_count[cell])
      out.elevation_m[cell]=sum[cell]/static_cast<float>(out.point_count[cell]);
  }
  return out;
}
} // namespace cteas::reconstruction::geo
