#pragma once
// P6A: precise, fail-closed scientific data contracts for the Hefei case.
//
// Scope: geometry, timestamps, validity masks, and selected control-mode
// compatibility ONLY. No CALMET wind, energy, turbulence or output physics
// is implemented here. Original CALMET 6.5.0 remains the numerical authority.
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6 {

class ContractError final : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};
inline void require(bool condition, const char* why) {
    if (!condition) throw ContractError(why);
}

// Explicit distinction between absence and any possible physical numeric
// value, including zero wind, zero precipitation and below-MSL elevations.
struct Sample {
    double value = 0.0;
    bool valid = false;

    static Sample observed(double v) {
        require(std::isfinite(v), "valid sample must be finite");
        return {v, true};
    }
    static Sample missing() noexcept { return {}; }
    void validate() const {
        if (valid) require(std::isfinite(value), "nonfinite valid sample");
    }
};

struct Geometry {
    int nx = 0;
    int ny = 0;
    int utm_zone = 0;
    bool northern_hemisphere = true;
    std::string datum;
    double southwest_x_km = std::numeric_limits<double>::quiet_NaN();
    double southwest_y_km = std::numeric_limits<double>::quiet_NaN();
    double spacing_km = std::numeric_limits<double>::quiet_NaN();
    // Model cell-face heights in metres, measured AGL. CALMET's actual
    // terrain-following z rules must still be verified from the original.
    std::vector<double> zfaces_agl_m;

    void validate_hefei_100m() const {
        require(nx == 50 && ny == 50, "only 50x50 study grid supported");
        require(utm_zone == 50 && northern_hemisphere && datum == "WGS-84",
                "only study UTM 50N WGS-84 supported");
        require(std::isfinite(southwest_x_km) &&
                    std::isfinite(southwest_y_km),
                "undefined grid origin");
        require(std::isfinite(spacing_km) &&
                    std::abs(spacing_km - 0.1) <= 1.0e-12,
                "only 100 m horizontal grid supported");
        constexpr std::array<double, 10> faces{
            0., 20., 40., 80., 160., 320., 640., 1200., 2000., 3000.
        };
        require(zfaces_agl_m.size() == faces.size(),
                "9 model layers require ten ZFACE entries");
        for (std::size_t k = 0; k < faces.size(); ++k) {
            require(std::isfinite(zfaces_agl_m[k]) &&
                        std::abs(zfaces_agl_m[k] - faces[k]) <= 1.0e-10,
                    "unexpected ZFACE or vertical coordinate unit");
            if (k) require(zfaces_agl_m[k] > zfaces_agl_m[k - 1],
                           "ZFACE must increase");
        }
    }

    [[nodiscard]] std::size_t layer_count() const {
        require(zfaces_agl_m.size() >= 2, "missing vertical layer faces");
        return zfaces_agl_m.size() - 1;
    }
    [[nodiscard]] std::size_t grid_index(int i, int j) const {
        require(i >= 0 && i < nx && j >= 0 && j < ny,
                "grid index outside domain");
        return static_cast<std::size_t>(j) * static_cast<std::size_t>(nx) +
               static_cast<std::size_t>(i);
    }
    [[nodiscard]] std::size_t layer_index(int i, int j, int k) const {
        require(k >= 0 && static_cast<std::size_t>(k) < layer_count(),
                "model layer index outside domain");
        return static_cast<std::size_t>(k) *
                   static_cast<std::size_t>(nx) *
                   static_cast<std::size_t>(ny) + grid_index(i, j);
    }
    [[nodiscard]] double cell_center_x_km(int i) const {
        require(i >= 0 && i < nx, "bad i index");
        return southwest_x_km + (static_cast<double>(i) + 0.5) * spacing_km;
    }
    [[nodiscard]] double cell_center_y_km(int j) const {
        require(j >= 0 && j < ny, "bad j index");
        return southwest_y_km + (static_cast<double>(j) + 0.5) * spacing_km;
    }
};

struct Timestamp {
    int year = 0;
    unsigned month = 0;
    unsigned day = 0;
    int hour = 0;
    int minute = 0;
    int second = 0;

    [[nodiscard]] std::chrono::sys_seconds absolute_utc() const {
        using namespace std::chrono;
        require(hour >= 0 && hour < 24 && minute >= 0 && minute < 60 &&
                    second >= 0 && second < 60,
                "invalid UTC clock");
        const year_month_day ymd{std::chrono::year{year},
                                 std::chrono::month{month},
                                 std::chrono::day{day}};
        require(ymd.ok(), "invalid UTC calendar date");
        return sys_days{ymd} + hours{hour} + minutes{minute} + seconds{second};
    }
};

