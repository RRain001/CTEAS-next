// P7T valley-width probe: a case matrix for the vendor-source parity test plus a
// physical-chain run on the locked case's real elevation field.
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/terrain_constraints.hpp"
#include "cteas/puff/terrain_relief.hpp"
#include "cteas/puff/terrain_width.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using cteas::puff::ElevationCell;
using cteas::puff::TerrainLookup;
using cteas::puff::ValleyWidthInputs;
using cteas::puff::WallTrapInputs;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7T cannot read file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

int valley_matrix() {
    int icase = 0, nx = 0, ny = 0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> nx >> ny) {
        std::vector<double> grid;
        double value = 0.0;
        for (int index = 0; index < nx * ny; ++index) {
            if (!(std::cin >> value)) throw std::runtime_error("P7T probe: missing elevation grid");
            grid.push_back(value);
        }
        const ElevationCell cell = [&grid, nx](int i, int j) {
            return grid[static_cast<std::size_t>(j - 1) * static_cast<std::size_t>(nx) +
                        static_cast<std::size_t>(i - 1)];
        };
        ValleyWidthInputs inputs;
        inputs.nx = nx;
        inputs.ny = ny;
        inputs.max_levels = 10;   // the vendor parameter MXVALZ
        const auto widths = cteas::puff::valley_widths(inputs, cell);
        std::cout << icase << ' ' << widths.layer_thickness_m;
        for (int level = 1; level <= inputs.max_levels; ++level) {
            for (int j = 1; j <= ny; ++j) {
                for (int i = 1; i <= nx; ++i) {
                    std::cout << ' ' << widths.at(level, i, j);
                }
            }
        }
        std::cout << '\n';
        ++cases;
    }
    std::cerr << "P7T_VALLEY_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

