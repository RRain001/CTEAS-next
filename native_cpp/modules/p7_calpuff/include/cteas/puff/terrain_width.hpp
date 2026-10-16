#pragma once

#include <functional>
#include <vector>

namespace cteas::puff {

// P7T: VWIDTH of CALPUFF 7.2.1 (calpuff.for L21896-22178), the producer of the
// /GRID/ valley-width table `ivalw(mxvalz,...)` and `dzval` that WALLTRAP
// consumes. It scans the CALMET elevation grid, so the port takes the grid as a
// 1-based accessor and the vendor parameters (MXVALZ, DZMIN, QAHIT) as explicit
// inputs; a missing accessor fails closed. The vendor's fatal "invalid valley
// width" check is reproduced as a refusal.

using ValleyWidthReal = float;

using ElevationCell = std::function<double(int i, int j)>;

struct ValleyWidthInputs {
    int nx = 0;                     // NXM(MD)
    int ny = 0;                     // NYM(MD)
    int max_levels = 10;            // MXVALZ (vendor parameter)
    double min_layer_m = 10.0;      // DZMIN
    double wall_fraction = 0.5;     // QAHIT
    double big_m = 9000.0;          // BIG (the elevation scan sentinel)
};

struct ValleyWidths {
    int nx = 0;
    int ny = 0;
    int max_levels = 0;
    double layer_thickness_m = 0.0;   // DZVAL
    std::vector<int> width;           // max_levels * nx * ny, i fastest
    [[nodiscard]] int at(int level, int i, int j) const {
        return width[static_cast<std::size_t>(level - 1) *
                         static_cast<std::size_t>(nx * ny) +
                     static_cast<std::size_t>(j - 1) * static_cast<std::size_t>(nx) +
                     static_cast<std::size_t>(i - 1)];
    }
};

[[nodiscard]] ValleyWidths valley_widths(const ValleyWidthInputs& inputs,
                                         const ElevationCell& elevation);

} // namespace cteas::puff
