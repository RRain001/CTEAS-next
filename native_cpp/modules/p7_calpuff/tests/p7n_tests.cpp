// P7N plume-rise contract tests: hand-derived closed forms and every
// fail-closed path. Original-routine parity is checked separately by
// tests/p7n_parity_tests.py against the compiled vendor units.
#include "cteas/puff/plume_rise.hpp"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using cteas::puff::BuoyantRiseInputs;
using cteas::puff::FinalRiseInputs;
using cteas::puff::MomentumRiseInputs;
using cteas::puff::PartialPenetrationInputs;
using cteas::puff::PlumeRiseState;
using cteas::puff::StackFluxInputs;
using cteas::puff::StackTipInputs;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7N TEST FAILURE: " + message);
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

void test_stktip() {
    StackTipInputs inputs;
    inputs.stack_height_m = 70.8;
    inputs.diameter_m = 1.6;
    inputs.exit_velocity_ms = 17.26;
    inputs.stack_wind_speed_ms = 1.4;
    inputs.momentum_flux = 300.0;
    // Exit velocity above 1.5*WS: no downwash.
    require_close(cteas::puff::stack_tip_downwash(inputs), 0.0, 0.0, "no downwash above 1.5*WS");
    // Zero momentum flux: the maximum reduction, capped by the stack height.
    inputs.momentum_flux = 0.0;
    require_close(cteas::puff::stack_tip_downwash(inputs), 4.8, 1.0e-6, "zero momentum flux");
    // Below 1.5*WS: 2*DIAM*(1.5 - VEXIT/WS).
    inputs.momentum_flux = 300.0;
    inputs.exit_velocity_ms = 1.0;
    require_close(cteas::puff::stack_tip_downwash(inputs), 3.2 * (1.5 - 1.0 / 1.4), 1.0e-6,
                  "downwash below 1.5*WS");
    // The reduction is capped by the physical stack height.
    inputs.stack_height_m = 1.0;
    require_close(cteas::puff::stack_tip_downwash(inputs), 1.0, 0.0, "capped by the stack height");
    require_throw([] {
        StackTipInputs broken;
        broken.stack_height_m = -1.0;
        (void)cteas::puff::stack_tip_downwash(broken);
    }, "negative stack height");
}

void test_fluxes() {
    StackFluxInputs inputs;
    inputs.diameter_m = 1.6;
    inputs.exit_velocity_ms = 17.26;
    inputs.stack_temperature_k = 298.15;
    inputs.ambient_temperature_k = 279.15;
    inputs.temperature_excess_k = 19.0;
    inputs.momentum_flux_factor = 1.0;
    const auto fluxes = cteas::puff::stack_fluxes(inputs);
    const float buoyancy = (2.4516625F * (1.6F * 1.6F) * 17.26F) / 298.15F * 19.0F;
    const float momentum =
        (0.25F * ((17.26F * 1.6F) * (17.26F * 1.6F)) * 279.15F) / 298.15F;
    require_close(fluxes.buoyancy_m4s3, buoyancy, 1.0e-3, "buoyancy flux closed form");
    require_close(fluxes.momentum_m4s2, momentum, 1.0e-3, "momentum flux closed form");
    // FMFAC below 0.5 zeroes the momentum flux.
    inputs.momentum_flux_factor = 0.0;
    require_close(cteas::puff::stack_fluxes(inputs).momentum_m4s2, 0.0, 0.0,
                  "momentum flux factor below 0.5");
    require_throw([] {
        StackFluxInputs broken;
        broken.stack_temperature_k = 0.0;
        (void)cteas::puff::stack_fluxes(broken);
    }, "zero stack temperature");
}

