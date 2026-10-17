// P7M CTSG kernel probe: case matrices for the vendor-source parity test plus a
// physical-chain run on the locked case's receptor grid.
//
// The matrix modes read the same case lines the Fortran oracle driver reads and
// write `icase <values>` lines, so tests/p7m_parity_tests.py can diff the two
// independently. The SIGMA matrix uses the same deterministic SIGTY/SIGTZ stubs
// the oracle driver defines; the vendor curves themselves are P7D's.
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/coupling.hpp"
#include "cteas/puff/ctsg.hpp"
#include "cteas/puff/dispersion.hpp"
#include "cteas/puff/receptors.hpp"

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

using cteas::puff::CtsgInputs;
using cteas::puff::CtsgResult;
using cteas::puff::CtsgState;
using cteas::puff::SigmaCurvePoint;
using cteas::puff::SigmaYCurve;
using cteas::puff::SigmaZCurve;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7M cannot read file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

// The deterministic SIGTY/SIGTZ stubs of reference/p7m_oracle_driver.f, in
// REAL*4 like the vendor routines.
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

SigmaCurvePoint stub_sigma_z(double sigma_z0_m, double dx_km, double dt_s, double height_m) {
    const float s0 = static_cast<float>(sigma_z0_m);
    const float dx = static_cast<float>(dx_km);
    const float dt = static_cast<float>(dt_s);
    const float height = static_cast<float>(height_m);
    SigmaCurvePoint point;
    point.value = static_cast<double>(s0 + 0.3F * dx + 0.2F * dt + 0.01F * height);
    point.virtual_distance_km = static_cast<double>(s0 * 0.02F);
    point.virtual_time_s = static_cast<double>(s0 * 0.4F);
    return point;
}

const SigmaYCurve& stub_y() {
    static const SigmaYCurve curve = stub_sigma_y;
    return curve;
}

const SigmaZCurve& stub_z() {
    static const SigmaZCurve curve = stub_sigma_z;
    return curve;
}

// The fixed-order /CTPASS/ state line shared with the oracle driver.
CtsgState state_from(const std::vector<double>& values, std::size_t offset) {
    require_true(values.size() >= offset + 46U, "state line needs 46 fields");
    const double* field = values.data() + offset;
    CtsgState state;
    state.tstart = field[0];
    state.tstep = field[1];
    state.u = field[2];
    state.q = field[3];
    state.zlid = field[4];
    state.frac = field[5];
    state.sz1 = field[6];
    state.sz2 = field[7];
    state.sy1 = field[8];
    state.sy2 = field[9];
    state.szr = field[10];
    state.syr = field[11];
    state.szmn = field[12];
    state.symn = field[13];
    state.hd = field[14];
    state.ubyn = field[15];
    state.h = field[16];
    state.zgrid = field[17];
    state.xc = field[18];
    state.yc = field[19];
    state.rotflo = field[20];
    state.rotang = field[21];
    state.alfw = field[22];
    state.beta = field[23];
    state.cbeta = field[24];
    state.d = field[25];
    state.baxi = field[26];
    state.r = field[27];
    state.x12f = field[28];
    state.x23f = field[29];
    state.xob = field[30];
    state.xp = field[31];
    state.yp = field[32];
    state.zpuff = field[33];
    state.xpf = field[34];
    state.ypf = field[35];
    state.t12p = field[36];
    state.timpg = field[37];
    state.szimpg = field[38];
    state.syimpg = field[39];
    state.xr = field[40];
    state.yr = field[41];
    state.zrec = field[42];
    state.isc = static_cast<int>(field[43]);
    state.ih = static_cast<int>(field[44]);
    state.ip = static_cast<int>(field[45]);
    return state;
}

