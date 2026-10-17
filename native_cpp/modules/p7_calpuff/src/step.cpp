#include "cteas/puff/step.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = StepReal;

constexpr R kZero = 0.0F;
constexpr R kHalf = 0.5F;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7P step: " + message);
}

void require_finite(double value, const std::string& what) {
    require_true(std::isfinite(value), what + " must be finite");
}

R to_real(double value, const char* what) {
    require_finite(value, what);
    return static_cast<R>(value);
}

} // namespace

StepBookkeeping step_bookkeeping(const StepBookkeepingInputs& inputs) {
    // SETPUF L48373-48399, REAL*4/INTEGER*4 exactly as the vendor writes it.
    const R total_distance = to_real(inputs.total_distance_m, "total distance");
    const R total_time = to_real(inputs.total_time_s, "total time");
    const R step_distance = to_real(inputs.step_distance_m, "step distance");
    const R step_seconds = to_real(inputs.step_seconds, "step seconds");
    const R km_per_m = to_real(inputs.km_per_m, "km per metre");
    const R wind = to_real(inputs.wind_speed_ms, "transport speed");
    const R calm_threshold = to_real(inputs.calm_wind_threshold, "calm wind threshold");
    require_true(step_seconds >= kZero, "the step must not be negative");

    StepBookkeeping result;
    result.distance_begin_m = static_cast<double>(total_distance);
    result.distance_end_m = static_cast<double>(total_distance + step_distance);
    result.time_begin_s = static_cast<double>(total_time);
    result.time_end_s = static_cast<double>(total_time + step_seconds);
    result.mid_distance_km = static_cast<double>(kHalf * step_distance * km_per_m);
    result.mid_time_s = static_cast<double>(kHalf * step_seconds);
    result.mean_speed_ms = static_cast<double>(wind);
    result.speed_kps = static_cast<double>(wind * km_per_m);
    result.downwash_code = inputs.downwash_code;
    result.x_final_m = inputs.x_final_m;
    result.dispersion_y_option = inputs.dispersion_y_option;
    result.dispersion_z_option = inputs.dispersion_z_option;
    result.calm = false;
    if (wind < calm_threshold) {
        result.calm = true;
        result.dispersion_y_option = 1;
        result.dispersion_z_option = 1;
        result.downwash_code = 0;
        result.x_final_m = 0.0;
    }
    return result;
}

StepUpdate apply_step_update(const StepUpdateInputs& inputs) {
    // SETPUF L48706-48723, REAL*4.
    R height_end = to_real(inputs.height_end_m, "end-of-step height");
    const R settling = to_real(inputs.settling_velocity_ms, "settling velocity");
    const R step_seconds = to_real(inputs.step_seconds, "step seconds");
    const R step_distance = to_real(inputs.step_distance_m, "step distance");
    const R total_distance = to_real(inputs.total_distance_m, "total distance");
    const R total_time = to_real(inputs.total_time_s, "total time");
    const R x_new = to_real(inputs.x_new_km, "end-of-step x");
    const R y_new = to_real(inputs.y_new_km, "end-of-step y");
    require_true(inputs.plume_tilt == 0 || inputs.plume_tilt == 1, "MTILT must be 0 or 1");
    require_true(settling >= kZero, "the settling velocity must not be negative");

    if (inputs.plume_tilt == 1) {
        height_end = height_end - settling * step_seconds;
        height_end = std::max(height_end, kZero);
    }
    StepUpdate result;
    result.height_end_m = static_cast<double>(height_end);
    result.total_distance_m = static_cast<double>(total_distance + step_distance);
    result.total_time_s = static_cast<double>(total_time + step_seconds);
    result.x_km = static_cast<double>(x_new);
    result.y_km = static_cast<double>(y_new);
    result.z_km = static_cast<double>(height_end);
    return result;
}

SigmaParameterState set_sigma_parameters(const SigmaParameterInputs& inputs,
                                         const SigmaYCurve& sigma_y_curve) {
    // SETCSIG (calpuff.for L52504-52619), REAL*4.
    require_true(static_cast<bool>(sigma_y_curve),
                 "the sigma-y curve must be supplied for the Heffter transition");
    require_true(inputs.stability_class >= 1, "the stability class must be at least 1");
    require_true(inputs.tau_ly != 1,
                 "MTAULY=1 needs TAULY, which is not reconstructed");

    SigmaParameterState state;
    state.dispersion_y_option = inputs.dispersion_y_option;
    state.dispersion_z_option = inputs.dispersion_z_option;
    state.urban = inputs.urban;
    state.mean_speed_ms = inputs.mean_speed_ms;
    state.stability_class = inputs.stability_class;
    state.obukhov_length_m = inputs.obukhov_length_m;
    state.brunt_vaisala_s = inputs.brunt_vaisala_s;
    state.heffter_sigma_z = inputs.heffter_sigma_z;
    state.sigma_v_ms = inputs.sigma_v_ms;
    state.sigma_w_ms = inputs.sigma_w_ms;
    state.min_sigma_y_m = inputs.min_sigma_y_m;
    state.min_sigma_z_m = inputs.min_sigma_z_m;
    state.cell_x = inputs.cell_x;
    state.cell_y = inputs.cell_y;
    state.met_domain = inputs.met_domain;
    if (state.stability_class > 6) state.stability_class = 6;

    const R syh = to_real(inputs.sigma_y_heffter_m, "SYH");
    state.sigma_z_heffter_m = static_cast<double>(syh);
    const auto point = sigma_y_curve(static_cast<double>(syh), 0.0, 0.0);
    state.heffter_transition_time_s = point.virtual_time_s;
    state.heffter_transition_distance_km = point.virtual_distance_km;
    return state;
}

} // namespace cteas::puff
