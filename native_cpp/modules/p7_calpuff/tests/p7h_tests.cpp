// P7H vertical coupling (VCOUP / VCBAR / CTADJ) contract tests.
// Hand-derived expectations plus fail-closed behaviour; original-routine parity
// is checked by tests/p7h_parity_tests.py against the compiled vendor units.
#include "cteas/puff/coupling.hpp"
#include "cteas/puff/receptors.hpp"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7H TEST FAILURE: " + message);
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

cteas::puff::VcoupInputs vcoup(int code, double zr, double zs, double sz, double lid,
                               double lid_max) {
    cteas::puff::VcoupInputs inputs;
    inputs.puff_code = code;
    inputs.receptor_height_m = zr;
    inputs.source_height_m = zs;
    inputs.sigma_z_m = sz;
    inputs.lid_height_m = lid;
    inputs.lid_max_m = lid_max;
    return inputs;
}

cteas::puff::PuffSampleState state(double z_begin1, double z_end1, double sigma_begin1,
                                  double sigma_end1) {
    cteas::puff::PuffSampleState value;
    value.puff_code = 1;
    value.z_begin1 = z_begin1;
    value.z_end1 = z_end1;
    value.sigma_z_begin1 = sigma_begin1;
    value.sigma_z_mid = 0.5 * (sigma_begin1 + sigma_end1);
    value.sigma_z_end1 = sigma_end1;
    value.z_begin2 = z_begin1;
    value.z_end2 = z_end1;
    value.sigma_z_begin2 = sigma_begin1;
    value.sigma_z_end2 = sigma_end1;
    return value;
}

void test_vcoup() {
    // Well-mixed codes 2/6 and their slug variants 12/16.
    for (const int code : {2, 6, 12, 16}) {
        require_close(cteas::puff::vertical_coupling(vcoup(code, 10.0, 0.0, 50.0, 100.0, 100.0)),
                      1.0 / 100.0, 1.0e-9, "well-mixed below lid");
        require_close(cteas::puff::vertical_coupling(vcoup(code, 150.0, 0.0, 50.0, 100.0, 200.0)),
                      1.0 / 100.0, 1.0e-9, "well-mixed above lid");
        require_close(cteas::puff::vertical_coupling(vcoup(code, 300.0, 0.0, 50.0, 100.0, 200.0)),
                      0.0, 1.0e-9, "well-mixed above the top of the mass");
    }
    require_close(cteas::puff::vertical_coupling(vcoup(4, 10.0, 10.0, 50.0, 100.0, 100.0)), 0.0,
                  1.0e-12, "above mixed layer and uniform");

    // Gaussian: a receptor far above the lid inside the mass distribution.
    require_close(cteas::puff::vertical_coupling(vcoup(1, 150.0, 50.0, 50.0, 100.0, 200.0)),
                  1.0 / 100.0, 1.0e-9, "elevated receptor inside the distribution");
    require_close(cteas::puff::vertical_coupling(vcoup(1, 250.0, 50.0, 50.0, 100.0, 200.0)), 0.0,
                  1.0e-12, "elevated receptor above the distribution");

    // Gaussian with a source above the lid: the lid is removed entirely.
    const double unlimited =
        cteas::puff::vertical_coupling(vcoup(1, 0.0, 300.0, 50.0, 100.0, 100.0));
    const double expected_unlimited = std::exp(-0.5 * (300.0 / 50.0) * (300.0 / 50.0)) /
                                      (2.5066283 * 50.0);
    require_close(unlimited, expected_unlimited, 1.0e-9, "unlimited mixing above the lid");

    // Sigma-z below SZCUT is screened out.
    require_close(cteas::puff::vertical_coupling(vcoup(1, 0.0, 10.0, 0.005, 100.0, 100.0)), 0.0,
                  1.0e-12, "sigma-z screen");
    // Strong trapping approaches the well-mixed limit 1/hlid.
    const double trapped = cteas::puff::vertical_coupling(vcoup(1, 0.0, 10.0, 200.0, 100.0, 100.0));
    require(trapped > 0.0 && trapped < 1.0 / 100.0 * 2.0, "strong trapping stays bounded");

    // Ground-level coupling decreases with height.
    const double low = cteas::puff::vertical_coupling(vcoup(1, 0.0, 20.0, 50.0, 1000.0, 1000.0));
    const double high = cteas::puff::vertical_coupling(vcoup(1, 0.0, 200.0, 50.0, 1000.0, 1000.0));
    require(low > high && high > 0.0, "coupling decreases with source height");

    require_throw([] { (void)cteas::puff::vertical_coupling(vcoup(17, 0.0, 10.0, 50.0, 100.0, 100.0)); },
                  "illegal puff code");
    require_throw([] { (void)cteas::puff::vertical_coupling(vcoup(1, 0.0, 10.0, 50.0, 0.0, 0.0)); },
                  "zero lid height");
    std::cout << "P7H_VCOUP_CONTRACT=PASS\n";
}

