// P7W: the one-step numerical comparison against the vendor's own instrumented
// puff-step dump (DGM round 3, reference/dgm_p7_advection_2022). Every record
// carries the vendor's PUFFDZ/ADVECT inputs and returns for one sampling substep,
// so each record is a real, independent comparison case for the ported units.
//
// This is a PUFF-STATE comparison (PUFFDZ/ADVECT returns), not a puff.con value
// comparison; the CONC.DAT header subset remains CTEAS-only.
#include "cteas/puff/advection.hpp"
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/plume_rise.hpp"
#include "cteas/puff/rise_wind.hpp"
#include "cteas/puff/step_integration.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using cteas::puff::AdvectiveWindInputs;
using cteas::puff::PuffExtentInputs;

constexpr std::size_t kHeaderInts = 24;
constexpr std::size_t kPayloadFloats = 64;
constexpr std::size_t kRecordBytes = (kHeaderInts + kPayloadFloats) * 4U;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7W cannot read file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

struct StepRecord {
    std::int32_t kpt = 0, packed = 0, seconds = 0, ii = 0, icode = 0, ixs = 0, iys = 0;
    std::int32_t mdoms = 0, istab = 0, ilayer = 0, nsam = 0, nsstr = 0, iold = 0;
    std::int32_t istype = 0, ipno = 0, mdstep = 0, ksam = 0, lcalm = 0, nspec = 0;
    std::int32_t lpuff = 0, islug = 0, isrcnum = 0;
    std::vector<float> payload;

    [[nodiscard]] double at(int slot) const {
        return static_cast<double>(payload.at(static_cast<std::size_t>(slot - 1)));
    }
};

std::vector<StepRecord> read_records(const std::string& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("P7W cannot read the dump: " + path);
    const std::string bytes((std::istreambuf_iterator<char>(input)),
                            std::istreambuf_iterator<char>());
    require_true(bytes.size() % kRecordBytes == 0U, "the dump size is not a whole number of records");
    std::vector<StepRecord> records;
    records.reserve(bytes.size() / kRecordBytes);
    for (std::size_t offset = 0; offset < bytes.size(); offset += kRecordBytes) {
        StepRecord record;
        std::int32_t header[kHeaderInts];
        std::memcpy(header, bytes.data() + offset, sizeof(header));
        record.kpt = header[0];
        record.packed = header[1];
        record.seconds = header[2];
        record.ii = header[3];
        record.icode = header[4];
        record.ixs = header[5];
        record.iys = header[6];
        record.mdoms = header[7];
        record.istab = header[8];
        record.ilayer = header[9];
        record.nsam = header[10];
        record.nsstr = header[11];
        record.iold = header[12];
        record.istype = header[13];
        record.ipno = header[14];
        record.mdstep = header[15];
        record.ksam = header[16];
        record.lcalm = header[17];
        record.nspec = header[18];
        record.lpuff = header[19];
        record.islug = header[20];
        record.isrcnum = header[21];
        require_true(record.kpt == 1, "unexpected record type in the dump");
        record.payload.resize(kPayloadFloats);
        std::memcpy(record.payload.data(), bytes.data() + offset + kHeaderInts * 4U,
                    kPayloadFloats * 4U);
        records.push_back(record);
    }
    return records;
}

struct Tally {
    long cases = 0;
    long mismatches = 0;
    long unchecked = 0;
    double max_abs = 0.0;
    double max_rel = 0.0;
};

void compare(Tally& tally, double want, double got, double tolerance, const std::string& field,
             const StepRecord& record) {
    ++tally.cases;
    const double absolute = std::abs(want - got);
    const double relative = absolute / std::max(std::abs(want), 1.0e-30);
    if (absolute > tolerance) {
        ++tally.mismatches;
        if (tally.mismatches <= 5) {
            std::cerr << "P7W mismatch " << field << " puff=" << record.ii << " ksam=" << record.ksam
                      << " packed=" << record.packed << " vendor=" << want << " port=" << got
                      << '\n';
        }
    }
    tally.max_abs = std::max(tally.max_abs, absolute);
    tally.max_rel = std::max(tally.max_rel, relative);
}

// The rise state RISEWIND needs: XFINAL/ZFINAL come from the reconstructed
// gradual-rise chain (P7N) exactly as COMP obtains them for the released puff.
struct RiseChain {
    bool enabled = false;
    double x_final_m = 0.0;
    double z_final_m = 0.0;
    cteas::puff::PlumeRiseState state;
};

