#include "cteas/puff/coupling.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = CouplingReal;

// Vendor constants (VCOUP data statements).
constexpr R kSmall = 1.0e-10F;        // SMALL
constexpr R kSqrtTwoPi = 2.5066283F;  // SRTPPI
constexpr R kPi = 3.1415926F;         // PI
constexpr R kUnlimitedLid = 9.9e10F;  // ZUNLIM
constexpr R kMinimumSigmaZ = 1.0e-2F; // SZCUT
constexpr R kTrappingThreshold = 0.63F;
constexpr R kExpCutoff = -20.0F;
constexpr R kThird = 0.3333333F;      // VCBAR THIRD
constexpr R kFourth = 0.25F;          // VCBAR FOURTH
constexpr R kHalf = 0.50F;            // VCBAR HALF

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7H coupling: " + message);
}

void require_finite(double value, const std::string& what) {
    require_true(std::isfinite(value), what + " must be finite");
}

} // namespace

double vertical_coupling(const VcoupInputs& inputs) {
    require_finite(inputs.receptor_height_m, "receptor height");
    require_finite(inputs.source_height_m, "source height");
    require_finite(inputs.sigma_z_m, "sigma-z");
    require_finite(inputs.lid_height_m, "lid height");
    require_finite(inputs.lid_max_m, "maximum lid height");
    require_true(inputs.puff_code == 99 || (inputs.puff_code >= 1 && inputs.puff_code <= 16),
                 "puff code must be 1-16 or 99");
    require_true(inputs.lid_height_m > 0.0, "lid height must be positive");
    require_true(inputs.lid_max_m >= inputs.lid_height_m,
                 "maximum lid height must not be below the lid height");

    // VCOUP (calpuff.for L53711-53864), REAL*4.
    const R receptor = static_cast<R>(inputs.receptor_height_m);
    R source = static_cast<R>(inputs.source_height_m);
    const R sigma_z = static_cast<R>(inputs.sigma_z_m);
    const R lid = static_cast<R>(inputs.lid_height_m);
    const R lid_max = static_cast<R>(inputs.lid_max_m);
    int code = inputs.puff_code;
    if (code > 10) code -= 10;

    if (code == 2 || code == 6) {
        // Within past/present mixed layer and uniform.
        if (receptor <= lid) return static_cast<double>(1.0F / lid);
        if (receptor <= lid_max) return static_cast<double>(1.0F / (lid_max - lid));
        return 0.0;
    }
    if (code == 4) return 0.0; // above the mixed layer and uniform

    // Gaussian distribution.
    R effective_lid = 0.0F;
    R effective_lid_max = 0.0F;
    if (source > lid) {
        effective_lid = kUnlimitedLid;
        effective_lid_max = kUnlimitedLid;
    } else {
        effective_lid = lid;
        effective_lid_max = std::max(lid, lid_max);
    }
    if (receptor > effective_lid) {
        if (receptor <= effective_lid_max) {
            return static_cast<double>(1.0F / (effective_lid_max - effective_lid));
        }
        return 0.0;
    }
    if (sigma_z < kMinimumSigmaZ) return 0.0;

    if ((sigma_z / effective_lid) > kTrappingThreshold) {
        // Near-uniform mixing (R. Yamartino, JAPCA 27, 5, May 1977).
        const R argument = -0.5F * (kPi * sigma_z / effective_lid) * (kPi * sigma_z / effective_lid);
        R expz = 1.0F;
        if (argument > kExpCutoff) {
            const R beta = std::exp(argument);
            const R beta2 = beta * beta;
            expz = (1.0F - beta2) *
                   (1.0F + beta2 + 2.0F * beta * std::cos(kPi * source / effective_lid) *
                                       std::cos(kPi * receptor / effective_lid));
        }
        return static_cast<double>(expz / effective_lid);
    }

    // Sum the reflection terms.
    const R sigma1 = sigma_z + kSmall;
    const R sigma2 = sigma_z * sigma_z + kSmall;
    R x = -0.5F * (receptor - source) * (receptor - source) / sigma2;
    if (x < kExpCutoff) return 0.0;
    R expz = std::exp(x);
    x = -0.5F * (receptor + source) * (receptor + source) / sigma2;
    if (x > kExpCutoff) expz += std::exp(x);
    for (int j = -1; j <= 1; j += 2) {
        const R reflection = 2.0F * static_cast<R>(j) * effective_lid;
        x = -0.5F * (receptor + source + reflection) * (receptor + source + reflection) / sigma2;
        if (x > kExpCutoff) expz += std::exp(x);
        x = -0.5F * (receptor - source + reflection) * (receptor - source + reflection) / sigma2;
        if (x > kExpCutoff) expz += std::exp(x);
    }
    return static_cast<double>(expz / (kSqrtTwoPi * sigma1));
}

