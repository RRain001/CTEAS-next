// P7P step-bookkeeping probe: case matrices for the vendor-source parity test
// plus a physical-chain step run on the locked case's stack and met hour.
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/dispersion.hpp"
#include "cteas/puff/step.hpp"

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

using cteas::puff::SigmaCurvePoint;
using cteas::puff::SigmaParameterInputs;
using cteas::puff::SigmaYCurve;
using cteas::puff::StepBookkeepingInputs;
using cteas::puff::StepUpdateInputs;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7P cannot read file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

// The deterministic SIGTY stub of reference/p7p_oracle_driver.f, in REAL*4.
SigmaCurvePoint stub_sigma_y(double sigma_y0_m, double dx_km, double dt_s) {
    const float s0 = static_cast<float>(sigma_y0_m);
    const float dx = static_cast<float>(dx_km);
    const float dt = static_cast<float>(dt_s);
    SigmaCurvePoint point;
    point.value = static_cast<double>(s0 + 0.5F * dx + 0.1F * dt);
    point.virtual_distance_km = static_cast<double>(s0 * 0.01F);
    point.virtual_time_s = static_cast<double>(s0 * 0.5F);
    return point;
}

int step_matrix() {
    int icase = 0, downwash = 0, idopty = 0, idoptz = 0;
    double total_distance = 0.0, total_time = 0.0, step_distance = 0.0, step_seconds = 0.0;
    double km_per_m = 0.0, wind = 0.0, calm_threshold = 0.0, x_final = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> total_distance >> total_time >> step_distance >> step_seconds >>
           km_per_m >> wind >> calm_threshold >> downwash >> x_final >> idopty >> idoptz) {
        StepBookkeepingInputs inputs;
        inputs.total_distance_m = total_distance;
        inputs.total_time_s = total_time;
        inputs.step_distance_m = step_distance;
        inputs.step_seconds = step_seconds;
        inputs.km_per_m = km_per_m;
        inputs.wind_speed_ms = wind;
        inputs.calm_wind_threshold = calm_threshold;
        inputs.downwash_code = downwash;
        inputs.x_final_m = x_final;
        inputs.dispersion_y_option = idopty;
        inputs.dispersion_z_option = idoptz;
        const auto result = cteas::puff::step_bookkeeping(inputs);
        std::cout << icase << ' ' << result.dispersion_y_option << ' '
                  << result.dispersion_z_option << ' ' << result.downwash_code << ' '
                  << result.distance_begin_m << ' ' << result.distance_end_m << ' '
                  << result.time_begin_s << ' ' << result.time_end_s << ' '
                  << result.mid_distance_km << ' ' << result.mid_time_s << ' '
                  << (result.calm ? 1 : 0) << ' ' << result.mean_speed_ms << ' '
                  << result.speed_kps << ' ' << result.x_final_m << '\n';
        ++cases;
    }
    std::cerr << "P7P_STEP_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int update_matrix() {
    int icase = 0, tilt = 0;
    double height = 0.0, settling = 0.0, step_seconds = 0.0, step_distance = 0.0;
    double total_distance = 0.0, total_time = 0.0, x_new = 0.0, y_new = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> height >> settling >> tilt >> step_seconds >> step_distance >>
           total_distance >> total_time >> x_new >> y_new) {
        StepUpdateInputs inputs;
        inputs.height_end_m = height;
        inputs.settling_velocity_ms = settling;
        inputs.plume_tilt = tilt;
        inputs.step_seconds = step_seconds;
        inputs.step_distance_m = step_distance;
        inputs.total_distance_m = total_distance;
        inputs.total_time_s = total_time;
        inputs.x_new_km = x_new;
        inputs.y_new_km = y_new;
        const auto result = cteas::puff::apply_step_update(inputs);
        std::cout << icase << ' ' << result.height_end_m << ' ' << result.total_distance_m << ' '
                  << result.total_time_s << ' ' << result.x_km << ' ' << result.y_km << ' '
                  << result.z_km << '\n';
        ++cases;
    }
    std::cerr << "P7P_UPDATE_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int setcsig_matrix() {
    int icase = 0, idopty = 0, idoptz = 0, urban = 0, stability = 0;
    double speed = 0.0, obukhov = 0.0, bvf = 0.0, sigma_v = 0.0, sigma_w = 0.0;
    double min_sy = 0.0, min_sz = 0.0, height = 0.0, mixing = 0.0;
    int ix = 0, iy = 0, md = 0, heffter = 0, tau_ly = 0;
    int cases = 0;
    std::cout.precision(17);
    const SigmaYCurve curve = stub_sigma_y;
    while (std::cin >> icase >> idopty >> idoptz >> urban >> speed >> stability >> obukhov >> bvf >>
           sigma_v >> sigma_w >> min_sy >> min_sz >> height >> mixing >> ix >> iy >> md >>
           heffter >> tau_ly) {
        SigmaParameterInputs inputs;
        inputs.dispersion_y_option = idopty;
        inputs.dispersion_z_option = idoptz;
        inputs.urban = urban;
        inputs.mean_speed_ms = speed;
        inputs.stability_class = stability;
        inputs.obukhov_length_m = obukhov;
        inputs.brunt_vaisala_s = bvf;
        inputs.sigma_v_ms = sigma_v;
        inputs.sigma_w_ms = sigma_w;
        inputs.min_sigma_y_m = min_sy;
        inputs.min_sigma_z_m = min_sz;
        inputs.height_m = height;
        inputs.mixing_height_m = mixing;
        inputs.cell_x = ix;
        inputs.cell_y = iy;
        inputs.met_domain = md;
        inputs.heffter_sigma_z = heffter;
        inputs.tau_ly = tau_ly;
        inputs.sigma_y_heffter_m = 300.0;   // the vendor BLOCK DATA value
        const auto state = cteas::puff::set_sigma_parameters(inputs, curve);
        const auto point = stub_sigma_y(300.0, 0.0, 0.0);
        std::cout << icase << ' ' << state.dispersion_y_option << ' ' << state.dispersion_z_option
                  << ' ' << state.urban << ' ' << state.stability_class << ' ' << state.heffter_sigma_z
                  << ' ' << state.cell_x << ' ' << state.cell_y << ' ' << state.met_domain << ' '
                  << state.mean_speed_ms << ' ' << state.obukhov_length_m << ' '
                  << state.brunt_vaisala_s << ' ' << state.sigma_v_ms << ' ' << state.sigma_w_ms
                  << ' ' << state.min_sigma_y_m << ' ' << state.min_sigma_z_m << ' '
                  << state.heffter_transition_time_s << ' ' << 300.0 << ' ' << 0.0 << ' ' << 0.0
                  << ' ' << point.value << ' ' << point.virtual_time_s << ' '
                  << point.virtual_distance_km << '\n';
        ++cases;
    }
    std::cerr << "P7P_SETCSIG_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