RiseChain build_rise_chain(const cteas::puff::Calmet21Summary& summary,
                           const std::map<std::string, std::vector<float>>& hour,
                           const std::map<std::string, std::vector<std::int32_t>>& hour_integers,
                           const cteas::puff::ControlFile& control, double stack_x_km,
                           double stack_y_km, double stack_height_m, double stack_diameter_m,
                           double stack_exit_velocity_ms, double stack_temperature_k) {
    RiseChain chain;
    const auto zface = control.required_float_list("ZFACE");
    const double spacing = summary.header.dx_m / 1000.0;
    const int cell_i = static_cast<int>((stack_x_km - summary.header.origin_x_m / 1000.0) /
                                        spacing);
    const int cell_j = static_cast<int>((stack_y_km - summary.header.origin_y_m / 1000.0) /
                                        spacing);
    require_true(cell_i >= 0 && cell_i < summary.header.nx && cell_j >= 0 &&
                     cell_j < summary.header.ny,
                 "the stack is outside the met grid");
    const std::size_t cell = static_cast<std::size_t>(cell_j) *
                                 static_cast<std::size_t>(summary.header.nx) +
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
        const auto found = hour.find(label);
        require_true(found != hour.end(), "missing wind field " + label);
        return static_cast<double>(found->second[index]);
    };
    const double u = wind_value(level_label("U"), cell);
    const double v = wind_value(level_label("V"), cell);
    const double speed = std::sqrt(u * u + v * v);
    require_true(speed > 0.01, "calm hour: the rise path is not meaningful");
    const double mixing_height = static_cast<double>(hour.at("ZI")[cell]);
    const double ambient_temperature = static_cast<double>(hour.at("TEMPK")[cell]);
    require_true(hour_integers.count("IPGT") == 1U, "the hour has no IPGT field");
    const int stability_class =
        std::max(1, std::min(6, static_cast<int>(hour_integers.at("IPGT")[cell])));
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
    cteas::puff::PartialPenetrationInputs penetration_inputs;
    penetration_inputs.final_rise_m = final_rise.z_final_m;
    penetration_inputs.buoyancy_flux = fluxes.buoyancy_m4s3;
    penetration_inputs.stack_wind_speed_ms = speed;
    penetration_inputs.stack_height_m = stack_height_m;
    penetration_inputs.mixing_height_m = mixing_height;
    penetration_inputs.ambient_temperature_k = ambient_temperature;
    penetration_inputs.inversion_gradient_k_per_m = ptginv;
    penetration_inputs.inversion_jump_k = ptginv * 30.0;
    const auto penetration = cteas::puff::partial_penetration_rise(penetration_inputs);
    const double rise_final = std::min(final_rise.z_final_m, penetration.final_rise_m);

    chain.enabled = true;
    chain.x_final_m = final_rise.x_final_m;
    chain.z_final_m = stack_height_m - tip_downwash + rise_final;
    chain.state.source_type = 1;
    chain.state.downwash_code = 0;
    chain.state.met_period = 1;
    chain.state.rise_method = 1;
    chain.state.shear_flag = 0;
    chain.state.x_m = 0.0;
    chain.state.final_rise_m = chain.z_final_m;
    chain.state.full_final_rise_m = rise_final;
    chain.state.stack_height_m = stack_height_m;
    chain.state.diameter_m = stack_diameter_m;
    chain.state.exit_velocity_ms = stack_exit_velocity_ms;
    chain.state.stack_wind_speed_ms = speed;
    chain.state.stability_class = stability_class;
    chain.state.sqrt_stability_s = 0.0;
    chain.state.momentum_flux = fluxes.momentum_m4s2;
    chain.state.buoyancy_flux = fluxes.buoyancy_m4s3;
    chain.state.x_final_momentum_m = final_rise.x_final_momentum_m;
    chain.state.z_final_momentum_m = final_rise.z_final_momentum_m;
    chain.state.x_final_buoyancy_m = final_rise.x_final_buoyancy_m;
    chain.state.z_final_buoyancy_m = final_rise.z_final_buoyancy_m;
    chain.state.stack_tip_downwash_m = tip_downwash;
    return chain;
}

struct StackArgs {
    bool enabled = false;
    double x_km = 0.0, y_km = 0.0, height_m = 0.0, diameter_m = 0.0, exit_velocity_ms = 0.0,
           temperature_k = 0.0;
};

