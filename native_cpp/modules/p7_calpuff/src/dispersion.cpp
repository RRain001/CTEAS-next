#include "cteas/puff/dispersion.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>

namespace cteas::puff {
namespace {

using R = DispersionReal;

// Vendor constants. Names in brackets are the original identifiers in
// calpuff.for so every number below can be checked against the source text.
constexpr R kSmallSigma_m = 0.001F;      // ZEROSIG
constexpr R kPseudoTolerance = 1.0e-4F;  // CRIT
constexpr int kMaxPseudoIterations = 50;
constexpr R kDegreesToRadians = 0.017453293F; // 0.017453293
constexpr R kIscRuralCoefficient = 465.11628F;
constexpr R kUrbanSigmaZCap_m = 5000.0F;  // SIGMAX
constexpr R kSecondsPerKm = 1000.0F;
constexpr R kKmPerMetre = 0.001F;
// The original resets small negative increments to zero (warning in the
// middle band) and halts beyond the second threshold.
constexpr R kDtResetFatal_s = -1.0F;      // ZEROSEC(2)
constexpr R kDxResetFatal_km = -0.001F;   // ZEROKM(2)
constexpr R kNoRoughnessB = -1000.0F;     // BZ0TRM when MROUGH = 0
constexpr R kRoughnessBThreshold = -999.0F;
// SIGSET roughness adjustment (MROUGH = 1).
constexpr R kRoughnessBAdd = 0.0777F;
constexpr R kRoughnessBScale = 0.0215F;
constexpr R kRoughnessAScale = 1.585F;
constexpr R kRoughnessAExponent = 0.1301F;
constexpr R kRoughnessReferenceZ0_m = 0.03F;
constexpr R kRoughnessYExponent = 0.2F;
constexpr R kAveragingExponent = 0.2F;    // PLAW

// Vendor BLOCK DATA defaults for the dispersion control options
// (calpuff.for lines 2204, 2206 and 2245-2247).
constexpr int kDefaultMdisp = 3;
constexpr int kDefaultMdisp2 = 3;
constexpr int kDefaultMturbvw = 3;
constexpr int kDefaultMtauly = 0;
constexpr int kDefaultMhftsz = 0;
constexpr int kDefaultMrough = 0;
constexpr double kDefaultAvetMinutes = 60.0;
constexpr double kDefaultPgtimeMinutes = 60.0;
constexpr double kDefaultSytdep_m = 550.0;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7D dispersion: " + message);
}

void require_finite(double value, const std::string& what) {
    require_true(std::isfinite(value), what + " must be finite");
}

int required_option_int(const ControlFile& control, const char* key, int fallback) {
    const auto found = control.values(key);
    if (found.empty()) return fallback;
    require_true(found.size() == 1U, std::string("expected at most one active control: ") + key);
    int value = 0;
    const auto& raw = found.front();
    const auto [end, error] = std::from_chars(raw.data(), raw.data() + raw.size(), value);
    require_true(end == raw.data() + raw.size() && error == std::errc{},
                 std::string("invalid integer option ") + key + "=" + raw);
    return value;
}

double required_option_double(const ControlFile& control, const char* key, double fallback) {
    const auto found = control.values(key);
    if (found.empty()) return fallback;
    require_true(found.size() == 1U, std::string("expected at most one active control: ") + key);
    std::string raw = found.front();
    for (char& c : raw) {
        if (c == 'D' || c == 'd') c = 'E';
    }
    std::size_t consumed = 0;
    double value = 0.0;
    try {
        value = std::stod(raw, &consumed);
    } catch (const std::exception&) {
        throw std::invalid_argument(std::string("P7D dispersion: invalid float option ") + key +
                                    "=" + found.front());
    }
    require_true(consumed == raw.size() && std::isfinite(value),
                 std::string("P7D dispersion: invalid or non-finite float option ") + key + "=" +
                     found.front());
    return value;
}

R rural_y_sigma(const DispersionTables& tables, int stability, R x_km, R averaging_factor,
                R roughness_factor) {
    // SIGTY IDOPTYS = 3 rural: th = 0.017453293*(C-D*log(xkm));
    //                         sigy = AVEFAC*YRFAC*465.11628*xkm*tan(th)
    const R theta = kDegreesToRadians * (tables.rural_y_coefficient[stability - 1] -
                                         tables.rural_y_exponent[stability - 1] * std::log(x_km));
    return averaging_factor * roughness_factor * kIscRuralCoefficient * x_km * std::tan(theta);
}

R xvy(const DispersionTables& tables, R sigma_y0_m, int stability) {
    // XVY: direct solution for the Briggs urban pseudo-distance (km).
    const R a2 = tables.urban_y_coefficient[stability - 1] * tables.urban_y_coefficient[stability - 1];
    const R bsy0 = 0.5F * tables.urban_y_inverse_length[stability - 1] * sigma_y0_m;
    return sigma_y0_m * (bsy0 + std::sqrt(bsy0 * bsy0 + a2)) / a2 * kKmPerMetre;
}

R xvz(const DispersionTables& tables, R sigma_z0_m, int stability) {
    // XVZ: ISC6-8 urban pseudo-distance (km). Stability classes 1-2 use the
    // cubic branch with overridden coefficients, class 3 is linear, classes
    // 4-6 use the closed form.
    const R third = 0.3333333F;
    R c = tables.urban_z_coefficient[stability - 1];
    R d = tables.urban_z_inverse_length[stability - 1];
    if (stability <= 2) {
        // Vendor `go to (180,180,190,200,200,200), kst` with the class A/B
        // coefficients overridden before the dispatch.
        c = 1.0e6F;
        d = 1.0e9F;
    }
    if (stability == 3) {
        // Class C takes the linear branch; the vendor's D = 0 for class C is
        // never used there.
        return sigma_z0_m / c * kKmPerMetre;
    }
    if (stability >= 4) {
        // Closed form for classes D, E and F.
        return sigma_z0_m * (d * sigma_z0_m + std::sqrt((d * sigma_z0_m) * (d * sigma_z0_m) +
                                                        4.0F * c * c)) /
               (2.0F * c * c) * kKmPerMetre;
    }
    const R a = -c * third;
    const R b = (2.0F / 27.0F - (sigma_z0_m / 240.0F) * (sigma_z0_m / 240.0F)) * d;
    const R s = 0.25F * b * b + a * a * a / 27.0F;
    R y = 0.0F;
    if (s < 0.0F || (-b / 2.0F + std::sqrt(s)) < 0.0F) {
        const R cs = 13.5F * (sigma_z0_m / 240.0F) * (sigma_z0_m / 240.0F) - 1.0F;
        const R theta = std::acos(cs) * third;
        y = 2.0F * third * std::cos(theta) * kSecondsPerKm;
    } else {
        const R root = std::sqrt(s);
        y = std::pow(-b / 2.0F + root, third) + std::pow(-b / 2.0F - root, third);
    }
    return (y - kSecondsPerKm * third) * kKmPerMetre;
}

// Small negative increments: the original resets them to zero and halts
// beyond ZEROSEC(2)/ZEROKM(2). Returns true when a reset happened, which the
// caller reports instead of hiding.
bool screen_increment(R& value, R fatal_threshold, const char* axis) {
    if (value >= 0.0F) return false;
    require_true(value >= fatal_threshold,
                 std::string("negative ") + axis + " increment beyond the original halt threshold");
    value = 0.0F;
    return true;
}

struct SigmaYResult {
    R sigma_y = 0.0F;
    R virtual_time_s = 0.0F;
    R virtual_distance_km = 0.0F;
    bool increment_reset = false;
    bool heffter = false;
};

SigmaYResult sigty(const DispersionEnvironment& environment, const DispersionTables& tables,
                   int stability, R transition_time_s, R sigma_y0, DispersionIncrement increment) {
    SigmaYResult result;
    R dt = static_cast<R>(increment.dt_s);
    R dx = static_cast<R>(increment.dx_km);
    result.increment_reset = screen_increment(dt, kDtResetFatal_s, "SIGTY-t");
    result.increment_reset =
        screen_increment(dx, kDxResetFatal_km, "SIGTY-x") || result.increment_reset;

    const R syh = static_cast<R>(environment.sigma_y_heffter_m);
    const R ayt = tables.heffter_y_coefficient;
    const R uavg = static_cast<R>(environment.transport_speed_ms);
    const R averaging = static_cast<R>(environment.averaging_factor);
    const R roughness = static_cast<R>(environment.sigma_y_roughness);

    // Heffter (1965) time-dependent growth for long travel times, for all
    // IDOPTYS values.
    if (dt > transition_time_s && sigma_y0 < kSmallSigma_m) {
        const R tprime = syh / ayt - transition_time_s;
        result.sigma_y = ayt * (dt + tprime);
        result.virtual_time_s = dt;
        result.virtual_distance_km = uavg * dt * kKmPerMetre;
        result.heffter = true;
        return result;
    }
    if (sigma_y0 > syh) {
        const R tprime = syh / ayt - transition_time_s;
        const R t0 = sigma_y0 / ayt - tprime;
        const R t = t0 + dt;
        result.sigma_y = ayt * (t + tprime);
        result.virtual_time_s = t;
        result.virtual_distance_km = uavg * t * kKmPerMetre;
        result.heffter = true;
        return result;
    }

    if (!environment.urban) {
        // IDOPTYS = 3 rural: ISC multi-segment-free PGT curve with a secant
        // inversion for the pseudo-distance of a non-zero initial sigma.
        R pseudo_km = 0.0F;
        if (sigma_y0 > kSmallSigma_m) {
            const R averaging_inverse = 1.0F / averaging;
            const R roughness_inverse = 1.0F / roughness;
            R x1 = kKmPerMetre * sigma_y0;
            R x2 = kKmPerMetre * std::pow(sigma_y0 * averaging_inverse * roughness_inverse *
                                              (1.0F / tables.mesopuff_y_coefficient[stability - 1]),
                                          (1.0F / tables.mesopuff_y_exponent[stability - 1]));
            R s1 = rural_y_sigma(tables, stability, x1, averaging, roughness);
            R s2 = rural_y_sigma(tables, stability, x2, averaging, roughness);
            R x3 = 0.0F;
            int iterations = 0;
            for (;;) {
                const R denominator = x2 - x1;
                x3 = x2;
                if (denominator != 0.0F) {
                    const R fraction = (sigma_y0 - s1) / (s2 - s1);
                    x3 = x1 + fraction * denominator;
                    const R step = x3 - x2;
                    const R limit = 0.85F * std::abs(denominator);
                    if (std::abs(step) > limit) x3 = x2 + std::copysign(limit, step);
                }
                ++iterations;
                require_true(iterations <= kMaxPseudoIterations,
                             "SIGTY pseudo-distance inversion did not converge");
                require_true(x3 > 0.0F && std::isfinite(x3),
                             "SIGTY pseudo-distance inversion left the positive domain");
                const R s3 = rural_y_sigma(tables, stability, x3, averaging, roughness);
                const R error = (s3 - sigma_y0) / sigma_y0;
                if (std::abs(error) < kPseudoTolerance) {
                    pseudo_km = x3;
                    break;
                }
                x1 = x2;
                s1 = s2;
                x2 = x3;
                s2 = s3;
            }
        }
        const R x_km = pseudo_km + dx;
        if (dx > 0.0F) {
            result.sigma_y = x_km > 0.0F
                                 ? rural_y_sigma(tables, stability, x_km, averaging, roughness)
                                 : 0.0F;
        } else {
            result.sigma_y = sigma_y0;
        }
        result.virtual_distance_km = x_km;
        result.virtual_time_s = x_km * kSecondsPerKm / uavg;
        return result;
    }

    // IDOPTYS = 3 urban: Briggs/MP curves as in ISC.
    R pseudo_km = 0.0F;
    if (sigma_y0 > kSmallSigma_m) pseudo_km = xvy(tables, sigma_y0 * (1.0F / averaging), stability);
    const R distance_m = kSecondsPerKm * (pseudo_km + dx);
    if (dx > 0.0F) {
        result.sigma_y = averaging * tables.urban_y_coefficient[stability - 1] * distance_m /
                         std::sqrt(1.0F + tables.urban_y_inverse_length[stability - 1] * distance_m);
    } else {
        result.sigma_y = sigma_y0;
    }
    result.virtual_distance_km = distance_m * kKmPerMetre;
    result.virtual_time_s = distance_m / uavg;
    return result;
}

struct SigmaZResult {
    R sigma_z = 0.0F;
    R virtual_time_s = 0.0F;
    R virtual_distance_km = 0.0F;
    bool increment_reset = false;
    bool capped = false;
};

SigmaZResult sigtz(const DispersionEnvironment& environment, const DispersionTables& tables,
                   int stability, R sigma_z0, R height_m, DispersionIncrement increment) {
    SigmaZResult result;
    R dt = static_cast<R>(increment.dt_s);
    R dx = static_cast<R>(increment.dx_km);
    result.increment_reset = screen_increment(dt, kDtResetFatal_s, "SIGTZ-t");
    result.increment_reset =
        screen_increment(dx, kDxResetFatal_km, "SIGTZ-x") || result.increment_reset;
    (void)height_m; // only used by IDOPTZS = 5 (CTDM), which P7D refuses

    const R uavg = static_cast<R>(environment.transport_speed_ms);

    if (!environment.urban) {
        // IDOPTZS = 3 rural: ISC multi-segment PG curve, optionally adjusted
        // by the gridded roughness factors (A' = A*AZ0FAC, B' = B-BZ0TRM).
        const int segments = tables.rural_z_segments[stability - 1];
        std::array<R, DispersionTables::segments> a{};
        std::array<R, DispersionTables::segments> b{};
        std::array<R, DispersionTables::segments> boundary_sigma{};
        for (int k = 0; k < segments; ++k) {
            a[static_cast<std::size_t>(k)] = tables.rural_z_coefficient[static_cast<std::size_t>(k)]
                                                                    [stability - 1];
            b[static_cast<std::size_t>(k)] = tables.rural_z_exponent[static_cast<std::size_t>(k)]
                                                                  [stability - 1];
        }
        const R roughness_term = static_cast<R>(environment.sigma_z_b_term);
        if (roughness_term > kRoughnessBThreshold) {
            const R roughness_factor = static_cast<R>(environment.sigma_z_a_roughness);
            for (int k = 0; k < segments; ++k) {
                a[static_cast<std::size_t>(k)] *= roughness_factor;
                b[static_cast<std::size_t>(k)] -= roughness_term;
            }
        }
        for (int k = 0; k < segments - 1; ++k) {
            const auto index = static_cast<std::size_t>(k);
            boundary_sigma[index] =
                a[index] * std::pow(tables.rural_z_junction_km[index][stability - 1], b[index]);
        }
        boundary_sigma[static_cast<std::size_t>(segments - 1)] = 1.0e20F;

        R pseudo_km = 0.0F;
        if (sigma_z0 > kSmallSigma_m) {
            int segment = 1;
            while (true) {
                if (sigma_z0 <= boundary_sigma[static_cast<std::size_t>(segment - 1)]) break;
                ++segment;
                if (segment >= segments) break;
            }
            const auto index = static_cast<std::size_t>(segment - 1);
            pseudo_km = std::pow(sigma_z0 / a[index], 1.0F / b[index]);
        }
        const R x_km = pseudo_km + dx;
        if (dx > 0.0F) {
            int segment = 1;
            while (true) {
                if (x_km <= tables.rural_z_junction_km[static_cast<std::size_t>(segment - 1)]
                                               [stability - 1]) {
                    break;
                }
                ++segment;
                if (segment >= segments) break;
            }
            const auto index = static_cast<std::size_t>(segment - 1);
            result.sigma_z = a[index] * std::pow(x_km, b[index]);
        } else {
            result.sigma_z = sigma_z0;
        }
        result.virtual_distance_km = x_km;
        result.virtual_time_s = x_km * kSecondsPerKm / uavg;
        return result;
    }

    // IDOPTZS = 3 urban: Briggs/MP curves capped at the ISC 5000 m value.
    if (sigma_z0 >= kUrbanSigmaZCap_m) {
        result.sigma_z = sigma_z0;
        result.capped = true;
        return result;
    }
    R pseudo_km = 0.0F;
    if (sigma_z0 > kSmallSigma_m) pseudo_km = xvz(tables, sigma_z0, stability);
    const R distance_m = kSecondsPerKm * (pseudo_km + dx);
    if (dx > 0.0F) {
        R sigma_z = tables.urban_z_coefficient[stability - 1] * distance_m;
        if (stability <= 2) {
            sigma_z *= std::sqrt(1.0F + tables.urban_z_inverse_length[stability - 1] * distance_m);
        }
        if (stability >= 4) {
            sigma_z /= std::sqrt(1.0F + tables.urban_z_inverse_length[stability - 1] * distance_m);
        }
        if (sigma_z > kUrbanSigmaZCap_m) {
            sigma_z = kUrbanSigmaZCap_m;
            result.capped = true;
        }
        result.sigma_z = sigma_z;
    } else {
        result.sigma_z = sigma_z0;
    }
    result.virtual_distance_km = distance_m * kKmPerMetre;
    result.virtual_time_s = distance_m / uavg;
    return result;
}

} // namespace

