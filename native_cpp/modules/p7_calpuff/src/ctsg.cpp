#include "cteas/puff/ctsg.hpp"

#include "cteas/puff/receptors.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = float;   // the vendor QATR/TFAC state is REAL*4

constexpr R kHalf = 0.5F;
constexpr R kOne = 1.0F;
constexpr int kJjLimit = 16000;   // QATR integer*2 guard

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7I CTSG support: " + message);
}

void require_finite(double value, const std::string& what) {
    require_true(std::isfinite(value), what + " must be finite");
}

} // namespace

QuadratureResult integrate_romberg(double lower, double upper, double eps, int dimension,
                                   const std::function<double(double)>& integrand) {
    require_finite(lower, "lower limit");
    require_finite(upper, "upper limit");
    require_finite(eps, "fractional tolerance");
    require_true(eps > 0.0, "fractional tolerance must be positive");
    require_true(dimension >= 1, "dimension must be at least 1");
    require_true(static_cast<bool>(integrand), "integrand must be provided");

    // QATR (calpuff.for L25406-25520), REAL*4 with a Romberg extrapolation table.
    // The vendor arguments are REAL*4, so the limits are rounded to single
    // precision before they reach the integrand (this is observable for
    // integrands like sin() near pi and is required for exact parity).
    const R lower_r = static_cast<R>(lower);
    const R upper_r = static_cast<R>(upper);
    std::vector<R> aux(static_cast<std::size_t>(dimension), 0.0F);
    QuadratureResult result;
    aux[0] = kHalf * static_cast<R>(integrand(static_cast<double>(lower_r)) +
                                   integrand(static_cast<double>(upper_r)));
    const R width = upper_r - lower_r;
    R value = width * aux[0];
    if (dimension <= 1) {
        result.value = value;
        result.status = QuadratureStatus::no_convergence;
        return result;
    }
    if (width == 0.0F) {
        result.value = value;
        result.status = QuadratureStatus::converged;
        return result;
    }

    R hh = width;
    R delt2 = 0.0F;
    R p = 1.0F;
    int jj = 1;
    bool stopped = false;
    for (int i = 2; i <= dimension; ++i) {
        value = aux[0];
        const R delt1 = delt2;
        const R hd = hh;
        hh = kHalf * hh;
        p = kHalf * p;
        R x = lower_r + hh;
        R sum = 0.0F;
        if (stopped) {
            throw std::invalid_argument(
                "P7I CTSG support: QATR interval count exceeded 32000 (vendor halts)");
        }
        if (jj > kJjLimit) stopped = true;
        for (int j = 1; j <= jj; ++j) {
            sum += static_cast<R>(integrand(static_cast<double>(x)));
            x += hd;
        }
        aux[static_cast<std::size_t>(i - 1)] = kHalf * aux[static_cast<std::size_t>(i - 2)] + p * sum;

        // Romberg extrapolation.
        R q = 1.0F;
        for (int j = 1; j <= i - 1; ++j) {
            const int index = i - j;
            q = q + q;
            q = q + q;
            aux[static_cast<std::size_t>(index - 1)] =
                aux[static_cast<std::size_t>(index)] +
                (aux[static_cast<std::size_t>(index)] - aux[static_cast<std::size_t>(index - 1)]) /
                    (q - 1.0F);
        }

        delt2 = std::abs(value - aux[0]);
        if (i >= 5) {
            if (value == 0.0F) {
                result.value = static_cast<double>(value);
                result.status = QuadratureStatus::converged;
                return result;
            }
            if ((delt2 / value) <= static_cast<R>(eps)) {
                result.value = static_cast<double>(width * aux[0]);
                result.status = QuadratureStatus::converged;
                return result;
            }
            if (delt2 >= delt1) {
                result.value = static_cast<double>(width * value);
                result.status = QuadratureStatus::diverging;
                return result;
            }
        }
        jj = jj + jj;
    }
    result.value = static_cast<double>(width * aux[0]);
    result.status = QuadratureStatus::no_convergence;
    return result;
}

RotatedPoint rotate_xy(double x, double y, double angle_rad) {
    require_finite(x, "x");
    require_finite(y, "y");
    require_finite(angle_rad, "rotation angle");
    // ROTATE (calpuff.for L25522-25549), REAL*4.
    const R angle = static_cast<R>(angle_rad);
    const R sine = std::sin(angle);
    const R cosine = std::cos(angle);
    RotatedPoint result;
    result.x = static_cast<double>(static_cast<R>(x) * cosine + static_cast<R>(y) * sine);
    result.y = static_cast<double>(-static_cast<R>(x) * sine + static_cast<R>(y) * cosine);
    return result;
}