double terrain_adjustment(double terrain_elevation_m, double height_m, double stack_height_m,
                          double stack_base_elevation_m, double plume_path_coefficient,
                          int terrain_adjustment_mode) {
    require_finite(terrain_elevation_m, "terrain elevation");
    require_finite(height_m, "puff height");
    require_finite(stack_height_m, "stack height");
    require_finite(stack_base_elevation_m, "stack base elevation");
    require_finite(plume_path_coefficient, "plume path coefficient");
    // CTADJ (calpuff.for L20480-20540), REAL*4.
    const R terrain = static_cast<R>(terrain_elevation_m);
    const R height = static_cast<R>(height_m);
    const R stack = static_cast<R>(stack_height_m);
    const R base = static_cast<R>(stack_base_elevation_m);
    if (terrain_adjustment_mode == 1) {
        const R relative = std::min(terrain - base, stack);
        return static_cast<double>(std::max(0.0F, height - relative));
    }
    if (terrain_adjustment_mode == 3) {
        const R delta = terrain - base;
        return static_cast<double>(height - (1.0F - static_cast<R>(plume_path_coefficient)) *
                                                std::min(height, delta));
    }
    throw std::invalid_argument("P7H coupling: CTADJ called with MCTADJ=" +
                                std::to_string(terrain_adjustment_mode) +
                                " (only 1 and 3 adjust the plume height)");
}

