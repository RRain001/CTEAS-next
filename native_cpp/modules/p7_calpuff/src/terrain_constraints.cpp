#include "cteas/puff/terrain_constraints.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = TerrainReal;

constexpr R kZero = 0.0F;
constexpr R kOne = 1.0F;
constexpr R kTwo = 2.0F;
constexpr R kHalf = 0.5F;
constexpr R kThird = 0.3333333F;
constexpr R kSmall = 1.0e-4F;
constexpr R kNSThreshold = 2.4142F;   // tan(67.5)
constexpr R kEWThreshold = 0.4142F;   // tan(22.5)
constexpr R kTrapRatio = 0.4F;        // WALLTRAP RCRIT

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7R terrain: " + message);
}

void require_finite(double value, const std::string& what) {
    require_true(std::isfinite(value), what + " must be finite");
}

R to_real(double value, const char* what) {
    require_finite(value, what);
    return static_cast<R>(value);
}

void require_lookup(const TerrainLookup& terrain) {
    require_true(static_cast<bool>(terrain.elevation_msl),
                 "the GETELEV terrain-elevation lookup must be supplied");
    require_true(static_cast<bool>(terrain.cell_elevation_msl),
                 "the /METHD/ cell-elevation lookup must be supplied");
    require_true(static_cast<bool>(terrain.relief),
                 "the /GRID/ relief lookup must be supplied");
    require_true(static_cast<bool>(terrain.valley_width),
                 "the /GRID/ valley-width lookup must be supplied");
}

} // namespace