int dgm_steps_mode(const std::string& dump_path, const std::string& met_path,
                   const std::string& control_path, const StackArgs& stack) {
    const auto control = cteas::puff::ControlFile::parse(read_text(control_path));
    require_true(control.required_int("MCTADJ") == 2, "the deck does not select MCTADJ=2");
    const auto records = read_records(dump_path);
    require_true(!records.empty(), "the dump has no records");

    // One CALMET hour is enough for the committed slice: all its records carry the
    // same packed time. A dump spanning hours would be read per hour.
    const std::int32_t hour_packed = records.front().packed;
    for (const auto& record : records) {
        require_true(record.packed == hour_packed,
                     "the dump spans more than one met hour; slice it first");
    }
    // YYYYJJJHH, exactly as the CALMET reader decodes it.
    const int year = hour_packed / 100000;
    const int julian = (hour_packed % 100000) / 100;
    const int hour = hour_packed % 100;

    std::map<std::string, std::vector<float>> hour_fields;
    std::map<std::string, std::vector<std::int32_t>> hour_integers;
    int matched_intervals = 0;
    const auto summary = cteas::puff::Calmet21Reader::read(
        met_path, [&](const cteas::puff::Calmet21Field& field) {
            // Every field carries its own begin time, so the dump's hour selects
            // its fields directly.
            if (field.begin.year != year || field.begin.julian_day != julian ||
                field.begin.hour != hour) {
                return;
            }
            if (field.label == "IRH") {
                ++matched_intervals;
                return;
            }
            if (field.integer) {
                hour_integers[field.label] = field.integer_values;
            } else {
                hour_fields[field.label] = field.real_values;
            }
        });
    require_true(matched_intervals >= 1, "the dump's met hour is not in MET.DAT");
    require_true(summary.statics.present, "MET.DAT has no decoded static fields");
    const int nx = summary.header.nx;
    const int ny = summary.header.ny;
    const int nz = summary.header.nz;
    require_true(static_cast<int>(summary.statics.cell_face_m.size()) == nz + 1,
                 "the face heights do not match NZ");

    // The rise chain (P7N) supplies RISEWIND's XFINAL/ZFINAL exactly as COMP
    // obtains them for the released puff.
    RiseChain rise_chain;
    if (stack.enabled) {
        rise_chain = build_rise_chain(summary, hour_fields, hour_integers, control, stack.x_km,
                                      stack.y_km, stack.height_m, stack.diameter_m,
                                      stack.exit_velocity_ms, stack.temperature_k);
        std::cout << "P7W_RISE_CHAIN XFIN_M=" << rise_chain.x_final_m
                  << " ZFIN_M=" << rise_chain.z_final_m
                  << " ISTAB=" << rise_chain.state.stability_class << '\n';
    }

    // Group by puff so each puff's first substep can use the previous substep's
    // stored sigma (the value PUFFDZ reads at the start of a step).
    std::map<std::int32_t, std::vector<const StepRecord*>> by_puff;
    for (const auto& record : records) by_puff[record.ii].push_back(&record);

    Tally puffdz_top, puffdz_bottom, advect_u, advect_v;
    Tally adjusted_u, adjusted_v, adjusted_ws, adjusted_calm;
    Tally step_length, step_distance, position_x, position_y, step_distance_m;
    Tally cadence_nsam, cadence_tsamp, cadence_reftsamp, cell_i, cell_j;
    Tally current_xb1, current_yb1, current_zb1, current_xe1, current_ye1, current_ze1;
    long risewind_applied = 0;
    long risewind_skipped = 0;
    long puffs = 0;
    long substeps = 0;
    long first_substep_skipped = 0;
    long cap_branch_skipped = 0;
    for (auto& [ii, steps] : by_puff) {
        (void)ii;
        ++puffs;
        std::sort(steps.begin(), steps.end(),
                  [](const StepRecord* a, const StepRecord* b) { return a->ksam < b->ksam; });
        for (std::size_t index = 0; index < steps.size(); ++index) {
            const StepRecord& record = *steps[index];
            ++substeps;
            require_true(record.mdoms == 1, "only the outer met domain is reconstructed");
            require_true(record.ixs >= 1 && record.ixs <= nx && record.iys >= 1 &&
                             record.iys <= ny,
                         "the record's met cell is outside the grid");
            const std::size_t cell = static_cast<std::size_t>(record.iys - 1) *
                                         static_cast<std::size_t>(nx) +
                                     static_cast<std::size_t>(record.ixs - 1);

            // ADVECT: the cell's real profile over the vendor's own ZBOT/ZTOP.
            AdvectiveWindInputs wind_inputs;
            wind_inputs.met_format = 1;
            for (int level = 1; level <= nz; ++level) {
                const std::string u_label = "U-LEV  " + std::to_string(level);
                const std::string v_label = "V-LEV  " + std::to_string(level);
                require_true(hour_fields.count(u_label) == 1U && hour_fields.count(v_label) == 1U,
                             "the hour has no U/V profile for level " + std::to_string(level));
                wind_inputs.u_profile_ms.push_back(
                    static_cast<double>(hour_fields.at(u_label)[cell]));
                wind_inputs.v_profile_ms.push_back(
                    static_cast<double>(hour_fields.at(v_label)[cell]));
            }
            wind_inputs.face_heights_m.assign(summary.statics.cell_face_m.begin(),
                                              summary.statics.cell_face_m.end());
            wind_inputs.z_bottom_m = record.at(9);
            wind_inputs.z_top_m = record.at(8);
            const auto wind = cteas::puff::advective_wind(wind_inputs);
            compare(advect_u, record.at(10), wind.u_ms, 1.0e-4, "uadv_advect", record);
            compare(advect_v, record.at(11), wind.v_ms, 1.0e-4, "vadv_advect", record);

            if (rise_chain.enabled) {
                // COMP applies RISEWIND only for a Gaussian puff that has not
                // reached its final rise, on the CALMET path (METFM=1).
                const double xtotb = record.at(20);
                const bool gaussian = (record.icode % 2) != 0;
                double u = record.at(10);
                double v = record.at(11);
                double ws = std::hypot(u, v);
                if (gaussian && xtotb < rise_chain.x_final_m) {
                    cteas::puff::RiseWindInputs rise_inputs;
                    rise_inputs.puff = record.lpuff != 0;
                    rise_inputs.iterations = 2;                  // the vendor's COMP ncount
                    rise_inputs.dz_m = record.at(8) - record.at(7);   // ztop - htmet
                    rise_inputs.start_distance_m = xtotb;
                    rise_inputs.final_distance_m = rise_chain.x_final_m;
                    rise_inputs.final_height_m = rise_chain.z_final_m;
                    rise_inputs.step_seconds = record.at(63);    // tsamp_effective
                    rise_inputs.u_final_ms = u;
                    rise_inputs.v_final_ms = v;
                    rise_inputs.wind_speed_ms = ws;
                    const auto rise = [&rise_chain](double x) {
                        auto state = rise_chain.state;
                        state.x_m = x;
                        return cteas::puff::gradual_plume_height(state).height_m;
                    };
                    const auto step_wind = [&wind_inputs](double zbot, double ztop) {
                        auto inputs = wind_inputs;
                        inputs.z_bottom_m = zbot;
                        inputs.z_top_m = ztop;
                        return cteas::puff::advective_wind(inputs);
                    };
                    const auto adjusted =
                        cteas::puff::transitional_rise_wind(rise_inputs, rise, step_wind);
                    u = adjusted.u_ms;
                    v = adjusted.v_ms;
                    ws = adjusted.wind_speed_ms;
                    ++risewind_applied;
                } else {
                    ++risewind_skipped;
                }
                compare(adjusted_u, record.at(13), u, 1.0e-4, "uadv_adjusted", record);
                compare(adjusted_v, record.at(14), v, 1.0e-4, "vadv_adjusted", record);
                // COMP's calm treatment (wscalm/0.5, ucalm/0.001).
                bool calm = false;
                if (ws < 0.5) {
                    calm = true;
                    if (std::abs(v) < 0.001) v = 0.001;
                    ws = std::max(ws, 0.001);
                }
                compare(adjusted_ws, record.at(12), ws, 1.0e-4, "ws_adjusted", record);
                compare(adjusted_calm, record.at(15), calm ? 1.0 : 0.0, 0.0, "lcalm", record);

                // The inline step integration: the substep length the vendor used,
                // then the end-of-step position from the adjusted transport wind.
                cteas::puff::SubstepInputs substep;
                substep.sampling_step_s = record.at(17);          // tsamp entering
                substep.wind_speed_ms = ws;
                substep.puff = record.lpuff != 0;
                substep.free_slug = false;
                substep.subsampling = record.nsam < 99;
                substep.grid_spacing_m = summary.header.dx_m;
                substep.x_sam_len = 1.0;
                substep.substep_index = record.ksam;
                substep.sampling_steps = record.nsam;
                const auto computed_substep = cteas::puff::substep_length(substep);
                compare(step_length, record.at(63), computed_substep.step_s, 1.0e-3,
                        "tsamp_effective", record);
                compare(step_distance, record.at(60), computed_substep.step_s * ws, 1.0e-2,
                        "distm_from_step", record);

                cteas::puff::AdvanceInputs advance_inputs;
                advance_inputs.x_cells = record.at(1);
                advance_inputs.y_cells = record.at(2);
                advance_inputs.u_ms = u;
                advance_inputs.v_ms = v;
                advance_inputs.step_s = record.at(63);            // tsamp_effective
                advance_inputs.grid_spacing_m = summary.header.dx_m;
                advance_inputs.wind_speed_ms = ws;
                const auto advance = cteas::puff::advance_puff(advance_inputs);
                compare(position_x, record.at(39), advance.x_cells, 1.0e-4, "xnew", record);
                compare(position_y, record.at(40), advance.y_cells, 1.0e-4, "ynew", record);
                // DISTM is WS*TSAMP in REAL*4 on the vendor side; the transport
                // wind already carries the RISEWIND float rounding, so the
                // tolerance is the same 1e-4 relative band (about 0.01 m here).
                compare(step_distance_m, record.at(60), advance.distance_m, 1.0e-2, "distm",
                        record);

                // SETPUF's /CURRENT/ coordinate publication.
                cteas::puff::CurrentCoordinateInputs current_inputs;
                current_inputs.x_begin_cells = record.at(24);   // xpb_in
                current_inputs.y_begin_cells = record.at(25);   // ypb_in
                current_inputs.z_begin_m = record.at(26);       // zpb_in
                current_inputs.x_end_cells = record.at(39);     // xnew
                current_inputs.y_end_cells = record.at(40);     // ynew
                current_inputs.grid_spacing_m = summary.header.dx_m;
                current_inputs.step_s = record.at(63);          // tsamp_effective
                const auto current = cteas::puff::current_coordinates(current_inputs);
                compare(current_xb1, record.at(48), current.x_begin_m, 1.0e-3, "xb1", record);
                compare(current_yb1, record.at(49), current.y_begin_m, 1.0e-3, "yb1", record);
                compare(current_zb1, record.at(50), current.z_begin_m, 1.0e-3, "zb1", record);
                compare(current_xe1, record.at(51), current.x_end_m, 1.0e-3, "xe1", record);
                compare(current_ye1, record.at(52), current.y_end_m, 1.0e-3, "ye1", record);
                compare(current_ze1, record.at(53), current.z_end_m, 1.0e-3, "ze1", record);

                // GETCELL: the vendor's own cell for the puff's position.
                cteas::puff::CellLookupInputs cell_inputs;
                cell_inputs.x_cells = record.at(1);
                cell_inputs.y_cells = record.at(2);
                cell_inputs.nx = nx;
                cell_inputs.ny = ny;
                cell_inputs.domains = 1;
                cell_inputs.domain = 1;
                cell_inputs.nest_factor = 1.0;
                const auto cell = cteas::puff::grid_cell(cell_inputs);
                compare(cell_i, static_cast<double>(record.ixs), static_cast<double>(cell.i), 0.0,
                        "ixs", record);
                compare(cell_j, static_cast<double>(record.iys), static_cast<double>(cell.j), 0.0,
                        "iys", record);

                // The vendor's own cadence identities for a new point-source puff.
                compare(cadence_nsam, static_cast<double>(record.nsam),
                        std::round(static_cast<double>(control.required_int("NSECDT")) /
                                   record.at(17)),
                        1.0e-9, "nsam", record);
                compare(cadence_tsamp, record.at(17), record.at(18), 1.0e-6, "tsamp_reftsamp",
                        record);
                compare(cadence_reftsamp, record.at(63) <= record.at(17) ? 1.0 : 0.0, 1.0, 0.0,
                        "tsamp_not_exceeding_reference", record);
            }

            // PUFFDZ: the vendor's own inputs. SIGMA-Z is the value stored at the
            // start of the step = the previous substep's post-SETPUF sigma; for a
            // puff's first substep in this slice it is not carried, so that
            // substep is reported as unchecked rather than guessed.
            if (index == 0U) {
                ++first_substep_skipped;
                ++puffdz_top.unchecked;
                ++puffdz_bottom.unchecked;
                continue;
            }
            const double sigma_z = steps[index - 1U]->at(44);   // sigzb_out
            PuffExtentInputs extent;
            extent.puff_code = record.icode;
            extent.puff = record.lpuff != 0;
            extent.stability_class = record.istab;
            extent.puff_height_m = record.at(7);                 // htmet
            extent.mixing_height_m = record.at(4);               // dpbl
            extent.sigma_z_begin_m = sigma_z;
            extent.sigma_z_end_m = steps[index - 1U]->at(59);    // sze1_out
            // ZIOLD/ZIMAX are not in the dump. The vendor caps ZTOP at DPBL only
            // when DPBL is above HTMET, so those records are determined; the rest
            // are reported as unchecked (never guessed).
            const bool gaussian = (record.icode % 2) != 0;
            if (gaussian && !(record.at(4) > record.at(7)) && record.istab <= 4 &&
                record.icode != 3 && record.icode != 13) {
                ++cap_branch_skipped;
                ++puffdz_top.unchecked;
                ++puffdz_bottom.unchecked;
                continue;
            }
            extent.previous_mixing_height_m = record.at(4);
            extent.maximum_mixing_height_m = record.at(4);
            extent.layer_bottom_m = static_cast<double>(
                summary.statics.cell_face_m[static_cast<std::size_t>(record.ilayer - 1)]);
            extent.layer_top_m = static_cast<double>(
                summary.statics.cell_face_m[static_cast<std::size_t>(record.ilayer)]);
            const auto extent_result = cteas::puff::puff_extent(extent);
            compare(puffdz_top, record.at(8), extent_result.z_top_m, 1.0e-3, "ztop", record);
            compare(puffdz_bottom, record.at(9), extent_result.z_bottom_m, 1.0e-3, "zbot", record);
        }
    }

    const auto report = [](const char* name, const Tally& tally) {
        std::cout << "P7W_DGM_STEP_" << name << "=CASES=" << tally.cases
                  << " MISMATCHES=" << tally.mismatches << " UNCHECKED=" << tally.unchecked
                  << " MAX_ABS=" << tally.max_abs << " MAX_REL=" << tally.max_rel << '\n';
    };
    std::cout << "P7W_DGM_STEP_DUMP=" << dump_path << " RECORDS=" << records.size()
              << " PUFFS=" << puffs << " SUBSTEPS=" << substeps
              << " FIRST_SUBSTEP_SKIPPED=" << first_substep_skipped
              << " CAP_BRANCH_SKIPPED=" << cap_branch_skipped << " PACKED=" << hour_packed << '\n';
    report("ZT_VENDOR_VS_PORT_TOP", puffdz_top);
    report("ZT_VENDOR_VS_PORT_BOTTOM", puffdz_bottom);
    report("UADV_VENDOR_VS_PORT", advect_u);
    report("VADV_VENDOR_VS_PORT", advect_v);
    if (rise_chain.enabled) {
        std::cout << "P7W_DGM_STEP_RISEWIND_APPLIED=" << risewind_applied
                  << " SKIPPED=" << risewind_skipped << '\n';
        report("UADV_ADJUSTED_VENDOR_VS_PORT", adjusted_u);
        report("VADV_ADJUSTED_VENDOR_VS_PORT", adjusted_v);
        report("WS_ADJUSTED_VENDOR_VS_PORT", adjusted_ws);
        report("LCALM_VENDOR_VS_PORT", adjusted_calm);
        report("TSAMP_EFFECTIVE_VENDOR_VS_PORT", step_length);
        report("DISTM_VENDOR_VS_PORT", step_distance_m);
        report("XNEW_VENDOR_VS_PORT", position_x);
        report("YNEW_VENDOR_VS_PORT", position_y);
        report("DISTM_FROM_STEP_VS_WS_TIMES_TSAMP", step_distance);
        report("NSAM_IDENTITY", cadence_nsam);
        report("TSAMP_EQ_REFTSAMP", cadence_tsamp);
        report("TSAMP_NOT_ABOVE_REFERENCE", cadence_reftsamp);
        report("GETCELL_I_VENDOR_VS_PORT", cell_i);
        report("GETCELL_J_VENDOR_VS_PORT", cell_j);
        report("CURRENT_XB1_VENDOR_VS_PORT", current_xb1);
        report("CURRENT_YB1_VENDOR_VS_PORT", current_yb1);
        report("CURRENT_ZB1_VENDOR_VS_PORT", current_zb1);
        report("CURRENT_XE1_VENDOR_VS_PORT", current_xe1);
        report("CURRENT_YE1_VENDOR_VS_PORT", current_ye1);
        report("CURRENT_ZE1_VENDOR_VS_PORT", current_ze1);
    }
    std::cout << "P7W_DGM_STEP_COMPARISON_IS_NOT_A_CONC_COMPARISON=true\n";
    return 0;
}

