// P7S terrain-state probe: case matrices for the vendor-source parity test plus a
// physical-chain relief run on the locked case's real CALMET elevation field.
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/terrain_constraints.hpp"
#include "cteas/puff/terrain_relief.hpp"

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
using cteas::puff::InterpolatedElevationInputs;
using cteas::puff::TerrainLookup;
using cteas::puff::TerrainStrainInputs;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7S cannot read file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

// The oracle's case format: a header record, then the elevation grid record.
std::vector<double> read_grid(int nx, int ny) {
    std::vector<double> values;
    double value = 0.0;
    for (int index = 0; index < nx * ny; ++index) {
        if (!(std::cin >> value)) throw std::runtime_error("P7S probe: missing elevation grid");
        values.push_back(value);
    }
    return values;
}

ElevationCell accessor(const std::vector<double>& grid, int nx) {
    return [&grid, nx](int i, int j) {
        return grid[static_cast<std::size_t>(j - 1) * static_cast<std::size_t>(nx) +
                    static_cast<std::size_t>(i - 1)];
    };
}

int teravg_matrix() {
    int icase = 0, nx = 0, ny = 0, i0 = 0, j0 = 0, i = 0, j = 0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> nx >> ny >> i0 >> j0 >> i >> j) {
        const auto grid = read_grid(nx, ny);
        std::cout << icase << ' '
                  << cteas::puff::terrain_strip_average(i0, j0, i, j, nx, ny, accessor(grid, nx))
                  << '\n';
        ++cases;
    }
    std::cerr << "P7S_TERAVG_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int trelief_matrix() {
    int icase = 0, nx = 0, ny = 0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> nx >> ny) {
        const auto grid = read_grid(nx, ny);
        const auto relief = cteas::puff::terrain_relief(nx, ny, accessor(grid, nx));
        std::cout << icase;
        for (int corner = 1; corner <= 5; ++corner) {
            for (int j = 1; j <= ny; ++j) {
                for (int i = 1; i <= nx; ++i) {
                    std::cout << ' ' << relief.at(corner, i, j);
                }
            }
        }
        std::cout << '\n';
        ++cases;
    }
    std::cerr << "P7S_TRELIEF_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int getelev_matrix() {
    int icase = 0, nx = 0, ny = 0;
    double x = 0.0, y = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> nx >> ny >> x >> y) {
        const auto grid = read_grid(nx, ny);
        InterpolatedElevationInputs inputs;
        inputs.x = x;
        inputs.y = y;
        inputs.nx = nx;
        inputs.ny = ny;
        inputs.nest_factor = 1.0;
        inputs.nest_offset_x = 0.0;
        inputs.nest_offset_y = 0.0;
        std::cout << icase << ' '
                  << cteas::puff::interpolated_elevation(inputs, accessor(grid, nx)) << '\n';
        ++cases;
    }
    std::cerr << "P7S_GETELEV_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

