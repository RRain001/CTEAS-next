#include "cteas/puff/conc_file.hpp"

#include "cteas/puff/fortran_records.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::puff {
namespace {

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7E conc file: " + message);
}

std::string padded(std::string value, std::size_t width, const std::string& what) {
    require_true(value.size() <= width, what + " is longer than " + std::to_string(width) + " characters");
    value.resize(width, ' ');
    return value;
}

void append_bytes(std::vector<std::uint8_t>& buffer, const void* data, std::size_t size) {
    const auto* bytes = static_cast<const std::uint8_t*>(data);
    buffer.insert(buffer.end(), bytes, bytes + size);
}

void append_int(std::vector<std::uint8_t>& buffer, std::int32_t value) {
    append_bytes(buffer, &value, sizeof(value));
}

void append_float(std::vector<std::uint8_t>& buffer, float value) {
    append_bytes(buffer, &value, sizeof(value));
}

// Sequential-unformatted framing: 4-byte marker, payload, 4-byte trailer.
void write_framed(std::ostream& out, const std::vector<std::uint8_t>& payload) {
    const std::int32_t marker = static_cast<std::int32_t>(payload.size());
    out.write(reinterpret_cast<const char*>(&marker), sizeof(marker));
    out.write(reinterpret_cast<const char*>(payload.data()),
              static_cast<std::streamsize>(payload.size()));
    out.write(reinterpret_cast<const char*>(&marker), sizeof(marker));
    require_true(bool(out), "failed to write a sequential-unformatted record");
}

bool valid_period(int year, int julian, int hour, int seconds) {
    return year >= 1900 && year <= 2100 && julian >= 1 && julian <= 366 && hour >= 0 && hour <= 23 &&
           seconds >= 0 && seconds <= 3600;
}

bool valid_date(int packed) {
    const int year = packed / 100000;
    const int day = (packed % 100000) / 100;
    const int hour = packed % 100;
    return year >= 1900 && year <= 2100 && day >= 1 && day <= 366 && hour >= 0 && hour <= 24;
}

} // namespace

struct ConcFileWriter::Impl {
    std::ofstream stream;
    bool closed = false;
};

ConcFileWriter::ConcFileWriter(const std::string& path, std::string data_version,
                               std::string model_version, std::vector<std::string> comments)
    : impl_(new Impl()) {
    impl_->stream.open(path, std::ios::binary | std::ios::trunc);
    require_true(bool(impl_->stream), "cannot create " + path);

    // Version record: 'CONC.DAT' label plus data and model version strings, the
    // same shape and size (96 bytes) as the vendor WROUT1 version record.
    std::vector<std::uint8_t> version;
    const std::string label = padded("CONC.DAT", 16U, "concentration file label");
    append_bytes(version, label.data(), label.size());
    const std::string data = padded(std::move(data_version), 16U, "data version");
    append_bytes(version, data.data(), data.size());
    const std::string model = padded(std::move(model_version), 64U, "model version");
    append_bytes(version, model.data(), model.size());
    require_true(version.size() == 96U, "version record must be 96 bytes");
    write_framed(impl_->stream, version);

    std::vector<std::uint8_t> count;
    append_int(count, static_cast<std::int32_t>(comments.size()));
    write_framed(impl_->stream, count);

    for (const auto& comment : comments) {
        std::vector<std::uint8_t> line;
        const std::string text = padded(comment, 132U, "comment record");
        append_bytes(line, text.data(), text.size());
        write_framed(impl_->stream, line);
    }
}

ConcFileWriter::~ConcFileWriter() {
    if (impl_ != nullptr) {
        if (!impl_->closed) impl_->stream.flush();
        delete impl_;
    }
}

void ConcFileWriter::write_record(const ConcRecord& record) {
    require_true(impl_ != nullptr && !impl_->closed, "writer is closed");
    validate_conc_record(record);
    std::vector<std::uint8_t> payload;
    const std::string label = padded(record.label, 8U, "record label");
    append_bytes(payload, label.data(), label.size());
    append_int(payload, record.begin_date);
    append_int(payload, record.begin_seconds);
    append_int(payload, record.end_date);
    append_int(payload, record.end_seconds);
    payload.reserve(payload.size() + record.values.size() * sizeof(float));
    for (const float value : record.values) append_float(payload, value);
    write_framed(impl_->stream, payload);
    ++records_written_;
}