void test_prfin() {
    FinalRiseInputs inputs;
    inputs.exit_velocity_ms = 17.26;
    inputs.diameter_m = 1.6;
    inputs.momentum_flux = 300.0;
    inputs.buoyancy_flux = 1200.0;
    inputs.stack_wind_speed_ms = 1.4;
    inputs.stability_class = 4;
    inputs.sqrt_stability_s = 0.02;
    const auto neutral = cteas::puff::final_plume_rise(inputs);
    require_close(neutral.x_final_buoyancy_m, 119.0 * std::pow(1200.0, 0.4), 1.0e-2,
                  "XFINB for FB >= 55");
    require_close(neutral.z_final_buoyancy_m, 38.71 * std::pow(1200.0, 0.6) / 1.4, 1.0e-2,
                  "ZFINB for FB >= 55");
    require_close(neutral.z_final_momentum_m, 3.0 * 1.6 * 17.26 / 1.4, 1.0e-2, "ZFINM neutral");
    require_close(neutral.z_final_m, std::max(neutral.z_final_buoyancy_m,
                                              neutral.z_final_momentum_m),
                  0.0, "ZFIN is the larger final rise");
    // Small buoyancy flux uses the ISC2 low-FB pair.
    inputs.buoyancy_flux = 30.0;
    const auto small = cteas::puff::final_plume_rise(inputs);
    require_close(small.x_final_buoyancy_m, 49.0 * std::pow(30.0, 0.625), 1.0e-2,
                  "XFINB for 0 < FB < 55");
    require_close(small.z_final_buoyancy_m, 21.425 * std::pow(30.0, 0.75) / 1.4, 1.0e-2,
                  "ZFINB for 0 < FB < 55");
    // Stable conditions use the bent-over/vertical pair.
    inputs.buoyancy_flux = 1200.0;
    inputs.stability_class = 5;
    const auto stable = cteas::puff::final_plume_rise(inputs);
    require_close(stable.x_final_buoyancy_m, 2.0715 * 1.4 / 0.02, 1.0e-3, "XFINB stable");
    const double bent_over = 2.6 * std::pow(1200.0 / (1.4 * 0.02 * 0.02), 0.333333);
    const double vertical = 4.0 * std::pow(1200.0, 0.25) / std::pow(0.02 * 0.02, 0.375);
    require_close(stable.z_final_buoyancy_m, std::min(bent_over, vertical), 1.0e-2,
                  "ZFINB stable is the lower of the two plume equations");
    require_close(stable.x_final_momentum_m, 1.57080 * 1.4 / 0.02, 1.0e-4, "XFINM stable");
    // Calm conditions (WSSTK < 1.0) set the distances to zero.
    inputs.stack_wind_speed_ms = 0.5;
    inputs.stability_class = 4;
    const auto calm = cteas::puff::final_plume_rise(inputs);
    require_close(calm.x_final_buoyancy_m, 0.0, 0.0, "XFINB calm");
    require_close(calm.x_final_momentum_m, 0.0, 0.0, "XFINM calm");
    require_close(calm.z_final_momentum_m, 3.0 * 1.6 * 17.26 / 1.0, 1.0e-3, "ZFINM calm");
    // Zero momentum flux zeroes the momentum distance and height explicitly.
    inputs.stack_wind_speed_ms = 1.4;
    inputs.momentum_flux = 0.0;
    const auto no_momentum = cteas::puff::final_plume_rise(inputs);
    require_close(no_momentum.x_final_momentum_m, 0.0, 0.0, "XFINM zeroed for FM = 0");
    require_close(no_momentum.z_final_momentum_m, 0.0, 0.0, "ZFINM zeroed for FM = 0");
    require_throw([] {
        FinalRiseInputs broken;
        broken.stability_class = 7;
        (void)cteas::puff::final_plume_rise(broken);
    }, "stability class outside 1-6");
}

void test_prm_prb() {
    MomentumRiseInputs momentum;
    momentum.diameter_m = 1.6;
    momentum.exit_velocity_ms = 17.26;
    momentum.momentum_flux = 300.0;
    momentum.stack_wind_speed_ms = 1.4;
    momentum.stability_class = 4;
    momentum.sqrt_stability_s = 0.02;
    momentum.x_m = 500.0;
    momentum.x_final_momentum_m = 3000.0;
    momentum.z_final_momentum_m = 12.0;
    const double beta_j = 0.333333 + 1.4 / 17.26;
    const double expected =
        std::pow(3.0 * 300.0 * 500.0 / (beta_j * beta_j * 1.4 * 1.4), 0.333333);
    require_close(cteas::puff::transitional_momentum_rise(momentum),
                  std::min(expected, 3.0 * 1.6 * 17.26 / 1.4), 1.0e-3,
                  "transitional momentum rise closed form");
    // Beyond the final distance the final rise is returned.
    momentum.x_m = 5000.0;
    require_close(cteas::puff::transitional_momentum_rise(momentum), 12.0, 0.0,
                  "momentum rise beyond XFINM");
    // Stable conditions use the sine term.
    momentum.x_m = 500.0;
    momentum.stability_class = 5;
    const double stable_expected = std::pow(
        3.0 * 300.0 * std::sin(0.02 * 500.0 / 1.4) / (beta_j * beta_j * 1.4 * 0.02), 0.333333);
    require_close(cteas::puff::transitional_momentum_rise(momentum),
                  std::min(stable_expected, 3.0 * 1.6 * 17.26 / 1.4), 1.0e-3,
                  "stable momentum rise closed form");
    // Zero exit velocity, zero flux or zero distance give no momentum rise.
    momentum.stability_class = 4;
    momentum.exit_velocity_ms = 0.0;
    require_close(cteas::puff::transitional_momentum_rise(momentum), 0.0, 0.0,
                  "zero exit velocity");
    momentum.exit_velocity_ms = 17.26;
    momentum.x_m = 0.0;
    require_close(cteas::puff::transitional_momentum_rise(momentum), 0.0, 0.0, "zero distance");

    BuoyantRiseInputs buoyant;
    buoyant.buoyancy_flux = 1200.0;
    buoyant.stack_wind_speed_ms = 1.4;
    buoyant.x_m = 500.0;
    buoyant.x_final_buoyancy_m = 4000.0;
    buoyant.z_final_buoyancy_m = 20.0;
    const double buoyant_expected =
        std::min(1.6 * std::pow(1200.0 * 500.0 * 500.0, 0.333333) / 1.4, 20.0);
    require_close(cteas::puff::transitional_buoyant_rise(buoyant), buoyant_expected, 1.0e-3,
                  "transitional buoyant rise closed form");
    buoyant.x_m = 10000.0;
    require_close(cteas::puff::transitional_buoyant_rise(buoyant), 20.0, 0.0,
                  "buoyant rise beyond XFINB");
    buoyant.buoyancy_flux = 0.0;
    require_close(cteas::puff::transitional_buoyant_rise(buoyant), 0.0, 0.0, "zero buoyancy flux");
}

