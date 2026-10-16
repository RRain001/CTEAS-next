#include "cteas/puff/terrain_width.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = ValleyWidthReal;

constexpr R kZero = 0.0F;
constexpr R kOne = 1.0F;
constexpr int kNullWidth = -1;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7T VWIDTH: " + message);
}

R cell_elevation(const ElevationCell& elevation, int i, int j, int nx, int ny) {
    require_true(i >= 1 && i <= nx && j >= 1 && j <= ny,
                 "the elevation cell index is outside the domain");
    const double value = elevation(i, j);
    require_true(std::isfinite(value), "the elevation value must be finite");
    return static_cast<R>(value);
}

int rounded_hits(R span, R fraction) {
    // Fortran NINT rounds half away from zero.
    return static_cast<int>(std::lround(static_cast<double>(span * fraction))) + 1;
}

} // namespace

ValleyWidths valley_widths(const ValleyWidthInputs& inputs, const ElevationCell& elevation) {
    // VWIDTH (calpuff.for L21896-22178), REAL*4/INTEGER*4.
    require_true(static_cast<bool>(elevation), "the elevation accessor must be supplied");
    require_true(inputs.nx >= 1 && inputs.ny >= 1, "the domain must have at least one cell");
    require_true(inputs.max_levels >= 1, "MXVALZ must be at least 1");
    const R dzmin = static_cast<R>(inputs.min_layer_m);
    const R qahit = static_cast<R>(inputs.wall_fraction);
    const R big = static_cast<R>(inputs.big_m);
    require_true(dzmin > kZero, "DZMIN must be positive");
    require_true(qahit > kZero && qahit < kOne, "QAHIT must be strictly between 0 and 1");

    const int nx = inputs.nx;
    const int ny = inputs.ny;
    const int levels = inputs.max_levels;

    ValleyWidths result;
    result.nx = nx;
    result.ny = ny;
    result.max_levels = levels;
    result.width.assign(static_cast<std::size_t>(levels * nx * ny), kNullWidth);

    R zmax = -big;
    R zmin = big;
    for (int j = 1; j <= ny; ++j) {
        for (int i = 1; i <= nx; ++i) {
            const R value = cell_elevation(elevation, i, j, nx, ny);
            if (value > zmax) zmax = value;
            if (value < zmin) zmin = value;
        }
    }
    R dzval = std::max(dzmin, (zmax - zmin) / static_cast<R>(levels));

    const auto level_width = [&result, nx, ny](int level, int i, int j) -> int& {
        return result.width[static_cast<std::size_t>(level - 1) *
                                static_cast<std::size_t>(nx * ny) +
                            static_cast<std::size_t>(j - 1) * static_cast<std::size_t>(nx) +
                            static_cast<std::size_t>(i - 1)];
    };

    // The vendor's `goto 1` restart: when the valley disappears too soon the
    // height increment is recomputed and the whole scan starts over.
    bool restart = true;
    R delz = kZero;
    bool lwidth = false;   // persists across the k loop, as the vendor's does
    while (restart) {
        restart = false;
        dzval = std::max(dzmin, dzval);
        for (int k = 1; k <= levels; ++k) {
            if (k > 1 && !lwidth && dzval > dzmin) {
                // lwidth is false here (checked below), so re-resolve.
                dzval = delz / static_cast<R>(levels);
                for (int j0 = 1; j0 <= ny; ++j0) {
                    for (int i0 = 1; i0 <= nx; ++i0) {
                        for (int k0 = 1; k0 <= levels; ++k0) {
                            level_width(k0, i0, j0) = kNullWidth;
                        }
                    }
                }
                restart = true;
                break;
            }
            delz = static_cast<R>(k) * dzval;
            lwidth = false;

            for (int j = 1; j <= ny; ++j) {
                for (int i = 1; i <= nx; ++i) {
                    if (k > 1 && level_width(k - 1, i, j) == kNullWidth) continue;
                    const R ztarget = cell_elevation(elevation, i, j, nx, ny) + delz;

                    // North.
                    int look_ns = kNullWidth;
                    for (int jy = j + 1; jy <= ny && look_ns == kNullWidth; ++jy) {
                        const int jdel = jy - j;
                        const int ixmin = std::max(1, i - jdel);
                        const int ixmax = std::min(nx, i + jdel);
                        const int iqa = rounded_hits(static_cast<R>(ixmax - ixmin), qahit);
                        int ihit = 0;
                        for (int ix = ixmin; ix <= ixmax; ++ix) {
                            if (cell_elevation(elevation, ix, jy, nx, ny) >= ztarget) {
                                ++ihit;
                                if (ihit == iqa) {
                                    look_ns = jy;
                                    break;
                                }
                            }
                        }
                    }
                    // South, only when the north side found the far wall.
                    if (look_ns >= 0) {
                        bool found = false;
                        for (int jy = j - 1; jy >= 1 && !found; --jy) {
                            const int jdel = j - jy;
                            const int ixmin = std::max(1, i - jdel);
                            const int ixmax = std::min(nx, i + jdel);
                            const int iqa = rounded_hits(static_cast<R>(ixmax - ixmin), qahit);
                            int ihit = 0;
                            for (int ix = ixmin; ix <= ixmax; ++ix) {
                                if (cell_elevation(elevation, ix, jy, nx, ny) >= ztarget) {
                                    ++ihit;
                                    if (ihit == iqa) {
                                        look_ns = look_ns - jy;
                                        found = true;
                                        break;
                                    }
                                }
                            }
                        }
                        if (!found) look_ns = kNullWidth;
                    }

                    // East.
                    int look_ew = kNullWidth;
                    for (int ix = i + 1; ix <= nx && look_ew == kNullWidth; ++ix) {
                        const int idel = ix - i;
                        const int jymin = std::max(1, j - idel);
                        const int jymax = std::min(ny, j + idel);
                        const int iqa = rounded_hits(static_cast<R>(jymax - jymin), qahit);
                        int ihit = 0;
                        for (int jy = jymin; jy <= jymax; ++jy) {
                            if (cell_elevation(elevation, ix, jy, nx, ny) >= ztarget) {
                                ++ihit;
                                if (ihit == iqa) {
                                    look_ew = ix;
                                    break;
                                }
                            }
                        }
                    }
                    if (look_ew >= 0) {
                        bool found = false;
                        for (int ix = i - 1; ix >= 1 && !found; --ix) {
                            const int idel = i - ix;
                            const int jymin = std::max(1, j - idel);
                            const int jymax = std::min(ny, j + idel);
                            const int iqa = rounded_hits(static_cast<R>(jymax - jymin), qahit);
                            int ihit = 0;
                            for (int jy = jymin; jy <= jymax; ++jy) {
                                if (cell_elevation(elevation, ix, jy, nx, ny) >= ztarget) {
                                    ++ihit;
                                    if (ihit == iqa) {
                                        look_ew = look_ew - ix;
                                        found = true;
                                        break;
                                    }
                                }
                            }
                        }
                        if (!found) look_ew = kNullWidth;
                    }

                    const int itest = look_ns * look_ew;
                    const int width = itest < 0 ? std::max(look_ns, look_ew)
                                                : std::min(look_ns, look_ew);
                    level_width(k, i, j) = width;
                    if (width > 1) lwidth = true;
                    require_true(!(width != kNullWidth && width < 2),
                                 "the vendor halts on an invalid valley width (0 or 1)");
                }
            }
        }
    }
    result.layer_thickness_m = static_cast<double>(dzval);
    return result;
}

} // namespace cteas::puff
