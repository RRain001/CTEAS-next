// P6F input adapter for the P6D real-case wind-field array product.
#include "cteas/p6f/p6d_fields.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iterator>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::p6f {
namespace {

constexpr const char* kPrefix = "P6F P6D fields ";

[[noreturn]] void fail(const std::string& message) {
    throw std::invalid_argument(std::string(kPrefix) + message);
}
void require(bool condition, const std::string& message) {
    if(!condition)fail(message);
}

// ------------------------------------------------------------- minimal JSON
// Just enough JSON (RFC 8259) to read a metadata document, with explicit
// failure instead of a silent guess. Duplicate keys, trailing garbage, deep
// nesting, truncated input and unsupported escapes are all rejected.
struct JsonValue {
    enum class Kind { null_value, boolean, number, string, array, object };
    Kind kind = Kind::null_value;
    bool boolean = false;
    double number = 0.0;
    std::string text;
    std::vector<JsonValue> array;
    std::vector<std::pair<std::string, JsonValue>> object;

    const JsonValue* find(const std::string& key) const {
        for(const auto& entry : object)
            if(entry.first == key)return &entry.second;
        return nullptr;
    }
};

struct JsonReader {
    const std::string& text;
    std::size_t at = 0;
    int depth = 0;

    void skip_space() {
        while(at < text.size() &&
              (text[at] == ' ' || text[at] == '\t' || text[at] == '\n' ||
               text[at] == '\r'))
            ++at;
    }
    char peek() {
        require(at < text.size(), "unexpected end of JSON document");
        return text[at];
    }
    void expect(char c) {
        require(at < text.size() && text[at] == c,
                std::string("expected '") + c + "' in JSON document");
        ++at;
    }
    JsonValue parse_value() {
        require(++depth <= 32, "JSON nesting is too deep");
        skip_space();
        const char c = peek();
        JsonValue value;
        if(c == '{') {
            value.kind = JsonValue::Kind::object;
            ++at;
            skip_space();
            if(peek() == '}') {
                ++at;
            } else {
                while(true) {
                    skip_space();
                    const std::string key = parse_string();
                    require(value.find(key) == nullptr,
                            "duplicate JSON key " + key);
                    skip_space();
                    expect(':');
                    value.object.emplace_back(key, parse_value());
                    skip_space();
                    const char next = peek();
                    if(next == ',') {
                        ++at;
                        continue;
                    }
                    expect('}');
                    break;
                }
            }
        } else if(c == '[') {
            value.kind = JsonValue::Kind::array;
            ++at;
            skip_space();
            if(peek() == ']') {
                ++at;
            } else {
                while(true) {
                    value.array.push_back(parse_value());
                    skip_space();
                    const char next = peek();
                    if(next == ',') {
                        ++at;
                        continue;
                    }
                    expect(']');
                    break;
                }
            }
        } else if(c == '"') {
            value.kind = JsonValue::Kind::string;
            value.text = parse_string();
        } else if(text.compare(at, 4U, "true") == 0) {
            at += 4U;
            value.kind = JsonValue::Kind::boolean;
            value.boolean = true;
        } else if(text.compare(at, 5U, "false") == 0) {
            at += 5U;
            value.kind = JsonValue::Kind::boolean;
            value.boolean = false;
        } else if(text.compare(at, 4U, "null") == 0) {
            at += 4U;
            value.kind = JsonValue::Kind::null_value;
        } else {
            const char* start = text.c_str() + at;
            char* end = nullptr;
            const double number = std::strtod(start, &end);
            require(end != start && end != nullptr, "invalid JSON value");
            require(std::isfinite(number), "non-finite JSON number");
            at += static_cast<std::size_t>(end - start);
            value.kind = JsonValue::Kind::number;
            value.number = number;
        }
        --depth;
        return value;
    }
    std::string parse_string() {
        expect('"');
        std::string out;
        while(true) {
            require(at < text.size(), "unterminated JSON string");
            const char c = text[at++];
            if(c == '"')break;
            if(c != '\\') {
                require(static_cast<unsigned char>(c) >= 0x20U,
                        "control character in JSON string");
                out.push_back(c);
                continue;
            }
            require(at < text.size(), "unterminated JSON escape");
            const char escape = text[at++];
            switch(escape) {
            case '"': out.push_back('"'); break;
            case '\\': out.push_back('\\'); break;
            case '/': out.push_back('/'); break;
            case 'b': out.push_back('\b'); break;
            case 'f': out.push_back('\f'); break;
            case 'n': out.push_back('\n'); break;
            case 'r': out.push_back('\r'); break;
            case 't': out.push_back('\t'); break;
            case 'u': {
                require(at + 4U <= text.size(), "truncated \\u escape");
                unsigned code = 0;
                for(int k = 0; k < 4; ++k) {
                    const char digit = text[at + static_cast<std::size_t>(k)];
                    code <<= 4U;
                    if(digit >= '0' && digit <= '9')code |= unsigned(digit - '0');
                    else if(digit >= 'a' && digit <= 'f')code |= unsigned(digit - 'a' + 10);
                    else if(digit >= 'A' && digit <= 'F')code |= unsigned(digit - 'A' + 10);
                    else fail("invalid \\u escape in JSON string");
                }
                at += 4U;
                // UTF-8 encoding of a BMP code point.
                if(code < 0x80U) {
                    out.push_back(static_cast<char>(code));
                } else if(code < 0x800U) {
                    out.push_back(static_cast<char>(0xc0U | (code >> 6U)));
                    out.push_back(static_cast<char>(0x80U | (code & 0x3fU)));
                } else {
                    out.push_back(static_cast<char>(0xe0U | (code >> 12U)));
                    out.push_back(static_cast<char>(0x80U | ((code >> 6U) & 0x3fU)));
                    out.push_back(static_cast<char>(0x80U | (code & 0x3fU)));
                }
                break;
            }
            default:
                fail("unsupported JSON escape");
            }
        }
        return out;
    }
};

JsonValue parse_json_document(const std::string& path) {
    std::ifstream input(path, std::ios::binary);
    if(!input)fail("cannot open " + path);
    const std::string text((std::istreambuf_iterator<char>(input)),
                           std::istreambuf_iterator<char>());
    require(!text.empty(), path + " is empty");
    JsonReader reader{text};
    JsonValue root = reader.parse_value();
    reader.skip_space();
    require(reader.at == text.size(), "trailing content after the JSON document");
    return root;
}

const JsonValue& member(const JsonValue& object, const std::string& key,
                        const std::string& what) {
    require(object.kind == JsonValue::Kind::object, what + " must be an object");
    const JsonValue* value = object.find(key);
    require(value != nullptr, what + " is missing the key '" + key + "'");
    return *value;
}
std::string as_string(const JsonValue& value, const std::string& what) {
    require(value.kind == JsonValue::Kind::string, what + " must be a string");
    return value.text;
}
double as_number(const JsonValue& value, const std::string& what) {
    require(value.kind == JsonValue::Kind::number, what + " must be a number");
    return value.number;
}
int as_int(const JsonValue& value, const std::string& what) {
    const double number = as_number(value, what);
    require(number == std::floor(number) &&
                number >= -2147483648.0 && number <= 2147483647.0,
            what + " must be an integer");
    return static_cast<int>(number);
}
float as_float(const JsonValue& value, const std::string& what) {
    const double number = as_number(value, what);
    require(std::isfinite(number) &&
                std::abs(number) <=
                    static_cast<double>(std::numeric_limits<float>::max()),
            what + " is out of float range");
    return static_cast<float>(number);
}

// Layout/dtype spellings this adapter can read. Anything else is rejected with
// the value it found, never silently reinterpreted.
bool is_i_fastest_layout(const std::string& raw) {
    std::string text;
    for(const char c : raw)
        text.push_back(c == '-' ? '_' : static_cast<char>(std::tolower(
                                                    static_cast<unsigned char>(c))));
    return text == "i_fastest" || text == "ifastest" || text == "i_fastest_index";
}
bool is_little_endian(const std::string& raw) {
    std::string text;
    for(const char c : raw)
        text.push_back(static_cast<char>(
            std::tolower(static_cast<unsigned char>(c))));
    return text == "little" || text == "le" || text == "lsb" ||
           text == "little_endian" || text == "little-endian";
}
bool is_float32_dtype(const std::string& raw) {
    std::string text;
    for(const char c : raw)
        text.push_back(c == '-' ? '_' : static_cast<char>(std::tolower(
                                                    static_cast<unsigned char>(c))));
    return text == "float32" || text == "f32" || text == "float" ||
           text == "little_endian_float32" || text == "float32_le";
}

// YYYY-MM-DD_HH, the P6D hourly label.
void parse_p6d_label(const std::string& label, int& year, int& month, int& day,
                     int& hour) {
    const auto digits = [&label](std::size_t at, std::size_t count) {
        require(at + count <= label.size(), "malformed hourly label " + label);
        int value = 0;
        for(std::size_t k = 0; k < count; ++k) {
            const char c = label[at + k];
            require(c >= '0' && c <= '9', "malformed hourly label " + label);
            value = value * 10 + (c - '0');
        }
        return value;
    };
    require(label.size() == 13U && label[4] == '-' && label[7] == '-' &&
                label[10] == '_',
            "malformed hourly label " + label +
                ": expected YYYY-MM-DD_HH");
    year = digits(0U, 4U);
    month = digits(5U, 2U);
    day = digits(8U, 2U);
    hour = digits(11U, 2U);
    require(hour <= 23, "malformed hourly label " + label);
}

std::string trim_text(const std::string& text) {
    const auto first = text.find_first_not_of(' ');
    if(first == std::string::npos)return std::string();
    const auto last = text.find_last_not_of(' ');
    return text.substr(first, last - first + 1U);
}

bool variant_ok(const std::string& variant) {
    // Producer prefixes that name a gridded U/V plane pair. `inter2` is the
    // P6D pre-tail INTER2 field (formerly published as `blend`), `blend` is the
    // closed DIAGNO field. `windbc_*` is deliberately absent: its planes are
    // stitched lateral boundaries with a nx*2*ny / nz*2*nx layout, not a grid.
    return variant == "wind1" || variant == "blend" ||
           variant == "slope_corrected" || variant == "inter2";
}

}  // namespace

