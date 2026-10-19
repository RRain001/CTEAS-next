#pragma once
// Issue #123 D2: isolated CTGPROC-style IPTYPE classifier.
// This is NOT the original Fortran PNPOLY/GLOBE/COASTEXT numeric parity gate.
// Official GSHHG "Full" resolution only, L1+L2+L3+L4 hierarchy.
// No references to frozen P2-B EXACT_AREA or any P2-A production CLI.
#include <array>
#include <cstddef>
#include <filesystem>
#include <memory>
#include <vector>
#include <ogr_geometry.h>

namespace cteas::reconstruction::geo {
struct OriginalCoastPolygon {
  int level=0; // 1 mainland, 2 lake, 3 island-in-lake, 4 pond-on-island
  std::unique_ptr<OGRGeometry> geometry; // planar model UTM metres
};

class OriginalGshhsPointClassifier {
public:
  explicit OriginalGshhsPointClassifier(std::vector<OriginalCoastPolygon> polygons);
  // Inputs deliberately follow original LUGRID: model coordinates in km,
  // rounded to REAL*4 by the historical GLOBE/LUGRID arithmetic.
  [[nodiscard]] int iptype_model_km(float x_km,float y_km,bool lcoast=true) const;
  [[nodiscard]] std::size_t polygon_count() const noexcept {return polygons_.size();}
  // Caller MUST independently SHA-verify official v2.3.7 archive/sidecars.
  // This loader checks layer names, CRS, geometry, bounded window and level.
  // It does not assert equivalent original FORTRAN coastline extraction.
  [[nodiscard]] static OriginalGshhsPointClassifier load_full_l1_to_l4(
      const std::array<std::filesystem::path,4>& shapefiles,
      int utm_epsg, const std::array<double,4>& model_bounds_utm_m);
private:
  std::vector<OriginalCoastPolygon> polygons_;
};
} // namespace cteas::reconstruction::geo
