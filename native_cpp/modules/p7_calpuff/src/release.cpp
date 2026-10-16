#include "cteas/puff/release.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = ReleaseReal;

constexpr R kZero = 0.0F;
constexpr R kOne = 1.0F;
constexpr R kUnlimitedMixingHeight = 1.0e04F;   // INJECT data ziunlm

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7O release: " + message);
}

void require_finite(double value, const std::string& what) {
    require_true(std::isfinite(value), what + " must be finite");
}

R to_real(double value, const char* what) {
    require_finite(value, what);
    return static_cast<R>(value);
}

} // namespace

ReleaseCadence release_cadence(const ReleaseCadenceInputs& inputs) {
    // POINTS1 L15975-16002, REAL*4/INTEGER*4 exactly as the vendor writes it.
    const R wind = to_real(inputs.wind_speed_ms, "release wind speed");
    const R interval = to_real(inputs.emission_interval, "emission interval");
    const R hour_seconds = to_real(inputs.hour_seconds, "emission hour length");
    require_true(inputs.max_puffs >= 1, "MXNEW must be at least 1");
    require_true(hour_seconds > kZero, "the emission hour must be positive");
    // The vendor truncates WSNEW*XTMP1+1 into an integer; for a non-negative
    // wind that equals INT(WSNEW*XTMP1)+1, so a negative wind (unphysical, and
    // not equivalent) is refused rather than silently diverging.
    require_true(wind >= kZero, "the release wind speed must not be negative");
    require_true(interval > kZero, "the emission interval must be positive");

    int puff_count = static_cast<int>(wind * interval) + 1;
    puff_count = std::max(puff_count, 1);
    puff_count = std::min(puff_count, inputs.max_puffs);
    ReleaseCadence result;
    result.puff_count = puff_count;
    result.new_puffs = puff_count;
    result.emission_duration_s = static_cast<double>(hour_seconds / static_cast<R>(puff_count));
    return result;
}

InjectionResult inject_emissions(const InjectionInputs& inputs) {
    // INJECT (calpuff.for L18561-18696), REAL*4.
    require_true(inputs.species_count >= 1, "at least one species is required");
    require_true(static_cast<std::size_t>(inputs.species_count) <= inputs.emission_rate.size(),
                 "the emission rate list is shorter than the species count");
    require_true(inputs.stability_class >= 1 && inputs.stability_class <= 6,
                 "stability class must be 1-6");
    const R duration = to_real(inputs.emission_duration_s, "emission duration");
    const R effective_height = to_real(inputs.effective_height_m, "effective height");
    const R max_layer = to_real(inputs.max_layer_height_m, "top of the upper layer");
    const R mixing_height = to_real(inputs.mixing_height_m, "mixing height");
    const R mixed_fraction = to_real(inputs.mass_fraction_mixed, "mixed-layer mass fraction");
    const bool gaussian = inputs.gaussian_distribution == 1;
    const int step_index = inputs.step_index;

    InjectionResult result;
    result.mixed_layer_mass.assign(static_cast<std::size_t>(inputs.species_count), 0.0);
    result.above_layer_mass.assign(static_cast<std::size_t>(inputs.species_count), 0.0);
    const auto rate = [&inputs](int index) {
        return to_real(inputs.emission_rate[static_cast<std::size_t>(index - 1)], "emission rate");
    };

    if (mixed_fraction != kOne && mixed_fraction != kZero) {
        // Partial penetration of the inversion.
        result.unlimited_mixing_height_m = static_cast<double>(max_layer);
        result.previous_mixing_height_m = static_cast<double>(mixing_height);
        for (int species = 1; species <= inputs.species_count; ++species) {
            const R total = rate(species) * duration;
            const R mixed = total * mixed_fraction;
            result.mixed_layer_mass[static_cast<std::size_t>(species - 1)] =
                static_cast<double>(mixed);
            result.above_layer_mass[static_cast<std::size_t>(species - 1)] =
                static_cast<double>(total - mixed);
        }
        result.puff_code = (gaussian ? 5 : 6) + step_index;
    } else if (effective_height <= mixing_height) {
        // Within the surface layer.
        for (int species = 1; species <= inputs.species_count; ++species) {
            result.mixed_layer_mass[static_cast<std::size_t>(species - 1)] =
                static_cast<double>(rate(species) * duration);
        }
        if (gaussian) {
            result.puff_code = 1 + step_index;
            if (inputs.stability_class >= 5) {
                result.unlimited_mixing_height_m = static_cast<double>(kUnlimitedMixingHeight);
                result.previous_mixing_height_m = static_cast<double>(kUnlimitedMixingHeight);
            } else {
                result.unlimited_mixing_height_m = static_cast<double>(mixing_height);
                result.previous_mixing_height_m = static_cast<double>(mixing_height);
            }
        } else {
            result.puff_code = 2 + step_index;
            result.unlimited_mixing_height_m = static_cast<double>(mixing_height);
            result.previous_mixing_height_m = static_cast<double>(mixing_height);
        }
    } else if (gaussian && inputs.stability_class >= 5) {
        // Above the surface layer in a stable regime: treated as unlimited mixing.
        result.puff_code = 1 + step_index;
        result.unlimited_mixing_height_m = static_cast<double>(kUnlimitedMixingHeight);
        result.previous_mixing_height_m = static_cast<double>(kUnlimitedMixingHeight);
        for (int species = 1; species <= inputs.species_count; ++species) {
            result.mixed_layer_mass[static_cast<std::size_t>(species - 1)] =
                static_cast<double>(rate(species) * duration);
        }
    } else {
        // Above the surface layer: all mass in the layer above the mixed layer.
        result.puff_code = (gaussian ? 3 : 4) + step_index;
        result.unlimited_mixing_height_m = static_cast<double>(mixing_height);
        result.previous_mixing_height_m = static_cast<double>(mixing_height);
        for (int species = 1; species <= inputs.species_count; ++species) {
            result.above_layer_mass[static_cast<std::size_t>(species - 1)] =
                static_cast<double>(rate(species) * duration);
        }
    }
    return result;
}

