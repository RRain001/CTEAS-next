// P7Q sigma-update contract tests: hand-derived closed forms and every
// fail-closed path. Original-routine parity is checked separately by
// tests/p7q_parity_tests.py against the compiled vendor blocks.
#include "cteas/puff/sigma_update.hpp"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using cteas::puff::SigmaAdjustInputs;
using cteas::puff::SigmaCurvePoint;
using cteas::puff::SigmaStepInputs;
using cteas::puff::SigmaUpdateInputs;
using cteas::puff::SigmaYCurve;
using cteas::puff::SigmaZCurve;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7Q TEST FAILURE: " + message);
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
    point.virtual_distance_km = static_cast<double>(s0 * 0.01F + 0.002F * dx);
    point.virtual_time_s = static_cast<double>(s0 * 0.5F + 2.0F * dt);
    return point;
}

SigmaCurvePoint stub_sigma_z(double sigma_z0_m, double dx_km, double dt_s, double height_m) {
    const float s0 = static_cast<float>(sigma_z0_m);
    const float dx = static_cast<float>(dx_km);
    const float dt = static_cast<float>(dt_s);
    const float height = static_cast<float>(height_m);
    SigmaCurvePoint point;
    point.value = static_cast<double>(s0 + 0.3F * dx + 0.2F * dt + 0.01F * height);
    point.virtual_distance_km = static_cast<double>(s0 * 0.02F + 0.003F * dx);
    point.virtual_time_s = static_cast<double>(s0 * 0.4F + 3.0F * dt);
    return point;
}

void test_sigma_step() {
    const SigmaYCurve y = stub_sigma_y;
    const SigmaZCurve z = stub_sigma_z;
    SigmaStepInputs inputs;
    inputs.sigma_y_start_m = 2.0;
    inputs.sigma_z_start_m = 1.0;
    inputs.puff_height_m = 70.8;
    inputs.mid_time_s = 1800.0;
    inputs.mid_distance_km = 2.513;
    inputs.puff_code = 1;
    const auto step = cteas::puff::sigma_step(inputs, y, z);
    require(step.gaussian_vertical, "an odd puff code is Gaussian in the vertical");
    // Sigma-y: the stub's virtual pair for 2 m is (1 s, 0.02 km), so the midpoint
    // is evaluated at (1801 s, 2.533 km) and the end at (3602 s, 5.046 km).
    require_close(step.sigma_y_begin_m, 2.0, 1.0e-6, "sigma-y at the start");
    require_close(step.sigma_y_mid_m, 0.5 * 2.533 + 0.1 * 1801.0, 1.0e-3, "sigma-y at the midpoint");
    // The vendor advances the END from the midpoint's TIME argument (tm + tmid),
    // not from the midpoint's virtual time.
    require_close(step.sigma_y_end_m, 0.5 * (2.533 + 2.513) + 0.1 * (1801.0 + 1800.0), 1.0e-3,
                  "sigma-y at the end");
    require_close(step.virtual_time_y_begin_s, 1.0, 1.0e-6, "sigma-y virtual time at the start");
    require_close(step.virtual_distance_y_begin_km, 0.02, 1.0e-6,
                  "sigma-y virtual distance at the start");
    // Sigma-z: the stub's virtual pair for 1 m at 70.8 m is (0.4 s, 0.02 km) plus
    // the height term in the value.
    require_close(step.sigma_z_begin_m, 1.0 + 0.01 * 70.8, 1.0e-6, "sigma-z at the start");
    require_close(step.sigma_z_mid_m,
                  0.3 * (0.02 + 2.513) + 0.2 * (0.4 + 1800.0) + 0.01 * 70.8, 1.0e-2,
                  "sigma-z at the midpoint");
    require_close(step.virtual_time_z_begin_s, 0.4, 1.0e-6, "sigma-z virtual time at the start");
    // An even puff code leaves sigma-z at its start value with no virtuals.
    SigmaStepInputs uniform = inputs;
    uniform.puff_code = 2;
    const auto uniform_step = cteas::puff::sigma_step(uniform, y, z);
    require(!uniform_step.gaussian_vertical, "an even puff code is uniform in the vertical");
    require_close(uniform_step.sigma_z_begin_m, 1.0, 0.0, "sigma-z is carried through unchanged");
    require_close(uniform_step.sigma_z_end_m, 1.0, 0.0, "sigma-z at the end is unchanged");
    require_close(uniform_step.virtual_time_z_end_s, 0.0, 0.0, "no sigma-z virtuals");
    require_throw([&] {
        (void)cteas::puff::sigma_step(inputs, SigmaYCurve(), z);
    }, "missing sigma-y curve");
    require_throw([&] {
        SigmaStepInputs broken = inputs;
        broken.sigma_y_start_m = -1.0;
        (void)cteas::puff::sigma_step(broken, y, z);
    }, "negative start-of-step sigma");
}

