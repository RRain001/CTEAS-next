// P6F <-> E22 cross-read test.
//
// The P6F writer must produce files that the independent P6E output-contract
// reader of calmet_dat21.hpp (the E22 contract, read-only here) parses without
// loss, and P6F must be able to read what the E22 writer produces. When the
// frozen real 2022 reference file is passed as argv[1] the same check is run on
// all 143 intervals x 45 fields of the re-serialised real case.
//
// The E22 header is consumed strictly as a decoder: this test never modifies
// the P6E module and the P6F library itself does not depend on it.
#include "cteas/p6f/calmet_dat21_writer.hpp"

#include "cteas/p6e/calmet_dat21.hpp"

#include <cassert>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {

std::string temp_path(const std::string& name) {
    return (std::filesystem::temp_directory_path() / name).string();
}

std::string trim_label(const std::string& text) {
    const auto first = text.find_first_not_of(' ');
    if(first == std::string::npos)return std::string();
    const auto last = text.find_last_not_of(' ');
    return text.substr(first, last - first + 1U);
}

// Explicit field arrays for one synthetic dataset, shared by both sides.
struct Fixture {
    int nx = 4, ny = 3, nz = 2, hours = 2;
    int nssta = 1, nusta = 1, npsta = 0;
    std::size_t cells() const {
        return static_cast<std::size_t>(nx) * static_cast<std::size_t>(ny);
    }
};

cteas::p6f::Calmet21File p6f_fixture(const Fixture& f) {
    using namespace cteas::p6f;
    Calmet21File file;
    Calmet21Header& h = file.header;
    Calmet21Statics& s = file.statics;
    const std::size_t cells = f.cells();
    h.nx = f.nx;
    h.ny = f.ny;
    h.nz = f.nz;
    h.dgrid_m = 100.f;
    h.xorigin_m = 510885.f;
    h.yorigin_m = 3531269.f;
    h.timezone = "UTC+0000";
    h.irtype = 1;
    h.iwfcod = 1;
    h.nssta = f.nssta;
    h.nusta = f.nusta;
    h.npsta = f.npsta;
    h.nlu = 14;
    h.iwat1 = 50;
    h.iwat2 = 55;
    h.lcalgrd = true;
    h.irlg = f.hours;
    h.comments = {"P6F/E22 cross-read fixture"};
    h.projection.pmap = "UTM";
    h.projection.datum = "WGS-84";
    h.projection.daten = "02-21-2003";
    h.projection.utmhem = "N";
    h.projection.iutmzn = 50;
    const std::int64_t start = days_from_civil(2022, 1U, 1U) * 86400;
    const Calmet21Calendar begin = calendar_from_instant(start);
    const Calmet21Calendar end = calendar_from_instant(
        start + static_cast<std::int64_t>(f.hours) * 3600);
    h.begin_year = begin.year;
    h.begin_month = begin.month;
    h.begin_day = begin.day;
    h.begin_hour = begin.hour;
    h.begin_second = begin.second;
    h.end_year = end.year;
    h.end_month = end.month;
    h.end_day = end.day;
    h.end_hour = end.hour;
    h.end_second = end.second;
    for(int face = 0; face <= f.nz; ++face)
        s.zface_m.push_back(120.f * static_cast<float>(face));
    s.surface_x_m.assign(static_cast<std::size_t>(f.nssta), 2500.f);
    s.surface_y_m.assign(static_cast<std::size_t>(f.nssta), 2500.f);
    s.upper_x_m.assign(static_cast<std::size_t>(f.nusta), 2500.f);
    s.upper_y_m.assign(static_cast<std::size_t>(f.nusta), 2600.f);
    s.precip_x_m.assign(static_cast<std::size_t>(f.npsta), 2400.f);
    s.precip_y_m.assign(static_cast<std::size_t>(f.npsta), 2450.f);
    s.z0_m.assign(cells, 0.5f);
    s.elev_m.assign(cells, 25.f);
    s.xlai.assign(cells, 1.5f);
    s.ilandu.assign(cells, 12);
    if(f.nssta >= 1)s.nears.assign(cells, 1);
    const std::vector<std::string> labels =
        hourly_labels(f.nz, 1, true, f.npsta);
    for(int hour = 0; hour < f.hours; ++hour) {
        const Calmet21Time t =
            instant_to_time(start + static_cast<std::int64_t>(hour) * 3600);
        Calmet21Time e = t;
        e.seconds += 3600;
        for(const std::string& label : labels) {
            Calmet21Field field;
            field.label = label;
            field.begin = t;
            field.end = e;
            field.integer = is_integer_label(label);
            const std::string name = trim_label(label);
            if(field.integer) {
                field.integer_values.resize(cells);
                for(std::size_t k = 0; k < cells; ++k)
                    field.integer_values[k] =
                        name == "IPGT" ? 1 + static_cast<std::int32_t>(k % 6)
                                       : 40 + static_cast<std::int32_t>(k % 50);
            } else {
                field.real_values.resize(cells);
                for(std::size_t k = 0; k < cells; ++k)
                    field.real_values[k] =
                        static_cast<float>(k) * 0.25f - 1.f;
            }
            file.hourly.push_back(std::move(field));
        }
    }
    return file;
}

