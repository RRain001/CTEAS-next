// ---------------------------------------------------------------------------
// CTEAS P6F -- CALMET.DAT 2.1 writer CLI.
//
//   roundtrip --file FILE [--out FILE] [--expect-sha256 HEX] [--report JSON]
//        Parses FILE with the writer's own fail-closed reader, re-serialises
//        the parsed dataset from its explicit field arrays and compares the
//        result with the input byte for byte. This is the module's ground
//        truth: on the frozen 2022 reference met.dat the two images are
//        identical and both hash to
//        b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30.
//        Exit 0 = identical, 1 = different or structurally invalid.
//
//   check --file FILE [--report JSON]
//        Parses and validates FILE, then reports the declaration, the run
//        controls, the static record inventory and the per-field hourly
//        inventory (denominator, XMISS count, min/max/mean over the defined
//        cells) with the declared SI unit and the OUTHR mask condition of
//        every field. A layout verdict is NOT a statement about the physical
//        correctness of the values.
//
//   emit-fixture --out FILE [--hours N] [--nx N --ny N --nz N]
//                [--nssta N --nusta N --npsta N]
//                [--start YYYY-MM-DDTHH:MM[:SS]] [--with-missing]
//        Writes a deterministic SYNTHETIC layout fixture from explicit field
//        arrays. Every value is a constant expression of the grid index: the
//        fixture exists to exercise the writer and is never evidence about
//        reconstructed meteorology. The file comments say so.
// ---------------------------------------------------------------------------
#include "cteas/p6f/calmet_dat21_writer.hpp"
#include "cteas/p6f/p6d_fields.hpp"
#include "cteas/p6f/sha256.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using cteas::p6f::Calmet21Field;
using cteas::p6f::Calmet21File;
using cteas::p6f::Calmet21Statics;
using cteas::p6f::Calmet21Time;

constexpr const char* kTool = "cteas_p6f_calmet_dat21_writer";

void require_argument(bool condition, const std::string& message) {
    if(!condition)throw std::runtime_error(message);
}

std::vector<std::uint8_t> read_bytes(const std::string& path) {
    std::ifstream input(path, std::ios::binary);
    if(!input)throw std::runtime_error("cannot open " + path);
    return std::vector<std::uint8_t>((std::istreambuf_iterator<char>(input)),
                                     std::istreambuf_iterator<char>());
}

void write_bytes(const std::string& path,
                 const std::vector<std::uint8_t>& bytes) {
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if(!output)throw std::runtime_error("cannot create " + path);
    output.write(reinterpret_cast<const char*>(bytes.data()),
                 static_cast<std::streamsize>(bytes.size()));
    output.close();
    if(!output)throw std::runtime_error("short write to " + path);
}

std::string trim_text(const std::string& text) {
    const auto first = text.find_first_not_of(' ');
    if(first == std::string::npos)return std::string();
    const auto last = text.find_last_not_of(' ');
    return text.substr(first, last - first + 1U);
}

std::string json_string(const std::string& text) {
    std::string out = "\"";
    for(const char c : text) {
        if(c == '"' || c == '\\')out.push_back('\\');
        out.push_back(c);
    }
    out.push_back('"');
    return out;
}
std::string json_number(double value) {
    if(!std::isfinite(value))return "null";
    char buffer[64];
    std::snprintf(buffer, sizeof(buffer), "%.17g", value);
    return buffer;
}
std::string json_bool(bool value) { return value ? "true" : "false"; }

// The record that owns a byte offset, for a readable mismatch report.
std::string describe_offset(const std::vector<std::uint8_t>& bytes,
                            std::size_t offset) {
    std::size_t cursor = 0;
    std::size_t index = 0;
    while(cursor + 8U <= bytes.size()) {
        const std::uint32_t length =
            std::uint32_t(bytes[cursor]) |
            (std::uint32_t(bytes[cursor + 1U]) << 8U) |
            (std::uint32_t(bytes[cursor + 2U]) << 16U) |
            (std::uint32_t(bytes[cursor + 3U]) << 24U);
        const std::size_t payload = cursor + 4U;
        if(offset < payload + length + 4U) {
            std::string label = "record " + std::to_string(index);
            if(length >= 8U && payload + 8U <= bytes.size()) {
                std::string text;
                for(std::size_t k = 0; k < 8U; ++k)
                    text.push_back(static_cast<char>(bytes[payload + k]));
                const auto first = text.find_first_not_of(' ');
                if(first != std::string::npos)
                    label += " label=" + json_string(text);
            }
            label += " offset_in_record=" +
                     std::to_string(offset > payload ? offset - payload : 0U);
            return label;
        }
        cursor = payload + length + 4U;
        ++index;
    }
    return "offset " + std::to_string(offset) + " is outside the record walk";
}

