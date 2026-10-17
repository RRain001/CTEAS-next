// P7T VWIDTH contract tests: hand-derived behaviour on synthetic terrain and every
// fail-closed path. Original-routine parity is checked separately by
// tests/p7t_parity_tests.py against the compiled vendor unit.
#include "cteas/puff/terrain_width.hpp"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using cteas::puff::ElevationCell;
using cteas::puff::ValleyWidthInputs;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7T TEST FAILURE: " + message);
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

ElevationCell from_grid(const std::vector<double>& grid, int nx) {
    return [&grid, nx](int i, int j) {
        return grid[static_cast<std::size_t>(j - 1) * static_cast<std::size_t>(nx) +
                    static_cast<std::size_t>(i - 1)];
    };
}

void test_flat_terrain() {
    // A flat grid has no walls, so every width stays at the null value and the
    // layer thickness falls back to DZMIN.
    std::vector<double> grid(25, 50.0);
    ValleyWidthInputs inputs;
    inputs.nx = 5;
    inputs.ny = 5;
    inputs.max_levels = 10;
    const auto widths = cteas::puff::valley_widths(inputs, from_grid(grid, 5));
    require_close(widths.layer_thickness_m, 10.0, 1.0e-6, "DZMIN for flat terrain");
    for (int level = 1; level <= 10; ++level) {
        for (int i = 1; i <= 5; ++i) {
            for (int j = 1; j <= 5; ++j) {
                require(widths.at(level, i, j) == -1, "flat terrain has no valley width");
            }
        }
    }
}

void test_valley() {
    // A symmetric valley: two 100 m walls with a 25 m floor. The wall hits the
    // target elevation from the centre cell at the first level.
    const int nx = 5;
    const int ny = 5;
    std::vector<double> grid;
    for (int j = 1; j <= ny; ++j) {
        for (int i = 1; i <= nx; ++i) {
            grid.push_back((i == 1 || i == nx) ? 100.0 : 25.0);
        }
    }
    ValleyWidthInputs inputs;
    inputs.nx = nx;
    inputs.ny = ny;
    inputs.max_levels = 10;
    const auto widths = cteas::puff::valley_widths(inputs, from_grid(grid, nx));
    require_close(widths.layer_thickness_m, 10.0, 1.0e-6, "DZMIN for a shallow valley");
    // The centre cell sees walls on both sides in the E/W direction.
    const int centre = widths.at(1, 3, 3);
    require(centre >= 2, "the centre cell reports a valley width of at least two cells");
    // The wall cells themselves have no valley at the first level.
    require(widths.at(1, 1, 3) == -1, "a wall cell has no valley width");
}

void test_fail_closed() {
    std::vector<double> grid(9, 50.0);
    require_throw([&] {
        ValleyWidthInputs broken;
        broken.nx = 3;
        broken.ny = 3;
        broken.max_levels = 0;
        (void)cteas::puff::valley_widths(broken, from_grid(grid, 3));
    }, "MXVALZ below one");
    require_throw([&] {
        ValleyWidthInputs broken;
        broken.nx = 0;
        broken.ny = 3;
        (void)cteas::puff::valley_widths(broken, from_grid(grid, 3));
    }, "an empty domain");
    require_throw([&] {
        ValleyWidthInputs broken;
        broken.nx = 3;
        broken.ny = 3;
        broken.min_layer_m = 0.0;
        (void)cteas::puff::valley_widths(broken, from_grid(grid, 3));
    }, "DZMIN below zero");
    require_throw([&] {
        ValleyWidthInputs broken;
        broken.nx = 3;
        broken.ny = 3;
        broken.wall_fraction = 1.0;
        (void)cteas::puff::valley_widths(broken, from_grid(grid, 3));
    }, "QAHIT outside (0,1)");
    require_throw([&] {
        ValleyWidthInputs broken;
        broken.nx = 3;
        broken.ny = 3;
        (void)cteas::puff::valley_widths(broken, ElevationCell());
    }, "a missing elevation accessor");
}

} // namespace

int main() {
    try {
        test_flat_terrain();
        test_valley();
        test_fail_closed();
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    std::cout << "P7T_VALLEY_WIDTH_CONTRACT=PASS\n";
    return 0;
}
