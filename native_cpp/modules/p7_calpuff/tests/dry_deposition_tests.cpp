// P7F MDRY=1 dry deposition contract tests.
// Hand-derived expectations from the vendor formulas, algorithm invariants and
// fail-closed behaviour. Original-routine parity is checked separately by
// tests/drydep_parity_tests.py against the compiled unmodified vendor VDCOMP.
#include "cteas/puff/control.hpp"
#include "cteas/puff/dry_deposition.hpp"

#include <bit>
#include <cstdint>
#include <cmath>
#include <fstream>
#include <iterator>
#include <limits>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using cteas::puff::DryDepositionEnvironment;
using cteas::puff::DryDepositionMethod;
using cteas::puff::DryDepositionSetup;
using cteas::puff::DryDepositionSpecies;
using cteas::puff::DryDepositionStep;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7F DRY DEPOSITION TEST FAILURE: " + message);
}

void require_close(double observed, double expected, double tolerance, const std::string& what) {
    require(std::abs(observed - expected) <= tolerance,
            what + ": observed " + std::to_string(observed) + " expected " +
                std::to_string(expected) + " tolerance " + std::to_string(tolerance));
}

// The vendor routines compute in REAL*4, so derived parameters are compared
// with a float32-level relative bound instead of an absolute one.
void require_close_relative(double observed, double expected, double relative,
                            const std::string& what) {
    require(std::abs(observed - expected) <= relative * std::max(std::abs(expected), 1.0e-30),
            what + ": observed " + std::to_string(observed) + " expected " +
                std::to_string(expected) + " relative tolerance " + std::to_string(relative));
}

template <typename Callable>
void require_throw(Callable&& callable, const std::string& what) {
    bool threw = false;
    try {
        callable();
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    require(threw, what + " must fail closed");
}

// Real-deck-like control text: the reference values from the Hefei 2022 case.
std::string control_text() {
    return R"(
! MDRY = 1 !
! NZ = 9 !
! ZFACE = 0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000 !
! CSPEC = H-3 !
! CSPEC = HE-3 !
! RCUTR = 30.0 !
! RGR = 10.0 !
! REACTR = 8.0 !
! NINT = 9 !
! IVEG = 1 !
INPUT GROUP: 3a, 3b -- Species list
Subgroup (3a)
!          H-3  =         1,               1,           1,                 0   !
!         HE-3  =         1,               0,           0,                 0   !
!END!
INPUT GROUP: 7 -- Chemical parameters for dry deposition of gases
!          H-3 =      .1509,           1.0,           8.0,                .0,                   .04 !
!END!
)";
}

DryDepositionSetup setup_from(const std::string& text) {
    return cteas::puff::dry_deposition_setup_from_control(text);
}

DryDepositionEnvironment environment(double ustar = 0.3, double monin = -50.0,
                                     double roughness = 0.1, double temperature = 288.0,
                                     double leaf_area = 2.0, double radiation = 300.0,
                                     int vegetation = 1, int land_use = 10) {
    DryDepositionEnvironment value;
    value.friction_velocity_ms = ustar;
    value.monin_obukhov_m = monin;
    value.roughness_m = roughness;
    value.temperature_k = temperature;
    value.leaf_area_index = leaf_area;
    value.shortwave_w_m2 = radiation;
    value.vegetation_state = vegetation;
    value.land_use = land_use;
    return value;
}

DryDepositionStep step(const DryDepositionSetup& setup, const DryDepositionEnvironment& env) {
    return cteas::puff::dry_deposition_step(setup, env, /*lid_height_m=*/500.0,
                                            /*sampling_step_s=*/3600.0, /*mixing_height_m=*/500.0,
                                            /*wstar_ms=*/0.5);
}

