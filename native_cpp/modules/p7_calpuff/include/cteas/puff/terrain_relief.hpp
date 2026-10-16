#pragma once

#include <cstddef>
#include <functional>
#include <vector>

namespace cteas::puff {

// P7S: the terrain-state producers of CALPUFF 7.2.1, transcribed from the
// unmodified vendor source and cross-checked against it by CTest:
//   TERAVG  calpuff.for L21547-21743  (average elevation of a 45-degree strip)
//   TRELIEF calpuff.for L21205-21545  (local relief and peak elevation per cell)
//   GETELEV calpuff.for L21098-21203  (bilinear elevation interpolation)
//
// The vendor reads the elevation grid from /METHD/ and the domain from GETCELL;
// here the grid is a 1-based cell accessor and the domain is an explicit input,
// so a missing or out-of-range access fails closed. VWIDTH (L21896-22178), which
// builds the valley-width table IVALW, is NOT reconstructed.

using TerrainStateReal = float;

// A 1-based elevation accessor over one met domain.
using ElevationCell = std::function<double(int i, int j)>;

// TERAVG equivalent: the average elevation of the strip of cells that lie in the
// 45-degree sector centred on the direction from (i0, j0) to (i, j).
[[nodiscard]] double terrain_strip_average(int i0, int j0, int i, int j, int nx, int ny,
                                           const ElevationCell& elevation);

// TRELIEF equivalent: relief(corner, i, j) for the four orientations (1 = N/S,
// 2 = NE/SW, 3 = E/W, 4 = SE/NW) plus the peak elevation (corner 5), returned as a
// flat array indexed corner * nx * ny + (j - 1) * nx + (i - 1), i.e. i fastest.
struct TerrainRelief {
    int nx = 0;
    int ny = 0;
    std::vector<double> values;   // 5 * nx * ny
    [[nodiscard]] double at(int corner, int i, int j) const {
        return values[static_cast<std::size_t>(corner - 1) * static_cast<std::size_t>(nx * ny) +
                      static_cast<std::size_t>(j - 1) * static_cast<std::size_t>(nx) +
                      static_cast<std::size_t>(i - 1)];
    }
};

[[nodiscard]] TerrainRelief terrain_relief(int nx, int ny, const ElevationCell& elevation);

// GETELEV equivalent: bilinear interpolation of the cell-centre elevations. The
// nested-grid scaling is explicit; a caller that needs a nested domain must
// supply the factors (the vendor obtains them from GETCELL).
struct InterpolatedElevationInputs {
    double x = 0.0;                 // met-grid units
    double y = 0.0;
    int nx = 0;                     // cells in this domain
    int ny = 0;
    double nest_factor = 1.0;       // NESTFAC(MD)
    double nest_offset_x = 0.0;     // RNXNEST0(MD)
    double nest_offset_y = 0.0;     // RNYNEST0(MD)
};

[[nodiscard]] double interpolated_elevation(const InterpolatedElevationInputs& inputs,
                                            const ElevationCell& elevation);

} // namespace cteas::puff
