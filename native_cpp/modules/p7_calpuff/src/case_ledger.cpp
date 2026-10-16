#include "cteas/puff/case_ledger.hpp"

#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/gregorian.hpp"
#include "cteas/puff/sha256.hpp"

#include <algorithm>
#include <charconv>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <iomanip>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <vector>

namespace cteas::puff {
namespace {

std::string fixed(double value, int precision = 3) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(precision) << value;
    return out.str();
}

std::string whole(long long value) { return std::to_string(value); }

bool regular_file(const std::string& path) {
    if (path.empty()) return false;
    std::error_code error;
    return std::filesystem::is_regular_file(path, error) && !error;
}

bool regular_file(const std::filesystem::path& path) {
    std::error_code error;
    return std::filesystem::is_regular_file(path, error) && !error;
}

std::uintmax_t file_bytes(const std::string& path) {
    std::error_code error;
    const auto size = std::filesystem::file_size(path, error);
    return error ? 0U : size;
}

double parse_float(const std::string& raw, const std::string& key) {
    std::string text = raw;
    for (char& c : text) {
        if (c == 'D' || c == 'd') c = 'E';
    }
    std::size_t consumed = 0;
    double value = 0.0;
    try {
        value = std::stod(text, &consumed);
    } catch (const std::exception&) {
        throw std::invalid_argument("P7 invalid float: " + key + "=" + raw);
    }
    if (consumed != text.size() || !std::isfinite(value)) {
        throw std::invalid_argument("P7 invalid/non-finite float: " + key + "=" + raw);
    }
    return value;
}

std::optional<int> optional_int(const ControlFile& control, const char* key) {
    const auto found = control.values(key);
    if (found.size() != 1U) return std::nullopt;
    const std::string& raw = found.front();
    int value = 0;
    const auto [end, error] = std::from_chars(raw.data(), raw.data() + raw.size(), value);
    if (error != std::errc{} || end != raw.data() + raw.size()) return std::nullopt;
    return value;
}

std::optional<double> optional_float(const ControlFile& control, const char* key) {
    const auto found = control.values(key);
    if (found.size() != 1U) return std::nullopt;
    return parse_float(found.front(), key);
}

std::string describe(const std::optional<int>& value) {
    return value ? whole(*value) : std::string("ABSENT");
}

std::string describe(const std::optional<double>& value) {
    return value ? fixed(*value) : std::string("ABSENT");
}

void add_refusal(CaseLedgerResult& result, std::string name, std::string expected, std::string observed,
                 bool passed) {
    result.checks.push_back({std::move(name), std::move(expected), std::move(observed), true, passed});
}

void add_info(CaseLedgerResult& result, std::string name, std::string expected, std::string observed) {
    result.checks.push_back(
        {std::move(name), std::move(expected), std::move(observed), false, true});
}

// Observed original CALMET.DAT 2.1 evidence. A parse failure is recorded, not
// thrown, so the ledger can still report every independent control-side check.
struct MetEvidence {
    bool parsed = false;
    std::string failure;
    int nx = 0, ny = 0, nz = 0, irtype = 0, wind_code = 0;
    int surface_stations = 0, upper_stations = 0, precipitation_stations = 0;
    double dx_m = 0.0, origin_x_m = 0.0, origin_y_m = 0.0;
    std::string timezone;
    std::size_t intervals = 0;
    std::int64_t first_unix = 0, final_unix = 0;
};

MetEvidence load_met(const std::string& path) {
    MetEvidence evidence;
    try {
        const auto summary = Calmet21Reader::read(path, {}, false);
        evidence.parsed = true;
        evidence.nx = summary.header.nx;
        evidence.ny = summary.header.ny;
        evidence.nz = summary.header.nz;
        evidence.irtype = summary.header.irtype;
        evidence.wind_code = summary.header.wind_code;
        evidence.surface_stations = summary.header.surface_stations;
        evidence.upper_stations = summary.header.upper_stations;
        evidence.precipitation_stations = summary.header.precipitation_stations;
        evidence.dx_m = summary.header.dx_m;
        evidence.origin_x_m = summary.header.origin_x_m;
        evidence.origin_y_m = summary.header.origin_y_m;
        evidence.timezone = summary.header.timezone;
        evidence.intervals = summary.intervals;
        evidence.first_unix = summary.first_begin.unix_seconds;
        evidence.final_unix = summary.final_end.unix_seconds;
    } catch (const std::exception& error) {
        evidence.failure = error.what();
    }
    return evidence;
}

// Observed selected-dry CALPUFF control evidence.
struct ControlEvidence {
    bool parsed = false;
    std::string failure;
    int start_year = 0, start_month = 0, start_day = 0, start_hour = 0, start_second = 0;
    int end_year = 0, end_month = 0, end_day = 0, end_hour = 0, end_second = 0;
    std::int64_t start_unix = 0, end_unix = 0;
    int nx = 0, ny = 0, nz = 0;
    double dgrid_km = 0.0;
    std::optional<double> xorigin_km, yorigin_km;
    std::string timezone;
    int point_sources = 0, species = 0, emitted = 0, wet_mode = 0;
    std::optional<int> decay_mode;
    std::string declared_met;
    std::vector<std::string> species_names;
};

ControlEvidence load_control(const std::string& path) {
    ControlEvidence evidence;
    try {
        const auto control = ControlFile::read_file(path);
        const auto selected = validate_selected_dry_inputs(control);
        evidence.nx = selected.nx;
        evidence.ny = selected.ny;
        evidence.nz = selected.nz;
        evidence.species = selected.species_count;
        evidence.emitted = selected.emitted_species_count;
        evidence.wet_mode = control.required_int("MWET");
        evidence.decay_mode = optional_int(control, "NDECAY");
        evidence.start_year = control.required_int("IBYR");
        evidence.start_month = control.required_int("IBMO");
        evidence.start_day = control.required_int("IBDY");
        evidence.start_hour = control.required_int("IBHR");
        evidence.start_second = control.required_int("IBSEC");
        evidence.end_year = control.required_int("IEYR");
        evidence.end_month = control.required_int("IEMO");
        evidence.end_day = control.required_int("IEDY");
        evidence.end_hour = control.required_int("IEHR");
        evidence.end_second = control.required_int("IESEC");
        evidence.dgrid_km = parse_float(control.required_one("DGRIDKM"), "DGRIDKM");
        evidence.xorigin_km = optional_float(control, "XORIGKM");
        evidence.yorigin_km = optional_float(control, "YORIGKM");
        evidence.timezone = control.required_one("ABTZ");
        evidence.declared_met = control.required_one("METDAT");
        evidence.point_sources = control.required_int("NPT1");
        evidence.species_names = control.values("CSPEC");
        evidence.start_unix = gregorian_unix_seconds(evidence.start_year, evidence.start_month,
                                                     evidence.start_day, evidence.start_hour,
                                                     evidence.start_second);
        evidence.end_unix = gregorian_unix_seconds(evidence.end_year, evidence.end_month,
                                                   evidence.end_day, evidence.end_hour,
                                                   evidence.end_second);
        evidence.parsed = true;
    } catch (const std::exception& error) {
        evidence.failure = error.what();
    }
    return evidence;
}

std::string lowered(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

std::string json_escape(std::string_view text) {
    std::string out;
    out.reserve(text.size());
    for (const char raw : text) {
        const auto byte = static_cast<unsigned char>(raw);
        switch (raw) {
        case '"': out += "\\\""; break;
        case '\\': out += "\\\\"; break;
        case '\n': out += "\\n"; break;
        case '\r': out += "\\r"; break;
        case '\t': out += "\\t"; break;
        default:
            if (byte < 0x20U) {
                std::ostringstream hex;
                hex << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                    << static_cast<int>(byte);
                out += hex.str();
            } else {
                out += raw;
            }
        }
    }
    return out;
}

std::string quoted(std::string_view text) { return "\"" + json_escape(text) + "\""; }

std::string join(const std::vector<std::string>& values) {
    std::string out;
    for (const auto& value : values) {
        if (!out.empty()) out += "|";
        out += value;
    }
    return out;
}

bool any_refusal_failed(const CaseLedgerResult& result) {
    for (const auto& check : result.checks) {
        if (check.refusal && !check.passed) return true;
    }
    return false;
}

void record_artifact(CaseLedgerResult& result, const std::string& role, const std::string& path) {
    LedgerArtifact artifact;
    artifact.role = role;
    artifact.path = path;
    artifact.bytes = file_bytes(path);
    try {
        artifact.sha256 = sha256_hex_file(path);
    } catch (const std::exception& error) {
        artifact.sha256 = std::string("UNREADABLE:") + error.what();
    }
    result.artifacts.push_back(std::move(artifact));
}

// Sibling output names of the original CALPUFF sample case; used only when the
// caller does not state a concentration/listing path explicitly.
std::string discover_sibling(const std::string& control_path,
                             const std::vector<const char*>& names) {
    const auto directory = std::filesystem::path(control_path).parent_path();
    for (const char* name : names) {
        const auto candidate = directory / name;
        if (regular_file(candidate)) return candidate.string();
    }
    return {};
}

} // namespace

CaseLedgerResult evaluate_hefei_2022_case(const CaseLedgerRequest& request) {
    CaseLedgerResult result;
    result.met_path = request.met_path;
    result.control_path = request.control_path;
    if (!regular_file(request.met_path)) result.missing_roles.push_back("original_met_dat");
    if (!regular_file(request.control_path)) result.missing_roles.push_back("calpuff_control");
    if (request.concentration_path.empty()) {
        result.concentration_path =
            discover_sibling(request.control_path, {"puff.con", "PUFF.CON", "conc.dat", "CONC.DAT"});
    } else {
        result.concentration_path = request.concentration_path;
        if (!regular_file(request.concentration_path))
            result.missing_roles.push_back("original_concentration");
    }
    if (request.listing_path.empty()) {
        result.listing_path = discover_sibling(request.control_path, {"puff.lst", "PUFF.LST"});
    } else {
        result.listing_path = request.listing_path;
        if (!regular_file(request.listing_path)) result.missing_roles.push_back("original_listing");
    }
    result.limitations.push_back(
        "SOFTWARE_INPUT_IDENTITY_ONLY: this ledger validates frozen input identity; no CALMET or "
        "CALPUFF physics is reconstructed by it.");
    result.limitations.push_back(
        "ORIGINAL_EXECUTION_IS_NOT_CPP_PARITY: an original concentration file is provenance, not "
        "C++ dispersion or concentration parity.");
    result.limitations.push_back(
        "WET_DEPOSITION_NOT_VERIFIABLE: the selected 2022 scope requires MWET=0 and zero original "
        "precipitation stations; wet scavenging cannot be validated from it.");

    if (!result.missing_roles.empty()) {
        result.status = std::string(kLedgerBlockedMissingInputs);
        result.exit_code = 3;
        result.limitations.push_back(
            "BLOCKED_INPUTS_ABSENT: no assertion is made about a case whose mandatory files are "
            "missing; missing roles: " + join(result.missing_roles));
        return result;
    }

    for (const auto& [role, path] :
         {std::pair<std::string, std::string>("original_met_dat", request.met_path),
          std::pair<std::string, std::string>("calpuff_control", request.control_path)}) {
        record_artifact(result, role, path);
    }
    if (!result.concentration_path.empty())
        record_artifact(result, "original_concentration", result.concentration_path);
    if (!result.listing_path.empty()) record_artifact(result, "original_listing", result.listing_path);

    const auto met = load_met(request.met_path);
    const auto control = load_control(request.control_path);

    // Mandatory SHA-256 pins, when the caller declares them. Hex case is
    // normalized because repository variables are free text.
    if (!request.expected_met_sha256.empty()) {
        const auto observed = result.artifacts.front().sha256;
        add_refusal(result, "original_met_dat_sha256_pin", lowered(request.expected_met_sha256),
                    observed, observed == lowered(request.expected_met_sha256));
    }
    if (!request.expected_control_sha256.empty()) {
        const auto observed = result.artifacts[1].sha256;
        add_refusal(result, "calpuff_control_sha256_pin", lowered(request.expected_control_sha256),
                    observed, observed == lowered(request.expected_control_sha256));
    }

    add_refusal(result, "original_met_dat_contract",
                "readable CALMET.DAT 2.1 IRTYPE=1 IWFCOD=1 with contiguous hourly fields",
                met.parsed ? std::string("PARSED") : met.failure, met.parsed);
    add_refusal(result, "calpuff_control_contract",
                "readable selected dry CALPUFF control with explicit frozen date/grid options",
                control.parsed ? std::string("PARSED") : control.failure, control.parsed);

    if (met.parsed) {
        add_info(result, "met_irtype", "1", whole(met.irtype));
        add_info(result, "met_wind_code", "1", whole(met.wind_code));
        add_refusal(result, "met_nx", whole(Hefei2022Spec::nx), whole(met.nx),
                    met.nx == Hefei2022Spec::nx);
        add_refusal(result, "met_ny", whole(Hefei2022Spec::ny), whole(met.ny),
                    met.ny == Hefei2022Spec::ny);
        add_refusal(result, "met_nz", whole(Hefei2022Spec::nz), whole(met.nz),
                    met.nz == Hefei2022Spec::nz);
        add_refusal(result, "met_dx_m", fixed(Hefei2022Spec::dx_m), fixed(met.dx_m),
                    std::abs(met.dx_m - Hefei2022Spec::dx_m) < 0.001);
        add_refusal(result, "met_timezone", "UTC+0000", met.timezone, met.timezone == "UTC+0000");
        add_refusal(result, "met_surface_stations", ">=1", whole(met.surface_stations),
                    met.surface_stations >= 1);
        add_refusal(result, "met_upper_stations", ">=1", whole(met.upper_stations),
                    met.upper_stations >= 1);
        add_refusal(result, "met_precipitation_stations", "0", whole(met.precipitation_stations),
                    met.precipitation_stations == 0);
        add_refusal(result, "met_hourly_intervals", whole(Hefei2022Spec::hourly_intervals),
                    whole(static_cast<long long>(met.intervals)),
                    met.intervals == static_cast<std::size_t>(Hefei2022Spec::hourly_intervals));
        add_refusal(result, "met_first_begin_unix_seconds", whole(Hefei2022Spec::first_unix_seconds),
                    whole(met.first_unix), met.first_unix == Hefei2022Spec::first_unix_seconds);
        add_refusal(result, "met_final_end_unix_seconds", whole(Hefei2022Spec::final_unix_seconds),
                    whole(met.final_unix), met.final_unix == Hefei2022Spec::final_unix_seconds);
        const double origin_dx = met.origin_x_m - Hefei2022Spec::stack_x_m;
        const double origin_dy = met.origin_y_m - Hefei2022Spec::stack_y_m;
        add_refusal(result, "met_origin_inside_2022_crop_window",
                    "origin within +-" + fixed(Hefei2022Spec::crop_margin_m) +
                        " m of the 2022 stack position in both axes",
                    "dx=" + fixed(origin_dx) + " dy=" + fixed(origin_dy),
                    std::abs(origin_dx) <= Hefei2022Spec::crop_margin_m &&
                        std::abs(origin_dy) <= Hefei2022Spec::crop_margin_m);
        add_info(result, "met_origin_m", "2022 domain lower face " +
                                             fixed(Hefei2022Spec::stack_x_m - 2500.0) + "/" +
                                             fixed(Hefei2022Spec::stack_y_m - 2500.0),
                 fixed(met.origin_x_m) + "/" + fixed(met.origin_y_m));
    }

    if (control.parsed) {
        add_refusal(result, "control_start_date", "2022-01-01 00:00:00 UTC",
                    whole(control.start_year) + "-" + whole(control.start_month) + "-" +
                        whole(control.start_day) + " " + whole(control.start_hour) + ":" +
                        whole(control.start_second),
                    control.start_year == Hefei2022Spec::start_year &&
                        control.start_month == Hefei2022Spec::start_month &&
                        control.start_day == Hefei2022Spec::start_day && control.start_hour == 0 &&
                        control.start_second == 0);
        add_refusal(result, "control_end_date", "2022-01-06 23:00:00 UTC",
                    whole(control.end_year) + "-" + whole(control.end_month) + "-" +
                        whole(control.end_day) + " " + whole(control.end_hour) + ":" +
                        whole(control.end_second),
                    control.end_year == Hefei2022Spec::end_year &&
                        control.end_month == Hefei2022Spec::end_month &&
                        control.end_day == Hefei2022Spec::end_day &&
                        control.end_hour == Hefei2022Spec::end_hour && control.end_second == 0);
        add_refusal(result, "control_nx", whole(Hefei2022Spec::nx), whole(control.nx),
                    control.nx == Hefei2022Spec::nx);
        add_refusal(result, "control_ny", whole(Hefei2022Spec::ny), whole(control.ny),
                    control.ny == Hefei2022Spec::ny);
        add_refusal(result, "control_nz", whole(Hefei2022Spec::nz), whole(control.nz),
                    control.nz == Hefei2022Spec::nz);
        add_refusal(result, "control_dgrid_km", fixed(Hefei2022Spec::dx_m / 1000.0, 4),
                    fixed(control.dgrid_km, 4),
                    std::abs(control.dgrid_km * 1000.0 - Hefei2022Spec::dx_m) < 0.001);
        add_refusal(result, "control_abtz", "UTC+0000", control.timezone,
                    control.timezone == "UTC+0000");
        add_refusal(result, "control_point_sources", "1 (single selected stack)", whole(control.point_sources),
                    control.point_sources == 1);
        add_refusal(result, "control_grid_origin_km_present", "XORIGKM and YORIGKM active once each",
                    describe(control.xorigin_km) + "/" + describe(control.yorigin_km),
                    control.xorigin_km.has_value() && control.yorigin_km.has_value());
        add_info(result, "control_species", "NSPEC=" + whole(control.species) +
                                                " NSE=" + whole(control.emitted),
                 join(control.species_names));
        add_info(result, "control_wet_mode", "MWET=0 (selected dry scope)",
                 "MWET=" + whole(control.wet_mode));
        add_info(result, "control_decay_mode", "recorded, not a parity claim",
                 "NDECAY=" + describe(control.decay_mode));
        add_info(result, "control_time_window_unix_seconds",
                 whole(Hefei2022Spec::first_unix_seconds) + ".." +
                     whole(Hefei2022Spec::final_unix_seconds),
                 whole(control.start_unix) + ".." + whole(control.end_unix));

        // The declared METDAT must resolve to the very file under audit whenever
        // the case tree is complete; a relocated tree is reported, not invented.
        const auto declared = std::filesystem::path(request.control_path).parent_path() /
                              std::filesystem::path(control.declared_met);
        const auto resolved = declared.lexically_normal();
        if (regular_file(resolved)) {
            const auto resolved_sha = sha256_hex_file(resolved.string());
            add_refusal(result, "control_metdat_resolves_to_original_met_dat",
                        resolved.string(), resolved_sha, resolved_sha == result.artifacts.front().sha256);
        } else {
            add_info(result, "control_metdat_resolution", control.declared_met,
                     "NOT_PRESENT_IN_TREE:" + resolved.string());
        }
    }

    if (met.parsed && control.parsed) {
        add_refusal(result, "grid_nx_matches_met", whole(met.nx), whole(control.nx),
                    control.nx == met.nx);
        add_refusal(result, "grid_ny_matches_met", whole(met.ny), whole(control.ny),
                    control.ny == met.ny);
        add_refusal(result, "grid_nz_matches_met", whole(met.nz), whole(control.nz),
                    control.nz == met.nz);
        const double control_dx_m = control.dgrid_km * 1000.0;
        add_refusal(result, "grid_dx_matches_met", fixed(met.dx_m), fixed(control_dx_m),
                    std::abs(control_dx_m - met.dx_m) < 0.001);
        add_refusal(result, "time_window_matches_met",
                    whole(met.first_unix) + ".." + whole(met.final_unix),
                    whole(control.start_unix) + ".." + whole(control.end_unix),
                    control.start_unix == met.first_unix && control.end_unix == met.final_unix);
        if (control.xorigin_km.has_value() && control.yorigin_km.has_value()) {
            const double slack = 0.5 * met.dx_m;
            const double control_x0 = *control.xorigin_km * 1000.0;
            const double control_y0 = *control.yorigin_km * 1000.0;
            const double control_x1 = control_x0 + control.nx * control_dx_m;
            const double control_y1 = control_y0 + control.ny * control_dx_m;
            const double met_x1 = met.origin_x_m + met.nx * met.dx_m;
            const double met_y1 = met.origin_y_m + met.ny * met.dx_m;
            const bool inside = control_x0 >= met.origin_x_m - slack && control_x1 <= met_x1 + slack &&
                                control_y0 >= met.origin_y_m - slack && control_y1 <= met_y1 + slack;
            add_refusal(result, "control_grid_within_met_domain",
                        "x[" + fixed(met.origin_x_m) + "," + fixed(met_x1) + "] y[" +
                            fixed(met.origin_y_m) + "," + fixed(met_y1) + "] (half-cell slack)",
                        "x[" + fixed(control_x0) + "," + fixed(control_x1) + "] y[" +
                            fixed(control_y0) + "," + fixed(control_y1) + "]",
                        inside);
        }
    }

    if (any_refusal_failed(result)) {
        std::vector<std::string> failed;
        for (const auto& check : result.checks) {
            if (check.refusal && !check.passed) failed.push_back(check.name);
        }
        result.status = std::string(kLedgerRejectedNotCanonical2022);
        result.exit_code = 4;
        result.limitations.push_back(
            "HISTORICAL_OR_FOREIGN_CASES_CANNOT_BE_RELABELLED: observed values are recorded so a "
            "non-2022 case can never be presented as the 2022 reference; failed checks: " +
            join(failed));
        return result;
    }

    result.canonical_2022 = true;
    result.reference_class = "CANONICAL_2022_HEFEI_50X50_100M";
    if (result.concentration_path.empty()) {
        result.status = std::string(kLedgerAcceptedPendingOriginalExecution);
        result.limitations.push_back(
            "NO_ORIGINAL_2022_EXECUTION_EVIDENCE: no original concentration file was found for "
            "this case, so the original CALPUFF reference run is still pending.");
    } else {
        result.status = std::string(kLedgerAcceptedOriginalOutputPresent);
        result.limitations.push_back(
            "ORIGINAL_CONCENTRATION_PRESENT_UNVERIFIED_AGAINST_CPP: the concentration file is "
            "pinned for provenance only; P7E concentration output does not exist yet.");
    }
    if (request.expected_met_sha256.empty() || request.expected_control_sha256.empty()) {
        result.limitations.push_back(
            "INPUT_PINS_INCOMPLETE: at least one caller-supplied frozen SHA-256 pin was absent, so "
            "identity relied on this tree only.");
    }
    result.exit_code = 0;
    return result;
}

std::string case_ledger_json(const CaseLedgerResult& result) {
    std::ostringstream out;
    out << "{\n"
        << "  \"gate\": \"P7_HFEI_2022_CASE_EXECUTION_LEDGER\",\n"
        << "  \"version\": 1,\n"
        << "  \"status\": " << quoted(result.status) << ",\n"
        << "  \"exit_code\": " << result.exit_code << ",\n"
        << "  \"reference_class\": " << quoted(result.reference_class) << ",\n"
        << "  \"canonical_2022\": " << (result.canonical_2022 ? "true" : "false") << ",\n"
        << "  \"case\": {\n"
        << "    \"met_dat\": " << quoted(result.met_path) << ",\n"
        << "    \"puff_control\": " << quoted(result.control_path) << ",\n"
        << "    \"concentration\": " << quoted(result.concentration_path) << ",\n"
        << "    \"listing\": " << quoted(result.listing_path) << "\n"
        << "  },\n"
        << "  \"missing_roles\": [";
    for (std::size_t i = 0; i < result.missing_roles.size(); ++i) {
        out << (i == 0 ? "" : ", ") << quoted(result.missing_roles[i]);
    }
    out << "],\n  \"checks\": [";
    for (std::size_t i = 0; i < result.checks.size(); ++i) {
        const auto& check = result.checks[i];
        out << (i == 0 ? "\n" : ",\n") << "    {\"check\": " << quoted(check.name)
            << ", \"severity\": " << quoted(check.refusal ? "refusal" : "info")
            << ", \"result\": "
            << quoted(check.refusal ? (check.passed ? "PASS" : "FAIL") : "INFO")
            << ", \"expected\": " << quoted(check.expected)
            << ", \"observed\": " << quoted(check.observed) << "}";
    }
    out << (result.checks.empty() ? "" : "\n  ") << "],\n  \"artifacts\": [";
    for (std::size_t i = 0; i < result.artifacts.size(); ++i) {
        const auto& artifact = result.artifacts[i];
        out << (i == 0 ? "\n" : ",\n") << "    {\"role\": " << quoted(artifact.role)
            << ", \"path\": " << quoted(artifact.path) << ", \"bytes\": " << artifact.bytes
            << ", \"sha256\": " << quoted(artifact.sha256) << "}";
    }
    out << (result.artifacts.empty() ? "" : "\n  ") << "],\n  \"limitations\": [";
    for (std::size_t i = 0; i < result.limitations.size(); ++i) {
        out << (i == 0 ? "\n" : ",\n") << "    " << quoted(result.limitations[i]);
    }
    out << (result.limitations.empty() ? "" : "\n  ") << "]\n}\n";
    return out.str();
}

} // namespace cteas::puff
