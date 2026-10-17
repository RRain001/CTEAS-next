#include "cteas/geo/landuse_fraction.hpp"
#include <ogr_spatialref.h>
#include <cmath>
#include <limits>
#include <memory>
#include <stdexcept>
#include <unordered_map>
namespace cteas::reconstruction::geo {
double P2Fractions::fraction(std::size_t i,std::size_t j,std::size_t k) const {
  if(i>=grid.nx||j>=grid.ny||k>=categories.size())
    throw std::out_of_range("P2 fraction index");
  const std::size_t cell=j*grid.nx+i;
  if(!cell_samples.at(cell))
    throw std::domain_error("P2 cell is missing; fraction undefined");
  return static_cast<double>(counts.at(cell*categories.size()+k))/
         static_cast<double>(cell_samples.at(cell));
}
P2Fractions compute_generic_utm50n(const GenericLanduse& input,P2Grid grid) {
  if(input.datum!="ESR-S"||input.categories.empty()||input.points.empty())
    throw std::invalid_argument("P2 GEN subset needs ESR-S categories and points");
  if(!std::isfinite(grid.x0_m)||!std::isfinite(grid.y0_m)||
     !std::isfinite(grid.dx_m)||grid.dx_m<=0||grid.nx==0||grid.ny==0)
    throw std::invalid_argument("P2 invalid grid");
  if(grid.nx>std::numeric_limits<std::size_t>::max()/grid.ny)
    throw std::overflow_error("P2 grid size overflow");
  const std::size_t nc=grid.nx*grid.ny;
  if(input.categories.size()>std::numeric_limits<std::size_t>::max()/nc)
    throw std::overflow_error("P2 category size overflow");
  std::unordered_map<int,std::size_t> codes;
  for(std::size_t k=0;k<input.categories.size();++k)
    if(!codes.emplace(input.categories[k],k).second)
      throw std::invalid_argument("P2 duplicated category");
  OGRSpatialReference sphere,utm;
  if(sphere.importFromProj4("+proj=longlat +a=6370997 +b=6370997 +no_defs +type=crs")!=OGRERR_NONE||
     utm.importFromEPSG(32650)!=OGRERR_NONE)
    throw std::runtime_error("P2 CRS registration failed");
  sphere.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  utm.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  const auto cleanup=[](OGRCoordinateTransformation* t){if(t)OCTDestroyCoordinateTransformation(t);};
  std::unique_ptr<OGRCoordinateTransformation,decltype(cleanup)> transformer(
     OGRCreateCoordinateTransformation(&sphere,&utm),cleanup);
  if(!transformer)throw std::runtime_error("P2 projection unavailable");
  P2Fractions out{grid,input.categories,
     std::vector<std::uint32_t>(nc*input.categories.size(),0),
     std::vector<std::uint32_t>(nc,0),0,0};
  // Target the original LUGRID real*4 indexing, not double-precision floor.
  const float x0=static_cast<float>(grid.x0_m/1000.);
  const float y0=static_cast<float>(grid.y0_m/1000.);
  const float step=static_cast<float>(grid.dx_m/1000.);
  for(const auto& sample:input.points) {
    const auto found=codes.find(sample.usgs92_category);
    if(found==codes.end())throw std::invalid_argument("P2 unknown input class");
    // CTGPROC COMP reads relon/rnlat into implicit Fortran REAL*4 first.
    // Preserve that quantization BEFORE any datum/projection conversion.
    // Without it two near-boundary samples are counted incorrectly in Hefei.
    double x=static_cast<double>(static_cast<float>(sample.longitude_deg));
    double y=static_cast<double>(static_cast<float>(sample.latitude_deg));
    if(!std::isfinite(x)||!std::isfinite(y)||
       !transformer->Transform(1,&x,&y))
      throw std::runtime_error("P2 coordinate conversion failure");
    // COORDLIB::COORDS uses implicit REAL*4 XMULTO = 0.001 and
    // evaluates CRDIO * DBLE(XMULTO) before GLOBE writes REAL*4 km.
    // Exactly dividing by 1000 misallocates boundary-point classes in
    // the heterogeneous 100 m reference, despite equal total hit count.
    const double legacy_m_to_km=static_cast<double>(0.001f);
    const float dx=static_cast<float>(x*legacy_m_to_km)-x0;
    const float dy=static_cast<float>(y*legacy_m_to_km)-y0;
    const int i=static_cast<int>(dx/step)+(dx>=0?1:0);
    const int j=static_cast<int>(dy/step)+(dy>=0?1:0);
    if(i<1||j<1||static_cast<std::size_t>(i)>grid.nx||
       static_cast<std::size_t>(j)>grid.ny) {++out.outside;continue;}
    const std::size_t cell=(static_cast<std::size_t>(j)-1)*grid.nx+
                           (static_cast<std::size_t>(i)-1);
    ++out.cell_samples[cell];
    ++out.counts[cell*input.categories.size()+found->second];
    ++out.included;
  }
  return out;
}
} // namespace cteas::reconstruction::geo