void ConcFileWriter::write_period_record(const ConcPeriod& period) {
    require_true(impl_ != nullptr && !impl_->closed, "writer is closed");
    const auto valid = [](int year, int julian, int hour, int seconds) {
        return year >= 1900 && year <= 2100 && julian >= 1 && julian <= 366 && hour >= 0 &&
               hour <= 23 && seconds >= 0 && seconds <= 3600;
    };
    require_true(valid(period.begin_year, period.begin_julian, period.begin_hour, period.begin_seconds),
                 "invalid begin period");
    require_true(valid(period.end_year, period.end_julian, period.end_hour, period.end_seconds),
                 "invalid end period");
    std::vector<std::uint8_t> payload;
    for (const int value : {period.begin_year, period.begin_julian, period.begin_hour,
                            period.begin_seconds, period.end_year, period.end_julian,
                            period.end_hour, period.end_seconds}) {
        append_int(payload, value);
    }
    write_framed(impl_->stream, payload);
    ++records_written_;
}

ConcGridDescriptor original_met_grid_descriptor(
    float origin_x_m, float origin_y_m, int discrete_receptors) {
    require_true(std::isfinite(origin_x_m) && std::isfinite(origin_y_m),
                 "original MET.DAT grid origin must be finite");
    require_true(discrete_receptors >= 0,
                 "original discrete receptor count must not be negative");
    constexpr float kOriginalMetresToKm = 0.001F;
    ConcGridDescriptor result;
    result.discrete_receptors = discrete_receptors;
    result.group_index = 1;
    result.group_name = "TOTAL";
    // Preserve original REAL*4 multiply, not double or text conversion.
    result.x_origin_km = static_cast<double>(origin_x_m * kOriginalMetresToKm);
    result.y_origin_km = static_cast<double>(origin_y_m * kOriginalMetresToKm);
    return result;
}

ConcSourceDescriptor original_total_source_descriptor(float origin_x_m,float origin_y_m) {
    const auto legacy=original_met_grid_descriptor(origin_x_m,origin_y_m);
    return {0,1,"TOTAL",legacy.x_origin_km,legacy.y_origin_km};
}

void ConcFileWriter::write_source_descriptor(const ConcSourceDescriptor& source) {
    require_true(impl_!=nullptr && !impl_->closed,"writer is closed");
    require_true(source.source_type>=0 && source.source_type<=8,
                 "invalid OUTPUT source KTYPE");
    require_true(source.source_index>=1,
                 "invalid OUTPUT source KSOURCE");
    require_true(!source.source_name.empty() && source.source_name.size()<=16U,
                 "invalid OUTPUT source CSRCNAM");
    require_true(std::isfinite(source.x_map_km) && std::isfinite(source.y_map_km),
                 "invalid OUTPUT source XY coordinates");
    if(source.source_type==0)
        require_true(source.source_index==1 && source.source_name=="TOTAL",
                     "TOTAL must have KTYPE=0 KSOURCE=1 name TOTAL");
    std::vector<std::uint8_t> payload;
    append_int(payload,source.source_type);
    append_int(payload,source.source_index);
    const auto name=padded(source.source_name,16U,"source name");
    append_bytes(payload,name.data(),name.size());
    append_float(payload,static_cast<float>(source.x_map_km));
    append_float(payload,static_cast<float>(source.y_map_km));
    require_true(payload.size()==32U,"OUTPUT source descriptor must be 32 bytes");
    write_framed(impl_->stream,payload);
    ++records_written_;
}