void test_original_gaussian_dry_mass() {
    cteas::puff::DryDepositionStep resistance;
    resistance.velocity_ms={0.005,0.0};
    resistance.boundary_ratio={0.8,1.0};
    const std::vector<float> mass={10.0F,7.0F};
    const auto sample=cteas::puff::original_gaussian_dry_mass(
        resistance,1,600.0F,0.001F,mass);
    const float exponent=600.0F*0.001F;
    const float fraction=std::exp(-0.005F*exponent);
    const float after=fraction*10.0F;
    require(sample.mixed_mass_after.size()==2U &&
            sample.fraction_remaining[0]==fraction &&
            sample.mixed_mass_after[0]==after &&
            sample.removed_mass[0]==10.0F-after &&
            sample.mixed_mass_after[1]==7.0F,
            "original Gaussian DRY VCBAR exponential mass update");
    const auto none=cteas::puff::original_gaussian_dry_mass(
        resistance,4,600.0F,0.001F,mass);
    const auto inactive=cteas::puff::original_gaussian_dry_mass(
        resistance,99,600.0F,0.001F,mass);
    require(none.mixed_mass_after==mass &&
            inactive.mixed_mass_after==mass,
            "vendor DRY icode 4/99 skips mass removal");
    const auto slug=cteas::puff::original_gaussian_dry_mass(
        resistance,11,600.0F,0.001F,mass);
    require(slug.mixed_mass_after==sample.mixed_mass_after,
            "vendor Gaussian slug code must preserve DRY exponent semantics");
    require_throw([&]{(void)cteas::puff::original_gaussian_dry_mass(
        resistance,2,600.0F,0.001F,mass);
    },"uniform puff excluded from Gaussian DRY");
    require_throw([&]{(void)cteas::puff::original_gaussian_dry_mass(
        resistance,1,600.0F,-1.0F,mass);
    },"negative VCBAR excluded");
    require_throw([&]{(void)cteas::puff::original_gaussian_dry_mass(
        resistance,1,600.0F,0.001F,{1.0F});
    },"unmatched source species count excluded");
    std::cout<<"P7_NATIVE_ORIGINAL_GAUSSIAN_DRY_MASS=PASS"
             <<" VCBAR_IN_EXPONENT=YES"
             <<" GAUSSIAN_VDPVD=ONE"
             <<" H3_DEPLETED_HE3_UNTOUCHED=YES"
             <<" CODE_4_99_SKIPPED=YES"
             <<" QM_REAL4=YES INTEGRATED_COMP=NOT_YET_ACCEPTED\\n";
}

void test_original_uniform_dry_mass() {
    cteas::puff::DryDepositionStep resistance;
    resistance.velocity_ms={0.005,0.0};
    resistance.boundary_ratio={0.8,1.0};
    resistance.fraction_remaining={0.6,1.0};
    const std::vector<float> mass={10.0F,7.0F};
    const auto uniform=cteas::puff::original_uniform_dry_mass(
        resistance,2,mass);
    require(uniform.mixed_mass_after==std::vector<float>({6.0F,7.0F}) &&
            uniform.removed_mass[0]==4.0F &&
            uniform.removed_mass[1]==0.0F,
            "uniform DRY must apply VDPVD-diffusion mass fraction");
    const auto slug=cteas::puff::original_uniform_dry_mass(
        resistance,16,mass);
    require(slug.mixed_mass_after==uniform.mixed_mass_after,
            "uniform code 16 must follow original ICODE6 DRY branch");
    const auto skip=cteas::puff::original_uniform_dry_mass(
        resistance,4,mass);
    require(skip.mixed_mass_after==mass,
            "original DRY ICODE4 mass must remain unchanged");
    require_throw([&]{
        (void)cteas::puff::original_uniform_dry_mass(resistance,1,mass);
    },"Gaussian code cannot use uniform-only VDPVD exponent");
    std::cout<<"P7_NATIVE_ORIGINAL_UNIFORM_DRY_MASS=PASS"
             <<" VDPVD_FROM_NATIVE_DRYSOURCE=YES"
             <<" H3_DEPLETED_HE3_PRESERVED=YES"
             <<" ICODE4_SKIP=YES\\n";
}

void test_method_validation() {
    require(static_cast<int>(cteas::puff::require_supported_dry_deposition_method(0, "X")) == 0,
            "method 0 accepted");
    require(static_cast<int>(cteas::puff::require_supported_dry_deposition_method(1, "X")) == 1,
            "method 1 accepted");
    require_throw([] { (void)cteas::puff::require_supported_dry_deposition_method(2, "X"); },
                  "method 2 (particle)");
    require_throw([] { (void)cteas::puff::require_supported_dry_deposition_method(3, "X"); },
                  "method 3 (user specified)");
    require_throw([] { (void)cteas::puff::require_supported_dry_deposition_method(4, "X"); },
                  "method 4 (illegal)");
    require_throw([] { (void)cteas::puff::require_supported_dry_deposition_method(-1, "X"); },
                  "negative method");
    std::cout << "P7F_DRYDEP_METHOD_FAIL_CLOSED=PASS\n";
}

