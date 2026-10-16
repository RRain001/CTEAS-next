// P7R terrain-constraint contract tests (CTADJ2 / WALLTRAP): hand-derived closed
// forms and every fail-closed path. Original-routine parity is checked separately
// by tests/p7r_parity_tests.py against the compiled vendor units.
#include "cteas/puff/terrain_constraints.hpp"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using cteas::puff::TerrainLookup;
using cteas::puff::TerrainStrainInputs;
using cteas::puff::WallTrapInputs;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7R TEST FAILURE: " + message);
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

TerrainLookup flat_terrain(double elevation, double relief) {
    TerrainLookup terrain;
    terrain.elevation_msl = [elevation](double, double) { return elevation; };
    terrain.cell_elevation_msl = terrain.elevation_msl;
    terrain.relief = [relief](double, double, int) { return relief; };
    terrain.valley_width = [](double, double, int) { return -1; };
    return terrain;
}

void test_ctadj2() {
    // No slope: the degenerate case returns strain 1 and no height change.
    const auto terrain = flat_terrain(50.0, 100.0);
    TerrainStrainInputs inputs;
    inputs.sigma_ratio = 0.5;
    inputs.puff_height_start_m = 70.0;
    inputs.x_old = 0.1;
    inputs.y_old = 0.5;
    inputs.x_new = 0.9;
    inputs.y_new = 0.5;
    inputs.sigma_z_start_m = 5.0;
    inputs.brunt_vaisala_s = 0.02;
    inputs.wind_speed_ms = 1.4;
    inputs.grid_spacing_m = 0.1;
    auto result = cteas::puff::terrain_strain(inputs, terrain);
    require_close(result.strain, 1.0, 0.0, "no slope gives unit strain");
    require_close(result.puff_height_end_m, 70.0, 0.0, "no slope keeps the puff height");
    require_close(result.fraction_beyond, 0.0, 0.0, "no slope gives zero FRACZ");
    require(!result.upslope, "a flat step is not upslope");

    // Upslope with stratification: the strain exceeds one and FRACZ is bounded.
    TerrainLookup sloped;
    sloped.elevation_msl = [](double x, double) { return x < 0.5 ? 50.0 : 80.0; };
    sloped.cell_elevation_msl = sloped.elevation_msl;
    sloped.relief = [](double, double, int) { return 100.0; };
    sloped.valley_width = [](double, double, int) { return -1; };
    result = cteas::puff::terrain_strain(inputs, sloped);
    require(result.upslope, "a rising step is upslope");
    require(result.strain > 1.0, "upslope strain exceeds one");
    // The vendor does not clamp FRACZ: it is the fraction of the step at which
    // the height change begins or ends, so it can be negative (the dividing
    // streamline lies above the start elevation) or exceed one (the puff height
    // is then reduced by the full rise).
    require(std::isfinite(result.fraction_beyond), "FRACZ is finite");
    require(result.puff_height_end_m <= inputs.puff_height_start_m,
            "the puff height is not raised by the constraint");

    // Without stratification (BVF = 0) the height is unchanged but the strain is
    // still computed from the terrain.
    TerrainStrainInputs neutral = inputs;
    neutral.brunt_vaisala_s = 0.0;
    const auto neutral_result = cteas::puff::terrain_strain(neutral, sloped);
    require_close(neutral_result.puff_height_end_m, inputs.puff_height_start_m, 0.0,
                  "no stratification keeps the puff height");
    require_close(neutral_result.fraction_beyond, 0.0, 0.0, "no stratification gives zero FRACZ");

    // The ratio is conditioned to at most one.
    TerrainStrainInputs big_ratio = inputs;
    big_ratio.sigma_ratio = 4.0;
    const auto conditioned = cteas::puff::terrain_strain(big_ratio, sloped);
    TerrainStrainInputs unit_ratio = inputs;
    unit_ratio.sigma_ratio = 1.0;
    require_close(conditioned.strain, cteas::puff::terrain_strain(unit_ratio, sloped).strain,
                  1.0e-6, "R above one is conditioned to one");

    require_throw([&] {
        TerrainStrainInputs broken = inputs;
        broken.wind_speed_ms = 0.0;
        (void)cteas::puff::terrain_strain(broken, sloped);
    }, "zero wind speed");
    require_throw([&] {
        TerrainLookup incomplete;
        incomplete.elevation_msl = sloped.elevation_msl;
        (void)cteas::puff::terrain_strain(inputs, incomplete);
    }, "missing terrain lookups");
}