// ------------------------------------------------------------------ readers
P6dFieldsMetadata read_p6d_fields_metadata(const std::string& metadata_path) {
    const JsonValue root = parse_json_document(metadata_path);
    P6dFieldsMetadata metadata;
    const JsonValue& grid = member(root, "grid", "metadata");
    metadata.nx = as_int(member(grid, "nx", "grid"), "grid.nx");
    metadata.ny = as_int(member(grid, "ny", "grid"), "grid.ny");
    metadata.nz = as_int(member(grid, "nz", "grid"), "grid.nz");
    require(metadata.nx >= 1 && metadata.ny >= 1 && metadata.nz >= 1,
            "grid extents must be positive");
    metadata.grid_spacing_m =
        as_float(member(grid, "grid_spacing_m", "grid"), "grid.grid_spacing_m");
    metadata.layout = as_string(member(grid, "layout", "grid"), "grid.layout");
    metadata.dtype = as_string(member(grid, "dtype", "grid"), "grid.dtype");
    require(is_i_fastest_layout(metadata.layout),
            "unsupported grid.layout '" + metadata.layout +
                "': this adapter implements the documented i-fastest index "
                "i + nx*(j + ny*k)");
    require(is_float32_dtype(metadata.dtype),
            "unsupported grid.dtype '" + metadata.dtype +
                "': this adapter reads raw little-endian float32 planes");
    if(const JsonValue* order = grid.find("byte_order")) {
        const std::string text = as_string(*order, "grid.byte_order");
        require(is_little_endian(text),
                "unsupported grid.byte_order '" + text +
                    "': this adapter reads little-endian planes");
    }
    const JsonValue& levels = member(root, "levels", "metadata");
    const JsonValue* faces = levels.find("zface_m");
    require(faces != nullptr && faces->kind == JsonValue::Kind::array,
            "metadata.levels.zface_m must be an array");
    for(const JsonValue& value : faces->array)
        metadata.zface_m.push_back(as_float(value, "levels.zface_m"));
    require(metadata.zface_m.size() ==
                static_cast<std::size_t>(metadata.nz) + 1U,
            "metadata.levels.zface_m must hold NZ+1 faces");
    if(const JsonValue* sentinel = root.find("missing_sentinel"))
        metadata.missing_sentinel = as_float(*sentinel, "missing_sentinel");
    if(const JsonValue* hour_label = root.find("hour_label")) {
        const std::string text = as_string(*hour_label, "hour_label");
        std::string folded;
        for(const char c : text)
            folded.push_back(static_cast<char>(
                std::tolower(static_cast<unsigned char>(c))));
        require(folded == "end" || folded == "start",
                "metadata.hour_label must be START or END, found '" + text + "'");
        metadata.label_is_interval_end = folded == "end";
    }
    if(const JsonValue* labels = root.find("hourly_labels")) {
        if(labels->kind == JsonValue::Kind::array) {
            for(const JsonValue& value : labels->array)
                metadata.hourly_labels.push_back(
                    as_string(value, "hourly_labels"));
        } else {
            metadata.hourly_label_count =
                as_int(*labels, "hourly_labels (count)");
            require(metadata.hourly_label_count >= 1,
                    "metadata.hourly_labels count must be positive");
        }
    }
    if(const JsonValue* product = root.find("product"))
        metadata.product = as_string(*product, "product");
    if(const JsonValue* status = root.find("status"))
        metadata.status = as_string(*status, "status");
    if(const JsonValue* blend = root.find("blend")) {
        if(blend->kind == JsonValue::Kind::object)
            if(const JsonValue* verdict = blend->find("verification"))
                metadata.blend_verification =
                    as_string(*verdict, "blend.verification");
    }
    if(const JsonValue* stages = root.find("stages_not_applied")) {
        if(stages->kind == JsonValue::Kind::array)
            for(const JsonValue& stage : stages->array) {
                if(stage.kind != JsonValue::Kind::object)continue;
                const JsonValue* name = stage.find("stage");
                if(name == nullptr || name->kind != JsonValue::Kind::string)
                    continue;
                if(name->text.rfind("FRADJ", 0U) != 0U)continue;
                if(const JsonValue* status = stage.find("status"))
                    metadata.fradj_status = as_string(*status, "FRADJ status");
            }
    }
    if(const JsonValue* partial = root.find("partial")) {
        require(partial->kind == JsonValue::Kind::boolean,
                "metadata.partial must be a boolean");
        metadata.partial = partial->boolean;
    }
    return metadata;
}