std::vector<std::string> original_wrout1_embedded_comments(
    const std::string& active_puff_control,
    const std::string& calmet_dat_path) {
    if(active_puff_control.empty())
        throw std::invalid_argument("WROUT1 embedded controls cannot be empty");
    std::vector<std::string> comments;
    comments.emplace_back("Produced by CALPUFF Version: 7.2.1  Level: 150618");
    comments.emplace_back(
        "Internal Coordinate Transformations  ---  COORDLIB   Version: 1.99   Level: 070921");
    std::istringstream control(active_puff_control);
    std::string line;
    while(std::getline(control,line)) {
        if(!line.empty() && line.back()=='\r')line.pop_back();
        require_true(line.size()<=132U,"WROUT1 raw control line too wide");
        comments.push_back(line);
    }
    FortranRecordReader met(calmet_dat_path,4,RecordByteOrder::LittleEndian);
    std::vector<std::uint8_t> raw;
    require_true(met.next(raw) && raw.size()==96U &&
                 std::string(reinterpret_cast<const char*>(raw.data()),10U)
                     =="CALMET.DAT",
                 "WROUT1 requires CALMET.DAT version record from source MET");
    std::string met_header(reinterpret_cast<const char*>(raw.data()),raw.size());
    met_header.erase(met_header.find_last_not_of(' ')+1);
    require_true(met.next(raw) && raw.size()==4U,
                 "WROUT1 expected MET.DAT embedded comment-count record");
    std::int32_t ncomments=0;
    std::memcpy(&ncomments,raw.data(),sizeof(ncomments));
    require_true(ncomments>0 && ncomments<100000,
                 "WROUT1 MET.DAT embedded comment count invalid");
    comments.emplace_back("");
    comments.emplace_back(132,'.');
    comments.emplace_back("");
    comments.emplace_back(std::move(met_header));
    for(std::int32_t i=0;i<ncomments;++i) {
        require_true(met.next(raw) && raw.size()==132U,
                     "WROUT1 MET.DAT embedded comment payload width drift");
        comments.emplace_back(reinterpret_cast<const char*>(raw.data()),
                              raw.size());
    }
    return comments;
}

void ConcFileWriter::write_original_wrout1_general_header(
    const OriginalWrout1GeneralHeader& h) {
    require_true(impl_!=nullptr && !impl_->closed,"writer is closed");
    require_true(h.start[0]>=1900 && h.start[0]<=2100 &&
                 h.start[1]>=1 && h.start[1]<=366 &&
                 h.start[2]>=0 && h.start[2]<=23 &&
                 h.start[3]>=0 && h.start[3]<=3600,
                 "WROUT1 general header invalid start date");
    require_true(h.timing_grid[0]>0 && h.timing_grid[2]>0 &&
                 h.timing_grid[3]>0 && h.timing_grid[4]>0 &&
                 h.options[10]==13,
                 "WROUT1 general header unsupported grid/source groups");
    std::vector<std::uint8_t> body;
    const auto chars=[&](const std::string& value,
                         std::size_t width,const char* what) {
        const auto text=padded(value,width,what);
        append_bytes(body,text.data(),text.size());
    };
    chars(h.model,12,"WROUT1 model");
    chars(h.model_version,12,"WROUT1 version");
    chars(h.model_level,12,"WROUT1 level");
    for(const auto value:h.start)append_int(body,value);
    chars(h.timezone,8,"WROUT1 timezone");
    for(const auto value:h.timing_grid)append_int(body,value);
    for(const auto value:h.spacing_km){
        require_true(std::isfinite(value)&&value>0.0F,
                     "WROUT1 spacing invalid");
        append_float(body,value);
    }
    append_int(body,h.original_one);
    for(const auto value:h.met_origins_km){
        require_true(std::isfinite(value),"WROUT1 MET origin invalid");
        append_float(body,value);
    }
    for(const auto value:h.options)append_int(body,value);
    for(const auto value:h.projection){
        require_true(std::isfinite(value),"WROUT1 projection invalid");
        append_float(body,value);
    }
    chars(h.pmap,8,"WROUT1 PMAP");
    chars(h.utmhem,4,"WROUT1 UTMHEM");
    chars(h.datum,8,"WROUT1 DATUM");
    chars(h.datum_epoch,12,"WROUT1 DATEN");
    for(const auto& text:h.latlon_labels)
        chars(text,16,"WROUT1 raw latitude/longitude");
    require_true(body.size()==300U,
                 "WROUT1 source-ordered general header not 300 bytes");
    write_framed(impl_->stream,body);
    ++records_written_;
}

void ConcFileWriter::write_original_wrout1_source_type_counts(
    const std::array<std::int32_t,13>& counts) {
    require_true(impl_!=nullptr && !impl_->closed,"writer is closed");
    std::vector<std::uint8_t> payload;
    payload.reserve(counts.size()*sizeof(std::int32_t));
    for(const auto count:counts) {
        require_true(count>=0,"WROUT1 negative source type count");
        append_int(payload,count);
    }
    require_true(payload.size()==52U,"WROUT1 13 INTEGER*4 source counters invalid");
    write_framed(impl_->stream,payload);
    ++records_written_;
}

