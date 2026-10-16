// P7N plume-rise probe: case matrices for the vendor-source parity test plus a
// physical-chain rise run on the locked case's stack and met hour.
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/plume_rise.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using cteas::puff::BuoyantRiseInputs;
using cteas::puff::FinalRiseInputs;
using cteas::puff::MomentumRiseInputs;
using cteas::puff::PartialPenetrationInputs;
using cteas::puff::PlumeRiseState;
using cteas::puff::StackFluxInputs;
using cteas::puff::StackTipInputs;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7N cannot read file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

int stktip_matrix() {
    int icase = 0;
    double stack_height = 0.0, diameter = 0.0, momentum_flux = 0.0, exit_velocity = 0.0;
    double wind = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> stack_height >> diameter >> momentum_flux >> exit_velocity >> wind) {
        StackTipInputs inputs;
        inputs.stack_height_m = stack_height;
        inputs.diameter_m = diameter;
        inputs.momentum_flux = momentum_flux;
        inputs.exit_velocity_ms = exit_velocity;
        inputs.stack_wind_speed_ms = wind;
        std::cout << icase << ' ' << cteas::puff::stack_tip_downwash(inputs) << '\n';
        ++cases;
    }
    std::cerr << "P7N_STKTIP_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int prfin_matrix() {
    int icase = 0, stability = 0;
    double exit_velocity = 0.0, diameter = 0.0, momentum_flux = 0.0, buoyancy_flux = 0.0;
    double wind = 0.0, sqrts = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> exit_velocity >> diameter >> momentum_flux >> buoyancy_flux >> wind
           >> stability >> sqrts) {
        FinalRiseInputs inputs;
        inputs.exit_velocity_ms = exit_velocity;
        inputs.diameter_m = diameter;
        inputs.momentum_flux = momentum_flux;
        inputs.buoyancy_flux = buoyancy_flux;
        inputs.stack_wind_speed_ms = wind;
        inputs.stability_class = stability;
        inputs.sqrt_stability_s = sqrts;
        const auto result = cteas::puff::final_plume_rise(inputs);
        std::cout << icase << ' ' << result.x_final_momentum_m << ' ' << result.x_final_buoyancy_m
                  << ' ' << result.x_final_m << ' ' << result.z_final_momentum_m << ' '
                  << result.z_final_buoyancy_m << ' ' << result.z_final_m << '\n';
        ++cases;
    }
    std::cerr << "P7N_PRFIN_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int prm_matrix() {
    int icase = 0, stability = 0;
    double diameter = 0.0, exit_velocity = 0.0, momentum_flux = 0.0, wind = 0.0, sqrts = 0.0;
    double x = 0.0, x_final = 0.0, z_final = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> diameter >> exit_velocity >> momentum_flux >> wind >> stability >>
           sqrts >> x >> x_final >> z_final) {
        MomentumRiseInputs inputs;
        inputs.diameter_m = diameter;
        inputs.exit_velocity_ms = exit_velocity;
        inputs.momentum_flux = momentum_flux;
        inputs.stack_wind_speed_ms = wind;
        inputs.stability_class = stability;
        inputs.sqrt_stability_s = sqrts;
        inputs.x_m = x;
        inputs.x_final_momentum_m = x_final;
        inputs.z_final_momentum_m = z_final;
        std::cout << icase << ' ' << cteas::puff::transitional_momentum_rise(inputs) << '\n';
        ++cases;
    }
    std::cerr << "P7N_PRM_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int prb_matrix() {
    int icase = 0;
    double buoyancy_flux = 0.0, wind = 0.0, x = 0.0, x_final = 0.0, z_final = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> buoyancy_flux >> wind >> x >> x_final >> z_final) {
        BuoyantRiseInputs inputs;
        inputs.buoyancy_flux = buoyancy_flux;
        inputs.stack_wind_speed_ms = wind;
        inputs.x_m = x;
        inputs.x_final_buoyancy_m = x_final;
        inputs.z_final_buoyancy_m = z_final;
        std::cout << icase << ' ' << cteas::puff::transitional_buoyant_rise(inputs) << '\n';
        ++cases;
    }
    std::cerr << "P7N_PRB_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int prfpp_matrix() {
    int icase = 0;
    double zfin = 0.0, buoyancy_flux = 0.0, wind = 0.0, stack_height = 0.0, mixing_height = 0.0;
    double temperature = 0.0, gradient = 0.0, jump = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> zfin >> buoyancy_flux >> wind >> stack_height >> mixing_height >>
           temperature >> gradient >> jump) {
        PartialPenetrationInputs inputs;
        inputs.final_rise_m = zfin;
        inputs.buoyancy_flux = buoyancy_flux;
        inputs.stack_wind_speed_ms = wind;
        inputs.stack_height_m = stack_height;
        inputs.mixing_height_m = mixing_height;
        inputs.ambient_temperature_k = temperature;
        inputs.inversion_gradient_k_per_m = gradient;
        inputs.inversion_jump_k = jump;
        const auto result = cteas::puff::partial_penetration_rise(inputs);
        std::cout << icase << ' ' << result.final_rise_m << ' ' << result.mass_fraction_mixed << ' '
                  << result.max_height_m << '\n';
        ++cases;
    }
    std::cerr << "P7N_PRFPP_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int flux_matrix() {
    int icase = 0;
    double diameter = 0.0, exit_velocity = 0.0, stack_temperature = 0.0, excess = 0.0;
    double ambient = 0.0, factor = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> diameter >> exit_velocity >> stack_temperature >> excess >> ambient >>
           factor) {
        StackFluxInputs inputs;
        inputs.diameter_m = diameter;
        inputs.exit_velocity_ms = exit_velocity;
        inputs.stack_temperature_k = stack_temperature;
        inputs.temperature_excess_k = excess;
        inputs.ambient_temperature_k = ambient;
        inputs.momentum_flux_factor = factor;
        const auto result = cteas::puff::stack_fluxes(inputs);
        std::cout << icase << ' ' << result.buoyancy_m4s3 << ' ' << result.momentum_m4s2 << '\n';
        ++cases;
    }
    std::cerr << "P7N_FLUX_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int grise_matrix() {
    int icase = 0;
    double field[21];
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase) {
        for (double& value : field) {
            if (!(std::cin >> value)) return 0;
        }
        PlumeRiseState state;
        state.source_type = static_cast<int>(field[0]);
        state.downwash_code = static_cast<int>(field[1]);
        state.met_period = static_cast<int>(field[2]);
        state.rise_method = static_cast<int>(field[3]);
        state.shear_flag = static_cast<int>(field[4]);
        state.x_m = field[5];
        state.final_rise_m = field[6];
        state.full_final_rise_m = field[7];
        state.stack_height_m = field[8];
        state.diameter_m = field[9];
        state.exit_velocity_ms = field[10];
        state.stack_wind_speed_ms = field[11];
        state.stability_class = static_cast<int>(field[12]);
        state.sqrt_stability_s = field[13];
        state.momentum_flux = field[14];
        state.x_final_momentum_m = field[15];
        state.z_final_momentum_m = field[16];
        state.buoyancy_flux = field[17];
        state.x_final_buoyancy_m = field[18];
        state.z_final_buoyancy_m = field[19];
        state.stack_tip_downwash_m = field[20];
        const auto result = cteas::puff::gradual_plume_height(state);
        std::cout << icase << ' ' << result.height_m << ' ' << result.rise_fraction << '\n';
        ++cases;
    }
    std::cerr << "P7N_GRISE_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