DispersionOption require_supported_dispersion_option(int mdisp) {
    if (mdisp != 3) {
        throw std::invalid_argument(
            "P7D dispersion: control MDISP=" + std::to_string(mdisp) +
            " is not reconstructed; only MDISP=3 (PG rural + MP urban) is supported");
    }
    return DispersionOption::gaussian_pg_rural_mp_urban;
}

RoughnessAdjustment roughness_adjustment(double z0_m) {
    require_finite(z0_m, "roughness length z0");
    require_true(z0_m > 0.0, "roughness length z0 must be positive");
    const R z0 = static_cast<R>(z0_m);
    RoughnessAdjustment adjustment;
    const R b_term = kRoughnessBAdd + kRoughnessBScale * std::log(z0);
    adjustment.sigma_z_b_term = static_cast<double>(b_term);
    adjustment.sigma_z_a_factor =
        static_cast<double>(std::pow(static_cast<R>(1000.0), b_term) * kRoughnessAScale *
                            std::pow(z0, kRoughnessAExponent));
    adjustment.sigma_y_factor =
        static_cast<double>(std::pow(z0 / kRoughnessReferenceZ0_m, kRoughnessYExponent));
    return adjustment;
}

const DispersionTables& dispersion_tables() {
    static const DispersionTables tables = [] {
        DispersionTables value;
        // Vendor BLOCK DATA (calpuff.for ~L2150-2185).
        value.urban_y_coefficient = {0.32F, 0.32F, 0.22F, 0.16F, 0.11F, 0.11F};
        value.urban_y_inverse_length = {4.0e-4F, 4.0e-4F, 4.0e-4F, 4.0e-4F, 4.0e-4F, 4.0e-4F};
        value.urban_z_coefficient = {0.24F, 0.24F, 0.20F, 0.14F, 0.08F, 0.08F};
        value.urban_z_inverse_length = {1.0e-3F, 1.0e-3F, 1.0e-3F, 3.0e-4F, 1.5e-3F, 1.5e-3F};
        value.rural_z_segments = {8, 3, 1, 6, 9, 10};
        // SIGTY rural ISC coefficient/exponent pairs (C, D in the routine).
        value.rural_y_coefficient = {24.1667F, 18.333F, 12.5F, 8.333F, 6.25F, 4.1667F};
        value.rural_y_exponent = {2.5334F, 1.8096F, 1.0857F, 0.72382F, 0.54287F, 0.36191F};
        // MESOPUFF II sigma-y curves (AYPGT, BYPGT) used for the second guess.
        value.mesopuff_y_coefficient = {0.36F, 0.25F, 0.19F, 0.13F, 0.096F, 0.063F};
        value.mesopuff_y_exponent = {0.9F, 0.9F, 0.9F, 0.9F, 0.9F, 0.9F};
        value.heffter_y_coefficient = 0.5F;
        value.heffter_z_coefficient = {5.0F, 3.873F, 2.739F, 1.871F, 1.225F, 0.707F};
        value.heffter_y_sigma_m = 300.0F;
        value.heffter_z_sigma_m = 88.0F;
        // Rural sigma-z A/B pairs per segment and stability class (AZRUR/BZRUR).
        constexpr std::array<std::array<R, 10>, 6> a_by_class{{
            {122.80F, 158.08F, 170.22F, 179.52F, 217.41F, 258.89F, 346.75F, 453.85F, 453.85F, 453.85F},
            {90.673F, 98.483F, 109.3F, 109.3F, 109.3F, 109.3F, 109.3F, 109.3F, 109.3F, 109.3F},
            {61.141F, 61.141F, 61.141F, 61.141F, 61.141F, 61.141F, 61.141F, 61.141F, 61.141F, 61.141F},
            {34.459F, 32.093F, 32.093F, 33.504F, 36.65F, 44.053F, 44.053F, 44.053F, 44.053F, 44.053F},
            {24.26F, 23.331F, 21.628F, 21.628F, 22.534F, 24.703F, 26.97F, 35.42F, 47.618F, 47.618F},
            {15.209F, 14.457F, 13.953F, 13.953F, 14.823F, 16.187F, 17.836F, 22.651F, 27.074F, 34.219F},
        }};
        constexpr std::array<std::array<R, 10>, 6> b_by_class{{
            {0.9447F, 1.0542F, 1.0932F, 1.1262F, 1.2644F, 1.4094F, 1.7283F, 2.1166F, 2.1166F, 2.1166F},
            {0.93198F, 0.98332F, 1.0971F, 1.0971F, 1.0971F, 1.0971F, 1.0971F, 1.0971F, 1.0971F, 1.0971F},
            {0.91465F, 0.91465F, 0.91465F, 0.91465F, 0.91465F, 0.91465F, 0.91465F, 0.91465F, 0.91465F,
             0.91465F},
            {0.86974F, 0.81066F, 0.64403F, 0.60486F, 0.56589F, 0.51179F, 0.51179F, 0.51179F, 0.51179F,
             0.51179F},
            {0.8366F, 0.81956F, 0.75660F, 0.63077F, 0.57154F, 0.50527F, 0.46713F, 0.37615F, 0.29592F,
             0.29592F},
            {0.81558F, 0.78407F, 0.68465F, 0.63227F, 0.54503F, 0.46490F, 0.41507F, 0.32681F, 0.27436F,
             0.21716F},
        }};
        // Vendor XZBRUR data; SIGSET overwrites the junctions up to NZBRUR-1
        // from the A/B continuity condition, which is reproduced below.
        constexpr std::array<std::array<R, 10>, 6> junction_by_class{{
            {0.10F, 0.15F, 0.20F, 0.25F, 0.30F, 0.40F, 0.50F, 3.11F, 1.0e20F, 1.0e20F},
            {0.20F, 0.40F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F},
            {1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F},
            {0.30F, 1.00F, 3.00F, 10.0F, 30.0F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F, 1.0e20F},
            {0.10F, 0.30F, 1.00F, 2.00F, 4.00F, 10.0F, 20.0F, 40.0F, 1.0e20F, 1.0e20F},
            {0.20F, 0.70F, 1.00F, 2.00F, 3.00F, 7.00F, 15.0F, 30.0F, 60.0F, 1.0e20F},
        }};
        for (std::size_t class_index = 0; class_index < DispersionTables::levels; ++class_index) {
            for (std::size_t segment = 0; segment < DispersionTables::segments; ++segment) {
                value.rural_z_coefficient[segment][class_index] = a_by_class[class_index][segment];
                value.rural_z_exponent[segment][class_index] = b_by_class[class_index][segment];
                value.rural_z_junction_km[segment][class_index] = junction_by_class[class_index][segment];
            }
        }
        // SIGSET junction recomputation for j = 1..NZBRUR-1.
        for (std::size_t class_index = 0; class_index < DispersionTables::levels; ++class_index) {
            const int jmax = value.rural_z_segments[class_index] - 1;
            for (int j = 1; j <= jmax; ++j) {
                const auto first = static_cast<std::size_t>(j - 1);
                const auto second = static_cast<std::size_t>(j);
                const R ratio = value.rural_z_coefficient[first][class_index] /
                                value.rural_z_coefficient[second][class_index];
                const R difference = value.rural_z_exponent[second][class_index] -
                                     value.rural_z_exponent[first][class_index];
                R cut = 1.0e20F;
                if (difference > 0.0F) cut = std::pow(ratio, 1.0F / difference);
                if (difference < 0.0F) cut = std::pow(1.0F / ratio, -1.0F / difference);
                value.rural_z_junction_km[first][class_index] = cut;
            }
        }
        return value;
    }();
    return tables;
}

