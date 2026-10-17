// P7 2022 Hefei case execution ledger contract tests.
// Synthetic fixtures only: they prove the ledger's frozen-spec and
// cross-file fail-closed behaviour, not any CALPUFF physics.
#include "cteas/puff/case_ledger.hpp"
#include "cteas/puff/gregorian.hpp"
#include "cteas/puff/sha256.hpp"

#include <algorithm>
#include <cstdint>
#include <cctype>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <ostream>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

namespace fs = std::filesystem;
using cteas::puff::CaseLedgerRequest;
using cteas::puff::CaseLedgerResult;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7 CASE LEDGER TEST FAILURE: " + message);
}

void write_bytes(std::ostream& out, const void* data, std::size_t size) {
    out.write(static_cast<const char*>(data), static_cast<std::streamsize>(size));
    require(bool(out), "synthetic write failed");
}

void frame_record(std::ofstream& out, const std::vector<std::uint8_t>& payload) {
    const std::int32_t marker = static_cast<std::int32_t>(payload.size());
    write_bytes(out, &marker, sizeof(marker));
    write_bytes(out, payload.data(), payload.size());
    write_bytes(out, &marker, sizeof(marker));
}

void store_i32(std::vector<std::uint8_t>& buffer, std::size_t offset, std::int32_t value) {
    std::memcpy(buffer.data() + offset, &value, sizeof(value));
}

void store_f32(std::vector<std::uint8_t>& buffer, std::size_t offset, float value) {
    std::memcpy(buffer.data() + offset, &value, sizeof(value));
}

std::vector<std::string> expected_labels(int nz) {
    std::vector<std::string> labels;
    for (int z = 1; z <= nz; ++z) {
        const auto number = std::to_string(z);
        const std::string padded(3 - number.size(), ' ');
        for (const auto* prefix : {"U-LEV", "V-LEV", "WFACE"})
            labels.push_back(std::string(prefix) + padded + number);
    }
    for (int z = 1; z <= nz; ++z) {
        const auto number = std::to_string(z);
        labels.push_back("T-LEV" + std::string(3 - number.size(), ' ') + number);
    }
    for (const auto* label : {"IPGT", "USTAR", "ZI", "EL", "WSTAR", "TEMPK", "RHO", "QSW", "IRH"})
        labels.push_back(label);
    return labels;
}

struct MetConfig {
    int nx = 50, ny = 50, nz = 9;
    double dx_m = 100.0;
    double origin_x_m = 510884.6439571;
    double origin_y_m = 3531268.9269678;
    std::string timezone = "UTC+0000";
    int surface_stations = 1, upper_stations = 1, precipitation_stations = 0;
    int intervals = 143;
    int start_year = 2022, start_julian_day = 1;
};

struct MetLayout {
    std::size_t header_payload = 0;
    std::size_t first_field_payload = 0;
};

// Emits a minimal but layout-complete original CALMET.DAT 2.1 file (IRTYPE=1,
// IWFCOD=1) with zero-valued finite fields.
MetLayout write_synthetic_met(const fs::path& path, const MetConfig& config) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    require(bool(out), "cannot create synthetic MET.DAT " + path.string());
    MetLayout layout;

    std::vector<std::uint8_t> signature(96, ' ');
    const std::string head = "CALMET.DAT      2.1             No-Obs file structure with control";
    std::copy(head.begin(), head.end(), signature.begin());
    frame_record(out, signature);

    std::vector<std::uint8_t> comments(4, 0);
    store_i32(comments, 0, 0);
    frame_record(out, comments);

    layout.header_payload = 104 + 12 + 4;
    layout.first_field_payload = layout.header_payload + 176 + 4 + 4;
    std::vector<std::uint8_t> header(176, 0);
    const std::string description = "UTM     WGS-84  02-21-2003  ";
    std::copy(description.begin(), description.end(), header.begin() + 112);
    const std::string timezone = "UTC+0000";
    std::copy(timezone.begin(), timezone.end(), header.begin() + 40);
    store_i32(header, 48, config.intervals);
    store_i32(header, 52, 1);
    store_i32(header, 56, config.nx);
    store_i32(header, 60, config.ny);
    store_i32(header, 64, config.nz);
    store_f32(header, 68, static_cast<float>(config.dx_m));
    store_f32(header, 72, static_cast<float>(config.origin_x_m));
    store_f32(header, 76, static_cast<float>(config.origin_y_m));
    store_i32(header, 80, 1);
    store_i32(header, 84, config.surface_stations);
    store_i32(header, 88, config.upper_stations);
    store_i32(header, 92, config.precipitation_stations);
    store_i32(header, 96, config.nz + 5);
    store_i32(header, 100, config.nx);
    store_i32(header, 104, config.ny + 5);
    store_i32(header, 108, 1);
    frame_record(out, header);

    const auto labels = expected_labels(config.nz);
    const std::size_t cells = static_cast<std::size_t>(config.nx) * config.ny;
    std::vector<std::uint8_t> payload(24 + 4 * cells, 0);
    for (int step = 0; step < config.intervals; ++step) {
        const std::int32_t begin_hour = step;
        const std::int32_t end_hour = step + 1;
        for (const auto& label : labels) {
            std::fill(payload.begin(), payload.end(), 0);
            std::fill(payload.begin(), payload.begin() + 8, ' ');
            std::copy(label.begin(), label.end(), payload.begin());
            const auto pack = [&config](std::int32_t hour_index) {
                const std::int32_t day = config.start_julian_day + hour_index / 24;
                return config.start_year * 100000 + day * 100 + hour_index % 24;
            };
            store_i32(payload, 8, pack(begin_hour));
            store_i32(payload, 12, 0);
            store_i32(payload, 16, pack(end_hour));
            store_i32(payload, 20, 0);
            frame_record(out, payload);
        }
    }
    require(bool(out), "synthetic MET.DAT flush failed");
    return layout;
}