void test_vcbar() {
    // With identical begin/end heights and sigmas the puff average equals the
    // single-point coupling value.
    const auto puff_state = state(50.0, 50.0, 40.0, 40.0);
    cteas::puff::VcbarInputs puff;
    puff.state = puff_state;
    puff.lid_height_m = 1000.0;
    puff.terrain_adjustment = 2;
    const double single = cteas::puff::vertical_coupling(vcoup(1, 0.0, 50.0, 40.0, 1000.0, 1000.0));
    require_close(cteas::puff::vertical_coupling_bar(puff), single, 1.0e-9,
                  "puff average equals the single sample");

    // Slug weighting: four samples of the same state also collapse to the value.
    cteas::puff::VcbarInputs slug = puff;
    slug.slug = true;
    require_close(cteas::puff::vertical_coupling_bar(slug), single, 1.0e-9,
                  "slug average equals the single sample");

    // Plume tilt: heights follow ZFINAL - t*VSETL.
    cteas::puff::VcbarInputs tilted = puff;
    tilted.plume_tilt = 1;
    tilted.state.final_height_m = 150.0;
    tilted.state.settling_velocity_ms = 0.1;
    tilted.state.time_begin1 = 100.0;
    tilted.state.time_end1 = 200.0;
    tilted.state.sigma_z_begin1 = 40.0;
    tilted.state.sigma_z_end1 = 40.0;
    // Begin = ZFINAL - t_begin*VSETL, end = ZFINAL - t_end*VSETL, mid = their mean.
    const double begin_height = 150.0 - 100.0 * 0.1;
    const double end_height = 150.0 - 200.0 * 0.1;
    const double mid_height = 0.5 * (begin_height + end_height);
    const double expected =
        (1.0 / 3.0) *
        (cteas::puff::vertical_coupling(vcoup(1, 0.0, mid_height, 40.0, 1000.0, 1000.0)) +
         cteas::puff::vertical_coupling(vcoup(1, 0.0, begin_height, 40.0, 1000.0, 1000.0)) +
         cteas::puff::vertical_coupling(vcoup(1, 0.0, end_height, 40.0, 1000.0, 1000.0)));
    require_close(cteas::puff::vertical_coupling_bar(tilted), expected, 1.0e-9, "plume tilt heights");

    // Terrain adjustment needs a lookup and then follows CTADJ.
    cteas::puff::VcbarInputs terrain = puff;
    terrain.terrain_adjustment = 1;
    terrain.grid_spacing_m = 100.0;
    terrain.stack_height_m = 70.8;
    terrain.stack_base_elevation_m = 40.0;
    require_throw([terrain] { (void)cteas::puff::vertical_coupling_bar(terrain); },
                  "MCTADJ=1 without a terrain lookup");
    terrain.terrain = [](double, double) { return 60.0; };
    const double adjusted = cteas::puff::vertical_coupling_bar(terrain);
    const double expected_height =
        std::max(0.0, 50.0 - std::min(60.0 - 40.0, 70.8));
    const double expected_terrain =
        cteas::puff::vertical_coupling(vcoup(1, 0.0, expected_height, 40.0, 1000.0, 1000.0));
    require_close(adjusted, expected_terrain, 1.0e-9, "MCTADJ=1 with a terrain lookup");

    // CTADJ directly: ISC treatment (MCTADJ=1) and the partial correction (3).
    require_close(cteas::puff::terrain_adjustment(60.0, 50.0, 70.8, 40.0, 1.0, 1), 30.0, 1.0e-9,
                  "CTADJ MCTADJ=1");
    require_close(cteas::puff::terrain_adjustment(60.0, 50.0, 70.8, 40.0, 0.5, 3), 40.0, 1.0e-9,
                  "CTADJ MCTADJ=3");
    require_throw([] { (void)cteas::puff::terrain_adjustment(60.0, 50.0, 70.8, 40.0, 1.0, 2); },
                  "CTADJ with MCTADJ=2");

    require_throw([puff] {
        auto calm = puff;
        calm.calm = true;
        (void)cteas::puff::vertical_coupling_bar(calm);
    }, "LCALM=true");
    require_throw([puff] {
        auto bad = puff;
        bad.lid_height_m = 0.0;
        (void)cteas::puff::vertical_coupling_bar(bad);
    }, "zero lid height");
    require_throw([puff] {
        auto bad = puff;
        bad.state.sigma_z_begin1 = -1.0;
        (void)cteas::puff::vertical_coupling_bar(bad);
    }, "negative sigma-z");
    require_throw([puff] {
        auto bad = puff;
        bad.terrain_adjustment = 4;
        (void)cteas::puff::vertical_coupling_bar(bad);
    }, "illegal MCTADJ");
    require_throw([puff] {
        auto bad = puff;
        bad.plume_tilt = 2;
        (void)cteas::puff::vertical_coupling_bar(bad);
    }, "illegal MTILT");
    std::cout << "P7H_VCBAR_CONTRACT=PASS\n";
}

