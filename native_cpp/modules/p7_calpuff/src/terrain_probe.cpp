// P7R terrain-constraint probe: case matrices for the vendor-source parity test
// plus a physical-chain run on the locked case's real elevation field.
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/terrain_constraints.hpp"

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

using cteas::puff::TerrainLookup;
using cteas::puff::TerrainStrainInputs;
using cteas::puff::WallTrapInputs;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7R cannot read file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

// The oracle's deterministic terrain stubs: the first met cell holds x < 0.5.
int ctadj2_matrix() {
    int icase = 0, upslope = 0;
    double r = 0.0, zpold = 0.0, xold = 0.0, yold = 0.0, xnew = 0.0, ynew = 0.0;
    double szold = 0.0, bvf = 0.0, ws = 0.0, dgrid = 0.0, elc = 0.0, eln = 0.0;
    double relc[5];
    double reln[5];
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> r >> zpold >> xold >> yold >> xnew >> ynew >> szold >> bvf >> ws >>
           dgrid >> relc[0] >> relc[1] >> relc[2] >> relc[3] >> relc[4] >> reln[0] >> reln[1] >>
           reln[2] >> reln[3] >> reln[4] >> elc >> eln) {
        TerrainLookup terrain;
        terrain.elevation_msl = [elc, eln](double x, double) { return x < 0.5 ? elc : eln; };
        terrain.cell_elevation_msl = terrain.elevation_msl;
        terrain.relief = [relc, reln](double x, double, int corner) {
            require_true(corner >= 1 && corner <= 5, "relief corner must be 1-5");
            const std::size_t index = static_cast<std::size_t>(corner - 1);
            return x < 0.5 ? relc[index] : reln[index];
        };
        terrain.valley_width = [](double, double, int) { return -1; };
        TerrainStrainInputs inputs;
        inputs.sigma_ratio = r;
        inputs.puff_height_start_m = zpold;
        inputs.x_old = xold;
        inputs.y_old = yold;
        inputs.x_new = xnew;
        inputs.y_new = ynew;
        inputs.sigma_z_start_m = szold;
        inputs.brunt_vaisala_s = bvf;
        inputs.wind_speed_ms = ws;
        inputs.grid_spacing_m = dgrid;
        const auto result = cteas::puff::terrain_strain(inputs, terrain);
        std::cout << icase << ' ' << result.strain << ' ' << result.puff_height_end_m << ' '
                  << result.fraction_beyond << ' ' << (result.upslope ? 1 : 0) << '\n';
        (void)upslope;
        ++cases;
    }
    std::cerr << "P7R_CTADJ2_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int walltrap_matrix() {
    int icase = 0;
    double syb = 0.0, sye = 0.0, z = 0.0, xb = 0.0, yb = 0.0, xe = 0.0, ye = 0.0;
    double bvf = 0.0, ws = 0.0, dzval = 0.0, xgridm = 0.0;
    int iw11 = 0, iw21 = 0, iw31 = 0, iw12 = 0, iw22 = 0, iw32 = 0;
    double el1 = 0.0, el2 = 0.0, rel5c = 0.0, rel5n = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> syb >> sye >> z >> xb >> yb >> xe >> ye >> bvf >> ws >> dzval >>
           xgridm >> iw11 >> iw21 >> iw31 >> iw12 >> iw22 >> iw32 >> el1 >> el2 >> rel5c >> rel5n) {
        TerrainLookup terrain;
        terrain.elevation_msl = [el1, el2](double x, double) { return x < 0.5 ? el1 : el2; };
        terrain.cell_elevation_msl = terrain.elevation_msl;
        terrain.relief = [rel5c, rel5n](double x, double, int corner) {
            require_true(corner == 5, "WALLTRAP only reads the peak relief");
            return x < 0.5 ? rel5c : rel5n;
        };
        terrain.valley_width = [iw11, iw21, iw31, iw12, iw22, iw32](double x, double, int level) {
            require_true(level >= 1 && level <= 3, "the valley-width stub covers levels 1-3");
            if (x < 0.5) {
                return level == 1 ? iw11 : (level == 2 ? iw21 : iw31);
            }
            return level == 1 ? iw12 : (level == 2 ? iw22 : iw32);
        };
        WallTrapInputs inputs;
        inputs.sigma_y_begin_m = syb;
        inputs.sigma_y_end_m = sye;
        inputs.puff_height_m = z;
        inputs.x_begin = xb;
        inputs.y_begin = yb;
        inputs.x_end = xe;
        inputs.y_end = ye;
        inputs.brunt_vaisala_s = bvf;
        inputs.wind_speed_ms = ws;
        inputs.valley_layer_thickness_m = dzval;
        inputs.grid_spacing_m = xgridm;
        inputs.max_valley_levels = 10;   // the vendor parameter MXVALZ
        const auto result = cteas::puff::wall_trap(inputs, terrain);
        std::cout << icase << ' ' << result.sigma_y_end_m << ' ' << (result.trapped ? 1 : 0)
                  << '\n';
        ++cases;
    }
    std::cerr << "P7R_WALLTRAP_PROBE=PASS cases=" << cases << '\n';
    return 0;
}