void test_prfpp() {
    PartialPenetrationInputs inputs;
    inputs.final_rise_m = 30.0;
    inputs.buoyancy_flux = 1200.0;
    inputs.stack_wind_speed_ms = 1.4;
    inputs.stack_height_m = 70.8;
    inputs.mixing_height_m = 231.0;
    inputs.ambient_temperature_k = 279.15;
    inputs.inversion_gradient_k_per_m = 0.02;
    inputs.inversion_jump_k = 0.6;
    // ZFIN below 0.67*(HMIX-HS): no modification.
    const auto unmodified = cteas::puff::partial_penetration_rise(inputs);
    require_close(unmodified.final_rise_m, 30.0, 0.0, "no modification below rise0");
    require_close(unmodified.mass_fraction_mixed, 1.0, 0.0, "all mass in the mixed layer");
    require_close(unmodified.max_height_m, 231.0, 1.0e-6, "HMAX with rise2 = ZI");
    // Stack top above the mixed layer: no mass below.
    inputs.mixing_height_m = 50.0;
    const auto above = cteas::puff::partial_penetration_rise(inputs);
    require_close(above.mass_fraction_mixed, 0.0, 0.0, "stack above the mixed layer");
    const double s_aloft = 9.80665 * 0.02 / 279.15;
    // PRFPP always returns min(ZFIN, RISE1), so the input rise caps the result.
    require_close(above.final_rise_m,
                  std::min(30.0, 2.6 * std::pow(1200.0 / (1.4 * s_aloft), 0.3333333)), 1.0e-3,
                  "stable rise equation above the mixed layer");
    // The partial-penetration branch with a bounded fraction.
    inputs.mixing_height_m = 231.0;
    inputs.final_rise_m = 200.0;
    const auto penetrating = cteas::puff::partial_penetration_rise(inputs);
    require(penetrating.mass_fraction_mixed >= 0.0 && penetrating.mass_fraction_mixed <= 1.0,
            "mass fraction in [0,1]");
    require(penetrating.final_rise_m <= 200.0, "the revised final rise never exceeds ZFIN");
    require_throw([] {
        PartialPenetrationInputs broken;
        broken.ambient_temperature_k = 0.0;
        (void)cteas::puff::partial_penetration_rise(broken);
    }, "zero ambient temperature");
}

PlumeRiseState rise_state() {
    PlumeRiseState state;
    state.source_type = 1;
    state.downwash_code = 0;
    state.met_period = 1;
    state.rise_method = 1;
    state.shear_flag = 0;
    state.x_m = 1000.0;
    state.final_rise_m = 200.0;
    state.full_final_rise_m = 200.0;
    state.stack_height_m = 70.8;
    state.diameter_m = 1.6;
    state.exit_velocity_ms = 17.26;
    state.stack_wind_speed_ms = 1.4;
    state.stability_class = 4;
    state.sqrt_stability_s = 0.02;
    state.momentum_flux = 300.0;
    state.buoyancy_flux = 1200.0;
    state.x_final_momentum_m = 3000.0;
    state.z_final_momentum_m = 12.0;
    state.x_final_buoyancy_m = 4000.0;
    state.z_final_buoyancy_m = 60.0;
    state.stack_tip_downwash_m = 2.0;
    return state;
}

