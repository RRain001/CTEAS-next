// P6F CALMET.DAT 2.1 writer -- implementation.
//
// Everything here is fail-closed: a dataset that does not describe a file the
// unmodified CALMET 6.5.0 would write is rejected instead of being repaired.
#include "cteas/p6f/calmet_dat21_writer.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::p6f {
namespace {

constexpr const char* kPrefix = "P6F CALMET.DAT 2.1 ";

[[noreturn]] void fail(const std::string& message) {
    throw std::invalid_argument(std::string(kPrefix) + message);
}
void require(bool condition, const std::string& message) {
    if(!condition)fail(message);
}

// --------------------------------------------------------- little-endian io
void put_u32(std::vector<std::uint8_t>& out, std::uint32_t value) {
    out.push_back(static_cast<std::uint8_t>(value & 0xffU));
    out.push_back(static_cast<std::uint8_t>((value >> 8U) & 0xffU));
    out.push_back(static_cast<std::uint8_t>((value >> 16U) & 0xffU));
    out.push_back(static_cast<std::uint8_t>((value >> 24U) & 0xffU));
}
void put_i32(std::vector<std::uint8_t>& out, std::int32_t value) {
    std::uint32_t bits = 0;
    static_assert(sizeof(bits) == sizeof(value));
    std::memcpy(&bits, &value, sizeof(bits));
    put_u32(out, bits);
}
void put_f32(std::vector<std::uint8_t>& out, float value) {
    std::uint32_t bits = 0;
    static_assert(sizeof(bits) == sizeof(value));
    std::memcpy(&bits, &value, sizeof(bits));
    put_u32(out, bits);
}
// The original writes character*n items space padded to the declared width.
void put_ascii(std::vector<std::uint8_t>& out, const std::string& text,
               std::size_t width, const char* what) {
    require(text.size() <= width,
            std::string(what) + " is longer than its " + std::to_string(width) +
                "-byte original field");
    for(const char c : text)
        out.push_back(static_cast<std::uint8_t>(c));
    out.insert(out.end(), width - text.size(), static_cast<std::uint8_t>(' '));
}
void put_record(std::vector<std::uint8_t>& out,
                const std::vector<std::uint8_t>& payload) {
    require(payload.size() <=
                static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max()),
            "record payload exceeds the Fortran marker range");
    put_u32(out, static_cast<std::uint32_t>(payload.size()));
    out.insert(out.end(), payload.begin(), payload.end());
    put_u32(out, static_cast<std::uint32_t>(payload.size()));
}
std::uint32_t read_u32(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    require(at <= bytes.size() && bytes.size() - at >= 4U,
            "truncated 4-byte word");
    return std::uint32_t(bytes[at]) | (std::uint32_t(bytes[at + 1U]) << 8U) |
           (std::uint32_t(bytes[at + 2U]) << 16U) |
           (std::uint32_t(bytes[at + 3U]) << 24U);
}
std::int32_t read_i32(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    const std::uint32_t bits = read_u32(bytes, at);
    std::int32_t value = 0;
    static_assert(sizeof(bits) == sizeof(value));
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}
float read_f32(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    const std::uint32_t bits = read_u32(bytes, at);
    float value = 0.f;
    static_assert(sizeof(bits) == sizeof(value));
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}
std::string read_ascii(const std::vector<std::uint8_t>& bytes, std::size_t at,
                       std::size_t width, const char* what) {
    require(at <= bytes.size() && width <= bytes.size() - at,
            std::string("truncated ") + what);
    std::string text;
    text.reserve(width);
    for(std::size_t k = at; k < at + width; ++k)
        text.push_back(static_cast<char>(bytes[k]));
    return text;
}
std::string trim(const std::string& text) {
    const auto first = text.find_first_not_of(' ');
    if(first == std::string::npos)return std::string();
    const auto last = text.find_last_not_of(' ');
    return text.substr(first, last - first + 1U);
}
std::string index3(int value) {
    const std::string digits = std::to_string(value);
    return std::string(3U - digits.size(), ' ') + digits;
}
std::string field_label(const char* name, int value) {
    const std::string text = std::string(name) + index3(value);
    require(text.size() == 8U, "internal label width drift");
    return text;
}
int days_in_month(int year, int month) {
    static const int table[12] = {31, 28, 31, 30, 31, 30,
                                  31, 31, 30, 31, 30, 31};
    if(month == 2)return is_leap_year(year) ? 29 : 28;
    return table[month - 1];
}
// Absolute instant of an explicit calendar clock word group.
std::int64_t calendar_instant(int year, int month, int day, int hour,
                              int second) {
    require(year >= 1 && year <= 9999, "calendar year out of range");
    require(month >= 1 && month <= 12, "calendar month out of range");
    require(day >= 1 && day <= days_in_month(year, month),
            "calendar day out of range");
    require(hour >= 0 && hour <= 23, "calendar hour out of range");
    require(second >= 0 && second <= 3600, "calendar second out of range");
    return days_from_civil(year, static_cast<unsigned>(month),
                           static_cast<unsigned>(day)) *
               86400 +
           static_cast<std::int64_t>(hour) * 3600 + second;
}

// ------------------------------------------------------ proleptic calendar
struct CivilDate {
    int year = 0;
    unsigned month = 1, day = 1;
};
// Inverse of days_from_civil for a proleptic Gregorian day number.
CivilDate civil_date_from_days(std::int64_t days) {
    const std::int64_t shifted = days + 719468;
    const std::int64_t era =
        (shifted >= 0 ? shifted : shifted - 146096) / 146097;
    const unsigned day_of_era = static_cast<unsigned>(shifted - era * 146097);
    const unsigned year_of_era =
        (day_of_era - day_of_era / 1460U + day_of_era / 36524U -
         day_of_era / 146096U) /
        365U;
    const int year =
        static_cast<int>(year_of_era) + static_cast<int>(era) * 400;
    const unsigned day_of_year =
        day_of_era - (365U * year_of_era + year_of_era / 4U -
                      year_of_era / 100U);
    const unsigned month_index = (5U * day_of_year + 2U) / 153U;
    CivilDate date;
    date.year = year + (month_index < 10U ? 0 : 1);
    date.month = month_index < 10U ? month_index + 3U : month_index - 9U;
    date.day = day_of_year - (153U * month_index + 2U) / 5U + 1U;
    return date;
}

