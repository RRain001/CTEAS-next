#include "cteas/puff/terrain_relief.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = TerrainStateReal;

constexpr R kZero = 0.0F;
constexpr R kOne = 1.0F;
constexpr R kHalf = 0.5F;
constexpr R kTan225 = 0.4142136F;   // TERAVG data tan225
constexpr R kBeta = 1.0F;           // TRELIEF data beta

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7S terrain: " + message);
}

R cell_elevation(const ElevationCell& elevation, int i, int j, int nx, int ny) {
    require_true(i >= 1 && i <= nx && j >= 1 && j <= ny,
                 "the elevation cell index is outside the domain");
    const double value = elevation(i, j);
    require_true(std::isfinite(value), "the elevation value must be finite");
    return static_cast<R>(value);
}

} // namespace

double terrain_strip_average(int i0, int j0, int i, int j, int nx, int ny,
                             const ElevationCell& elevation) {
    // TERAVG (calpuff.for L21547-21743), REAL*4.
    require_true(static_cast<bool>(elevation), "the elevation accessor must be supplied");
    require_true(nx >= 1 && ny >= 1, "the domain must have at least one cell");
    require_true(i >= 1 && i <= nx && j >= 1 && j <= ny, "the sector centre is outside the domain");
    require_true(i0 >= 1 && i0 <= nx && j0 >= 1 && j0 <= ny,
                 "the sector origin is outside the domain");

    if (i0 == i) {
        // N/S sector: an E/W strip of cells.
        const int jdel = std::abs(j - j0);
        const int idel = static_cast<int>(static_cast<R>(jdel) * kTan225);
        const int ixmin = std::max(1, i - idel);
        const int ixmax = std::min(nx, i + idel);
        int nsum = 0;
        R tsum = kZero;
        for (int ix = ixmin; ix <= ixmax; ++ix) {
            nsum += 1;
            tsum += cell_elevation(elevation, ix, j, nx, ny);
        }
        return static_cast<double>(tsum / static_cast<R>(nsum));
    }
    if (j0 == j) {
        // E/W sector: a N/S strip of cells.
        const int idel = std::abs(i - i0);
        const int jdel = static_cast<int>(static_cast<R>(idel) * kTan225);
        const int jymin = std::max(1, j - jdel);
        const int jymax = std::min(ny, j + jdel);
        int nsum = 0;
        R tsum = kZero;
        for (int jy = jymin; jy <= jymax; ++jy) {
            nsum += 1;
            tsum += cell_elevation(elevation, i, jy, nx, ny);
        }
        return static_cast<double>(tsum / static_cast<R>(nsum));
    }
    if ((j - j0) == (i - i0)) {
        // NE/SW sector: a NW/SE strip, then the half-step cells.
        int kdiag = std::abs(i - i0);
        kdiag = static_cast<int>(static_cast<R>(kdiag) * kTan225);
        const int jymin = std::max(1, j - kdiag);
        const int jymax = std::min(ny, j + kdiag);
        const int ixmin = std::max(1, i - kdiag);
        const int ixmax = std::min(nx, i + kdiag);
        const int kleft = -std::min(i - ixmin, jymax - j);
        const int krght = std::min(ixmax - i, j - jymin);
        R nsum = kZero;
        R tsum = kZero;
        for (int k = kleft; k <= krght; ++k) {
            nsum += kOne;
            tsum += cell_elevation(elevation, i + k, j - k, nx, ny);
        }
        const int nx2 = 2 * nx;
        const int ny2 = 2 * ny;
        const int i02 = 2 * i0;
        int i2 = 2 * i + 1;
        int j2 = 2 * j + 1;
        if (i < i0) i2 -= 2;
        if (j < j0) j2 -= 2;
        kdiag = static_cast<int>(static_cast<R>(std::abs(i2 - i02)) * kTan225);
        const int jymin2 = std::max(2, j2 - kdiag);
        const int jymax2 = std::min(ny2, j2 + kdiag);
        const int ixmin2 = std::max(2, i2 - kdiag);
        const int ixmax2 = std::min(nx2, i2 + kdiag);
        const int kleft2 = -std::min(i2 - ixmin2, jymax2 - j2);
        const int krght2 = std::min(ixmax2 - i2, j2 - jymin2);
        for (int k = kleft2; k <= krght2; ++k) {
            int ii = i2 + k;
            int jj = j2 - k;
            if ((ii % 2) == 0 && (jj % 2) == 0) {
                ii /= 2;
                jj /= 2;
                nsum += kOne;
                tsum += cell_elevation(elevation, ii, jj, nx, ny);
            }
        }
        return static_cast<double>(tsum / nsum);
    }
    if ((j - j0) == -(i - i0)) {
        // NW/SE sector: a SW/NE strip, then the half-step cells.
        int kdiag = std::abs(i - i0);
        kdiag = static_cast<int>(static_cast<R>(kdiag) * kTan225);
        const int jymin = std::max(1, j - kdiag);
        const int jymax = std::min(ny, j + kdiag);
        const int ixmin = std::max(1, i - kdiag);
        const int ixmax = std::min(nx, i + kdiag);
        const int kleft = -std::min(i - ixmin, j - jymin);
        const int krght = std::min(ixmax - i, jymax - j);
        R nsum = kZero;
        R tsum = kZero;
        for (int k = kleft; k <= krght; ++k) {
            nsum += kOne;
            tsum += cell_elevation(elevation, i + k, j + k, nx, ny);
        }
        const int nx2 = 2 * nx;
        const int ny2 = 2 * ny;
        const int i02 = 2 * i0;
        int i2 = 2 * i + 1;
        int j2 = 2 * j + 1;
        if (i < i0) i2 -= 2;
        if (j < j0) j2 -= 2;
        kdiag = static_cast<int>(static_cast<R>(std::abs(i2 - i02)) * kTan225);
        const int jymin2 = std::max(2, j2 - kdiag);
        const int jymax2 = std::min(ny2, j2 + kdiag);
        const int ixmin2 = std::max(2, i2 - kdiag);
        const int ixmax2 = std::min(nx2, i2 + kdiag);
        const int kleft2 = -std::min(i2 - ixmin2, j2 - jymin2);
        const int krght2 = std::min(ixmax2 - i2, jymax2 - j2);
        for (int k = kleft2; k <= krght2; ++k) {
            int ii = i2 + k;
            int jj = j2 + k;
            if ((ii % 2) == 0 && (jj % 2) == 0) {
                ii /= 2;
                jj /= 2;
                nsum += kOne;
                tsum += cell_elevation(elevation, ii, jj, nx, ny);
            }
        }
        return static_cast<double>(tsum / nsum);
    }
    // The vendor's TERAVG is only defined for the four sector orientations; a
    // point outside them leaves ELAVG untouched, which this port refuses.
    throw std::invalid_argument(
        "P7S TERAVG: the sector direction is not one of the four orientations");
}

