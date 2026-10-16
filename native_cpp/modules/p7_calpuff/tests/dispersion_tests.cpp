// P7D MDISP=3 dispersion coefficient contract tests.
// Hand-derived expectations from the vendor formulas, algorithm invariants and
// fail-closed behaviour. Original-source parity is checked separately by
// tests/sigma_fortran_parity_tests.py against the unmodified vendor routines.
#include "cteas/puff/control.hpp"
#include "cteas/puff/dispersion.hpp"

#include <cmath>
#include <cstddef>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using cteas::puff::ControlFile;
using cteas::puff::DispersionEnvironment;
using cteas::puff::DispersionIncrement;
using cteas::puff::DispersionSetup;
using cteas::puff::DispersionStep;
using cteas::puff::SigmaCurves;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7D DISPERSION TEST FAILURE: " + message);
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
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    require(threw, what + " must fail closed");
}

DispersionEnvironment environment(int stability, bool urban, double speed, double heffter_sigma_y) {
    DispersionEnvironment value;
    value.stability_class = stability;
    value.urban = urban;
    value.transport_speed_ms = speed;
    value.sigma_y_heffter_m = heffter_sigma_y;
    return value;
}

DispersionStep sigma_y(const SigmaCurves& curves, double sigy0, double dx_km, double dt_s) {
    DispersionIncrement increment;
    increment.dx_km = dx_km;
    increment.dt_s = dt_s;
    return curves.sigma_y(sigy0, increment);
}

DispersionStep sigma_z(const SigmaCurves& curves, double sigz0, double zht, double dx_km) {
    DispersionIncrement increment;
    increment.dx_km = dx_km;
    increment.dt_s = dx_km * 1000.0 / curves.environment().transport_speed_ms;
    return curves.sigma_z(sigz0, zht, increment);
}

const char* control_text() {
    return R"(
! MDISP = 3 !
! MDISP2 = 3 !
! MTURBVW = 3 !
! MTAULY = 0 !
! MHFTSZ = 0 !
! MROUGH = 0 !
! AVET = 60. !
! PGTIME = 60. !
! SYTDEP = 5.5E02 !
)";
}

void test_option_validation() {
    require(static_cast<int>(cteas::puff::require_supported_dispersion_option(3)) == 3,
            "MDISP=3 must be accepted");
    for (const int unsupported : {0, 1, 2, 4, 5, -1}) {
        require_throw([unsupported] { (void)cteas::puff::require_supported_dispersion_option(unsupported); },
                      "MDISP=" + std::to_string(unsupported));
    }
    std::cout << "P7D_DISPERSION_OPTION_FAIL_CLOSED=PASS\n";
}

void test_environment_validation() {
    const SigmaCurves baseline(environment(4, false, 3.0, 550.0));
    require(baseline.heffter_transition_time_y_s() > 0.0, "THFTY must be positive");
    require(!baseline.stability_class_conditioned(), "class 4 must not be conditioned");

    require_throw([] { (void)SigmaCurves(environment(0, false, 3.0, 550.0)); }, "stability 0");
    require_throw([] { (void)SigmaCurves(environment(-1, false, 3.0, 550.0)); }, "negative stability");
    require_throw([] { (void)SigmaCurves(environment(4, false, 0.0, 550.0)); }, "zero transport speed");
    require_throw([] { (void)SigmaCurves(environment(4, false, -3.0, 550.0)); }, "negative speed");
    require_throw([] { (void)SigmaCurves(environment(4, false, 3.0, 0.0)); }, "zero SYH");
    DispersionEnvironment heffter_z = environment(4, false, 3.0, 550.0);
    heffter_z.heffter_sigma_z = true;
    require_throw([heffter_z] { (void)SigmaCurves(heffter_z); }, "MHFTSZ=1");
    DispersionEnvironment bad_averaging = environment(4, false, 3.0, 550.0);
    bad_averaging.averaging_factor = 0.0;
    require_throw([bad_averaging] { (void)SigmaCurves(bad_averaging); }, "zero averaging factor");
    DispersionEnvironment bad_roughness = environment(4, false, 3.0, 550.0);
    bad_roughness.sigma_y_roughness = -1.0;
    require_throw([bad_roughness] { (void)SigmaCurves(bad_roughness); }, "negative roughness factor");

    // The vendor SETCSIG conditions a stability class above 6 to 6.
    const SigmaCurves conditioned(environment(7, false, 3.0, 550.0));
    require(conditioned.stability_class_conditioned(), "class 7 must be conditioned");
    require(conditioned.environment().stability_class == 6, "class 7 must become 6");
    const auto high = sigma_y(conditioned, 0.0, 1.0, 0.0);
    const auto reference = sigma_y(SigmaCurves(environment(6, false, 3.0, 550.0)), 0.0, 1.0, 0.0);
    require(high.sigma_y_m == reference.sigma_y_m, "conditioned class must match class 6");

    require_throw([&baseline] { (void)sigma_y(baseline, -1.0, 0.0, 0.0); }, "negative sigma-y0");
    require_throw([&baseline] { (void)sigma_z(baseline, std::nan(""), 0.0, 1.0); }, "NaN sigma-z0");
    require_throw([&baseline] { (void)sigma_y(baseline, 0.0, std::nan(""), 0.0); },
                  "NaN distance increment");
    std::cout << "P7D_DISPERSION_ENVIRONMENT_FAIL_CLOSED=PASS\n";
}

