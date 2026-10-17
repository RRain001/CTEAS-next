// P7V advection probe: the vendor-source parity matrix for ZFIND/ADVWND/ADVECT/
// PUFFDZ plus a physical-chain run of PUFFDZ + ADVECT over the locked case's real
// CALMET cell winds. It is explicitly NOT a puff.con comparison.
#include "cteas/puff/advection.hpp"
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"

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

using cteas::puff::AdvectiveWindInputs;
using cteas::puff::LayerAverageInputs;
using cteas::puff::PuffExtentInputs;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7V cannot read file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

std::vector<double> read_values(int count) {
    std::vector<double> values;
    values.reserve(static_cast<std::size_t>(count));
    for (int index = 0; index < count; ++index) {
        double value = 0.0;
        if (!(std::cin >> value)) throw std::runtime_error("P7V probe: truncated case");
        values.push_back(value);
    }
    return values;
}

// The matrix mirrors the oracle's stdin grammar; the mode is fixed by --mode.
int matrix_mode(int mode) {
    int cases = 0;
    std::cout.precision(17);
    int icase = 0;
    while (std::cin >> icase) {
        if (mode == 1) {
            int nz = 0;
            if (!(std::cin >> nz)) throw std::runtime_error("P7V probe: missing nz");
            const auto faces = read_values(nz + 1);
            const auto z = read_values(1);
            std::cout << icase << ' '
                      << cteas::puff::find_layer(z[0], faces) << '\n';
        } else if (mode == 2 || mode == 3) {
            int nz = 0;
            if (!(std::cin >> nz)) throw std::runtime_error("P7V probe: missing nz");
            const auto faces = read_values(nz + 1);
            const auto u = read_values(nz);
            const auto v = read_values(nz);
            const auto span = read_values(2);
            if (mode == 2) {
                LayerAverageInputs inputs;
                inputs.u_ms = u;
                inputs.v_ms = v;
                inputs.face_heights_m = faces;
                inputs.z_bottom_m = span[0];
                inputs.z_top_m = span[1];
                const auto wind = cteas::puff::layer_average_wind(inputs);
                std::cout << icase << ' ' << wind.u_ms << ' ' << wind.v_ms << '\n';
            } else {
                AdvectiveWindInputs inputs;
                inputs.met_format = 1;
                inputs.u_profile_ms = u;
                inputs.v_profile_ms = v;
                inputs.face_heights_m = faces;
                inputs.z_bottom_m = span[0];
                inputs.z_top_m = span[1];
                const auto wind = cteas::puff::advective_wind(inputs);
                std::cout << icase << ' ' << wind.u_ms << ' ' << wind.v_ms << '\n';
            }
        } else if (mode == 4) {
            // The vendor's list-directed reader takes a LOGICAL for LPUFF, so the
            // grammar carries T/F there and the probe maps it to a bool.
            std::vector<std::string> tokens;
            for (int index = 0; index < 14; ++index) {
                std::string token;
                if (!(std::cin >> token)) throw std::runtime_error("P7V probe: truncated case");
                tokens.push_back(token);
            }
            std::vector<double> rest;
            for (std::size_t index = 0; index < tokens.size(); ++index) {
                if (index == 1U) {
                    rest.push_back((tokens[index] == "T" || tokens[index] == "t" ||
                                    tokens[index] == ".TRUE.") ? 1.0 : 0.0);
                } else {
                    rest.push_back(std::stod(tokens[index]));
                }
            }
            PuffExtentInputs inputs;
            inputs.puff_code = static_cast<int>(rest[0]);
            inputs.puff = rest[1] != 0.0;
            inputs.stability_class = static_cast<int>(rest[2]);
            // rest[3] is ILAYER: the oracle places ZFACE(ILAYER)/ZFACE(ILAYER+1)
            // from the case line, so the port receives them as explicit inputs.
            inputs.puff_height_m = rest[4];
            inputs.mixing_height_m = rest[5];
            inputs.sigma_z_begin_m = rest[6];
            inputs.sigma_z_end_m = rest[7];
            inputs.previous_mixing_height_m = rest[8];
            inputs.maximum_mixing_height_m = rest[9];
            inputs.layer_bottom_m = rest[10];
            inputs.layer_top_m = rest[11];
            const int nspec = static_cast<int>(rest[12]);
            inputs.mixed_layer_mass.assign(static_cast<std::size_t>(nspec), 1.0);
            inputs.above_layer_mass.assign(static_cast<std::size_t>(nspec), rest[13]);
            const auto extent = cteas::puff::puff_extent(inputs);
            std::cout << icase << ' ' << extent.z_top_m << ' ' << extent.z_bottom_m << '\n';
        } else {
            throw std::invalid_argument("P7V probe: unknown mode");
        }
        ++cases;
    }
    std::cerr << "P7V_ADVECTION_PROBE=PASS MODE=" << mode << " CASES=" << cases << '\n';
    return 0;
}