double vertical_coupling_bar(const VcbarInputs& inputs) {
    require_true(!inputs.calm,
                 "LCALM must be FALSE; the vendor routine halts for the calm branch");
    require_finite(inputs.lid_height_m, "lid height");
    require_finite(inputs.plume_path_coefficient, "plume path coefficient");
    require_true(inputs.terrain_adjustment == 0 || inputs.terrain_adjustment == 1 ||
                     inputs.terrain_adjustment == 2 || inputs.terrain_adjustment == 3,
                 "MCTADJ must be 0, 1, 2 or 3");
    require_true(inputs.plume_tilt == 0 || inputs.plume_tilt == 1, "MTILT must be 0 or 1");
    const bool terrain_path = inputs.terrain_adjustment == 1 || inputs.terrain_adjustment == 3;
    if (terrain_path) {
        require_true(static_cast<bool>(inputs.terrain),
                     "MCTADJ=1/3 needs a terrain lookup (GETELEV/GETCELL is not ported; "
                     "supply the met-grid elevation lookup)");
        require_finite(inputs.grid_spacing_m, "grid spacing");
        require_true(inputs.grid_spacing_m > 0.0, "grid spacing must be positive");
        require_finite(inputs.stack_height_m, "stack height");
        require_finite(inputs.stack_base_elevation_m, "stack base elevation");
    }
    const auto& state = inputs.state;
    for (const auto& [value, name] :
         {std::pair<double, const char*>{state.z_begin1, "z_begin1"},
          {state.z_end1, "z_end1"}, {state.z_begin2, "z_begin2"}, {state.z_end2, "z_end2"},
          {state.sigma_z_begin1, "sigma_z_begin1"}, {state.sigma_z_mid, "sigma_z_mid"},
          {state.sigma_z_end1, "sigma_z_end1"},
          {state.sigma_z_begin2, "sigma_z_begin2"}, {state.sigma_z_end2, "sigma_z_end2"},
          {state.final_height_m, "final height"}, {state.settling_velocity_ms, "settling velocity"}}) {
        require_finite(value, name);
    }
    for (const double value : {state.sigma_z_begin1, state.sigma_z_mid, state.sigma_z_end1,
                               state.sigma_z_begin2, state.sigma_z_end2}) {
        require_true(value >= 0.0, "sigma-z must not be negative");
    }
    require_finite(inputs.lid_height_m, "lid height");
    require_true(inputs.lid_height_m > 0.0, "lid height must be positive");

    // VCBAR (calpuff.for L53866-54088), REAL*4.
    const R lid = static_cast<R>(inputs.lid_height_m);
    const R lid_max = lid;   // HLIDMAX = HLID for the VCOUP calls (ZGR = 0)
    const auto coupling = [&](double height, double sigma_z) {
        VcoupInputs call;
        call.puff_code = state.puff_code;
        call.receptor_height_m = 0.0;   // ZGR = 0 (terrain-following receptor height)
        call.source_height_m = height;
        call.sigma_z_m = sigma_z;
        call.lid_height_m = static_cast<double>(lid);
        call.lid_max_m = static_cast<double>(lid_max);
        return static_cast<R>(vertical_coupling(call));
    };
    const auto adjusted_height = [&](double height, double x_km, double y_km) {
        R value = static_cast<R>(height);
        if (terrain_path) {
            const R elevation = static_cast<R>(inputs.terrain(x_km, y_km));
            value = static_cast<R>(terrain_adjustment(static_cast<double>(elevation),
                                                     static_cast<double>(value),
                                                     inputs.stack_height_m,
                                                     inputs.stack_base_elevation_m,
                                                     inputs.plume_path_coefficient,
                                                     inputs.terrain_adjustment));
        }
        return std::max(value, 0.0F);
    };

    R result = 0.0F;
    if (!inputs.slug) {
        // PUFF: mid-step, then beginning and end, each weighted by one third.
        R z_begin1 = 0.0F;
        R z_end1 = 0.0F;
        if (inputs.plume_tilt == 1) {
            const R final_height = static_cast<R>(state.final_height_m);
            const R settling = static_cast<R>(state.settling_velocity_ms);
            z_begin1 = final_height - static_cast<R>(state.time_begin1) * settling;
            z_end1 = final_height - static_cast<R>(state.time_end1) * settling;
        } else {
            z_begin1 = static_cast<R>(state.z_begin1);
            z_end1 = static_cast<R>(state.z_end1);
        }
        const R z_mid = kHalf * (z_begin1 + z_end1);
        result += kThird * coupling(static_cast<double>(adjusted_height(
                                       static_cast<double>(z_mid),
                                       static_cast<double>(kHalf * static_cast<R>(state.x_begin1) +
                                                           kHalf * static_cast<R>(state.x_end1)),
                                       static_cast<double>(kHalf * static_cast<R>(state.y_begin1) +
                                                           kHalf * static_cast<R>(state.y_end1)))),
                                   state.sigma_z_mid);
        result += kThird * coupling(
                               static_cast<double>(adjusted_height(static_cast<double>(z_begin1),
                                                                   state.x_begin1, state.y_begin1)),
                               state.sigma_z_begin1);
        result += kThird * coupling(
                               static_cast<double>(adjusted_height(static_cast<double>(z_end1),
                                                                   state.x_end1, state.y_end1)),
                               state.sigma_z_end1);
        return static_cast<double>(result);
    }

    // SLUG: four quarter-weighted samples (both ends, start and end of step).
    R z_begin1 = 0.0F;
    R z_end1 = 0.0F;
    R z_begin2 = 0.0F;
    R z_end2 = 0.0F;
    if (inputs.plume_tilt == 1) {
        const R final_height = static_cast<R>(state.final_height_m);
        const R settling = static_cast<R>(state.settling_velocity_ms);
        z_begin1 = final_height - static_cast<R>(state.time_begin1) * settling;
        z_end1 = final_height - static_cast<R>(state.time_end1) * settling;
        z_begin2 = final_height - static_cast<R>(state.time_begin2) * settling;
        z_end2 = final_height - static_cast<R>(state.time_end2) * settling;
    } else {
        z_begin1 = static_cast<R>(state.z_begin1);
        z_end1 = static_cast<R>(state.z_end1);
        z_begin2 = static_cast<R>(state.z_begin2);
        z_end2 = static_cast<R>(state.z_end2);
    }
    result += kFourth * coupling(
                            static_cast<double>(adjusted_height(static_cast<double>(z_begin1),
                                                                state.x_begin1, state.y_begin1)),
                            state.sigma_z_begin1);
    result += kFourth * coupling(
                            static_cast<double>(adjusted_height(static_cast<double>(z_begin2),
                                                                state.x_begin2, state.y_begin2)),
                            state.sigma_z_begin2);
    result += kFourth * coupling(
                            static_cast<double>(adjusted_height(static_cast<double>(z_end1),
                                                                state.x_end1, state.y_end1)),
                            state.sigma_z_end1);
    result += kFourth * coupling(
                            static_cast<double>(adjusted_height(static_cast<double>(z_end2),
                                                                state.x_end2, state.y_end2)),
                            state.sigma_z_end2);
    return static_cast<double>(result);
}

} // namespace cteas::puff
