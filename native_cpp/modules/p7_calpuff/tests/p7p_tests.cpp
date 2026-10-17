// P7P step-bookkeeping contract tests: hand-derived closed forms and every
// fail-closed path. Original-routine parity is checked separately by
// tests/p7p_parity_tests.py against the compiled vendor units.
#include "cteas/puff/step.hpp"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using cteas::puff::SigmaCurvePoint;
using cteas::puff::SigmaParameterInputs;
using cteas::puff::SigmaYCurve;
using cteas::puff::StepBookkeepingInputs;
using cteas::puff::StepUpdateInputs;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7P TEST FAILURE: " + message);
}

void require_close(double observed, double expected, double tolerance, const std::string& what) {
    require(std::abs(observed - expected) <= tolerance,
            what + ": observed " + std::to_string(observed) + " expected " +
                std::to_string(expected) + " tolerance " + std::to_string(tolerance));
}

template <typename Callable>
void require_throw(Callable&& callable, const std::string& what) {
    bool threw = false;
    try {
        callable();
    } catch (const std::exception&) {
        threw = true;
    }
    require(threw, what + " must fail closed");
}

SigmaCurvePoint stub_sigma_y(double sigma_y0_m, double dx_km, double dt_s) {
    const float s0 = static_cast<float>(sigma_y0_m);
    const float dx = static_cast<float>(dx_km);
    const float dt = static_cast<float>(dt_s);
    SigmaCurvePoint point;
    point.value = static_cast<double>(s0 + 0.5F * dx + 0.1F * dt);
    point.virtual_distance_km = static_cast<double>(s0 * 0.01F);
    point.virtual_time_s = static_cast<double>(s0 * 0.5F);
    return point;
}

void test_step_bookkeeping() {
    StepBookkeepingInputs inputs;
    inputs.total_distance_m = 1000.0;
    inputs.total_time_s = 3600.0;
    inputs.step_distance_m = 5026.0;
    inputs.step_seconds = 3600.0;
    inputs.km_per_m = 0.001;
    inputs.wind_speed_ms = 1.396;
    inputs.calm_wind_threshold = 0.5;
    inputs.downwash_code = 0;
    inputs.x_final_m = 163.913;
    inputs.dispersion_y_option = 3;
    inputs.dispersion_z_option = 3;
    const auto step = cteas::puff::step_bookkeeping(inputs);
    require_close(step.distance_begin_m, 1000.0, 1.0e-3, "distance at the start of the step");
    require_close(step.distance_end_m, 6026.0, 1.0e-3, "distance at the end of the step");
    require_close(step.time_begin_s, 3600.0, 1.0e-3, "time at the start of the step");
    require_close(step.time_end_s, 7200.0, 1.0e-3, "time at the end of the step");
    require_close(step.mid_distance_km, 2.513, 1.0e-6, "midpoint distance");
    require_close(step.mid_time_s, 1800.0, 1.0e-3, "midpoint time");
    require_close(step.mean_speed_ms, 1.396, 1.0e-6, "mean transport speed");
    require_close(step.speed_kps, 0.001396, 1.0e-9, "speed in km/s");
    require(!step.calm, "a windy step is not calm");
    require(step.dispersion_y_option == 3 && step.dispersion_z_option == 3,
            "the dispersion options pass through");
    require_close(step.x_final_m, 163.913, 1.0e-6, "the final-rise distance passes through");

    // A calm hour forces the sigma-v/w options and switches off downwash and rise.
    StepBookkeepingInputs calm = inputs;
    calm.wind_speed_ms = 0.3;
    const auto calm_step = cteas::puff::step_bookkeeping(calm);
    require(calm_step.calm, "a sub-threshold wind is calm");
    require(calm_step.dispersion_y_option == 1 && calm_step.dispersion_z_option == 1,
            "calm forces the sigma-v/w dispersion options");
    require(calm_step.downwash_code == 0, "calm switches downwash off");
    require_close(calm_step.x_final_m, 0.0, 0.0, "calm clears the final-rise distance");
    require_close(calm_step.mean_speed_ms, 0.3, 1.0e-6, "the calm speed is still reported");
    require_throw([] {
        StepBookkeepingInputs broken;
        broken.step_seconds = -1.0;
        (void)cteas::puff::step_bookkeeping(broken);
    }, "negative step length");
}