void ConcFileWriter::write_original_wrout1_identity(
    const OriginalWrout1Identity& item) {
    require_true(impl_!=nullptr && !impl_->closed,"writer is closed");
    require_true(!item.species_name.empty() && item.species_name.size()<=8,
                 "WROUT1 species A8 invalid");
    require_true(item.species_index>=1 && item.species_index<=9999999,
                 "WROUT1 species I7 invalid");
    require_true(!item.concentration_units.empty() &&
                 item.concentration_units.size()<=16,
                 "WROUT1 unit A16 invalid");
    require_true(item.source_identifier>=1,
                 "WROUT1 source identifier invalid");
    require_true(!item.source_name.empty() && item.source_name.size()<=16,
                 "WROUT1 source name A16 invalid");
    for(const auto& line:item.run_titles)
        require_true(line.size()<=80,"WROUT1 title A80 too long");
    // Stage and validate ALL payloads before the first sequential write.
    std::array<std::vector<std::uint8_t>,4> records;
    for(const auto& title:item.run_titles){
        const auto line=padded(title,80,"WROUT1 title");
        append_bytes(records[0],line.data(),line.size());
    }
    const auto label=padded(item.species_name,8,"WROUT1 species");
    append_bytes(records[1],label.data(),label.size());
    std::string species_index=std::to_string(item.species_index);
    species_index.insert(0,7-species_index.size(),' ');
    append_bytes(records[1],species_index.data(),species_index.size());
    const auto units=padded(item.concentration_units,16,"WROUT1 units");
    append_bytes(records[2],units.data(),units.size());
    append_int(records[3],item.source_identifier);
    const auto source=padded(item.source_name,16,"WROUT1 source");
    append_bytes(records[3],source.data(),source.size());
    require_true(records[0].size()==240 && records[1].size()==15 &&
                 records[2].size()==16 && records[3].size()==20,
                 "WROUT1 identity payload width drift");
    for(const auto& rec:records){
        write_framed(impl_->stream,rec);
        ++records_written_;
    }
}

void ConcFileWriter::write_grid_descriptor(const ConcGridDescriptor& descriptor) {
    // Backward-compatible TOTAL-only alias. These fields NEVER describe
    // receptor grid dimensions in vendor OUTPUT L57912-57913.
    require_true(descriptor.discrete_receptors==0 &&
                 descriptor.group_index==1 && descriptor.group_name=="TOTAL",
                 "legacy TOTAL descriptor cannot represent individual source");
    write_source_descriptor({0,1,"TOTAL",
        descriptor.x_origin_km,descriptor.y_origin_km});
}

void ConcFileWriter::write_species_field(const std::string& label, int species_index, int nx, int ny,
                                        const std::vector<float>& values) {
    require_true(impl_ != nullptr && !impl_->closed, "writer is closed");
    require_true(species_index >= 1, "species index must be at least 1");
    require_true(nx > 0 && ny > 0, "field dimensions must be positive");
    const auto expected = static_cast<std::size_t>(nx) * static_cast<std::size_t>(ny);
    require_true(values.size() == expected,
                 "field holds " + std::to_string(values.size()) + " values, expected " +
                     std::to_string(expected));
    for (const float value : values) {
        require_true(std::isfinite(value), "field values must be finite");
    }
    std::vector<std::uint8_t> payload;
    const std::string name = padded(label, 8U, "species label");
    append_bytes(payload, name.data(), name.size());
    // Original WROUT1 writes an I7 numeric field, right-justified with
    // LEADING spaces. Padded("1",7) used to left-justify it ("1      "),
    // which escaped structure-only CONC.DAT tests but changes the bytes.
    std::string index = std::to_string(species_index);
    require_true(index.size() <= 7U, "species index exceeds original I7 field");
    index.insert(0U, 7U - index.size(), ' ');
    append_bytes(payload, index.data(), index.size());
    payload.reserve(payload.size() + values.size() * sizeof(float));
    for (const float value : values) append_float(payload, value);
    write_framed(impl_->stream, payload);
    ++records_written_;
}