void test_accumulation_wiring() {
    // The coupling-aware accumulation uses VCBAR for F1: with the same inputs
    // the explicit-F1 call and the coupled call must agree.
    cteas::puff::SamplingIntegrals integrals;
    integrals.i1 = 2.0;
    integrals.i2 = 1.0;
    cteas::puff::ReceptorAccumulationInputs inputs;
    inputs.mass_old = 10.0;
    inputs.mass_new = 8.0;
    inputs.sigma_y_at_receptor_m = 50.0;
    inputs.time_fraction = 1.0;
    cteas::puff::VcbarInputs coupling;
    coupling.state = state(50.0, 50.0, 40.0, 40.0);
    coupling.lid_height_m = 1000.0;
    coupling.terrain_adjustment = 2;
    const double factor = cteas::puff::vertical_coupling_bar(coupling);
    auto explicit_inputs = inputs;
    explicit_inputs.vertical_factor = factor;
    require_close(cteas::puff::receptor_concentration_increment_with_coupling(integrals, inputs,
                                                                             coupling),
                  cteas::puff::receptor_concentration_increment(integrals, explicit_inputs), 1.0e-9,
                  "coupled accumulation matches the explicit F1 path");
    std::cout << "P7H_ACCUMULATION_WIRING=PASS VCBAR_1_PER_M=" << factor << "\n";
}

} // namespace

int main() {
    try {
        test_vcoup();
        test_vcbar();
        test_accumulation_wiring();
        std::cout << "P7H_VERTICAL_COUPLING_CONTRACT=PASS\n"
                     "P7H_IS_NOT_A_CONCENTRATION_PARITY_TEST=true\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 1;
    }
}