TerrainStrain terrain_strain(const TerrainStrainInputs& inputs, const TerrainLookup& terrain) {
    // CTADJ2 (calpuff.for L20542-20835), REAL*4.
    require_lookup(terrain);
    R r = to_real(inputs.sigma_ratio, "sigma ratio");
    const R zpold = to_real(inputs.puff_height_start_m, "start-of-step puff height");
    const R xold = to_real(inputs.x_old, "old x");
    const R yold = to_real(inputs.y_old, "old y");
    const R xnew = to_real(inputs.x_new, "new x");
    const R ynew = to_real(inputs.y_new, "new y");
    const R szold = to_real(inputs.sigma_z_start_m, "start-of-step sigma-z");
    const R bvf = to_real(inputs.brunt_vaisala_s, "Brunt-Vaisala frequency");
    const R ws = to_real(inputs.wind_speed_ms, "wind speed");
    const R dgrid = to_real(inputs.grid_spacing_m, "grid spacing");
    require_true(ws > kZero, "the wind speed must be positive for the strain computation");

    // The vendor conditions the ratio to be at most one.
    r = std::min(kOne, r);

    const R xstep = (xnew - xold) * dgrid;
    const R ystep = (ynew - yold) * dgrid;
    const R delx = std::sqrt(xstep * xstep + ystep * ystep);
    const R elold = to_real(terrain.elevation_msl(static_cast<double>(xold),
                                                  static_cast<double>(yold)),
                            "terrain elevation at the old position");
    const R elnew = to_real(terrain.elevation_msl(static_cast<double>(xnew),
                                                  static_cast<double>(ynew)),
                            "terrain elevation at the new position");
    const R rise = elnew - elold;
    const R arise = std::abs(rise);

    TerrainStrain result;
    result.upslope = rise > kZero;

    const auto corner_relief = [&terrain](int corner, R x, R y) {
        return to_real(terrain.relief(static_cast<double>(x), static_cast<double>(y), corner),
                       "terrain relief");
    };
    R relief_along = kZero;
    if (std::abs(ystep) > kNSThreshold * std::abs(xstep)) {
        relief_along = std::max(corner_relief(1, xold, yold), corner_relief(1, xnew, ynew));
    } else {
        const R ybyx = ystep / xstep;
        if (ybyx > kEWThreshold) {
            relief_along = std::max(corner_relief(2, xold, yold), corner_relief(2, xnew, ynew));
        } else if (ybyx < -kEWThreshold) {
            relief_along = std::max(corner_relief(4, xold, yold), corner_relief(4, xnew, ynew));
        } else {
            relief_along = std::max(corner_relief(3, xold, yold), corner_relief(3, xnew, ynew));
        }
    }
    const R eltop = std::max(corner_relief(5, xold, yold), corner_relief(5, xnew, ynew));

    R strain = kOne;
    R zpnew = zpold;
    R fracz = kZero;
    if (delx <= kSmall || arise <= kSmall) {
        // Degenerate case of no step or no slope.
        strain = kOne;
        zpnew = zpold;
        fracz = kZero;
    } else {
        const R slope = rise / delx;
        const R aslope = std::abs(slope);
        if (bvf > kZero && result.upslope) {
            const R elds = eltop - ws / bvf;
            fracz = (elds - elold) / rise;
            if (fracz > kZero) {
                const R sznew = szold / r;
                R fraczs = (zpold - 1.8F * szold) / (rise + 1.8F * (sznew - szold));
                fraczs = std::max(kZero, fraczs);
                fracz = std::min(fraczs, fracz);
            }
            if (fracz <= kZero) {
                zpnew = zpold;
            } else if (fracz >= kOne) {
                zpnew = zpold - rise;
            } else {
                zpnew = zpold - rise * fracz;
            }
        } else {
            zpnew = zpold;
            fracz = kZero;
        }

        const R zp = kHalf * (zpold + zpnew);
        R etabyh = kZero;
        if (relief_along <= 0.1F * zp) {
            etabyh = 10.0F;
        } else {
            etabyh = std::max(0.1F, zp / relief_along);
        }
        R fri = bvf * relief_along / ws;
        fri = std::min(kOne, fri);
        const R etabyl = kTwo * etabyh * aslope;
        R expnl = kZero;
        R expnli = kZero;
        if (etabyl >= 0.1F) {
            expnl = std::exp(etabyl);
            expnli = kOne / expnl;
        } else {
            expnl = kOne + etabyl;
            expnli = kOne - etabyl;
        }
        const R strat = fri * etabyh;
        R sinln = kZero;
        R cosln = kZero;
        if (strat >= 0.1F) {
            sinln = std::sin(strat);
            cosln = std::cos(strat);
        } else {
            sinln = strat;
            cosln = kOne - kHalf * strat * strat;
        }
        const R trig = sinln / (cosln - expnl);

        R xbyl = kZero;
        if (slope > kZero) {
            xbyl = -std::sqrt(kThird * (kOne + kTwo * aslope * (kOne - expnli) / etabyl));
            if (std::abs(trig) >= 0.01F) {
                xbyl = xbyl + kHalf * (kOne - std::sqrt(kOne + trig * trig)) / trig;
            } else {
                xbyl = xbyl - kHalf * kHalf * trig;
            }
        } else {
            xbyl = std::sqrt(kThird * (kOne + kTwo * aslope * (kOne - expnli) / etabyl));
            if (std::abs(trig) >= 0.01F) {
                xbyl = xbyl + (kOne - std::sqrt(kOne + trig * trig)) / trig;
            } else {
                xbyl = xbyl - kHalf * trig;
            }
        }
        const R xbyl2 = xbyl * xbyl;
        const R tzi = kOne + (kTwo * aslope / (etabyl * (kOne + xbyl2))) *
                                (kOne - expnli * (cosln - xbyl * sinln));
        const R tz = kOne / tzi;
        const R tzsq = tz * tz;
        R dxbyl = kOne;
        if (arise < relief_along) dxbyl = arise / relief_along;
        // Original CTADJ2 calpuff.for L20800:
        // DTZ=-DXBYL*(TWO*ASLOPE*TZSQ/(ETABYL*(ONE+XBYL2)**2))*...
        // REAL*4 evaluates (ONE+XBYL2)**2 before multiplying ETABYL.
        // Left-associating ETABYL*TERM*TERM changes an intermediate ULP.
        const R hill_term=kOne+xbyl2;
        const R hill_squared=hill_term*hill_term;
        const R dtz = -dxbyl * (kTwo * aslope * tzsq / (etabyl * hill_squared)) *
                      (-kTwo * xbyl +
                       expnli * (kTwo * xbyl * cosln + (kOne - xbyl2) * sinln));
        const R sfcnsq = std::exp(kTwo * (kOne - tz));
        const R rsq = r * r;
        const R arg = kTwo * dtz;
        const R exparg = std::exp(-arg);
        if (std::abs(arg) > 0.05F) {
            strain = rsq + sfcnsq * (kOne - rsq) * (kOne - exparg) / arg;
        } else {
            strain = rsq + sfcnsq * (kOne - rsq);
        }
        strain = std::sqrt(strain);
    }

    result.strain = static_cast<double>(strain);
    result.puff_height_end_m = static_cast<double>(zpnew);
    result.fraction_beyond = static_cast<double>(fracz);
    return result;
}