void test_walltrap() {
    // No stratification: no trapping at all.
    auto terrain = flat_terrain(50.0, 100.0);
    terrain.valley_width = [](double, double, int) { return 10; };
    WallTrapInputs inputs;
    inputs.sigma_y_begin_m = 500.0;
    inputs.sigma_y_end_m = 300.0;
    inputs.puff_height_m = 25.0;
    inputs.x_begin = 0.1;
    inputs.y_begin = 0.5;
    inputs.x_end = 0.9;
    inputs.y_end = 0.5;
    inputs.brunt_vaisala_s = 0.0;
    inputs.wind_speed_ms = 1.4;
    inputs.valley_layer_thickness_m = 10.0;
    inputs.grid_spacing_m = 100.0;
    inputs.max_valley_levels = 10;
    auto result = cteas::puff::wall_trap(inputs, terrain);
    require(!result.trapped, "a neutral case is not trapped");
    require_close(result.sigma_y_end_m, 300.0, 0.0, "sigma-y is unchanged without stratification");

    // Full trapping when both ends exceed the criterion.
    inputs.brunt_vaisala_s = 0.05;
    inputs.puff_height_m = 10.0;   // below the dividing streamline (ELDS = 100 - 28 = 72)
    inputs.sigma_y_begin_m = 500.0;
    inputs.sigma_y_end_m = 600.0;
    result = cteas::puff::wall_trap(inputs, terrain);
    require(result.trapped, "both ends above RCRIT trap the puff");
    require_close(result.sigma_y_end_m, 500.0, 0.0, "full trapping holds sigma-y at its start value");

    // Partial trapping: the linear crossing of the criterion.
    inputs.sigma_y_begin_m = 500.0;
    inputs.sigma_y_end_m = 300.0;
    result = cteas::puff::wall_trap(inputs, terrain);
    require(result.trapped, "one end above RCRIT traps the puff");
    require_close(result.sigma_y_end_m, 400.0, 1.0e-4,
                  "partial trapping interpolates at the criterion crossing");

    // No trapping when both ends are below the criterion.
    inputs.sigma_y_begin_m = 100.0;
    inputs.sigma_y_end_m = 300.0;
    result = cteas::puff::wall_trap(inputs, terrain);
    require(!result.trapped, "both ends below RCRIT give no trapping");
    require_close(result.sigma_y_end_m, 300.0, 0.0, "sigma-y is unchanged below the criterion");

    // A puff above the dividing streamline is never trapped.
    inputs.sigma_y_begin_m = 500.0;
    inputs.sigma_y_end_m = 600.0;
    inputs.puff_height_m = 1000.0;   // ELPUFF = 50 + 1000 > ELDS = 72
    result = cteas::puff::wall_trap(inputs, terrain);
    require(!result.trapped, "a puff above the dividing streamline is not trapped");

    // A missing valley table (-1) disables trapping.
    TerrainLookup no_valley = terrain;
    no_valley.valley_width = [](double, double, int) { return -1; };
    inputs.puff_height_m = 10.0;
    require(!cteas::puff::wall_trap(inputs, no_valley).trapped,
            "a missing valley width disables trapping");

    require_throw([&] {
        WallTrapInputs broken = inputs;
        broken.wind_speed_ms = 0.0;
        (void)cteas::puff::wall_trap(broken, terrain);
    }, "zero wind speed with stratification");
    require_throw([&] {
        WallTrapInputs broken = inputs;
        broken.max_valley_levels = 0;
        (void)cteas::puff::wall_trap(broken, terrain);
    }, "MXVALZ below one");
}

} // namespace

int main() {
    try {
        test_ctadj2();
        test_walltrap();
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    std::cout << "P7R_TERRAIN_CONSTRAINTS_CONTRACT=PASS\n";
    return 0;
}