TerrainFactors terrain_factors(double x_m, double begin_m, double end_m, double spacing_m,
                               const std::vector<double>& top_factors,
                               const std::vector<double>& lateral_factors) {
    require_finite(x_m, "position");
    require_finite(begin_m, "begin position");
    require_finite(end_m, "end position");
    require_finite(spacing_m, "spacing");
    require_true(spacing_m > 0.0, "spacing must be positive");
    require_true(end_m > begin_m, "end position must exceed the begin position");
    require_true(!top_factors.empty() && top_factors.size() == lateral_factors.size(),
                 "terrain factor arrays must be non-empty and of equal length");

    // TFAC (calpuff.for L25765-25813), REAL*4.
    TerrainFactors factors;
    const R x = static_cast<R>(x_m);
    const R begin = static_cast<R>(begin_m);
    const R end = static_cast<R>(end_m);
    const R spacing = static_cast<R>(spacing_m);
    if (!(x > begin && x < end)) return factors;
    const int previous = static_cast<int>((x - begin) / spacing);
    const int position = previous + 1;
    const int next = position + 1;
    require_true(position >= 1 && static_cast<std::size_t>(next) <= top_factors.size(),
                 "terrain factor arrays are too short for this position");
    const R grid_x = begin + spacing * static_cast<R>(previous);
    const R fraction = (x - grid_x) / spacing;
    const auto index = [](int one_based) { return static_cast<std::size_t>(one_based - 1); };
    const R top = fraction * static_cast<R>(top_factors[index(next)] -
                                            top_factors[index(position)]) +
                  static_cast<R>(top_factors[index(position)]);
    const R lateral = fraction * static_cast<R>(lateral_factors[index(next)] -
                                               lateral_factors[index(position)]) +
                      static_cast<R>(lateral_factors[index(position)]);
    require_true(top != 0.0 && lateral != 0.0, "terrain factors must not be zero");
    factors.top = static_cast<double>(top);
    factors.lateral = static_cast<double>(lateral);
    factors.total = static_cast<double>(kOne / (top * lateral));
    return factors;
}

// ---------------------------------------------------------------------------
// P7M: CTSG kernel (calpuff.for MUNU/IREG/BI/BJI/BJIL/SIGMA/CTREC/PUFFC/LOWER/CTSG)
// ---------------------------------------------------------------------------
namespace {

// Vendor /CONST/ values as CTINIT sets them (calpuff.for L22412-22434).
constexpr R kZero = 0.0F;
constexpr R kTwo = 2.0F;
constexpr R kThree = 3.0F;
constexpr R kFour = 4.0F;
constexpr R kSmall = 1.0e-6F;
constexpr R kExpMax = 69.0F;
constexpr R kEpsRefl = 0.01F;
constexpr int kMaxReflections = 50;                    // MXREFL
constexpr R kRt2pi = 0.0F;                             // never initialized by CTINIT
constexpr R kRt2 = 1.4142135F;                         // SQRT(2.0) in REAL*4
constexpr R kPi = 3.1415927F;
constexpr R kPiBy2 = kHalf * kPi;

R to_real(double value, const char* what) {
    require_finite(value, what);
    return static_cast<R>(value);
}

template <typename Curve>
bool curve_available(const Curve& curve) {
    return static_cast<bool>(curve);
}

R sign_of(R magnitude, R reference) { return reference >= kZero ? magnitude : -magnitude; }

} // namespace

EllipticCoordinates elliptic_coordinates(int mu_flag, double x_scaled, double y_scaled,
                                         double axis_ratio) {
    require_true(mu_flag == 0 || mu_flag == 1, "muflag must be 0 or 1");
    // MUNU (calpuff.for L24865-24967), REAL*4.
    R xbi = to_real(x_scaled, "scaled x");
    R ybi = to_real(y_scaled, "scaled y");
    const R r = to_real(axis_ratio, "axis ratio");
    require_true(r >= 0.0F, "axis ratio must not be negative");

    R absx = std::abs(xbi);
    R absy = std::abs(ybi);
    // The squares are taken BEFORE the near-axis snap, exactly as the vendor does.
    const R xsq = xbi * xbi;
    const R ysq = ybi * ybi;
    if (absx < kSmall) {
        xbi = kZero;
        absx = kZero;
    }
    if (absy < kSmall) {
        ybi = kZero;
        absy = kZero;
    }
    const R rsq = r * r;
    R rp1 = r + kOne;
    R rsqm1 = rsq - kOne;
    if (rsqm1 < kSmall) {
        rsqm1 = kZero;
        rp1 = kTwo;
    }
    const R rdsq = xsq + ysq;

    R nu = kZero;
    if (xbi == kZero) {
        nu = kPiBy2;
        if (ybi < kZero) nu = kThree * kPiBy2;
    } else if (ybi == kZero) {
        nu = kZero;
        if (xbi < kZero) nu = kPi;
    } else if (rsqm1 == kZero) {
        nu = std::atan2(ybi, xbi);
    } else {
        const R capb = rdsq / rsqm1 - kOne;
        const R ac = -ybi * ybi / rsqm1;
        const R snusq = (-capb + std::sqrt(capb * capb - kFour * ac)) / kTwo;
        if (snusq < kSmall) {
            nu = kZero;
        } else {
            R arg = std::sqrt(snusq);
            if ((kOne - arg) < kZero) arg = kOne;
            nu = std::asin(arg);
            if (xbi < kZero) nu = kPi - nu;
            if (ybi < kZero) nu = -nu;
        }
    }
    const R cosnu = std::cos(nu);
    const R sinnu = std::sin(nu);

    R mu = kZero;
    if (mu_flag != 1) {
        if (ybi == kZero && xbi == kZero) {
            mu = kZero;
        } else if (std::abs(sinnu) <= kSmall) {
            mu = std::log((absx + std::sqrt(xsq - rsqm1)) / rp1);
        } else if (std::abs(cosnu) <= kSmall) {
            mu = std::log((absy + std::sqrt(ysq + rsqm1)) / rp1);
        } else {
            mu = std::log((xbi / cosnu + ybi / sinnu) / rp1);
        }
    }
    EllipticCoordinates result;
    result.mu = static_cast<double>(mu);
    result.nu = static_cast<double>(nu);
    return result;
}