void ConcFileWriter::close() {
    if (impl_ == nullptr || impl_->closed) return;
    impl_->stream.close();
    require_true(!impl_->stream.fail(), "failed to close the concentration file");
    impl_->closed = true;
}

void validate_conc_record(const ConcRecord& record) {
    require_true(!record.label.empty() && record.label.size() <= 8U,
                 "record label must be 1 to 8 characters");
    require_true(valid_date(record.begin_date), "invalid begin date YYYYJJJHH");
    require_true(valid_date(record.end_date), "invalid end date YYYYJJJHH");
    require_true(record.begin_seconds >= 0 && record.begin_seconds <= 3600,
                 "begin seconds must be in 0..3600");
    require_true(record.end_seconds >= 0 && record.end_seconds <= 3600,
                 "end seconds must be in 0..3600");
    require_true(record.end_date > record.begin_date ||
                     (record.end_date == record.begin_date &&
                      record.end_seconds >= record.begin_seconds),
                 "record end time must not precede its begin time");
    for (const float value : record.values) {
        require_true(std::isfinite(value), "record values must be finite");
    }
}

void validate_conc_field(const ConcRecord& record, int nx, int ny) {
    require_true(nx > 0 && ny > 0, "field dimensions must be positive");
    validate_conc_record(record);
    const auto expected = static_cast<std::size_t>(nx) * static_cast<std::size_t>(ny);
    require_true(record.values.size() == expected,
                 "field record holds " + std::to_string(record.values.size()) + " values, expected " +
                     std::to_string(expected));
}

ConcFileSummary summarize_conc_file(const std::string& path) {
    FortranRecordReader reader(path, 4, RecordByteOrder::LittleEndian);
    ConcFileSummary summary;
    std::vector<std::uint8_t> record;
    bool first_period = true;
    while (reader.next(record)) {
        ++summary.records;
        summary.bytes += record.size() + 8U;
        summary.record_sizes.push_back(record.size());
        const auto int_at = [&record](std::size_t offset) {
            std::int32_t value = 0;
            std::memcpy(&value, record.data() + offset, sizeof(value));
            return value;
        };
        if (record.size() == 32U) {
            // (year, julian, hour, seconds) x2 = the sampling period record, or
            // (nrec, group index, 'TOTAL', XORIGKM, YORIGKM) = the grid descriptor.
            const bool period = valid_period(int_at(0), int_at(4), int_at(8), int_at(12)) &&
                                valid_period(int_at(16), int_at(20), int_at(24), int_at(28));
            if (period) {
                ++summary.period_records;
                if (first_period) {
                    summary.first_begin_date = int_at(0) * 1000 + int_at(4);
                    first_period = false;
                }
                summary.last_end_date = int_at(16) * 1000 + int_at(20);
                continue;
            }
            std::string name(reinterpret_cast<const char*>(record.data() + 8U), 16U);
            if (name.rfind("TOTAL", 0U) == 0U) {
                ++summary.grid_records;
                continue;
            }
        }
        if (record.size() >= 15U) {
            const std::string label(reinterpret_cast<const char*>(record.data()), 8U);
            const std::size_t values = record.size() - 15U;
            if (values > 0U && values % sizeof(float) == 0U && !label.empty() &&
                label.find_first_not_of(" ") != std::string::npos) {
                ++summary.species_field_records;
                summary.species_field_sizes.push_back(record.size());
                const auto found = std::find_if(
                    summary.species_field_counts.begin(), summary.species_field_counts.end(),
                    [&label](const auto& entry) { return entry.first == label; });
                if (found == summary.species_field_counts.end()) {
                    summary.species_field_counts.emplace_back(label, 1U);
                } else {
                    ++found->second;
                }
                continue;
            }
        }
        ++summary.unframed_records;
        const std::string key = record.size() >= 8U
                                    ? std::string(reinterpret_cast<const char*>(record.data()), 8U)
                                    : std::string("<short>");
        const auto found = std::find_if(summary.label_counts.begin(), summary.label_counts.end(),
                                        [&key](const auto& entry) { return entry.first == key; });
        if (found == summary.label_counts.end()) {
            summary.label_counts.emplace_back(key, 1U);
        } else {
            ++found->second;
        }
    }
    require_true(summary.records > 0U, "no records found in " + path);
    return summary;
}