SigmaCurves::SigmaCurves(DispersionEnvironment environment) : environment_(environment) {
    require_true(environment_.stability_class >= 1, "PG stability class must be >= 1");
    if (environment_.stability_class > 6) {
        environment_.stability_class = 6;
        conditioned_ = true;
    }
    stability_ = environment_.stability_class;
    require_finite(environment_.transport_speed_ms, "transport speed");
    require_true(environment_.transport_speed_ms > 0.0, "transport speed must be positive");
    require_finite(environment_.sigma_y_heffter_m, "SYH sigma-y transition");
    require_true(environment_.sigma_y_heffter_m > 0.0, "SYH sigma-y transition must be positive");
    require_finite(environment_.averaging_factor, "averaging time factor");
    require_true(environment_.averaging_factor > 0.0, "averaging time factor must be positive");
    require_finite(environment_.sigma_y_roughness, "sigma-y roughness factor");
    require_true(environment_.sigma_y_roughness > 0.0, "sigma-y roughness factor must be positive");
    require_finite(environment_.sigma_z_a_roughness, "sigma-z roughness A factor");
    require_true(environment_.sigma_z_a_roughness > 0.0,
                 "sigma-z roughness A factor must be positive");
    require_finite(environment_.sigma_z_b_term, "sigma-z roughness B term");
    require_true(!environment_.heffter_sigma_z,
                 "MHFTSZ=1 needs the HEFTRAN sigma-z transition time, which is not reconstructed; "
                 "P7D supports the selected MHFTSZ=0 case");
}