struct Window {
    Timestamp first_label;
    Timestamp last_label;
    int model_seconds = 3600;
    std::string reference_timezone = "UTC+0000";

    // This is a count of nominal clock labels, not a claim that original
    // CALMET emits this many records: file timestamp semantics remain gated.
    [[nodiscard]] std::size_t nominal_label_count() const {
        require(reference_timezone == "UTC+0000", "UTC conversion unresolved");
        require(model_seconds == 3600, "subhourly timesteps unsupported");
        const auto begin = first_label.absolute_utc();
        const auto end = last_label.absolute_utc();
        require(end >= begin, "end before start");
        const auto seconds =
            std::chrono::duration_cast<std::chrono::seconds>(end - begin).count();
        require(seconds % model_seconds == 0,
                "end timestamp is not on the hourly grid");
        require(seconds <= 60LL * 60LL * 24LL * 366LL,
                "window exceeds P6A safety bound");
        return static_cast<std::size_t>(seconds / model_seconds + 1);
    }
};

struct ObservationModes {
    int noobs = 0;
    int iprog = 0;
    int iwfcod = 1;
    int irtype = 1;
    int itprog = 0;
    int irhprog = 0;
    int surface_format = 2; // IFORMS, original formatted input
    int precip_format = 2;  // IFORMP, original formatted input
    int saved_output_format = 1;  // IFORMO, confirm with original
    bool diagnostic_wind = true;

    void validate_selected_path() const {
        require(noobs == 0 && iprog == 0 && iwfcod == 1 &&
                    irtype == 1 && itprog == 0 && irhprog == 0,
                "selected P6 path requires observed diagnostic wind and full micromet");
        require(diagnostic_wind, "wind-only/objective-only replacement unsupported");
        require(surface_format == 2 && precip_format == 2,
                "unverified source meteorological file format");
        require(saved_output_format == 1, "unverified output file format");
    }
};

struct ForcingInventory {
    bool geo_dat_p3_verified = false;
    bool surf_dat_p5_fortran_verified = false;
    bool upper_dat_p4_fortran_verified = false;
    // NPSTA=0 is an explicit original CALMET observation-mode choice:
    // the diagnostic+micrometeorology run can be valid with no rainfall
    // grid. This DOES NOT satisfy CALPUFF wet-deposition scientific needs.
    bool precipitation_mode_explicitly_confirmed = false;
    bool precipitation_input_verified = false;
    int n_surface_stations = 0;
    int n_upper_stations = 0;
    int n_precip_stations = 0;

    [[nodiscard]] bool can_attempt_full_reference_run() const noexcept {
        return geo_dat_p3_verified && surf_dat_p5_fortran_verified &&
               upper_dat_p4_fortran_verified &&
               n_surface_stations > 0 && n_upper_stations > 0 &&
               precipitation_mode_explicitly_confirmed &&
               n_precip_stations >= 0 &&
               (n_precip_stations == 0 || precipitation_input_verified);
    }
    [[nodiscard]] bool can_claim_wet_deposition_forcing() const noexcept {
        return can_attempt_full_reference_run() &&
               n_precip_stations > 0 && precipitation_input_verified;
    }
    void require_full_reference_ready() const {
        require(can_attempt_full_reference_run(),
                "P6 original diagnostic reference blocked by station or explicit precip-mode contract");
    }
    void require_wet_deposition_forcing() const {
        require(can_claim_wet_deposition_forcing(),
                "P6 NPSTA=0 can run but does not provide verified precipitation for wet deposition");
    }
};

// No wind solver exists in P6A. This class only enforces array indexing,
// missingness and valid finite numbers, independent of float sentinel values.
class MaskedField3D final {
public:
    explicit MaskedField3D(const Geometry& g) : geometry_(g) {
        g.validate_hefei_100m();
        elements_.resize(static_cast<std::size_t>(g.nx) *
                         static_cast<std::size_t>(g.ny) * g.layer_count());
    }

    void set(int i, int j, int k, Sample value) {
        value.validate();
        elements_.at(geometry_.layer_index(i, j, k)) = value;
    }
    [[nodiscard]] Sample get(int i, int j, int k) const {
        return elements_.at(geometry_.layer_index(i, j, k));
    }
    [[nodiscard]] std::size_t size() const noexcept {
        return elements_.size();
    }
private:
    Geometry geometry_;
    std::vector<Sample> elements_;
};

} // namespace cteas::calmet::p6