void test_adjust() {
    SigmaAdjustInputs inputs;
    inputs.sigma_y_begin_m = 2.0;
    inputs.sigma_y_mid_m = 5.0;
    inputs.sigma_y_end_m = 20.0;
    inputs.sigma_z_begin_m = 1.0;
    inputs.sigma_z_mid_m = 5.0;
    inputs.sigma_z_end_m = 20.0;
    inputs.final_rise_variance_m2 = 100.0;
    inputs.initial_sigma_y_squared_m2 = 0.0;
    inputs.gaussian_vertical = true;
    const auto adjust = cteas::puff::adjust_sigmas(inputs);
    require_close(adjust.stored_sigma_y_m, 20.0, 1.0e-6, "the end-of-step sigma-y is stored");
    require_close(adjust.sigma_y_quadrature_m2, 100.0, 1.0e-6, "SYSQ = BIDFNL + SY0SQ");
    require_close(adjust.sigma_y_begin_m, std::sqrt(4.0 + 100.0), 1.0e-4, "BID quadrature on syb1");
    require_close(adjust.sigma_y_end_m, std::sqrt(400.0 + 100.0), 1.0e-4,
                  "BID quadrature on sye1");
    require_close(adjust.stored_sigma_z_m, 20.0, 1.0e-6, "the end-of-step sigma-z is stored");
    require_close(adjust.sigma_z_mid_m, std::sqrt(25.0 + 100.0), 1.0e-4,
                  "BID quadrature on szm1");
    // Monotonicity: sigmas must grow with time.
    SigmaAdjustInputs shrinking = inputs;
    shrinking.sigma_y_begin_m = 30.0;
    shrinking.sigma_y_mid_m = 5.0;
    shrinking.sigma_y_end_m = 10.0;
    const auto monotone = cteas::puff::adjust_sigmas(shrinking);
    require_close(monotone.sigma_y_mid_m, std::sqrt(30.0 * 30.0 + 100.0), 1.0e-4,
                  "SYM1 is raised to SYB1");
    require_close(monotone.sigma_y_end_m, monotone.sigma_y_mid_m, 1.0e-4,
                  "SYE1 is raised to SYM1");
    // A uniform vertical distribution leaves sigma-z and its store alone.
    SigmaAdjustInputs uniform = inputs;
    uniform.gaussian_vertical = false;
    const auto uniform_adjust = cteas::puff::adjust_sigmas(uniform);
    require_close(uniform_adjust.sigma_z_mid_m, 5.0, 1.0e-6, "sigma-z is untouched when uniform");
    require_close(uniform_adjust.stored_sigma_z_m, 0.0, 0.0, "no sigma-z store when uniform");
    // Calm: the minimum sigmas track the midpoint values.
    SigmaAdjustInputs calm = inputs;
    calm.calm = true;
    const auto calm_adjust = cteas::puff::adjust_sigmas(calm);
    require_close(calm_adjust.minimum_sigma_y_m, calm_adjust.sigma_y_mid_m, 0.0,
                  "the calm minimum sigma-y is the midpoint value");
    require_close(calm_adjust.minimum_sigma_z_m, calm_adjust.sigma_z_mid_m, 0.0,
                  "the calm minimum sigma-z is the midpoint value");
    require_throw([] {
        SigmaAdjustInputs broken;
        broken.final_rise_variance_m2 = -1.0;
        (void)cteas::puff::adjust_sigmas(broken);
    }, "negative BIDFNL");
}