void test_increment_screening() {
    const SigmaCurves curves(environment(4, false, 3.0, 550.0));
    const auto zero = sigma_y(curves, 0.0, 10.0, 0.0);
    const auto reset = sigma_y(curves, 0.0, 10.0, -0.005);
    require(reset.y_increment_reset, "small negative dt must be reported as reset");
    require(reset.sigma_y_m == zero.sigma_y_m, "small negative dt must equal the zero increment");
    require_throw([&curves] { (void)sigma_y(curves, 0.0, 10.0, -2.0); }, "dt below the halt threshold");
    const auto dx_reset = sigma_y(curves, 0.0, -0.0005, 0.0);
    require(dx_reset.y_increment_reset, "small negative dx must be reported as reset");
    require(dx_reset.sigma_y_m == 0.0, "dx reset keeps the start-of-step sigma");
    require_throw([&curves] { (void)sigma_y(curves, 0.0, -0.002, 0.0); },
                  "dx below the halt threshold");
    const auto z_zero = sigma_z(curves, 100.0, 0.0, 0.0);
    const auto z_reset = sigma_z(curves, 100.0, 0.0, -0.0005);
    require(z_reset.z_increment_reset && z_reset.sigma_z_m == z_zero.sigma_z_m,
            "sigma-z reset must match the zero increment");
    std::cout << "P7D_DISPERSION_INCREMENT_SCREENING=PASS\n";
}