double SigmaCurves::heffter_transition_time_y_s() const {
    // SETCSIG obtains THFTY by calling SIGTY with SIGY0 = SYH and zero
    // increments. The transition time is not an input of that call: with
    // DT = 0 both Heffter tests fail, so zero is passed here.
    DispersionIncrement zero_increment;
    return sigty(environment_, dispersion_tables(), stability_, 0.0F,
                 static_cast<R>(environment_.sigma_y_heffter_m), zero_increment)
        .virtual_time_s;
}

DispersionStep SigmaCurves::sigma_y(double sigy0_m, DispersionIncrement increment) const {
    require_finite(sigy0_m, "initial sigma-y");
    require_true(sigy0_m >= 0.0, "initial sigma-y must not be negative");
    require_finite(increment.dx_km, "sigma-y travel distance increment");
    require_finite(increment.dt_s, "sigma-y travel time increment");
    const auto result = sigty(environment_, dispersion_tables(), stability_,
                              static_cast<R>(heffter_transition_time_y_s()),
                              static_cast<R>(sigy0_m), increment);
    require_true(std::isfinite(result.sigma_y), "sigma-y left the finite domain");
    DispersionStep step;
    step.sigma_y_m = result.sigma_y;
    step.virtual_time_y_s = result.virtual_time_s;
    step.virtual_distance_y_km = result.virtual_distance_km;
    step.heffter_transition_time_y_s = heffter_transition_time_y_s();
    step.stability_class_conditioned = conditioned_;
    step.y_increment_reset = result.increment_reset;
    step.heffter_y_active = result.heffter;
    return step;
}

