#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/fortran_records.hpp"
#include "cteas/puff/gregorian.hpp"

#include <algorithm>
#include <cstring>
#include <cstdint>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::puff {
namespace {
std::uint32_t raw32(const std::vector<std::uint8_t>& v, std::size_t p) {
    if (p > v.size() || v.size() - p < 4U)
        throw std::runtime_error("P7B short CALMET.DAT 4-byte field");
    return std::uint32_t(v[p]) | (std::uint32_t(v[p+1]) << 8U) |
           (std::uint32_t(v[p+2]) << 16U) | (std::uint32_t(v[p+3]) << 24U);
}
std::int32_t integer32(const std::vector<std::uint8_t>& v, std::size_t p) {
    const std::uint32_t bits = raw32(v,p);
    std::int32_t decoded = 0;
    static_assert(sizeof(decoded) == sizeof(bits));
    std::memcpy(&decoded, &bits, sizeof(bits));
    return decoded;
}
float real32(const std::vector<std::uint8_t>& v, std::size_t p) {
    const std::uint32_t bits = raw32(v,p);
    float decoded = 0.0F;
    static_assert(sizeof(decoded) == sizeof(bits));
    std::memcpy(&decoded, &bits, sizeof(bits));
    return decoded;
}
std::string ascii(const std::vector<std::uint8_t>& v, std::size_t p, std::size_t size) {
    if (p > v.size() || size > v.size()-p)
        throw std::runtime_error("P7B truncated CALMET.DAT ASCII");
    std::string s;
    for (std::size_t i=p; i<p+size; ++i) {
        if (v[i] < 32U || v[i] > 126U)
            throw std::runtime_error("P7B nonprintable CALMET.DAT ASCII");
        s.push_back(static_cast<char>(v[i]));
    }
    while (!s.empty() && s.back() == ' ') s.pop_back();
    return s;
}
void check(bool valid, const std::string& message) {
    if (!valid) throw std::runtime_error("P7B CALMET21 " + message);
}
// Gregorian dates are converted by the shared cteas::puff::days_from_civil
// helper so the CALMET.DAT reader and the P7 case ledger cannot drift apart.
Calmet21Time timestamp(std::int32_t packed, std::int32_t seconds) {
    Calmet21Time t;
    t.year = packed / 100000;
    t.julian_day = (packed % 100000) / 100;
    t.hour = packed % 100;
    t.seconds = seconds;
    const bool leap = t.year%4 == 0 && (t.year%100 != 0 || t.year%400 == 0);
    check(t.year >= 1900 && t.year <= 2100 && t.julian_day >= 1 &&
          t.julian_day <= (leap ? 366 : 365) &&
          t.hour >= 0 && t.hour <= 23 && seconds >= 0 && seconds <= 3600,
          "invalid original Julian timestamp");
    t.unix_seconds = (days_from_civil(t.year, 1U, 1U) +
                      static_cast<std::int64_t>(t.julian_day - 1)) * 86400 +
                     static_cast<std::int64_t>(t.hour) * 3600 + seconds;
    return t;
}
std::vector<std::string> expected_labels(int nz) {
    std::vector<std::string> labels;
    for (int z=1; z<=nz; ++z) {
        const auto number = std::to_string(z);
        check(number.size()<=3, "too many levels");
        const std::string padded(3-number.size(), ' ');
        for (const auto* prefix: {"U-LEV", "V-LEV", "WFACE"})
            labels.emplace_back(std::string(prefix) + padded + number);
    }
    for (int z=1; z<=nz; ++z) {
        const auto number = std::to_string(z);
        labels.emplace_back("T-LEV" + std::string(3-number.size(), ' ') + number);
    }
    for (const auto* label: {"IPGT","USTAR","ZI","EL","WSTAR",
                             "TEMPK","RHO","QSW","IRH"})
        labels.emplace_back(label);
    return labels;
}

// Original OUTHD static records (CALMET calmet.for L12482-12536). Labels are
// exact and the payload length must match the documented field, otherwise the
// record is malformed and must not be ignored silently.
bool decode_static_record(const std::string& label, const std::vector<std::uint8_t>& record,
                          int nx, int ny, int nz, Calmet21Static& statics) {
    const std::size_t cells = std::size_t(nx) * std::size_t(ny);
    const auto grid_reals = [&record](std::size_t count, const std::string& name) {
        check(record.size() == 24U + 4U * count, "malformed " + name + " static grid");
        std::vector<float> values;
        values.reserve(count);
        for (std::size_t i = 0; i < count; ++i) {
            const float value = real32(record, 24U + 4U * i);
            check(std::isfinite(value), "nonfinite " + name + " value");
            values.push_back(value);
        }
        return values;
    };
    const auto grid_integers = [&record](std::size_t count, const std::string& name) {
        check(record.size() == 24U + 4U * count, "malformed " + name + " static grid");
        std::vector<std::int32_t> values;
        values.reserve(count);
        for (std::size_t i = 0; i < count; ++i) {
            values.push_back(integer32(record, 24U + 4U * i));
        }
        return values;
    };
    const auto check_range = [&label](const std::vector<float>& values, float low, float high) {
        for (const float value : values) {
            check(value >= low && value <= high, "out-of-range " + label + " value");
        }
    };
    if (label == "ZFACE") {
        statics.cell_face_m = grid_reals(std::size_t(nz) + 1U, label);
        statics.present = true;
        ++statics.decoded_records;
        return true;
    }
    if (label == "Z0") {
        statics.roughness_m = grid_reals(cells, label);
        check_range(statics.roughness_m, 0.0F, 100.0F);
        statics.present = true;
        ++statics.decoded_records;
        return true;
    }
    if (label == "ILANDU") {
        statics.land_use = grid_integers(cells, label);
        for (const auto value : statics.land_use) {
            check(value >= 0 && value <= 1000, "out-of-range ILANDU category");
        }
        statics.present = true;
        ++statics.decoded_records;
        return true;
    }
    if (label == "ELEV") {
        statics.elevation_m = grid_reals(cells, label);
        check_range(statics.elevation_m, -1000.0F, 10000.0F);
        statics.present = true;
        ++statics.decoded_records;
        return true;
    }
    if (label == "XLAI") {
        statics.leaf_area_index = grid_reals(cells, label);
        check_range(statics.leaf_area_index, 0.0F, 20.0F);
        statics.present = true;
        ++statics.decoded_records;
        return true;
    }
    if (label == "NEARS") {
        statics.nearest_station = grid_integers(cells, label);
        statics.present = true;
        ++statics.decoded_records;
        return true;
    }
    return false;
}

Calmet21Header header(const std::vector<std::uint8_t>& v, int ncom) {
    check(v.size()>=100U, "missing original control header");
    Calmet21Header h;
    h.comment_records=ncom;
    h.timezone=ascii(v,40U,8U);
    h.irtype=integer32(v,52U);
    h.nx=integer32(v,56U); h.ny=integer32(v,60U); h.nz=integer32(v,64U);
    h.dx_m=real32(v,68U);
    h.origin_x_m=real32(v,72U); h.origin_y_m=real32(v,76U);
    h.wind_code=integer32(v,80U);
    h.surface_stations=integer32(v,84U);
    h.upper_stations=integer32(v,88U);
    h.precipitation_stations=integer32(v,92U);
    check(h.nx>0 && h.ny>0 && h.nz>0 && h.nx<=4096 && h.ny<=4096 &&
          h.nz<=99 && std::int64_t(h.nx)*h.ny<=2000000 &&
          std::isfinite(h.dx_m) && h.dx_m>0 &&
          std::isfinite(h.origin_x_m) && std::isfinite(h.origin_y_m) &&
          !h.timezone.empty() && h.surface_stations>=0 && h.upper_stations>=0 &&
          h.precipitation_stations>=0, "invalid grid or station metadata");
    return h;
}
} // namespace

