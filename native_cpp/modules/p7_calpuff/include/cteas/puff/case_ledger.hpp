#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace cteas::puff {

// Frozen Hefei 2022 selected case specification. Source of the numbers:
// docs/reconstruction_cpp/HEFEI_2022_REFERENCE_CASE.md (case spec locked,
// original Fortran controls still unverified) and the 2022 crop metadata.
// These constants are the acceptance boundary of the P7 2022 execution
// ledger and are NOT evidence that a real original 2022 case exists.
struct Hefei2022Spec {
    static constexpr int nx = 50;
    static constexpr int ny = 50;
    static constexpr int nz = 9;
    static constexpr double dx_m = 100.0;
    // Stack position and +-3.5 km crop extent in EPSG:32650 (UTM 50N).
    static constexpr double stack_x_m = 513384.6439571;
    static constexpr double stack_y_m = 3533768.9269678;
    static constexpr double crop_margin_m = 3500.0;
    // 2022-01-01 00:00:00Z through 2022-01-06 23:00:00Z, 143 original
    // CALMET hourly intervals.
    static constexpr int start_year = 2022;
    static constexpr int start_month = 1;
    static constexpr int start_day = 1;
    static constexpr int end_year = 2022;
    static constexpr int end_month = 1;
    static constexpr int end_day = 6;
    static constexpr int end_hour = 23;
    static constexpr int hourly_intervals = 143;
    static constexpr std::int64_t first_unix_seconds = 1640995200;
    static constexpr std::int64_t final_unix_seconds = 1641510000;
};

// Machine-readable ledger status names.
inline constexpr std::string_view kLedgerAcceptedPendingOriginalExecution =
    "ACCEPTED_CANONICAL_2022_PENDING_ORIGINAL_EXECUTION";
inline constexpr std::string_view kLedgerAcceptedOriginalOutputPresent =
    "ACCEPTED_CANONICAL_2022_ORIGINAL_OUTPUT_PRESENT";
inline constexpr std::string_view kLedgerBlockedMissingInputs = "BLOCKED_MISSING_INPUTS";
inline constexpr std::string_view kLedgerRejectedNotCanonical2022 = "REJECTED_NOT_CANONICAL_2022";

// One ledger row: a frozen-spec or cross-file assertion with the values that
// were actually observed. `refusal` rows can make the case not canonical;
// info rows are recorded evidence and never change the verdict.
struct LedgerCheck {
    std::string name;
    std::string expected;
    std::string observed;
    bool refusal = true;
    bool passed = true;
};

struct LedgerArtifact {
    std::string role;
    std::string path;
    std::uintmax_t bytes = 0;
    std::string sha256;
};

struct CaseLedgerRequest {
    std::string met_path;
    std::string control_path;
    std::string concentration_path; // optional; discovered next to the control when empty
    std::string listing_path;       // optional; discovered next to the control when empty
    std::string expected_met_sha256;
    std::string expected_control_sha256;
};

struct CaseLedgerResult {
    std::string status;
    std::string reference_class = "NOT_CANONICAL_2022";
    bool canonical_2022 = false;
    int exit_code = 0;
    std::string met_path;
    std::string control_path;
    std::string concentration_path;
    std::string listing_path;
    std::vector<std::string> missing_roles;
    std::vector<LedgerCheck> checks;
    std::vector<LedgerArtifact> artifacts;
    std::vector<std::string> limitations;
};

// Fail-closed evaluation of one candidate frozen 2022 case. Never reports
// acceptance without a readable MET.DAT and CALPUFF control file plus every
// frozen-spec and cross-file assertion passing. Software/input identity only:
// it makes no CALPUFF physics or concentration-parity claim.
[[nodiscard]] CaseLedgerResult evaluate_hefei_2022_case(const CaseLedgerRequest& request);

// Deterministic JSON rendering of a ledger result.
[[nodiscard]] std::string case_ledger_json(const CaseLedgerResult& result);

} // namespace cteas::puff