void test_setup_from_control() {
    const auto setup = setup_from(control_text());
    require(setup.species.size() == 2U, "two species parsed");
    require(setup.species[0].name == "H-3" && setup.species[1].name == "HE-3", "species names");
    require(setup.species[0].method == DryDepositionMethod::gas_resistance, "H-3 is computed gas");
    require(setup.species[1].method == DryDepositionMethod::none, "HE-3 has no dry removal");
    require(setup.species[0].has_gas_parameters && !setup.species[1].has_gas_parameters,
            "group 7 parameters only for the gas species");
    require(setup.deposited_species == 1, "one deposited species");
    // DRYI: ZREF = min(0.5*(ZFACE1+ZFACE2), 10) = min(10, 10)
    require_close(setup.reference_height_m, 10.0, 1.0e-12, "reference height");
    require_close(setup.reference_cuticle_resistance_s_m, 30.0 * 100.0, 1.0e-9, "RCUTR to s/m");
    require_close(setup.reference_ground_resistance_s_m, 10.0 * 100.0, 1.0e-9, "RGR to s/m");
    require_close(setup.reference_reactivity, 8.0, 1.0e-12, "REACTR");
    // DRYI: pdiff = .1509 cm**2/s -> 1.509e-5 m**2/s, rm = 0 s/cm -> 0 s/m
    require_close_relative(setup.diffusivity_m2_s[0], 1.509e-5, 1.0e-6, "diffusivity to m**2/s");
    require_close_relative(setup.mesophyll_resistance_s_m[0], 0.0, 1.0e-6, "mesophyll resistance");
    // Vendor DRYI L26969 first stores 0.1509 as REAL*4 and only then
    // multiplies by the REAL*4 literal 1.E-4.  A double multiplication
    // rounded once to float gives the adjacent, incorrect binary32 word.
    const float vendor_pdiff=0.1509F*1.0e-4F;
    const float incorrectly_widened=static_cast<float>(0.1509*1.0e-4);
    require(std::bit_cast<std::uint32_t>(vendor_pdiff)==0x377d2b0fU &&
                std::bit_cast<std::uint32_t>(incorrectly_widened)==0x377d2b0eU,
            "DRYI regression fixture must distinguish REAL4 from promoted REAL8");
    require(std::bit_cast<std::uint32_t>(
                static_cast<float>(setup.diffusivity_m2_s[0]))==
                std::bit_cast<std::uint32_t>(vendor_pdiff),
            "DRYI input .1509 must be converted to m2/s in two REAL4 steps");
    std::cout<<"P7F_DRYI_REAL4_DIFFUSIVITY_BITS=PASS H3_PDIFF=0x377d2b0f"
                " DOUBLE_PROMOTION_REJECTED=YES\\n";
    // DRYI: sc = vair/pdiff, rd1 = d1*sc**d2/vk  (vair = 0.15e-4, d1 = 2.0, d2 = 2/3, vk = 0.4)
    const double schmidt = 0.15e-4 / 1.509e-5;
    require_close_relative(setup.deposition_layer_term[0],
                           2.0 * std::pow(schmidt, 0.6666667) / 0.4, 1.0e-6, "RD1");
    // DRYI: rcut = rcutr*reactr/react with react == 8 -> unchanged
    require_close_relative(setup.cuticle_resistance_s_m[0], 3000.0, 1.0e-6, "cuticle resistance");
    require_close_relative(setup.ground_resistance_s_m[0], 1000.0, 1.0e-6, "ground resistance");
    // DRYI: rgw1 = henry/(alphas*d3) = 0.04/(1.0*4.8e-4)
    require_close_relative(setup.water_ground_term_s_m[0], 0.04 / 4.8e-4, 1.0e-6, "water ground term");
    std::cout << "P7F_DRYDEP_SETUP_FROM_CONTROL=PASS"
                 " ZREF_M=10 RD1=" << setup.deposition_layer_term[0] << "\n";
}