NewPuffState new_puff_state(const NewPuffInputs& inputs) {
    // POINTS1 L16120-16176: source arguments and COMMON /PUFF/ fields are\n    // original unqualified REAL (4 bytes). The outward-facing diagnostic\n    // NewPuffState is double but MUST contain exact promoted REAL*4 values.\n    // The XPT1GRD/YPT1GRD coordinates are relative met-grid units and must\n    // be supplied as such by the original grid conversion (separate gate).
    require_true(inputs.source_type >= 1, "the source type must be positive");
    NewPuffState state;
    state.x_km = static_cast<double>(to_real(inputs.source_x_km, "x_km"));
    state.y_km = static_cast<double>(to_real(inputs.source_y_km, "y_km"));
    state.tibl_height_m = -1.0;
    state.base_elevation_m = static_cast<double>(to_real(inputs.base_elevation_m, "base_elevation_m"));
    state.sigma_y_m = static_cast<double>(to_real(inputs.sigma_y_source_m, "sigma_y_m"));
    state.sigma_z_m = static_cast<double>(to_real(inputs.sigma_z_source_m, "sigma_z_m"));
    state.final_height_m = static_cast<double>(to_real(inputs.effective_height_m, "final_height_m"));
    state.height_begin_m = static_cast<double>(to_real(inputs.effective_height_m, "height_begin_m"));
    state.height_end_m = static_cast<double>(to_real(inputs.effective_height_m, "height_end_m"));
    state.x_final_m = static_cast<double>(to_real(inputs.x_final_m, "x_final_m"));
    state.final_rise_variance_m2 = static_cast<double>(to_real(inputs.final_rise_variance_m2, "final_rise_variance_m2"));
    state.buoyancy_flux = static_cast<double>(to_real(inputs.buoyancy_flux, "buoyancy_flux"));
    state.momentum_flux = static_cast<double>(to_real(inputs.momentum_flux, "momentum_flux"));
    state.x_final_buoyancy_m = static_cast<double>(to_real(inputs.x_final_buoyancy_m, "x_final_buoyancy_m"));
    state.x_final_momentum_m = static_cast<double>(to_real(inputs.x_final_momentum_m, "x_final_momentum_m"));
    state.z_final_buoyancy_m = static_cast<double>(to_real(inputs.z_final_buoyancy_m, "z_final_buoyancy_m"));
    state.z_final_momentum_m = static_cast<double>(to_real(inputs.z_final_momentum_m, "z_final_momentum_m"));
    state.stack_tip_downwash_m = static_cast<double>(to_real(inputs.stack_tip_downwash_m, "stack_tip_downwash_m"));
    state.split_flag = 1;
    state.stack_height_m = static_cast<double>(to_real(inputs.stack_height_m, "stack_height_m"));
    state.exit_velocity_ms = static_cast<double>(to_real(inputs.exit_velocity_ms, "exit_velocity_ms"));
    state.diameter_m = static_cast<double>(to_real(inputs.diameter_m, "diameter_m"));
    state.emission_duration_s = static_cast<double>(to_real(inputs.emission_duration_s, "emission_duration_s"));
    state.stack_wind_speed_ms = static_cast<double>(to_real(inputs.stack_wind_speed_ms, "stack_wind_speed_ms"));
    state.stability_class = inputs.stability_class;
    state.sqrt_stability_s = static_cast<double>(to_real(inputs.sqrt_stability_s, "sqrt_stability_s"));
    state.urban = inputs.urban;
    state.sigma_v_ms = static_cast<double>(to_real(inputs.sigma_v_ms, "sigma_v_ms"));
    state.sigma_w_ms = static_cast<double>(to_real(inputs.sigma_w_ms, "sigma_w_ms"));
    state.obukhov_length_m = static_cast<double>(to_real(inputs.obukhov_length_m, "obukhov_length_m"));
    state.plume_path_exponent = static_cast<double>(to_real(inputs.plume_path_exponent, "plume_path_exponent"));
    state.wind_ratio = 1.0;
    state.downwash_code = inputs.downwash_code;
    state.building_height_m = static_cast<double>(to_real(inputs.building_height_m, "building_height_m"));
    state.building_width_m = static_cast<double>(to_real(inputs.building_width_m, "building_width_m"));
    state.effective_height2_m = static_cast<double>(to_real(inputs.effective_height2_m, "effective_height2_m"));
    state.streamline_height_m = static_cast<double>(to_real(inputs.streamline_height_m, "streamline_height_m"));
    state.wake_radius_m = static_cast<double>(to_real(inputs.wake_radius_m, "wake_radius_m"));
    state.wake_xshift_m = static_cast<double>(to_real(inputs.wake_xshift_m, "wake_xshift_m"));
    state.source_sigma_y_m = static_cast<double>(to_real(inputs.initial_sigma_y_m, "source_sigma_y_m"));
    state.source_sigma_z_m = static_cast<double>(to_real(inputs.initial_sigma_z_m, "source_sigma_z_m"));
    state.sigma_y0_m = static_cast<double>(to_real(inputs.sigma_y_source_m, "sigma_y0_m"));
    state.sigma_z0_m = static_cast<double>(to_real(inputs.sigma_z_source_m, "sigma_z0_m"));
    state.release_index = inputs.release_index;
    state.source_index = inputs.source_index;
    state.source_type = inputs.source_type;
    return state;
}

double advance_puff_age(double age_s, double step_s) {
    // SETPUF (calpuff.for L48718): TMTOTB(II) = TMTOTB(II) + TSAMP. A puff
    // released during the current step starts at zero (SWAP L19366).
    require_finite(age_s, "puff age");
    require_finite(step_s, "sampling step");
    require_true(age_s >= 0.0, "the puff age must not be negative");
    require_true(step_s >= 0.0, "the sampling step must not be negative");
    return static_cast<double>(to_real(age_s, "puff age") + to_real(step_s, "sampling step"));
}

} // namespace cteas::puff