// --------------------------------------------------------------- raw walker
struct RecordWalker {
    const std::vector<std::uint8_t>& bytes;
    std::size_t cursor = 0;

    bool next(std::vector<std::uint8_t>& payload) {
        if(cursor == bytes.size())return false;
        require(bytes.size() - cursor >= 2U * record_marker_bytes,
                "truncated Fortran record marker");
        const std::uint32_t length = read_u32(bytes, cursor);
        const std::size_t start = cursor + record_marker_bytes;
        require(length <= bytes.size() - start - record_marker_bytes,
                "record length exceeds the remaining file");
        require(read_u32(bytes, start + length) == length,
                "Fortran record length markers disagree");
        payload.assign(bytes.begin() + static_cast<std::ptrdiff_t>(start),
                       bytes.begin() +
                           static_cast<std::ptrdiff_t>(start + length));
        cursor = start + length + record_marker_bytes;
        return true;
    }
};

// --------------------------------------------------------- field metadata
struct LabelMeta {
    const char* unit;
    const char* written_when;
    const char* source;
};
LabelMeta hourly_label_meta(const std::string& trimmed) {
    if(trimmed.rfind("U-LEV", 0U) == 0U)
        return {"m/s", "always (OUTHR wind loop)",
                "P6D diagnostic wind field"};
    if(trimmed.rfind("V-LEV", 0U) == 0U)
        return {"m/s", "always (OUTHR wind loop)",
                "P6D diagnostic wind field"};
    if(trimmed.rfind("WFACE", 0U) == 0U)
        return {"m/s", "LCALGRD", "P6D diagnostic wind field"};
    if(trimmed.rfind("T-LEV", 0U) == 0U)
        return {"K", "LCALGRD and IRTYPE=1", "P6E 3-D temperature field"};
    if(trimmed == "IPGT")
        return {"PGT stability class 1..6 (integer)", "IRTYPE=1",
                "P6E PGT stability class"};
    if(trimmed == "USTAR")
        return {"m/s", "IRTYPE=1", "P6E friction velocity"};
    if(trimmed == "ZI")
        return {"m", "IRTYPE=1", "P6E mixing height"};
    if(trimmed == "EL")
        return {"m", "IRTYPE=1", "P6E Monin-Obukhov length"};
    if(trimmed == "WSTAR")
        return {"m/s", "IRTYPE=1", "P6E convective velocity scale"};
    if(trimmed == "TEMPK")
        return {"K", "IRTYPE=1", "P6E 2-D surface temperature"};
    if(trimmed == "RHO")
        return {"kg/m3", "IRTYPE=1", "P6E air density"};
    if(trimmed == "QSW")
        return {"W/m2", "IRTYPE=1", "P6E short-wave radiation"};
    if(trimmed == "IRH")
        return {"percent (integer)", "IRTYPE=1",
                "P6E 2-D surface relative humidity"};
    if(trimmed == "RMM")
        return {"mm/h", "NPSTA/=0",
                "case precipitation rate"};
    if(trimmed == "IPCODE")
        return {"precipitation code (integer)", "NPSTA/=0",
                "case precipitation code"};
    fail("field label has no CALMET.DAT 2.1 definition: " + trimmed);
}
const std::vector<std::string>& internal_only_labels_ref() {
    static const std::vector<std::string> labels = internal_only_labels();
    return labels;
}

// --------------------------------------------------------------- validation
void require_finite(float value, const std::string& what) {
    require(std::isfinite(value), "non-finite value in " + what);
}
void require_finite_vector(const std::vector<float>& values,
                           const std::string& what) {
    for(const float value : values)require_finite(value, what);
}
void validate_clock(const Calmet21Time& time, const std::string& what) {
    require(time.year >= 1 && time.year <= 9999, what + " has an invalid year");
    require(time.julian_day >= 1 && time.julian_day <= days_in_year(time.year),
            what + " has an invalid day of year");
    require(time.hour >= 0 && time.hour <= 23, what + " has an invalid hour");
    require(time.seconds >= 0 && time.seconds < 86400,
            what + " has an invalid second");
}

}  // namespace

// --------------------------------------------------------------------- time
std::int64_t days_from_civil(int year, unsigned month, unsigned day) {
    year -= month <= 2U ? 1 : 0;
    const std::int64_t era = (year >= 0 ? year : year - 399) / 400;
    const unsigned year_of_era =
        static_cast<unsigned>(year - static_cast<int>(era) * 400);
    const unsigned day_of_year =
        (153U * (month + (month > 2U ? -3U : 9U)) + 2U) / 5U + day - 1U;
    const unsigned day_of_era = year_of_era * 365U + year_of_era / 4U -
                                year_of_era / 100U + day_of_year;
    return era * 146097 + static_cast<std::int64_t>(day_of_era) - 719468;
}

Calmet21Time civil_from_days(std::int64_t days) {
    const CivilDate date = civil_date_from_days(days);
    Calmet21Time time;
    time.year = date.year;
    time.julian_day =
        static_cast<int>(days - days_from_civil(date.year, 1U, 1U)) + 1;
    return time;
}