void test_hand_derived_values() {
    // Class C is a single PG segment (AZRUR=61.141, BZRUR=0.91465), so the
    // rural sigma-z is closed form; sigma-y uses th = 0.017453293*C.
    const SigmaCurves rural_c(environment(3, false, 3.0, 550.0));
    const auto y = sigma_y(rural_c, 0.0, 1.0, 0.0);
    const double theta = 0.017453293 * 12.5;
    require_close(y.sigma_y_m, 465.11628 * std::tan(theta), 5.0e-3,
                  "class C rural sigma-y at 1 km");
    const auto z = sigma_z(rural_c, 0.0, 0.0, 1.0);
    require_close(z.sigma_z_m, 61.141, 5.0e-3, "class C rural sigma-z at 1 km");

    const auto z_10 = sigma_z(rural_c, 0.0, 0.0, 10.0);
    require_close(z_10.sigma_z_m, 61.141 * std::pow(10.0, 0.91465), 0.05,
                  "class C rural sigma-z at 10 km");

    // Urban class C: sigma-y = 0.22*xm/sqrt(1+4e-4*xm), sigma-z = 0.20*xm.
    const SigmaCurves urban_c(environment(3, true, 3.0, 550.0));
    const auto uy = sigma_y(urban_c, 0.0, 1.0, 0.0);
    require_close(uy.sigma_y_m, 0.22 * 1000.0 / std::sqrt(1.0 + 4.0e-4 * 1000.0), 5.0e-3,
                  "class C urban sigma-y at 1 km");
    const auto uz = sigma_z(urban_c, 0.0, 0.0, 1.0);
    require_close(uz.sigma_z_m, 200.0, 5.0e-3, "class C urban sigma-z at 1 km");

    // Urban class D: sigma-z = 0.14*xm/sqrt(1+3e-4*xm).
    const SigmaCurves urban_d(environment(4, true, 3.0, 550.0));
    const auto uz_d = sigma_z(urban_d, 0.0, 0.0, 1.0);
    require_close(uz_d.sigma_z_m, 0.14 * 1000.0 / std::sqrt(1.0 + 3.0e-4 * 1000.0), 5.0e-3,
                  "class D urban sigma-z at 1 km");
    const auto uy_d = sigma_y(urban_d, 0.0, 1.0, 0.0);
    require_close(uy_d.sigma_y_m, 0.16 * 1000.0 / std::sqrt(1.0 + 4.0e-4 * 1000.0), 5.0e-3,
                  "class D urban sigma-y at 1 km");

    // Growth in distance for every stability class, rural and urban. The ISC
    // urban sigma-z saturates at its 5000 m cap, so only non-decreasing growth
    // is required there.
    for (int stability = 1; stability <= 6; ++stability) {
        for (const bool urban : {false, true}) {
            const SigmaCurves curves(environment(stability, urban, 3.0, 550.0));
            double previous_y = 0.0;
            double previous_z = 0.0;
            for (double distance = 0.01; distance <= 200.0; distance *= 1.7) {
                const auto y_step = sigma_y(curves, 0.0, distance, 0.0);
                const auto z_step = sigma_z(curves, 0.0, 0.0, distance);
                require(y_step.sigma_y_m > previous_y, "sigma-y must grow with distance");
                if (urban) {
                    require(z_step.sigma_z_m >= previous_z, "urban sigma-z must not decrease");
                    require(z_step.sigma_z_m <= 5000.0, "urban sigma-z must respect the ISC cap");
                } else {
                    require(z_step.sigma_z_m > previous_z, "rural sigma-z must grow with distance");
                }
                previous_y = y_step.sigma_y_m;
                previous_z = z_step.sigma_z_m;
            }
        }
    }

    // ISC urban sigma-z is capped at 5000 m (class A grows into the cap first).
    const SigmaCurves urban_a(environment(1, true, 3.0, 550.0));
    const auto capped = sigma_z(urban_a, 0.0, 0.0, 200.0);
    require(capped.sigma_z_m == 5000.0 && capped.urban_sigma_z_capped,
            "urban sigma-z must be held at the 5000 m cap");
    const auto above_cap = sigma_z(urban_a, 6000.0, 0.0, 1.0);
    require(above_cap.sigma_z_m == 6000.0 && above_cap.urban_sigma_z_capped,
            "initial sigma-z above the cap must be returned unchanged");
    std::cout << "P7D_DISPERSION_HAND_DERIVED_VALUES=PASS\n";
}