void write_text(const fs::path& path, const std::string& text) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    require(bool(out), "cannot write " + path.string());
    out << text;
    require(bool(out), "text write failed for " + path.string());
}

std::string replace_once(std::string text, const std::string& old_value, const std::string& new_value) {
    const auto position = text.find(old_value);
    require(position != std::string::npos, "fixture mutation target absent: " + old_value);
    text.replace(position, old_value.size(), new_value);
    return text;
}

std::string synthetic_control() {
    return R"(
! METDAT = ../../deliverables/met/met.dat !
! METFM = 1 !  * METFM = 2 *
! METRUN = 0 !
! NSECDT = 3600 !
! NSPEC = 2 !
! NSE = 1 !
! NX = 50 !
! NY = 50 !
! NZ = 9 !
! ZFACE = 0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000 !
! MGAUSS = 1 !
! MSLUG = 0 !
! MDISP = 3 !
! MCHEM = 0 !
! MWET = 0 !
! NDECAY = 1 !
! IOUTU = 3 !
! NPT1 = 1 !
! DGRIDKM = 0.1 !
! XORIGKM = 510.8846439571 !
! YORIGKM = 3531.2689269678 !
! IBYR = 2022 !
! IBMO = 1 !
! IBDY = 1 !
! IBHR = 0 !
! IBSEC = 0 !
! IEYR = 2022 !
! IEMO = 1 !
! IEDY = 6 !
! IEHR = 23 !
! IESEC = 0 !
! ABTZ = UTC+0000 !
! CSPEC = H-3 !  !END!
! CSPEC = HE-3 ! !END!
)";
}

CaseLedgerResult evaluate(const fs::path& met, const fs::path& control,
                          const std::string& concentration = {}, const std::string& met_pin = {},
                          const std::string& control_pin = {}) {
    CaseLedgerRequest request;
    request.met_path = met.string();
    request.control_path = control.string();
    request.concentration_path = concentration;
    request.expected_met_sha256 = met_pin;
    request.expected_control_sha256 = control_pin;
    return cteas::puff::evaluate_hefei_2022_case(request);
}

bool failed_check(const CaseLedgerResult& result, const std::string& name) {
    for (const auto& check : result.checks) {
        if (check.name == name) return check.refusal && !check.passed;
    }
    throw std::runtime_error("P7 CASE LEDGER TEST FAILURE: check never emitted: " + name);
}

void require_all_refusals_pass(const CaseLedgerResult& result) {
    for (const auto& check : result.checks) {
        if (check.refusal && !check.passed) {
            throw std::runtime_error("P7 CASE LEDGER TEST FAILURE: unexpected refusal: " + check.name +
                                     " expected=" + check.expected + " observed=" + check.observed);
        }
    }
}

void patch_f32(const fs::path& path, std::size_t offset, float value) {
    std::fstream file(path, std::ios::binary | std::ios::in | std::ios::out);
    require(bool(file), "cannot patch " + path.string());
    file.seekp(static_cast<std::streamoff>(offset));
    write_bytes(file, &value, sizeof(value));
}