Calmet21Calendar calendar_from_instant(std::int64_t instant) {
    std::int64_t days = instant / 86400;
    std::int64_t rest = instant % 86400;
    if(rest < 0) {
        rest += 86400;
        --days;
    }
    const CivilDate date = civil_date_from_days(days);
    Calmet21Calendar calendar;
    calendar.year = date.year;
    calendar.month = static_cast<int>(date.month);
    calendar.day = static_cast<int>(date.day);
    calendar.hour = static_cast<int>(rest / 3600);
    calendar.minute = static_cast<int>((rest % 3600) / 60);
    calendar.second = static_cast<int>(rest % 60);
    return calendar;
}

std::string iso8601_utc(std::int64_t instant) {
    const Calmet21Calendar calendar = calendar_from_instant(instant);
    const auto two = [](int value) {
        return value < 10 ? std::string("0") + std::to_string(value)
                          : std::to_string(value);
    };
    const auto four = [](int value) {
        const std::string text = std::to_string(value);
        return std::string(4U - text.size(), '0') + text;
    };
    return four(calendar.year) + "-" + two(calendar.month) + "-" +
           two(calendar.day) + "T" + two(calendar.hour) + ":" +
           two(calendar.minute) + ":" + two(calendar.second) + "Z";
}

std::int32_t pack_time(const Calmet21Time& time) {
    validate_clock(time, "packed time label");
    return time.year * 100000 + time.julian_day * 100 + time.hour;
}

Calmet21Time unpack_time(std::int32_t packed, int seconds) {
    require(packed >= 0, "negative packed time label");
    Calmet21Time time;
    time.year = packed / 100000;
    time.julian_day = (packed % 100000) / 100;
    time.hour = packed % 100;
    time.seconds = seconds;
    validate_clock(time, "packed time label");
    return time;
}

std::int64_t instant_seconds(const Calmet21Time& time) {
    validate_clock(time, "time label");
    return (days_from_civil(time.year, 1U, 1U) +
            static_cast<std::int64_t>(time.julian_day - 1)) *
               86400 +
           static_cast<std::int64_t>(time.hour) * 3600 + time.seconds;
}

Calmet21Time instant_to_time(std::int64_t instant) {
    std::int64_t days = instant / 86400;
    std::int64_t rest = instant % 86400;
    if(rest < 0) {
        rest += 86400;
        --days;
    }
    Calmet21Time time = civil_from_days(days);
    time.hour = static_cast<int>(rest / 3600);
    time.seconds = static_cast<int>(rest % 3600);
    return time;
}

Calmet21Time next_hour(Calmet21Time time) {
    if(++time.hour == 24) {
        time.hour = 0;
        if(++time.julian_day > days_in_year(time.year)) {
            time.julian_day = 1;
            ++time.year;
        }
    }
    return time;
}

// ------------------------------------------------------------------- layout
bool is_integer_label(const std::string& label) {
    const std::string name = trim(label);
    return name == "IPGT" || name == "IRH";
}

std::vector<std::string> hourly_labels(int nz, int irtype, bool lcalgrd,
                                       int npsta) {
    require(nz >= 1 && nz <= 999,
            "NZ must be 1..999 (the original writes the level as I3)");
    require(irtype == 0 || irtype == 1, "IRTYPE must be 0 or 1");
    require(npsta >= 0, "NPSTA must not be negative");
    std::vector<std::string> labels;
    labels.reserve(static_cast<std::size_t>(nz) * 3U + 12U);
    for(int level = 1; level <= nz; ++level) {
        labels.push_back(field_label("U-LEV", level));
        labels.push_back(field_label("V-LEV", level));
        if(lcalgrd)labels.push_back(field_label("WFACE", level));
    }
    if(irtype == 0)return labels;
    if(lcalgrd)
        for(int level = 1; level <= nz; ++level)
            labels.push_back(field_label("T-LEV", level));
    labels.emplace_back("IPGT    ");
    labels.emplace_back("USTAR   ");
    labels.emplace_back("ZI      ");
    labels.emplace_back("EL      ");
    labels.emplace_back("WSTAR   ");
    if(npsta != 0)labels.emplace_back("RMM     ");
    labels.emplace_back("TEMPK   ");
    labels.emplace_back("RHO     ");
    labels.emplace_back("QSW     ");
    labels.emplace_back("IRH     ");
    if(npsta != 0)labels.emplace_back("IPCODE  ");
    return labels;
}

std::size_t fields_per_interval(const Calmet21Header& header) {
    return hourly_labels(header.nz, header.irtype, header.lcalgrd,
                         header.npsta)
        .size();
}

std::size_t interval_count(const Calmet21File& file) {
    const std::size_t per_interval = fields_per_interval(file.header);
    require(per_interval != 0U, "empty hourly field layout");
    return file.hourly.size() / per_interval;
}

std::vector<Calmet21FieldSpec> hourly_field_specs(int nz, int irtype,
                                                  bool lcalgrd, int npsta) {
    std::vector<Calmet21FieldSpec> specs;
    for(const std::string& label : hourly_labels(nz, irtype, lcalgrd, npsta)) {
        const std::string name = trim(label);
        const LabelMeta meta = hourly_label_meta(name);
        Calmet21FieldSpec spec;
        spec.label = label;
        spec.unit = meta.unit;
        spec.integer = is_integer_label(name);
        spec.written_when = meta.written_when;
        spec.source = meta.source;
        specs.push_back(std::move(spec));
    }
    return specs;
}

