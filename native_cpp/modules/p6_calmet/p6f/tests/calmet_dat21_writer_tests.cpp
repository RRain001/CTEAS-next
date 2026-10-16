// P6F CALMET.DAT 2.1 writer unit tests.
//
// Software contract only: explicit field arrays -> legal v2.1 records -> read
// back, plus the fail-closed matrix. The byte-identity proof against the frozen
// real 2022 reference case lives in the module's CTest set (see
// tests/verify_real_reference_roundtrip.py).
#include "cteas/p6f/calmet_dat21_writer.hpp"
#include "cteas/p6f/sha256.hpp"

#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using namespace cteas::p6f;

namespace {

std::string trim(const std::string& text) {
    const auto first = text.find_first_not_of(' ');
    if(first == std::string::npos)return std::string();
    const auto last = text.find_last_not_of(' ');
    return text.substr(first, last - first + 1U);
}

std::string temp_path(const std::string& name) {
    return (std::filesystem::temp_directory_path() / name).string();
}

// A dataset built from explicit arrays; every value is a constant of the
// indices, so it is a software fixture and never a physics result.
Calmet21File make_dataset(int nx, int ny, int nz, int hours, int nssta,
                          int nusta, int npsta, bool with_missing) {
    Calmet21File file;
    Calmet21Header& header = file.header;
    Calmet21Statics& statics = file.statics;
    const std::size_t cells =
        static_cast<std::size_t>(nx) * static_cast<std::size_t>(ny);
    header.nx = nx;
    header.ny = ny;
    header.nz = nz;
    header.dgrid_m = 100.f;
    header.xorigin_m = 510885.f;
    header.yorigin_m = 3531269.f;
    header.timezone = "UTC+0000";
    header.irtype = 1;
    header.iwfcod = 1;
    header.nssta = nssta;
    header.nusta = nusta;
    header.npsta = npsta;
    header.nowsta = 0;
    header.nlu = 14;
    header.iwat1 = 50;
    header.iwat2 = 55;
    header.lcalgrd = true;
    header.irlg = hours;
    header.comments = {"P6F unit fixture", "SYNTHETIC -- not an observation"};
    header.projection.pmap = "UTM";
    header.projection.datum = "WGS-84";
    header.projection.daten = "02-21-2003";
    header.projection.utmhem = "N";
    header.projection.iutmzn = 50;
    const std::int64_t start = days_from_civil(2022, 1U, 1U) * 86400;
    const Calmet21Calendar begin = calendar_from_instant(start);
    const Calmet21Calendar end =
        calendar_from_instant(start + static_cast<std::int64_t>(hours) * 3600);
    header.begin_year = begin.year;
    header.begin_month = begin.month;
    header.begin_day = begin.day;
    header.begin_hour = begin.hour;
    header.begin_second = begin.second;
    header.end_year = end.year;
    header.end_month = end.month;
    header.end_day = end.day;
    header.end_hour = end.hour;
    header.end_second = end.second;
    for(int face = 0; face <= nz; ++face)
        statics.zface_m.push_back(120.f * static_cast<float>(face));
    statics.surface_x_m.assign(static_cast<std::size_t>(nssta), 2500.f);
    statics.surface_y_m.assign(static_cast<std::size_t>(nssta), 2500.f);
    statics.upper_x_m.assign(static_cast<std::size_t>(nusta), 2500.f);
    statics.upper_y_m.assign(static_cast<std::size_t>(nusta), 2600.f);
    statics.precip_x_m.assign(static_cast<std::size_t>(npsta), 2400.f);
    statics.precip_y_m.assign(static_cast<std::size_t>(npsta), 2450.f);
    statics.z0_m.assign(cells, 0.5f);
    statics.elev_m.assign(cells, 25.f);
    statics.xlai.assign(cells, 1.5f);
    statics.ilandu.assign(cells, 12);
    if(nssta >= 1)statics.nears.assign(cells, 1);
    const std::vector<std::string> labels = hourly_labels(nz, 1, true, npsta);
    for(int hour = 0; hour < hours; ++hour) {
        const Calmet21Time begin_time =
            instant_to_time(start + static_cast<std::int64_t>(hour) * 3600);
        Calmet21Time end_time = begin_time;
        end_time.seconds += 3600;
        for(const std::string& label : labels) {
            Calmet21Field field;
            field.label = label;
            field.begin = begin_time;
            field.end = end_time;
            field.integer = is_integer_label(label);
            const std::string name = trim(label);
            if(field.integer) {
                field.integer_values.resize(cells);
                for(std::size_t k = 0; k < cells; ++k)
                    field.integer_values[k] =
                        name == "IPGT" ? 1 + static_cast<std::int32_t>(k % 6)
                                       : 40 + static_cast<std::int32_t>(k % 50);
                if(with_missing && name == "IRH")
                    field.integer_values[0] = missing_integer;
            } else {
                field.real_values.resize(cells);
                for(std::size_t k = 0; k < cells; ++k) {
                    float value = 0.f;
                    if(name.rfind("U-LEV", 0U) == 0U)
                        value = 2.f + 0.01f * static_cast<float>(k % 7);
                    else if(name.rfind("V-LEV", 0U) == 0U)
                        value = 1.f - 0.01f * static_cast<float>(k % 5);
                    else if(name.rfind("WFACE", 0U) == 0U)
                        value = 0.001f * static_cast<float>(k % 3);
                    else if(name.rfind("T-LEV", 0U) == 0U)
                        value = 291.f - 0.0065f * 120.f;
                    else if(name == "USTAR")
                        value = 0.2f;
                    else if(name == "ZI")
                        value = 500.f;
                    else if(name == "EL")
                        value = 50.f;
                    else if(name == "WSTAR")
                        value = 1.f;
                    else if(name == "RMM")
                        value = 0.1f;
                    else if(name == "TEMPK")
                        value = 292.f;
                    else if(name == "RHO")
                        value = 1.2f;
                    else if(name == "QSW")
                        value = 300.f;
                    field.real_values[k] = value;
                }
                if(with_missing && name == "TEMPK")
                    field.real_values[1] = missing_real;
            }
            file.hourly.push_back(std::move(field));
        }
    }
    return file;
}

template <class F> void rejects(F f, const std::string& needle) {
    bool thrown = false;
    try {
        f();
    } catch(const std::invalid_argument& error) {
        thrown = std::string(error.what()).find(needle) != std::string::npos;
        if(!thrown)std::cerr << "wrong message: " << error.what()
                             << " (expected to contain " << needle << ")\n";
    }
    assert(thrown);
}

void same_float(const std::vector<float>& a, const std::vector<float>& b) {
    assert(a.size() == b.size());
    for(std::size_t k = 0; k < a.size(); ++k) {
        assert(std::memcmp(&a[k], &b[k], sizeof(float)) == 0);
    }
}
void same_int(const std::vector<std::int32_t>& a,
              const std::vector<std::int32_t>& b) {
    assert(a == b);
}
void same_time(const Calmet21Time& a, const Calmet21Time& b) {
    assert(a.year == b.year && a.julian_day == b.julian_day &&
           a.hour == b.hour && a.seconds == b.seconds);
}
void same_dataset(const Calmet21File& a, const Calmet21File& b) {
    const Calmet21Header& x = a.header;
    const Calmet21Header& y = b.header;
    // The declaration/comment/projection text fields are written space padded
    // to their original width, so equality is up to that padding.
    assert(trim(x.dataset) == trim(y.dataset) && trim(x.version) == trim(y.version) &&
           trim(x.model) == trim(y.model));
    assert(x.comments.size() == y.comments.size());
    for(std::size_t k = 0; k < x.comments.size(); ++k)
        assert(trim(x.comments[k]) == trim(y.comments[k]));
    assert(x.begin_year == y.begin_year && x.begin_month == y.begin_month &&
           x.begin_day == y.begin_day && x.begin_hour == y.begin_hour &&
           x.begin_second == y.begin_second && x.end_year == y.end_year &&
           x.end_month == y.end_month && x.end_day == y.end_day &&
           x.end_hour == y.end_hour && x.end_second == y.end_second);
    assert(x.timezone == y.timezone && x.irlg == y.irlg && x.irtype == y.irtype &&
           x.iwfcod == y.iwfcod);
    assert(x.nx == y.nx && x.ny == y.ny && x.nz == y.nz);
    assert(x.dgrid_m == y.dgrid_m && x.xorigin_m == y.xorigin_m &&
           x.yorigin_m == y.yorigin_m);
    assert(x.nssta == y.nssta && x.nusta == y.nusta && x.npsta == y.npsta &&
           x.nowsta == y.nowsta && x.nlu == y.nlu && x.iwat1 == y.iwat1 &&
           x.iwat2 == y.iwat2 && x.lcalgrd == y.lcalgrd);
    assert(trim(x.projection.pmap) == trim(y.projection.pmap) &&
           trim(x.projection.datum) == trim(y.projection.datum) &&
           trim(x.projection.daten) == trim(y.projection.daten) &&
           trim(x.projection.utmhem) == trim(y.projection.utmhem) &&
           x.projection.iutmzn == y.projection.iutmzn &&
           x.projection.feast == y.projection.feast &&
           x.projection.fnorth == y.projection.fnorth &&
           x.projection.rnlat0 == y.projection.rnlat0 &&
           x.projection.relon0 == y.projection.relon0 &&
           x.projection.xlat1 == y.projection.xlat1 &&
           x.projection.xlat2 == y.projection.xlat2);
    same_float(a.statics.zface_m, b.statics.zface_m);
    same_float(a.statics.surface_x_m, b.statics.surface_x_m);
    same_float(a.statics.surface_y_m, b.statics.surface_y_m);
    same_float(a.statics.upper_x_m, b.statics.upper_x_m);
    same_float(a.statics.upper_y_m, b.statics.upper_y_m);
    same_float(a.statics.precip_x_m, b.statics.precip_x_m);
    same_float(a.statics.precip_y_m, b.statics.precip_y_m);
    same_float(a.statics.z0_m, b.statics.z0_m);
    same_int(a.statics.ilandu, b.statics.ilandu);
    same_float(a.statics.elev_m, b.statics.elev_m);
    same_float(a.statics.xlai, b.statics.xlai);
    same_int(a.statics.nears, b.statics.nears);
    assert(a.hourly.size() == b.hourly.size());
    for(std::size_t k = 0; k < a.hourly.size(); ++k) {
        assert(trim(a.hourly[k].label) == trim(b.hourly[k].label));
        assert(a.hourly[k].integer == b.hourly[k].integer);
        same_time(a.hourly[k].begin, b.hourly[k].begin);
        same_time(a.hourly[k].end, b.hourly[k].end);
        if(a.hourly[k].integer)
            same_int(a.hourly[k].integer_values, b.hourly[k].integer_values);
        else
            same_float(a.hourly[k].real_values, b.hourly[k].real_values);
    }
}

// Byte offset of the payload of the record whose 8-byte label is `label`.
std::size_t payload_offset(const std::vector<std::uint8_t>& bytes,
                           const std::string& label) {
    std::size_t cursor = 0;
    while(cursor + 8U <= bytes.size()) {
        std::uint32_t length = 0;
        std::memcpy(&length, bytes.data() + cursor, sizeof(length));
        const std::size_t payload = cursor + 4U;
        std::string text;
        for(std::size_t k = 0; k < 8U && payload + k < bytes.size(); ++k)
            text.push_back(static_cast<char>(bytes[payload + k]));
        if(trim(text) == label)return payload;
        cursor = payload + length + 4U;
    }
    assert(false && "label not found");
    return 0;
}

void standard_tests() {
    // Explicit arrays -> records -> read back, per-field equality.
    for(int npsta : {0, 2}) {
        for(int nssta : {0, 1}) {
            const Calmet21File source =
                make_dataset(4, 3, 2, 3, nssta, 1, npsta, true);
            const std::vector<std::uint8_t> bytes =
                serialize_calmet_dat21(source);
            const Calmet21File parsed = parse_calmet_dat21(bytes);
            same_dataset(source, parsed);
            assert(interval_count(parsed) == 3U);
            assert(fields_per_interval(parsed.header) ==
                   static_cast<std::size_t>(npsta == 0 ? 17 : 19));
            // every record is 24 + 4*NX*NY bytes and framed by its length
            std::size_t cursor = 0;
            std::size_t records = 0;
            while(cursor + 8U <= bytes.size()) {
                std::uint32_t length = 0;
                std::memcpy(&length, bytes.data() + cursor, sizeof(length));
                std::uint32_t trailer = 0;
                std::memcpy(&trailer, bytes.data() + cursor + 4U + length,
                            sizeof(trailer));
                assert(trailer == length);
                cursor += 8U + length;
                ++records;
            }
            assert(cursor == bytes.size());
            const std::size_t statics = 7U +
                (npsta != 0 ? 2U : 0U) + (nssta >= 1 ? 3U : 0U);
            assert(records == 3U + source.header.comments.size() + statics +
                                  source.hourly.size());
        }
    }

    // File path API.
    const std::string path = temp_path("cteas_p6f_writer_unit.dat");
    const Calmet21File source = make_dataset(3, 2, 2, 2, 1, 0, 1, false);
    write_calmet_dat21(path, source);
    const Calmet21File reopened = read_calmet_dat21(path);
    same_dataset(source, reopened);
    std::filesystem::remove(path);

    // Sub-hourly start: the declared run clock is (year, month, day, hour) plus
    // seconds inside that hour, exactly as the original writes it.
    {
        Calmet21File offset = make_dataset(3, 2, 1, 2, 0, 0, 0, false);
        const std::int64_t start =
            days_from_civil(2022, 1U, 1U) * 86400 + 1800;
        offset.header.begin_second = 1800;
        offset.header.end_hour = 2;
        offset.header.end_second = 1800;
        const std::size_t per = fields_per_interval(offset.header);
        for(std::size_t index = 0; index < offset.hourly.size(); ++index) {
            Calmet21Time begin = instant_to_time(
                start + static_cast<std::int64_t>(index / per) * 3600);
            Calmet21Time end = begin;
            end.seconds += 3600;
            offset.hourly[index].begin = begin;
            offset.hourly[index].end = end;
        }
        const Calmet21File back =
            parse_calmet_dat21(serialize_calmet_dat21(offset));
        same_dataset(offset, back);
        assert(interval_count(back) == 2U);
        assert(back.header.begin_second == 1800 && back.header.end_second == 1800);
        assert(back.hourly[0].begin.hour == 0 && back.hourly[0].begin.seconds == 1800);
    }

    // IRTYPE=0: the wind-only layout round trips through the same writer.
    {
        Calmet21File winds = make_dataset(3, 2, 1, 2, 0, 0, 0, false);
        const std::vector<std::string> keep =
            hourly_labels(winds.header.nz, 0, winds.header.lcalgrd, 0);
        std::vector<Calmet21Field> filtered;
        for(const Calmet21Field& field : winds.hourly)
            for(const std::string& label : keep)
                if(field.label == label)filtered.push_back(field);
        winds.hourly = std::move(filtered);
        winds.header.irtype = 0;
        const Calmet21File back =
            parse_calmet_dat21(serialize_calmet_dat21(winds));
        same_dataset(winds, back);
        assert(back.header.irtype == 0 && interval_count(back) == 2U);
        assert(fields_per_interval(back.header) == 3U);  // U/V/W of one level
    }

    // The frozen real case stores land-use category 20 with NLU=14: the writer
    // copies the categories verbatim instead of range-rejecting them (the
    // inventory reports how many cells exceed NLU).
    {
        Calmet21File land_use = make_dataset(3, 2, 1, 1, 0, 0, 0, false);
        land_use.header.nlu = 14;
        land_use.statics.ilandu.assign(6U, 20);
        const Calmet21File back =
            parse_calmet_dat21(serialize_calmet_dat21(land_use));
        assert(back.statics.ilandu == land_use.statics.ilandu);
    }

    // XMISS sentinels survive bit-exactly and are counted, not treated as data.
    const Calmet21File missing = make_dataset(4, 3, 2, 2, 1, 1, 0, true);
    const Calmet21File round = parse_calmet_dat21(serialize_calmet_dat21(missing));
    same_dataset(missing, round);
    const std::vector<Calmet21FieldStats> stats = field_inventory(round);
    std::size_t total_missing = 0;
    for(const Calmet21FieldStats& entry : stats) {
        total_missing += entry.missing;
        if(entry.label == "TEMPK") {
            assert(entry.missing == 2U);  // one sentinel in each of 2 records
            assert(entry.defined == entry.values - 2U);
            assert(entry.minimum == 292.0 && entry.maximum == 292.0);
        }
        if(entry.label == "IRH") {
            assert(entry.missing == 2U);
            assert(entry.defined == entry.values - 2U);
        }
        assert(entry.records == 2U);
        assert(!entry.unit.empty() && entry.unit != "unknown");
    }
    assert(total_missing == 4U);
}

void layout_tests() {
    // The exact OUTHR order verified against the frozen real reference case.
    const std::vector<std::string> labels = hourly_labels(2, 1, true, 0);
    const std::vector<std::string> expected = {
        "U-LEV  1", "V-LEV  1", "WFACE  1", "U-LEV  2", "V-LEV  2", "WFACE  2",
        "T-LEV  1", "T-LEV  2", "IPGT    ", "USTAR   ", "ZI      ", "EL      ",
        "WSTAR   ", "TEMPK   ", "RHO     ", "QSW     ", "IRH     "};
    assert(labels == expected);
    const std::vector<std::string> with_precip = hourly_labels(2, 1, true, 3);
    assert(with_precip.size() == expected.size() + 2U);
    assert(with_precip[13] == "RMM     ");
    assert(with_precip.back() == "IPCODE  ");
    // LCALGRD suppresses W and the 3-D temperature block.
    const std::vector<std::string> no_lcalgrd = hourly_labels(2, 1, false, 0);
    assert(no_lcalgrd.size() == 4U + 9U);
    assert(no_lcalgrd[0] == "U-LEV  1" && no_lcalgrd[1] == "V-LEV  1" &&
           no_lcalgrd[2] == "U-LEV  2");
    // IRTYPE=0 writes the wind block only (OUTHR returns right after it).
    const std::vector<std::string> wind_only = hourly_labels(2, 0, true, 0);
    const std::vector<std::string> wind_expected = {
        "U-LEV  1", "V-LEV  1", "WFACE  1", "U-LEV  2", "V-LEV  2", "WFACE  2"};
    assert(wind_only == wind_expected);
    const std::vector<std::string> wind_only_no_w = hourly_labels(2, 0, false, 0);
    assert(wind_only_no_w.size() == 4U && wind_only_no_w[0] == "U-LEV  1" &&
           wind_only_no_w[2] == "U-LEV  2");
    assert(is_integer_label("IPGT    ") && is_integer_label("IRH     "));
    assert(!is_integer_label("U-LEV  1") && !is_integer_label("TEMPK   "));
    // Declared units and masks are explicit for every field of the mode.
    const std::vector<Calmet21FieldSpec> specs = hourly_field_specs(2, 1, true, 0);
    assert(specs.size() == expected.size());
    assert(specs[0].unit == "m/s" && specs[6].unit == "K" &&
           specs[10].unit == "m" && specs[13].unit == "K");
    assert(specs[8].integer && specs[16].integer);
    assert(specs[2].written_when == "LCALGRD");
    const std::vector<Calmet21FieldSpec> statics =
        static_field_specs(50, 50, 9, 1, 1, 0);
    assert(statics.size() == 10U && statics[0].label == "ZFACE" &&
           statics.back().label == "NEARS");
    assert(static_field_specs(50, 50, 9, 0, 0, 0).size() == 5U);
}

void calendar_tests() {
    std::int64_t instant = 0;
    for(int year = 1600; year <= 2400; ++year) {
        int day_of_year = 0;
        for(int month = 1; month <= 12; ++month) {
            const int limit = month == 2 ? (is_leap_year(year) ? 29 : 28)
                              : (month == 4 || month == 6 || month == 9 ||
                                 month == 11)
                                  ? 30
                                  : 31;
            for(int day = 1; day <= limit; ++day) {
                ++day_of_year;
                const std::int64_t days =
                    days_from_civil(year, static_cast<unsigned>(month),
                                    static_cast<unsigned>(day));
                const Calmet21Time time = civil_from_days(days);
                assert(time.year == year && time.julian_day == day_of_year &&
                       time.hour == 0 && time.seconds == 0);
                const Calmet21Calendar calendar =
                    calendar_from_instant(days * 86400);
                assert(calendar.year == year && calendar.month == month &&
                       calendar.day == day);
                const std::string iso = iso8601_utc(days * 86400);
                const auto two = [](int v) {
                    const std::string text = std::to_string(v);
                    return std::string(2U - text.size(), '0') + text;
                };
                const std::string prefix =
                    std::to_string(year) + "-" + two(month) + "-" + two(day) +
                    "T00:00:00Z";
                assert(iso == prefix);
                assert(instant_seconds(instant_to_time(days * 86400)) ==
                       days * 86400);
            }
        }
    }
    assert(iso8601_utc(0) == "1970-01-01T00:00:00Z");
    assert(iso8601_utc(instant) == "1970-01-01T00:00:00Z");
    assert(iso8601_utc(days_from_civil(2022, 1U, 6U) * 86400 + 23 * 3600) ==
           "2022-01-06T23:00:00Z");
    const Calmet21Time hour = instant_to_time(days_from_civil(2022, 1U, 1U) * 86400);
    assert(pack_time(hour) == 202200100 && hour.seconds == 0);
    Calmet21Time next = hour;
    for(int k = 0; k < 143; ++k)next = next_hour(next);
    assert(next.year == 2022 && next.julian_day == 6 && next.hour == 23);
    rejects([] { (void)pack_time(Calmet21Time{2022, 0, 0, 0}); },
            "invalid day of year");
    rejects([] { (void)unpack_time(0, 0); }, "invalid year");
}

void fail_closed_tests() {
    const Calmet21File good = make_dataset(4, 3, 2, 3, 1, 1, 0, false);
    const auto broken = [&good](auto mutate, const std::string& needle) {
        Calmet21File copy = good;
        mutate(copy);
        rejects([&copy] { (void)serialize_calmet_dat21(copy); }, needle);
    };
    // A dataset whose field set does not match its declared mode must fail
    // closed: this IRTYPE=1 dataset carries the 2-D meteorological fields that
    // IRTYPE=0 does not write.
    broken([](Calmet21File& f) { f.header.irtype = 0; },
           "does not contain complete intervals");
    broken([](Calmet21File& f) { f.header.iwfcod = 0; }, "IWFCOD must be 1");
    broken([](Calmet21File& f) { f.header.nz = 0; }, "grid extent NZ");
    broken([](Calmet21File& f) { f.header.ny = 0; }, "grid extent NX/NY");
    broken([](Calmet21File& f) { f.header.dgrid_m = 0.f; }, "DGRID");
    broken([](Calmet21File& f) { f.header.dgrid_m = NAN; }, "DGRID");
    broken([](Calmet21File& f) { f.header.xorigin_m = INFINITY; }, "origin");
    broken([](Calmet21File& f) { f.header.timezone = "UTC+000"; }, "AXTZ");
    broken([](Calmet21File& f) { f.header.nssta = -1; }, "station counts");
    broken([](Calmet21File& f) { f.header.npsta = -1; }, "station counts");
    broken([](Calmet21File& f) { f.header.npsta = -1; }, "MM5 precipitation");
    broken([](Calmet21File& f) { f.header.iwat1 = 60; }, "IWAT1");
    broken([](Calmet21File& f) { f.header.irtype = 2; },
           "IRTYPE must be 0 (winds only) or 1");
    broken([](Calmet21File& f) { f.statics.ilandu[0] = -1; },
           "negative land-use category");
    broken([](Calmet21File& f) { f.header.dataset = "NOTMET.DAT"; },
           "declaration dataset");
    broken([](Calmet21File& f) { f.header.version = "2.0"; },
           "declaration version");
    broken([](Calmet21File& f) { f.header.projection.pmap = "UTM-EXTRA"; },
           "PMAP is longer");
    broken([](Calmet21File& f) { f.header.projection.utmhem = "NORTH"; },
           "UTMHEM is longer");
    broken([](Calmet21File& f) { f.header.projection.feast = NAN; },
           "map projection constants");
    broken([](Calmet21File& f) { f.header.comments.push_back(std::string(133U, 'x')); },
           "comment record is longer");
    broken([](Calmet21File& f) { f.statics.zface_m.pop_back(); },
           "ZFACE must have NZ+1");
    broken([](Calmet21File& f) { f.statics.zface_m[1] = f.statics.zface_m[0]; },
           "ZFACE must increase");
    broken([](Calmet21File& f) { f.statics.zface_m[1] = NAN; },
           "non-finite value in ZFACE");
    broken([](Calmet21File& f) { f.statics.surface_x_m.pop_back(); },
           "surface station coordinate counts");
    broken([](Calmet21File& f) { f.statics.upper_y_m.pop_back(); },
           "upper-air station coordinate counts");
    broken([](Calmet21File& f) { f.statics.z0_m.pop_back(); }, "Z0 must have");
    broken([](Calmet21File& f) { f.statics.elev_m.pop_back(); }, "ELEV must have");
    broken([](Calmet21File& f) { f.statics.xlai.pop_back(); }, "XLAI must have");
    broken([](Calmet21File& f) { f.statics.ilandu.pop_back(); },
           "ILANDU must have");
    broken([](Calmet21File& f) { f.statics.nears.clear(); },
           "NEARS must have NX*NY");
    broken([](Calmet21File& f) {
        Calmet21File other = make_dataset(4, 3, 2, 1, 0, 0, 0, false);
        f = other;
        f.statics.nears.assign(12U, 1);
    }, "NEARS must not be supplied when NSSTA<1");
    broken([](Calmet21File& f) { f.header.irlg = 2; }, "IRLG must equal");
    broken([](Calmet21File& f) { f.hourly.pop_back(); }, "complete intervals");
    broken([](Calmet21File& f) {
        std::swap(f.hourly[0].label, f.hourly[1].label);
    }, "hourly field order mismatch");
    broken([](Calmet21File& f) { f.hourly[1].real_values.pop_back(); },
           "must have NX*NY real values");
    broken([](Calmet21File& f) {
        f.hourly[16].real_values.assign(12U, 1.f);  // IRH stays integer
    }, "must not carry real values as well");
    broken([](Calmet21File& f) {
        Calmet21Field& field = f.hourly[16];  // IRH, integer
        field.real_values.assign(12U, 1.f);
        field.integer_values.clear();
        field.integer = false;
    }, "must be stored as the integer/real kind");
    broken([](Calmet21File& f) {
        f.hourly[13].integer_values.assign(12U, 1);  // TEMPK
    }, "must not carry integer values as well");
    broken([](Calmet21File& f) { f.hourly[13].real_values.pop_back(); },
           "must have NX*NY real values");
    broken([](Calmet21File& f) { f.hourly[13].real_values[0] = INFINITY; },
           "non-finite value in TEMPK");
    broken([](Calmet21File& f) { f.hourly[0].label = "ZICONV  "; },
           "internal CALMET state");
    broken([](Calmet21File& f) { f.hourly[13].label = "RMM     "; },
           "cannot appear when NPSTA=0");
    broken([](Calmet21File& f) { f.hourly[0].end.seconds = 3599; },
           "exactly 3600 s");
    broken([](Calmet21File& f) {
        // 3600 s of elapsed time, but not the packed clock the original writes
        ++f.hourly[0].end.hour;
        f.hourly[0].end.seconds = f.hourly[0].begin.seconds;
    }, "same packed hour");
    broken([](Calmet21File& f) {
        for(std::size_t slot = 17U; slot < 34U; ++slot) {
            f.hourly[slot].begin.hour += 1;
            f.hourly[slot].end.hour += 1;
        }
    }, "must be contiguous");
    broken([](Calmet21File& f) { f.hourly[0].begin.julian_day = 0; },
           "invalid day of year");
    broken([](Calmet21File& f) { f.hourly[0].end.seconds = 90000; },
           "invalid second");
    broken([](Calmet21File& f) { f.header.end_day = 5; },
           "declared run end clock");
    broken([](Calmet21File& f) { f.header.begin_hour = 1; },
           "declared run begin clock");
    // NPSTA=1 without the matching station coordinates.
    {
        Calmet21File copy = make_dataset(4, 3, 2, 1, 1, 1, 1, false);
        copy.statics.precip_x_m.clear();
        rejects([&copy] { (void)serialize_calmet_dat21(copy); },
                "precipitation station coordinate counts");
    }
    // A label that the mode does not contain at all.
    {
        Calmet21File copy = good;
        copy.hourly[0].label = "XPSTA   ";
        rejects([&copy] { (void)serialize_calmet_dat21(copy); },
                "hourly field order mismatch");
    }

    // Structural failures of a byte image.
    const std::vector<std::uint8_t> bytes =
        serialize_calmet_dat21(make_dataset(3, 2, 2, 2, 1, 1, 0, false));
    {
        std::vector<std::uint8_t> cut = bytes;
        cut.resize(cut.size() - 1U);
        rejects([&cut] { (void)parse_calmet_dat21(cut); }, "record length exceeds");
    }
    {
        std::vector<std::uint8_t> cut = bytes;
        cut.resize(40U);
        rejects([&cut] { (void)parse_calmet_dat21(cut); },
                "record length exceeds");
    }
    {
        std::vector<std::uint8_t> damaged = bytes;
        damaged[4U + 96U] = 7U;  // corrupt the first record trailer
        rejects([&damaged] { (void)parse_calmet_dat21(damaged); },
                "markers disagree");
    }
    {
        std::vector<std::uint8_t> damaged = bytes;
        const std::uint32_t absurd = 0x7fffffffU;
        std::memcpy(damaged.data(), &absurd, sizeof(absurd));
        rejects([&damaged] { (void)parse_calmet_dat21(damaged); },
                "record length exceeds");
    }
    {
        std::vector<std::uint8_t> damaged = bytes;
        const std::size_t payload = payload_offset(damaged, "ZFACE");
        damaged[payload + 8U] = 1U;  // static clock must stay zero
        rejects([&damaged] { (void)parse_calmet_dat21(damaged); },
                "zero clock words");
    }
    {
        std::vector<std::uint8_t> damaged = bytes;
        const std::size_t payload = payload_offset(damaged, "T-LEV  1");
        damaged[payload + 1U] = 0U;  // break the label
        rejects([&damaged] { (void)parse_calmet_dat21(damaged); },
                "hourly field order mismatch");
    }
    {
        std::vector<std::uint8_t> damaged = bytes;
        damaged[4U + 8U] = static_cast<std::uint8_t>('X');  // dataset name
        rejects([&damaged] { (void)parse_calmet_dat21(damaged); },
                "unsupported CALMET.DAT signature");
    }
    {
        rejects([] { (void)read_calmet_dat21("/nonexistent/p6f/met.dat"); },
                "cannot open");
    }
}

void digest_tests() {
    assert(sha256_hex({}) ==
           "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    assert(sha256_hex({97U, 98U, 99U}) ==
           "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    assert(sha256_hex({97U, 98U, 99U, 100U, 101U, 102U, 103U, 104U}) ==
           "9c56cc51b374c3ba189210d5b6d4bf57790d351c96c47c02190ecf1e430635ab");
    std::vector<std::uint8_t> million(1000000U, 97U);
    assert(sha256_hex(million) ==
           "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
}

}  // namespace

int main() {
    standard_tests();
    layout_tests();
    calendar_tests();
    fail_closed_tests();
    digest_tests();
    std::cout << "P6F_WRITER_UNIT_TESTS_PASS\n";
    return 0;
}
