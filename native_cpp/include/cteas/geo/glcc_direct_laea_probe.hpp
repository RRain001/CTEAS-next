#pragma once
// Shared exact-source Direct LAEA projector for selected P2-A D1 production
// and its separately recomputed forensic sidecar. The UTM50N Hefei case
// passed authentic unmodified original GLAZAS integer/fraction science in
// Run #39188861410. Other WGS84 UTM zones are an engineering extension,
// NOT covered by that science verdict; retain provenance and no false PASS.
#include <ogr_spatialref.h>
#include <cmath>
#include <memory>
#include <stdexcept>
namespace cteas::reconstruction::geo {
struct DirectLaeaPoint {
  float x_km=0.f,y_km=0.f;
  int i=0,j=0;
  float laea_x_km=0.f,laea_y_km=0.f;
};
// CTGPROC COORDLIB 1.99: XMULTO is implicitly REAL*4 and receives 0.001,
// then COORDS computes XYZIO = CRDIO * DBLE(XMULTO) in REAL*8.
// GLOBE finally stores SNGL(XYZIO) in its REAL*4 kilometre output.
// Multiplication by double(0.001f) is intentionally NOT metres / 1000.0.
// Diagnostic only: the production GLCC GEN-replay already stages XMULTO.
[[nodiscard]] inline float coordlib_real4_km_from_metres(double metres) {
  const float xmulto=0.001f;
  return static_cast<float>(metres*static_cast<double>(xmulto));
}
class DirectLaeaProbe {
public:
  explicit DirectLaeaProbe(int utm_epsg) :
    transform_(nullptr,OCTDestroyCoordinateTransformation) {
    // WGS84 UTM north/south only. The genuine original parity verdict
    // remains scoped to the pinned Hefei zone-50N case.
    if(!((utm_epsg>=32601 && utm_epsg<=32660) ||
         (utm_epsg>=32701 && utm_epsg<=32760)))
      throw std::invalid_argument("DIRECT_LAEA_PROBE_WGS84_UTM_ONLY");
    source_.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
    target_.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
    if(source_.importFromProj4("+proj=laea +lat_0=45 +lon_0=100 "
                "+R=6370997 +units=m +no_defs +type=crs")!=OGRERR_NONE
        || target_.importFromEPSG(utm_epsg)!=OGRERR_NONE)
      throw std::runtime_error("DIRECT_LAEA_PROBE_CRS_FAILURE");
    transform_.reset(OGRCreateCoordinateTransformation(&source_,&target_));
    if(!transform_)throw std::runtime_error("DIRECT_LAEA_PROBE_TRANSFORM_FAILURE");
  }
  DirectLaeaProbe(const DirectLaeaProbe&)=delete;
  DirectLaeaProbe& operator=(const DirectLaeaProbe&)=delete;

  [[nodiscard]] DirectLaeaPoint project(int source_i,int source_j,
                    int mesh_i,int mesh_j,int mesh,float x0,float y0,
                    float step) const {
    if(source_i<1||source_j<1||mesh<1||mesh>50||
       mesh_i<1||mesh_i>mesh||mesh_j<1||mesh_j>mesh||
       !(step>0.f)||!std::isfinite(step))
      throw std::invalid_argument("DIRECT_LAEA_PROBE_BAD_MESH");
    // All intermediate LAEA coordinates reproduce the exact grouping of
    // original Fortran REAL*4 expressions (CTGPROC GLOBAL branch).
    const float xc=-8000.f+1.f*static_cast<float>(source_i-1);
    const float yc=-5499.f+1.f*static_cast<float>(source_j-1);
    const float dx=1.f,dy=1.f;
    const float xx=xc-.5f*dx, yy=yc-.5f*dy;
    const float dxmesh=dx/static_cast<float>(mesh);
    const float dymesh=dy/static_cast<float>(mesh);
    const float xmesh=xx+(static_cast<float>(mesh_i)-.5f)*dxmesh;
    const float ymesh=yy+(static_cast<float>(mesh_j)-.5f)*dymesh;
    double east=1000.*static_cast<double>(xmesh);
    double north=1000.*static_cast<double>(ymesh);
    if(!transform_->Transform(1,&east,&north)||
       !std::isfinite(east)||!std::isfinite(north))
      throw std::runtime_error("DIRECT_LAEA_PROBE_PROJECT_FAILED");
    // Respect COORDS REAL*4 XMULTO staging before GLOBE REAL*4 output.
    // Keep GDAL projection itself unchanged: source-parity remains diagnostic.
    const float x=coordlib_real4_km_from_metres(east);
    const float y=coordlib_real4_km_from_metres(north);
    const float delta_x=x-x0;
    const float delta_y=y-y0;
    const int i=static_cast<int>(delta_x/step)+(delta_x>=0.f?1:0);
    const int j=static_cast<int>(delta_y/step)+(delta_y>=0.f?1:0);
    return {x,y,i,j,xmesh,ymesh};
  }
private:
  OGRSpatialReference source_,target_;
  std::unique_ptr<OGRCoordinateTransformation,
                  decltype(&OCTDestroyCoordinateTransformation)> transform_;
};
} // namespace cteas::reconstruction::geo