int region_index(double x, double x12, double x23) {
    // IREG (calpuff.for L24576-24597), REAL*4 comparisons.
    const R position = to_real(x, "position");
    const R upwind = to_real(x12, "upwind boundary");
    const R downwind = to_real(x23, "downwind boundary");
    if (position < upwind) return 1;
    if (position > downwind) return 3;
    return 2;
}

double reflection_b(double afac, double argm, double argp) {
    // BI (calpuff.for L22229-22263), REAL*4.
    const R factor = to_real(afac, "afac");
    const R minus = to_real(argm, "argm");
    const R plus = to_real(argp, "argp");
    const R exarg1 = factor * minus * minus;
    const R exarg2 = factor * plus * plus;
    R term1 = kZero;
    R term2 = kZero;
    if (exarg1 < kExpMax) term1 = std::exp(-exarg1);
    if (exarg2 < kExpMax) term2 = std::exp(-exarg2);
    return static_cast<double>(kTwo * (term1 + term2));
}

double reflection_bji(double ak, double dm, double dp, double d0, double eoimh, double eoiph,
                      double ej, double szesq, double szosq) {
    // BJI (calpuff.for L22265-22316), REAL*4.
    const R k = to_real(ak, "ak");
    const R dmr = to_real(dm, "dm");
    const R dpr = to_real(dp, "dp");
    const R d0r = to_real(d0, "d0");
    const R eoimhr = to_real(eoimh, "eoimh");
    const R eoiphr = to_real(eoiph, "eoiph");
    const R ejr = to_real(ej, "ej");
    const R szesqr = to_real(szesq, "szesq");
    const R szosqr = to_real(szosq, "szosq");
    require_true(szesqr > kZero, "szesq must be positive");

    const R dum = kHalf / szesqr;
    const R akd1 = k * (dmr + szosqr * ejr);
    const R akd2 = k * (dmr - szosqr * ejr);
    const R akd3 = k * (dpr - szosqr * ejr);
    const R akd4 = k * (dpr + szosqr * ejr);

    const R exarg1 = dum * (ejr - eoimhr) * (ejr - eoimhr);
    const R exarg2 = dum * (ejr + eoimhr) * (ejr + eoimhr);
    const R exarg3 = dum * (ejr + eoiphr) * (ejr + eoiphr);
    const R exarg4 = dum * (ejr - eoiphr) * (ejr - eoiphr);

    R term1 = kZero;
    R term2 = kZero;
    R term3 = kZero;
    R term4 = kZero;
    if (exarg1 < kExpMax) term1 = std::exp(-exarg1) * (std::erf(d0r - akd1) + std::erf(akd1));
    if (exarg2 < kExpMax) term2 = std::exp(-exarg2) * (std::erf(d0r - akd2) + std::erf(akd2));
    if (exarg3 < kExpMax) term3 = std::exp(-exarg3) * (std::erf(d0r + akd3) - std::erf(akd3));
    if (exarg4 < kExpMax) term4 = std::exp(-exarg4) * (std::erf(d0r + akd4) - std::erf(akd4));
    return static_cast<double>(term1 + term2 + term3 + term4);
}