void patch_i32(const fs::path& path, std::size_t offset, std::int32_t value) {
    std::fstream file(path, std::ios::binary | std::ios::in | std::ios::out);
    require(bool(file), "cannot patch " + path.string());
    file.seekp(static_cast<std::streamoff>(offset));
    write_bytes(file, &value, sizeof(value));
}

void test_sha256() {
    require(cteas::puff::sha256_hex("") ==
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "SHA-256 empty vector");
    require(cteas::puff::sha256_hex("abc") ==
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "SHA-256 abc vector");
    require(cteas::puff::sha256_hex(
                "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq") ==
                "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
            "SHA-256 56-byte vector");
    const std::string million(1000000, 'a');
    require(cteas::puff::sha256_hex(million) ==
                "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0",
            "SHA-256 one-million-a vector");
    cteas::puff::Sha256Hasher chunked;
    for (std::size_t start = 0; start < million.size(); start += 7) {
        chunked.update(std::string_view(million).substr(start, 7));
    }
    require(chunked.hex_digest() == cteas::puff::sha256_hex(million), "SHA-256 chunked equality");
    std::cout << "P7_LEDGER_SHA256_VECTORS=PASS\n";
}

void test_gregorian() {
    require(cteas::puff::gregorian_unix_seconds(2022, 1, 1, 0, 0) ==
                cteas::puff::Hefei2022Spec::first_unix_seconds,
            "2022-01-01T00:00Z instant");
    require(cteas::puff::gregorian_unix_seconds(2022, 1, 6, 23, 0) ==
                cteas::puff::Hefei2022Spec::final_unix_seconds,
            "2022-01-06T23:00Z instant");
    require(cteas::puff::Hefei2022Spec::final_unix_seconds -
                    cteas::puff::Hefei2022Spec::first_unix_seconds ==
                static_cast<std::int64_t>(cteas::puff::Hefei2022Spec::hourly_intervals) * 3600,
            "143 hourly intervals between the frozen endpoints");
    std::cout << "P7_LEDGER_GREGORIAN_2022_WINDOW=PASS\n";
}

} // namespace