// ------------------------------------------------------------ iso-8601 input
std::int64_t parse_iso_instant(const std::string& text) {
    const auto digits = [&text](std::size_t at, std::size_t count) {
        if(at + count > text.size())
            throw std::runtime_error("malformed --start value: " + text);
        int value = 0;
        for(std::size_t k = 0; k < count; ++k) {
            const char c = text[at + k];
            if(c < '0' || c > '9')
                throw std::runtime_error("malformed --start value: " + text);
            value = value * 10 + (c - '0');
        }
        return value;
    };
    if(text.size() < 16U || text[4] != '-' || text[7] != '-' ||
       text[10] != 'T' || text[13] != ':')
        throw std::runtime_error(
            "--start must look like YYYY-MM-DDTHH:MM[:SS]");
    const int year = digits(0U, 4U);
    const int month = digits(5U, 2U);
    const int day = digits(8U, 2U);
    const int hour = digits(11U, 2U);
    const int minute = digits(14U, 2U);
    int second = 0;
    if(text.size() > 16U) {
        if(text[16] != ':')
            throw std::runtime_error("malformed --start value: " + text);
        second = digits(17U, 2U);
    }
    if(second > 59)throw std::runtime_error("--start seconds must be 0..59");
    const std::int64_t instant =
        cteas::p6f::days_from_civil(year, static_cast<unsigned>(month),
                                    static_cast<unsigned>(day)) *
            86400 +
        static_cast<std::int64_t>(hour) * 3600 + minute * 60 + second;
    // Reject a rolled-over date (month 13, February 30, ...) instead of
    // silently writing a different calendar day than the caller asked for.
    const cteas::p6f::Calmet21Calendar back =
        cteas::p6f::calendar_from_instant(instant);
    if(back.year != year || back.month != month || back.day != day ||
       back.hour != hour || back.minute != minute || back.second != second)
        throw std::runtime_error("--start is not a real calendar date/time: " +
                                 text);
    return instant;
}

// --------------------------------------------------------------- fixture data
// Deterministic, explicitly synthetic field arrays. Nothing here is a physics
// result: each value is a constant expression of the cell/level indices.
std::size_t cell_index(int i, int j, int nx) {
    return static_cast<std::size_t>(j) * static_cast<std::size_t>(nx) +
           static_cast<std::size_t>(i);
}
bool is_water(int i, int j) { return (i + 2 * j) % 23 == 0; }
int land_use(int i, int j) { return is_water(i, j) ? 55 : 12; }
float roughness(int i, int j) { return is_water(i, j) ? 0.0002f : 0.5f; }

