#pragma once
// G18E8: selected-only P6F CommitOutput stage (original G14 slot 16).
// The SAME live G14 frame must contain complete, stage-computed G18E7 COMP
// fields/memory. Reuses G18C5 (45 fields), G18C6 (original CALMET.DAT
// framing), and G18D1 (exact G14/P6F precommit) without any replacement
// serializer, MET.DAT backfill, or second hour authority.
// No disk publication here: these are PREPARED bytes for G14 precommit.
// Test-scoped, NOT a verified production multistation CALMET implementation.
#include "cteas/p6/p6g_g18e7_live_comp_stage_adapter.hpp"
#include "cteas/p6/p6g_g18d1_p6f_precommit.hpp"
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
class G18E8SelectedP6fCommitStageAdapter final : public MultiHourPhysics {
public:
    G18E8SelectedP6fCommitStageAdapter(
        const G18E7SelectedLiveCompStageAdapter& comp,
        const G18E2SelectedHeatfxStageAdapter& heat,
        std::string original_metinp)
        : comp_(comp),heat_(heat),deck_(std::move(original_metinp)) {}

    p6::NativeHourStageResult run(
        p6::NativeHourStage,MultiHourFrame&) override {
        return {p6::NativeHourSource::Unknown,false};
    }

    void run_selected(p6::NativeHourStage stage,MultiHourFrame& frame,
                      bool explicitly_test_only) {
        static_assert(p6::kHefeiOriginalStageOrder[16] ==
                      p6::NativeHourStage::CommitOutput);
        if(!explicitly_test_only || prepared_.has_value() ||
           stage!=p6::kHefeiOriginalStageOrder[16] ||
           !frame.source_controls || frame.input.end!=frame.surface.end)
            throw std::invalid_argument(
                "G18E8 requires selected original G14 slot 16 only");
        const auto& candidate=comp_.selected_candidate_for(frame);
        const auto& heat=heat_.selected_heat_for(frame);
        const auto& fields=candidate.candidate_fields;
        const auto& memory=candidate.candidate_memory;
        // A valid P6F file constructed from a detached, old, or changed
        // candidate must never certify the current frame's physics.
        if(candidate.end!=frame.input.end ||
           frame.fields.u_mps!=fields.u_mps ||
           frame.fields.v_mps!=fields.v_mps ||
           frame.fields.w_face_mps!=fields.w_face_mps ||
           frame.fields.temperature_k!=fields.temperature_k ||
           frame.fields.qh_wm2!=fields.qh_wm2 ||
           frame.fields.ustar_mps!=fields.ustar_mps ||
           frame.fields.el_m!=fields.el_m ||
           frame.fields.wstar_mps!=fields.wstar_mps ||
           frame.next.zi_m!=memory.zi_m ||
           frame.next.ziconv_m!=memory.ziconv_m ||
           frame.next.dptt_k!=memory.dptt_k)
            throw std::invalid_argument(
                "G18E8 current G14 state differs from complete staged COMP");
        // All 45 selected source values and the original output contract
        // come from the physical G17/G18 kernels and the existing P6F
        // writer. No pre-commit file publication or state mutation occurs.
        const auto records=g18c5_selected_p6f_fields(
            frame,heat,candidate,deck_,true);
        const auto dataset=g18c6_selected_one_hour_dataset(
            frame,records,heat.nearest_surface,deck_,true);
        auto bytes=g18d1_validate_p6f_precommit(frame,dataset);
        if(bytes.empty())
            throw std::runtime_error("G18E8 prepared empty source P6F byte image");
        // Publish to this test-scoped adapter only after ALL source checks
        // succeeded. A failure leaves the hour and byte image uncommitted.
        prepared_.emplace(std::move(bytes));
        frame_=&frame;
        previous_=frame.previous;
        hour_index_=frame.hour_index;
        end_=frame.input.end;
    }

    [[nodiscard]] const std::vector<std::uint8_t>& selected_bytes_for(
        const MultiHourFrame& frame) const {
        if(!prepared_ || &frame!=frame_ ||
           frame.hour_index!=hour_index_ || frame.input.end!=end_ ||
           frame.previous.zi_m!=previous_.zi_m ||
           frame.previous.ziconv_m!=previous_.ziconv_m ||
           frame.previous.dptt_k!=previous_.dptt_k)
            throw std::logic_error(
                "G18E8 P6F prepared bytes cross G14 hour/commit boundary");
        const auto& candidate=comp_.selected_candidate_for(frame);
        const auto& fields=candidate.candidate_fields;
        const auto& memory=candidate.candidate_memory;
        if(frame.fields.u_mps!=fields.u_mps ||
           frame.fields.v_mps!=fields.v_mps ||
           frame.fields.w_face_mps!=fields.w_face_mps ||
           frame.fields.temperature_k!=fields.temperature_k ||
           frame.fields.qh_wm2!=fields.qh_wm2 ||
           frame.fields.ustar_mps!=fields.ustar_mps ||
           frame.fields.el_m!=fields.el_m ||
           frame.fields.wstar_mps!=fields.wstar_mps ||
           frame.next.zi_m!=memory.zi_m ||
           frame.next.ziconv_m!=memory.ziconv_m ||
           frame.next.dptt_k!=memory.dptt_k)
            throw std::logic_error(
                "G18E8 prepared byte image outlived original G14 field state");
        return *prepared_;
    }

private:
    const G18E7SelectedLiveCompStageAdapter& comp_;
    const G18E2SelectedHeatfxStageAdapter& heat_;
    std::string deck_;
    std::optional<std::vector<std::uint8_t>> prepared_;
    const MultiHourFrame* frame_=nullptr;
    p6::NativeGridMemory previous_;
    std::chrono::sys_seconds end_{};
    std::size_t hour_index_=0;
};
} // namespace cteas::calmet::p6g
