#pragma once
// CALMET 6.5.0 selected Hefei 2022 single-pass COMP/DIAGNO hour authority.
//
// This is a scheduler/physics adapter contract. It does NOT claim that the
// monolithic P6D/P6E executable drivers have been adapted to these callbacks,
// or that independently generated 143h CALMET.DAT has passed scientific parity.
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6 {

enum class NativeHourStage {
    PrepdiPreviousZiconv,
    DiagnoWind1,
    DiagnoFradj,
    DiagnoHeatfx,
    DiagnoAirden,
    DiagnoElustr,
    DiagnoSlope,
    DiagnoWindbcFirstGuess,
    DiagnoStheorElustr2Mixhtst,
    DiagnoInter2,
    DiagnoWindbcPostInter2Htfac1,
    DiagnoSmoothDivcelW,
    CompGridMixht,
    CompAvemix,
    CompWstarr,
    CompTemp3d,
    CommitOutput
};

constexpr std::array<NativeHourStage, 17> kHefeiOriginalStageOrder = {
    NativeHourStage::PrepdiPreviousZiconv,
    NativeHourStage::DiagnoWind1,
    NativeHourStage::DiagnoFradj,
    NativeHourStage::DiagnoHeatfx,
    NativeHourStage::DiagnoAirden,
    NativeHourStage::DiagnoElustr,
    NativeHourStage::DiagnoSlope,
    NativeHourStage::DiagnoWindbcFirstGuess,
    NativeHourStage::DiagnoStheorElustr2Mixhtst,
    NativeHourStage::DiagnoInter2,
    NativeHourStage::DiagnoWindbcPostInter2Htfac1,
    NativeHourStage::DiagnoSmoothDivcelW,
    NativeHourStage::CompGridMixht,
    NativeHourStage::CompAvemix,
    NativeHourStage::CompWstarr,
    NativeHourStage::CompTemp3d,
    NativeHourStage::CommitOutput
};

enum class NativeHourSource {
    NativeCpp,
    OriginalFortranOracle,
    FrozenReferenceBackfill,
    Unknown
};

struct NativeGridMemory {
    // REAL*4 COMMON-state semantics: this is the committed preceding hour.
    // DPTT is a temperature jump and may legitimately be negative.
    std::vector<float> zi_m;
    std::vector<float> ziconv_m;
    std::vector<float> dptt_k;
};

struct NativeHourFields {
    // Hour-major is outside this interface. Each hour is k-major/i-fastest.
    std::vector<float> u_mps, v_mps, w_face_mps;
    std::vector<float> temperature_k;
    // P6E native grid fields; the full CALMET.DAT record set is a separate G4 gate.
    std::vector<float> qh_wm2, ustar_mps, el_m, wstar_mps;
};

struct NativeHourInput {
    std::size_t hour_index = 0; // 0 .. 142, no skipped/repeated hours
    int htfac = 1;             // selected original Hefei 2022 route only
    std::string utc_label;     // original hourly provenance label
};

struct NativeHourFrame {
    NativeHourInput input;
    const NativeGridMemory& previous; // never current-hour P6E state
    NativeGridMemory next;            // committed only after full COMP
    NativeHourFields fields;          // independently computed physical fields
};

struct NativeHourStageResult {
    NativeHourSource source = NativeHourSource::Unknown;
    bool completed = false;
};

class NativeHourPhysics {
public:
    virtual ~NativeHourPhysics() = default;
    // Each stage must call its native kernel, not a frozen-reference lookup.
    // State writes to frame.next remain uncommitted until all stages complete.
    virtual NativeHourStageResult run(
        NativeHourStage stage, NativeHourFrame& frame) = 0;
};

class P6SinglePassHourlyScheduler {
public:
    explicit P6SinglePassHourlyScheduler(std::size_t nx, std::size_t ny,
                                         std::size_t nz = 9)
        : nx_(nx), ny_(ny), nz_(nz),
          memory_{std::vector<float>(nx*ny, 0.0f),
                  std::vector<float>(nx*ny, 0.0f),
                  std::vector<float>(nx*ny, 0.0f)} {
        if (nx_ != 50 || ny_ != 50 || nz_ != 9)
            throw std::invalid_argument(
                "single-pass scheduler currently supports only locked 50x50x9 Hefei");
    }

    std::size_t completed_hours() const noexcept { return completed_; }
    const NativeGridMemory& committed_memory() const noexcept { return memory_; }

    void advance(const NativeHourInput& input, NativeHourPhysics& physics) {
        if (completed_ >= 143 || input.hour_index != completed_ ||
            input.htfac != 1 || input.utc_label.empty())
            throw std::invalid_argument(
                "hour must be consecutive, inside 143, labeled and HTFAC=1");
        // The prior hour is kept immutable throughout PREPDI -> DIAGNO ->
        // COMP. Specifically, CGAMMA may read previous.ziconv_m only here;
        // station DPTT mutation during DIAGNO goes into next, before MIXHT.
        NativeHourFrame frame{input, memory_, memory_, {}};
        for (NativeHourStage stage : kHefeiOriginalStageOrder) {
            const auto result = physics.run(stage, frame);
            if (!result.completed || result.source != NativeHourSource::NativeCpp)
                throw std::runtime_error(
                    "CALMET native stage missing or original oracle/backfill used");
        }
        validate_memory(frame.next);
        validate_fields(frame.fields);
        // Atomic logical commit: exceptions above do not advance the clock
        // or the previous-hour thermal memory. No full-period second pass.
        memory_ = std::move(frame.next);
        ++completed_;
    }

    void require_frozen_case_complete() const {
        if (completed_ != 143)
            throw std::runtime_error("143 consecutive native hours required");
    }

private:
    static void validate_array(const std::vector<float>& values,
                               std::size_t expected, const char* label) {
        if (values.size() != expected)
            throw std::runtime_error(std::string("unproduced native field: ") + label);
        for (float value : values)
            if (!std::isfinite(value) || value == 9999.0f)
                throw std::runtime_error(std::string("invalid native value: ") + label);
    }

    void validate_memory(const NativeGridMemory& state) const {
        const std::size_t n = nx_ * ny_;
        validate_array(state.zi_m, n, "ZI");
        validate_array(state.ziconv_m, n, "ZICONV");
        validate_array(state.dptt_k, n, "DPTT");
        for (std::size_t i = 0; i < n; ++i)
            if (state.zi_m[i] < 0.0f || state.ziconv_m[i] < 0.0f)
                throw std::runtime_error("negative ZI or ZICONV");
    }

    void validate_fields(const NativeHourFields& f) const {
        const std::size_t n = nx_ * ny_, three = n * nz_;
        validate_array(f.u_mps, three, "U");
        validate_array(f.v_mps, three, "V");
        validate_array(f.w_face_mps, n * (nz_ + 1U), "WFACE_ALL_NZ_PLUS_ONE_FACES");
        validate_array(f.temperature_k, three, "TEMP3D");
        validate_array(f.qh_wm2, n, "QH");
        validate_array(f.ustar_mps, n, "USTAR");
        validate_array(f.el_m, n, "EL");
        validate_array(f.wstar_mps, n, "WSTAR");
    }

    std::size_t nx_, ny_, nz_;
    std::size_t completed_ = 0;
    NativeGridMemory memory_;
};

} // namespace cteas::calmet::p6