Calmet21File build_fixture(int nx, int ny, int nz, int hours, int nssta,
                           int nusta, int npsta, std::int64_t start_instant,
                           bool with_missing) {
    Calmet21File file;
    cteas::p6f::Calmet21Header& header = file.header;
    Calmet21Statics& statics = file.statics;
    const std::size_t cells =
        static_cast<std::size_t>(nx) * static_cast<std::size_t>(ny);

    header.dataset = "CALMET.DAT";
    header.version = "2.1";
    header.model = "No-Obs file structure with embedded control file";
    header.comments = {
        "P6F SYNTHETIC layout fixture -- writer test only",
        "every value is a constant expression of the grid index",
        "NOT a reconstructed or observed meteorological result",
        "generated by cteas_p6f_calmet_dat21_writer emit-fixture"};
    const cteas::p6f::Calmet21Calendar begin =
        cteas::p6f::calendar_from_instant(start_instant);
    const cteas::p6f::Calmet21Calendar end =
        cteas::p6f::calendar_from_instant(
            start_instant + static_cast<std::int64_t>(hours) * 3600);
    // The OUTHD clock words are (year, month, day, hour) plus seconds inside
    // that hour, so a sub-hourly start such as 00:30 is hour 0 + 1800 s.
    header.begin_year = begin.year;
    header.begin_month = begin.month;
    header.begin_day = begin.day;
    header.begin_hour = begin.hour;
    header.begin_second = begin.minute * 60 + begin.second;
    header.end_year = end.year;
    header.end_month = end.month;
    header.end_day = end.day;
    header.end_hour = end.hour;
    header.end_second = end.minute * 60 + end.second;
    header.timezone = "UTC+0000";
    header.irlg = hours;
    header.irtype = 1;
    header.nx = nx;
    header.ny = ny;
    header.nz = nz;
    header.dgrid_m = 100.f;
    header.xorigin_m = 510885.f;
    header.yorigin_m = 3531269.f;
    header.iwfcod = 1;
    header.nssta = nssta;
    header.nusta = nusta;
    header.npsta = npsta;
    header.nowsta = 0;
    header.nlu = 14;
    header.iwat1 = 50;
    header.iwat2 = 55;
    header.lcalgrd = true;
    header.projection.pmap = "UTM";
    header.projection.datum = "WGS-84";
    header.projection.daten = "02-21-2003";
    header.projection.feast = 0.f;
    header.projection.fnorth = 0.f;
    header.projection.utmhem = "N";
    header.projection.iutmzn = 50;
    header.projection.rnlat0 = 0.f;
    header.projection.relon0 = 0.f;
    header.projection.xlat1 = 0.f;
    header.projection.xlat2 = 0.f;

    for(int face = 0; face <= nz; ++face)
        statics.zface_m.push_back(
            120.f * static_cast<float>(face) + 10.f * static_cast<float>(face % 3));
    statics.surface_x_m.assign(static_cast<std::size_t>(nssta), 2500.f);
    statics.surface_y_m.assign(static_cast<std::size_t>(nssta), 2500.f);
    statics.upper_x_m.assign(static_cast<std::size_t>(nusta), 2500.f);
    statics.upper_y_m.assign(static_cast<std::size_t>(nusta), 2600.f);
    statics.precip_x_m.assign(static_cast<std::size_t>(npsta), 2400.f);
    statics.precip_y_m.assign(static_cast<std::size_t>(npsta), 2450.f);
    statics.z0_m.resize(cells);
    statics.elev_m.resize(cells);
    statics.xlai.resize(cells);
    statics.ilandu.resize(cells);
    for(int j = 0; j < ny; ++j)
        for(int i = 0; i < nx; ++i) {
            const std::size_t k = cell_index(i, j, nx);
            statics.z0_m[k] = roughness(i, j);
            statics.elev_m[k] = 20.f + static_cast<float>((i * 7 + j * 3) % 40);
            statics.xlai[k] = is_water(i, j) ? 0.f : 1.5f;
            statics.ilandu[k] = land_use(i, j);
        }
    if(nssta >= 1)statics.nears.assign(cells, 1);

    const std::vector<std::string> labels = cteas::p6f::hourly_labels(
        nz, header.irtype, header.lcalgrd, npsta);
    for(int hour = 0; hour < hours; ++hour) {
        const std::int64_t begin_instant =
            start_instant + static_cast<std::int64_t>(hour) * 3600;
        const Calmet21Time begin_time = cteas::p6f::instant_to_time(begin_instant);
        Calmet21Time end_time = begin_time;
        end_time.seconds += 3600;
        for(const std::string& label : labels) {
            const std::string name = label.substr(0U, 5U);
            Calmet21Field field;
            field.label = label;
            field.begin = begin_time;
            field.end = end_time;
            field.integer = cteas::p6f::is_integer_label(label);
            if(field.integer) {
                field.integer_values.resize(cells);
                for(std::size_t k = 0; k < cells; ++k) {
                    const int i = static_cast<int>(k % static_cast<std::size_t>(nx));
                    const int j = static_cast<int>(k / static_cast<std::size_t>(nx));
                    const int base = label.rfind("IPGT", 0U) == 0U
                                         ? 1 + (i + j) % 6
                                         : 40 + (i + 3 * j) % 50;
                    field.integer_values[k] =
                        (with_missing && k % 97U == 0U)
                            ? cteas::p6f::missing_integer
                            : base;
                }
            } else {
                field.real_values.resize(cells);
                for(std::size_t k = 0; k < cells; ++k) {
                    const int i = static_cast<int>(k % static_cast<std::size_t>(nx));
                    const int j = static_cast<int>(k / static_cast<std::size_t>(nx));
                    float value = 0.f;
                    if(name == "U-LEV") {
                        const int level = std::atoi(label.substr(5U).c_str());
                        value = 2.f + 0.1f * static_cast<float>(level) +
                                0.01f * static_cast<float>((i + j) % 7);
                    } else if(name == "V-LEV") {
                        const int level = std::atoi(label.substr(5U).c_str());
                        value = 1.f - 0.05f * static_cast<float>(level);
                    } else if(name == "WFACE") {
                        value = 0.001f * static_cast<float>((i + j) % 5);
                    } else if(name == "T-LEV") {
                        const int level = std::atoi(label.substr(5U).c_str());
                        value = 291.f -
                                0.0065f *
                                    statics.zface_m[static_cast<std::size_t>(level)];
                    } else if(label.rfind("USTAR", 0U) == 0U) {
                        value = 0.15f + 0.01f * static_cast<float>(hour % 5);
                    } else if(label.rfind("ZI", 0U) == 0U) {
                        value = 500.f + 20.f * static_cast<float>(i % 10);
                    } else if(label.rfind("EL", 0U) == 0U) {
                        value = 50.f;
                    } else if(label.rfind("WSTAR", 0U) == 0U) {
                        value = 1.f;
                    } else if(label.rfind("TEMPK", 0U) == 0U) {
                        value = 292.f;
                    } else if(label.rfind("RHO", 0U) == 0U) {
                        value = 1.2f;
                    } else if(label.rfind("QSW", 0U) == 0U) {
                        value = 300.f;
                    } else if(label.rfind("RMM", 0U) == 0U) {
                        value = 0.1f;
                    }
                    if(with_missing && k % 97U == 0U)
                        value = cteas::p6f::missing_real;
                    field.real_values[k] = value;
                }
            }
            file.hourly.push_back(std::move(field));
        }
    }
    return file;
}

