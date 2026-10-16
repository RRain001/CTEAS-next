// P7O release-scheduler contract tests: hand-derived closed forms and every
// fail-closed path. Original-routine parity is checked separately by
// tests/p7o_parity_tests.py against the compiled vendor units.
#include "cteas/puff/release.hpp"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using cteas::puff::InjectionInputs;
using cteas::puff::NewPuffInputs;
using cteas::puff::ReleaseCadenceInputs;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7O TEST FAILURE: " + message);
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

void test_cadence() {
    ReleaseCadenceInputs inputs;
    inputs.wind_speed_ms = 1.396;
    inputs.emission_interval = 1.0;
    inputs.max_puffs = 99;
    inputs.hour_seconds = 3600.0;
    // NPUFFS = INT(WS*XTMP1) + 1, DT = DHR/NPUFFS.
    const auto cadence = cteas::puff::release_cadence(inputs);
    require(cadence.puff_count == 2, "one puff per unit of travel plus one");
    require_close(cadence.emission_duration_s, 1800.0, 1.0e-6, "emission duration");
    require(cadence.new_puffs == cadence.puff_count, "one release set per source");
    // A calm hour still releases one puff per hour.
    inputs.wind_speed_ms = 0.1;
    require(cteas::puff::release_cadence(inputs).puff_count == 1, "calm hour releases one puff");
    // MXNEW caps the count.
    inputs.wind_speed_ms = 10.0;
    inputs.max_puffs = 3;
    const auto capped = cteas::puff::release_cadence(inputs);
    require(capped.puff_count == 3, "MXNEW caps the puff count");
    require_close(capped.emission_duration_s, 1200.0, 1.0e-6, "capped emission duration");
    // The emission interval scales the count.
    inputs.max_puffs = 99;
    inputs.emission_interval = 0.5;
    require(cteas::puff::release_cadence(inputs).puff_count == 6, "interval scales the count");
    require_throw([] {
        ReleaseCadenceInputs broken;
        broken.max_puffs = 0;
        (void)cteas::puff::release_cadence(broken);
    }, "MXNEW below one");
    require_throw([] {
        ReleaseCadenceInputs broken;
        broken.hour_seconds = 0.0;
        (void)cteas::puff::release_cadence(broken);
    }, "zero-length emission hour");
}

void test_inject() {
    InjectionInputs inputs;
    inputs.species_count = 2;
    inputs.emission_duration_s = 1800.0;
    inputs.effective_height_m = 136.158;
    inputs.max_layer_height_m = 231.0;
    inputs.mixing_height_m = 230.977;
    inputs.mass_fraction_mixed = 1.0;
    inputs.stability_class = 4;
    inputs.gaussian_distribution = 1;
    inputs.emission_rate = {8.34e5, 0.0};
    // Within the surface layer: all mass in the mixed layer, Gaussian code 1.
    auto result = cteas::puff::inject_emissions(inputs);
    require(result.puff_code == 1, "Gaussian puff within the mixed layer has code 1");
    require_close(result.mixed_layer_mass[0], 8.34e5 * 1800.0, 1.5e3, "mixed-layer mass");
    require_close(result.above_layer_mass[0], 0.0, 0.0, "no mass above the lid");
    require_close(result.unlimited_mixing_height_m, 230.977, 1.0e-3, "ZIMAX within the layer");
    // Partial penetration splits the mass by FMIX and uses code 5.
    inputs.mass_fraction_mixed = 0.25;
    inputs.max_layer_height_m = 400.0;
    result = cteas::puff::inject_emissions(inputs);
    require(result.puff_code == 5, "Gaussian partial penetration has code 5");
    require_close(result.mixed_layer_mass[0], 0.25 * 8.34e5 * 1800.0, 4.0e2, "FMIX of the mass");
    require_close(result.above_layer_mass[0], 0.75 * 8.34e5 * 1800.0, 1.2e3, "remainder above");
    // Above the mixed layer in a stable regime: unlimited mixing.
    inputs.mass_fraction_mixed = 1.0;
    inputs.effective_height_m = 400.0;
    inputs.stability_class = 5;
    result = cteas::puff::inject_emissions(inputs);
    require(result.puff_code == 1, "stable above-lid Gaussian has code 1");
    require_close(result.unlimited_mixing_height_m, 1.0e4, 0.0, "unlimited mixing height");
    require_close(result.above_layer_mass[0], 0.0, 0.0, "stable case keeps the mass mixed");
    // Above the mixed layer in a neutral regime: all mass above.
    inputs.stability_class = 4;
    result = cteas::puff::inject_emissions(inputs);
    require(result.puff_code == 3, "neutral above-lid Gaussian has code 3");
    require_close(result.mixed_layer_mass[0], 0.0, 0.0, "no mass in the mixed layer");
    require_close(result.above_layer_mass[0], 8.34e5 * 1800.0, 1.5e3, "all mass above");
    // Uniform (MGAUSS=0) variants use codes 2/4/6.
    inputs.gaussian_distribution = 0;
    inputs.effective_height_m = 136.158;
    require(cteas::puff::inject_emissions(inputs).puff_code == 2, "uniform mixed layer has code 2");
    inputs.effective_height_m = 400.0;
    require(cteas::puff::inject_emissions(inputs).puff_code == 4, "uniform above has code 4");
    inputs.mass_fraction_mixed = 0.5;
    require(cteas::puff::inject_emissions(inputs).puff_code == 6,
            "uniform partial penetration has code 6");
    // The step index shifts the code (slug forms).
    inputs.step_index = 10;
    require(cteas::puff::inject_emissions(inputs).puff_code == 16, "slug step index shifts the code");
    require_throw([] {
        InjectionInputs broken;
        broken.species_count = 1;
        broken.emission_rate = {};
        (void)cteas::puff::inject_emissions(broken);
    }, "missing emission rate");
    require_throw([] {
        InjectionInputs broken;
        broken.species_count = 1;
        broken.emission_rate = {1.0};
        broken.stability_class = 0;
        (void)cteas::puff::inject_emissions(broken);
    }, "invalid stability class");
}