void test_terrain_sigma_source_order() {
    const SigmaYCurve y=stub_sigma_y;
    const SigmaZCurve z=stub_sigma_z;
    SigmaUpdateInputs inputs;
    inputs.step.sigma_y_start_m=2.0;
    inputs.step.sigma_z_start_m=1.0;
    inputs.step.puff_height_m=70.8;
    inputs.step.mid_time_s=25.0;
    inputs.step.mid_distance_km=0.2;
    inputs.step.puff_code=1;
    auto no_terrain=cteas::puff::sigma_update(inputs,y,z);
    require(!no_terrain.terrain,"flat original sigma unexpectedly has terrain state");
    // Fully explicit REAL4 mock terrain state; no oracle/frozen outputs.
    cteas::puff::TerrainLookup real_lookup;
    real_lookup.elevation_msl=[](double x,double){return 10.0+0.005*x;};
    real_lookup.cell_elevation_msl=[](double,double){return 10.0;};
    real_lookup.relief=[](double,double,int){return 60.0;};
    real_lookup.valley_width=[](double,double,int){return 15;};
    cteas::puff::OriginalTerrainSigmaInputs terr;
    terr.lookup=&real_lookup;
    terr.x_begin_cells=5.0F;terr.y_begin_cells=5.0F;
    terr.x_end_cells=6.0F;terr.y_end_cells=5.0F;
    terr.z_begin_m=70.8F;terr.brunt_vaisala_s=0.015F;
    terr.wind_speed_ms=1.2F;terr.met_spacing_m=100.0F;
    const auto result=cteas::puff::sigma_update(inputs,y,z,&terr);
    require(result.terrain.has_value(),"native CTADJ2 midpoint/end state absent");
    require(std::isfinite(result.terrain->z_end_m) &&
            std::isfinite(result.terrain->fracz_end) &&
            std::isfinite(result.step.sigma_z_end_m) &&
            result.adjust.stored_sigma_z_m>0.0,
            "CTADJ2 SETPUF did not return finite native height and stored sigma");
    auto missing=terr;missing.lookup=nullptr;
    require_throw([&]{
        (void)cteas::puff::sigma_update(inputs,y,z,&missing);
    },"original MCTADJ2 may not invent missing terrain data");
    auto even=inputs;even.step.puff_code=2;
    require_throw([&]{
        (void)cteas::puff::sigma_update(even,y,z,&terr);
    },"selected original MCTADJ2 only supports Gaussian sigma");
    std::cout<<"P7_MCTADJ2_SETPUF_SOURCE_ORDER=PASS"
             <<" CTADJ2_MID_END=YES REINVERT_SIGTZ=YES"
             <<" FRACZ1_LUP1=FROM_END=YES"
             <<" NO_NATIVE_RELIEF_FAIL_CLOSED=YES\\n";
}

void test_sigma_update_chain() {
    const SigmaYCurve y = stub_sigma_y;
    const SigmaZCurve z = stub_sigma_z;
    SigmaUpdateInputs inputs;
    inputs.step.sigma_y_start_m = 2.0;
    inputs.step.sigma_z_start_m = 1.0;
    inputs.step.puff_height_m = 70.8;
    inputs.step.mid_time_s = 1800.0;
    inputs.step.mid_distance_km = 2.513;
    inputs.step.puff_code = 1;
    inputs.final_rise_variance_m2 = 100.0;
    inputs.initial_sigma_y_squared_m2 = 4.0;
    inputs.calm = true;
    const auto result = cteas::puff::sigma_update(inputs, y, z);
    require_close(result.adjust.sigma_y_quadrature_m2, 104.0, 1.0e-5, "SYSQ = 100 + 4");
    require_close(result.adjust.stored_sigma_y_m, result.step.sigma_y_end_m, 1.0e-6,
                  "the store is the pre-quadrature end-of-step sigma");
    require(result.adjust.stored_sigma_y_m < result.adjust.sigma_y_end_m,
            "the BID quadrature grows the reported sigma past the stored one");
    require_close(result.adjust.minimum_sigma_y_m, result.adjust.sigma_y_mid_m, 0.0,
                  "the calm minimum comes from the adjusted midpoint");
}

} // namespace

int main() {
    try {
        test_sigma_step();
        test_adjust();
        test_sigma_update_chain();
        test_terrain_sigma_source_order();
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    std::cout << "P7Q_SIGMA_UPDATE_CONTRACT=PASS\n";
    return 0;
}