// ------------------------------------------------------------------ reports
std::string check_report(const std::string& path,
                         const std::vector<std::uint8_t>& bytes,
                         const Calmet21File& file) {
    const cteas::p6f::Calmet21Header& header = file.header;
    const Calmet21Statics& statics = file.statics;
    const std::size_t cells =
        static_cast<std::size_t>(header.nx) * static_cast<std::size_t>(header.ny);
    std::string out;
    out += "{\n";
    out += "  \"tool\": " + json_string(kTool) + ",\n";
    out += "  \"command\": \"check\",\n";
    out += "  \"file\": " + json_string(path) + ",\n";
    out += "  \"file_bytes\": " + std::to_string(bytes.size()) + ",\n";
    out += "  \"file_sha256\": " + json_string(cteas::p6f::sha256_hex(bytes)) +
           ",\n";
    out += "  \"declaration\": {\"dataset\": " + json_string(header.dataset) +
           ", \"version\": " + json_string(header.version) + ", \"model\": " +
           json_string(header.model) + "},\n";
    out += "  \"comments\": " + std::to_string(header.comments.size()) + ",\n";
    out += "  \"controls\": {\n";
    out += "    \"begin_year\": " + std::to_string(header.begin_year) +
           ", \"begin_month\": " + std::to_string(header.begin_month) +
           ", \"begin_day\": " + std::to_string(header.begin_day) +
           ", \"begin_hour\": " + std::to_string(header.begin_hour) +
           ", \"begin_second\": " + std::to_string(header.begin_second) + ",\n";
    out += "    \"end_year\": " + std::to_string(header.end_year) +
           ", \"end_month\": " + std::to_string(header.end_month) +
           ", \"end_day\": " + std::to_string(header.end_day) +
           ", \"end_hour\": " + std::to_string(header.end_hour) +
           ", \"end_second\": " + std::to_string(header.end_second) + ",\n";
    out += "    \"timezone\": " + json_string(header.timezone) +
           ", \"irlg\": " + std::to_string(header.irlg) +
           ", \"irtype\": " + std::to_string(header.irtype) +
           ", \"iwfcod\": " + std::to_string(header.iwfcod) + ",\n";
    out += "    \"nx\": " + std::to_string(header.nx) +
           ", \"ny\": " + std::to_string(header.ny) +
           ", \"nz\": " + std::to_string(header.nz) +
           ", \"cells\": " + std::to_string(cells) + ",\n";
    out += "    \"dgrid_m\": " + json_number(header.dgrid_m) +
           ", \"xorigin_m\": " + json_number(header.xorigin_m) +
           ", \"yorigin_m\": " + json_number(header.yorigin_m) + ",\n";
    out += "    \"nssta\": " + std::to_string(header.nssta) +
           ", \"nusta\": " + std::to_string(header.nusta) +
           ", \"npsta\": " + std::to_string(header.npsta) +
           ", \"nowsta\": " + std::to_string(header.nowsta) +
           ", \"nlu\": " + std::to_string(header.nlu) +
           ", \"iwat1\": " + std::to_string(header.iwat1) +
           ", \"iwat2\": " + std::to_string(header.iwat2) +
           ", \"lcalgrd\": " + json_bool(header.lcalgrd) + ",\n";
    out += "    \"pmap\": " + json_string(header.projection.pmap) +
           ", \"datum\": " + json_string(header.projection.datum) +
           ", \"daten\": " + json_string(header.projection.daten) + ",\n";
    out += "    \"feast\": " + json_number(header.projection.feast) +
           ", \"fnorth\": " + json_number(header.projection.fnorth) +
           ", \"utmhem\": " + json_string(header.projection.utmhem) +
           ", \"iutmzn\": " + std::to_string(header.projection.iutmzn) +
           ", \"rnlat0\": " + json_number(header.projection.rnlat0) +
           ", \"relon0\": " + json_number(header.projection.relon0) +
           ", \"xlat1\": " + json_number(header.projection.xlat1) +
           ", \"xlat2\": " + json_number(header.projection.xlat2) + "\n";
    out += "  },\n";
    // The original copies the land-use categories it read; NLU is not an upper
    // bound of them in the no-observation case (the frozen reference case itself
    // stores category 20 with NLU=14), so the categories are reported instead of
    // being range-rejected.
    std::size_t ilandu_over_nlu = 0, ilandu_negative = 0;
    std::int32_t ilandu_max = 0;
    for(const std::int32_t category : statics.ilandu) {
        if(category > header.nlu)++ilandu_over_nlu;
        if(category < 0)++ilandu_negative;
        ilandu_max = std::max(ilandu_max, category);
    }
    out += "  \"statics\": {\"zface_faces\": " +
           std::to_string(statics.zface_m.size()) +
           ", \"zface_min_m\": " +
           json_number(statics.zface_m.empty()
                           ? std::numeric_limits<double>::quiet_NaN()
                           : static_cast<double>(statics.zface_m.front())) +
           ", \"zface_max_m\": " +
           json_number(statics.zface_m.empty()
                           ? std::numeric_limits<double>::quiet_NaN()
                           : static_cast<double>(statics.zface_m.back())) +
           ", \"surface_stations\": " + std::to_string(statics.surface_x_m.size()) +
           ", \"upper_stations\": " + std::to_string(statics.upper_x_m.size()) +
           ", \"precip_stations\": " + std::to_string(statics.precip_x_m.size()) +
           ", \"grid_cells\": " + std::to_string(cells) +
           ", \"nlu\": " + std::to_string(header.nlu) +
           ", \"ilandu_max\": " + std::to_string(ilandu_max) +
           ", \"ilandu_over_nlu_cells\": " + std::to_string(ilandu_over_nlu) +
           ", \"ilandu_negative_cells\": " + std::to_string(ilandu_negative) +
           ", \"ilandu_note\": " +
           json_string("ILANDU is written verbatim; NLU is not an upper bound in "
                       "the no-observation case") +
           "},\n";
    const std::size_t intervals = cteas::p6f::interval_count(file);
    out += "  \"hourly\": {\"intervals\": " + std::to_string(intervals) +
           ", \"fields_per_interval\": " +
           std::to_string(cteas::p6f::fields_per_interval(header)) +
           ", \"field_records\": " + std::to_string(file.hourly.size()) + ",\n";
    out += "    \"first_begin\": " +
           json_string(file.hourly.empty()
                           ? std::string("null")
                           : cteas::p6f::iso8601_utc(
                                 cteas::p6f::instant_seconds(
                                     file.hourly.front().begin))) +
           ", \"last_end\": " +
           json_string(file.hourly.empty()
                           ? std::string("null")
                           : cteas::p6f::iso8601_utc(
                                 cteas::p6f::instant_seconds(
                                     file.hourly.back().end))) +
           ", \"seconds_per_interval\": 3600, \"contiguous\": " +
           json_bool(intervals > 1U) + "},\n";
    out += "  \"fields\": [\n";
    const std::vector<cteas::p6f::Calmet21FieldStats> stats =
        cteas::p6f::field_inventory(file);
    for(std::size_t k = 0; k < stats.size(); ++k) {
        const cteas::p6f::Calmet21FieldStats& entry = stats[k];
        out += "    {\"label\": " + json_string(entry.label) +
               ", \"unit\": " + json_string(entry.unit) +
               ", \"integer\": " + json_bool(entry.integer) +
               ", \"records\": " + std::to_string(entry.records) +
               ", \"values\": " + std::to_string(entry.values) +
               ", \"defined\": " + std::to_string(entry.defined) +
               ", \"missing\": " + std::to_string(entry.missing) +
               ", \"min\": " + json_number(entry.minimum) +
               ", \"max\": " + json_number(entry.maximum) +
               ", \"mean\": " + json_number(entry.mean) + "}" +
               (k + 1U == stats.size() ? "\n" : ",\n");
    }
    out += "  ],\n";
    out += "  \"static_fields\": [\n";
    const std::vector<cteas::p6f::Calmet21FieldSpec> static_specs =
        cteas::p6f::static_field_specs(header.nx, header.ny, header.nz,
                                       header.nssta, header.nusta,
                                       header.npsta);
    for(std::size_t k = 0; k < static_specs.size(); ++k)
        out += "    {\"label\": " + json_string(static_specs[k].label) +
               ", \"unit\": " + json_string(static_specs[k].unit) +
               ", \"integer\": " + json_bool(static_specs[k].integer) +
               ", \"written_when\": " + json_string(static_specs[k].written_when) +
               ", \"source\": " + json_string(static_specs[k].source) + "}" +
               (k + 1U == static_specs.size() ? "\n" : ",\n");
    out += "  ],\n";
    out += "  \"hourly_layout\": [\n";
    const std::vector<cteas::p6f::Calmet21FieldSpec> hourly_specs =
        cteas::p6f::hourly_field_specs(header.nz, header.irtype,
                                       header.lcalgrd, header.npsta);
    for(std::size_t k = 0; k < hourly_specs.size(); ++k)
        out += "    {\"label\": " + json_string(hourly_specs[k].label) +
               ", \"unit\": " + json_string(hourly_specs[k].unit) +
               ", \"integer\": " + json_bool(hourly_specs[k].integer) +
               ", \"written_when\": " + json_string(hourly_specs[k].written_when) +
               ", \"source\": " + json_string(hourly_specs[k].source) + "}" +
               (k + 1U == hourly_specs.size() ? "\n" : ",\n");
    out += "  ],\n";
    out += "  \"status\": \"PASS_LAYOUT_VALID\"\n";
    out += "}\n";
    return out;
}