// Physical-chain rise run: the locked case's own stack, its own met hour, and
// the reconstructed Briggs rise path (MTRANS=1, MTIP=1, MRISE=1, MPARTL=1).
// Explicitly NOT a comparison with the frozen puff.con.
int deck_rise_mode(const std::string& met_path, const std::string& control_path, int hour_index,
                   double stack_x_km, double stack_y_km, double stack_height_m,
                   double stack_diameter_m, double stack_exit_velocity_ms,
                   double stack_temperature_k) {
    const auto text = read_text(control_path);
    const auto control = cteas::puff::ControlFile::parse(text);
    const int step_seconds = control.required_int("NSECDT");
    const auto zface = control.required_float_list("ZFACE");
    require_true(control.required_int("MTRANS") == 1 && control.required_int("MTIP") == 1 &&
                     control.required_int("MRISE") == 1,
                 "the deck does not select the reconstructed gradual-rise path");

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
                 "missing hourly fields for the rise run");

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
    require_true(speed > 0.01, "calm hour: the rise path is not meaningful");
    const double mixing_height = static_cast<double>(hour.values.at("ZI")[cell]);
    const double ambient_temperature = static_cast<double>(hour.values.at("TEMPK")[cell]);
    const int stability_class = std::max(1, std::min(6, hour.integers.at("IPGT")[cell]));

    StackFluxInputs flux_inputs;
    flux_inputs.diameter_m = stack_diameter_m;
    flux_inputs.exit_velocity_ms = stack_exit_velocity_ms;
    flux_inputs.stack_temperature_k = stack_temperature_k;
    flux_inputs.ambient_temperature_k = ambient_temperature;
    flux_inputs.temperature_excess_k = std::max(0.0, stack_temperature_k - ambient_temperature);
    flux_inputs.momentum_flux_factor = 1.0;
    const auto fluxes = cteas::puff::stack_fluxes(flux_inputs);

    StackTipInputs tip_inputs;
    tip_inputs.stack_height_m = stack_height_m;
    tip_inputs.diameter_m = stack_diameter_m;
    tip_inputs.momentum_flux = fluxes.momentum_m4s2;
    tip_inputs.exit_velocity_ms = stack_exit_velocity_ms;
    tip_inputs.stack_wind_speed_ms = speed;
    const double tip_downwash = cteas::puff::stack_tip_downwash(tip_inputs);

    // The stable branches (ISTAB >= 5) need the potential-temperature gradient
    // of the layer below the stack top, which the vendor obtains from the met
    // model or the default PTGRAD0; that plumbing is not reconstructed here, so
    // the run fails closed instead of inventing a gradient.
    require_true(stability_class <= 4,
                 "the sampled hour is stable (ISTAB >= 5): the stable rise branches need the "
                 "potential-temperature gradient plumbing, which is not reconstructed");

    FinalRiseInputs final_inputs;
    final_inputs.exit_velocity_ms = stack_exit_velocity_ms;
    final_inputs.diameter_m = stack_diameter_m;
    final_inputs.momentum_flux = fluxes.momentum_m4s2;
    final_inputs.buoyancy_flux = fluxes.buoyancy_m4s3;
    final_inputs.stack_wind_speed_ms = speed;
    final_inputs.stability_class = stability_class;
    final_inputs.sqrt_stability_s = 0.0;   // unused by the neutral/unstable branches
    const auto final_rise = cteas::puff::final_plume_rise(final_inputs);

    // Partial penetration (MPARTL=1) with the vendor's default gradient path
    // (PTGRAD0 = 0.005 K/m, JSUP = 5 -> PTGINV = max(PTG0(1), PTGRAD0) = 0.020 K/m,
    // DZINV = 30 m -> DPTINV = 0.6 K); the met-model gradient (PTLAPS) is not
    // reconstructed.
    const double ptginv = std::max(0.020, 0.005);
    const double dptinv = ptginv * 30.0;
    PartialPenetrationInputs penetration_inputs;
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

    // Gradual rise at a range of downwind distances, including the distances the
    // reconstructed step covers (5.026 km for the sampled hour).
    const double step_distance_m = speed * static_cast<double>(step_seconds);
    const double distances[] = {100.0, 500.0, 1000.0, step_distance_m, 10000.0};
    std::cout.precision(17);
    std::cout << "P7N_DECK_RISE_RUN=PASS HOUR=" << hour_index << " STABILITY=" << stability_class
              << " SPEED_MS=" << speed << " AMBIENT_K=" << ambient_temperature
              << " ZI_M=" << mixing_height << " STACK_H_M=" << stack_height_m
              << " DIAM_M=" << stack_diameter_m << " VEXIT_MS=" << stack_exit_velocity_ms
              << " TSTAK_K=" << stack_temperature_k
              << " TEMP_EXCESS_K=" << flux_inputs.temperature_excess_k
              << " FLUXB=" << fluxes.buoyancy_m4s3 << " FLUXM=" << fluxes.momentum_m4s2
              << " TIPDW_M=" << tip_downwash
              << " XFIN_M=" << final_rise.x_final_m
              << " ZFIN_M=" << final_rise.z_final_m
              << " ZFIN_MOMENTUM_M=" << final_rise.z_final_momentum_m
              << " ZFIN_BUOYANCY_M=" << final_rise.z_final_buoyancy_m
              << " FMIX=" << penetration.mass_fraction_mixed
              << " ZFIN_PARTIAL_M=" << penetration.final_rise_m
              << " PLUME_HEIGHT_M=" << plume_height
              << " PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true\n";
    for (const double distance : distances) {
        PlumeRiseState state;
        state.source_type = 1;
        state.downwash_code = 0;
        state.met_period = 1;
        state.rise_method = 1;
        state.shear_flag = 0;
        state.x_m = distance;
        // ZFINAL is the stored plume height (only read by the method-0 path).
        state.final_rise_m = stack_height_m - tip_downwash + rise_final;
        state.full_final_rise_m = rise_final;
        state.stack_height_m = stack_height_m;
        state.diameter_m = stack_diameter_m;
        state.exit_velocity_ms = stack_exit_velocity_ms;
        state.stack_wind_speed_ms = speed;
        state.stability_class = stability_class;
        state.sqrt_stability_s = 0.0;
        state.momentum_flux = fluxes.momentum_m4s2;
        state.buoyancy_flux = fluxes.buoyancy_m4s3;
        state.x_final_momentum_m = final_rise.x_final_momentum_m;
        state.z_final_momentum_m = final_rise.z_final_momentum_m;
        state.x_final_buoyancy_m = final_rise.x_final_buoyancy_m;
        state.z_final_buoyancy_m = final_rise.z_final_buoyancy_m;
        state.stack_tip_downwash_m = tip_downwash;
        const auto gradual = cteas::puff::gradual_plume_height(state);
        std::cout << "P7N_DECK_GRADUAL_RISE X_M=" << distance << " HEIGHT_M=" << gradual.height_m
                  << " RISE_FRACTION=" << gradual.rise_fraction << '\n';
    }
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const std::string mode = argc > 1 ? argv[1] : "";
        if (mode == "--stktip-matrix") return stktip_matrix();
        if (mode == "--prfin-matrix") return prfin_matrix();
        if (mode == "--prm-matrix") return prm_matrix();
        if (mode == "--prb-matrix") return prb_matrix();
        if (mode == "--prfpp-matrix") return prfpp_matrix();
        if (mode == "--flux-matrix") return flux_matrix();
        if (mode == "--grise-matrix") return grise_matrix();
        if (mode == "--deck-rise" && argc == 11) {
            return deck_rise_mode(argv[2], argv[3], std::stoi(argv[4]), std::stod(argv[5]),
                                  std::stod(argv[6]), std::stod(argv[7]), std::stod(argv[8]),
                                  std::stod(argv[9]), std::stod(argv[10]));
        }
        std::cerr << "Usage: cteas_p7n_probe --stktip-matrix | --prfin-matrix | --prm-matrix |\n"
                     "  --prb-matrix | --prfpp-matrix | --flux-matrix | --grise-matrix |\n"
                     "  --deck-rise MET CONTROL HOUR STACK_X_KM STACK_Y_KM STACK_H_M DIAM_M "
                     "VEXIT_MS TSTAK_K\n";
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "P7N_PROBE=FAIL: " << error.what() << '\n';
        return 1;
    }
}