// RISEWIND parity matrix: the same case grammar as reference/p7w_oracle_driver.f,
// with the oracle's deterministic GRISE/ADVECT stubs mirrored in C++ so the
// comparison isolates RISEWIND's own iteration.
int rise_wind_mode() {
    int cases = 0;
    int icase = 0;
    std::cout.precision(17);
    while (std::cin >> icase) {
        double xbeg = 0.0, xfinal = 0.0, zfinal = 0.0, dzb = 0.0, dt = 0.0;
        double ufnl = 0.0, vfnl = 0.0, h0 = 0.0, hr = 0.0, lr = 0.0;
        double a0 = 0.0, a1 = 0.0, a2 = 0.0, b0 = 0.0, b1 = 0.0, b2 = 0.0;
        int ncount = 0;
        if (!(std::cin >> xbeg >> xfinal >> zfinal >> dzb >> dt >> ufnl >> vfnl >> ncount >>
              h0 >> hr >> lr >> a0 >> a1 >> a2 >> b0 >> b1 >> b2)) {
            throw std::runtime_error("P7W probe: truncated rise-wind case");
        }
        cteas::puff::RiseWindInputs inputs;
        inputs.puff = true;
        inputs.iterations = ncount;
        inputs.dz_m = dzb;
        inputs.start_distance_m = xbeg;
        inputs.final_distance_m = xfinal;
        inputs.final_height_m = zfinal;
        inputs.step_seconds = dt;
        inputs.u_final_ms = ufnl;
        inputs.v_final_ms = vfnl;
        inputs.wind_speed_ms = std::hypot(ufnl, vfnl);
        const auto rise = [h0, hr, lr](double x) { return h0 + hr * (1.0 - std::exp(-x / lr)); };
        const auto wind = [a0, a1, a2, b0, b1, b2](double zbot, double ztop) {
            cteas::puff::AdvectiveWind result;
            result.u_ms = a0 + a1 * zbot + a2 * ztop;
            result.v_ms = b0 + b1 * zbot + b2 * ztop;
            return result;
        };
        const auto result = cteas::puff::transitional_rise_wind(inputs, rise, wind);
        std::cout << icase << ' ' << result.u_ms << ' ' << result.v_ms << ' '
                  << result.wind_speed_ms << '\n';
        ++cases;
    }
    std::cerr << "P7W_RISE_WIND_PROBE=PASS CASES=" << cases << '\n';
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 5 && std::string(argv[1]) == "--dgm-steps") {
            return dgm_steps_mode(argv[2], argv[3], argv[4], StackArgs{});
        }
        if (argc == 11 && std::string(argv[1]) == "--dgm-steps") {
            StackArgs stack;
            stack.enabled = true;
            stack.x_km = std::stod(argv[5]);
            stack.y_km = std::stod(argv[6]);
            stack.height_m = std::stod(argv[7]);
            stack.diameter_m = std::stod(argv[8]);
            stack.exit_velocity_ms = std::stod(argv[9]);
            stack.temperature_k = std::stod(argv[10]);
            return dgm_steps_mode(argv[2], argv[3], argv[4], stack);
        }
        if (argc == 2 && std::string(argv[1]) == "--rise-wind") return rise_wind_mode();
        std::cerr << "Usage: cteas_p7w_probe --dgm-steps DUMP_SLICE MET CONTROL "
                     "[STACK_X_KM STACK_Y_KM STACK_H_M DIAM_M VEXIT_MS TSTAK_K] | --rise-wind\n";
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "cteas_p7w_probe: " << error.what() << '\n';
        return 1;
    }
}