void write_report(const std::string& path, const std::string& text) {
    if(path.empty())return;
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if(!output)throw std::runtime_error("cannot create report " + path);
    output << text;
    output.close();
    if(!output)throw std::runtime_error("short report write to " + path);
}

// ---------------------------------------------------------------- commands
int command_roundtrip(const std::string& file, const std::string& out,
                      const std::string& expect, const std::string& report) {
    const std::vector<std::uint8_t> input = read_bytes(file);
    const Calmet21File parsed = cteas::p6f::parse_calmet_dat21(input);
    const std::vector<std::uint8_t> rewritten =
        cteas::p6f::serialize_calmet_dat21(parsed);
    if(!out.empty())write_bytes(out, rewritten);
    const std::string input_sha = cteas::p6f::sha256_hex(input);
    const std::string output_sha = cteas::p6f::sha256_hex(rewritten);
    const bool identical = input.size() == rewritten.size() &&
                           std::equal(input.begin(), input.end(),
                                      rewritten.begin());
    std::size_t difference = 0;
    while(difference < input.size() && difference < rewritten.size() &&
          input[difference] == rewritten[difference])
        ++difference;
    const bool expect_ok = expect.empty() || input_sha == expect;
    if(!expect_ok)
        std::cerr << "P6F_ROUNDTRIP_SHA256_MISMATCH expected=" << expect
                  << " actual=" << input_sha << "\n";
    std::string text;
    text += "{\n  \"tool\": " + json_string(kTool) + ",\n";
    text += "  \"command\": \"roundtrip\",\n";
    text += "  \"input\": " + json_string(file) + ",\n";
    text += "  \"input_bytes\": " + std::to_string(input.size()) + ",\n";
    text += "  \"input_sha256\": " + json_string(input_sha) + ",\n";
    text += "  \"output\": " + json_string(out) + ",\n";
    text += "  \"output_bytes\": " + std::to_string(rewritten.size()) + ",\n";
    text += "  \"output_sha256\": " + json_string(output_sha) + ",\n";
    text += "  \"byte_identical\": " + json_bool(identical) + ",\n";
    text += "  \"first_difference\": ";
    text += identical ? std::string("null")
                      : std::to_string(difference) + " /* " +
                            describe_offset(input, difference) + " */";
    text += ",\n";
    text += "  \"expect_sha256\": " + json_string(expect) + ",\n";
    text += "  \"expect_sha256_match\": " + json_bool(expect_ok) + ",\n";
    text += "  \"intervals\": " +
            std::to_string(cteas::p6f::interval_count(parsed)) + ",\n";
    text += "  \"fields_per_interval\": " +
            std::to_string(cteas::p6f::fields_per_interval(parsed.header)) + ",\n";
    text += "  \"status\": " +
            json_string(identical && expect_ok ? "PASS_ROUND_TRIP_BYTE_IDENTICAL"
                                               : "FAIL_ROUND_TRIP_DIFFERS") +
            "\n}\n";
    write_report(report, text);
    if(identical && expect_ok) {
        std::cout << "P6F_ROUNDTRIP_BYTE_IDENTICAL sha256=" << output_sha
                  << " bytes=" << rewritten.size()
                  << " intervals=" << cteas::p6f::interval_count(parsed)
                  << " fields_per_interval="
                  << cteas::p6f::fields_per_interval(parsed.header) << "\n";
        return 0;
    }
    std::cout << "P6F_ROUNDTRIP_MISMATCH first_difference=" << difference
              << " input_sha256=" << input_sha
              << " output_sha256=" << output_sha << "\n";
    return 1;
}