void test_grise() {
    const auto state = rise_state();
    const auto result = cteas::puff::gradual_plume_height(state);
    MomentumRiseInputs momentum;
    momentum.diameter_m = state.diameter_m;
    momentum.exit_velocity_ms = state.exit_velocity_ms;
    momentum.momentum_flux = state.momentum_flux;
    momentum.stack_wind_speed_ms = state.stack_wind_speed_ms;
    momentum.stability_class = state.stability_class;
    momentum.sqrt_stability_s = state.sqrt_stability_s;
    momentum.x_m = state.x_m;
    momentum.x_final_momentum_m = state.x_final_momentum_m;
    momentum.z_final_momentum_m = state.z_final_momentum_m;
    BuoyantRiseInputs buoyant;
    buoyant.buoyancy_flux = state.buoyancy_flux;
    buoyant.stack_wind_speed_ms = state.stack_wind_speed_ms;
    buoyant.x_m = state.x_m;
    buoyant.x_final_buoyancy_m = state.x_final_buoyancy_m;
    buoyant.z_final_buoyancy_m = state.z_final_buoyancy_m;
    const double rise = std::max(cteas::puff::transitional_momentum_rise(momentum),
                                 cteas::puff::transitional_buoyant_rise(buoyant));
    // The kernel is REAL*4, so the closed form is compared at single precision.
    require_close(result.height_m, state.stack_height_m + rise - state.stack_tip_downwash_m,
                  1.0e-4, "GRISE height is stack + rise - stack-tip downwash");
    require_close(result.rise_fraction, rise / state.full_final_rise_m, 1.0e-6,
                  "GRISE rise fraction");

    // Method 0 (PRIME cavity plume): no rise, the stored final height is used.
    PlumeRiseState cavity = state;
    cavity.downwash_code = 4;
    const auto cavity_result = cteas::puff::gradual_plume_height(cavity);
    require_close(cavity_result.height_m, cavity.final_rise_m, 0.0, "cavity plume height");
    require_close(cavity_result.rise_fraction, 1.0, 0.0, "cavity rise fraction stays one");

    // A zero final rise keeps the rise fraction at one.
    PlumeRiseState no_full_rise = state;
    no_full_rise.full_final_rise_m = 0.0;
    require_close(cteas::puff::gradual_plume_height(no_full_rise).rise_fraction, 1.0, 0.0,
                  "rise fraction with ZFRISE = 0");

    // The stack-tip downwash cannot push the plume below the ground.
    PlumeRiseState grounded = state;
    grounded.stack_tip_downwash_m = 1.0e6;
    require_close(cteas::puff::gradual_plume_height(grounded).height_m, 0.0, 0.0,
                  "plume height is clipped at zero");

    require_throw([] {
        PlumeRiseState broken = rise_state();
        broken.shear_flag = 1;
        (void)cteas::puff::gradual_plume_height(broken);
    }, "MSHEAR=1 (PRSHEAR not reconstructed)");
    require_throw([] {
        PlumeRiseState broken = rise_state();
        broken.downwash_code = 3;
        (void)cteas::puff::gradual_plume_height(broken);
    }, "PRIME tabulated rise");
    require_throw([] {
        PlumeRiseState broken = rise_state();
        broken.downwash_code = 2;
        (void)cteas::puff::gradual_plume_height(broken);
    }, "Schulman-Scire rise");
    require_throw([] {
        PlumeRiseState broken = rise_state();
        broken.rise_method = 2;
        (void)cteas::puff::gradual_plume_height(broken);
    }, "numerical rise (MRISE=2)");
    require_throw([] {
        PlumeRiseState broken = rise_state();
        broken.source_type = 4;
        (void)cteas::puff::gradual_plume_height(broken);
    }, "area source rise");
    require_throw([] {
        PlumeRiseState broken = rise_state();
        broken.downwash_code = 9;
        (void)cteas::puff::gradual_plume_height(broken);
    }, "invalid IDW0");
    require_throw([] {
        PlumeRiseState broken = rise_state();
        broken.met_period = 0;
        (void)cteas::puff::gradual_plume_height(broken);
    }, "invalid met period");
}

} // namespace

int main() {
    try {
        test_stktip();
        test_fluxes();
        test_prfin();
        test_prm_prb();
        test_prfpp();
        test_grise();
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    std::cout << "P7N_PLUME_RISE_CONTRACT=PASS\n";
    return 0;
}