std::vector<std::string> read_p6d_produced_hours(const std::string& path) {
    std::ifstream input(path);
    if(!input)fail("cannot open " + path);
    std::vector<std::string> labels;
    std::string token;
    while(input >> token)
        labels.push_back(token);
    require(!labels.empty(), path + " lists no hours");
    for(std::size_t k = 0; k < labels.size(); ++k) {
        int year = 0, month = 0, day = 0, hour = 0;
        parse_p6d_label(labels[k], year, month, day, hour);
        require(k == 0U || labels[k - 1U] < labels[k],
                "produced hours must be unique and chronological");
    }
    return labels;
}

std::vector<float> read_p6d_plane(const std::string& path, std::size_t count) {
    std::ifstream input(path, std::ios::binary);
    if(!input)fail("cannot open " + path);
    const std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(input)),
                                          std::istreambuf_iterator<char>());
    require(bytes.size() == 4U * count,
            path + " holds " + std::to_string(bytes.size()) +
                " bytes, expected " + std::to_string(4U * count) +
                " (NX*NY*NZ float32 values)");
    std::vector<float> values(count);
    for(std::size_t k = 0; k < count; ++k)
        std::memcpy(&values[k], bytes.data() + 4U * k, sizeof(float));
    for(const float value : values)
        require(std::isfinite(value),
                path + " contains a non-finite value (the contract allows the "
                       "missing sentinel, not NaN/Inf)");
    return values;
}