int command_check(const std::string& file, const std::string& report) {
    const std::vector<std::uint8_t> bytes = read_bytes(file);
    const Calmet21File parsed = cteas::p6f::parse_calmet_dat21(bytes);
    write_report(report, check_report(file, bytes, parsed));
    const std::vector<cteas::p6f::Calmet21FieldStats> stats =
        cteas::p6f::field_inventory(parsed);
    std::size_t missing = 0;
    for(const cteas::p6f::Calmet21FieldStats& entry : stats)
        missing += entry.missing;
    std::cout << "P6F_CHECK_LAYOUT_VALID sha256="
              << cteas::p6f::sha256_hex(bytes)
              << " comments=" << parsed.header.comments.size()
              << " intervals=" << cteas::p6f::interval_count(parsed)
              << " fields_per_interval="
              << cteas::p6f::fields_per_interval(parsed.header)
              << " field_records=" << parsed.hourly.size()
              << " missing_values=" << missing << "\n";
    return 0;
}

int command_emit_fixture(const std::string& out, int hours, int nx, int ny,
                         int nz, int nssta, int nusta, int npsta, int irtype,
                         const std::string& start, bool with_missing,
                         const std::string& report) {
    const std::int64_t start_instant =
        start.empty() ? cteas::p6f::days_from_civil(2022, 1U, 1U) * 86400
                      : parse_iso_instant(start);
    Calmet21File file = build_fixture(nx, ny, nz, hours, nssta, nusta,
                                      npsta, start_instant, with_missing);
    if(irtype != 1) {
        // IRTYPE=0 keeps only the wind block of each hour (OUTHR returns after
        // the U/V/[W] loop), so drop the fields the mode does not write.
        const std::vector<std::string> keep =
            cteas::p6f::hourly_labels(file.header.nz, irtype,
                                      file.header.lcalgrd, file.header.npsta);
        std::vector<cteas::p6f::Calmet21Field> filtered;
        for(const cteas::p6f::Calmet21Field& field : file.hourly) {
            const std::string name = trim_text(field.label);
            bool wanted = false;
            for(const std::string& label : keep)
                wanted = wanted || (trim_text(label) == name);
            if(wanted)filtered.push_back(field);
        }
        file.hourly = std::move(filtered);
        file.header.irtype = irtype;
    }
    const std::vector<std::uint8_t> bytes =
        cteas::p6f::serialize_calmet_dat21(file);
    write_bytes(out, bytes);
    std::string text;
    text += "{\n  \"tool\": " + json_string(kTool) + ",\n";
    text += "  \"command\": \"emit-fixture\",\n";
    text += "  \"out\": " + json_string(out) + ",\n";
    text += "  \"bytes\": " + std::to_string(bytes.size()) + ",\n";
    text += "  \"sha256\": " + json_string(cteas::p6f::sha256_hex(bytes)) + ",\n";
    text += "  \"intervals\": " + std::to_string(hours) + ",\n";
    text += "  \"fields_per_interval\": " +
            std::to_string(cteas::p6f::fields_per_interval(file.header)) + ",\n";
    text += "  \"synthetic\": true,\n";
    text += "  \"status\": \"PASS_FIXTURE_WRITTEN\"\n}\n";
    write_report(report, text);
    std::cout << "P6F_FIXTURE_WRITTEN sha256="
              << cteas::p6f::sha256_hex(bytes) << " bytes=" << bytes.size()
              << " intervals=" << hours << " fields_per_interval="
              << cteas::p6f::fields_per_interval(file.header)
              << " (SYNTHETIC layout fixture)\n";
    return 0;
}