std::vector<Calmet21FieldSpec> static_field_specs(int nx, int ny, int nz,
                                                  int nssta, int nusta,
                                                  int npsta) {
    require(nx >= 1 && ny >= 1 && nz >= 1 && nssta >= 0 && nusta >= 0 &&
                npsta >= 0,
            "invalid static field extents");
    (void)nx;
    (void)ny;
    std::vector<Calmet21FieldSpec> specs;
    const auto push = [&specs](const char* label, const char* unit, bool ieee,
                               const char* when, const char* source) {
        Calmet21FieldSpec spec;
        spec.label = label;
        spec.unit = unit;
        spec.integer = ieee;
        spec.written_when = when;
        spec.source = source;
        specs.push_back(std::move(spec));
    };
    push("ZFACE", "m", false, "always", "case input (cell face heights)");
    if(nssta >= 1) {
        push("XSSTA", "m", false, "NSSTA>=1", "case input (surface station x)");
        push("YSSTA", "m", false, "NSSTA>=1", "case input (surface station y)");
    }
    if(nusta >= 1) {
        push("XUSTA", "m", false, "NUSTA>=1", "case input (upper station x)");
        push("YUSTA", "m", false, "NUSTA>=1", "case input (upper station y)");
    }
    if(npsta >= 1) {
        push("XPSTA", "m", false, "NPSTA>=1", "case input (precip station x)");
        push("YPSTA", "m", false, "NPSTA>=1", "case input (precip station y)");
    }
    push("Z0", "m", false, "always", "case input (roughness length)");
    push("ILANDU", "land-use category (integer)", true, "always",
         "case input (land use)");
    push("ELEV", "m", false, "always", "case input (terrain height)");
    push("XLAI", "m2/m2", false, "always", "case input (leaf area index)");
    if(nssta >= 1)
        push("NEARS", "surface station index (integer)", true, "NSSTA>=1",
             "case input (nearest surface station)");
    (void)nz;
    return specs;
}