P6dWindHour read_p6d_wind_hour(const std::string& directory,
                               const std::string& variant,
                               const std::string& w_field,
                               const std::string& label,
                               const P6dFieldsMetadata& metadata) {
    require(variant_ok(variant),
            "variant must be wind1, inter2, blend or slope_corrected, found " +
                variant +
                " (windbc_* planes are lateral boundaries, not a gridded "
                "field, and are not a CALMET.DAT source)");
    int year = 0, month = 0, day = 0, hour = 0;
    parse_p6d_label(label, year, month, day, hour);
    const std::size_t cells =
        static_cast<std::size_t>(metadata.nx) * static_cast<std::size_t>(metadata.ny);
    const std::size_t levels = static_cast<std::size_t>(metadata.nz);
    const std::string base = directory + "/" + variant;
    P6dWindHour out;
    out.label = label;
    out.u_mps = read_p6d_plane(base + "_u_" + label + ".f32", cells * levels);
    out.v_mps = read_p6d_plane(base + "_v_" + label + ".f32", cells * levels);
    out.w_face_mps =
        read_p6d_plane(directory + "/" + w_field + "_" + label + ".f32",
                       cells * (levels + 1U));
    return out;
}

Calmet21File build_calmet_from_p6d(const std::string& directory,
                                   const std::string& variant,
                                   const std::string& w_field,
                                   const std::vector<std::string>& labels,
                                   const Calmet21File& statics_from,
                                   const Calmet21File* met_fields_from,
                                   int irtype, bool allow_unverified) {
    require(!labels.empty(), "no hourly labels were selected");
    require(irtype == 0 || irtype == 1, "IRTYPE must be 0 or 1");
    require(irtype == 1 || met_fields_from == nullptr,
            "--met-fields-from is only meaningful with IRTYPE=1");
    require(irtype == 0 || met_fields_from != nullptr,
            "IRTYPE=1 also writes T-LEV, IPGT, USTAR, ZI, EL, WSTAR, TEMPK, RHO, "
            "QSW and IRH; the P6D wind contract does not contain them, so "
            "IRTYPE=1 requires --met-fields-from <legal CALMET.DAT 2.1>");

    const P6dFieldsMetadata metadata =
        read_p6d_fields_metadata(directory + "/metadata.json");
    require(metadata.nx == statics_from.header.nx &&
                metadata.ny == statics_from.header.ny &&
                metadata.nz == statics_from.header.nz,
            "the P6D grid does not match --statics-from");
    require(metadata.zface_m == statics_from.statics.zface_m,
            "the P6D levels.zface_m does not match the ZFACE of --statics-from");
    // P6D publishes the verification verdict of its own products. A variant its
    // original-source replay rejects must not be written silently.
    const std::string verdict = metadata.blend_verification;
    if(variant != "wind1" && !verdict.empty() &&
       verdict.rfind("NOT_SOURCE_VERIFIED", 0U) == 0U && !allow_unverified)
        fail("variant " + variant + " is marked '" + verdict +
             "' by the P6D product metadata: it is not source-verified, so the "
             "writer refuses it; pass --accept-unverified-variant to write it "
             "for QA/plumbing only");
    if(metadata.hourly_label_count > 0)
        require(labels.size() <=
                    static_cast<std::size_t>(metadata.hourly_label_count),
                "metadata.hourly_labels declares " +
                    std::to_string(metadata.hourly_label_count) +
                    " hours but more were selected");
    // A subset of the produced hours (--hours) is allowed; every selected label
    // must still be one the metadata declares.
    for(const std::string& label : labels)
        if(!metadata.hourly_labels.empty())
            require(std::find(metadata.hourly_labels.begin(),
                              metadata.hourly_labels.end(),
                              label) != metadata.hourly_labels.end(),
                    "metadata.hourly_labels does not contain the selected hour " +
                        label);

    // The declaration, static records, station tables, projection block and
    // remaining controls are case input: they come from --statics-from. Only
    // the run window and IRLG are re-derived from the intervals written.
    Calmet21File file = statics_from;
    file.header.irtype = irtype;
    file.hourly.clear();

    const std::size_t cells =
        static_cast<std::size_t>(metadata.nx) * static_cast<std::size_t>(metadata.ny);
    const std::vector<std::string> label_set =
        hourly_labels(metadata.nz, irtype, file.header.lcalgrd,
                      file.header.npsta);

    std::map<std::pair<std::string, std::int64_t>, const Calmet21Field*>
        met_index;
    if(met_fields_from != nullptr) {
        require(fields_per_interval(met_fields_from->header) == label_set.size(),
                "the met source file has a different hourly field layout than "
                "IRTYPE=" + std::to_string(irtype) + " with NCALGRD/LCALGRD=" +
                    (file.header.lcalgrd ? "true" : "false") + " and NPSTA=" +
                    std::to_string(file.header.npsta));
        for(const Calmet21Field& field : met_fields_from->hourly)
            met_index[{trim_text(field.label), instant_seconds(field.begin)}] =
                &field;
    }

    for(const std::string& label : labels) {
        const P6dWindHour winds =
            read_p6d_wind_hour(directory, variant, w_field, label, metadata);
        int year = 0, month = 0, day = 0, hour = 0;
        parse_p6d_label(label, year, month, day, hour);
        const std::int64_t label_instant =
            days_from_civil(year, static_cast<unsigned>(month),
                            static_cast<unsigned>(day)) *
                86400 +
            static_cast<std::int64_t>(hour) * 3600;
        const std::int64_t begin_instant =
            metadata.label_is_interval_end ? label_instant - 3600 : label_instant;
        const Calmet21Time begin = instant_to_time(begin_instant);
        Calmet21Time end = begin;
        end.seconds += 3600;
        for(const std::string& file_label : label_set) {
            const std::string name = trim_text(file_label);
            Calmet21Field field;
            field.label = file_label;
            field.begin = begin;
            field.end = end;
            field.integer = is_integer_label(file_label);
            if(name.rfind("U-LEV", 0U) == 0U || name.rfind("V-LEV", 0U) == 0U ||
               name.rfind("WFACE", 0U) == 0U) {
                const int level = std::atoi(name.substr(5U).c_str());
                require(level >= 1 && level <= metadata.nz,
                        "level out of range in " + name);
                field.real_values.resize(cells);
                // The P6D product is level-major with the documented i-fastest
                // index i + nx*(j + ny*k): every level plane is contiguous, so
                // cell c of level k lives at c + cells*k. Reading it as
                // cell-major silently permutes the field (a defect this adapter
                // carried until the P6G end-to-end run exposed it).
                for(std::size_t cell = 0; cell < cells; ++cell) {
                    float value = 0.f;
                    if(name.rfind("U-LEV", 0U) == 0U)
                        value = winds.u_mps[cell + cells *
                                            static_cast<std::size_t>(level - 1)];
                    else if(name.rfind("V-LEV", 0U) == 0U)
                        value = winds.v_mps[cell + cells *
                                            static_cast<std::size_t>(level - 1)];
                    else
                        // CALMET.DAT writes W at the TOP face of each layer, so
                        // the P6D face k+1 is WFACE(k); the ground face is not
                        // part of the v2.1 record.
                        value = winds.w_face_mps
                            [cell + cells * static_cast<std::size_t>(level)];
                    field.real_values[cell] = value;
                }
                file.hourly.push_back(std::move(field));
                continue;
            }
            require(met_fields_from != nullptr,
                    "field " + name +
                        " has no P6D source: only U/V/W come from the P6D wind "
                        "arrays");
            const auto found = met_index.find({name, begin_instant});
            require(found != met_index.end(),
                    "the met source file has no " + name + " for interval " +
                        label);
            const Calmet21Field& source = *found->second;
            field.integer = source.integer;
            if(source.integer)
                field.integer_values = source.integer_values;
            else
                field.real_values = source.real_values;
            file.hourly.push_back(std::move(field));
        }
    }

    const Calmet21Calendar begin_calendar =
        calendar_from_instant(instant_seconds(file.hourly.front().begin));
    const Calmet21Calendar end_calendar =
        calendar_from_instant(instant_seconds(file.hourly.back().end));
    file.header.begin_year = begin_calendar.year;
    file.header.begin_month = begin_calendar.month;
    file.header.begin_day = begin_calendar.day;
    file.header.begin_hour = begin_calendar.hour;
    file.header.begin_second =
        begin_calendar.minute * 60 + begin_calendar.second;
    file.header.end_year = end_calendar.year;
    file.header.end_month = end_calendar.month;
    file.header.end_day = end_calendar.day;
    file.header.end_hour = end_calendar.hour;
    file.header.end_second = end_calendar.minute * 60 + end_calendar.second;
    file.header.irlg = static_cast<std::int32_t>(labels.size());
    validate_calmet_dat21(file);
    return file;
}

}  // namespace cteas::p6f
