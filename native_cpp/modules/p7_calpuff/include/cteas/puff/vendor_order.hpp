#pragma once
#include <array>
#include <cstddef>
#include <stdexcept>
#include <string_view>

namespace cteas::puff {

// One puff substep within original CALPUFF COMP, frozen 2022 METFM=1 path.
// Original source anchors are independently checked in the Python DGM oracle.
// This is a sequencing guard, NOT a replacement for the missing full driver.
// The selected dry/receptor path has additional conditional gates between SETPUF
// and late history; disabled CHEM/WET branches are not silently accepted.
enum class VendorSubstepPhase {
    SamplingCadence,         // COMP L10347
    LoadPreviousPuffState,   // COMP L10473
    ResolveMetCell,          // COMP L10487
    EvaluatePuffDz,         // COMP L10495
    EvaluateAdvect,         // COMP L10499
    ApplyRiseWindAndCalm,   // COMP L10528
    ChooseSubstepLength,    // COMP L10548-10582
    AdvancePosition,        // COMP L10607-10619
    ApplyVmass,             // COMP L10859 (pre-SETPUF)
    CommitSetpuf,           // COMP L10940-10942
    CommitNextStepHistory   // COMP L11391-11398, post-CALCPF
};

inline constexpr std::array<VendorSubstepPhase, 11> kVendorSubstepOrder{{
    VendorSubstepPhase::SamplingCadence,
    VendorSubstepPhase::LoadPreviousPuffState,
    VendorSubstepPhase::ResolveMetCell,
    VendorSubstepPhase::EvaluatePuffDz,
    VendorSubstepPhase::EvaluateAdvect,
    VendorSubstepPhase::ApplyRiseWindAndCalm,
    VendorSubstepPhase::ChooseSubstepLength,
    VendorSubstepPhase::AdvancePosition,
    VendorSubstepPhase::ApplyVmass,
    VendorSubstepPhase::CommitSetpuf,
    VendorSubstepPhase::CommitNextStepHistory,
}};

// A future original-equivalent C++ orchestrator MUST advance this guard
// *only after* the matching physics call completes, using the SAME puff state.
// Do not connect the non-vendor P7C absolute-UTM Runge-Kutta prototype here.
class VendorSubstepOrder {
public:
    // Enforce the optional physical stages only for explicitly enabled
    // coupling modes. The original QOLD snapshot is before DRY; receptor
    // CALCPF must finish before the next-step ZIOLD/ZIMAX/lid commit.
    explicit VendorSubstepOrder(bool dry_enabled=false,
                                bool receptors_enabled=false)
        : dry_enabled_(dry_enabled), receptors_enabled_(receptors_enabled) {}
    void captured_pre_removal_mass() {
        require_coupling_position();
        if (!(dry_enabled_ || receptors_enabled_) || qold_captured_)
            throw std::logic_error("P7 QOLD capture disabled or duplicated");
        qold_captured_ = true;
    }
    void dry_removal_completed() {
        require_coupling_position();
        if (!dry_enabled_ || !qold_captured_ || dry_completed_ ||
            receptor_completed_)
            throw std::logic_error("P7 DRY before QOLD, duplicated or after CALCPF");
        dry_completed_ = true;
    }
    void receptors_sampled() {
        require_coupling_position();
        if (!receptors_enabled_ || !qold_captured_ ||
            (dry_enabled_ && !dry_completed_) || receptor_completed_)
            throw std::logic_error("P7 CALCPF before QOLD/DRY or duplicated");
        receptor_completed_ = true;
    }
    void completed(VendorSubstepPhase phase) {
        if (next_ >= kVendorSubstepOrder.size() || phase != kVendorSubstepOrder[next_])
            throw std::logic_error("P7 original COMP phase order violation");
        const bool missing_qold=(dry_enabled_ || receptors_enabled_) &&
                                !qold_captured_;
        const bool missing_dry=dry_enabled_ && !dry_completed_;
        const bool missing_receptor=receptors_enabled_ && !receptor_completed_;
        if (phase == VendorSubstepPhase::CommitNextStepHistory &&
            (missing_qold || missing_dry || missing_receptor))
            throw std::logic_error("P7 next-step history before QOLD/DRY/CALCPF");
        ++next_;
    }
    [[nodiscard]] bool complete() const noexcept { return next_ == kVendorSubstepOrder.size(); }
    [[nodiscard]] std::size_t next_index() const noexcept { return next_; }
    void finish() const {
        if (!complete()) throw std::logic_error("P7 original COMP substep incomplete");
    }
    void begin_next_substep() {
        finish();
        next_ = 0U;
        qold_captured_ = dry_completed_ = receptor_completed_ = false;
    }
private:
    void require_coupling_position() const {
        // The only valid seam is after SETPUF and before late history.
        if (next_ != kVendorSubstepOrder.size()-1U)
            throw std::logic_error("P7 coupling outside SETPUF/history seam");
    }
    std::size_t next_ = 0U;
    bool dry_enabled_ = false;
    bool receptors_enabled_ = false;
    bool qold_captured_ = false;
    bool dry_completed_ = false;
    bool receptor_completed_ = false;
};
} // namespace cteas::puff
