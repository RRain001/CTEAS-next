#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/conc_file.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/dispersion.hpp"
#include "cteas/puff/receptors.hpp"

#include <algorithm>
#include <cmath>
#include <map>
#include <exception>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>

namespace {

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7E cannot read control file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

int receptor_mode(const std::string& path) {
    const auto text = read_text(path);
    const auto receptors = cteas::puff::receptors_from_control(text);
    std::cout << "{\n"
              << "  \"gate\": \"P7E_RECEPTOR_GEOMETRY\",\n"
              << "  \"control\": \"" << path << "\",\n"
              << "  \"gridded\": " << (receptors.gridded ? "true" : "false") << ",\n"
              << "  \"sampling_nx\": " << receptors.sampling_nx << ",\n"
              << "  \"sampling_ny\": " << receptors.sampling_ny << ",\n"
              << "  \"mesh_down\": " << receptors.mesh_down << ",\n"
              << "  \"spacing_km\": " << receptors.spacing_km << ",\n"
              << "  \"grid_receptors\": " << receptors.grid.size() << ",\n"
              << "  \"discrete_receptors\": " << receptors.discrete.size() << "\n"
              << "}\n";
    std::cout << "P7E_RECEPTOR_GEOMETRY=PASS GRIDDED=" << (receptors.gridded ? "true" : "false")
              << " SAMPLING_NX=" << receptors.sampling_nx << " SAMPLING_NY=" << receptors.sampling_ny
              << " MESHDN=" << receptors.mesh_down << " SPACING_KM=" << receptors.spacing_km
              << " GRID_RECEPTORS=" << receptors.grid.size()
              << " DISCRETE_RECEPTORS=" << receptors.discrete.size();
    if (!receptors.grid.empty()) {
        std::cout << " FIRST_X_KM=" << receptors.grid.front().x_km
                  << " FIRST_Y_KM=" << receptors.grid.front().y_km
                  << " LAST_X_KM=" << receptors.grid.back().x_km
                  << " LAST_Y_KM=" << receptors.grid.back().y_km;
    }
    std::cout << '\n';
    return 0;
}

int structure_mode(const std::string& path) {
    const auto summary = cteas::puff::summarize_conc_file(path);
    std::cout << "P7E_CONC_STRUCTURE=PASS RECORDS=" << summary.records << " BYTES=" << summary.bytes
              << " PERIOD_RECORDS=" << summary.period_records
              << " GRID_RECORDS=" << summary.grid_records
              << " SPECIES_FIELDS=" << summary.species_field_records
              << " OTHER=" << summary.unframed_records
              << " FIRST_BEGIN=" << summary.first_begin_date << " LAST_END=" << summary.last_end_date
              << '\n';
    for (const auto& entry : summary.species_field_counts) {
        std::cout << "P7E_CONC_SPECIES_FIELD label=\"" << entry.first << "\" count=" << entry.second
                  << '\n';
    }
    if (!summary.species_field_sizes.empty()) {
        std::size_t smallest = summary.species_field_sizes.front();
        std::size_t largest = summary.species_field_sizes.front();
        for (const auto size : summary.species_field_sizes) {
            smallest = std::min(smallest, size);
            largest = std::max(largest, size);
        }
        std::cout << "P7E_CONC_SPECIES_FIELD_SIZES min=" << smallest << " max=" << largest << '\n';
    }
    for (const auto& entry : summary.label_counts) {
        std::cout << "P7E_CONC_LABEL label=\"" << entry.first << "\" count=" << entry.second << '\n';
    }
    if (!summary.framed_sizes.empty()) {
        std::size_t smallest = summary.framed_sizes.front();
        std::size_t largest = summary.framed_sizes.front();
        for (const auto size : summary.framed_sizes) {
            smallest = std::min(smallest, size);
            largest = std::max(largest, size);
        }
        std::cout << "P7E_CONC_FRAMED_SIZES min=" << smallest << " max=" << largest << '\n';
    }
    return 0;
}

int matrix_mode() {
    // PFSAMP case matrix: icase xold yold xnew ynew xrec yrec sigma_y dist2
    std::size_t cases = 0;
    std::cout.setf(std::ios::scientific, std::ios::floatfield);
    std::cout.precision(12);
    while (true) {
        int icase = 0;
        double xold = 0.0, yold = 0.0, xnew = 0.0, ynew = 0.0;
        double xrec = 0.0, yrec = 0.0, sigma = 0.0, dist2 = 0.0;
        if (!(std::cin >> icase >> xold >> yold >> xnew >> ynew >> xrec >> yrec >> sigma >> dist2)) {
            if (std::cin.eof()) break;
            throw std::invalid_argument("malformed PFSAMP case line");
        }
        const auto integrals = cteas::puff::puff_sampling_integrals(xold, yold, xnew, ynew, xrec, yrec,
                                                                    sigma, dist2);
        std::cout << icase << ' ' << integrals.i1 << ' ' << integrals.i2 << '\n';
        ++cases;
    }
    std::cerr << "P7E_PFSAMP_PROBE=PASS CASES=" << cases << " NOT_A_MODEL_RUN=true\n";
    return 0;
}

int vcoup_matrix_mode() {
    std::cout.setf(std::ios::scientific, std::ios::floatfield);
    std::cout.precision(12);
    std::size_t cases = 0;
    while (true) {
        int icase = 0, code = 0;
        double zr = 0.0, zs = 0.0, sz = 0.0, lid = 0.0, lid_max = 0.0;
        if (!(std::cin >> icase >> code >> zr >> zs >> sz >> lid >> lid_max)) {
            if (std::cin.eof()) break;
            throw std::invalid_argument("malformed VCOUP case line");
        }
        cteas::puff::VcoupInputs inputs;
        inputs.puff_code = code;
        inputs.receptor_height_m = zr;
        inputs.source_height_m = zs;
        inputs.sigma_z_m = sz;
        inputs.lid_height_m = lid;
        inputs.lid_max_m = lid_max;
        std::cout << icase << ' ' << cteas::puff::vertical_coupling(inputs) << '\n';
        ++cases;
    }
    std::cerr << "P7H_VCOUP_PROBE=PASS CASES=" << cases << "\n";
    return 0;
}

int vcbar_matrix_mode() {
    std::cout.setf(std::ios::scientific, std::ios::floatfield);
    std::cout.precision(12);
    std::size_t cases = 0;
    while (true) {
        int icase = 0, slug = 0, code = 0, mctadj = 0, mtilt = 0;
        double lid = 0.0, ppcoef = 0.0, dgridi = 0.0, ht0 = 0.0, elbase = 0.0;
        double zb1 = 0.0, ze1 = 0.0, szb1 = 0.0, szm1 = 0.0, sze1 = 0.0;
        double zb2 = 0.0, ze2 = 0.0, szb2 = 0.0, sze2 = 0.0;
        double tb1 = 0.0, te1 = 0.0, tb2 = 0.0, te2 = 0.0, zfinal = 0.0, vsetl = 0.0;
        if (!(std::cin >> icase >> slug >> code >> mctadj >> mtilt >> lid >> ppcoef >> dgridi >>
              ht0 >> elbase >> zb1 >> ze1 >> szb1 >> szm1 >> sze1 >> zb2 >> ze2 >> szb2 >> sze2 >> tb1 >>
              te1 >> tb2 >> te2 >> zfinal >> vsetl)) {
            if (std::cin.eof()) break;
            throw std::invalid_argument("malformed VCBAR case line");
        }
        cteas::puff::VcbarInputs inputs;
        inputs.slug = slug != 0;
        inputs.state.puff_code = code;
        inputs.state.z_begin1 = zb1;
        inputs.state.z_end1 = ze1;
        inputs.state.z_begin2 = zb2;
        inputs.state.z_end2 = ze2;
        inputs.state.sigma_z_begin1 = szb1;
        inputs.state.sigma_z_mid = szm1;
        inputs.state.sigma_z_end1 = sze1;
        inputs.state.sigma_z_begin2 = szb2;
        inputs.state.sigma_z_end2 = sze2;
        inputs.state.time_begin1 = tb1;
        inputs.state.time_end1 = te1;
        inputs.state.time_begin2 = tb2;
        inputs.state.time_end2 = te2;
        inputs.state.final_height_m = zfinal;
        inputs.state.settling_velocity_ms = vsetl;
        inputs.lid_height_m = lid;
        inputs.plume_path_coefficient = ppcoef;
        inputs.terrain_adjustment = mctadj;
        inputs.plume_tilt = mtilt;
        inputs.grid_spacing_m = dgridi;
        inputs.stack_height_m = ht0;
        inputs.stack_base_elevation_m = elbase;
        std::cout << icase << ' ' << cteas::puff::vertical_coupling_bar(inputs) << '\n';
        ++cases;
    }
    std::cerr << "P7H_VCBAR_PROBE=PASS CASES=" << cases << "\n";
    return 0;
}

// Real receptor-grid run: one synthetic puff moved one step over the locked
// case's 2500-receptor grid, with the vertical factor taken from the
// reconstructed VCBAR. Physical-chain demonstration on real inputs, NOT a
// comparison against the frozen puff.con. The release point is the case's
// documented stack position (513.3846439571, 3533.7689269678 km, 70.8 m).
int real_grid_mode(const std::string& met_path, const std::string& control_path, int hour_index,
                   double release_mass, double stack_x, double stack_y, double stack_height) {
    const auto text = read_text(control_path);
    const auto control = cteas::puff::ControlFile::parse(text);
    const auto receptors = cteas::puff::receptors_from_control(text);
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
    require_true(summary.statics.present, "MET.DAT has no decoded static fields");
    require_true(intervals > hour_index, "requested hour is not present");
    require_true(hour.values.count("ZI") == 1U && hour.integers.count("IPGT") == 1U,
                 "missing hourly fields for the coupling run");

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
    require_true(speed > 0.01, "calm hour: sampling integrals are not meaningful");
    const double mixing_height = static_cast<double>(hour.values.at("ZI")[cell]);
    require_true(mixing_height > 0.0, "mixing height must be positive");
    // PG stability class straight from the original CALMET IPGT field.
    const int stability_class = std::max(1, std::min(6, hour.integers.at("IPGT")[cell]));
    const bool urban = summary.statics.land_use[cell] >= 10 && summary.statics.land_use[cell] <= 19;

    cteas::puff::DispersionSetup dispersion_setup;
    dispersion_setup.mdisp = audit.mdisp;
    dispersion_setup.sigma_y_heffter_m = audit.sytdep_m;
    dispersion_setup.averaging_factor = 1.0;
    const cteas::puff::SigmaCurves curves(cteas::puff::dispersion_environment(
        dispersion_setup, stability_class, urban, speed));
    const double distance_km = speed * static_cast<double>(step_seconds) / 1000.0;
    cteas::puff::DispersionIncrement increment;
    increment.dx_km = distance_km;
    increment.dt_s = static_cast<double>(step_seconds);
    const auto sigma_y_step = curves.sigma_y(0.0, increment);
    const auto sigma_z_step = curves.sigma_z(0.0, stack_height, increment);
    const double x_new = stack_x + distance_km * (u / speed);
    const double y_new = stack_y + distance_km * (v / speed);

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
    const double vertical_factor = cteas::puff::vertical_coupling_bar(coupling);

    double total = 0.0, maximum = 0.0, minimum = 0.0;
    std::size_t non_zero = 0;
    const double dx = x_new - stack_x;
    const double dy = y_new - stack_y;
    const double length_squared = dx * dx + dy * dy;
    for (const auto& receptor : receptors.grid) {
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
        cteas::puff::ReceptorAccumulationInputs inputs;
        inputs.mass_old = release_mass;
        inputs.mass_new = release_mass;
        inputs.sigma_y_at_receptor_m = sigma_y_step.sigma_y_m;
        inputs.time_fraction = 1.0;
        inputs.deposition_ratio = 1.0;
        const double value = cteas::puff::receptor_concentration_increment_with_coupling(
            integrals, inputs, coupling);
        total += value;
        maximum = std::max(maximum, value);
        minimum = std::min(minimum, value);
        if (value > 0.0) ++non_zero;
    }
    std::cout << "P7H_REAL_GRID_RUN=PASS HOUR=" << hour_index << " RECEPTORS="
              << receptors.grid.size() << " STABILITY=" << stability_class
              << " URBAN=" << (urban ? "true" : "false") << " SPEED_MS=" << speed
              << " STEP_KM=" << distance_km << " SIGMA_Y_M=" << sigma_y_step.sigma_y_m
              << " SIGMA_Z_M=" << sigma_z_step.sigma_z_m << " ZI_M=" << mixing_height
              << " VCBAR_1_PER_M=" << vertical_factor << " SUM=" << total << " MAX=" << maximum
              << " MIN=" << minimum << " NONZERO=" << non_zero
              << " PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true\n";
    return 0;
}

// P7G: the CONC.DAT structure comparison. Writes a file with this module's own
// framing for every period the frozen artifact carries, then reports the record
// inventory of both so the structural difference is explicit and measured.
int structure_compare_mode(const std::string& frozen_path, const std::string& out_path,
                           int nx, int ny) {
    const auto frozen = cteas::puff::summarize_conc_file(frozen_path);
    const auto periods = cteas::puff::read_conc_periods(frozen_path);
    require_true(!periods.empty(), "the frozen artifact has no period records");

    cteas::puff::ConcFileWriter writer(out_path, "7.0",
                                       "CALPUFF Version: 7.2.1  Level: 150618", {});
    std::vector<float> values(static_cast<std::size_t>(nx) * static_cast<std::size_t>(ny), 0.0F);
    for (const auto& period : periods) {
        cteas::puff::ConcPeriod record;
        record.begin_year = period.begin_year;
        record.begin_julian = period.begin_julian;
        record.begin_hour = period.begin_hour;
        record.begin_seconds = period.begin_seconds;
        record.end_year = period.end_year;
        record.end_julian = period.end_julian;
        record.end_hour = period.end_hour;
        record.end_seconds = period.end_seconds;
        writer.write_period_record(record);
        cteas::puff::ConcGridDescriptor descriptor;
        writer.write_grid_descriptor(descriptor);
        writer.write_species_field("H-3     ", 1, nx, ny, values);
    }
    writer.close();

    const auto written = cteas::puff::summarize_conc_file(out_path);
    std::cout << "P7G_CONC_STRUCTURE_COMPARE FROZEN_RECORDS=" << frozen.records
              << " FROZEN_BYTES=" << frozen.bytes << " WRITTEN_RECORDS=" << written.records
              << " WRITTEN_BYTES=" << written.bytes << " PERIODS=" << periods.size()
              << " FROZEN_PERIODS=" << frozen.period_records
              << " FROZEN_GRID=" << frozen.grid_records
              << " FROZEN_SPECIES_FIELDS=" << frozen.species_field_records
              << " WRITTEN_PERIODS=" << written.period_records
              << " WRITTEN_GRID=" << written.grid_records
              << " WRITTEN_SPECIES_FIELDS=" << written.species_field_records
              << " FIRST_BEGIN=" << frozen.first_begin_date
              << " LAST_END=" << frozen.last_end_date << '\n';
    for (const auto& entry : frozen.species_field_counts) {
        std::cout << "P7G_CONC_STRUCTURE_SPECIES FROZEN_LABEL=\"" << entry.first
                  << "\" FROZEN_COUNT=" << entry.second << '\n';
    }
    std::cout << "P7G_CONC_STRUCTURE_LABELS FROZEN=" << frozen.label_counts.size()
              << " WRITTEN=" << written.label_counts.size() << '\n';
    for (const auto& entry : frozen.label_counts) {
        std::cout << "P7G_CONC_STRUCTURE_LABEL FROZEN_LABEL=\"" << entry.first
                  << "\" FROZEN_COUNT=" << entry.second << '\n';
    }
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 3 && std::string(argv[1]) == "--receptors") return receptor_mode(argv[2]);
        if (argc == 3 && std::string(argv[1]) == "--structure") return structure_mode(argv[2]);
        if (argc == 2 && std::string(argv[1]) == "--vcoup-matrix") return vcoup_matrix_mode();
        if (argc == 2 && std::string(argv[1]) == "--vcbar-matrix") return vcbar_matrix_mode();
        if (argc == 6 && std::string(argv[1]) == "--structure-compare") {
            return structure_compare_mode(argv[2], argv[3], std::stoi(argv[4]), std::stoi(argv[5]));
        }
        if (argc == 9 && std::string(argv[1]) == "--real-grid") {
            return real_grid_mode(argv[2], argv[3], std::stoi(argv[4]), std::stod(argv[5]),
                                  std::stod(argv[6]), std::stod(argv[7]), std::stod(argv[8]));
        }
        if (argc != 1) {
            std::cerr << "Usage: cteas_p7e_probe [--receptors CONTROL_FILE | --structure CONC.DAT]\n"
                         "Without arguments reads the PFSAMP case matrix on stdin:\n"
                         "  icase xold yold xnew ynew xrec yrec sigma_y dist2\n"
                         "and writes: icase xi1 xi2\n";
            return 2;
        }
        return matrix_mode();
    } catch (const std::exception& error) {
        std::cerr << "P7E_PROBE=FAIL: " << error.what() << '\n';
        return 1;
    }
}