void test_setup_fail_closed() {
    require_throw([] { (void)setup_from(control_text() + "\n! MDRY = 0 !"); }, "MDRY=0");
    require_throw([] { (void)setup_from(control_text() + "\n! MDRY = 2 !"); }, "MDRY=2");
    require_throw([] { (void)setup_from(control_text() + "\n! RCUTR = 0. !"); }, "RCUTR=0");
    require_throw([] { (void)setup_from(control_text() + "\n! RGR = -1. !"); }, "negative RGR");
    require_throw([] { (void)setup_from(control_text() + "\n! REACTR = 0. !"); }, "REACTR=0");
    require_throw([] { (void)setup_from(control_text() + "\n! IVEG = 4 !"); }, "IVEG=4");
    require_throw([] { (void)setup_from(control_text() + "\n! NINT = 0 !"); }, "NINT=0");
    // Species-flag violations.
    require_throw([] { (void)setup_from("! MDRY = 1 !\n! ZFACE = 0, 20 !\n! CSPEC = H-3 !\n"
                                         "Subgroup (3a)\n! H-3 = 1, 1, 2, 0 !\n!END!\n"); },
                  "particle method in group 3a");
    require_throw([] { (void)setup_from("! MDRY = 1 !\n! ZFACE = 0, 20 !\n! CSPEC = H-3 !\n"
                                         "Subgroup (3a)\n! H-3 = 1, 1, 3, 0 !\n!END!\n"); },
                  "user-specified method in group 3a");
    require_throw([] { (void)setup_from("! MDRY = 1 !\n! ZFACE = 0, 20 !\n! CSPEC = H-3 !\n"
                                         "Subgroup (3a)\n! H-3 = 1, 1, 9, 0 !\n!END!\n"); },
                  "illegal method value");
    // A gas species without group 7 parameters must fail closed.
    require_throw([] { (void)setup_from("! MDRY = 1 !\n! ZFACE = 0, 20 !\n! CSPEC = H-3 !\n"
                                        "Subgroup (3a)\n! H-3 = 1, 1, 1, 0 !\n!END!\n"
                                        "INPUT GROUP: 7\n!END!\n"); },
                  "missing gas parameters");
    // CSPEC / group 3a mismatch.
    require_throw([] { (void)setup_from("! MDRY = 1 !\n! ZFACE = 0, 20 !\n! CSPEC = H-3 !\n"
                                        "Subgroup (3a)\n! XX-1 = 1, 1, 0, 0 !\n!END!\n"); },
                  "species name mismatch");
    // Illegal gas parameters.
    require_throw([] { (void)setup_from("! MDRY = 1 !\n! ZFACE = 0, 20 !\n! CSPEC = H-3 !\n"
                                        "Subgroup (3a)\n! H-3 = 1, 1, 1, 0 !\n!END!\n"
                                        "INPUT GROUP: 7\n! H-3 = 0., 1., 8., 0., 0.04 !\n!END!\n"); },
                  "zero diffusivity");
    require_throw([] { (void)setup_from("! MDRY = 1 !\n! ZFACE = 0, 20 !\n! CSPEC = H-3 !\n"
                                        "Subgroup (3a)\n! H-3 = 1, 1, 1, 0 !\n!END!\n"
                                        "INPUT GROUP: 7\n! H-3 = .15, 0., 8., 0., 0.04 !\n!END!\n"); },
                  "zero alpha star");
    require_throw([] { (void)setup_from("! MDRY = 1 !\n! ZFACE = 0, 20 !\n! CSPEC = H-3 !\n"
                                        "Subgroup (3a)\n! H-3 = 1, 1, 1, 0 !\n!END!\n"
                                        "INPUT GROUP: 7\n! XX = .15, 1., 8., 0., 0.04 !\n!END!\n"); },
                  "gas row for unknown species");
    require_throw([] { (void)setup_from("! MDRY = 1 !\n! ZFACE = 0, 20 !\n! CSPEC = H-3 !\n"
                                        "Subgroup (3a)\n! H-3 = 1, 1, 0, 0 !\n!END!\n"
                                        "INPUT GROUP: 7\n! H-3 = .15, 1., 8., 0., 0.04 !\n!END!\n"); },
                  "gas row for a non-deposited species");
    std::cout << "P7F_DRYDEP_SETUP_FAIL_CLOSED=PASS\n";
}