double reflection_bjil(double ak, double b1, double ej, double eoi, double szsq, double szosq,
                       double szpsq) {
    // BJIL (calpuff.for L22318-22363), REAL*4.
    const R k = to_real(ak, "ak");
    const R b1r = to_real(b1, "b1");
    const R ejr = to_real(ej, "ej");
    const R eoir = to_real(eoi, "eoi");
    const R szsqr = to_real(szsq, "szsq");
    const R szosqr = to_real(szosq, "szosq");
    const R szpsqr = to_real(szpsq, "szpsq");
    require_true(szsqr > kZero, "szsq must be positive");

    const R dum = kHalf / szsqr;
    const R b2 = ejr * szosqr;
    const R b3 = eoir * szpsqr;

    const R exarg1 = dum * (ejr - eoir) * (ejr - eoir);
    const R exarg2 = dum * (ejr + eoir) * (ejr + eoir);

    const R arg1p = k * (b1r + b2 + b3);
    const R arg1m = k * (b1r - b2 - b3);
    const R arg2p = k * (b1r + b2 - b3);
    const R arg2m = k * (b1r - b2 + b3);

    R term1 = kZero;
    R term2 = kZero;
    if (exarg1 < kExpMax) term1 = std::exp(-exarg1) * (std::erf(arg1p) + std::erf(arg1m));
    if (exarg2 < kExpMax) term2 = std::exp(-exarg2) * (std::erf(arg2p) + std::erf(arg2m));
    return static_cast<double>(term1 + term2);
}

double sigma_restart(int itype, double puff_height_m, double speed_ms, double t_s,
                     double sigma_start_m, double start_age_s, double sigma_end_m, double step_s,
                     double sigma_receptor_m, double fraction, const SigmaYCurve& sigma_y_curve,
                     const SigmaZCurve& sigma_z_curve) {
    // SIGMA (calpuff.for L25551-25645), REAL*4.
    require_true(itype == 1 || itype == 2, "itype must be 1 (sigma-y) or 2 (sigma-z)");
    require_true(curve_available(sigma_y_curve) && curve_available(sigma_z_curve),
                 "both sigma curves must be supplied");
    const R s1 = to_real(sigma_start_m, "sigma at the start of the step");
    const R s2 = to_real(sigma_end_m, "sigma at the end of the step");
    const R t = to_real(t_s, "puff age");
    const R tstart = to_real(start_age_s, "age at the start of the step");
    const R tstep = to_real(step_s, "step duration");
    const R frac = to_real(fraction, "fraction of the step");
    const R zpuff = to_real(puff_height_m, "puff height");
    const R speed = to_real(speed_ms, "advection speed");

    // The vendor returns the start-of-step sigma without any curve evaluation
    // when the sigma does not grow over the step.
    if (s1 == s2) return static_cast<double>(s1);

    R ages[3];
    R sigmas[3];
    ages[0] = tstart + frac * tstep;
    sigmas[0] = to_real(sigma_receptor_m, "sigma at the receptor");
    ages[1] = tstart;
    sigmas[1] = s1;
    ages[2] = tstart + tstep;
    sigmas[2] = s2;
    int index = 0;
    R adelt = std::abs(t - ages[0]);
    for (int i = 1; i < 3; ++i) {
        if (std::abs(t - ages[i]) < adelt) {
            index = i;
            adelt = std::abs(t - ages[i]);
        }
    }
    const R speed_kps = 0.001F * speed;
    R sigma = kZero;
    if (itype == 1) {
        const auto reverse = sigma_y_curve(static_cast<double>(sigmas[index]), 0.0, 0.0);
        const R virtual_time = static_cast<R>(reverse.virtual_time_s);
        const R virtual_distance = static_cast<R>(reverse.virtual_distance_km);
        const R tsec = std::max(kZero, virtual_time + (t - ages[index]));
        const R dkm = std::max(kZero, virtual_distance + (t - ages[index]) * speed_kps);
        if (tsec > kZero) {
            sigma = static_cast<R>(sigma_y_curve(0.0, static_cast<double>(dkm),
                                                 static_cast<double>(tsec))
                                       .value);
        }
    } else {
        // The vendor SIGMA sigma-z branch computes TSEC and DKM but then passes
        // the REVERSE outputs (VDZ, VTZ) to the forward SIGTZ call, unlike the
        // sigma-y branch which passes DKM/TSEC. That asymmetry is a property of
        // the original routine and is reproduced verbatim here.
        const auto reverse = sigma_z_curve(static_cast<double>(sigmas[index]), 0.0, 0.0,
                                           static_cast<double>(zpuff));
        const R virtual_time = static_cast<R>(reverse.virtual_time_s);
        const R virtual_distance = static_cast<R>(reverse.virtual_distance_km);
        const R tsec = std::max(kZero, virtual_time + (t - ages[index]));
        if (tsec > kZero) {
            sigma = static_cast<R>(sigma_z_curve(0.0, static_cast<double>(virtual_distance),
                                                 static_cast<double>(virtual_time),
                                                 static_cast<double>(zpuff))
                                       .value);
        }
    }
    return static_cast<double>(sigma);
}