// --------------------------------------------------------------- validation
void validate_calmet_dat21(const Calmet21File& file) {
    const Calmet21Header& header = file.header;
    const Calmet21Statics& statics = file.statics;

    // OUTHR writes the wind block for both run types and returns before the
    // 2-D meteorological fields when IRTYPE=0 (L13160-L13180); the label set
    // follows from the header, so both layouts are supported.
    require(header.irtype == 0 || header.irtype == 1,
            "IRTYPE must be 0 (winds only) or 1 (winds + meteorological "
            "fields)");
    require(header.iwfcod == 1, "IWFCOD must be 1 (write u, v and w)");
    require(header.nx >= 1 && header.ny >= 1,
            "grid extent NX/NY must be positive");
    require(header.nz >= 1 && header.nz <= 999,
            "grid extent NZ must be 1..999");
    require(std::isfinite(header.dgrid_m) && header.dgrid_m > 0.f,
            "DGRID must be finite and positive");
    require(std::isfinite(header.xorigin_m) && std::isfinite(header.yorigin_m),
            "grid origin must be finite");
    require(std::isfinite(header.projection.feast) &&
                std::isfinite(header.projection.fnorth) &&
                std::isfinite(header.projection.rnlat0) &&
                std::isfinite(header.projection.relon0) &&
                std::isfinite(header.projection.xlat1) &&
                std::isfinite(header.projection.xlat2),
            "map projection constants must be finite");
    require(header.timezone.size() == 8U,
            "AXTZ must be exactly 8 characters");
    require(header.nssta >= 0 && header.nusta >= 0 && header.npsta >= 0,
            "station counts must not be negative: NPSTA=-1 selects MM5 "
            "precipitation input, whose RMM/IPCODE mask semantics this writer "
            "does not implement; supply observed precipitation stations "
            "(NPSTA>=1) or omit precipitation (NPSTA=0)");
    require(header.nowsta >= 0, "NOWSTA must not be negative");
    require(header.nlu >= 0, "NLU must not be negative");
    require(header.iwat1 <= header.iwat2, "IWAT1 must not exceed IWAT2");
    require(trim(header.dataset) == "CALMET.DAT",
            "declaration dataset must be CALMET.DAT");
    require(trim(header.version) == "2.1", "declaration version must be 2.1");
    require(header.comments.size() <= max_comment_records,
            "too many comment records for a CALMET.DAT 2.1 file");
    for(const std::string& comment : header.comments)
        require(comment.size() <= comment_bytes,
                "comment record is longer than 132 bytes");
    require(header.projection.pmap.size() <= 8U,
            "PMAP is longer than its 8-byte original field");
    require(header.projection.datum.size() <= 8U,
            "DATUM is longer than its 8-byte original field");
    require(header.projection.daten.size() <= 12U,
            "DATEN is longer than its 12-byte original field");
    require(header.projection.utmhem.size() <= 4U,
            "UTMHEM is longer than its 4-byte original field");

    const std::size_t cells =
        static_cast<std::size_t>(header.nx) * static_cast<std::size_t>(header.ny);
    require(statics.zface_m.size() == static_cast<std::size_t>(header.nz) + 1U,
            "ZFACE must have NZ+1 cell faces");
    for(std::size_t k = 0; k < statics.zface_m.size(); ++k) {
        require_finite(statics.zface_m[k], "ZFACE");
        require(k == 0U || statics.zface_m[k] > statics.zface_m[k - 1U],
                "ZFACE must increase strictly with height");
    }
    const auto check_station = [](const char* what,
                                  const std::vector<float>& x,
                                  const std::vector<float>& y, int count) {
        require(static_cast<int>(x.size()) == count &&
                    static_cast<int>(y.size()) == count,
                std::string(what) + " coordinate counts must equal the "
                                    "declared station count");
        require_finite_vector(x, what);
        require_finite_vector(y, what);
    };
    check_station("surface station", statics.surface_x_m, statics.surface_y_m,
                  header.nssta);
    check_station("upper-air station", statics.upper_x_m, statics.upper_y_m,
                  header.nusta);
    check_station("precipitation station", statics.precip_x_m,
                  statics.precip_y_m, header.npsta);
    for(const std::int32_t category : statics.ilandu)
        require(category >= 0,
                "ILANDU must not contain a negative land-use category");
    require(statics.z0_m.size() == cells, "Z0 must have NX*NY values");
    require(statics.elev_m.size() == cells, "ELEV must have NX*NY values");
    require(statics.xlai.size() == cells, "XLAI must have NX*NY values");
    require(statics.ilandu.size() == cells, "ILANDU must have NX*NY values");
    require_finite_vector(statics.z0_m, "Z0");
    require_finite_vector(statics.elev_m, "ELEV");
    require_finite_vector(statics.xlai, "XLAI");
    if(header.nssta >= 1)
        require(statics.nears.size() == cells, "NEARS must have NX*NY values");
    else
        require(statics.nears.empty(),
                "NEARS must not be supplied when NSSTA<1: the original writes "
                "no such record");

    const std::vector<std::string> labels =
        hourly_labels(header.nz, header.irtype, header.lcalgrd, header.npsta);
    const std::size_t per_interval = labels.size();
    require(file.hourly.size() % per_interval == 0U,
            "the hourly field vector does not contain complete intervals");
    const std::size_t intervals = file.hourly.size() / per_interval;
    require(header.irlg >= 0, "IRLG must not be negative");
    require(static_cast<std::size_t>(header.irlg) == intervals,
            "IRLG must equal the number of hourly intervals in the file");
    if(intervals == 0U)return;

    // A label the original never writes must be reported as such instead of
    // being silently dropped or renamed.
    for(const Calmet21Field& field : file.hourly) {
        const std::string name = trim(field.label);
        for(const std::string& internal : internal_only_labels_ref())
            require(name != internal,
                    name + " is internal CALMET state and has no CALMET.DAT "
                           "2.1 representation");
        if(header.npsta == 0)
            require(name != "RMM" && name != "IPCODE",
                    name + " cannot appear when NPSTA=0 (the original writes "
                           "RMM/IPCODE only when NPSTA/=0)");
    }

    const Calmet21Time first_begin = file.hourly.front().begin;
    const Calmet21Time last_end = file.hourly.back().end;
    require(calendar_instant(header.begin_year, header.begin_month,
                             header.begin_day, header.begin_hour,
                             header.begin_second) ==
                instant_seconds(first_begin),
            "the declared run begin clock must equal the first hourly "
            "interval begin");
    require(calendar_instant(header.end_year, header.end_month, header.end_day,
                             header.end_hour, header.end_second) ==
                instant_seconds(last_end),
            "the declared run end clock must equal the last hourly interval "
            "end");

    for(std::size_t hour = 0; hour < intervals; ++hour) {
        const Calmet21Field& lead = file.hourly[hour * per_interval];
        const std::int64_t begin = instant_seconds(lead.begin);
        const std::int64_t end = instant_seconds(lead.end);
        require(end - begin == 3600,
                "every hourly interval must be exactly 3600 s");
        require(pack_time(lead.end) == pack_time(lead.begin) &&
                    lead.end.seconds == lead.begin.seconds + 3600,
                "the original writes the hourly end clock as the same packed "
                "hour with seconds advanced by 3600");
        if(hour > 0U)
            require(begin == instant_seconds(
                                 file.hourly[(hour - 1U) * per_interval].end),
                    "hourly intervals must be contiguous");
        for(std::size_t slot = 0; slot < per_interval; ++slot) {
            const Calmet21Field& field =
                file.hourly[hour * per_interval + slot];
            require(trim(field.label) == trim(labels[slot]),
                    "hourly field order mismatch: expected " + labels[slot] +
                        " but found " + trim(field.label));
            validate_clock(field.begin, "hourly begin clock");
            validate_clock(field.end, "hourly end clock");
            require(pack_time(field.begin) == pack_time(lead.begin) &&
                        field.begin.seconds == lead.begin.seconds &&
                        pack_time(field.end) == pack_time(lead.end) &&
                        field.end.seconds == lead.end.seconds,
                    "all fields of one hour must share one time label");
            require(field.integer == is_integer_label(field.label),
                    trim(field.label) +
                        " must be stored as the integer/real kind the original "
                        "writes");
            if(field.integer) {
                require(field.integer_values.size() == cells,
                        trim(field.label) + " must have NX*NY integer values");
                require(field.real_values.empty(),
                        trim(field.label) +
                            " must not carry real values as well");
            } else {
                require(field.real_values.size() == cells,
                        trim(field.label) + " must have NX*NY real values");
                require(field.integer_values.empty(),
                        trim(field.label) +
                            " must not carry integer values as well");
                require_finite_vector(field.real_values, trim(field.label));
            }
        }
    }
}