// The same dataset expressed through the E22 writer contract.
void e22_fixture(const Fixture& f, cteas::p6e::CalmetDat21Header& h,
                 cteas::p6e::CalmetDat21Static& s,
                 std::vector<cteas::p6e::CalmetDat21Field>& hourly) {
    const cteas::p6f::Calmet21File source = p6f_fixture(f);
    const std::size_t cells = f.cells();
    h.nx = source.header.nx;
    h.ny = source.header.ny;
    h.nz = source.header.nz;
    h.dgrid_m = source.header.dgrid_m;
    h.xorigin_m = source.header.xorigin_m;
    h.yorigin_m = source.header.yorigin_m;
    h.timezone = "UTC+0000";
    h.irtype = 1;
    h.iwfcod = 1;
    h.nssta = f.nssta;
    h.nusta = f.nusta;
    h.npsta = f.npsta;
    h.nlu = 14;
    h.iwat1 = 50;
    h.iwat2 = 55;
    h.lcalgrd = true;
    h.run_hours = f.hours;
    h.comments = {"P6F/E22 cross-read fixture"};
    h.begin_year = source.header.begin_year;
    h.begin_month = source.header.begin_month;
    h.begin_day = source.header.begin_day;
    h.begin_hour = source.header.begin_hour;
    h.begin_second = source.header.begin_second;
    h.end_year = source.header.end_year;
    h.end_month = source.header.end_month;
    h.end_day = source.header.end_day;
    h.end_hour = source.header.end_hour;
    h.end_second = source.header.end_second;
    h.controls_tail = cteas::p6e::calmet21_default_controls_tail();
    s.zface_m = source.statics.zface_m;
    s.surface_x_m.assign(static_cast<std::size_t>(f.nssta), 2500.f);
    s.surface_y_m.assign(static_cast<std::size_t>(f.nssta), 2500.f);
    s.upper_x_m.assign(static_cast<std::size_t>(f.nusta), 2500.f);
    s.upper_y_m.assign(static_cast<std::size_t>(f.nusta), 2600.f);
    s.precip_x_m.assign(static_cast<std::size_t>(f.npsta), 2400.f);
    s.precip_y_m.assign(static_cast<std::size_t>(f.npsta), 2450.f);
    s.z0_m.assign(cells, 0.5f);
    s.elev_m.assign(cells, 25.f);
    s.xlai.assign(cells, 1.5f);
    s.ilandu.assign(cells, 12);
    if(f.nssta >= 1)s.nears.assign(cells, 1);
    hourly.clear();
    for(const cteas::p6f::Calmet21Field& field : source.hourly) {
        cteas::p6e::CalmetDat21Field out;
        // The E22 contract keeps the label up to the original padding (its
        // 2-D labels are the bare four-to-five letter names, its levelled
        // labels the padded I3 form); both are re-padded to the 8-byte file
        // field by each writer.
        out.label = trim_label(field.label);
        out.begin.year = field.begin.year;
        out.begin.julian_day = field.begin.julian_day;
        out.begin.hour = field.begin.hour;
        out.begin.seconds = field.begin.seconds;
        out.end.year = field.end.year;
        out.end.julian_day = field.end.julian_day;
        out.end.hour = field.end.hour;
        out.end.seconds = field.end.seconds;
        out.integer = field.integer;
        out.real_values = field.real_values;
        out.integer_values = field.integer_values;
        hourly.push_back(std::move(out));
    }
}