int munu_matrix() {
    int icase = 0;
    int muflag = 0;
    double xbi = 0.0, ybi = 0.0, axis_ratio = 0.0;
    int cases = 0;
    std::cout.precision(17);
    while (std::cin >> icase >> muflag >> xbi >> ybi >> axis_ratio) {
        const auto coordinates =
            cteas::puff::elliptic_coordinates(muflag, xbi, ybi, axis_ratio);
        std::cout << icase << ' ' << coordinates.mu << ' ' << coordinates.nu << '\n';
        ++cases;
    }
    std::cerr << "P7M_MUNU_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int bi_matrix() {
    int icase = 0;
    double afac = 0.0;
    double argm = 0.0;
    double argp = 0.0;
    int cases = 0;
    while (std::cin >> icase >> afac >> argm >> argp) {
        std::cout.precision(17);
        std::cout << icase << ' ' << cteas::puff::reflection_b(afac, argm, argp) << '\n';
        ++cases;
    }
    std::cerr << "P7M_BI_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int bji_matrix() {
    int icase = 0;
    double ak = 0.0, dm = 0.0, dp = 0.0, d0 = 0.0, eoimh = 0.0, eoiph = 0.0, ej = 0.0;
    double szesq = 0.0, szosq = 0.0, szpsq = 0.0;
    int cases = 0;
    // The vendor BJI reads SZESQ and SZOSQ from /CTPASS/ and never reads SZPSQ;
    // the field is still part of the shared case line.
    while (std::cin >> icase >> ak >> dm >> dp >> d0 >> eoimh >> eoiph >> ej >> szesq >> szosq >>
           szpsq) {
        require_true(std::isfinite(szpsq), "szpsq must be finite");
        std::cout.precision(17);
        std::cout << icase << ' '
                  << cteas::puff::reflection_bji(ak, dm, dp, d0, eoimh, eoiph, ej, szesq, szosq)
                  << '\n';
        ++cases;
    }
    std::cerr << "P7M_BJI_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int bjil_matrix() {
    int icase = 0;
    double ak = 0.0, b1 = 0.0, ej = 0.0, eoi = 0.0, szsq = 0.0, szosq = 0.0, szpsq = 0.0;
    int cases = 0;
    while (std::cin >> icase >> ak >> b1 >> ej >> eoi >> szsq >> szosq >> szpsq) {
        std::cout.precision(17);
        std::cout << icase << ' '
                  << cteas::puff::reflection_bjil(ak, b1, ej, eoi, szsq, szosq, szpsq) << '\n';
        ++cases;
    }
    std::cerr << "P7M_BJIL_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int sigma_matrix() {
    int icase = 0, itype = 0;
    double zpuff = 0.0, ws = 0.0, t = 0.0, s1 = 0.0, tstart = 0.0, s2 = 0.0, tstep = 0.0, sr = 0.0;
    double frac = 0.0;
    int cases = 0;
    while (std::cin >> icase >> itype >> zpuff >> ws >> t >> s1 >> tstart >> s2 >> tstep >> sr >>
           frac) {
        std::cout.precision(17);
        std::cout << icase << ' '
                  << cteas::puff::sigma_restart(itype, zpuff, ws, t, s1, tstart, s2, tstep, sr,
                                                frac, stub_y(), stub_z())
                  << '\n';
        ++cases;
    }
    std::cerr << "P7M_SIGMA_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int ireg_matrix() {
    int icase = 0;
    double x = 0.0, x12 = 0.0, x23 = 0.0;
    int cases = 0;
    while (std::cin >> icase >> x >> x12 >> x23) {
        std::cout << icase << ' ' << cteas::puff::region_index(x, x12, x23) << '\n';
        ++cases;
    }
    std::cerr << "P7M_IREG_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int ctrec_matrix() {
    std::cout.precision(17);
    int cases = 0;
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.find_first_not_of(" \t\r\n") == std::string::npos) continue;
        std::istringstream fields(line);
        std::vector<double> values;
        double value = 0.0;
        while (fields >> value) values.push_back(value);
        if (values.size() < 47U) continue;
        CtsgState state = state_from(values, 1);
        cteas::puff::receptor_geometry(state);
        std::cout << static_cast<int>(values[0]) << ' ' << state.xrf << ' ' << state.yrf << ' '
                  << state.xre << ' ' << state.yre << ' ' << state.xrb << ' ' << state.yrb << ' '
                  << state.t12ru << ' ' << state.t12rl << ' ' << state.iregu << ' ' << state.iregl
                  << '\n';
        ++cases;
    }
    std::cerr << "P7M_CTREC_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int puffc_matrix() {
    std::cout.precision(17);
    int cases = 0;
    std::string line;
    std::string extra_line;
    while (std::getline(std::cin, line)) {
        if (line.find_first_not_of(" \t\r\n") == std::string::npos) continue;
        if (!std::getline(std::cin, extra_line)) break;
        std::istringstream fields(line);
        std::vector<double> values;
        double value = 0.0;
        while (fields >> value) values.push_back(value);
        std::vector<double> extra;
        {
            std::istringstream fields2(extra_line);
            double item = 0.0;
            while (fields2 >> item) extra.push_back(item);
        }
        if (values.size() < 47U || extra.size() < 3U) continue;
        CtsgState state = state_from(values, 1);
        // PUFFC reads CTREC's outputs from the state, as the vendor does.
        cteas::puff::receptor_geometry(state);
        const int imode = static_cast<int>(extra[0]);
        std::cout << static_cast<int>(values[0]) << ' '
                  << cteas::puff::puff_concentration(state, imode, extra[1], extra[2]) << '\n';
        ++cases;
    }
    std::cerr << "P7M_PUFFC_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int lower_matrix() {
    std::cout.precision(17);
    int cases = 0;
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.find_first_not_of(" \t\r\n") == std::string::npos) continue;
        std::istringstream fields(line);
        std::vector<double> values;
        double value = 0.0;
        while (fields >> value) values.push_back(value);
        if (values.size() < 47U) continue;
        CtsgState state = state_from(values, 1);
        cteas::puff::receptor_geometry(state);
        std::cout << static_cast<int>(values[0]) << ' '
                  << cteas::puff::lower_segment(state, stub_y(), stub_z()) << '\n';
        ++cases;
    }
    std::cerr << "P7M_LOWER_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int ctsg_matrix() {
    std::cout.precision(17);
    int cases = 0;
    std::string line;
    std::string extra_line;
    while (std::getline(std::cin, line)) {
        if (line.find_first_not_of(" \t\r\n") == std::string::npos) continue;
        if (!std::getline(std::cin, extra_line)) break;
        std::istringstream fields(line);
        std::vector<double> values;
        double value = 0.0;
        while (fields >> value) values.push_back(value);
        std::vector<double> extra;
        {
            std::istringstream fields2(extra_line);
            double item = 0.0;
            while (fields2 >> item) extra.push_back(item);
        }
        if (values.size() < 47U || extra.size() < 3U) continue;
        CtsgInputs inputs;
        inputs.receptor_index = 1;
        inputs.puff_index = static_cast<int>(extra[0]);
        inputs.hill_index = static_cast<int>(extra[1]);
        inputs.start_age_s = extra[2];
        inputs.receptor_x_m = values[41];
        inputs.receptor_y_m = values[42];
        const CtsgResult result =
            cteas::puff::ctsg(state_from(values, 1), inputs, stub_y(), stub_z());
        std::cout << static_cast<int>(values[0]) << ' ' << result.concentration << ' '
                  << result.flat_concentration << '\n';
        ++cases;
    }
    std::cerr << "P7M_CTSG_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