// ------------------------------------------------------------- serialisation
std::vector<std::uint8_t> serialize_calmet_dat21(const Calmet21File& file) {
    validate_calmet_dat21(file);
    const Calmet21Header& header = file.header;
    const Calmet21Statics& statics = file.statics;

    std::vector<std::uint8_t> out;
    std::vector<std::uint8_t> payload;

    // record #1 -- file declaration (96 bytes)
    put_ascii(payload, header.dataset, 16U, "dataset name");
    put_ascii(payload, header.version, 16U, "version");
    put_ascii(payload, header.model, 64U, "model name");
    put_record(out, payload);

    // record #2 -- number of comment records
    payload.clear();
    put_i32(payload, static_cast<std::int32_t>(header.comments.size()));
    put_record(out, payload);

    // records #3..#NCOM+2 -- the comment section (132 bytes each)
    for(const std::string& comment : header.comments) {
        payload.clear();
        put_ascii(payload, comment, comment_bytes, "comment");
        put_record(out, payload);
    }

    // record #NCOM+3 -- run controls (176 bytes, OUTHD order)
    payload.clear();
    put_i32(payload, header.begin_year);
    put_i32(payload, header.begin_month);
    put_i32(payload, header.begin_day);
    put_i32(payload, header.begin_hour);
    put_i32(payload, header.begin_second);
    put_i32(payload, header.end_year);
    put_i32(payload, header.end_month);
    put_i32(payload, header.end_day);
    put_i32(payload, header.end_hour);
    put_i32(payload, header.end_second);
    put_ascii(payload, header.timezone, 8U, "time zone label");
    put_i32(payload, header.irlg);
    put_i32(payload, header.irtype);
    put_i32(payload, header.nx);
    put_i32(payload, header.ny);
    put_i32(payload, header.nz);
    put_f32(payload, header.dgrid_m);
    put_f32(payload, header.xorigin_m);
    put_f32(payload, header.yorigin_m);
    put_i32(payload, header.iwfcod);
    put_i32(payload, header.nssta);
    put_i32(payload, header.nusta);
    put_i32(payload, header.npsta);
    put_i32(payload, header.nowsta);
    put_i32(payload, header.nlu);
    put_i32(payload, header.iwat1);
    put_i32(payload, header.iwat2);
    put_i32(payload, header.lcalgrd ? 1 : 0);
    put_ascii(payload, header.projection.pmap, 8U, "PMAP");
    put_ascii(payload, header.projection.datum, 8U, "DATUM");
    put_ascii(payload, header.projection.daten, 12U, "DATEN");
    put_f32(payload, header.projection.feast);
    put_f32(payload, header.projection.fnorth);
    put_ascii(payload, header.projection.utmhem, 4U, "UTMHEM");
    put_i32(payload, header.projection.iutmzn);
    put_f32(payload, header.projection.rnlat0);
    put_f32(payload, header.projection.relon0);
    put_f32(payload, header.projection.xlat1);
    put_f32(payload, header.projection.xlat2);
    require(payload.size() == controls_bytes, "controls record size drift");
    put_record(out, payload);

    // static records: label + four zero clock words + NX*NY words
    const auto write_static_real = [&out, &payload](
                                       const char* label,
                                       const std::vector<float>& values) {
        payload.clear();
        put_ascii(payload, label, 8U, "static record label");
        for(int k = 0; k < 4; ++k)put_i32(payload, 0);
        for(const float value : values)put_f32(payload, value);
        put_record(out, payload);
    };
    const auto write_static_int = [&out, &payload](
                                      const char* label,
                                      const std::vector<std::int32_t>& values) {
        payload.clear();
        put_ascii(payload, label, 8U, "static record label");
        for(int k = 0; k < 4; ++k)put_i32(payload, 0);
        for(const std::int32_t value : values)put_i32(payload, value);
        put_record(out, payload);
    };
    write_static_real("ZFACE", statics.zface_m);
    if(header.nssta >= 1) {
        write_static_real("XSSTA", statics.surface_x_m);
        write_static_real("YSSTA", statics.surface_y_m);
    }
    if(header.nusta >= 1) {
        write_static_real("XUSTA", statics.upper_x_m);
        write_static_real("YUSTA", statics.upper_y_m);
    }
    if(header.npsta >= 1) {
        write_static_real("XPSTA", statics.precip_x_m);
        write_static_real("YPSTA", statics.precip_y_m);
    }
    write_static_real("Z0", statics.z0_m);
    write_static_int("ILANDU", statics.ilandu);
    write_static_real("ELEV", statics.elev_m);
    write_static_real("XLAI", statics.xlai);
    if(header.nssta >= 1)write_static_int("NEARS", statics.nears);

    // hourly records, in the exact OUTHR order
    for(const Calmet21Field& field : file.hourly) {
        payload.clear();
        put_ascii(payload, field.label, 8U, "hourly field label");
        put_i32(payload, pack_time(field.begin));
        put_i32(payload, field.begin.seconds);
        put_i32(payload, pack_time(field.end));
        put_i32(payload, field.end.seconds);
        if(field.integer)
            for(const std::int32_t value : field.integer_values)
                put_i32(payload, value);
        else
            for(const float value : field.real_values)put_f32(payload, value);
        put_record(out, payload);
    }
    return out;
}