void test_pseudo_distance_and_heffter() {
    const SigmaCurves curves(environment(4, false, 3.0, 550.0));
    // The rural pseudo-distance inversion must satisfy the curve it solves.
    const double target = 250.0;
    const auto initial = sigma_y(curves, target, 0.0, 0.0);
    require_close(initial.sigma_y_m, target, 1.0e-6, "start-of-step sigma-y is returned");
    const auto grown = sigma_y(curves, 0.0, initial.virtual_distance_y_km, 0.0);
    require_close(grown.sigma_y_m, target, target * 1.0e-4,
                  "pseudo-distance must reproduce the initial sigma-y");
    require(initial.virtual_time_y_s > 0.0, "pseudo-distance must give a virtual time");

    // Heffter growth beyond SYH is linear in travel time.
    const double transition = curves.heffter_transition_time_y_s();
    const double dt = transition + 3600.0;
    const auto heffter = sigma_y(curves, 0.0, dt * 0.003, dt);
    require(heffter.heffter_y_active, "Heffter growth must be reported");
    const double expected = 0.5 * (dt + (550.0 / 0.5 - transition));
    require_close(heffter.sigma_y_m, expected, 1.0e-3, "Heffter sigma-y");
    require(heffter.sigma_y_m > 550.0, "Heffter sigma-y must exceed SYH");

    // A start-of-step sigma above SYH continues on the Heffter curve.
    const auto beyond = sigma_y(curves, 900.0, 5.0, 1000.0);
    require(beyond.heffter_y_active, "sigma above SYH must use Heffter growth");
    require_close(beyond.sigma_y_m, 900.0 + 0.5 * 1000.0, 1.0e-3, "Heffter growth above SYH");
    std::cout << "P7D_DISPERSION_PSEUDO_DISTANCE_AND_HEFFTER=PASS\n";
}

void test_roughness_adjustment() {
    const auto adjustment = cteas::puff::roughness_adjustment(0.1);
    const double b_term = 0.0777 + 0.0215 * std::log(0.1);
    require_close(adjustment.sigma_z_b_term, b_term, 1.0e-6, "BZ0TRM");
    require_close(adjustment.sigma_y_factor, std::pow(0.1 / 0.03, 0.2), 1.0e-6, "YZ0FAC");
    require_close(adjustment.sigma_z_a_factor,
                  std::pow(1000.0, b_term) * 1.585 * std::pow(0.1, 0.1301), 1.0e-6, "AZ0FAC");
    require_throw([] { (void)cteas::puff::roughness_adjustment(0.0); }, "z0 = 0");
    require_throw([] { (void)cteas::puff::roughness_adjustment(-0.03); }, "negative z0");

    // Roughness-adjusted class C rural sigma-z must use A' = A*AZ0FAC and
    // B' = B-BZ0TRM; sigma-y uses YZ0FAC.
    DispersionEnvironment adjusted = environment(3, false, 3.0, 550.0);
    adjusted.sigma_y_roughness = adjustment.sigma_y_factor;
    adjusted.sigma_z_a_roughness = adjustment.sigma_z_a_factor;
    adjusted.sigma_z_b_term = adjustment.sigma_z_b_term;
    const SigmaCurves curves(adjusted);
    const auto z = sigma_z(curves, 0.0, 0.0, 1.0);
    const double expected_z = 61.141 * adjustment.sigma_z_a_factor *
                              std::pow(1.0, 0.91465 - adjustment.sigma_z_b_term);
    require_close(z.sigma_z_m, expected_z, 5.0e-3, "roughness-adjusted rural sigma-z");
    const auto y = sigma_y(curves, 0.0, 1.0, 0.0);
    const double theta = 0.017453293 * 12.5;
    require_close(y.sigma_y_m, adjustment.sigma_y_factor * 465.11628 * std::tan(theta), 5.0e-3,
                  "roughness-adjusted rural sigma-y");

    // The default BZ0TRM of -1000 disables the adjustment.
    DispersionEnvironment plain = environment(3, false, 3.0, 550.0);
    plain.sigma_z_a_roughness = adjustment.sigma_z_a_factor;
    const auto plain_z = sigma_z(SigmaCurves(plain), 0.0, 0.0, 1.0);
    require_close(plain_z.sigma_z_m, 61.141, 5.0e-3, "disabled roughness adjustment");
    std::cout << "P7D_DISPERSION_ROUGHNESS_ADJUSTMENT=PASS\n";
}