void receptor_geometry(CtsgState& state) {
    // CTREC (calpuff.for L22841-22921), REAL*4.
    const R xrc = to_real(state.xr - state.xc, "hill-centred receptor x");
    const R yrc = to_real(state.yr - state.yc, "hill-centred receptor y");
    auto rotated = rotate_xy(static_cast<double>(xrc), static_cast<double>(yrc), state.rotflo);
    state.xrf = rotated.x;
    state.yrf = rotated.y;
    rotated = rotate_xy(state.xrf, state.yrf, -state.rotang);
    state.xre = rotated.x;
    state.yre = rotated.y;

    if (to_real(state.zrec, "receptor height") < to_real(state.hd, "dividing height")) {
        const auto coordinates =
            elliptic_coordinates(0, static_cast<double>(to_real(state.xre * state.baxi, "xre*baxi")),
                                 static_cast<double>(to_real(state.yre * state.baxi, "yre*baxi")),
                                 state.r);
        if (static_cast<R>(coordinates.mu) > kZero) {
            R rsq = to_real(state.r * state.r, "axis ratio squared");
            if (rsq < kOne) rsq = kOne;
            const R dum1 = std::sqrt(rsq - kOne);
            if (dum1 != kZero) {
                const R rmu0 = std::log((to_real(state.r, "axis ratio") + kOne) / dum1);
                const R sinnu = std::sin(static_cast<R>(coordinates.nu));
                const R cosnu = std::cos(static_cast<R>(coordinates.nu));
                const R sinhmu = std::sinh(rmu0);
                const R coshmu = std::cosh(rmu0);
                const R baxi = to_real(state.baxi, "baxi");
                state.xre = static_cast<double>((dum1 * coshmu * cosnu) / baxi);
                state.yre = static_cast<double>((dum1 * sinhmu * sinnu) / baxi);
            } else {
                const R xre = to_real(state.xre, "receptor x");
                const R yre = to_real(state.yre, "receptor y");
                const R factor =
                    kOne / (std::sqrt(xre * xre + yre * yre) * to_real(state.baxi, "baxi"));
                state.xre = static_cast<double>(xre * factor);
                state.yre = static_cast<double>(yre * factor);
            }
            rotated = rotate_xy(state.xre, state.yre, state.rotang);
            state.xrf = rotated.x;
            state.yrf = rotated.y;
        }
    }

    rotated = rotate_xy(state.xrf, state.yrf, state.beta);
    state.xrb = rotated.x;
    state.yrb = rotated.y;
    state.iregu = region_index(state.xrf, state.x12f, state.x23f);
    state.iregl = region_index(state.xrb, state.xob, -state.xob);
    const R u = to_real(state.u, "transport speed");
    require_true(u != kZero, "transport speed must not be zero");
    state.t12ru =
        static_cast<double>((to_real(state.xrf, "xrf") - to_real(state.x12f, "x12f")) / u);
    state.t12rl = static_cast<double>((to_real(state.xrb, "xrb") - to_real(state.xob, "xob")) /
                                      (u * to_real(state.cbeta, "cbeta")));
}

double puff_concentration(const CtsgState& state, int imode, double zpole_m, double dpole_m) {
    // PUFFC (calpuff.for L25286-25404), REAL*4. ERFDIF is the P7E port of the
    // vendor routine (the vendor PUFFC uses ERFDIF, not the intrinsic ERF).
    require_true(imode >= 0 && imode <= 2, "imode must be 0, 1 or 2");
    R pole = to_real(zpole_m, "pole height");
    const R lateral_offset = to_real(dpole_m, "stagnation-streamline offset");
    if (imode == 0) pole = kZero;

    const R timpg = to_real(state.timpg, "age at impingement");
    const R t12rl = to_real(state.t12rl, "travel time from the lower boundary");
    const R tup = timpg + t12rl;
    if (tup <= kZero) return 0.0;

    const R sz = to_real(state.szr, "receptor sigma-z");
    const R sy = to_real(state.syr, "receptor sigma-y");
    require_true(sy != kZero, "receptor sigma-y must not be zero");
    const R szsq = sz * sz;
    const R sysq = sy * sy;
    const R zlid = to_real(state.zlid, "mixing lid");
    const R u = to_real(state.u, "transport speed");
    const R q = to_real(state.q, "mass");
    const R tstep = to_real(state.tstep, "step duration");
    require_true(tstep != kZero && u != kZero, "step duration and speed must not be zero");

    int imix = 0;
    if (sz >= 1.6F * zlid) imix = 1;

    const R t1mtr = -(to_real(state.t12p, "travel time to the puff") + t12rl);
    const R t2mtr = tstep + t1mtr;
    const R dum = u / (kRt2 * sy);
    const R co = q * (static_cast<R>(erf_difference(static_cast<double>(t2mtr * dum),
                                                   static_cast<double>(t1mtr * dum)))) /
                 (tstep * kFour * kPi * u * sy * sz);
    if (co == kZero) return 0.0;

    R dely = to_real(state.yrf - state.ypf, "crosswind distance");
    if (imode == 2) dely = lateral_offset;
    const R argy = kHalf * (dely * dely / sysq);
    if (!(argy < kExpMax)) return 0.0;
    const R fy = std::exp(-argy);

    if (imix == 1) {
        // RT2PI is zero in the vendor (see ctsg.hpp), so this branch returns zero.
        const R fz = kRt2pi * sz / zlid;
        return static_cast<double>(co * fy * fz);
    }

    const R zpuff = to_real(state.zpuff, "puff height");
    const R zplus = zpuff + pole;
    const R zminus = zpuff - pole;
    const R dumz = kHalf / szsq;
    R argz1 = dumz * zminus * zminus;
    R argz2 = dumz * zplus * zplus;
    R fz = kZero;
    if (argz1 < kExpMax) fz += std::exp(-argz1);
    if (argz2 < kExpMax) fz += std::exp(-argz2);

    if (fz > kZero) {
        for (int i = 1; i <= kMaxReflections; ++i) {
            const R two_izl = kTwo * static_cast<R>(i) * zlid;
            argz1 = dumz * (two_izl - zminus) * (two_izl - zminus);
            argz2 = dumz * (two_izl - zplus) * (two_izl - zplus);
            const R argz3 = dumz * (two_izl + zminus) * (two_izl + zminus);
            const R argz4 = dumz * (two_izl + zplus) * (two_izl + zplus);
            R term1 = kZero;
            R term2 = kZero;
            R term3 = kZero;
            R term4 = kZero;
            if (argz1 < kExpMax) term1 = std::exp(-argz1);
            if (argz2 < kExpMax) term2 = std::exp(-argz2);
            if (argz3 < kExpMax) term3 = std::exp(-argz3);
            if (argz4 < kExpMax) term4 = std::exp(-argz4);
            const R previous = fz;
            fz = fz + term1 + term2 + term3 + term4;
            const R test = (fz - previous) / fz;
            if (test < kEpsRefl) break;
        }
    }
    return static_cast<double>(co * fy * fz);
}

