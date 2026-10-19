#pragma once
// #123 D4: C++ reproduction candidate for original CTGPROC v7.0.0
// COASTRD (BLN) -> IPTYPE -> PNPOLY REAL*4 semantics.
//
// Unlike D2's GEOS test adapter, this accepts the ORIGINAL-extracted
// BLN polygon order and its REAL*4 kilometre coordinates. It is not
// yet proved numerically equal to the unmodified original Fortran.
#include <cstddef>
#include <filesystem>
#include <span>
#include <vector>

namespace cteas::reconstruction::geo {
struct OriginalBlnVertexR4 {float x_km=0.f,y_km=0.f;};
struct OriginalBlnPolygonR4 {
  int type=0, source=0, polygon_id=0, iside=0;
  std::vector<OriginalBlnVertexR4> points; // preserve original order / closure
  float xmin=0.f,xmax=0.f,ymin=0.f,ymax=0.f;
};
// Exactly matches PNPOLY's result DOMAIN, not a GEOS test:
// -1 outside; 0 on edge/vertex; +1 inside.
// Coordinates and every intermediate expression are IEEE REAL*4 float.
[[nodiscard]] int original_pnpoly_r4(float px,float py,
    std::span<const OriginalBlnVertexR4> ordered_vertices);

class OriginalBlnIptypeR4 {
public:
  explicit OriginalBlnIptypeR4(std::vector<OriginalBlnPolygonR4> polygons);
  [[nodiscard]] int iptype(float px_km,float py_km,bool lcoast=true) const;
  [[nodiscard]] std::size_t polygon_count() const noexcept {return polygons_.size();}
  // Mirrors COASTRD's list-directed BLN input, without reading vendor
  // binary or fabricating surrounding polygons; strict bounds fail closed.
  [[nodiscard]] static OriginalBlnIptypeR4 load_coastrd_bln(
      const std::filesystem::path& bln,
      float xllk,float yllk,float xurk,float yurk);
private:
  std::vector<OriginalBlnPolygonR4> polygons_;
};
} // namespace cteas::reconstruction::geo
