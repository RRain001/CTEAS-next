// P7S terrain-state contract tests (TERAVG / TRELIEF / GETELEV): hand-derived
// closed forms and every fail-closed path. Original-routine parity is checked
// separately by tests/p7s_parity_tests.py against the compiled vendor units.
#include "cteas/puff/terrain_relief.hpp"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using cteas::puff::ElevationCell;
using cteas::puff::InterpolatedElevationInputs;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7S TEST FAILURE: " + message);
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

ElevationCell flat(double value, int nx) {
    return [value, nx](int i, int j) {
        if (i < 1 || i > nx || j < 1) throw std::runtime_error("out of range");
        return value;
    };
}

void test_teravg() {
    // A flat grid averages to its own value in every orientation.
    const auto cell = flat(100.0, 5);
    require_close(cteas::puff::terrain_strip_average(3, 3, 3, 5, 5, 5, cell), 100.0, 1.0e-6,
                  "N/S sector over a flat grid");
    require_close(cteas::puff::terrain_strip_average(3, 3, 5, 3, 5, 5, cell), 100.0, 1.0e-6,
                  "E/W sector over a flat grid");
    require_close(cteas::puff::terrain_strip_average(2, 2, 4, 4, 5, 5, cell), 100.0, 1.0e-6,
                  "NE/SW sector over a flat grid");
    require_close(cteas::puff::terrain_strip_average(4, 4, 2, 2, 5, 5, cell), 100.0, 1.0e-6,
                  "NE/SW sector (reversed) over a flat grid");
    require_close(cteas::puff::terrain_strip_average(2, 4, 4, 2, 5, 5, cell), 100.0, 1.0e-6,
                  "SE/NW sector over a flat grid");
    // A N/S sector at the same row is the single cell.
    require_close(cteas::puff::terrain_strip_average(3, 3, 3, 3, 5, 5, cell), 100.0, 1.0e-6,
                  "a degenerate sector averages one cell");
    // A ramp: the N/S strip at row 5 covers three cells (idel = 2*0.4142 = 0).
    const ElevationCell ramp = [](int i, int j) { return static_cast<double>(10 * i + j); };
    const double expected = (10.0 * 3.0 + 5.0);
    require_close(cteas::puff::terrain_strip_average(3, 3, 3, 5, 5, 5, ramp), expected, 1.0e-6,
                  "N/S strip on a ramp");
    // (1,1) -> (3,2) is neither an axis nor a diagonal, so the vendor's TERAVG
    // has no branch for it; the port refuses instead of returning a stale value.
    require_throw([&] {
        (void)cteas::puff::terrain_strip_average(1, 1, 3, 2, 5, 5, cell);
    }, "a direction that is not one of the four orientations");
    require_throw([&] {
        (void)cteas::puff::terrain_strip_average(0, 1, 3, 5, 5, 5, cell);
    }, "sector origin outside the domain");
}

void test_trelief() {
    // A flat grid has zero relief in every orientation and the peak equals the
    // cell elevation.
    const auto cell = flat(50.0, 4);
    const auto relief = cteas::puff::terrain_relief(4, 4, cell);
    require(relief.nx == 4 && relief.ny == 4, "the relief grid keeps its shape");
    for (int corner = 1; corner <= 4; ++corner) {
        for (int i = 1; i <= 4; ++i) {
            for (int j = 1; j <= 4; ++j) {
                require_close(relief.at(corner, i, j), 0.0, 0.0, "flat terrain has zero relief");
            }
        }
    }
    require_close(relief.at(5, 2, 2), 50.0, 0.0, "the peak of flat terrain is the elevation");

    // A monotone ramp: the E/W relief at an interior cell is the two-sided rise.
    const ElevationCell ramp = [](int i, int) { return static_cast<double>(100 * i); };
    const auto ramp_relief = cteas::puff::terrain_relief(4, 4, ramp);
    // At (2,2) the walk east accumulates 100+100 = 200 (cells 3 and 4) and the
    // walk west accumulates 100 (cell 1); rplus = 300, rminus = 100 -> 300.
    require_close(ramp_relief.at(3, 2, 2), 300.0, 1.0e-4, "E/W relief on a ramp");
    require_close(ramp_relief.at(5, 2, 2), 100.0 * 4.0, 1.0e-4, "the peak reaches the ramp top");
    // At the western edge only the eastward walk contributes.
    require_close(ramp_relief.at(3, 1, 2), 300.0, 1.0e-4, "E/W relief at the western edge");
    require_throw([] {
        (void)cteas::puff::terrain_relief(0, 4, flat(50.0, 4));
    }, "an empty domain");
}

void test_getelev() {
    const auto cell = flat(50.0, 4);
    InterpolatedElevationInputs inputs;
    inputs.nx = 4;
    inputs.ny = 4;
    inputs.x = 1.5;
    inputs.y = 1.5;
    require_close(cteas::puff::interpolated_elevation(inputs, cell), 50.0, 1.0e-6,
                  "a flat grid interpolates to its own value");
    // A ramp in x: the interpolated value at the centre of cell 2 is 100*2.
    const ElevationCell ramp = [](int i, int) { return static_cast<double>(100 * i); };
    require_close(cteas::puff::interpolated_elevation(inputs, ramp), 200.0, 1.0e-4,
                  "the interpolation returns the cell-centre value");
    inputs.x = 1.0;
    require_close(cteas::puff::interpolated_elevation(inputs, ramp), 150.0, 1.0e-4,
                  "halfway between two cell centres");
    // A single-cell domain returns that cell.
    InterpolatedElevationInputs single;
    single.nx = 1;
    single.ny = 1;
    require_close(cteas::puff::interpolated_elevation(single, flat(7.0, 1)), 7.0, 0.0,
                  "a single-cell domain");
    require_throw([] {
        InterpolatedElevationInputs broken;
        broken.nx = 0;
        (void)cteas::puff::interpolated_elevation(broken, flat(1.0, 1));
    }, "an empty domain");
}

} // namespace

int main() {
    try {
        test_teravg();
        test_trelief();
        test_getelev();
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    std::cout << "P7S_TERRAIN_STATE_CONTRACT=PASS\n";
    return 0;
}