int command_write_from_p6d(const std::string& fields, const std::string& variant,
                           const std::string& w_field,
                           const std::string& statics_from,
                           const std::string& met_fields_from, int irtype,
                           int hours, bool allow_unverified,
                           const std::string& out, const std::string& report) {
    require_argument(!fields.empty(), "write-from-p6d requires --fields");
    require_argument(!statics_from.empty(),
                     "write-from-p6d requires --statics-from <legal CALMET.DAT>");
    require_argument(!out.empty(), "write-from-p6d requires --out");
    require_argument(!met_fields_from.empty() || irtype == 0,
                     "IRTYPE=1 needs --met-fields-from <legal CALMET.DAT>");
    const cteas::p6f::Calmet21File statics =
        cteas::p6f::read_calmet_dat21(statics_from);
    std::unique_ptr<cteas::p6f::Calmet21File> met;
    if(!met_fields_from.empty())
        met = std::make_unique<cteas::p6f::Calmet21File>(
            cteas::p6f::read_calmet_dat21(met_fields_from));
    std::vector<std::string> labels =
        cteas::p6f::read_p6d_produced_hours(fields + "/produced_hours.txt");
    const std::size_t available = labels.size();
    const cteas::p6f::P6dFieldsMetadata declared =
        cteas::p6f::read_p6d_fields_metadata(fields + "/metadata.json");
    if(declared.hourly_label_count > 0)
        require_argument(static_cast<std::size_t>(declared.hourly_label_count) ==
                             available,
                         "metadata.hourly_labels declares " +
                             std::to_string(declared.hourly_label_count) +
                             " hours but produced_hours.txt lists " +
                             std::to_string(available));
    if(hours > 0 && static_cast<std::size_t>(hours) < labels.size())
        labels.resize(static_cast<std::size_t>(hours));
    const cteas::p6f::P6dFieldsMetadata metadata = declared;
    const cteas::p6f::Calmet21File file = cteas::p6f::build_calmet_from_p6d(
        fields, variant, w_field, labels, statics, met.get(), irtype,
        allow_unverified);
    const std::vector<std::uint8_t> bytes =
        cteas::p6f::serialize_calmet_dat21(file);
    write_bytes(out, bytes);
    std::string text;
    text += "{\n  \"tool\": " + json_string(kTool) + ",\n";
    text += "  \"command\": \"write-from-p6d\",\n";
    text += "  \"fields\": " + json_string(fields) + ",\n";
    text += "  \"variant\": " + json_string(variant) + ",\n";
    text += "  \"w_field\": " + json_string(w_field) + ",\n";
    text += "  \"statics_from\": " + json_string(statics_from) + ",\n";
    text += "  \"met_fields_from\": " + json_string(met_fields_from) + ",\n";
    text += "  \"irtype\": " + std::to_string(irtype) + ",\n";
    text += "  \"hours_available\": " + std::to_string(available) + ",\n";
    text += "  \"hours_written\": " + std::to_string(labels.size()) + ",\n";
    text += "  \"first_label\": " + json_string(labels.front()) + ",\n";
    text += "  \"last_label\": " + json_string(labels.back()) + ",\n";
    text += "  \"grid\": [" + std::to_string(metadata.nx) + "," +
            std::to_string(metadata.ny) + "," + std::to_string(metadata.nz) +
            "],\n";
    text += "  \"product\": " + json_string(metadata.product) + ",\n";
    text += "  \"product_status\": " + json_string(metadata.status) + ",\n";
    text += "  \"product_partial\": " + json_bool(metadata.partial) + ",\n";
    text += "  \"blend_verification\": " + json_string(metadata.blend_verification) +
            ",\n";
    text += "  \"fradj_status\": " + json_string(metadata.fradj_status) + ",\n";
    text += "  \"variant_source_verified\": " +
            json_bool(variant == "wind1") + ",\n";
    text += "  \"w_face_source_verified\": " +
            json_bool(w_field != "w_face") + ",\n";
    text += "  \"accept_unverified_variant\": " +
            json_bool(allow_unverified) + ",\n";
    text += "  \"grid_layout\": " + json_string(metadata.layout) + ",\n";
    text += "  \"grid_dtype\": " + json_string(metadata.dtype) + ",\n";
    text += "  \"missing_sentinel\": " +
            json_number(metadata.missing_sentinel) + ",\n";
    text += "  \"out\": " + json_string(out) + ",\n";
    text += "  \"out_bytes\": " + std::to_string(bytes.size()) + ",\n";
    text += "  \"out_sha256\": " +
            json_string(cteas::p6f::sha256_hex(bytes)) + ",\n";
    text += "  \"intervals\": " +
            std::to_string(cteas::p6f::interval_count(file)) + ",\n";
    text += "  \"fields_per_interval\": " +
            std::to_string(cteas::p6f::fields_per_interval(file.header)) + ",\n";
    text += "  \"status\": \"PASS_WRITTEN_FROM_P6D_ARRAYS\"\n}\n";
    write_report(report, text);
    std::cout << "P6F_WRITE_FROM_P6D_WRITTEN sha256="
              << cteas::p6f::sha256_hex(bytes) << " bytes=" << bytes.size()
              << " intervals=" << cteas::p6f::interval_count(file)
              << " fields_per_interval="
              << cteas::p6f::fields_per_interval(file.header)
              << " irtype=" << irtype << " variant=" << variant
              << " w_field=" << w_field << "\n";
    return 0;
}