// Physical-chain run: the locked case's real CALMET elevation field drives the
// MCTADJ=2 constraints for one puff step. TRELIEF's directional relief and the
// valley-width table are NOT reconstructed, so the relief is a documented
// stand-in computed from the real elevation field and the valley width is
// reported as absent.
int deck_terrain_mode(const std::string& met_path, const std::string& control_path, int hour_index,
                      double stack_x_km, double stack_y_km, double stack_height_m,
                      double sigma_z_start_m, double sigma_ratio, double wind_speed_ms,
                      double brunt_vaisala_s) {
    const auto text = read_text(control_path);
    const auto control = cteas::puff::ControlFile::parse(text);
    const int step_seconds = control.required_int("NSECDT");
    require_true(control.required_int("MCTADJ") == 2,
                 "the deck does not select MCTADJ=2, so these constraints are off its path");

    struct Hour {
        std::map<std::string, std::vector<float>> values;
        std::map<std::string, std::vector<std::int32_t>> integers;
    } hour;
    int intervals = 0;
    const auto summary = cteas::puff::Calmet21Reader::read(
        met_path, [&](const cteas::puff::Calmet21Field& field) {
            if (intervals == hour_index) {
                if (field.integer) hour.integers[field.label] = field.integer_values;
                else hour.values[field.label] = field.real_values;
            }
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

    const auto cell_index = [&](double x_m, double y_m, int& i, int& j) {
        i = static_cast<int>((x_m - origin_x_m) / dx_m);
        j = static_cast<int>((y_m - origin_y_m) / dx_m);
        i = std::max(0, std::min(nx - 1, i));
        j = std::max(0, std::min(ny - 1, j));
    };
    // GETELEV stand-in: bilinear interpolation of the real elevation field.
    const auto elevation_at = [&](double x_m, double y_m) {
        const double fx = (x_m - origin_x_m) / dx_m - 0.5;
        const double fy = (y_m - origin_y_m) / dx_m - 0.5;
        const int i0 = std::max(0, std::min(nx - 1, static_cast<int>(std::floor(fx))));
        const int j0 = std::max(0, std::min(ny - 1, static_cast<int>(std::floor(fy))));
        const int i1 = std::min(nx - 1, i0 + 1);
        const int j1 = std::min(ny - 1, j0 + 1);
        const double tx = std::max(0.0, std::min(1.0, fx - i0));
        const double ty = std::max(0.0, std::min(1.0, fy - j0));
        const auto at = [&](int i, int j) {
            return static_cast<double>(elevation[static_cast<std::size_t>(j) * nx + i]);
        };
        return (1.0 - tx) * (1.0 - ty) * at(i0, j0) + tx * (1.0 - ty) * at(i1, j0) +
               (1.0 - tx) * ty * at(i0, j1) + tx * ty * at(i1, j1);
    };
    // TRELIEF stand-in: the local relief is the drop from the surrounding peak
    // to the cell elevation (documented; the vendor's directional relief is not
    // reconstructed).
    const auto relief_at = [&](double x_m, double y_m) {
        int i = 0;
        int j = 0;
        cell_index(x_m, y_m, i, j);
        double peak = elevation[static_cast<std::size_t>(j) * nx + i];
        for (int jj = std::max(0, j - 2); jj <= std::min(ny - 1, j + 2); ++jj) {
            for (int ii = std::max(0, i - 2); ii <= std::min(nx - 1, i + 2); ++ii) {
                peak = std::max(peak, static_cast<double>(
                                          elevation[static_cast<std::size_t>(jj) * nx + ii]));
            }
        }
        return std::max(0.0, peak - elevation_at(x_m, y_m));
    };

    // The vendor's GETELEV/GETCELL take met-grid units, so the lookups convert
    // to metres before sampling the decoded elevation field.
    const auto to_metres = [&](double x_mgu, double y_mgu) {
        return std::pair<double, double>{x_mgu * dx_m + origin_x_m, y_mgu * dx_m + origin_y_m};
    };
    TerrainLookup terrain;
    terrain.elevation_msl = [&](double x_mgu, double y_mgu) {
        const auto [x_m, y_m] = to_metres(x_mgu, y_mgu);
        return elevation_at(x_m, y_m);
    };
    terrain.cell_elevation_msl = [&](double x_mgu, double y_mgu) {
        const auto [x_m, y_m] = to_metres(x_mgu, y_mgu);
        int i = 0;
        int j = 0;
        cell_index(x_m, y_m, i, j);
        return static_cast<double>(elevation[static_cast<std::size_t>(j) * nx + i]);
    };
    terrain.relief = [&](double x_mgu, double y_mgu, int corner) {
        const auto [x_m, y_m] = to_metres(x_mgu, y_mgu);
        if (corner == 5) {
            int i = 0;
            int j = 0;
            cell_index(x_m, y_m, i, j);
            return static_cast<double>(elevation[static_cast<std::size_t>(j) * nx + i]) +
                   relief_at(x_m, y_m);
        }
        return relief_at(x_m, y_m);
    };
    terrain.valley_width = [](double, double, int) { return -1; };   // no valley table

    const double step_distance_m = wind_speed_ms * static_cast<double>(step_seconds);
    const double x_old_m = stack_x_km * 1000.0;
    const double y_old_m = stack_y_km * 1000.0;
    const double x_new_m = x_old_m + step_distance_m;
    TerrainStrainInputs strain_inputs;
    strain_inputs.sigma_ratio = sigma_ratio;
    strain_inputs.puff_height_start_m = stack_height_m;
    strain_inputs.x_old = (x_old_m - origin_x_m) / dx_m;
    strain_inputs.y_old = (y_old_m - origin_y_m) / dx_m;
    strain_inputs.x_new = (x_new_m - origin_x_m) / dx_m;
    strain_inputs.y_new = strain_inputs.y_old;
    strain_inputs.sigma_z_start_m = sigma_z_start_m;
    strain_inputs.brunt_vaisala_s = brunt_vaisala_s;
    strain_inputs.wind_speed_ms = wind_speed_ms;
    strain_inputs.grid_spacing_m = dx_m;
    const auto strain = cteas::puff::terrain_strain(strain_inputs, terrain);

    WallTrapInputs trap_inputs;
    trap_inputs.sigma_y_begin_m = 100.0;
    trap_inputs.sigma_y_end_m = 200.0;
    trap_inputs.puff_height_m = stack_height_m;
    trap_inputs.x_begin = strain_inputs.x_old;
    trap_inputs.y_begin = strain_inputs.y_old;
    trap_inputs.x_end = strain_inputs.x_new;
    trap_inputs.y_end = strain_inputs.y_new;
    trap_inputs.brunt_vaisala_s = brunt_vaisala_s;
    trap_inputs.wind_speed_ms = wind_speed_ms;
    trap_inputs.valley_layer_thickness_m = 10.0;
    trap_inputs.grid_spacing_m = dx_m;
    trap_inputs.max_valley_levels = 10;
    const auto trap = cteas::puff::wall_trap(trap_inputs, terrain);

    std::cout.precision(17);
    std::cout << "P7R_DECK_TERRAIN_RUN=PASS HOUR=" << hour_index
              << " MCTADJ=" << control.required_int("MCTADJ") << " ZI_M=" << mixing_height
              << " DX_M=" << dx_m << " ELEV_MIN_M=" << *std::min_element(elevation.begin(),
                                                                         elevation.end())
              << " ELEV_MAX_M=" << *std::max_element(elevation.begin(), elevation.end())
              << " PUFF_HEIGHT_M=" << stack_height_m << " SIGMA_Z_START_M=" << sigma_z_start_m
              << " ELEV_OLD_M=" << elevation_at(x_old_m, y_old_m)
              << " ELEV_NEW_M=" << elevation_at(x_new_m, y_old_m)
              << " DELX_M=" << step_distance_m
              << " SIGMA_RATIO=" << sigma_ratio << " SPEED_MS=" << wind_speed_ms
              << " BVF=" << brunt_vaisala_s << " STRAIN=" << strain.strain
              << " ZPNEW_M=" << strain.puff_height_end_m
              << " FRACZ=" << strain.fraction_beyond
              << " UPSLOPE=" << (strain.upslope ? "true" : "false")
              << " WALLTRAP_TRAPPED=" << (trap.trapped ? "true" : "false")
              << " WALLTRAP_SYE_M=" << trap.sigma_y_end_m
              << " TRELIEF_STANDIN=true VALLEY_TABLE_ABSENT=true"
              << " PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true\n";
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const std::string mode = argc > 1 ? argv[1] : "";
        if (mode == "--ctadj2-matrix") return ctadj2_matrix();
        if (mode == "--walltrap-matrix") return walltrap_matrix();
        if (mode == "--deck-terrain" && argc == 12) {
            return deck_terrain_mode(argv[2], argv[3], std::stoi(argv[4]), std::stod(argv[5]),
                                     std::stod(argv[6]), std::stod(argv[7]), std::stod(argv[8]),
                                     std::stod(argv[9]), std::stod(argv[10]), std::stod(argv[11]));
        }
        std::cerr << "Usage: cteas_p7r_probe --ctadj2-matrix | --walltrap-matrix |\n"
                     "  --deck-terrain MET CONTROL HOUR STACK_X_KM STACK_Y_KM STACK_H_M "
                     "SIGMA_Z_START_M SIGMA_RATIO SPEED_MS BVF\n";
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "P7R_PROBE=FAIL: " << error.what() << '\n';
        return 1;
    }
}