void test_step_update() {
    StepUpdateInputs inputs;
    inputs.height_end_m = 136.158;
    inputs.settling_velocity_ms = 0.01;
    inputs.plume_tilt = 0;
    inputs.step_seconds = 3600.0;
    inputs.step_distance_m = 5026.0;
    inputs.total_distance_m = 1000.0;
    inputs.total_time_s = 3600.0;
    inputs.x_new_km = 513.0;
    inputs.y_new_km = 3533.0;
    // MTILT=0: the settling velocity is read but never applied.
    auto update = cteas::puff::apply_step_update(inputs);
    require_close(update.height_end_m, 136.158, 1.0e-4, "no settling with MTILT=0");
    require_close(update.total_distance_m, 6026.0, 1.0e-3, "total distance after the step");
    require_close(update.total_time_s, 7200.0, 1.0e-3, "total time after the step");
    require_close(update.x_km, 513.0, 1.0e-9, "end-of-step x");
    require_close(update.z_km, 136.158, 1.0e-4, "ZPB is the end-of-step height");
    // MTILT=1: the plume settles and is clipped at the ground.
    inputs.plume_tilt = 1;
    update = cteas::puff::apply_step_update(inputs);
    require_close(update.height_end_m, 136.158 - 0.01 * 3600.0, 1.0e-3, "settling with MTILT=1");
    inputs.settling_velocity_ms = 1.0;
    update = cteas::puff::apply_step_update(inputs);
    require_close(update.height_end_m, 0.0, 0.0, "the settled height is clipped at zero");
    require_throw([] {
        StepUpdateInputs broken;
        broken.plume_tilt = 2;
        (void)cteas::puff::apply_step_update(broken);
    }, "invalid MTILT");
    require_throw([] {
        StepUpdateInputs broken;
        broken.settling_velocity_ms = -1.0;
        (void)cteas::puff::apply_step_update(broken);
    }, "negative settling velocity");
}

void test_setcsig() {
    const SigmaYCurve curve = stub_sigma_y;
    SigmaParameterInputs inputs;
    inputs.dispersion_y_option = 3;
    inputs.dispersion_z_option = 3;
    inputs.urban = 0;
    inputs.mean_speed_ms = 1.396;
    inputs.stability_class = 9;
    inputs.obukhov_length_m = -49.0;
    inputs.brunt_vaisala_s = 0.0;
    inputs.sigma_v_ms = 1.0;
    inputs.sigma_w_ms = 1.0;
    inputs.min_sigma_y_m = 1.0;
    inputs.min_sigma_z_m = 1.0;
    inputs.height_m = 70.8;
    inputs.mixing_height_m = 231.0;
    inputs.cell_x = 25;
    inputs.cell_y = 25;
    inputs.met_domain = 1;
    inputs.heffter_sigma_z = 0;
    inputs.tau_ly = 0;
    inputs.sigma_y_heffter_m = 300.0;
    const auto state = cteas::puff::set_sigma_parameters(inputs, curve);
    require(state.stability_class == 6, "the stability class is conditioned to 6");
    require(state.dispersion_y_option == 3 && state.dispersion_z_option == 3,
            "the dispersion options are stored");
    require(state.urban == 0 && state.cell_x == 25 && state.cell_y == 25 && state.met_domain == 1,
            "the cell indices are stored");
    require_close(state.mean_speed_ms, 1.396, 1.0e-6, "the mean speed is stored");
    require_close(state.obukhov_length_m, -49.0, 1.0e-6, "the Obukhov length is stored");
    require_close(state.min_sigma_y_m, 1.0, 0.0, "the minimum sigma-y is stored");
    require_close(state.sigma_z_heffter_m, 300.0, 0.0, "SZH = SYH");
    // The stub curve gives THFTY = 0.5*SYH and DHFTY = 0.01*SYH.
    require_close(state.heffter_transition_time_s, 150.0, 1.0e-6, "Heffter transition time");
    require_close(state.heffter_transition_distance_km, 3.0, 1.0e-6, "Heffter transition distance");
    require_throw([&] {
        SigmaParameterInputs broken = inputs;
        broken.tau_ly = 1;
        (void)cteas::puff::set_sigma_parameters(broken, curve);
    }, "MTAULY=1 (TAULY not reconstructed)");
    require_throw([&] {
        SigmaParameterInputs broken = inputs;
        broken.stability_class = 0;
        (void)cteas::puff::set_sigma_parameters(broken, curve);
    }, "invalid stability class");
    require_throw([&] {
        (void)cteas::puff::set_sigma_parameters(inputs, SigmaYCurve());
    }, "missing sigma-y curve");
}

} // namespace

int main() {
    try {
        test_step_bookkeeping();
        test_step_update();
        test_setcsig();
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    std::cout << "P7P_STEP_BOOKKEEPING_CONTRACT=PASS\n";
    return 0;
}
