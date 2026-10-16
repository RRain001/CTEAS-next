// P7Q sigma-update probe: case matrices for the vendor-source parity test plus a
// physical-chain sigma run on the locked case's stack and met hour.
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/dispersion.hpp"
#include "cteas/puff/sigma_update.hpp"

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

using cteas::puff::SigmaAdjustInputs;
using cteas::puff::SigmaCurvePoint;
using cteas::puff::SigmaStepInputs;
using cteas::puff::SigmaUpdateInputs;
using cteas::puff::SigmaYCurve;
using cteas::puff::SigmaZCurve;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7Q cannot read file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

// The deterministic SIGTY/SIGTZ stubs of reference/p7q_oracle_driver.f.
SigmaCurvePoint stub_sigma_y(double sigma_y0_m, double dx_km, double dt_s) {
    const float s0 = static_cast<float>(sigma_y0_m);
    const float dx = static_cast<float>(dx_km);
    const float dt = static_cast<float>(dt_s);
    SigmaCurvePoint point;
    point.value = static_cast<double>(s0 + 0.5F * dx + 0.1F * dt);
    point.virtual_distance_km = static_cast<double>(s0 * 0.01F + 0.002F * dx);
    point.virtual_time_s = static_cast<double>(s0 * 0.5F + 2.0F * dt);
    return point;
}

SigmaCurvePoint stub_sigma_z(double sigma_z0_m, double dx_km, double dt_s, double height_m) {
    const float s0 = static_cast<float>(sigma_z0_m);
    const float dx = static_cast<float>(dx_km);
    const float dt = static_cast<float>(dt_s);
    const float height = static_cast<float>(height_m);
    SigmaCurvePoint point;
    point.value = static_cast<double>(s0 + 0.3F * dx + 0.2F * dt + 0.01F * height);
    point.virtual_distance_km = static_cast<double>(s0 * 0.02F + 0.003F * dx);
    point.virtual_time_s = static_cast<double>(s0 * 0.4F + 3.0F * dt);
    return point;
}