// Physical-chain run: TRELIEF over the locked case's real CALMET elevation field
// produces the relief corners, which then drive the MCTADJ=2 constraints.
int deck_relief_mode(const std::string& met_path, const std::string& control_path, int hour_index,
                     double stack_x_km, double stack_y_km, double stack_height_m,
                     double sigma_z_start_m, double sigma_ratio, double wind_speed_ms,
                     double brunt_vaisala_s) {
    const auto text = read_text(control_path);
    const auto control = cteas::puff::ControlFile::parse(text);
    const int step_seconds = control.required_int("NSECDT");
    require_true(control.required_int("MCTADJ") == 2, "the deck does not select MCTADJ=2");

    struct Hour {
        std::map<std::string, std::vector<float>> values;
    } hour;
    int intervals = 0;
    const auto summary = cteas::puff::Calmet21Reader::read(
        met_path, [&](const cteas::puff::Calmet21Field& field) {
            if (intervals == hour_index && !field.integer) hour.values[field.label] = field.real_values;
            if (field.label == "IRH") ++intervals;
        });
    require_true(intervals > hour_index, "requested hour is not present");
    require_true(summary.statics.present, "MET.DAT has no decoded static fields");
    require_true(hour.values.count("ZI") == 1U, "missing the hourly mixing height");

    const int nx = summary.header.nx;
    const int ny = summary.header.ny;
    const double dx_m = summary.header.dx_m;
    const double origin_x_m = summary.header.origin_x_m;
    const double origin_y_m = summary.header.origin_y_m;
    const std::vector<float>& elevation = summary.statics.elevation_m;
    require_true(elevation.size() == static_cast<std::size_t>(nx * ny),
                 "the decoded elevation field has the wrong size");
    const double mixing_height = static_cast<double>(hour.values.at("ZI")[0]);

    // TRELIEF over the real elevation field (i fastest, as the vendor stores it).
    const ElevationCell cell = [&elevation, nx](int i, int j) {
        return static_cast<double>(elevation[static_cast<std::size_t>(j - 1) *
                                                static_cast<std::size_t>(nx) +
                                            static_cast<std::size_t>(i - 1)]);
    };
    const auto relief = cteas::puff::terrain_relief(nx, ny, cell);

    int i_cell = 0;
    int j_cell = 0;
    const auto cell_index = [&](double x_km, double y_km) {
        i_cell = static_cast<int>((x_km * 1000.0 - origin_x_m) / dx_m) + 1;
        j_cell = static_cast<int>((y_km * 1000.0 - origin_y_m) / dx_m) + 1;
        i_cell = std::max(1, std::min(nx, i_cell));
        j_cell = std::max(1, std::min(ny, j_cell));
    };
    cell_index(stack_x_km, stack_y_km);

    const auto to_mgu = [&](double x_km, double y_km) {
        return std::pair<double, double>{(x_km * 1000.0 - origin_x_m) / dx_m,
                                         (y_km * 1000.0 - origin_y_m) / dx_m};
    };
    TerrainLookup terrain;
    terrain.elevation_msl = [&](double x_mgu, double y_mgu) {
        InterpolatedElevationInputs inputs;
        inputs.x = x_mgu;
        inputs.y = y_mgu;
        inputs.nx = nx;
        inputs.ny = ny;
        return cteas::puff::interpolated_elevation(inputs, cell);
    };
    terrain.cell_elevation_msl = [&](double x_mgu, double y_mgu) {
        int i = std::max(1, std::min(nx, static_cast<int>(x_mgu) + 1));
        int j = std::max(1, std::min(ny, static_cast<int>(y_mgu) + 1));
        return cell(i, j);
    };
    terrain.relief = [&](double x_mgu, double y_mgu, int corner) {
        int i = std::max(1, std::min(nx, static_cast<int>(x_mgu) + 1));
        int j = std::max(1, std::min(ny, static_cast<int>(y_mgu) + 1));
        return relief.at(corner, i, j);
    };
    terrain.valley_width = [](double, double, int) { return -1; };   // VWIDTH not reconstructed

    const double step_distance_m = wind_speed_ms * static_cast<double>(step_seconds);
    const auto [x_old_mgu, y_old_mgu] = to_mgu(stack_x_km, stack_y_km);
    const auto [x_new_mgu, y_new_mgu] = to_mgu(stack_x_km + step_distance_m / 1000.0,
                                               stack_y_km);
    TerrainStrainInputs strain_inputs;
    strain_inputs.sigma_ratio = sigma_ratio;
    strain_inputs.puff_height_start_m = stack_height_m;
    strain_inputs.x_old = x_old_mgu;
    strain_inputs.y_old = y_old_mgu;
    strain_inputs.x_new = x_new_mgu;
    strain_inputs.y_new = y_new_mgu;
    strain_inputs.sigma_z_start_m = sigma_z_start_m;
    strain_inputs.brunt_vaisala_s = brunt_vaisala_s;
    strain_inputs.wind_speed_ms = wind_speed_ms;
    strain_inputs.grid_spacing_m = dx_m;
    const auto strain = cteas::puff::terrain_strain(strain_inputs, terrain);

    std::cout.precision(17);
    std::cout << "P7S_DECK_RELIEF_RUN=PASS HOUR=" << hour_index << " NX=" << nx << " NY=" << ny
              << " DX_M=" << dx_m << " ZI_M=" << mixing_height
              << " CELL_I=" << i_cell << " CELL_J=" << j_cell
              << " RELIEF_NS_M=" << relief.at(1, i_cell, j_cell)
              << " RELIEF_NESW_M=" << relief.at(2, i_cell, j_cell)
              << " RELIEF_EW_M=" << relief.at(3, i_cell, j_cell)
              << " RELIEF_SENW_M=" << relief.at(4, i_cell, j_cell)
              << " RELIEF_PEAK_M=" << relief.at(5, i_cell, j_cell)
              << " ELEV_CELL_M=" << cell(i_cell, j_cell) << " STRAIN=" << strain.strain
              << " ZPNEW_M=" << strain.puff_height_end_m
              << " FRACZ=" << strain.fraction_beyond
              << " UPSLOPE=" << (strain.upslope ? "true" : "false")
              << " TRELIEF_STANDIN=false VWIDTH_NOT_RECONSTRUCTED=true"
              << " VALLEY_TABLE_ABSENT=true PHYSICAL_CHAIN_ONLY=true"
              << " NOT_A_PUFF_CON_COMPARISON=true\n";
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const std::string mode = argc > 1 ? argv[1] : "";
        if (mode == "--teravg-matrix") return teravg_matrix();
        if (mode == "--trelief-matrix") return trelief_matrix();
        if (mode == "--getelev-matrix") return getelev_matrix();
        if (mode == "--deck-relief" && argc == 12) {
            return deck_relief_mode(argv[2], argv[3], std::stoi(argv[4]), std::stod(argv[5]),
                                    std::stod(argv[6]), std::stod(argv[7]), std::stod(argv[8]),
                                    std::stod(argv[9]), std::stod(argv[10]), std::stod(argv[11]));
        }
        std::cerr << "Usage: cteas_p7s_probe --teravg-matrix | --trelief-matrix | "
                     "--getelev-matrix |\n  --deck-relief MET CONTROL HOUR STACK_X_KM STACK_Y_KM "
                     "STACK_H_M SIGMA_Z_START_M SIGMA_RATIO SPEED_MS BVF\n";
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "P7S_PROBE=FAIL: " << error.what() << '\n';
        return 1;
    }
}