void same_real_values(const std::vector<float>& a, const std::vector<float>& b,
                      const std::string& what) {
    assert(a.size() == b.size());
    for(std::size_t k = 0; k < a.size(); ++k) {
        if(std::memcmp(&a[k], &b[k], sizeof(float)) != 0) {
            std::cerr << "E22_CROSS_READ_VALUE_MISMATCH " << what << " cell " << k
                      << "\n";
            assert(false);
        }
    }
}

// p6f dataset (authoritative explicit arrays) vs the E22 reader's view.
void compare_against_e22(const cteas::p6f::Calmet21File& mine,
                         const cteas::p6e::CalmetDat21Dataset& theirs,
                         const std::string& what) {
    const cteas::p6f::Calmet21Header& h = mine.header;
    const cteas::p6e::CalmetDat21Header& t = theirs.header;
    assert(t.nx == h.nx && t.ny == h.ny && t.nz == h.nz);
    assert(t.dgrid_m == h.dgrid_m && t.xorigin_m == h.xorigin_m &&
           t.yorigin_m == h.yorigin_m);
    assert(t.irtype == h.irtype && t.iwfcod == h.iwfcod &&
           t.lcalgrd == h.lcalgrd);
    assert(t.nssta == h.nssta && t.nusta == h.nusta && t.npsta == h.npsta &&
           t.nowsta == h.nowsta && t.nlu == h.nlu && t.iwat1 == h.iwat1 &&
           t.iwat2 == h.iwat2);
    assert(trim_label(t.timezone) == trim_label(h.timezone));
    assert(t.run_hours == h.irlg);
    assert(t.comments.size() == h.comments.size());
    for(std::size_t k = 0; k < t.comments.size(); ++k)
        assert(trim_label(t.comments[k]) == trim_label(h.comments[k]));
    assert(t.begin_year == h.begin_year && t.begin_month == h.begin_month &&
           t.begin_day == h.begin_day && t.begin_hour == h.begin_hour &&
           t.begin_second == h.begin_second && t.end_year == h.end_year &&
           t.end_month == h.end_month && t.end_day == h.end_day &&
           t.end_hour == h.end_hour && t.end_second == h.end_second);
    same_real_values(mine.statics.zface_m, theirs.statics.zface_m, "ZFACE");
    same_real_values(mine.statics.surface_x_m, theirs.statics.surface_x_m,
                     "XSSTA");
    same_real_values(mine.statics.surface_y_m, theirs.statics.surface_y_m,
                     "YSSTA");
    same_real_values(mine.statics.upper_x_m, theirs.statics.upper_x_m, "XUSTA");
    same_real_values(mine.statics.upper_y_m, theirs.statics.upper_y_m, "YUSTA");
    same_real_values(mine.statics.precip_x_m, theirs.statics.precip_x_m,
                     "XPSTA");
    same_real_values(mine.statics.precip_y_m, theirs.statics.precip_y_m,
                     "YPSTA");
    same_real_values(mine.statics.z0_m, theirs.statics.z0_m, "Z0");
    same_real_values(mine.statics.elev_m, theirs.statics.elev_m, "ELEV");
    same_real_values(mine.statics.xlai, theirs.statics.xlai, "XLAI");
    assert(mine.statics.ilandu == theirs.statics.ilandu);
    assert(mine.statics.nears == theirs.statics.nears);
    assert(mine.hourly.size() == theirs.hourly.size());
    assert(theirs.intervals == cteas::p6f::interval_count(mine));
    for(std::size_t k = 0; k < mine.hourly.size(); ++k) {
        const cteas::p6f::Calmet21Field& a = mine.hourly[k];
        const cteas::p6e::CalmetDat21Field& b = theirs.hourly[k];
        if(trim_label(a.label) != trim_label(b.label)) {
            std::cerr << "E22_CROSS_READ_LABEL_MISMATCH " << what << " record " << k
                      << ": " << trim_label(a.label) << " != " << trim_label(b.label)
                      << "\n";
            assert(false);
        }
        assert(a.integer == b.integer);
        assert(a.begin.year == b.begin.year && a.begin.julian_day == b.begin.julian_day &&
               a.begin.hour == b.begin.hour && a.begin.seconds == b.begin.seconds);
        assert(a.end.year == b.end.year && a.end.julian_day == b.end.julian_day &&
               a.end.hour == b.end.hour && a.end.seconds == b.end.seconds);
        if(a.integer)
            assert(a.integer_values == b.integer_values);
        else
            same_real_values(a.real_values, b.real_values, trim_label(a.label));
    }
    std::cout << "E22_CROSS_READ_PASS " << what
              << " field_records=" << mine.hourly.size() << "\n";
}

}  // namespace

