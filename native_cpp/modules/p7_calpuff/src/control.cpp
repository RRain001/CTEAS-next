#include "cteas/puff/control.hpp"

#include <algorithm>
#include <charconv>
#include <cctype>
#include <cmath>
#include <fstream>
#include <iterator>
#include <regex>
#include <stdexcept>
#include <string>
#include <utility>

namespace cteas::puff {
namespace {
std::string trim(std::string s) {
    const auto first = s.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return {};
    const auto last = s.find_last_not_of(" \t\r\n");
    return s.substr(first, last - first + 1);
}

std::string normalized(std::string_view key) {
    std::string out(key);
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    return out;
}

int exact_int(const std::string& raw, const std::string& key) {
    const std::string value = trim(raw);
    int number = 0;
    const auto [end, ec] = std::from_chars(value.data(), value.data() + value.size(), number);
    if (ec != std::errc{} || end != value.data() + value.size()) {
        throw std::invalid_argument("P7 invalid integer: " + key + "=" + raw);
    }
    return number;
}

double exact_float(std::string raw, const std::string& key) {
    raw = trim(raw);
    std::replace(raw.begin(), raw.end(), 'D', 'E');
    std::replace(raw.begin(), raw.end(), 'd', 'e');
    std::size_t consumed = 0;
    double number = 0.0;
    try {
        number = std::stod(raw, &consumed);
    } catch (const std::exception&) {
        throw std::invalid_argument("P7 invalid float: " + key + "=" + raw);
    }
    if (consumed != raw.size() || !std::isfinite(number)) {
        throw std::invalid_argument("P7 invalid/non-finite float: " + key + "=" + raw);
    }
    return number;
}

void require_equals(const ControlFile& c, const char* key, int expected) {
    if (c.required_int(key) != expected) {
        throw std::invalid_argument(std::string("P7 option unsupported in selected dry input scope: ") + key);
    }
}
} // namespace

ControlFile ControlFile::parse(std::string_view text) {
    // Read only active !KEY=value! assignments; *KEY=value* is an inactive
    // template default in original CALPUFF files. Preserve repeated keys
    // such as CSPEC, ZFACE and source definitions; do not flatten to a map.
    const std::regex active(R"(![ \t]*([A-Za-z][A-Za-z0-9_]*)[ \t]*=[ \t]*([^!\r\n]*)!)");
    ControlFile control;
    std::size_t line_number = 0;
    std::size_t pos = 0;
    while (pos < text.size()) {
        const std::size_t end = text.find('\n', pos);
        const std::size_t last = end == std::string_view::npos ? text.size() : end;
        const std::string line(text.substr(pos, last - pos));
        ++line_number;
        for (std::sregex_iterator it(line.begin(), line.end(), active), stop; it != stop; ++it) {
            const auto& match = *it;
            control.entries_.push_back({normalized(match[1].str()),
                                        trim(match[2].str()), line_number});
        }
        if (end == std::string_view::npos) break;
        pos = end + 1;
    }
    return control;
}

ControlFile ControlFile::read_file(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7 cannot open original control file: " + path);
    const std::string content((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    if (!input.eof() && input.fail()) throw std::runtime_error("P7 control read failed: " + path);
    return parse(content);
}

std::vector<std::string> ControlFile::values(std::string_view key) const {
    std::vector<std::string> found;
    const auto wanted = normalized(key);
    for (const auto& entry : entries_) if (entry.key == wanted) found.push_back(entry.value);
    return found;
}

std::string ControlFile::required_one(std::string_view key) const {
    auto found = values(key);
    if (found.size() != 1 || found.front().empty()) {
        throw std::invalid_argument("P7 expected exactly one active control: " + normalized(key));
    }
    return found.front();
}

int ControlFile::required_int(std::string_view key) const {
    const auto k = normalized(key);
    return exact_int(required_one(key), k);
}

std::vector<double> ControlFile::required_float_list(std::string_view key) const {
    const auto k = normalized(key);
    auto found = values(key);
    if (found.empty()) throw std::invalid_argument("P7 missing active list: " + k);
    std::vector<double> numbers;
    for (const auto& line : found) {
        std::size_t start = 0;
        do {
            const auto end = line.find(',', start);
            numbers.push_back(exact_float(line.substr(start, end == std::string::npos
                ? std::string::npos : end - start), k));
            if (end == std::string::npos) break;
            start = end + 1;
        } while (true);
    }
    return numbers;
}

SelectedDryInputs validate_selected_dry_inputs(const ControlFile& c) {
    // Strictly limit this stage to the active reference input family. This is
    // NOT an assertion that any of these algorithms has been reconstructed.
    require_equals(c, "METFM", 1);
    require_equals(c, "MGAUSS", 1);
    require_equals(c, "MSLUG", 0);
    require_equals(c, "MDISP", 3);
    require_equals(c, "MCHEM", 0);
    require_equals(c, "MWET", 0);
    const int metrun = c.required_int("METRUN");
    if (metrun != 0 && metrun != 1) throw std::invalid_argument("P7 METRUN must be 0 or 1");
    SelectedDryInputs out;
    out.met_file = c.required_one("METDAT");
    out.nx = c.required_int("NX");
    out.ny = c.required_int("NY");
    out.nz = c.required_int("NZ");
    out.time_step_s = c.required_int("NSECDT");
    out.species_count = c.required_int("NSPEC");
    out.emitted_species_count = c.required_int("NSE");
    out.output_units = c.required_int("IOUTU");
    out.zface_m = c.required_float_list("ZFACE");
    if (out.nx <= 0 || out.ny <= 0 || out.nz <= 0 ||
        out.time_step_s <= 0 || out.time_step_s > 3600 || 3600 % out.time_step_s != 0 ||
        out.species_count <= 0 || out.emitted_species_count <= 0 ||
        out.emitted_species_count > out.species_count ||
        (out.output_units != 1 && out.output_units != 3) ||
        out.zface_m.size() != static_cast<std::size_t>(out.nz + 1)) {
        throw std::invalid_argument("P7 selected reference geometry/time/species constraints failed");
    }
    if (out.zface_m.front() < 0.0) throw std::invalid_argument("P7 negative ZFACE");
    for (std::size_t i = 1; i < out.zface_m.size(); ++i) {
        if (out.zface_m[i] <= out.zface_m[i - 1])
            throw std::invalid_argument("P7 ZFACE not strictly increasing");
    }
    return out;
}
} // namespace cteas::puff