TerrainRelief terrain_relief(int nx, int ny, const ElevationCell& elevation) {
    // TRELIEF (calpuff.for L21205-21545), REAL*4.
    require_true(static_cast<bool>(elevation), "the elevation accessor must be supplied");
    require_true(nx >= 1 && ny >= 1, "the domain must have at least one cell");
    TerrainRelief result;
    result.nx = nx;
    result.ny = ny;
    result.values.assign(static_cast<std::size_t>(5 * nx * ny), 0.0);

    for (int j = 1; j <= ny; ++j) {
        for (int i = 1; i <= nx; ++i) {
            R rise = kZero;

            // 1: N/S. The accumulating walks are written once per orientation
            // exactly as the vendor does, with the slope-ratio break (BETA).
            const auto walk = [&](int step_i, int step_j, bool negative) {
                // Returns (reliefi, reliefd) for one orientation.
                R reliefi = kZero;
                const int i_next = i + step_i;
                const int j_next = j + step_j;
                if (i_next >= 1 && i_next <= nx && j_next >= 1 && j_next <= ny) {
                    R delh1 = cell_elevation(elevation, i_next, j_next, nx, ny) -
                              cell_elevation(elevation, i, j, nx, ny);
                    if (negative) delh1 = -delh1;
                    reliefi = delh1;
                    if (std::abs(delh1) > kZero) {
                        R elavg = cell_elevation(elevation, i_next, j_next, nx, ny);
                        for (int k = 1;; ++k) {
                            const int ii = i_next + step_i * k;
                            const int jj = j_next + step_j * k;
                            if (ii < 1 || ii > nx || jj < 1 || jj > ny) break;
                            const R elavg0 = elavg;
                            elavg = static_cast<R>(
                                terrain_strip_average(i, j, ii, jj, nx, ny, elevation));
                            R delh = elavg - elavg0;
                            if (negative) delh = -delh;
                            const R rr = std::abs(delh / delh1 - kOne);
                            if (rr <= kBeta) {
                                reliefi += delh;
                            } else {
                                break;
                            }
                        }
                    }
                }
                return reliefi;
            };

            // Orientation 1: increasing/decreasing j.
            R reliefi = walk(0, 1, false);
            R reliefd = walk(0, -1, true);
            R rplus = std::abs(reliefi + reliefd);
            R rminus = std::abs(reliefi - reliefd);
            result.values[static_cast<std::size_t>(0) * static_cast<std::size_t>(nx * ny) +
                          static_cast<std::size_t>(j - 1) * static_cast<std::size_t>(nx) +
                          static_cast<std::size_t>(i - 1)] =
                static_cast<double>(rplus > rminus ? rplus
                                                   : std::max(std::abs(reliefi), std::abs(reliefd)));
            rise = std::max(rise, reliefi);
            rise = std::max(rise, -reliefd);

            // Orientation 2: NE/SW (increasing/decreasing i and j together).
            reliefi = walk(1, 1, false);
            reliefd = walk(-1, -1, true);
            rplus = std::abs(reliefi + reliefd);
            rminus = std::abs(reliefi - reliefd);
            result.values[static_cast<std::size_t>(1) * static_cast<std::size_t>(nx * ny) +
                          static_cast<std::size_t>(j - 1) * static_cast<std::size_t>(nx) +
                          static_cast<std::size_t>(i - 1)] =
                static_cast<double>(rplus > rminus ? rplus
                                                   : std::max(std::abs(reliefi), std::abs(reliefd)));
            rise = std::max(rise, reliefi);
            rise = std::max(rise, -reliefd);

            // Orientation 3: E/W (increasing/decreasing i).
            reliefi = walk(1, 0, false);
            reliefd = walk(-1, 0, true);
            rplus = std::abs(reliefi + reliefd);
            rminus = std::abs(reliefi - reliefd);
            result.values[static_cast<std::size_t>(2) * static_cast<std::size_t>(nx * ny) +
                          static_cast<std::size_t>(j - 1) * static_cast<std::size_t>(nx) +
                          static_cast<std::size_t>(i - 1)] =
                static_cast<double>(rplus > rminus ? rplus
                                                   : std::max(std::abs(reliefi), std::abs(reliefd)));
            rise = std::max(rise, reliefi);
            rise = std::max(rise, -reliefd);

            // Orientation 4: SE/NW (increasing i, decreasing j).
            reliefi = walk(1, -1, false);
            reliefd = walk(-1, 1, true);
            rplus = std::abs(reliefi + reliefd);
            rminus = std::abs(reliefi - reliefd);
            result.values[static_cast<std::size_t>(3) * static_cast<std::size_t>(nx * ny) +
                          static_cast<std::size_t>(j - 1) * static_cast<std::size_t>(nx) +
                          static_cast<std::size_t>(i - 1)] =
                static_cast<double>(rplus > rminus ? rplus
                                                   : std::max(std::abs(reliefi), std::abs(reliefd)));
            rise = std::max(rise, reliefi);
            rise = std::max(rise, -reliefd);

            result.values[static_cast<std::size_t>(4) * static_cast<std::size_t>(nx * ny) +
                          static_cast<std::size_t>(j - 1) * static_cast<std::size_t>(nx) +
                          static_cast<std::size_t>(i - 1)] =
                static_cast<double>(cell_elevation(elevation, i, j, nx, ny) + rise);
        }
    }
    return result;
}