WallTrap wall_trap(const WallTrapInputs& inputs, const TerrainLookup& terrain) {
    // WALLTRAP (calpuff.for L21745-21894), REAL*4.
    require_lookup(terrain);
    const R syb = to_real(inputs.sigma_y_begin_m, "start-of-step sigma-y");
    R sye = to_real(inputs.sigma_y_end_m, "end-of-step sigma-y");
    const R z = to_real(inputs.puff_height_m, "puff height");
    const R xb = to_real(inputs.x_begin, "begin x");
    const R yb = to_real(inputs.y_begin, "begin y");
    const R xe = to_real(inputs.x_end, "end x");
    const R ye = to_real(inputs.y_end, "end y");
    const R bvf = to_real(inputs.brunt_vaisala_s, "Brunt-Vaisala frequency");
    const R ws = to_real(inputs.wind_speed_ms, "wind speed");
    const R dzval = to_real(inputs.valley_layer_thickness_m, "valley layer thickness");
    const R xgridm = to_real(inputs.grid_spacing_m, "grid spacing");
    require_true(inputs.max_valley_levels >= 1, "MXVALZ must be at least 1");

    WallTrap result;
    result.trapped = false;
    if (bvf <= kZero) {
        result.sigma_y_end_m = static_cast<double>(sye);
        return result;
    }
    require_true(ws > kZero && dzval > kZero,
                 "the wind speed and the valley layer thickness must be positive");

    const R eltop = std::max(
        to_real(terrain.relief(static_cast<double>(xb), static_cast<double>(yb), 5),
                "peak relief at the begin position"),
        to_real(terrain.relief(static_cast<double>(xe), static_cast<double>(ye), 5),
                "peak relief at the end position"));
    const R elds = eltop - ws / bvf;
    const R elpuff = std::min(to_real(terrain.cell_elevation_msl(static_cast<double>(xb),
                                                                 static_cast<double>(yb)),
                                      "cell elevation at the begin position"),
                              to_real(terrain.cell_elevation_msl(static_cast<double>(xe),
                                                                 static_cast<double>(ye)),
                                      "cell elevation at the end position")) +
                     z;
    if (elpuff > elds) {
        result.sigma_y_end_m = static_cast<double>(sye);
        return result;
    }

    const R zgrid = z / dzval;
    int izbot = static_cast<int>(zgrid);
    R dzfac = kZero;
    if (izbot == 0) {
        izbot = 1;
        dzfac = kZero;
    } else {
        dzfac = zgrid - static_cast<R>(izbot);
    }
    const int iztop = izbot + 1;
    if (izbot >= inputs.max_valley_levels) {
        result.sigma_y_end_m = static_cast<double>(sye);
        return result;
    }
    const auto width = [&terrain](int level, R x, R y) {
        return terrain.valley_width(static_cast<double>(x), static_cast<double>(y), level);
    };
    if (width(iztop, xb, yb) == -1 || width(iztop, xe, ye) == -1 || width(izbot, xb, yb) == -1 ||
        width(izbot, xe, ye) == -1) {
        result.sigma_y_end_m = static_cast<double>(sye);
        return result;
    }
    const R wb = xgridm * ((kOne - dzfac) * static_cast<R>(width(izbot, xb, yb)) +
                           dzfac * static_cast<R>(width(iztop, xb, yb)));
    const R we = xgridm * ((kOne - dzfac) * static_cast<R>(width(izbot, xe, ye)) +
                           dzfac * static_cast<R>(width(iztop, xe, ye)));

    const R rb = syb / wb;
    const R re = sye / we;
    if (std::max(rb, re) <= kTrapRatio) {
        result.sigma_y_end_m = static_cast<double>(sye);
        return result;
    }
    if (std::min(rb, re) >= kTrapRatio) {
        result.trapped = true;
        sye = syb;
    } else {
        const R frac = std::max(kZero, (syb - kTrapRatio * wb) /
                                           ((we - wb) * kTrapRatio - (sye - syb)));
        result.trapped = true;
        R f = kZero;
        if (re >= kTrapRatio) {
            f = frac;
        } else if (rb >= kTrapRatio) {
            f = kOne - frac;
        }
        sye = syb + f * (sye - syb);
    }
    result.sigma_y_end_m = static_cast<double>(sye);
    return result;
}

} // namespace cteas::puff