// Physical-chain run: TRELIEF + VWIDTH over the locked case's real elevation
// field, then WALLTRAP with the real valley widths.
int deck_valley_mode(const std::string& met_path, const std::string& control_path, int hour_index,
                     double stack_x_km, double stack_y_km, double stack_height_m) {
    const auto text = read_text(control_path);
    const auto control = cteas::puff::ControlFile::parse(text);
    require_true(control.required_int("MCTADJ") == 2, "the deck does not select MCTADJ=2");

    struct Hour {
        std::map<std::string, std::vector<float>> values;
    } hour;
    int intervals = 0;
    const auto summary = cteas::puff::Calmet21Reader::read(
        met_path, [&](const cteas::puff::Calmet21Field& field) {
            if (intervals == hour_index && !field.integer) {
                hour.values[field.label] = field.real_values;
            }
            if (field.label == "IRH") ++intervals;
        });
    require_true(intervals > hour_index, "requested hour is not present");
    require_true(summary.statics.present, "MET.DAT has no decoded static fields");

    const int nx = summary.header.nx;
    const int ny = summary.header.ny;
    const double dx_m = summary.header.dx_m;
    const double origin_x_m = summary.header.origin_x_m;
    const double origin_y_m = summary.header.origin_y_m;
    const std::vector<float>& elevation = summary.statics.elevation_m;
    require_true(elevation.size() == static_cast<std::size_t>(nx * ny),
                 "the decoded elevation field has the wrong size");
    const double mixing_height = static_cast<double>(hour.values.at("ZI")[0]);

    const ElevationCell cell = [&elevation, nx](int i, int j) {
        return static_cast<double>(elevation[static_cast<std::size_t>(j - 1) *
                                                static_cast<std::size_t>(nx) +
                                            static_cast<std::size_t>(i - 1)]);
    };
    const auto relief = cteas::puff::terrain_relief(nx, ny, cell);
    ValleyWidthInputs width_inputs;
    width_inputs.nx = nx;
    width_inputs.ny = ny;
    width_inputs.max_levels = 10;
    const auto widths = cteas::puff::valley_widths(width_inputs, cell);

    const auto to_mgu = [&](double x_km, double y_km) {
        return std::pair<double, double>{(x_km * 1000.0 - origin_x_m) / dx_m,
                                         (y_km * 1000.0 - origin_y_m) / dx_m};
    };
    const auto [x_mgu, y_mgu] = to_mgu(stack_x_km, stack_y_km);
    const int i_cell = std::max(1, std::min(nx, static_cast<int>(x_mgu) + 1));
    const int j_cell = std::max(1, std::min(ny, static_cast<int>(y_mgu) + 1));

    TerrainLookup terrain;
    terrain.elevation_msl = [&](double x, double y) {
        int i = std::max(1, std::min(nx, static_cast<int>(x) + 1));
        int j = std::max(1, std::min(ny, static_cast<int>(y) + 1));
        return cell(i, j);
    };
    terrain.cell_elevation_msl = terrain.elevation_msl;
    terrain.relief = [&](double x, double y, int corner) {
        int i = std::max(1, std::min(nx, static_cast<int>(x) + 1));
        int j = std::max(1, std::min(ny, static_cast<int>(y) + 1));
        return relief.at(corner, i, j);
    };
    terrain.valley_width = [&](double x, double y, int level) {
        int i = std::max(1, std::min(nx, static_cast<int>(x) + 1));
        int j = std::max(1, std::min(ny, static_cast<int>(y) + 1));
        if (level < 1 || level > width_inputs.max_levels) return -1;
        return widths.at(level, i, j);
    };

    WallTrapInputs trap_inputs;
    trap_inputs.sigma_y_begin_m = 100.0;
    trap_inputs.sigma_y_end_m = 200.0;
    trap_inputs.puff_height_m = stack_height_m;
    trap_inputs.x_begin = x_mgu;
    trap_inputs.y_begin = y_mgu;
    trap_inputs.x_end = x_mgu + 0.05;
    trap_inputs.y_end = y_mgu;
    trap_inputs.brunt_vaisala_s = 0.02;
    trap_inputs.wind_speed_ms = 1.396;
    trap_inputs.valley_layer_thickness_m = widths.layer_thickness_m;
    trap_inputs.grid_spacing_m = dx_m;
    trap_inputs.max_valley_levels = width_inputs.max_levels;
    const auto trap = cteas::puff::wall_trap(trap_inputs, terrain);

    int defined = 0;
    for (int level = 1; level <= width_inputs.max_levels; ++level) {
        for (int j = 1; j <= ny; ++j) {
            for (int i = 1; i <= nx; ++i) {
                if (widths.at(level, i, j) != -1) ++defined;
            }
        }
    }

    std::cout.precision(17);
    std::cout << "P7T_DECK_VALLEY_RUN=PASS HOUR=" << hour_index << " NX=" << nx << " NY=" << ny
              << " DX_M=" << dx_m << " ZI_M=" << mixing_height
              << " CELL_I=" << i_cell << " CELL_J=" << j_cell
              << " DZVAL_M=" << widths.layer_thickness_m
              << " DEFINED_WIDTHS=" << defined
              << " WIDTH_L1_CELLS=" << widths.at(1, i_cell, j_cell)
              << " WIDTH_L2_CELLS=" << widths.at(2, i_cell, j_cell)
              << " WALLTRAP_TRAPPED=" << (trap.trapped ? "true" : "false")
              << " WALLTRAP_SYE_M=" << trap.sigma_y_end_m
              << " TRELIEF_STANDIN=false VWIDTH_RECONSTRUCTED=true"
              << " VALLEY_TABLE_ABSENT=false PHYSICAL_CHAIN_ONLY=true"
              << " NOT_A_PUFF_CON_COMPARISON=true\n";
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const std::string mode = argc > 1 ? argv[1] : "";
        if (mode == "--valley-matrix") return valley_matrix();
        if (mode == "--deck-valley" && argc == 8) {
            return deck_valley_mode(argv[2], argv[3], std::stoi(argv[4]), std::stod(argv[5]),
                                    std::stod(argv[6]), std::stod(argv[7]));
        }
        std::cerr << "Usage: cteas_p7t_probe --valley-matrix |\n"
                     "  --deck-valley MET CONTROL HOUR STACK_X_KM STACK_Y_KM STACK_H_M\n";
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "P7T_PROBE=FAIL: " << error.what() << '\n';
        return 1;
    }
}