int sigma_matrix() {
    int icase = 0, puff_code = 0;
    double sigma_y = 0.0, sigma_z = 0.0, height = 0.0, mid_time = 0.0, mid_distance = 0.0;
    int cases = 0;
    std::cout.precision(17);
    const SigmaYCurve y = stub_sigma_y;
    const SigmaZCurve z = stub_sigma_z;
    while (std::cin >> icase >> sigma_y >> sigma_z >> height >> mid_time >> mid_distance >>
           puff_code) {
        SigmaStepInputs inputs;
        inputs.sigma_y_start_m = sigma_y;
        inputs.sigma_z_start_m = sigma_z;
        inputs.puff_height_m = height;
        inputs.mid_time_s = mid_time;
        inputs.mid_distance_km = mid_distance;
        inputs.puff_code = puff_code;
        const auto step = cteas::puff::sigma_step(inputs, y, z);
        std::cout << icase << ' ' << step.sigma_y_begin_m << ' ' << step.sigma_y_mid_m << ' '
                  << step.sigma_y_end_m << ' ' << step.virtual_time_y_begin_s << ' '
                  << step.virtual_time_y_mid_s << ' ' << step.virtual_time_y_end_s << ' '
                  << step.virtual_distance_y_begin_km << ' ' << step.virtual_distance_y_mid_km
                  << ' ' << step.virtual_distance_y_end_km << ' ' << step.sigma_z_begin_m << ' '
                  << step.sigma_z_mid_m << ' ' << step.sigma_z_end_m << ' '
                  << step.virtual_time_z_begin_s << ' ' << step.virtual_time_z_mid_s << ' '
                  << step.virtual_time_z_end_s << ' ' << step.virtual_distance_z_begin_km << ' '
                  << step.virtual_distance_z_mid_km << ' ' << step.virtual_distance_z_end_km
                  << '\n';
        ++cases;
    }
    std::cerr << "P7Q_SIGMA_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int sigma_y_matrix() {
    int icase = 0, calm = 0;
    double syb1 = 0.0, sym1 = 0.0, sye1 = 0.0, bid = 0.0, sy0sq = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> syb1 >> sym1 >> sye1 >> bid >> sy0sq >> calm) {
        SigmaAdjustInputs inputs;
        inputs.sigma_y_begin_m = syb1;
        inputs.sigma_y_mid_m = sym1;
        inputs.sigma_y_end_m = sye1;
        inputs.final_rise_variance_m2 = bid;
        inputs.initial_sigma_y_squared_m2 = sy0sq;
        inputs.calm = calm == 1;
        inputs.gaussian_vertical = false;
        const auto adjust = cteas::puff::adjust_sigmas(inputs);
        std::cout << icase << ' ' << adjust.sigma_y_begin_m << ' ' << adjust.sigma_y_mid_m << ' '
                  << adjust.sigma_y_end_m << ' ' << adjust.sigma_y_quadrature_m2 << ' '
                  << adjust.stored_sigma_y_m << ' ' << adjust.minimum_sigma_y_m << '\n';
        ++cases;
    }
    std::cerr << "P7Q_SIGMA_Y_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int sigma_z_matrix() {
    int icase = 0, calm = 0;
    double szb1 = 0.0, szm1 = 0.0, sze1 = 0.0, bid = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> szb1 >> szm1 >> sze1 >> bid >> calm) {
        SigmaAdjustInputs inputs;
        inputs.sigma_z_begin_m = szb1;
        inputs.sigma_z_mid_m = szm1;
        inputs.sigma_z_end_m = sze1;
        inputs.final_rise_variance_m2 = bid;
        inputs.calm = calm == 1;
        inputs.gaussian_vertical = true;
        const auto adjust = cteas::puff::adjust_sigmas(inputs);
        std::cout << icase << ' ' << adjust.sigma_z_begin_m << ' ' << adjust.sigma_z_mid_m << ' '
                  << adjust.sigma_z_end_m << ' ' << adjust.stored_sigma_z_m << ' '
                  << adjust.minimum_sigma_z_m << '\n';
        ++cases;
    }
    std::cerr << "P7Q_SIGMA_Z_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