double interpolated_elevation(const InterpolatedElevationInputs& inputs,
                              const ElevationCell& elevation) {
    // GETELEV (calpuff.for L21098-21203), REAL*4.
    require_true(static_cast<bool>(elevation), "the elevation accessor must be supplied");
    require_true(inputs.nx >= 1 && inputs.ny >= 1, "the domain must have at least one cell");
    require_true(std::isfinite(inputs.x) && std::isfinite(inputs.y),
                 "the interpolation point must be finite");
    require_true(inputs.nest_factor > 0.0, "the nested-grid factor must be positive");
    const R x = static_cast<R>(inputs.x);
    const R y = static_cast<R>(inputs.y);
    const R nest_factor = static_cast<R>(inputs.nest_factor);
    const R xmd = x * nest_factor - static_cast<R>(inputs.nest_offset_x);
    const R ymd = y * nest_factor - static_cast<R>(inputs.nest_offset_y);

    if (inputs.nx == 1 && inputs.ny == 1) return static_cast<double>(cell_elevation(elevation, 1, 1, 1, 1));

    int ixll = 1;
    int ixllp1 = 1;
    if (inputs.nx != 1) {
        ixll = static_cast<int>(xmd + kHalf);
        ixll = std::max(ixll, 1);
        ixll = std::min(ixll, inputs.nx - 1);
        ixllp1 = ixll + 1;
    }
    int iyll = 1;
    int iyllp1 = 1;
    if (inputs.ny != 1) {
        iyll = static_cast<int>(ymd + kHalf);
        iyll = std::max(iyll, 1);
        iyll = std::min(iyll, inputs.ny - 1);
        iyllp1 = iyll + 1;
    }
    const R t = xmd - (static_cast<R>(ixll) - kHalf);
    const R onemt = kOne - t;
    const R u = ymd - (static_cast<R>(iyll) - kHalf);
    const R onemu = kOne - u;
    const R value =
        onemt * onemu * cell_elevation(elevation, ixll, iyll, inputs.nx, inputs.ny) +
        t * onemu * cell_elevation(elevation, ixllp1, iyll, inputs.nx, inputs.ny) +
        t * u * cell_elevation(elevation, ixllp1, iyllp1, inputs.nx, inputs.ny) +
        u * onemt * cell_elevation(elevation, ixll, iyllp1, inputs.nx, inputs.ny);
    return static_cast<double>(value);
}

} // namespace cteas::puff