// Physical-chain step run: the locked deck's stack and met hour through the
// reconstructed step bookkeeping and /CSIGMA/ selection.
int deck_step_mode(const std::string& met_path, const std::string& control_path, int hour_index,
                   double stack_x_km, double stack_y_km, double stack_height_m) {
    const auto text = read_text(control_path);
    const auto control = cteas::puff::ControlFile::parse(text);
    const int step_seconds = control.required_int("NSECDT");
    const auto zface = control.required_float_list("ZFACE");
    const auto audit = cteas::puff::audit_dispersion_options(control);

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
    require_true(hour.values.count("ZI") == 1U && hour.integers.count("IPGT") == 1U,
                 "missing hourly fields for the step run");

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
    require_true(speed > 0.01, "calm hour: the step chain is not meaningful");
    const double mixing_height = static_cast<double>(hour.values.at("ZI")[cell]);
    const int stability_class = std::max(1, std::min(6, hour.integers.at("IPGT")[cell]));
    const bool urban = summary.statics.land_use[cell] >= 10 && summary.statics.land_use[cell] <= 19;

    const double step_distance_m = speed * static_cast<double>(step_seconds);
    StepBookkeepingInputs bookkeeping;
    bookkeeping.total_distance_m = 0.0;
    bookkeeping.total_time_s = 0.0;
    bookkeeping.step_distance_m = step_distance_m;
    bookkeeping.step_seconds = static_cast<double>(step_seconds);
    bookkeeping.km_per_m = 0.001;
    bookkeeping.wind_speed_ms = speed;
    bookkeeping.calm_wind_threshold = 0.5;   // the vendor BLOCK DATA value
    bookkeeping.downwash_code = 0;
    bookkeeping.x_final_m = 0.0;
    bookkeeping.dispersion_y_option = audit.mdisp;
    bookkeeping.dispersion_z_option = audit.mdisp;
    const auto step = cteas::puff::step_bookkeeping(bookkeeping);

    cteas::puff::DispersionSetup dispersion_setup;
    dispersion_setup.mdisp = audit.mdisp;
    dispersion_setup.sigma_y_heffter_m = audit.sytdep_m;
    dispersion_setup.averaging_factor = 1.0;
    const cteas::puff::SigmaCurves curves(cteas::puff::dispersion_environment(
        dispersion_setup, stability_class, urban, speed));
    const SigmaYCurve curve = [&curves](double sigma_y0_m, double dx_km, double dt_s) {
        cteas::puff::DispersionIncrement increment;
        increment.dx_km = dx_km;
        increment.dt_s = dt_s;
        const auto evaluated = curves.sigma_y(sigma_y0_m, increment);
        SigmaCurvePoint point;
        point.value = evaluated.sigma_y_m;
        point.virtual_time_s = evaluated.virtual_time_y_s;
        point.virtual_distance_km = evaluated.virtual_distance_y_km;
        return point;
    };

    SigmaParameterInputs sigma_inputs;
    sigma_inputs.dispersion_y_option = audit.mdisp;
    sigma_inputs.dispersion_z_option = audit.mdisp;
    sigma_inputs.urban = urban ? 1 : 0;
    sigma_inputs.mean_speed_ms = speed;
    sigma_inputs.stability_class = stability_class;
    sigma_inputs.obukhov_length_m = static_cast<double>(hour.values.count("EL") == 1U
                                                            ? hour.values.at("EL")[cell]
                                                            : 0.0);
    sigma_inputs.brunt_vaisala_s = 0.0;
    sigma_inputs.sigma_v_ms = 0.0;
    sigma_inputs.sigma_w_ms = 0.0;
    sigma_inputs.min_sigma_y_m = 1.0;   // the vendor COMPARM defaults (symin/szmin = 1)
    sigma_inputs.min_sigma_z_m = 1.0;
    sigma_inputs.height_m = stack_height_m;
    sigma_inputs.mixing_height_m = mixing_height;
    sigma_inputs.cell_x = cell_i + 1;
    sigma_inputs.cell_y = cell_j + 1;
    sigma_inputs.met_domain = 1;
    sigma_inputs.heffter_sigma_z = audit.mhftsz;
    sigma_inputs.tau_ly = 0;
    sigma_inputs.sigma_y_heffter_m = audit.sytdep_m;
    const auto sigma_state = cteas::puff::set_sigma_parameters(sigma_inputs, curve);

    StepUpdateInputs update;
    update.height_end_m = stack_height_m;
    update.settling_velocity_ms = 0.0;   // gases: no gravitational settling
    update.plume_tilt = control.required_int("MTILT");
    update.step_seconds = static_cast<double>(step_seconds);
    update.step_distance_m = step_distance_m;
    update.total_distance_m = 0.0;
    update.total_time_s = 0.0;
    update.x_new_km = stack_x_km + step_distance_m * 0.001 * (u / speed);
    update.y_new_km = stack_y_km + step_distance_m * 0.001 * (v / speed);
    const auto updated = cteas::puff::apply_step_update(update);

    std::cout.precision(17);
    std::cout << "P7P_DECK_STEP_RUN=PASS HOUR=" << hour_index
              << " STABILITY=" << stability_class << " URBAN=" << (urban ? "true" : "false")
              << " SPEED_MS=" << speed << " ZI_M=" << mixing_height
              << " STEP_S=" << step_seconds << " STEP_DISTANCE_M=" << step_distance_m
              << " CALM=" << (step.calm ? "true" : "false")
              << " UAVG_MS=" << step.mean_speed_ms << " UKPS=" << step.speed_kps
              << " XTTB1_M=" << step.distance_begin_m << " XTTE1_M=" << step.distance_end_m
              << " TB1_S=" << step.time_begin_s << " TE1_S=" << step.time_end_s
              << " DMIDKM=" << step.mid_distance_km << " TMID_S=" << step.mid_time_s
              << " IDOPTYS=" << sigma_state.dispersion_y_option
              << " IRUS=" << sigma_state.urban << " KSTABS=" << sigma_state.stability_class
              << " SZH_M=" << sigma_state.sigma_z_heffter_m
              << " THFTY_S=" << sigma_state.heffter_transition_time_s
              << " DHFTY_KM=" << sigma_state.heffter_transition_distance_km
              << " XPB_KM=" << updated.x_km << " YPB_KM=" << updated.y_km
              << " ZPB_M=" << updated.z_km << " XTOTB_M=" << updated.total_distance_m
              << " TMTOTB_S=" << updated.total_time_s
              << " SIGMA_UPDATE_NOT_RECONSTRUCTED=true"
              << " PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true\n";
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const std::string mode = argc > 1 ? argv[1] : "";
        if (mode == "--step-matrix") return step_matrix();
        if (mode == "--update-matrix") return update_matrix();
        if (mode == "--setcsig-matrix") return setcsig_matrix();
        if (mode == "--deck-step" && argc == 8) {
            return deck_step_mode(argv[2], argv[3], std::stoi(argv[4]), std::stod(argv[5]),
                                  std::stod(argv[6]), std::stod(argv[7]));
        }
        std::cerr << "Usage: cteas_p7p_probe --step-matrix | --update-matrix | "
                     "--setcsig-matrix |\n  --deck-step MET CONTROL HOUR STACK_X_KM STACK_Y_KM "
                     "STACK_H_M\n";
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "P7P_PROBE=FAIL: " << error.what() << '\n';
        return 1;
    }
}