DispersionStep SigmaCurves::sigma_z(double sigz0_m, double height_m,
                                   DispersionIncrement increment) const {
    require_finite(sigz0_m, "initial sigma-z");
    require_true(sigz0_m >= 0.0, "initial sigma-z must not be negative");
    require_finite(height_m, "puff height");
    require_finite(increment.dx_km, "sigma-z travel distance increment");
    require_finite(increment.dt_s, "sigma-z travel time increment");
    const auto result = sigtz(environment_, dispersion_tables(), stability_,
                              static_cast<R>(sigz0_m), static_cast<R>(height_m), increment);
    require_true(std::isfinite(result.sigma_z), "sigma-z left the finite domain");
    DispersionStep step;
    step.sigma_z_m = result.sigma_z;
    step.virtual_time_z_s = result.virtual_time_s;
    step.virtual_distance_z_km = result.virtual_distance_km;
    step.stability_class_conditioned = conditioned_;
    step.z_increment_reset = result.increment_reset;
    step.urban_sigma_z_capped = result.capped;
    return step;
}

DispersionOptionAudit audit_dispersion_options(const ControlFile& control) {
    DispersionOptionAudit audit;
    audit.mdisp = required_option_int(control, "MDISP", kDefaultMdisp);
    audit.mdisp2 = required_option_int(control, "MDISP2", kDefaultMdisp2);
    audit.mturbvw = required_option_int(control, "MTURBVW", kDefaultMturbvw);
    audit.mtauly = required_option_int(control, "MTAULY", kDefaultMtauly);
    audit.mhftsz = required_option_int(control, "MHFTSZ", kDefaultMhftsz);
    audit.mrough = required_option_int(control, "MROUGH", kDefaultMrough);
    audit.avet_minutes = required_option_double(control, "AVET", kDefaultAvetMinutes);
    audit.pgtime_minutes = required_option_double(control, "PGTIME", kDefaultPgtimeMinutes);
    audit.sytdep_m = required_option_double(control, "SYTDEP", kDefaultSytdep_m);
    // For MDISP=3 the turbulence-based lateral time scale (TYIDR, from MTAULY
    // and TAULY) and the MTURBVW/MDISP2 turbulence options never enter SIGTY or
    // SIGTZ: they are used by IDOPT 1, 2 and 5 only.
    const bool turbulence_options = audit.mdisp == 1 || audit.mdisp == 5;
    audit.mdisp2_effective = turbulence_options;
    audit.mturbvw_effective = turbulence_options;
    audit.mtauly_effective = turbulence_options;
    audit.selected_option_note =
        "MDISP=" + std::to_string(audit.mdisp) +
        ": PG rural curves and MP/Briggs urban curves; MDISP2, MTURBVW and MTAULY are recorded but "
        "not effective for this option";
    return audit;
}