// Physical-chain sigma run: the locked deck's stack and met hour through the
// reconstructed sigma update. The sigma update is a per-puff quantity; the
// receptor grid enters only through the sampling (P7E).
int deck_sigma_mode(const std::string& met_path, const std::string& control_path, int hour_index,
                    double stack_x_km, double stack_y_km, double stack_height_m,
                    double sigma_y_start_m, double sigma_z_start_m, double final_rise_variance_m2) {
    const auto text = read_text(control_path);
    const auto control = cteas::puff::ControlFile::parse(text);
    const int step_seconds = control.required_int("NSECDT");
    const auto zface = control.required_float_list("ZFACE");
    const auto audit = cteas::puff::audit_dispersion_options(control);
    // The locked deck selects MCTADJ=2, whose strain (CTADJ2) and valley
    // (WALLTRAP) adjustments are NOT reconstructed; the run reports the
    // reconstructed sub-chain and says so instead of hiding the difference.
    const int deck_mctadj = control.required_int("MCTADJ");

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
                 "missing hourly fields for the sigma run");

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
    require_true(speed > 0.01, "calm hour: the sigma chain is not meaningful");
    const int stability_class = std::max(1, std::min(6, hour.integers.at("IPGT")[cell]));
    const bool urban = summary.statics.land_use[cell] >= 10 && summary.statics.land_use[cell] <= 19;

    cteas::puff::DispersionSetup dispersion_setup;
    dispersion_setup.mdisp = audit.mdisp;
    dispersion_setup.sigma_y_heffter_m = audit.sytdep_m;
    dispersion_setup.averaging_factor = 1.0;
    const cteas::puff::SigmaCurves curves(cteas::puff::dispersion_environment(
        dispersion_setup, stability_class, urban, speed));
    const SigmaYCurve y = [&curves](double sigma_y0_m, double dx_km, double dt_s) {
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
    const SigmaZCurve z = [&curves](double sigma_z0_m, double dx_km, double dt_s, double height_m) {
        cteas::puff::DispersionIncrement increment;
        increment.dx_km = dx_km;
        increment.dt_s = dt_s;
        const auto evaluated = curves.sigma_z(sigma_z0_m, height_m, increment);
        SigmaCurvePoint point;
        point.value = evaluated.sigma_z_m;
        point.virtual_time_s = evaluated.virtual_time_z_s;
        point.virtual_distance_km = evaluated.virtual_distance_z_km;
        return point;
    };

    const double step_distance_km = speed * static_cast<double>(step_seconds) / 1000.0;
    SigmaUpdateInputs inputs;
    inputs.step.sigma_y_start_m = sigma_y_start_m;
    inputs.step.sigma_z_start_m = sigma_z_start_m;
    inputs.step.puff_height_m = stack_height_m;
    inputs.step.mid_time_s = 0.5 * static_cast<double>(step_seconds);
    inputs.step.mid_distance_km = 0.5 * step_distance_km;
    inputs.step.puff_code = 1;
    inputs.final_rise_variance_m2 = final_rise_variance_m2;
    inputs.initial_sigma_y_squared_m2 = 0.0;
    inputs.calm = false;
    const auto result = cteas::puff::sigma_update(inputs, y, z);

    std::cout.precision(17);
    std::cout << "P7Q_DECK_SIGMA_RUN=PASS HOUR=" << hour_index
              << " STABILITY=" << stability_class << " URBAN=" << (urban ? "true" : "false")
              << " SPEED_MS=" << speed << " STEP_S=" << step_seconds
              << " STEP_DISTANCE_KM=" << step_distance_km
              << " SIGMA_Y_START_M=" << sigma_y_start_m << " SIGMA_Z_START_M=" << sigma_z_start_m
              << " SYB1_M=" << result.step.sigma_y_begin_m
              << " SYM1_M=" << result.step.sigma_y_mid_m
              << " SYE1_M=" << result.step.sigma_y_end_m
              << " SZB1_M=" << result.step.sigma_z_begin_m
              << " SZM1_M=" << result.step.sigma_z_mid_m
              << " SZE1_M=" << result.step.sigma_z_end_m
              << " VTYE1_S=" << result.step.virtual_time_y_end_s
              << " VDYE1_KM=" << result.step.virtual_distance_y_end_km
              << " VTZE1_S=" << result.step.virtual_time_z_end_s
              << " VDZE1_KM=" << result.step.virtual_distance_z_end_km
              << " SIGYB_STORED_M=" << result.adjust.stored_sigma_y_m
              << " SIGZB_STORED_M=" << result.adjust.stored_sigma_z_m
              << " SYSQ_M2=" << result.adjust.sigma_y_quadrature_m2
              << " DECK_MCTADJ=" << deck_mctadj
              << " MCTADJ2_ADJUSTMENTS_OMITTED="
              << ((deck_mctadj == 2) ? "true" : "false")
              << " PRIME_WAKE_NOT_RECONSTRUCTED=true"
              << " PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true\n";
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const std::string mode = argc > 1 ? argv[1] : "";
        if (mode == "--sigma-matrix") return sigma_matrix();
        if (mode == "--sigma-y-matrix") return sigma_y_matrix();
        if (mode == "--sigma-z-matrix") return sigma_z_matrix();
        if (mode == "--deck-sigma" && argc == 11) {
            return deck_sigma_mode(argv[2], argv[3], std::stoi(argv[4]), std::stod(argv[5]),
                                   std::stod(argv[6]), std::stod(argv[7]), std::stod(argv[8]),
                                   std::stod(argv[9]), std::stod(argv[10]));
        }
        std::cerr << "Usage: cteas_p7q_probe --sigma-matrix | --sigma-y-matrix | "
                     "--sigma-z-matrix |\n  --deck-sigma MET CONTROL HOUR STACK_X_KM STACK_Y_KM "
                     "STACK_H_M SIGMA_Y_START_M SIGMA_Z_START_M BID_M2\n";
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "P7Q_PROBE=FAIL: " << error.what() << '\n';
        return 1;
    }
}