std::string option_value(const std::vector<std::string>& args, std::size_t& at,
                         const std::string& name) {
    if(at + 1U >= args.size())
        throw std::runtime_error(name + " requires a value");
    return args[++at];
}
int option_int(const std::vector<std::string>& args, std::size_t& at,
               const std::string& name) {
    const std::string text = option_value(args, at, name);
    try {
        return std::stoi(text);
    } catch(const std::exception&) {
        throw std::runtime_error(name + " requires an integer, got " + text);
    }
}

}  // namespace

int main(int argc, char** argv) {
    const std::vector<std::string> args(argv + 1, argv + argc);
    if(args.empty()) {
        std::cerr << "usage: cteas_p6f_calmet_dat21_writer "
                     "<roundtrip|check|emit-fixture|write-from-p6d> [options]\n";
        return 2;
    }
    try {
        const std::string command = args[0];
        std::string file, out, expect, report, start;
        std::string fields, variant = "wind1", w_field = "w_face";
        std::string statics_from, met_fields_from;
        bool allow_unverified = false;
        // 0 means "all produced hours" for write-from-p6d and 3 for the
        // synthetic fixture generator.
        int hours = 0, nx = 8, ny = 5, nz = 3;
        int nssta = 1, nusta = 1, npsta = 0, irtype = 1;
        bool irtype_given = false;
        bool with_missing = false;
        for(std::size_t at = 1; at < args.size(); ++at) {
            const std::string& flag = args[at];
            if(flag == "--file")file = option_value(args, at, flag);
            else if(flag == "--out")out = option_value(args, at, flag);
            else if(flag == "--expect-sha256")expect = option_value(args, at, flag);
            else if(flag == "--report")report = option_value(args, at, flag);
            else if(flag == "--start")start = option_value(args, at, flag);
            else if(flag == "--hours") {
                hours = option_int(args, at, flag);
                require_argument(hours >= 0, "--hours must not be negative");
            }
            else if(flag == "--nx")nx = option_int(args, at, flag);
            else if(flag == "--ny")ny = option_int(args, at, flag);
            else if(flag == "--nz")nz = option_int(args, at, flag);
            else if(flag == "--nssta")nssta = option_int(args, at, flag);
            else if(flag == "--nusta")nusta = option_int(args, at, flag);
            else if(flag == "--npsta")npsta = option_int(args, at, flag);
            else if(flag == "--irtype") {
                irtype = option_int(args, at, flag);
                irtype_given = true;
            }
            else if(flag == "--fields")fields = option_value(args, at, flag);
            else if(flag == "--variant")variant = option_value(args, at, flag);
            else if(flag == "--w-field")w_field = option_value(args, at, flag);
            else if(flag == "--statics-from")statics_from = option_value(args, at, flag);
            else if(flag == "--met-fields-from")met_fields_from = option_value(args, at, flag);
            else if(flag == "--accept-unverified-variant")allow_unverified = true;
            else if(flag == "--with-missing")with_missing = true;
            else throw std::runtime_error("unknown option " + flag);
        }
        if(command == "roundtrip") {
            if(file.empty())throw std::runtime_error("roundtrip requires --file");
            return command_roundtrip(file, out, expect, report);
        }
        if(command == "check") {
            if(file.empty())throw std::runtime_error("check requires --file");
            return command_check(file, report);
        }
        if(command == "write-from-p6d") {
            // The wind-only layout (IRTYPE=0) is the honest product of the P6D
            // U/V/W contract; IRTYPE=1 additionally needs the 2-D
            // meteorological fields from another legal file.
            return command_write_from_p6d(fields, variant, w_field, statics_from,
                                          met_fields_from,
                                          irtype_given ? irtype : 0, hours,
                                          allow_unverified, out, report);
        }
        if(command == "emit-fixture") {
            if(out.empty())
                throw std::runtime_error("emit-fixture requires --out");
            return command_emit_fixture(out, hours > 0 ? hours : 3, nx, ny, nz,
                                        nssta, nusta, npsta, irtype, start,
                                        with_missing, report);
        }
        std::cerr << "unknown command " << command << "\n";
        return 2;
    } catch(const std::exception& error) {
        std::cerr << "P6F_ERROR " << error.what() << "\n";
        return 1;
    }
}