int main(int argc, char** argv) {
    // 1. P6F writes, the E22 reader reads.
    const Fixture fixture;
    const cteas::p6f::Calmet21File mine = p6f_fixture(fixture);
    const std::string written = temp_path("cteas_p6f_e22_cross_read.dat");
    cteas::p6f::write_calmet_dat21(written, mine);
    compare_against_e22(mine, cteas::p6e::read_calmet_dat21(written),
                        "p6f_writer_synthetic");

    // 2. The E22 writer writes, P6F reads.
    cteas::p6e::CalmetDat21Header e22_header;
    cteas::p6e::CalmetDat21Static e22_static;
    std::vector<cteas::p6e::CalmetDat21Field> e22_hourly;
    e22_fixture(fixture, e22_header, e22_static, e22_hourly);
    const std::string e22_path = temp_path("cteas_p6e_e22_written.dat");
    cteas::p6e::write_calmet_dat21(e22_path, e22_header, e22_static, e22_hourly);
    const cteas::p6f::Calmet21File reread = cteas::p6f::read_calmet_dat21(e22_path);
    assert(reread.hourly.size() == mine.hourly.size());
    assert(reread.header.nx == mine.header.nx && reread.header.nz == mine.header.nz);
    for(std::size_t k = 0; k < reread.hourly.size(); ++k)
        if(reread.hourly[k].integer)
            assert(reread.hourly[k].integer_values == mine.hourly[k].integer_values);
        else
            same_real_values(reread.hourly[k].real_values,
                             mine.hourly[k].real_values, "e22_written");
    std::cout << "P6F_READS_E22_WRITER_PASS field_records="
              << reread.hourly.size() << "\n";
    std::filesystem::remove(written);
    std::filesystem::remove(e22_path);

    // 3. The frozen real reference case, when it is present in the checkout.
    if(argc > 1) {
        const std::string frozen = argv[1];
        const cteas::p6f::Calmet21File parsed = cteas::p6f::read_calmet_dat21(frozen);
        const std::string rewritten = temp_path("cteas_p6f_e22_real_rewritten.dat");
        cteas::p6f::write_calmet_dat21(rewritten, parsed);
        compare_against_e22(parsed, cteas::p6e::read_calmet_dat21(rewritten),
                            "frozen_2022_real_case");
        // The E22 reader must agree on the re-serialised file and on the input.
        const cteas::p6e::CalmetDat21Dataset from_original =
            cteas::p6e::read_calmet_dat21(frozen);
        assert(from_original.intervals == cteas::p6f::interval_count(parsed));
        assert(from_original.hourly.size() == parsed.hourly.size());
        std::filesystem::remove(rewritten);
    }
    std::cout << "P6F_E22_CROSS_READ_TESTS_PASS\n";
    return 0;
}