// ------------------------------------------------------------------ parsing
Calmet21File parse_calmet_dat21(const std::vector<std::uint8_t>& bytes,
                                  bool native_one_hour_transport) {
    Calmet21File file;
    Calmet21Header& header = file.header;
    Calmet21Statics& statics = file.statics;
    RecordWalker walker{bytes};
    std::vector<std::uint8_t> payload;

    require(walker.next(payload), "missing file declaration record");
    require(payload.size() == declaration_bytes,
            "the file declaration record must be 96 bytes");
    header.dataset = read_ascii(payload, 0U, 16U, "dataset name");
    header.version = read_ascii(payload, 16U, 16U, "version");
    header.model = read_ascii(payload, 32U, 64U, "model name");
    require(trim(header.dataset) == "CALMET.DAT" &&
                trim(header.version) == "2.1",
            "unsupported CALMET.DAT signature/version");

    require(walker.next(payload) && payload.size() == 4U,
            "missing comment count record");
    const std::int32_t comments = read_i32(payload, 0U);
    require(comments >= 0 &&
                static_cast<std::uint32_t>(comments) <= max_comment_records,
            "invalid comment count");
    header.comments.reserve(static_cast<std::size_t>(comments));
    for(std::int32_t index = 0; index < comments; ++index) {
        require(walker.next(payload) && payload.size() == comment_bytes,
                "malformed comment record");
        header.comments.push_back(
            read_ascii(payload, 0U, comment_bytes, "comment"));
    }

    require(walker.next(payload) && payload.size() == controls_bytes,
            "the run controls record must be 176 bytes");
    header.begin_year = read_i32(payload, 0U);
    header.begin_month = read_i32(payload, 4U);
    header.begin_day = read_i32(payload, 8U);
    header.begin_hour = read_i32(payload, 12U);
    header.begin_second = read_i32(payload, 16U);
    header.end_year = read_i32(payload, 20U);
    header.end_month = read_i32(payload, 24U);
    header.end_day = read_i32(payload, 28U);
    header.end_hour = read_i32(payload, 32U);
    header.end_second = read_i32(payload, 36U);
    header.timezone = read_ascii(payload, 40U, 8U, "time zone label");
    header.irlg = read_i32(payload, 48U);
    header.irtype = read_i32(payload, 52U);
    header.nx = read_i32(payload, 56U);
    header.ny = read_i32(payload, 60U);
    header.nz = read_i32(payload, 64U);
    header.dgrid_m = read_f32(payload, 68U);
    header.xorigin_m = read_f32(payload, 72U);
    header.yorigin_m = read_f32(payload, 76U);
    header.iwfcod = read_i32(payload, 80U);
    header.nssta = read_i32(payload, 84U);
    header.nusta = read_i32(payload, 88U);
    header.npsta = read_i32(payload, 92U);
    header.nowsta = read_i32(payload, 96U);
    header.nlu = read_i32(payload, 100U);
    header.iwat1 = read_i32(payload, 104U);
    header.iwat2 = read_i32(payload, 108U);
    header.lcalgrd = read_i32(payload, 112U) != 0;
    header.projection.pmap = read_ascii(payload, 116U, 8U, "PMAP");
    header.projection.datum = read_ascii(payload, 124U, 8U, "DATUM");
    header.projection.daten = read_ascii(payload, 132U, 12U, "DATEN");
    header.projection.feast = read_f32(payload, 144U);
    header.projection.fnorth = read_f32(payload, 148U);
    header.projection.utmhem = read_ascii(payload, 152U, 4U, "UTMHEM");
    header.projection.iutmzn = read_i32(payload, 156U);
    header.projection.rnlat0 = read_f32(payload, 160U);
    header.projection.relon0 = read_f32(payload, 164U);
    header.projection.xlat1 = read_f32(payload, 168U);
    header.projection.xlat2 = read_f32(payload, 172U);

    require((header.irtype == 0 || header.irtype == 1) && header.iwfcod == 1,
            "only IRTYPE=0/1 with IWFCOD=1 files are supported");
    require(header.nx >= 1 && header.nx <= 1000000 && header.ny >= 1 &&
                header.ny <= 1000000,
            "invalid grid extent in the run controls");
    require(header.nz >= 1 && header.nz <= 999,
            "invalid NZ in the run controls");
    require(header.nssta >= 0 && header.nusta >= 0 && header.npsta >= 0,
            "negative station count in the run controls");
    const std::size_t cells =
        static_cast<std::size_t>(header.nx) * static_cast<std::size_t>(header.ny);

    const auto read_static_real = [&walker, &payload](
                                      const char* expected, std::size_t count,
                                      std::vector<float>& values) {
        require(walker.next(payload),
                std::string("missing static record ") + expected);
        require(trim(read_ascii(payload, 0U, 8U, "static label")) == expected,
                std::string("static record label mismatch, expected ") +
                    expected);
        for(int word = 0; word < 4; ++word)
            require(read_i32(payload,
                             8U + static_cast<std::size_t>(word) * 4U) == 0,
                    std::string("static record ") + expected +
                        " must carry the original zero clock words");
        require(payload.size() == field_header_bytes + 4U * count,
                std::string("static record size drift for ") + expected);
        values.resize(count);
        for(std::size_t k = 0; k < count; ++k)
            values[k] = read_f32(payload, field_header_bytes + 4U * k);
    };
    const auto read_static_int = [&walker, &payload](
                                     const char* expected, std::size_t count,
                                     std::vector<std::int32_t>& values) {
        require(walker.next(payload),
                std::string("missing static record ") + expected);
        require(trim(read_ascii(payload, 0U, 8U, "static label")) == expected,
                std::string("static record label mismatch, expected ") +
                    expected);
        for(int word = 0; word < 4; ++word)
            require(read_i32(payload,
                             8U + static_cast<std::size_t>(word) * 4U) == 0,
                    std::string("static record ") + expected +
                        " must carry the original zero clock words");
        require(payload.size() == field_header_bytes + 4U * count,
                std::string("static record size drift for ") + expected);
        values.resize(count);
        for(std::size_t k = 0; k < count; ++k)
            values[k] = read_i32(payload, field_header_bytes + 4U * k);
    };
    read_static_real("ZFACE", static_cast<std::size_t>(header.nz) + 1U,
                     statics.zface_m);
    if(header.nssta >= 1) {
        read_static_real("XSSTA", static_cast<std::size_t>(header.nssta),
                         statics.surface_x_m);
        read_static_real("YSSTA", static_cast<std::size_t>(header.nssta),
                         statics.surface_y_m);
    }
    if(header.nusta >= 1) {
        read_static_real("XUSTA", static_cast<std::size_t>(header.nusta),
                         statics.upper_x_m);
        read_static_real("YUSTA", static_cast<std::size_t>(header.nusta),
                         statics.upper_y_m);
    }
    if(header.npsta >= 1) {
        read_static_real("XPSTA", static_cast<std::size_t>(header.npsta),
                         statics.precip_x_m);
        read_static_real("YPSTA", static_cast<std::size_t>(header.npsta),
                         statics.precip_y_m);
    }
    read_static_real("Z0", cells, statics.z0_m);
    read_static_int("ILANDU", cells, statics.ilandu);
    read_static_real("ELEV", cells, statics.elev_m);
    read_static_real("XLAI", cells, statics.xlai);
    if(header.nssta >= 1)read_static_int("NEARS", cells, statics.nears);

    const std::vector<std::string> labels =
        hourly_labels(header.nz, header.irtype, header.lcalgrd, header.npsta);
    while(walker.next(payload)) {
        require(payload.size() == field_header_bytes + 4U * cells,
                "unexpected hourly record size");
        Calmet21Field field;
        field.label = read_ascii(payload, 0U, 8U, "hourly label");
        const std::size_t slot = file.hourly.size() % labels.size();
        require(trim(field.label) == trim(labels[slot]),
                "hourly field order mismatch: expected " + labels[slot] +
                    " but found " + trim(field.label));
        field.begin = unpack_time(read_i32(payload, 8U), read_i32(payload, 12U));
        field.end = unpack_time(read_i32(payload, 16U), read_i32(payload, 20U));
        field.integer = is_integer_label(field.label);
        if(field.integer) {
            field.integer_values.resize(cells);
            for(std::size_t k = 0; k < cells; ++k)
                field.integer_values[k] =
                    read_i32(payload, field_header_bytes + 4U * k);
        } else {
            field.real_values.resize(cells);
            for(std::size_t k = 0; k < cells; ++k)
                field.real_values[k] =
                    read_f32(payload, field_header_bytes + 4U * k);
        }
        file.hourly.push_back(std::move(field));
    }
    require(file.hourly.size() % labels.size() == 0U,
            "the file ends inside an hourly field group");
    if(native_one_hour_transport) {
        const std::size_t per_hour=fields_per_interval(header);
        require(file.hourly.size()==per_hour&&header.irlg==1,
                "native transport must carry exactly one complete hour");
        const auto& first=file.hourly.front().begin;
        const auto& last=file.hourly.back().end;
        const auto begin=calendar_from_instant(instant_seconds(first));
        const auto end=calendar_from_instant(instant_seconds(last));
        header.begin_year=begin.year;header.begin_month=begin.month;
        header.begin_day=begin.day;header.begin_hour=begin.hour;
        header.begin_second=begin.minute*60+begin.second;
        header.end_year=end.year;header.end_month=end.month;
        header.end_day=end.day;header.end_hour=end.hour;
        header.end_second=end.minute*60+end.second;
    }
    validate_calmet_dat21(file);
    return file;
}

