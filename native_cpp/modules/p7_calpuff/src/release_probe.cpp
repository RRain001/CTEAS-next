// P7O release-scheduler probe: case matrices for the vendor-source parity test
// plus a physical-chain release run on the locked case's stack and met hour.
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/plume_rise.hpp"
#include "cteas/puff/release.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using cteas::puff::InjectionInputs;
using cteas::puff::NewPuffInputs;
using cteas::puff::ReleaseCadenceInputs;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7O cannot read file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

int inject_matrix() {
    int icase = 0, species = 0, step_index = 0, stability = 0, gaussian = 0;
    double duration = 0.0, effective = 0.0, max_layer = 0.0, mixing = 0.0, mixed_fraction = 0.0;
    double q1 = 0.0, q2 = 0.0, q3 = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> species >> duration >> step_index >> effective >> max_layer >>
           mixing >> mixed_fraction >> stability >> gaussian >> q1 >> q2 >> q3) {
        InjectionInputs inputs;
        inputs.species_count = species;
        inputs.emission_duration_s = duration;
        inputs.step_index = step_index;
        inputs.effective_height_m = effective;
        inputs.max_layer_height_m = max_layer;
        inputs.mixing_height_m = mixing;
        inputs.mass_fraction_mixed = mixed_fraction;
        inputs.stability_class = stability;
        inputs.gaussian_distribution = gaussian;
        inputs.emission_rate = {q1, q2, q3};
        const auto result = cteas::puff::inject_emissions(inputs);
        std::cout << icase << ' ' << species << ' ' << result.puff_code << ' '
                  << result.unlimited_mixing_height_m << ' ' << result.previous_mixing_height_m;
        for (int index = 0; index < 3; ++index) {
            // The vendor arrays are MXSPEC wide; the driver zeroes the species
            // beyond NSPEC, so both sides report zeros there.
            const double mixed = index < species
                                     ? result.mixed_layer_mass[static_cast<std::size_t>(index)]
                                     : 0.0;
            const double above = index < species
                                     ? result.above_layer_mass[static_cast<std::size_t>(index)]
                                     : 0.0;
            std::cout << ' ' << mixed << ' ' << above;
        }
        std::cout << '\n';
        ++cases;
    }
    std::cerr << "P7O_INJECT_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int cadence_matrix() {
    int icase = 0, max_puffs = 0;
    double wind = 0.0, interval = 0.0, hour_seconds = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> wind >> interval >> max_puffs >> hour_seconds) {
        ReleaseCadenceInputs inputs;
        inputs.wind_speed_ms = wind;
        inputs.emission_interval = interval;
        inputs.max_puffs = max_puffs;
        inputs.hour_seconds = hour_seconds;
        const auto result = cteas::puff::release_cadence(inputs);
        std::cout << icase << ' ' << result.puff_count << ' ' << result.new_puffs << ' '
                  << result.emission_duration_s << '\n';
        ++cases;
    }
    std::cerr << "P7O_CADENCE_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int state_matrix() {
    std::cout.precision(17);
    int cases = 0;
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.find_first_not_of(" \t\r\n") == std::string::npos) continue;
        std::istringstream fields(line);
        std::vector<double> values;
        double value = 0.0;
        while (fields >> value) values.push_back(value);
        if (values.size() < 40U) continue;
        NewPuffInputs inputs;
        inputs.source_x_km = values[1];
        inputs.source_y_km = values[2];
        inputs.base_elevation_m = values[3];
        inputs.sigma_y_source_m = values[4];
        inputs.sigma_z_source_m = values[5];
        inputs.effective_height_m = values[6];
        inputs.x_final_m = values[7];
        inputs.final_rise_variance_m2 = values[8];
        inputs.buoyancy_flux = values[9];
        inputs.momentum_flux = values[10];
        inputs.x_final_buoyancy_m = values[11];
        inputs.x_final_momentum_m = values[12];
        inputs.z_final_buoyancy_m = values[13];
        inputs.z_final_momentum_m = values[14];
        inputs.stack_tip_downwash_m = values[15];
        inputs.stack_height_m = values[16];
        inputs.exit_velocity_ms = values[17];
        inputs.diameter_m = values[18];
        inputs.emission_duration_s = values[19];
        inputs.stack_wind_speed_ms = values[20];
        inputs.stability_class = static_cast<int>(values[21]);
        inputs.sqrt_stability_s = values[22];
        inputs.urban = static_cast<int>(values[23]);
        inputs.sigma_v_ms = values[24];
        inputs.sigma_w_ms = values[25];
        inputs.obukhov_length_m = values[26];
        inputs.plume_path_exponent = values[27];
        inputs.downwash_code = static_cast<int>(values[28]);
        inputs.building_height_m = values[29];
        inputs.building_width_m = values[30];
        inputs.effective_height2_m = values[31];
        inputs.streamline_height_m = values[32];
        inputs.wake_radius_m = values[33];
        inputs.wake_xshift_m = values[34];
        inputs.initial_sigma_y_m = values[35];
        inputs.initial_sigma_z_m = values[36];
        inputs.release_index = static_cast<int>(values[37]);
        inputs.source_index = static_cast<int>(values[38]);
        inputs.source_type = static_cast<int>(values[39]);
        const auto state = cteas::puff::new_puff_state(inputs);
        std::cout << static_cast<int>(values[0]) << ' ' << state.x_km << ' ' << state.y_km << ' '
                  << state.tibl_height_m << ' ' << state.base_elevation_m << ' ' << state.sigma_y_m
                  << ' ' << state.sigma_z_m << ' ' << state.final_height_m << ' '
                  << state.height_begin_m << ' ' << state.height_end_m << ' ' << state.x_final_m
                  << ' ' << state.final_rise_variance_m2 << ' ' << state.buoyancy_flux << ' '
                  << state.momentum_flux << ' ' << state.x_final_buoyancy_m << ' '
                  << state.x_final_momentum_m << ' ' << state.z_final_buoyancy_m << ' '
                  << state.z_final_momentum_m << ' ' << state.stack_tip_downwash_m << ' '
                  << state.split_flag << ' ' << state.stack_height_m << ' '
                  << state.exit_velocity_ms << ' ' << state.diameter_m << ' '
                  << state.emission_duration_s << ' ' << state.stack_wind_speed_ms << ' '
                  << state.stability_class << ' ' << state.sqrt_stability_s << ' ' << state.urban
                  << ' ' << state.sigma_v_ms << ' ' << state.sigma_w_ms << ' '
                  << state.obukhov_length_m << ' ' << state.plume_path_exponent << ' '
                  << state.wind_ratio << ' ' << state.downwash_code << ' '
                  << state.building_height_m << ' ' << state.building_width_m << ' '
                  << state.effective_height2_m << ' ' << state.streamline_height_m << ' '
                  << state.wake_radius_m << ' ' << state.wake_xshift_m << ' '
                  << state.source_sigma_y_m << ' ' << state.source_sigma_z_m << ' '
                  << state.sigma_y0_m << ' ' << state.sigma_z0_m << ' ' << state.release_index
                  << ' ' << state.source_index << ' ' << state.source_type << '\n';
        ++cases;
    }
    std::cerr << "P7O_STATE_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