int const_mode() {
    const auto constants = cteas::puff::ctsg_constants();
    std::cout.precision(17);
    std::cout << "P7M_CONST_RT2PI " << constants.rt2pi << '\n'
              << "P7M_CONST_SMALL " << constants.small << '\n'
              << "P7M_CONST_EXPMAX " << constants.expmax << '\n'
              << "P7M_CONST_EPSREFL " << constants.epsrefl << '\n'
              << "P7M_CONST_MXREFL " << constants.max_reflections << '\n';
    return 0;
}

// Physical-chain run over the locked case's receptor grid: one synthetic puff
// moved one step with real met inputs, sampled by the reconstructed CTSG kernel.
// The locked deck has NHILL=0 and NCTREC=0, so CTSG is NOT on its concentration
// path; the hill geometry below is constructed so that the lower-segment branch
// is actually exercised. This is explicitly NOT a comparison with puff.con.
int real_grid_mode(const std::string& met_path, const std::string& control_path, int hour_index,
                   double release_mass, double stack_x, double stack_y, double stack_height) {
    const auto text = read_text(control_path);
    const auto control = cteas::puff::ControlFile::parse(text);
    const auto receptors = cteas::puff::receptors_from_control(text);
    const int step_seconds = control.required_int("NSECDT");
    // The locked deck's own subgrid-terrain configuration decides whether the
    // vendor would ever call CTSG (lctsg requires NCTREC > 0).
    const int deck_nhill = control.required_int("NHILL");
    const int deck_nctrec = control.required_int("NCTREC");
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
    require_true(summary.statics.present, "MET.DAT has no decoded static fields");
    require_true(intervals > hour_index, "requested hour is not present");
    require_true(hour.values.count("ZI") == 1U && hour.integers.count("IPGT") == 1U,
                 "missing hourly fields for the CTSG run");

    const double spacing = summary.header.dx_m / 1000.0;
    const int cell_i = static_cast<int>((stack_x - summary.header.origin_x_m / 1000.0) / spacing);
    const int cell_j = static_cast<int>((stack_y - summary.header.origin_y_m / 1000.0) / spacing);
    require_true(cell_i >= 0 && cell_i < summary.header.nx && cell_j >= 0 &&
                     cell_j < summary.header.ny,
                 "stack is outside the met grid");
    const std::size_t cell = static_cast<std::size_t>(cell_j) * summary.header.nx +
                             static_cast<std::size_t>(cell_i);
    int level = 0;
    for (int z = 0; z < summary.header.nz; ++z) {
        if (stack_height >= zface[static_cast<std::size_t>(z)] &&
            stack_height < zface[static_cast<std::size_t>(z) + 1U]) {
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
    require_true(speed > 0.01, "calm hour: the CTSG sampling integrals are not meaningful");
    const double mixing_height = static_cast<double>(hour.values.at("ZI")[cell]);
    require_true(mixing_height > 0.0, "mixing height must be positive");
    const int stability_class = std::max(1, std::min(6, hour.integers.at("IPGT")[cell]));
    const bool urban = summary.statics.land_use[cell] >= 10 && summary.statics.land_use[cell] <= 19;

    cteas::puff::DispersionSetup dispersion_setup;
    dispersion_setup.mdisp = audit.mdisp;
    dispersion_setup.sigma_y_heffter_m = audit.sytdep_m;
    dispersion_setup.averaging_factor = 1.0;
    const cteas::puff::SigmaCurves curves(cteas::puff::dispersion_environment(
        dispersion_setup, stability_class, urban, speed));
    const SigmaYCurve sigma_y_curve = [&curves](double sigma_y0_m, double dx_km, double dt_s) {
        cteas::puff::DispersionIncrement increment;
        increment.dx_km = dx_km;
        increment.dt_s = dt_s;
        const auto step = curves.sigma_y(sigma_y0_m, increment);
        SigmaCurvePoint point;
        point.value = step.sigma_y_m;
        point.virtual_time_s = step.virtual_time_y_s;
        point.virtual_distance_km = step.virtual_distance_y_km;
        return point;
    };
    const SigmaZCurve sigma_z_curve = [&curves](double sigma_z0_m, double dx_km, double dt_s,
                                                double height_m) {
        cteas::puff::DispersionIncrement increment;
        increment.dx_km = dx_km;
        increment.dt_s = dt_s;
        const auto step = curves.sigma_z(sigma_z0_m, height_m, increment);
        SigmaCurvePoint point;
        point.value = step.sigma_z_m;
        point.virtual_time_s = step.virtual_time_z_s;
        point.virtual_distance_km = step.virtual_distance_z_km;
        return point;
    };

    const double distance_km = speed * static_cast<double>(step_seconds) / 1000.0;
    cteas::puff::DispersionIncrement increment;
    increment.dx_km = distance_km;
    increment.dt_s = static_cast<double>(step_seconds);
    const auto sigma_y_step = curves.sigma_y(1.0, increment);
    const auto sigma_z_step = curves.sigma_z(1.0, stack_height, increment);
    const double x_new = stack_x + distance_km * (u / speed);
    const double y_new = stack_y + distance_km * (v / speed);

    // Constructed hill geometry: CTSG's CTPAR outputs are explicit inputs of the
    // port, and the locked deck has no hill at all (NHILL=0, NCTREC=0), so a
    // documented synthetic hill 2 km downwind of the stack is used here to
    // exercise the kernel. The dividing-streamline height is placed above the
    // release height so that material is actually in the lower segment.
    const double hill_relief_m = 200.0;
    const double dividing_height_m = 120.0;
    const double hill_axis_m = 2000.0;
    const double axis_ratio = 0.5;
    const double hill_offset_m = 2000.0;
    // CTSG's own coordinates are metres relative to the MET-grid origin
    // (/CTPASS/ documentation), while the receptor set and the stack position
    // are in kilometres; the kernel state is built in metres here. The hill is
    // placed `hill_offset_m` DOWNWIND of the stack and the hill-centred frame is
    // rotated so that its x-axis follows the real flow of the sampled hour.
    const double stack_x_m = stack_x * 1000.0;
    const double stack_y_m = stack_y * 1000.0;
    const double flow_x = u / speed;
    const double flow_y = v / speed;
    const double hill_x_m = stack_x_m + hill_offset_m * flow_x;
    const double hill_y_m = stack_y_m + hill_offset_m * flow_y;
    const double puff_x_m = x_new * 1000.0 - hill_x_m;
    const double puff_y_m = y_new * 1000.0 - hill_y_m;
    const double impingement_time_s = hill_offset_m / speed;
    const auto impingement_y = curves.sigma_y(1.0, cteas::puff::DispersionIncrement{
                                                       hill_offset_m / 1000.0,
                                                       impingement_time_s});
    const auto impingement_z = curves.sigma_z(1.0, stack_height,
                                              cteas::puff::DispersionIncrement{
                                                  hill_offset_m / 1000.0,
                                                  impingement_time_s});
    CtsgState base;
    base.q = release_mass;
    base.u = speed;
    base.zlid = mixing_height;
    base.tstart = 0.0;
    base.tstep = static_cast<double>(step_seconds);
    base.frac = 1.0;
    // The puff's sigmas at the start of this step are the sigmas at the hill
    // (the impingement point), because the reconstructed scenario lets the puff
    // travel from the stack to the hill before the sampled step.
    base.sz1 = impingement_z.sigma_z_m;
    base.sy1 = impingement_y.sigma_y_m;
    base.sz2 = sigma_z_step.sigma_z_m;
    base.sy2 = sigma_y_step.sigma_y_m;
    base.szr = sigma_z_step.sigma_z_m;
    base.syr = sigma_y_step.sigma_y_m;
    base.szmn = 1.0;
    base.symn = 1.0;
    base.hd = dividing_height_m;
    base.h = hill_relief_m;
    base.ubyn = speed;
    base.zgrid = 0.0;
    base.xc = hill_x_m;
    base.yc = hill_y_m;
    base.rotflo = std::atan2(v, u);
    base.rotang = 0.0;
    base.alfw = 0.0;
    base.beta = 0.0;
    base.cbeta = 1.0;
    base.d = 0.0;
    base.baxi = 1.0 / hill_axis_m;
    base.r = axis_ratio;
    base.x12f = -0.5 * hill_axis_m;
    base.x23f = 0.5 * hill_axis_m;
    base.xob = 0.0;
    base.xp = stack_x_m;
    base.yp = stack_y_m;
    base.zpuff = stack_height;
    // CTPAR outputs in the flow-aligned hill frame.
    base.xpf = puff_x_m * flow_x + puff_y_m * flow_y;
    base.ypf = -puff_x_m * flow_y + puff_y_m * flow_x;
    base.t12p = (base.xpf - base.x12f) / speed;
    base.timpg = impingement_time_s;
    base.szimpg = impingement_z.sigma_z_m;
    base.syimpg = impingement_y.sigma_y_m;
    base.isc = stability_class;
    base.ih = 1;
    base.ip = 1;

    double total = 0.0;
    double flat_total = 0.0;
    double maximum = 0.0;
    double flat_maximum = 0.0;
    std::size_t non_zero = 0;
    std::size_t lower_branch = 0;
    std::size_t pole_branch = 0;
    std::size_t vcbar_non_zero = 0;
    double vcbar_total = 0.0;
    for (const auto& receptor : receptors.grid) {
        CtsgState state = base;
        state.zrec = receptor.ground_elevation_m + receptor.height_m;
        state.xr = receptor.x_km * 1000.0;
        state.yr = receptor.y_km * 1000.0;
        CtsgInputs inputs;
        inputs.puff_index = 1;
        inputs.hill_index = 1;
        inputs.start_age_s = 0.0;
        inputs.receptor_x_m = state.xr;
        inputs.receptor_y_m = state.yr;
        const CtsgResult result = cteas::puff::ctsg(state, inputs, sigma_y_curve, sigma_z_curve);
        total += result.concentration;
        flat_total += result.flat_concentration;
        maximum = std::max(maximum, result.concentration);
        flat_maximum = std::max(flat_maximum, result.flat_concentration);
        if (result.concentration > 0.0) ++non_zero;
        CtsgState geometry = state;
        cteas::puff::receptor_geometry(geometry);
        if (geometry.iregl == 1) ++pole_branch;
        else ++lower_branch;

        // The vendor's real-case (non-hill) path is the CALCPF accumulation with
        // the VCBAR vertical factor, reconstructed in P7H; it is a different
        // formulation, so only a physical-chain comparison is reported.
        cteas::puff::VcbarInputs coupling;
        coupling.state.puff_code = 1;
        coupling.state.x_begin1 = stack_x;
        coupling.state.y_begin1 = stack_y;
        coupling.state.z_begin1 = stack_height;
        coupling.state.sigma_z_begin1 = sigma_z_step.sigma_z_m;
        coupling.state.x_end1 = x_new;
        coupling.state.y_end1 = y_new;
        coupling.state.z_end1 = stack_height;
        coupling.state.sigma_z_end1 = sigma_z_step.sigma_z_m;
        coupling.lid_height_m = mixing_height;
        coupling.plume_path_coefficient = 1.0;
        coupling.terrain_adjustment = 2;
        const double dx = x_new - stack_x;
        const double dy = y_new - stack_y;
        const double length_squared = dx * dx + dy * dy;
        const double projection =
            ((receptor.x_km - stack_x) * dx + (receptor.y_km - stack_y) * dy) / length_squared;
        const double t = std::max(0.0, std::min(1.0, projection));
        const double closest_x = stack_x + t * dx;
        const double closest_y = stack_y + t * dy;
        const double distance_squared = (receptor.x_km - closest_x) * (receptor.x_km - closest_x) +
                                        (receptor.y_km - closest_y) * (receptor.y_km - closest_y);
        const auto integrals = cteas::puff::puff_sampling_integrals(
            stack_x, stack_y, x_new, y_new, receptor.x_km, receptor.y_km, sigma_y_step.sigma_y_m,
            distance_squared);
        cteas::puff::ReceptorAccumulationInputs accumulation;
        accumulation.mass_old = release_mass;
        accumulation.mass_new = release_mass;
        accumulation.sigma_y_at_receptor_m = sigma_y_step.sigma_y_m;
        accumulation.time_fraction = 1.0;
        accumulation.deposition_ratio = 1.0;
        const double vcbar_value = cteas::puff::receptor_concentration_increment_with_coupling(
            integrals, accumulation, coupling);
        vcbar_total += vcbar_value;
        if (vcbar_value > 0.0) ++vcbar_non_zero;
    }

    std::cout.precision(17);
    std::cout << "P7M_REAL_GRID_CTSG_RUN=PASS HOUR=" << hour_index
              << " RECEPTORS=" << receptors.grid.size() << " STABILITY=" << stability_class
              << " URBAN=" << (urban ? "true" : "false") << " SPEED_MS=" << speed
              << " STEP_KM=" << distance_km << " SIGMA_Y_M=" << sigma_y_step.sigma_y_m
              << " SIGMA_Z_M=" << sigma_z_step.sigma_z_m << " ZI_M=" << mixing_height
              << " HILL_RELIEF_M=" << hill_relief_m << " HD_M=" << dividing_height_m
              << " SYNTHETIC_HILL=true LOWER_BRANCH=" << lower_branch
              << " POLE_BRANCH=" << pole_branch << " SUM=" << total << " MAX=" << maximum
              << " NONZERO=" << non_zero << " CFLAT_SUM=" << flat_total
              << " CFLAT_MAX=" << flat_maximum << " VCBAR_STANDARD_SUM=" << vcbar_total
              << " VCBAR_STANDARD_NONZERO=" << vcbar_non_zero
              << " PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true\n";
    std::cout << "P7M_REAL_GRID_CTSG_CAVEAT=LOCKED_DECK_NHILL=" << deck_nhill
              << " LOCKED_DECK_NCTREC=" << deck_nctrec
              << " CTSG_NOT_ON_LOCKED_DECK_PATH="
              << ((deck_nhill == 0 && deck_nctrec == 0) ? "true" : "false")
              << " CONSTRUCTED_HILL=true NO_CONC_DAT_VALUE_COMPARISON=true\n";
    require_true(deck_nhill == 0 && deck_nctrec == 0,
                 "this physical-chain run documents the no-hill locked deck; a deck with hills "
                 "needs CTPAR, which is not reconstructed");
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const std::string mode = argc > 1 ? argv[1] : "";
        if (mode == "--munu-matrix") return munu_matrix();
        if (mode == "--bi-matrix") return bi_matrix();
        if (mode == "--bji-matrix") return bji_matrix();
        if (mode == "--bjil-matrix") return bjil_matrix();
        if (mode == "--sigma-matrix") return sigma_matrix();
        if (mode == "--ireg-matrix") return ireg_matrix();
        if (mode == "--ctrec-matrix") return ctrec_matrix();
        if (mode == "--puffc-matrix") return puffc_matrix();
        if (mode == "--lower-matrix") return lower_matrix();
        if (mode == "--ctsg-matrix") return ctsg_matrix();
        if (mode == "--const") return const_mode();
        if (mode == "--real-grid" && argc == 9) {
            return real_grid_mode(argv[2], argv[3], std::stoi(argv[4]), std::stod(argv[5]),
                                  std::stod(argv[6]), std::stod(argv[7]), std::stod(argv[8]));
        }
        std::cerr << "Usage: cteas_p7m_probe --munu-matrix | --bi-matrix | --bji-matrix |\n"
                     "  --bjil-matrix | --sigma-matrix | --ireg-matrix | --ctrec-matrix |\n"
                     "  --puffc-matrix | --lower-matrix | --ctsg-matrix | --const |\n"
                     "  --real-grid MET CONTROL HOUR MASS STACK_X_KM STACK_Y_KM STACK_HEIGHT_M\n";
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "P7M_PROBE=FAIL: " << error.what() << '\n';
        return 1;
    }
}