int main() {
    try {
        test_sha256();
        test_gregorian();

        // The dedicated runner host is shared by three runner installations and
        // can execute two P7 jobs at once (for example a re-run of an older
        // commit next to a new commit), so the fixture directory must be unique
        // per process instead of a fixed /tmp path.
        std::random_device random;
        const fs::path root =
            fs::temp_directory_path() /
            ("p7-case-ledger-contract-" + std::to_string(random()) + "-" +
             std::to_string(std::chrono::high_resolution_clock::now().time_since_epoch().count()));
        fs::remove_all(root);
        fs::create_directories(root);
        const fs::path met = root / "met.dat";
        const fs::path small = root / "small.dat";
        const fs::path control = root / "puff.inp";
        const fs::path concentration = root / "puff.con";
        write_text(control, synthetic_control());
        const auto canonical_framing = write_synthetic_met(met, MetConfig{});

        // A 60x60x2 3-interval fixture keeps the refusal matrix cheap: it fails
        // nx/ny/nz and the frozen window, and its larger horizontal extent still
        // contains the frozen control grid so containment is exercised on its own.
        MetConfig small_config;
        small_config.nx = 60;
        small_config.ny = 60;
        small_config.nz = 2;
        small_config.origin_x_m = 510384.6439571;
        small_config.origin_y_m = 3530768.9269678;
        small_config.intervals = 3;
        const auto small_layout = write_synthetic_met(small, small_config);

        const auto accepted = evaluate(met, control);
        require(accepted.status == "ACCEPTED_CANONICAL_2022_PENDING_ORIGINAL_EXECUTION",
                "canonical synthetic 2022 case status: " + accepted.status);
        require(accepted.exit_code == 0 && accepted.canonical_2022, "canonical accepted flag");
        require(accepted.reference_class == "CANONICAL_2022_HEFEI_50X50_100M", "reference class");
        require_all_refusals_pass(accepted);
        require(accepted.artifacts.size() == 2, "two mandatory artifacts");
        require(accepted.artifacts.front().sha256.size() == 64, "artifact hash length");
        require(accepted.artifacts.front().sha256 == cteas::puff::sha256_hex_file(met.string()),
                "artifact hash equals direct hash");

        write_text(concentration, "synthetic concentration placeholder");
        const auto uppercase = [](std::string value) {
            std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
                return static_cast<char>(std::toupper(c));
            });
            return value;
        };
        const auto with_output = evaluate(met, control, {},
                                          uppercase(accepted.artifacts.front().sha256),
                                          uppercase(accepted.artifacts[1].sha256));
        require(with_output.status == "ACCEPTED_CANONICAL_2022_ORIGINAL_OUTPUT_PRESENT",
                "discovered concentration artifact status: " + with_output.status);
        require(with_output.exit_code == 0 && with_output.artifacts.size() == 3,
                "pinned canonical case with original output accepted");
        require_all_refusals_pass(with_output);
        fs::remove(concentration);

        const auto bad_pin = evaluate(small, control, {}, std::string(64, '0'), {});
        require(bad_pin.exit_code == 4 && failed_check(bad_pin, "original_met_dat_sha256_pin"),
                "wrong MET pin refused");

        const auto coarse = evaluate(small, control);
        require(coarse.exit_code == 4, "non-frozen synthetic fixture refused");
        for (const auto* name : {"met_nx", "met_ny", "met_nz", "met_hourly_intervals"}) {
            require(failed_check(coarse, name), std::string("small fixture refusal: ") + name);
        }
        require(!failed_check(coarse, "control_grid_within_met_domain"),
                "contained control grid must pass containment");

        patch_i32(small, small_layout.header_payload + 92, 3);
        const auto precip = evaluate(small, control);
        require(precip.exit_code == 4 && failed_check(precip, "met_precipitation_stations"),
                "precipitation stations refused");
        patch_i32(small, small_layout.header_payload + 92, 0);

        patch_f32(small, small_layout.header_payload + 68, 1000.0F);
        const auto coarse_dx = evaluate(small, control);
        require(coarse_dx.exit_code == 4 && failed_check(coarse_dx, "met_dx_m"),
                "1 km MET spacing refused");
        patch_f32(small, small_layout.header_payload + 68, 100.0F);

        patch_f32(small, small_layout.header_payload + 72, 475000.0F);
        const auto elsewhere = evaluate(small, control);
        require(elsewhere.exit_code == 4 &&
                    failed_check(elsewhere, "met_origin_inside_2022_crop_window"),
                "MET origin outside the 2022 crop refused");
        patch_f32(small, small_layout.header_payload + 72, 510384.6439571F);

        patch_i32(small, small_layout.first_field_payload + 8, 202300100);
        const auto shifted_time = evaluate(small, control);
        require(shifted_time.exit_code == 4 && failed_check(shifted_time, "original_met_dat_contract"),
                "shifted first-hour clock refused");
        patch_i32(small, small_layout.first_field_payload + 8, 202200100);

        const auto truncated = root / "truncated.dat";
        {
            std::ifstream source(small, std::ios::binary);
            std::vector<char> head(4096);
            source.read(head.data(), static_cast<std::streamsize>(head.size()));
            write_text(truncated, std::string(head.data(), head.size()));
        }
        const auto broken = evaluate(truncated, control);
        require(broken.exit_code == 4 && failed_check(broken, "original_met_dat_contract"),
                "truncated MET.DAT refused");

        MetConfig historical_config;
        historical_config.nx = 60;
        historical_config.ny = 60;
        historical_config.nz = 2;
        historical_config.dx_m = 1000.0;
        historical_config.origin_x_m = 475000.0;
        historical_config.origin_y_m = 3515436.0;
        historical_config.intervals = 119;
        historical_config.start_year = 2023;
        const fs::path historical = root / "historical-2023-like.dat";
        write_synthetic_met(historical, historical_config);
        const auto not_2022 = evaluate(historical, control);
        require(not_2022.exit_code == 4 && not_2022.status == "REJECTED_NOT_CANONICAL_2022",
                "non-2022 case refused");
        require(!not_2022.canonical_2022 && not_2022.reference_class == "NOT_CANONICAL_2022",
                "non-2022 reference class");
        for (const auto* name : {"met_dx_m", "met_hourly_intervals", "met_first_begin_unix_seconds",
                                 "met_final_end_unix_seconds", "met_origin_inside_2022_crop_window"}) {
            require(failed_check(not_2022, name), std::string("non-2022 refusal: ") + name);
        }

        const std::string base = synthetic_control();
        const auto mutate = [&](const std::string& old_value, const std::string& new_value) {
            const fs::path path = root / "mutated.inp";
            write_text(path, replace_once(base, old_value, new_value));
            return path;
        };
        const auto expect_control_refusal = [&](const char* name, const std::string& old_value,
                                                const std::string& new_value) {
            const auto result = evaluate(small, mutate(old_value, new_value));
            require(result.exit_code == 4, std::string("control mutation refused: ") + name);
            require(failed_check(result, name), std::string("control refusal check: ") + name);
        };
        expect_control_refusal("calpuff_control_contract", "! METDAT = ../../deliverables/met/met.dat !",
                               "! NOTMETDAT = ../../deliverables/met/met.dat !");
        expect_control_refusal("calpuff_control_contract",
                               "! ZFACE = 0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000 !",
                               "! ZFACE = 0, 20, 40, 80, 160, 320, 640, 1200, 2000 !");
        expect_control_refusal("calpuff_control_contract", "! NSE = 1 !", "! NSE = 3 !");
        expect_control_refusal("control_start_date", "! IBYR = 2022 !", "! IBYR = 2023 !");
        expect_control_refusal("control_end_date", "! IEHR = 23 !", "! IEHR = 22 !");
        expect_control_refusal("control_dgrid_km", "! DGRIDKM = 0.1 !", "! DGRIDKM = 1 !");
        expect_control_refusal("control_abtz", "! ABTZ = UTC+0000 !", "! ABTZ = UTC+0800 !");
        expect_control_refusal("control_point_sources", "! NPT1 = 1 !", "! NPT1 = 2 !");
        expect_control_refusal("control_nx", "! NX = 50 !", "! NX = 49 !");
        expect_control_refusal("control_grid_within_met_domain", "! XORIGKM = 510.8846439571 !",
                               "! XORIGKM = 470.000 !");

        const auto grid_mismatch = evaluate(small, mutate("! NX = 50 !", "! NX = 49 !"));
        require(failed_check(grid_mismatch, "grid_nx_matches_met"), "cross-file grid refusal");

        const auto blocked = evaluate(root / "absent.dat", control);
        require(blocked.status == "BLOCKED_MISSING_INPUTS" && blocked.exit_code == 3 &&
                    blocked.checks.empty() && !blocked.canonical_2022,
                "missing MET.DAT blocked");
        require(blocked.missing_roles.size() == 1 && blocked.missing_roles.front() == "original_met_dat",
                "blocked missing role name");
        const auto missing_control = evaluate(met, root / "absent.inp");
        require(missing_control.exit_code == 3, "missing control blocked");
        const auto missing_artifact = evaluate(met, control, (root / "absent.con").string());
        require(missing_artifact.exit_code == 3 && missing_artifact.missing_roles.size() == 1,
                "explicit missing concentration blocked");

        const auto document = cteas::puff::case_ledger_json(accepted);
        require(document.find("\"gate\": \"P7_HFEI_2022_CASE_EXECUTION_LEDGER\"") != std::string::npos,
                "ledger JSON gate");
        require(document.find("\"canonical_2022\": true") != std::string::npos, "ledger JSON flag");
        require(document.find("\"result\": \"FAIL\"") == std::string::npos,
                "accepted case has no failure row");
        const std::uintmax_t expected_bytes =
            300 + static_cast<std::uintmax_t>(cteas::puff::Hefei2022Spec::hourly_intervals) *
                      expected_labels(cteas::puff::Hefei2022Spec::nz).size() *
                      (4 + 24 + 4 * static_cast<std::size_t>(cteas::puff::Hefei2022Spec::nx *
                                                             cteas::puff::Hefei2022Spec::ny) + 4);
        require(fs::file_size(met) == expected_bytes,
                "canonical synthetic fixture does not cover all 143 frozen intervals");
        require(canonical_framing.header_payload == small_layout.header_payload &&
                    canonical_framing.first_field_payload == small_layout.first_field_payload,
                "fixture record framing must not depend on grid size");

        fs::remove_all(root);
        std::cout << "P7_LEDGER_ACCEPTED_CANONICAL_2022=PASS\n"
                     "P7_LEDGER_FAIL_CLOSED_REFUSALS=PASS\n"
                     "P7_LEDGER_BLOCKED_MISSING_INPUTS=PASS\n"
                     "P7_2022_LEDGER_IS_NOT_A_PHYSICS_PARITY_TEST=true\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 1;
    }
}