void test_resistance_model() {
    const auto setup = setup_from(control_text());
    const auto base = step(setup, environment());
    // HE-3 is not deposited at all.
    require(base.velocity_ms[1] == 0.0 && base.boundary_ratio[1] == 1.0 &&
                base.fraction_remaining[1] == 1.0,
            "non-deposited species must have zero velocity and no removal");
    require(base.velocity_ms[0] > 0.0, "H-3 deposition velocity must be positive");

    // Hand-derived closed form with inactive vegetation (RC = 1/(XLAI/RCUT+1/RG)).
    auto inactive = environment();
    inactive.vegetation_state = 3;
    const auto inactive_step = step(setup, inactive);
    const double ustar = std::max(0.3, 1.0e-5);
    const double zref = 10.0;
    const double ratio = std::min(-zref / -50.0, 1.0);
    const double zmel = std::log(ratio);
    const double psih = std::exp(0.598 + 0.39 * zmel - 0.090 * zmel * zmel);
    const double ra = std::max((std::log(zref / 0.1) - psih) / (0.4 * ustar), 1.0);
    const double rd = 2.0 * std::pow(0.15e-4 / 1.509e-5, 0.6666667) / 0.4 / ustar;
    const double rg = 1000.0;
    const double rcut = 3000.0;
    const double rc = 1.0 / (2.0 / rcut + 1.0 / rg);
    require_close(inactive_step.atmospheric_resistance_s_m, ra, 1.0e-4, "aerodynamic resistance");
    require_close(inactive_step.velocity_ms[0], 1.0 / (ra + rd + rc), 1.0e-6,
                  "inactive-vegetation deposition velocity");
    require_close_relative(inactive_step.psi_heat, psih, 1.0e-6, "psi heat function");

    // Stomatal opening: temperature above 35 C forces the maximum opening,
    // below 10 C the minimum, and in between radiation interpolates.
    auto hot = environment();
    hot.temperature_k = 315.0;
    hot.shortwave_w_m2 = 0.0;
    auto cold = environment();
    cold.temperature_k = 270.0;
    cold.shortwave_w_m2 = 600.0;
    const auto hot_step = step(setup, hot);
    const auto cold_step = step(setup, cold);
    const double pconst = 2.3e-8;
    const double diffusivity = 1.509e-5;
    const double rs_max = pconst / (2.5e-6 * diffusivity);
    const double rs_min = pconst / (0.1e-6 * diffusivity);
    const double rf_max = rs_max;
    const double rf_min = rs_min;
    const double rc_hot = 1.0 / (2.0 / rf_max + 2.0 / rcut + 1.0 / rg);
    const double rc_cold = 1.0 / (2.0 / rf_min + 2.0 / rcut + 1.0 / rg);
    require_close(hot_step.velocity_ms[0], 1.0 / (ra + rd + rc_hot), 1.0e-6, "hot stomata");
    require_close(cold_step.velocity_ms[0], 1.0 / (ra + rd + rc_cold), 1.0e-6, "cold stomata");
    require(hot_step.velocity_ms[0] > cold_step.velocity_ms[0],
            "open stomata must deposit faster than closed stomata");

    // Radiation interpolation between BMIN and BMAX at 600 W/m2 reference.
    auto dark = environment();
    dark.shortwave_w_m2 = 0.0;
    auto bright = environment();
    bright.shortwave_w_m2 = 600.0;
    const auto dark_step = step(setup, dark);
    const auto bright_step = step(setup, bright);
    const double rc_dark = 1.0 / (2.0 / (pconst / (0.1e-6 * diffusivity)) + 2.0 / rcut + 1.0 / rg);
    const double rc_bright = 1.0 / (2.0 / (pconst / (2.5e-6 * diffusivity)) + 2.0 / rcut + 1.0 / rg);
    require_close(dark_step.velocity_ms[0], 1.0 / (ra + rd + rc_dark), 1.0e-6, "dark stomata");
    require_close(bright_step.velocity_ms[0], 1.0 / (ra + rd + rc_bright), 1.0e-6, "bright stomata");
    // Radiation above QSWMAX is clamped.
    auto saturated = environment();
    saturated.shortwave_w_m2 = 1200.0;
    require_close_relative(step(setup, saturated).velocity_ms[0], bright_step.velocity_ms[0], 1.0e-6,
                           "radiation clamp at QSWMAX");

    // Water cells use the wind-driven roughness and the water ground term.
    auto water = environment();
    water.land_use = 550;
    water.u10_ms = 5.0;
    const auto water_step = step(setup, water);
    require(water_step.water_cell, "water cell detected");
    require_close_relative(water_step.effective_roughness_m, 2.0e-6 * std::pow(5.0, 2.5), 1.0e-6,
                           "wind-driven water roughness");
    const double ra_water =
        std::max((std::log(zref / (2.0e-6 * std::pow(5.0, 2.5))) - psih) / (0.4 * ustar), 1.0);
    const double rg_water = (0.04 / (1.0 * 4.8e-4)) / ustar;
    // Temperature 288 K and 300 W/m2 interpolate the stomatal opening between
    // BMIN and BMAX (fr = 300/600).
    const double opening_mid = 2.5e-6 * 0.5 + 0.1e-6 * 0.5;
    const double rf_mid = pconst / (opening_mid * diffusivity);
    const double rc_water = 1.0 / (2.0 / rf_mid + 2.0 / rcut + 1.0 / rg_water);
    require_close_relative(water_step.velocity_ms[0], 1.0 / (ra_water + rd + rc_water), 1.0e-6,
                           "water-cell deposition velocity");
    auto calm_water = environment();
    calm_water.land_use = 550;
    calm_water.u10_ms = 0.0;
    calm_water.v10_ms = 0.0;
    require_close(step(setup, calm_water).effective_roughness_m, 2.0e-6, 1.0e-12,
                  "calm water roughness minimum");

    // Stable and neutral stability branches of the psi function.
    for (const double monin : {-1.0e9, -100.0, -10.0, 0.0, 10.0, 100.0, 100000.0}) {
        const auto variant = step(setup, environment(0.3, monin));
        require(std::isfinite(variant.velocity_ms[0]) && variant.velocity_ms[0] > 0.0,
                "finite deposition velocity for Monin-Obukhov " + std::to_string(monin));
    }
    // u* is floored at USMIN = 1e-5 so the velocity stays finite.
    const auto weak = step(setup, environment(0.0, -50.0));
    require(std::isfinite(weak.velocity_ms[0]) && weak.velocity_ms[0] >= 0.0,
            "u* floor keeps the aerodynamic resistance finite");

    // Higher friction velocity reduces the aerodynamic resistance.
    require(step(setup, environment(0.6, -50.0)).atmospheric_resistance_s_m <
                step(setup, environment(0.3, -50.0)).atmospheric_resistance_s_m,
            "aerodynamic resistance decreases with u*");
    std::cout << "P7F_DRYDEP_RESISTANCE_MODEL=PASS H3_VD=" << base.velocity_ms[0]
              << " RA=" << base.atmospheric_resistance_s_m << "\n";
}