double lower_segment(const CtsgState& state, const SigmaYCurve& sigma_y_curve,
                     const SigmaZCurve& sigma_z_curve) {
    // LOWER (calpuff.for L24657-24863), REAL*4.
    const R baxi = to_real(state.baxi, "baxi");
    const auto coordinates = elliptic_coordinates(
        1, static_cast<double>(to_real(state.xre, "receptor x") * baxi),
        static_cast<double>(to_real(state.yre, "receptor y") * baxi), state.r);
    const R side = sign_of(kOne, std::sin(static_cast<R>(coordinates.nu) +
                                          to_real(state.alfw, "flow angle")));

    const R timpg = to_real(state.timpg, "age at impingement");
    const R t12rl = to_real(state.t12rl, "travel time from the lower boundary");
    const R tup = timpg + t12rl;
    if (tup <= kZero) return 0.0;

    const R sz1 = to_real(state.sz1, "sigma-z at the start");
    const R sz2 = to_real(state.sz2, "sigma-z at the end");
    const R sy1 = to_real(state.sy1, "sigma-y at the start");
    const R sy2 = to_real(state.sy2, "sigma-y at the end");
    const R u = to_real(state.u, "transport speed");
    const R zpuff = to_real(state.zpuff, "puff height");
    const R tstart = to_real(state.tstart, "age at the start");
    const R tstep = to_real(state.tstep, "step duration");
    const R frac = to_real(state.frac, "fraction of the step");

    R sz = static_cast<R>(sigma_restart(2, static_cast<double>(zpuff), static_cast<double>(u),
                                        static_cast<double>(tup), static_cast<double>(sz1),
                                        static_cast<double>(tstart), static_cast<double>(sz2),
                                        static_cast<double>(tstep),
                                        static_cast<double>(to_real(state.szr, "receptor sigma-z")),
                                        static_cast<double>(frac), sigma_y_curve,
                                        sigma_z_curve));
    sz = std::max(sz1, sz);
    sz = std::min(sz2, sz);
    R sy = static_cast<R>(sigma_restart(1, static_cast<double>(zpuff), static_cast<double>(u),
                                        static_cast<double>(tup), static_cast<double>(sy1),
                                        static_cast<double>(tstart), static_cast<double>(sy2),
                                        static_cast<double>(tstep),
                                        static_cast<double>(to_real(state.syr, "receptor sigma-y")),
                                        static_cast<double>(frac), sigma_y_curve,
                                        sigma_z_curve));
    sy = std::max(sy1, sy);
    sy = std::min(sy2, sy);
    require_true(sy != kZero && sz != kZero, "receptor sigmas must not be zero");

    const R szsq = sz * sz;
    const R sysq = sy * sy;
    R szo = to_real(state.szimpg, "sigma-z at impingement");
    R szosq = szo * szo;
    R syo = to_real(state.syimpg, "sigma-y at impingement");
    const R syosq = syo * syo;
    R szpsq = szsq - szosq;
    const R sypsq = sysq - syosq;
    R szp = kZero;
    R syp = kZero;
    if (szpsq <= kZero) {
        szo = sz;
        szosq = szsq;
        szpsq = kZero;
    } else {
        szp = std::sqrt(szpsq);
    }
    if (sypsq <= kZero) {
        syo = sy;
        syp = kZero;
    } else {
        syp = std::sqrt(sypsq);
    }

    const R zlid = to_real(state.zlid, "mixing lid");
    int imix = 0;
    if (szo >= 1.6F * zlid) imix = 1;

    const R t1mtr = -(to_real(state.t12p, "travel time to the puff") + t12rl);
    const R t2mtr = tstep + t1mtr;
    const R dum = u / (kRt2 * sy);
    const R q = to_real(state.q, "mass");
    const R co = q * (std::erf(t2mtr * dum) - std::erf(t1mtr * dum)) /
                 (tstep * kFour * kPi * u * sy * sz);
    if (co <= kZero) return 0.0;

    const R d = to_real(state.d, "off-axis distance");
    const R argy1 = kHalf * (d * d / sysq);
    if (!(argy1 < kExpMax)) return 0.0;
    const R argy2 = (d * syp) / (kRt2 * syo * sy);
    const R fy = std::exp(-argy1) * (kOne + side * std::erf(argy2));

    if (imix == 1) {
        // RT2PI is zero in the vendor (see ctsg.hpp), so this branch returns zero.
        const R fz = kRt2pi * sz / zlid;
        return static_cast<double>(co * fy * fz);
    }

    const R hd = to_real(state.hd, "dividing height");
    const R zrec = to_real(state.zrec, "receptor height");
    R twofz = kZero;
    if (szp > kSmall) {
        const R ak = kOne / (kRt2 * sz * szo * szp);
        const R b1 = hd * szsq;
        const R eoi = zpuff;
        twofz = static_cast<R>(
            reflection_bjil(static_cast<double>(ak), static_cast<double>(b1),
                            static_cast<double>(zrec), static_cast<double>(eoi),
                            static_cast<double>(szsq), static_cast<double>(szosq),
                            static_cast<double>(szpsq)));
        if (twofz != kZero) {
            bool finished = false;
            // Reflections from the lid upwind of the hill (j = 1, i > 1).
            for (int i = 2; i <= kMaxReflections; ++i) {
                const R eoip = kTwo * static_cast<R>(i - 1) * zlid + zpuff;
                const R eoim = eoip - kTwo * zpuff;
                const R plus = static_cast<R>(reflection_bjil(
                    static_cast<double>(ak), static_cast<double>(b1), static_cast<double>(zrec),
                    static_cast<double>(eoip), static_cast<double>(szsq),
                    static_cast<double>(szosq), static_cast<double>(szpsq)));
                const R minus = static_cast<R>(reflection_bjil(
                    static_cast<double>(ak), static_cast<double>(b1), static_cast<double>(zrec),
                    static_cast<double>(eoim), static_cast<double>(szsq),
                    static_cast<double>(szosq), static_cast<double>(szpsq)));
                const R add = plus + minus;
                twofz += add;
                if (add / twofz < kEpsRefl) break;
            }
            // Reflections from the lid over and downwind of the hill (i = 1, j > 1).
            for (int j = 2; j <= kMaxReflections; ++j) {
                const R ejp = kTwo * static_cast<R>(j - 1) * zlid + zrec;
                const R ejm = ejp - kTwo * zrec;
                const R plus = static_cast<R>(reflection_bjil(
                    static_cast<double>(ak), static_cast<double>(b1), static_cast<double>(ejp),
                    static_cast<double>(eoi), static_cast<double>(szsq),
                    static_cast<double>(szosq), static_cast<double>(szpsq)));
                const R minus = static_cast<R>(reflection_bjil(
                    static_cast<double>(ak), static_cast<double>(b1), static_cast<double>(ejm),
                    static_cast<double>(eoi), static_cast<double>(szsq),
                    static_cast<double>(szosq), static_cast<double>(szpsq)));
                const R add = plus + minus;
                twofz += add;
                if (add / twofz < kEpsRefl) break;
            }
            // Reflections throughout (i > 1, j > 1).
            for (int i = 2; i <= kMaxReflections && !finished; ++i) {
                const R eoip = kTwo * static_cast<R>(i - 1) * zlid + zpuff;
                const R eoim = eoip - kTwo * zpuff;
                for (int j = 1; j <= kMaxReflections; ++j) {
                    const R ejp = kTwo * static_cast<R>(j - 1) * zlid + zrec;
                    const R ejm = ejp - kTwo * zrec;
                    const R add =
                        static_cast<R>(reflection_bjil(
                            static_cast<double>(ak), static_cast<double>(b1),
                            static_cast<double>(ejp), static_cast<double>(eoip),
                            static_cast<double>(szsq), static_cast<double>(szosq),
                            static_cast<double>(szpsq))) +
                        static_cast<R>(reflection_bjil(
                            static_cast<double>(ak), static_cast<double>(b1),
                            static_cast<double>(ejm), static_cast<double>(eoip),
                            static_cast<double>(szsq), static_cast<double>(szosq),
                            static_cast<double>(szpsq))) +
                        static_cast<R>(reflection_bjil(
                            static_cast<double>(ak), static_cast<double>(b1),
                            static_cast<double>(ejp), static_cast<double>(eoim),
                            static_cast<double>(szsq), static_cast<double>(szosq),
                            static_cast<double>(szpsq))) +
                        static_cast<R>(reflection_bjil(
                            static_cast<double>(ak), static_cast<double>(b1),
                            static_cast<double>(ejm), static_cast<double>(eoim),
                            static_cast<double>(szsq), static_cast<double>(szosq),
                            static_cast<double>(szpsq)));
                    twofz += add;
                    if (add / twofz < kEpsRefl) {
                        // The vendor returns for j == 1 and continues the i loop
                        // otherwise (labels 501 and 400).
                        if (j > 1) break;
                        finished = true;
                        break;
                    }
                }
            }
        }
    } else if (zrec <= hd) {
        // Sigma-z is not growing: only the j = 1 terms contribute.
        const R ak = kHalf / szsq;
        const R eoip = zpuff;
        twofz = static_cast<R>(
            reflection_b(static_cast<double>(ak), static_cast<double>(eoip - zrec),
                         static_cast<double>(eoip + zrec)));
        if (twofz != kZero) {
            for (int i = 2; i <= kMaxReflections; ++i) {
                const R eoip_i = kTwo * static_cast<R>(i - 1) * zlid + zpuff;
                const R eoim = eoip_i - kTwo * zpuff;
                const R plus = static_cast<R>(
                    reflection_b(static_cast<double>(ak), static_cast<double>(eoip_i - zrec),
                                 static_cast<double>(eoip_i + zrec)));
                const R minus = static_cast<R>(
                    reflection_b(static_cast<double>(ak), static_cast<double>(eoim - zrec),
                                 static_cast<double>(eoim + zrec)));
                const R add = plus + minus;
                twofz += add;
                if (add / twofz <= kEpsRefl) break;
            }
        }
    }

    const R fz = kHalf * twofz;
    return static_cast<double>(co * fy * fz);
}

