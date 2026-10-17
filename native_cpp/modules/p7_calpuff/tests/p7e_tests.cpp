// P7E receptor geometry, puff-to-receptor sampling and CONC.DAT framing tests.
// Hand-derived expectations plus the measured structure of the frozen original
// artifact. Vendor-routine parity (PFSAMP, WRTI1D/WRTR1D framing) is checked
// separately by tests/p7e_parity_tests.py.
#include "cteas/puff/conc_file.hpp"
#include "cteas/puff/fortran_records.hpp"
#include "cteas/puff/receptors.hpp"

#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

namespace fs = std::filesystem;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7E TEST FAILURE: " + message);
}

void require_close(double observed, double expected, double tolerance, const std::string& what) {
    require(std::abs(observed - expected) <= tolerance,
            what + ": observed " + std::to_string(observed) + " expected " +
                std::to_string(expected) + " tolerance " + std::to_string(tolerance));
}

template <typename Callable>
void require_throw(Callable&& callable, const std::string& what) {
    bool threw = false;
    try {
        callable();
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    require(threw, what + " must fail closed");
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    require(bool(input), "cannot read " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

// Unlike read_conc_species_fields(), this preserves the seven raw I7
// characters and detects record-content differences that ordinary roundtrip
// parsing and record-length-only tests would silently accept.
std::string raw_species_I7(const std::string& path) {
    cteas::puff::FortranRecordReader reader(
        path, 4, cteas::puff::RecordByteOrder::LittleEndian);
    std::vector<std::uint8_t> record;
    while(reader.next(record)) {
        if (record.size() < 15U) continue;
        if (std::memcmp(record.data(), "H-3", 3U) == 0) {
            return std::string(
                reinterpret_cast<const char*>(record.data() + 8U), 7U);
        }
    }
    throw std::runtime_error("H-3 species field not found in original CONC.DAT");
}

// The frozen 143h WROUT1 output has exactly 286 32-byte period/grid
// descriptors. Compare the RAW payload bytes, not merely their counts and
// human-decoded timestamps. Original Fortran record markers are checked by
// the reader itself.
std::vector<std::string> original_32byte_descriptors(const std::string& path) {
    cteas::puff::FortranRecordReader reader(
        path, 4, cteas::puff::RecordByteOrder::LittleEndian);
    std::vector<std::uint8_t> record;
    std::vector<std::string> fields;
    while(reader.next(record)) {
        if (record.size() == 32U) {
            fields.emplace_back(
                reinterpret_cast<const char*>(record.data()),record.size());
        }
    }
    return fields;
}

std::string bytes_hex(const std::string& raw) {
    static constexpr char hex[] = "0123456789abcdef";
    std::string out;
    out.reserve(raw.size()*2U);
    for(const unsigned char v : raw) {
        out.push_back(hex[v>>4U]);
        out.push_back(hex[v&0xfU]);
    }
    return out;
}

std::string control_text() {
    return R"(
! NX = 50 !
! NY = 50 !
! NZ = 9 !
! DGRIDKM = 0.1 !
! XORIGKM = 510.885 !
! YORIGKM = 3531.269 !
! IBCOMP = 1 !
! JBCOMP = 1 !
! IECOMP = 50 !
! JECOMP = 50 !
! LSAMP = T !
! IBSAMP = 1 !
! JBSAMP = 1 !
! IESAMP = 50 !
! JESAMP = 50 !
! MESHDN = 1 !
NON-GRIDDED (DISCRETE) RECEPTOR DATA
!END!
)";
}

std::string control_with(const std::string& replacement, const std::string& original) {
    std::string text = control_text();
    const auto position = text.find(original);
    require(position != std::string::npos, "fixture mutation target absent: " + original);
    text.replace(position, original.size(), replacement);
    return text;
}

void test_receptor_geometry() {
    const auto receptors = cteas::puff::receptors_from_control(control_text());
    require(receptors.gridded, "gridded receptors enabled");
    require(receptors.sampling_nx == 50 && receptors.sampling_ny == 50, "sampling grid 50x50");
    require(receptors.mesh_down == 1, "MESHDN");
    require_close(receptors.spacing_km, 0.1, 1.0e-12, "spacing");
    require(receptors.grid.size() == 2500U, "2500 gridded receptors");
    require(receptors.discrete.empty(), "no discrete receptors in the locked configuration");
    // Vendor convention: first receptor at (IBSAMP-0.5)*DGRID from the origin.
    require_close(receptors.grid.front().x_km, 510.885 + 0.05, 1.0e-9, "first receptor X");
    require_close(receptors.grid.front().y_km, 3531.269 + 0.05, 1.0e-9, "first receptor Y");
    require_close(receptors.grid.back().x_km, 510.885 + 0.05 + 49.0 * 0.1, 1.0e-9, "last receptor X");
    require_close(receptors.grid.back().y_km, 3531.269 + 0.05 + 49.0 * 0.1, 1.0e-9, "last receptor Y");

    // MESHDN=2 refines the sampling grid inside the same cell range.
    const auto refined = cteas::puff::receptors_from_control(
        control_with("! MESHDN = 2 !", "! MESHDN = 1 !"));
    require(refined.sampling_nx == 99 && refined.sampling_ny == 99, "refined sampling grid size");
    require_close(refined.spacing_km, 0.05, 1.0e-12, "refined spacing");
    require(refined.grid.size() == 99U * 99U, "refined receptor count");

    // Discrete receptors from the documented subgroup 17b format.
    const auto discrete = cteas::puff::receptors_from_control(control_with(
        "NON-GRIDDED (DISCRETE) RECEPTOR DATA\n! 1 = 510.9, 3531.3, 12.5, 1.5 !\n! 2 = 511.0, 3531.4, 0.0 !\n!END!",
        "NON-GRIDDED (DISCRETE) RECEPTOR DATA\n!END!"));
    require(discrete.discrete.size() == 2U, "two discrete receptors parsed");
    require_close(discrete.discrete.front().ground_elevation_m, 12.5, 1.0e-12, "discrete elevation");
    require_close(discrete.discrete.front().height_m, 1.5, 1.0e-12, "discrete height");
    require_close(discrete.discrete.back().height_m, 0.0, 1.0e-12, "default receptor height");

    // Fail closed.
    require_throw([] {
        (void)cteas::puff::receptors_from_control(
            control_with("! IESAMP = 60 !", "! IESAMP = 50 !"));
    }, "sampling grid outside the met grid");
    require_throw([] {
        (void)cteas::puff::receptors_from_control(
            control_with("! IECOMP = 30 !", "! IECOMP = 50 !"));
    }, "sampling grid outside the computational grid");
    require_throw([] {
        (void)cteas::puff::receptors_from_control(control_with("! MESHDN = 0 !", "! MESHDN = 1 !"));
    }, "MESHDN below one");
    require_throw([] {
        (void)cteas::puff::receptors_from_control(
            control_with("! LSAMP = F !", "! LSAMP = T !"));
    }, "neither gridded nor discrete receptors");
    require_throw([] {
        (void)cteas::puff::receptors_from_control(control_with(
            "NON-GRIDDED (DISCRETE) RECEPTOR DATA\n! 1 = 600.0, 3531.3, 0.0 !\n!END!",
            "NON-GRIDDED (DISCRETE) RECEPTOR DATA\n!END!"));
    }, "discrete receptor outside the met grid");
    require_throw([] {
        (void)cteas::puff::receptors_from_control(control_with(
            "NON-GRIDDED (DISCRETE) RECEPTOR DATA\n! 1 = 510.9, 3531.3 !\n!END!",
            "NON-GRIDDED (DISCRETE) RECEPTOR DATA\n!END!"));
    }, "discrete receptor with too few values");
    std::cout << "P7E_RECEPTOR_GEOMETRY=PASS GRID_RECEPTORS=2500 SPACING_KM=0.1\n";
}

void test_original_pfscrn() {
    using cteas::puff::original_puff_screen;
    // CALPUFF L4649-4679, REAL4. Moving 0->2 along X with radius 1.
    const auto on=original_puff_screen(0,0,2,0,1,0,1);
    require(on.has_impact && !on.calm_midpoint_branch &&
            on.closest_distance_squared==0.0,
            "PFSCRN moving on-track receptor incorrectly screened");
    const auto near=original_puff_screen(0,0,2,0,1,0.5,1);
    require(near.has_impact && near.closest_distance_squared==0.25,
            "PFSCRN missed perpendicular nearest approach");
    const auto edge=original_puff_screen(0,0,2,0,3,0,1);
    require(edge.has_impact && edge.closest_distance_squared==1.0,
            "PFSCRN radius threshold must be inclusive");
    const auto far=original_puff_screen(0,0,2,0,3.01,0,1);
    require(!far.has_impact,"PFSCRN out-of-radius receptor not excluded");
    const auto still=original_puff_screen(0,0,0,0,0.2,0,1);
    require(still.has_impact && still.calm_midpoint_branch,
            "PFSCRN calm midpoint branch incorrectly selected");
    const auto midpoint=original_puff_screen(0,0,0.00001,0,0.2,0,1);
    require(midpoint.calm_midpoint_branch && midpoint.has_impact,
            "PFSCRN short trajectory must use original a<1.e-4");
    require_throw([]{(void)original_puff_screen(0,0,1,0,0,0,0);},
                  "PFSCRN accepted zero radius");
    require_throw([]{(void)original_puff_screen(0,0,1,0,0,0,std::nan(""));},
                  "PFSCRN accepted NaN radius");
    std::cout<<"P7E_ORIGINAL_PFSCRN_REAL4=PASS MOVING=YES CALM=YES"
             <<" INCLUSIVE_RADIUS=YES FAIL_CLOSED=YES\n";
}

void test_sampling_integrals() {
    // Low-wind shortcut: A < 1e-4 -> xi2 = 0.5*exp(-dist2/(2*tsy)), xi1 = 2*xi2.
    const auto low = cteas::puff::puff_sampling_integrals(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0, 0.0);
    require(low.low_wind_branch, "stationary puff uses the low-wind branch");
    require_close(low.i2, 0.5, 1.0e-6, "low-wind I2");
    require_close(low.i1, 1.0, 1.0e-6, "low-wind I1");
    const auto offset = cteas::puff::puff_sampling_integrals(0.0, 0.0, 0.0, 0.0, 0.0, 100.0, 100.0,
                                                             100.0 * 100.0);
    require_close(offset.i2, 0.5 * std::exp(-0.5), 1.0e-6, "low-wind I2 with offset");

    // Reversing the trajectory leaves the sampling integrals unchanged.
    const auto forward = cteas::puff::puff_sampling_integrals(0.0, 0.0, 0.5, 0.0, 0.25, 0.1, 50.0,
                                                              0.01);
    const auto backward = cteas::puff::puff_sampling_integrals(0.5, 0.0, 0.0, 0.0, 0.25, 0.1, 50.0,
                                                               0.01);
    require(!forward.low_wind_branch, "moving puff does not use the low-wind branch");
    require_close(backward.i1, forward.i1, 1.0e-9, "I1 is invariant under trajectory reversal");
    require_close(backward.i2, forward.i2, 1.0e-9, "I2 is invariant under trajectory reversal");

    // A trajectory that ends far away with a large crosswind offset gives a
    // much smaller integral than one passing through the receptor.
    const auto through = cteas::puff::puff_sampling_integrals(0.0, 0.0, 1.0, 0.0, 0.5, 0.0, 20.0,
                                                              0.0);
    const auto far = cteas::puff::puff_sampling_integrals(0.0, 0.0, 1.0, 0.0, 0.5, 5.0, 20.0, 25.0);
    require(through.i1 > far.i1, "closer approach must sample more mass");

    // ERFDIF branches: same-sign small, same-sign large, opposite signs, equal.
    require_close(cteas::puff::erf_difference(0.4, 0.1), std::erf(0.4) - std::erf(0.1), 1.0e-6,
                  "ERFDIF small same-sign");
    require_close(cteas::puff::erf_difference(1.0, 0.8), std::erf(1.0) - std::erf(0.8), 1.0e-6,
                  "ERFDIF erfc branch");
    require_close(cteas::puff::erf_difference(-0.5, -1.0), std::erf(-0.5) - std::erf(-1.0), 1.0e-6,
                  "ERFDIF negative same-sign");
    require_close(cteas::puff::erf_difference(0.5, -0.5), std::erf(0.5) - std::erf(-0.5), 1.0e-6,
                  "ERFDIF opposite signs");
    require_close(cteas::puff::erf_difference(10.0, 9.5), 0.0, 1.0e-12, "ERFDIF large arguments");
    require_close(cteas::puff::erf_difference(0.3, 0.3), 0.0, 1.0e-12, "ERFDIF equal arguments");

    require_throw([] {
        (void)cteas::puff::puff_sampling_integrals(0.0, 0.0, 1.0, 0.0, 0.5, 0.0, 0.0, 0.0);
    }, "zero sigma-y");
    require_throw([] {
        (void)cteas::puff::puff_sampling_integrals(0.0, 0.0, 1.0, 0.0, 0.5, 0.0, 20.0, -1.0);
    }, "negative closest-approach distance squared");
    std::cout << "P7E_PFSAMP_AND_ERFDIF=PASS\n";
}

void test_accumulation() {
    // Hand-derived: dinv = ASDF/(2*pi*sigma**2); t2 = i2*dinv; t1 = i1*dinv - t2.
    cteas::puff::SamplingIntegrals integrals;
    integrals.i1 = 2.0;
    integrals.i2 = 1.0;
    cteas::puff::ReceptorAccumulationInputs inputs;
    inputs.mass_old = 10.0;
    inputs.mass_new = 8.0;
    inputs.sigma_y_at_receptor_m = 50.0;
    inputs.vertical_factor = 0.002;
    inputs.time_fraction = 0.5;
    inputs.deposition_ratio = 0.9;
    const double inverse = 1.0 / (6.2831853 * 50.0 * 50.0);
    const double t2 = 1.0 * inverse;
    const double t1 = 2.0 * inverse - t2;
    const double expected = 0.9 * 0.002 * 0.5 * (10.0 * t1 + 8.0 * t2);
    require_close(cteas::puff::receptor_concentration_increment(integrals, inputs), expected,
                  1.0e-12, "accumulation closed form");
    require_throw([&] {
        auto bad = inputs;
        bad.sigma_y_at_receptor_m = 0.0;
        (void)cteas::puff::receptor_concentration_increment(integrals, bad);
    }, "zero sigma-y at receptor");
    require_throw([&] {
        auto bad = inputs;
        bad.time_fraction = 0.0;
        (void)cteas::puff::receptor_concentration_increment(integrals, bad);
    }, "zero time fraction");
    require_throw([&] {
        auto bad = inputs;
        bad.time_fraction = 1.5;
        (void)cteas::puff::receptor_concentration_increment(integrals, bad);
    }, "time fraction above one");
    require_throw([&] {
        auto bad = inputs;
        bad.vertical_factor = -1.0;
        (void)cteas::puff::receptor_concentration_increment(integrals, bad);
    }, "negative vertical factor");
    require_throw([&] {
        auto bad = inputs;
        bad.area_source_factor = -1.0;
        (void)cteas::puff::receptor_concentration_increment(integrals, bad);
    }, "negative area source factor");
    require_throw([&] {
        auto bad = inputs;
        bad.mass_old = std::nan("");
        (void)cteas::puff::receptor_concentration_increment(integrals, bad);
    }, "NaN mass");
    std::cout << "P7E_RECEPTOR_ACCUMULATION=PASS\n";
}

void test_conc_file_round_trip(const fs::path& root) {
    const fs::path path = root / "roundtrip.con";
    {
        cteas::puff::ConcFileWriter writer(path.string(), "2.2", "CTEAS P7E test",
                                           {"comment one", "comment two"});
        cteas::puff::ConcPeriod period;
        period.begin_year = 2022;
        period.begin_julian = 1;
        period.begin_hour = 0;
        period.end_year = 2022;
        period.end_julian = 1;
        period.end_hour = 1;
        writer.write_period_record(period);
        cteas::puff::ConcGridDescriptor descriptor;
        descriptor.group_name = "TOTAL";
        descriptor.x_origin_km = 510.885;
        descriptor.y_origin_km = 3531.269;
        writer.write_grid_descriptor(descriptor);
        std::vector<float> values(4U, 1.5F);
        writer.write_species_field("H-3", 1, 2, 2, values);
        writer.close();
    }
    require(raw_species_I7(path.string()) == "      1",
            "new writer must encode original species I7 right-justified");
    const auto summary = cteas::puff::summarize_conc_file(path.string());
    require(summary.records == 7U, "version + count + 2 comments + period + grid + field");
    require(summary.period_records == 1U && summary.grid_records == 1U &&
                summary.species_field_records == 1U,
            "record classification");
    const auto periods = cteas::puff::read_conc_periods(path.string());
    require(periods.size() == 1U && periods.front().begin_julian == 1 && periods.front().end_hour == 1,
            "period round trip");
    const auto fields = cteas::puff::read_conc_species_fields(path.string(), 2, 2);
    require(fields.size() == 1U && fields.front().label.rfind("H-3", 0U) == 0U &&
                fields.front().species_index == 1 && fields.front().values.size() == 4U,
            "species field round trip");
    require_close(fields.front().values.front(), 1.5, 1.0e-12, "field value");
    require_throw([&path] { (void)cteas::puff::read_conc_species_fields(path.string(), 3, 3); },
                  "wrong expected dimensions");
    require_throw([&root] {
        cteas::puff::ConcFileWriter writer((root / "bad.con").string(), "2.2", "x", {});
        cteas::puff::ConcPeriod period;
        period.begin_year = 2022;
        period.begin_julian = 400;   // illegal julian day
        writer.write_period_record(period);
    }, "illegal period");
    require_throw([&root] {
        cteas::puff::ConcFileWriter writer((root / "bad2.con").string(), "2.2", "x", {});
        std::vector<float> values(3U, 1.0F);
        writer.write_species_field("H-3", 1, 2, 2, values);
    }, "field value count mismatch");
    std::cout << "P7E_CONC_FILE_ROUND_TRIP=PASS\n";
}

void test_frozen_structure(const fs::path& root, const std::string& frozen_path) {
    const auto frozen = cteas::puff::summarize_conc_file(frozen_path);
    require(frozen.period_records == 143U && frozen.grid_records == 143U &&
                frozen.species_field_records == 143U,
            "frozen artifact record classification");
    require(frozen.species_field_counts.size() == 1U &&
                frozen.species_field_counts.front().first.rfind("H-3", 0U) == 0U &&
                frozen.species_field_counts.front().second == 143U,
            "frozen artifact H-3 field count");
    require(frozen.species_field_sizes.front() == 10015U &&
                frozen.species_field_sizes.back() == 10015U,
            "frozen artifact field size");

    // Structure-only parity: a CTEAS file written for the same configuration
    // must reproduce the data-record sequence of the frozen artifact. Values
    // are this module's own, so no value comparison is claimed.
    const fs::path path = root / "structure.con";
    {
        cteas::puff::ConcFileWriter writer(path.string(), "2.2", "CTEAS P7E structure",
                                           {"structure parity fixture"});
        std::vector<float> values(2500U, 0.0F);
        for (std::size_t hour = 0; hour < 143U; ++hour) {
            cteas::puff::ConcPeriod period;
            period.begin_year = 2022;
            period.begin_julian = 1 + static_cast<int>(hour / 24U);
            period.begin_hour = static_cast<int>(hour % 24U);
            period.end_year = 2022;
            period.end_julian = 1 + static_cast<int>((hour + 1U) / 24U);
            period.end_hour = static_cast<int>((hour + 1U) % 24U);
            writer.write_period_record(period);
            // The original WROUT1 header uses MET.DAT grid origins in
            // metres and a single REAL4 0.001 multiplier, not a float cast
            // of the 3-decimal puff.inp kilometre text.
            const auto descriptor = cteas::puff::original_met_grid_descriptor(
                510885.0F, 3531269.0F);
            require(descriptor.group_index == 1 &&
                    descriptor.x_origin_km == static_cast<double>(510.885009765625F) &&
                    descriptor.y_origin_km == static_cast<double>(3531.269287109375F),
                    "WROUT1 original metadata must use REAL4 MET origin and group one");
            writer.write_grid_descriptor(descriptor);
            writer.write_species_field("H-3", 1, 50, 50, values);
        }
        writer.close();
    }
    const auto original_I7 = raw_species_I7(frozen_path);
    const auto native_I7 = raw_species_I7(path.string());
    require(original_I7 == "      1",
            "locked original Fortran species field no longer has canonical I7 bytes");
    require(native_I7 == original_I7,
            "native WROUT1 species index bytes differ from original frozen puff.con");
    const auto ours = cteas::puff::summarize_conc_file(path.string());
    require(ours.period_records == frozen.period_records &&
                ours.grid_records == frozen.grid_records &&
                ours.species_field_records == frozen.species_field_records,
            "data-record counts must match the frozen artifact");
    require(ours.species_field_sizes == frozen.species_field_sizes,
            "species field record sizes must match the frozen artifact");
    require(ours.species_field_counts.front().second ==
                frozen.species_field_counts.front().second,
            "species field counts must match the frozen artifact");
    const auto frozen_descriptors=original_32byte_descriptors(frozen_path);
    const auto native_descriptors=original_32byte_descriptors(path.string());
    require(frozen_descriptors.size()==286U && native_descriptors.size()==286U,
            "143-hour original WROUT1 must have exactly 286 period/grid records");
    for(std::size_t i=0; i<286U; ++i) {
        require(native_descriptors[i]==frozen_descriptors[i],
                "2022 original WROUT1 32-byte metadata mismatch at record " +
                std::to_string(i+1U) + " original=" + bytes_hex(frozen_descriptors[i]) +
                " native=" + bytes_hex(native_descriptors[i]));
    }
    std::cout<<"P7E_ORIGINAL_WROUT1_32BYTE_METADATA=PASS RECORDS=286 HOURS=143\n";
    const auto ours_periods = cteas::puff::read_conc_periods(path.string());
    const auto frozen_periods = cteas::puff::read_conc_periods(frozen_path);
    require(ours_periods.size() == frozen_periods.size(), "period record counts must match");
    require(ours_periods.front().begin_year == frozen_periods.front().begin_year &&
                ours_periods.front().begin_julian == frozen_periods.front().begin_julian &&
                ours_periods.back().end_julian == frozen_periods.back().end_julian &&
                ours_periods.back().end_hour == frozen_periods.back().end_hour,
            "period record times must match the frozen artifact");
    std::cout << "P7E_FROZEN_STRUCTURE_PARITY=PASS RECORDS=" << frozen.records
              << " PERIODS=" << frozen.period_records << " FIELDS=" << frozen.species_field_records
              << " FIELD_BYTES=" << frozen.species_field_sizes.front() << "\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        std::string frozen;
        std::string control;
        for (int index = 1; index < argc; ++index) {
            const std::string option = argv[index];
            if (option == "--frozen-conc" && index + 1 < argc) {
                frozen = argv[++index];
            } else if (option == "--control" && index + 1 < argc) {
                control = argv[++index];
            } else {
                std::cerr << "Usage: cteas_p7e_tests [--control CONTROL_FILE] [--frozen-conc CONC.DAT]\n";
                return 2;
            }
        }
        std::random_device random;
        const fs::path root =
            fs::temp_directory_path() /
            ("p7e-tests-" + std::to_string(random()) + "-" +
             std::to_string(std::chrono::high_resolution_clock::now().time_since_epoch().count()));
        fs::remove_all(root);
        fs::create_directories(root);

        test_receptor_geometry();
        test_original_pfscrn();
        test_sampling_integrals();
        test_accumulation();
        test_conc_file_round_trip(root);
        if (!control.empty()) {
            const auto receptors = cteas::puff::receptors_from_control(read_text(control));
            require(receptors.grid.size() == 2500U, "locked deck must define 2500 grid receptors");
            std::cout << "P7E_LOCKED_CASE_RECEPTORS=PASS GRID_RECEPTORS=" << receptors.grid.size()
                      << " DISCRETE=" << receptors.discrete.size() << "\n";
        }
        if (!frozen.empty()) test_frozen_structure(root, frozen);

        fs::remove_all(root);
        std::cout << "P7E_RECEPTOR_SAMPLING_CONC_CONTRACT=PASS\n"
                     "P7E_VALUE_COMPARISON_WITH_FROZEN_CONC=NOT_CLAIMED_FULL_MODEL_MISSING\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 1;
    }
}