void test_removal_fraction() {
    const auto setup = setup_from(control_text());
    const auto base = step(setup, environment());
    const double lid = 500.0;
    const double mixing = 500.0;
    const double ustar = 0.3;
    const double diffusivity = std::max(0.1 * 0.5 * mixing, 0.01 * ustar * mixing);
    const double depth = std::max(mixing - 10.0, 0.00001);
    const double expected_ratio = diffusivity / (diffusivity + base.velocity_ms[0] * depth);
    require_close_relative(base.boundary_ratio[0], expected_ratio, 1.0e-6, "boundary layer ratio");
    require_close_relative(base.fraction_remaining[0],
                           std::exp(-expected_ratio * base.velocity_ms[0] * 3600.0 / lid), 1.0e-6,
                           "uniform-puff removal fraction");
    require(base.fraction_remaining[0] > 0.0 && base.fraction_remaining[0] < 1.0,
            "removal fraction must be in (0,1)");
    require(base.boundary_diffusivity_m2_s > 0.0, "boundary diffusivity");
    // Neutral/stable: w* = 0 uses CONK1 only.
    const auto neutral = cteas::puff::dry_deposition_step(setup, environment(), lid, 3600.0,
                                                          mixing, /*wstar_ms=*/0.0);
    require_close(neutral.boundary_diffusivity_m2_s, 0.01 * ustar * mixing, 1.0e-9,
                  "neutral boundary diffusivity");
    std::cout << "P7F_DRYDEP_REMOVAL_FRACTION=PASS FRACDRY=" << base.fraction_remaining[0]
              << " DIFFK=" << base.boundary_diffusivity_m2_s << "\n";
}