Calmet21File parse_calmet_dat21(const std::vector<std::uint8_t>& bytes) {
    // Keep the original public strict parser API unchanged.
    return parse_calmet_dat21(bytes,false);
}

Calmet21File read_calmet_dat21(const std::string& path) {
    std::ifstream input(path, std::ios::binary);
    if(!input)fail("cannot open " + path);
    const std::vector<std::uint8_t> bytes(
        (std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    return parse_calmet_dat21(bytes);
}
Calmet21File read_calmet_dat21_native_one_hour(const std::string& path) {
    std::ifstream input(path,std::ios::binary);
    if(!input)fail("cannot open native one-hour transport " + path);
    const std::vector<std::uint8_t> bytes(
        (std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    return parse_calmet_dat21(bytes,true);
}

void write_calmet_dat21(const std::string& path, const Calmet21File& file) {
    const std::vector<std::uint8_t> bytes = serialize_calmet_dat21(file);
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if(!output)fail("cannot create " + path);
    output.write(reinterpret_cast<const char*>(bytes.data()),
                 static_cast<std::streamsize>(bytes.size()));
    if(!output)fail("short write to " + path);
    output.close();
    if(!output)fail("short write to " + path);
}

// ---------------------------------------------------------------- inventory
std::vector<Calmet21FieldStats> field_inventory(const Calmet21File& file) {
    const Calmet21Header& header = file.header;
    const std::size_t cells =
        static_cast<std::size_t>(header.nx) * static_cast<std::size_t>(header.ny);
    const std::vector<Calmet21FieldSpec> specs =
        hourly_field_specs(header.nz, header.irtype, header.lcalgrd,
                           header.npsta);
    std::vector<Calmet21FieldStats> stats;
    std::vector<double> totals;
    const auto slot_for = [&stats, &totals, &specs](const std::string& name,
                                                    bool integer) {
        for(std::size_t k = 0; k < stats.size(); ++k)
            if(stats[k].label == name)return k;
        Calmet21FieldStats created;
        created.label = name;
        created.integer = integer;
        created.unit = "unknown";
        created.minimum = std::numeric_limits<double>::quiet_NaN();
        created.maximum = std::numeric_limits<double>::quiet_NaN();
        created.mean = std::numeric_limits<double>::quiet_NaN();
        for(const Calmet21FieldSpec& spec : specs)
            if(trim(spec.label) == name)created.unit = spec.unit;
        stats.push_back(std::move(created));
        totals.push_back(0.0);
        return stats.size() - 1U;
    };
    const auto add_values = [&stats, &totals, cells](
                                std::size_t slot, const auto& values) {
        Calmet21FieldStats& entry = stats[slot];
        ++entry.records;
        entry.values += cells;
        for(const auto value : values) {
            if(is_missing(value)) {
                ++entry.missing;
                continue;
            }
            const double number = static_cast<double>(value);
            if(std::isnan(entry.minimum) || number < entry.minimum)
                entry.minimum = number;
            if(std::isnan(entry.maximum) || number > entry.maximum)
                entry.maximum = number;
            totals[slot] += number;
            ++entry.defined;
        }
    };
    for(const Calmet21Field& field : file.hourly) {
        const std::string name = trim(field.label);
        const std::size_t slot = slot_for(name, field.integer);
        if(field.integer)
            add_values(slot, field.integer_values);
        else
            add_values(slot, field.real_values);
    }
    for(std::size_t k = 0; k < stats.size(); ++k)
        if(stats[k].defined != 0U)
            stats[k].mean = totals[k] / static_cast<double>(stats[k].defined);
    return stats;
}

}  // namespace cteas::p6f