Calmet21Summary Calmet21Reader::read(const std::string& path,
                                     const Observer& visitor, bool frozen_hefei_2022) {
    FortranRecordReader records(path, 4, RecordByteOrder::LittleEndian);
    std::vector<std::uint8_t> r;
    check(records.next(r), "no signature");
    const std::string sig=ascii(r,0U,std::min(std::size_t(40),r.size()));
    check(sig.find("CALMET.DAT")==0U && sig.find("2.1")!=std::string::npos,
          "unsupported CALMET.DAT signature/version");
    check(records.next(r) && r.size()==4U, "missing count of comments");
    const int ncom=integer32(r,0);
    check(ncom>=0 && ncom<=10000, "invalid comment count");
    for (int n=0; n<ncom; ++n) {
        check(records.next(r) && r.size()==132U, "malformed comment record");
    }
    check(records.next(r), "missing original controls");
    Calmet21Summary result;
    result.header=header(r,ncom);
    const auto& h=result.header;
    check(h.irtype==1 && h.wind_code==1, "unsupported selected output mode");
    const auto labels=expected_labels(h.nz);
    const std::size_t cells=std::size_t(h.nx)*std::size_t(h.ny);
    const std::size_t payload_bytes=24U+4U*cells;
    std::size_t cursor=0;
    std::int64_t previous_hour_end=0;
    std::int64_t current_hour_begin=0, current_hour_end=0;
    while (records.next(r)) {
        // Original CALMET OUTHD includes labelled Z0, terrain, land-use and
        // other static fields. A metadata record may have the SAME byte
        // length as an hourly field, so payload size alone is insufficient.
        // OUTHD/OUTHR source: static header records use zero begin/end clocks.
        if (r.size()<24U) {
            check(result.hourly_fields==0, "short record after hourly fields");
            ++result.metadata_records;
            continue;
        }
        const std::string label=ascii(r,0,8);
        const bool no_time=(integer32(r,8)==0 && integer32(r,16)==0);
        if (no_time && result.hourly_fields==0) {
            check(label!=labels.at(0), "missing timestamp on first U field");
            if (decode_static_record(label, r, h.nx, h.ny, h.nz, result.statics)) continue;
            ++result.metadata_records;
            continue;
        }
        check(r.size()==payload_bytes, "unexpected non-field record size: "+label);
        check(label==labels.at(cursor), "field name/order mismatch: "+label);
        const auto begin=timestamp(integer32(r,8),integer32(r,12));
        const auto end=timestamp(integer32(r,16),integer32(r,20));
        check(end.unix_seconds-begin.unix_seconds==3600,
              "original hourly interval must be exactly one hour");
        if (cursor==0) {
            if (result.intervals==0) result.first_begin=begin;
            else check(begin.unix_seconds==previous_hour_end, "hourly gap/overlap");
            current_hour_begin=begin.unix_seconds;
            current_hour_end=end.unix_seconds;
            ++result.intervals;
        } else {
            check(begin.unix_seconds==current_hour_begin &&
                  end.unix_seconds==current_hour_end,
                  "fields in same hour have different time tags");
        }
        Calmet21Field field;
        field.label=label;
        field.begin=begin;
        field.end=end;
        field.integer=(label=="IPGT" || label=="IRH");
        if (field.integer) {
            field.integer_values.reserve(cells);
            for (std::size_t i=0; i<cells; ++i)
                field.integer_values.push_back(integer32(r,24U+4U*i));
        } else {
            field.real_values.reserve(cells);
            for (std::size_t i=0; i<cells; ++i) {
                const float value=real32(r,24U+4U*i);
                check(std::isfinite(value), "nonfinite real meteorological value in "+label);
                field.real_values.push_back(value);
            }
        }
        if (visitor) visitor(field);
        result.final_end=end;
        ++result.hourly_fields;
        cursor=(cursor+1U)%labels.size();
        if (cursor==0) previous_hour_end=current_hour_end;
    }
    check(result.intervals>0 && cursor==0 &&
          result.hourly_fields==result.intervals*labels.size(),
          "incomplete hourly field group");
    if (frozen_hefei_2022) {
        check(h.nx==50 && h.ny==50 && h.nz==9 && h.timezone=="UTC+0000" &&
              h.surface_stations>=1 && h.upper_stations>=1 &&
              h.precipitation_stations==0 && std::abs(h.dx_m-100.0F)<0.0001F,
              "Hefei 2022 grid/forcing outside selected P7 scope");
        check(result.intervals==143 &&
              result.first_begin.unix_seconds==timestamp(202200100,0).unix_seconds &&
              result.final_end.unix_seconds==timestamp(202200623,0).unix_seconds,
              "Hefei 2022 expected exactly 143 original hourly intervals");
    }
    return result;
}
} // namespace cteas::puff