void test_environment_fail_closed() {
    const auto setup = setup_from(control_text());
    require_throw([&setup] { (void)cteas::puff::dry_deposition_step(setup, environment(), 0.0, 3600.0, 500.0, 0.5); },
                  "zero lid height");
    require_throw([&setup] { (void)cteas::puff::dry_deposition_step(setup, environment(), 500.0, 0.0, 500.0, 0.5); },
                  "zero sampling step");
    require_throw([&setup] { (void)cteas::puff::dry_deposition_step(setup, environment(), 500.0, 3600.0, 0.0, 0.5); },
                  "zero mixing height");
    require_throw([&setup] { (void)cteas::puff::dry_deposition_step(setup, environment(), 500.0, 3600.0, 500.0, -1.0); },
                  "negative w*");
    require_throw([&setup] { (void)cteas::puff::dry_deposition_step(setup, environment(std::nan("")), 500.0, 3600.0, 500.0, 0.5); },
                  "NaN u*");
    auto zero_roughness = environment();
    zero_roughness.roughness_m = 0.0;
    require_throw([&setup, &zero_roughness] { (void)step(setup, zero_roughness); }, "zero roughness");
    auto negative_lai = environment();
    negative_lai.leaf_area_index = -1.0;
    require_throw([&setup, &negative_lai] { (void)step(setup, negative_lai); }, "negative LAI");
    auto bad_temperature = environment();
    bad_temperature.temperature_k = 0.0;
    require_throw([&setup, &bad_temperature] { (void)step(setup, bad_temperature); }, "zero temperature");
    auto bad_vegetation = environment();
    bad_vegetation.vegetation_state = 9;
    require_throw([&setup, &bad_vegetation] { (void)step(setup, bad_vegetation); }, "illegal vegetation state");
    auto infinite_monin = environment();
    infinite_monin.monin_obukhov_m = std::numeric_limits<double>::infinity();
    require_throw([&setup, &infinite_monin] { (void)step(setup, infinite_monin); },
                  "infinite Monin-Obukhov length");
    std::cout << "P7F_DRYDEP_ENVIRONMENT_FAIL_CLOSED=PASS\n";
}

void test_real_deck(const std::string& path) {
    std::ifstream input(path);
    require(bool(input), "cannot read " + path);
    const std::string text((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    const auto audit = cteas::puff::audit_dry_deposition(text);
    require(audit.mdry == 1, "real deck must enable MDRY=1");
    require(audit.gas_species.size() == 1U && audit.gas_species.front() == "H-3",
            "real deck H-3 must use computed gas deposition");
    require(audit.non_deposited_species.size() == 1U && audit.non_deposited_species.front() == "HE-3",
            "real deck HE-3 must have no dry removal");
    require(audit.unsupported_species.empty(), "real deck must not need unsupported methods");
    require_close(audit.reference_cuticle_resistance_s_m, 3000.0, 1.0e-9, "real deck RCUTR");
    require_close(audit.reference_ground_resistance_s_m, 1000.0, 1.0e-9, "real deck RGR");
    require_close(audit.reference_reactivity, 8.0, 1.0e-12, "real deck REACTR");
    require_close(audit.reference_height_m, 10.0, 1.0e-12, "real deck ZREF");
    require(audit.vegetation_state == 1, "real deck IVEG");
    const auto setup = setup_from(text);
    require_close_relative(setup.diffusivity_m2_s[0], 1.509e-5, 1.0e-6, "real deck H-3 diffusivity");
    require_close_relative(setup.deposition_layer_term[0], 4.98, 1.0e-3, "real deck H-3 RD1");
    std::cout << "P7F_REAL_DECK_DRYDEP_AUDIT=PASS MDRY=1 GAS=H-3 NON_DEPOSITED=HE-3 ZREF_M=10"
                 " RD1=" << setup.deposition_layer_term[0] << "\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        test_method_validation();
        test_original_gaussian_dry_mass();
        test_original_uniform_dry_mass();
        test_setup_from_control();
        test_setup_fail_closed();
        test_resistance_model();
        test_removal_fraction();
        test_environment_fail_closed();
        if (argc == 3 && std::string(argv[1]) == "--control") {
            test_real_deck(argv[2]);
        } else if (argc != 1) {
            std::cerr << "Usage: cteas_p7_dry_deposition_tests [--control CONTROL_FILE]\n";
            return 2;
        }
        std::cout << "P7F_DRYDEP_MDRY1_CONTRACT=PASS\n"
                     "P7F_DRYDEP_IS_NOT_A_CONCENTRATION_TEST=true\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 1;
    }
}