// Physical-chain run over the locked case: the real CALMET cell's U/V profile and
// the real mixing height drive PUFFDZ (vertical extent) and ADVECT (advective
// wind). SIGMA_Z_M is an explicit input because the sigma model is P7Q's output.
int deck_advection_mode(const std::string& met_path, const std::string& control_path,
                        int hour_index, double stack_x_km, double stack_y_km,
                        double release_height_m, double sigma_z_m) {
    const auto control = cteas::puff::ControlFile::parse(read_text(control_path));
    require_true(control.required_int("MCTADJ") == 2, "the deck does not select MCTADJ=2");

    std::map<std::string, std::vector<float>> hour;
    std::map<std::string, std::vector<std::int32_t>> hour_integers;
    int intervals = 0;
    const auto summary = cteas::puff::Calmet21Reader::read(
        met_path, [&](const cteas::puff::Calmet21Field& field) {
            if (intervals == hour_index) {
                if (field.integer) {
                    hour_integers[field.label] = field.integer_values;
                } else {
                    hour[field.label] = field.real_values;
                }
            }
            if (field.label == "IRH") ++intervals;
        });
    require_true(intervals > hour_index, "requested hour is not present");
    require_true(summary.statics.present, "MET.DAT has no decoded static fields");

    const int nx = summary.header.nx;
    const int ny = summary.header.ny;
    const int nz = summary.header.nz;
    const double dx_m = summary.header.dx_m;
    require_true(summary.statics.present, "MET.DAT has no decoded face heights");
    const std::vector<float>& zface_field = summary.statics.cell_face_m;
    require_true(static_cast<int>(zface_field.size()) == nz + 1,
                 "the face heights do not match NZ");
    const std::vector<double> zface(zface_field.begin(), zface_field.end());

    const double origin_x_m = summary.header.origin_x_m;
    const double origin_y_m = summary.header.origin_y_m;
    const auto to_mgu = [&](double x_km, double y_km) {
        return std::pair<double, double>{(x_km * 1000.0 - origin_x_m) / dx_m,
                                         (y_km * 1000.0 - origin_y_m) / dx_m};
    };
    const auto [x_mgu, y_mgu] = to_mgu(stack_x_km, stack_y_km);
    const int i_cell = std::max(1, std::min(nx, static_cast<int>(x_mgu) + 1));
    const int j_cell = std::max(1, std::min(ny, static_cast<int>(y_mgu) + 1));
    const std::size_t offset = static_cast<std::size_t>(j_cell - 1) * static_cast<std::size_t>(nx) +
                               static_cast<std::size_t>(i_cell - 1);

    std::vector<double> u_profile;
    std::vector<double> v_profile;
    for (int level = 1; level <= nz; ++level) {
        const std::string suffix = std::to_string(level);
        const std::string u_label = "U-LEV  " + suffix;
        const std::string v_label = "V-LEV  " + suffix;
        require_true(hour.count(u_label) == 1 && hour.count(v_label) == 1,
                     "the hour has no U/V profile for level " + suffix);
        const auto& u_field = hour.at(u_label);
        const auto& v_field = hour.at(v_label);
        require_true(u_field.size() == static_cast<std::size_t>(nx * ny) &&
                         v_field.size() == static_cast<std::size_t>(nx * ny),
                     "the U/V field has the wrong XY extent");
        u_profile.push_back(static_cast<double>(u_field[offset]));
        v_profile.push_back(static_cast<double>(v_field[offset]));
    }
    const double mixing_height = static_cast<double>(hour.at("ZI")[0]);
    // The stability class is CALMET's own IPGT for this hour and cell, clamped
    // exactly as CTSG does (the vendor's 1-6 range).
    require_true(hour_integers.count("IPGT") == 1U, "the hour has no IPGT field");
    const auto& ipgt = hour_integers.at("IPGT");
    require_true(ipgt.size() == static_cast<std::size_t>(nx * ny),
                 "the IPGT field has the wrong XY extent");
    const int stability_class = std::max(1, std::min(6, static_cast<int>(ipgt[offset])));

    PuffExtentInputs extent_inputs;
    extent_inputs.puff_code = 1;
    extent_inputs.puff = true;
    extent_inputs.stability_class = stability_class;
    extent_inputs.puff_height_m = release_height_m;
    extent_inputs.mixing_height_m = mixing_height;
    extent_inputs.sigma_z_begin_m = sigma_z_m;
    extent_inputs.previous_mixing_height_m = mixing_height;
    extent_inputs.maximum_mixing_height_m = mixing_height;
    const auto extent = cteas::puff::puff_extent(extent_inputs);

    AdvectiveWindInputs wind_inputs;
    wind_inputs.met_format = 1;
    wind_inputs.u_profile_ms = u_profile;
    wind_inputs.v_profile_ms = v_profile;
    wind_inputs.face_heights_m = zface;
    wind_inputs.z_bottom_m = extent.z_bottom_m;
    wind_inputs.z_top_m = extent.z_top_m;
    const auto wind = cteas::puff::advective_wind(wind_inputs);
    const double speed = std::hypot(wind.u_ms, wind.v_ms);

    std::cout.precision(6);
    std::cout << std::fixed;
    std::cout << "P7V_DECK_ADVECTION_RUN=PASS HOUR=" << hour_index << " NX=" << nx << " NY=" << ny
              << " NZ=" << nz << " DX_M=" << dx_m << " CELL_I=" << i_cell << " CELL_J=" << j_cell
              << " ZI_M=" << mixing_height << " ISTAB=" << stability_class
              << " RELEASE_H_M=" << release_height_m
              << " SIGMA_Z_M=" << sigma_z_m << " ZTOP_M=" << extent.z_top_m
              << " ZBOT_M=" << extent.z_bottom_m << " UADV_MS=" << wind.u_ms
              << " VADV_MS=" << wind.v_ms << " SPEED_MS=" << speed << '\n';
    std::cout << "P7V_DECK_ADVECTION_IS_NOT_A_CONC_COMPARISON=true\n";
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 3 && std::string(argv[1]) == "--mode") return matrix_mode(std::stoi(argv[2]));
        if (argc == 9 && std::string(argv[1]) == "--deck-advection") {
            return deck_advection_mode(argv[2], argv[3], std::stoi(argv[4]), std::stod(argv[5]),
                                       std::stod(argv[6]), std::stod(argv[7]), std::stod(argv[8]));
        }
        std::cerr << "Usage: cteas_p7v_probe --mode {1|2|3|4} < matrix |\n"
                     "  --deck-advection MET CONTROL HOUR STACK_X_KM STACK_Y_KM RELEASE_H_M "
                     "SIGMA_Z_M\n";
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "cteas_p7v_probe: " << error.what() << '\n';
        return 1;
    }
}