DispersionSetup dispersion_setup_from_control(const ControlFile& control) {
    DispersionSetup setup;
    setup.audit = audit_dispersion_options(control);
    setup.mdisp = setup.audit.mdisp;
    setup.option = require_supported_dispersion_option(setup.mdisp);
    require_true(setup.audit.avet_minutes > 0.0, "AVET must be positive");
    require_true(setup.audit.pgtime_minutes > 0.0, "PGTIME must be positive");
    require_true(setup.audit.sytdep_m > 0.0, "SYTDEP must be positive");
    if (setup.audit.mrough != 0 && setup.audit.mrough != 1) {
        throw std::invalid_argument("P7D dispersion: unsupported MROUGH=" +
                                    std::to_string(setup.audit.mrough));
    }
    require_true(setup.audit.mrough != 1,
                 "MROUGH=1 needs gridded z0 from CALMET; use roughness_adjustment(z0) with per-cell "
                 "roughness instead");
    if (setup.audit.mhftsz != 0 && setup.audit.mhftsz != 1) {
        throw std::invalid_argument("P7D dispersion: unsupported MHFTSZ=" +
                                    std::to_string(setup.audit.mhftsz));
    }
    require_true(setup.audit.mhftsz != 1,
                 "MHFTSZ=1 needs the HEFTRAN sigma-z transition time, which is not reconstructed");
    setup.sigma_y_heffter_m = setup.audit.sytdep_m;
    setup.averaging_factor =
        setup.audit.avet_minutes == setup.audit.pgtime_minutes
            ? 1.0
            : static_cast<double>(std::pow(static_cast<R>(setup.audit.avet_minutes /
                                                          setup.audit.pgtime_minutes),
                                           kAveragingExponent));
    setup.heffter_sigma_z = setup.audit.mhftsz == 1;
    setup.roughness_adjustment = setup.audit.mrough == 1;
    return setup;
}

DispersionEnvironment dispersion_environment(const DispersionSetup& setup, int stability_class,
                                             bool urban, double transport_speed_ms) {
    DispersionEnvironment environment;
    environment.stability_class = stability_class;
    environment.urban = urban;
    environment.transport_speed_ms = transport_speed_ms;
    environment.sigma_y_heffter_m = setup.sigma_y_heffter_m;
    environment.averaging_factor = setup.averaging_factor;
    require_true(!setup.roughness_adjustment,
                 "MROUGH=1 needs per-cell roughness factors; build the environment from "
                 "roughness_adjustment(z0) instead");
    environment.sigma_y_roughness = 1.0;
    environment.sigma_z_a_roughness = 1.0;
    environment.sigma_z_b_term = static_cast<double>(kNoRoughnessB);
    environment.heffter_sigma_z = setup.heffter_sigma_z;
    return environment;
}

} // namespace cteas::puff