std::vector<ConcRecord> read_conc_records(const std::string& path) {
    FortranRecordReader reader(path, 4, RecordByteOrder::LittleEndian);
    std::vector<ConcRecord> records;
    std::vector<std::uint8_t> record;
    while (reader.next(record)) {
        if (record.size() < 24U) continue;
        ConcRecord parsed;
        parsed.label.assign(reinterpret_cast<const char*>(record.data()), 8U);
        std::int32_t begin = 0, begin_seconds = 0, end = 0, end_seconds = 0;
        std::memcpy(&begin, record.data() + 8U, sizeof(begin));
        std::memcpy(&begin_seconds, record.data() + 12U, sizeof(begin_seconds));
        std::memcpy(&end, record.data() + 16U, sizeof(end));
        std::memcpy(&end_seconds, record.data() + 20U, sizeof(end_seconds));
        if (!valid_date(begin) || !valid_date(end)) continue;
        parsed.begin_date = begin;
        parsed.begin_seconds = begin_seconds;
        parsed.end_date = end;
        parsed.end_seconds = end_seconds;
        const std::size_t values = (record.size() - 24U) / sizeof(float);
        parsed.values.resize(values);
        if (values > 0U) {
            std::memcpy(parsed.values.data(), record.data() + 24U, values * sizeof(float));
        }
        records.push_back(std::move(parsed));
    }
    require_true(!records.empty(), "no framed records found in " + path);
    return records;
}

std::vector<ConcPeriod> read_conc_periods(const std::string& path) {
    FortranRecordReader reader(path, 4, RecordByteOrder::LittleEndian);
    std::vector<ConcPeriod> periods;
    std::vector<std::uint8_t> record;
    while (reader.next(record)) {
        if (record.size() != 32U) continue;
        const auto int_at = [&record](std::size_t offset) {
            std::int32_t value = 0;
            std::memcpy(&value, record.data() + offset, sizeof(value));
            return value;
        };
        if (!valid_period(int_at(0), int_at(4), int_at(8), int_at(12)) ||
            !valid_period(int_at(16), int_at(20), int_at(24), int_at(28))) {
            continue;
        }
        ConcPeriod period;
        period.begin_year = int_at(0);
        period.begin_julian = int_at(4);
        period.begin_hour = int_at(8);
        period.begin_seconds = int_at(12);
        period.end_year = int_at(16);
        period.end_julian = int_at(20);
        period.end_hour = int_at(24);
        period.end_seconds = int_at(28);
        periods.push_back(period);
    }
    require_true(!periods.empty(), "no sampling period records found in " + path);
    return periods;
}

std::vector<ConcSpeciesField> read_conc_species_fields(const std::string& path, int nx, int ny) {
    require_true(nx > 0 && ny > 0, "expected field dimensions must be positive");
    const auto expected = static_cast<std::size_t>(nx) * static_cast<std::size_t>(ny);
    FortranRecordReader reader(path, 4, RecordByteOrder::LittleEndian);
    std::vector<ConcSpeciesField> fields;
    std::vector<std::uint8_t> record;
    while (reader.next(record)) {
        if (record.size() != 15U + expected * sizeof(float)) continue;
        ConcSpeciesField field;
        field.label.assign(reinterpret_cast<const char*>(record.data()), 8U);
        std::string index(reinterpret_cast<const char*>(record.data() + 8U), 7U);
        const auto first = index.find_first_not_of(" \t");
        require_true(first != std::string::npos, "species field index is blank");
        const auto last = index.find_last_not_of(" \t");
        const std::string digits = index.substr(first, last - first + 1);
        int parsed = 0;
        const auto [end, error] = std::from_chars(digits.data(), digits.data() + digits.size(), parsed);
        require_true(end == digits.data() + digits.size() && error == std::errc{},
                     "species field index is not an integer: " + digits);
        field.species_index = parsed;
        field.values.resize(expected);
        std::memcpy(field.values.data(), record.data() + 15U, expected * sizeof(float));
        fields.push_back(std::move(field));
    }
    require_true(!fields.empty(), "no species field records of the expected size found in " + path);
    return fields;
}

} // namespace cteas::puff