CtsgResult ctsg(CtsgState state, const CtsgInputs& inputs, const SigmaYCurve& sigma_y_curve,
                const SigmaZCurve& sigma_z_curve) {
    // CTSG (calpuff.for L22923-23112). The CTSG argument list is taken from the
    // state fields; the persistent /CTPASS/ values that decide whether CTPAR
    // runs are state.tstart, state.ip and state.ih (the PREVIOUS call). The
    // vendor's TWOKZ/TWOKY derivation is omitted: only CTPAR (not ported) and
    // the debug print read it.
    const bool same_period = (to_real(state.tstart, "previous start age") ==
                              to_real(inputs.start_age_s, "start age")) &&
                             (state.ip == inputs.puff_index) && (state.ih == inputs.hill_index);
    if (!same_period) {
        throw std::runtime_error(
            "P7M CTSG: the vendor would call CTPAR for this puff/hill/time step, and CTPAR is "
            "not reconstructed (supply the CTPAR outputs and reuse the same step)");
    }
    state.ir = inputs.receptor_index;
    state.ip = inputs.puff_index;
    state.ih = inputs.hill_index;
    state.tstart = inputs.start_age_s;
    state.xr = inputs.receptor_x_m;
    state.yr = inputs.receptor_y_m;
    // Height above the base plane of the current hill (REAL*4 in the vendor).
    state.zrec = static_cast<double>(to_real(state.zrec, "receptor height") -
                                     to_real(state.zgrid, "hill base plane"));

    receptor_geometry(state);

    double above = 0.0;
    double below = 0.0;
    if (state.zrec > state.hd) {
        if (state.zlid > state.hd) {
            if (state.iregu == 1) {
                above = puff_concentration(state, 1, state.hd, 0.0);
            } else {
                throw std::runtime_error(
                    "P7M CTSG: UPPER (above the dividing streamline, not upwind of the hill) "
                    "is not reconstructed");
            }
            if (state.iregl != 1 && state.hd > 0.0) {
                below = lower_segment(state, sigma_y_curve, sigma_z_curve);
            }
        }
    } else if (state.hd > 0.0) {
        if (state.iregl == 1) {
            below = puff_concentration(state, 2, state.zrec, state.d);
        } else {
            below = lower_segment(state, sigma_y_curve, sigma_z_curve);
        }
    }
    CtsgResult result;
    result.flat_concentration = puff_concentration(state, 0, 0.0, 0.0);
    result.concentration = above + below;
    return result;
}

CtsgConstants ctsg_constants() {
    CtsgConstants constants;
    constants.rt2pi = static_cast<double>(kRt2pi);
    constants.small = static_cast<double>(kSmall);
    constants.expmax = static_cast<double>(kExpMax);
    constants.epsrefl = static_cast<double>(kEpsRefl);
    constants.max_reflections = kMaxReflections;
    return constants;
}

} // namespace cteas::puff