void test_control_audit() {
    const auto control = ControlFile::parse(control_text());
    const auto audit = cteas::puff::audit_dispersion_options(control);
    require(audit.mdisp == 3 && audit.mdisp2 == 3 && audit.mturbvw == 3, "audited option values");
    require(audit.mtauly == 0 && audit.mhftsz == 0 && audit.mrough == 0, "audited flags");
    require(audit.avet_minutes == 60.0 && audit.pgtime_minutes == 60.0 && audit.sytdep_m == 550.0,
            "audited dispersion timings");
    require(!audit.mdisp2_effective && !audit.mturbvw_effective && !audit.mtauly_effective,
            "turbulence options are not effective for MDISP=3");
    const auto setup = cteas::puff::dispersion_setup_from_control(control);
    require(setup.mdisp == 3 && setup.sigma_y_heffter_m == 550.0 && setup.averaging_factor == 1.0,
            "MDISP=3 setup values");
    const auto environment_value = cteas::puff::dispersion_environment(setup, 4, false, 3.0);
    require(environment_value.sigma_z_b_term == -1000.0, "MROUGH=0 keeps the adjustment disabled");

    // Vendor BLOCK DATA defaults apply when a key is absent.
    const auto defaults = cteas::puff::audit_dispersion_options(ControlFile::parse("! MDISP = 3 !"));
    require(defaults.sytdep_m == 550.0 && defaults.avet_minutes == 60.0 &&
                defaults.pgtime_minutes == 60.0 && defaults.mhftsz == 0 && defaults.mrough == 0,
            "vendor default dispersion option values");
    require(defaults.mdisp2_effective == false, "defaults are not effective for MDISP=3");

    require_throw([] { (void)cteas::puff::dispersion_setup_from_control(ControlFile::parse("! MDISP = 1 !")); },
                  "MDISP=1");
    require_throw([] { (void)cteas::puff::dispersion_setup_from_control(ControlFile::parse("! MDISP = 5 !")); },
                  "MDISP=5");
    require_throw([] {
        (void)cteas::puff::dispersion_setup_from_control(ControlFile::parse("! MDISP = 3 !\n! MROUGH = 1 !"));
    }, "MROUGH=1");
    require_throw([] {
        (void)cteas::puff::dispersion_setup_from_control(ControlFile::parse("! MDISP = 3 !\n! MHFTSZ = 1 !"));
    }, "MHFTSZ=1");
    require_throw([] {
        (void)cteas::puff::dispersion_setup_from_control(ControlFile::parse("! MDISP = 3 !\n! AVET = 0. !"));
    }, "AVET=0");
    require_throw([] {
        (void)cteas::puff::dispersion_setup_from_control(ControlFile::parse("! MDISP = 3 !\n! SYTDEP = -1. !"));
    }, "SYTDEP<0");
    require_throw([] {
        (void)cteas::puff::dispersion_setup_from_control(ControlFile::parse("! MDISP = 3 !\n! MROUGH = 2 !"));
    }, "MROUGH=2");
    std::cout << "P7D_DISPERSION_CONTROL_AUDIT=PASS\n";
}

void test_averaging_factor() {
    const auto control = ControlFile::parse("! MDISP = 3 !\n! AVET = 180. !\n! PGTIME = 60. !");
    const auto setup = cteas::puff::dispersion_setup_from_control(control);
    const double expected = std::pow(3.0, 0.2);
    require_close(setup.averaging_factor, expected, 1.0e-6, "averaging factor (AVET/PGTIME)**0.2");
    const SigmaCurves curves(cteas::puff::dispersion_environment(setup, 3, false, 3.0));
    const auto adjusted = sigma_y(curves, 0.0, 1.0, 0.0);
    const SigmaCurves plain(environment(3, false, 3.0, 550.0));
    const auto reference = sigma_y(plain, 0.0, 1.0, 0.0);
    require_close(adjusted.sigma_y_m, reference.sigma_y_m * expected, 5.0e-3,
                  "sigma-y scales with the averaging factor");
    std::cout << "P7D_DISPERSION_AVERAGING_FACTOR=PASS\n";
}

} // namespace

int main() {
    try {
        test_option_validation();
        test_environment_validation();
        test_increment_screening();
        test_hand_derived_values();
        test_pseudo_distance_and_heffter();
        test_roughness_adjustment();
        test_control_audit();
        test_averaging_factor();
        std::cout << "P7D_DISPERSION_MDISP3_CONTRACT=PASS\n"
                     "P7D_DISPERSION_IS_NOT_A_CONCENTRATION_TEST=true\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 1;
    }
}