// Physical-chain release run: the locked deck's stack and met hour through the
// reconstructed rise (P7N) and release (P7O) chains.
int deck_release_mode(const std::string& met_path, const std::string& control_path, int hour_index,
                      double stack_x_km, double stack_y_km, double stack_height_m,
                      double stack_diameter_m, double stack_exit_velocity_ms,
                      double stack_temperature_k, double emission_rate_bq_s) {
    const auto text = read_text(control_path);
    const auto control = cteas::puff::ControlFile::parse(text);
    const int step_seconds = control.required_int("NSECDT");
    const auto zface = control.required_float_list("ZFACE");

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
    require_true(hour.values.count("ZI") == 1U && hour.values.count("TEMPK") == 1U &&
                     hour.integers.count("IPGT") == 1U,
                 "missing hourly fields for the release run");

    const double spacing = summary.header.dx_m / 1000.0;
    const int cell_i = static_cast<int>((stack_x_km - summary.header.origin_x_m / 1000.0) / spacing);
    const int cell_j = static_cast<int>((stack_y_km - summary.header.origin_y_m / 1000.0) / spacing);
    require_true(cell_i >= 0 && cell_i < summary.header.nx && cell_j >= 0 &&
                     cell_j < summary.header.ny,
                 "stack is outside the met grid");
    const std::size_t cell = static_cast<std::size_t>(cell_j) * summary.header.nx +
                             static_cast<std::size_t>(cell_i);
    int level = 0;
    for (int z = 0; z < summary.header.nz; ++z) {
        if (stack_height_m >= zface[static_cast<std::size_t>(z)] &&
            stack_height_m < zface[static_cast<std::size_t>(z) + 1U]) {
            level = z;
            break;
        }
    }
    const auto level_label = [level](const char* prefix) {
        const std::string number = std::to_string(level + 1);
        return std::string(prefix) + "-LEV" + std::string(3U - number.size(), ' ') + number;
    };
    const auto wind_value = [&hour](const std::string& label, std::size_t index) {
        const auto found = hour.values.find(label);
        require_true(found != hour.values.end(), "missing wind field " + label);
        return static_cast<double>(found->second[index]);
    };
    const double u = wind_value(level_label("U"), cell);
    const double v = wind_value(level_label("V"), cell);
    const double speed = std::sqrt(u * u + v * v);
    require_true(speed > 0.01, "calm hour: the release chain is not meaningful");
    const double mixing_height = static_cast<double>(hour.values.at("ZI")[cell]);
    const double ambient_temperature = static_cast<double>(hour.values.at("TEMPK")[cell]);
    const int stability_class = std::max(1, std::min(6, hour.integers.at("IPGT")[cell]));
    require_true(stability_class <= 4,
                 "the sampled hour is stable (ISTAB >= 5): the stable rise branches need the "
                 "potential-temperature gradient plumbing, which is not reconstructed");

    cteas::puff::StackFluxInputs flux_inputs;
    flux_inputs.diameter_m = stack_diameter_m;
    flux_inputs.exit_velocity_ms = stack_exit_velocity_ms;
    flux_inputs.stack_temperature_k = stack_temperature_k;
    flux_inputs.ambient_temperature_k = ambient_temperature;
    flux_inputs.temperature_excess_k = std::max(0.0, stack_temperature_k - ambient_temperature);
    flux_inputs.momentum_flux_factor = 1.0;
    const auto fluxes = cteas::puff::stack_fluxes(flux_inputs);

    cteas::puff::StackTipInputs tip_inputs;
    tip_inputs.stack_height_m = stack_height_m;
    tip_inputs.diameter_m = stack_diameter_m;
    tip_inputs.momentum_flux = fluxes.momentum_m4s2;
    tip_inputs.exit_velocity_ms = stack_exit_velocity_ms;
    tip_inputs.stack_wind_speed_ms = speed;
    const double tip_downwash = cteas::puff::stack_tip_downwash(tip_inputs);

    cteas::puff::FinalRiseInputs final_inputs;
    final_inputs.exit_velocity_ms = stack_exit_velocity_ms;
    final_inputs.diameter_m = stack_diameter_m;
    final_inputs.momentum_flux = fluxes.momentum_m4s2;
    final_inputs.buoyancy_flux = fluxes.buoyancy_m4s3;
    final_inputs.stack_wind_speed_ms = speed;
    final_inputs.stability_class = stability_class;
    final_inputs.sqrt_stability_s = 0.0;
    const auto final_rise = cteas::puff::final_plume_rise(final_inputs);

    const double ptginv = std::max(0.020, 0.005);
    const double dptinv = ptginv * 30.0;
    cteas::puff::PartialPenetrationInputs penetration_inputs;
    penetration_inputs.final_rise_m = final_rise.z_final_m;
    penetration_inputs.buoyancy_flux = fluxes.buoyancy_m4s3;
    penetration_inputs.stack_wind_speed_ms = speed;
    penetration_inputs.stack_height_m = stack_height_m;
    penetration_inputs.mixing_height_m = mixing_height;
    penetration_inputs.ambient_temperature_k = ambient_temperature;
    penetration_inputs.inversion_gradient_k_per_m = ptginv;
    penetration_inputs.inversion_jump_k = dptinv;
    const auto penetration = cteas::puff::partial_penetration_rise(penetration_inputs);
    const double rise_final = std::min(final_rise.z_final_m, penetration.final_rise_m);
    const double plume_height = stack_height_m - tip_downwash + rise_final;

    // The vendor's release wind is WSNEW = max(WS, W at the final rise) from
    // RLSMET, which is not reconstructed; the stack-height wind is used here and
    // the difference is reported.
    ReleaseCadenceInputs cadence_inputs;
    cadence_inputs.wind_speed_ms = speed;
    cadence_inputs.emission_interval = 1.0;
    cadence_inputs.max_puffs = 99;
    cadence_inputs.hour_seconds = 3600.0;
    const auto cadence = cteas::puff::release_cadence(cadence_inputs);

    InjectionInputs injection_inputs;
    injection_inputs.species_count = 2;
    injection_inputs.emission_duration_s = cadence.emission_duration_s;
    injection_inputs.step_index = 0;
    injection_inputs.effective_height_m = plume_height;
    injection_inputs.max_layer_height_m = penetration.max_height_m;
    injection_inputs.mixing_height_m = mixing_height;
    injection_inputs.mass_fraction_mixed = penetration.mass_fraction_mixed;
    injection_inputs.stability_class = stability_class;
    injection_inputs.gaussian_distribution = control.required_int("MGAUSS");
    injection_inputs.emission_rate = {emission_rate_bq_s, 0.0};
    const auto injection = cteas::puff::inject_emissions(injection_inputs);

    std::cout.precision(17);
    std::cout << "P7O_DECK_RELEASE_RUN=PASS HOUR=" << hour_index
              << " STABILITY=" << stability_class << " SPEED_MS=" << speed
              << " ZI_M=" << mixing_height << " PLUME_HEIGHT_M=" << plume_height
              << " PUFFS_PER_HOUR=" << cadence.puff_count
              << " EMISSION_DURATION_S=" << cadence.emission_duration_s
              << " MGAUSS=" << injection_inputs.gaussian_distribution
              << " PUFF_CODE=" << injection.puff_code
              << " ZIMAX_M=" << injection.unlimited_mixing_height_m
              << " ZIOLD_M=" << injection.previous_mixing_height_m
              << " QM_H3_BQ=" << injection.mixed_layer_mass[0]
              << " QU_H3_BQ=" << injection.above_layer_mass[0]
              << " QM_HE3_BQ=" << injection.mixed_layer_mass[1]
              << " QU_HE3_BQ=" << injection.above_layer_mass[1]
              << " STEP_S=" << step_seconds
              << " AGE_AFTER_ONE_STEP_S=" << cteas::puff::advance_puff_age(0.0, step_seconds)
              << " RELEASE_WIND_IS_STACK_WIND=true RLSMET_NOT_RECONSTRUCTED=true"
              << " PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true\n";
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const std::string mode = argc > 1 ? argv[1] : "";
        if (mode == "--inject-matrix") return inject_matrix();
        if (mode == "--cadence-matrix") return cadence_matrix();
        if (mode == "--state-matrix") return state_matrix();
        if (mode == "--deck-release" && argc == 12) {
            return deck_release_mode(argv[2], argv[3], std::stoi(argv[4]), std::stod(argv[5]),
                                     std::stod(argv[6]), std::stod(argv[7]), std::stod(argv[8]),
                                     std::stod(argv[9]), std::stod(argv[10]), std::stod(argv[11]));
        }
        std::cerr << "Usage: cteas_p7o_probe --inject-matrix | --cadence-matrix | "
                     "--state-matrix |\n  --deck-release MET CONTROL HOUR STACK_X_KM STACK_Y_KM "
                     "STACK_H_M DIAM_M VEXIT_MS TSTAK_K EMISSION_BQ_S\n";
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "P7O_PROBE=FAIL: " << error.what() << '\n';
        return 1;
    }
}