void test_new_puff_state() {
    NewPuffInputs inputs;
    inputs.source_x_km = 513.385;
    inputs.source_y_km = 3533.769;
    inputs.base_elevation_m = 0.0;
    inputs.sigma_y_source_m = 1.0;
    inputs.sigma_z_source_m = 1.0;
    inputs.effective_height_m = 136.158;
    inputs.x_final_m = 163.913;
    inputs.final_rise_variance_m2 = 100.0;
    inputs.buoyancy_flux = 6.9035;
    inputs.momentum_flux = 178.51;
    inputs.x_final_buoyancy_m = 163.913;
    inputs.x_final_momentum_m = 163.913;
    inputs.z_final_buoyancy_m = 65.358;
    inputs.z_final_momentum_m = 65.358;
    inputs.stack_tip_downwash_m = 0.0;
    inputs.stack_height_m = 70.8;
    inputs.exit_velocity_ms = 17.26;
    inputs.diameter_m = 1.6;
    inputs.emission_duration_s = 1800.0;
    inputs.stack_wind_speed_ms = 1.396;
    inputs.stability_class = 4;
    inputs.sqrt_stability_s = 0.0;
    inputs.urban = 0;
    inputs.sigma_v_ms = 1.0;
    inputs.sigma_w_ms = 1.0;
    inputs.obukhov_length_m = -49.0;
    inputs.plume_path_exponent = 0.5;
    inputs.downwash_code = 0;
    inputs.building_height_m = 0.0;
    inputs.building_width_m = 0.0;
    inputs.effective_height2_m = 0.0;
    inputs.streamline_height_m = 0.0;
    inputs.wake_radius_m = 0.0;
    inputs.wake_xshift_m = 0.0;
    inputs.initial_sigma_y_m = 1.0;
    inputs.initial_sigma_z_m = 1.0;
    inputs.release_index = 1;
    inputs.source_index = 1;
    inputs.source_type = 1;
    const auto state = cteas::puff::new_puff_state(inputs);
    // The original unqualified COMMON /PUFF/ scalar is REAL*4. A double
    // diagnostic must report the promoted *stored float*, not the double
    // original input literal.
    const auto real4 = [](double value) {
        return static_cast<double>(static_cast<float>(value));
    };
    require_close(state.x_km, real4(513.385), 0.0, "release XPT1GRD REAL4");
    require_close(state.y_km, real4(3533.769), 0.0, "release YPT1GRD REAL4");
    require(state.x_km != inputs.source_x_km && state.y_km != inputs.source_y_km,
            "REAL4 COMMON x/y must not retain double-literal precision");
    require_close(state.tibl_height_m, -1.0, 0.0, "TIBL height is disabled at release");
    require_close(state.final_height_m, real4(136.158), 0.0,
                  "release height is the REAL4 effective height");
    require_close(state.exit_velocity_ms, real4(17.26), 0.0, "exit velocity stored as REAL4");
    require_close(state.buoyancy_flux, real4(6.9035), 0.0, "buoyancy flux stored as REAL4");
    require_close(state.height_begin_m, state.final_height_m, 0.0, "ZPB = HEFF");
    require_close(state.height_end_m, state.final_height_m, 0.0, "ZPE = HEFF");
    require(state.split_flag == 1, "ISPLIT starts at one");
    require_close(state.wind_ratio, 1.0, 0.0, "vector/scalar wind ratio starts at one");
    require_close(state.sigma_y0_m, inputs.sigma_y_source_m, 0.0, "SY0 = SYSRC");
    require_close(state.source_sigma_z_m, inputs.initial_sigma_z_m, 0.0, "SZSRC0 = SZINI");
    require(state.release_index == 1 && state.source_index == 1 && state.source_type == 1,
            "puff identity is carried");
    require_throw([] {
        NewPuffInputs broken;
        broken.source_type = 0;
        (void)cteas::puff::new_puff_state(broken);
    }, "invalid source type");
}

void test_age_rule() {
    // A puff released during the current step starts at age 0 and grows by TSAMP.
    require_close(cteas::puff::advance_puff_age(0.0, 3600.0), 3600.0, 1.0e-9, "first step age");
    require_close(cteas::puff::advance_puff_age(3600.0, 3600.0), 7200.0, 1.0e-9, "second step age");
    require_close(cteas::puff::advance_puff_age(0.0, 0.0), 0.0, 0.0, "zero-length step");
    require_throw([] { (void)cteas::puff::advance_puff_age(-1.0, 60.0); }, "negative age");
    require_throw([] { (void)cteas::puff::advance_puff_age(0.0, -1.0); }, "negative step");
}

} // namespace

int main() {
    try {
        test_cadence();
        test_inject();
        test_new_puff_state();
        test_age_rule();
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    std::cout << "P7O_RELEASE_SCHEDULER_CONTRACT=PASS\n";
    return 0;
}
