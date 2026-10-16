#pragma once
// G18E2: source-observed 2SS IAVET=1 HEATFX executed at the frozen G14
// DIAGNO HEATFX stage slot, after native FRADJ and both original SURFVAR
// passes. Reuses PR #53's HEATFX kernel through G17C; never duplicates it.
// Source coefficients and water-QH inputs are explicitly TEST-scoped:
// this is NOT a production 17-stage NativeCpp implementation.
#include "cteas/p6/p6g_g17c_iavet1_heat_handoff.hpp"
#include <chrono>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <utility>

namespace cteas::calmet::p6g {
class G18E2SelectedHeatfxStageAdapter final : public MultiHourPhysics {
public:
    G18E2SelectedHeatfxStageAdapter(
        G17SelectedTerrainFixturePhysics& terrain,
        const G17B4TwoPassSurfvar& surface,
        G17CSelectedHeatInputs controls)
        : terrain_(terrain), surface_(surface),
          controls_(std::move(controls)) {}

    p6::NativeHourStageResult run(
        p6::NativeHourStage,MultiHourFrame&) override {
        return {p6::NativeHourSource::Unknown,false};
    }

    void run_selected(p6::NativeHourStage stage,MultiHourFrame& frame,
                      bool explicitly_test_only) {
        static_assert(p6::kHefeiOriginalStageOrder[3]==
                      p6::NativeHourStage::DiagnoHeatfx);
        if(!explicitly_test_only||!controls_.explicitly_test_only||
           heat_.has_value()||stage!=p6::kHefeiOriginalStageOrder[3]||
           !frame.source_controls||
           frame.input.end!=frame.surface.end||
           surface_.end()!=frame.input.end||
           !surface_.first_ready()||!surface_.second_ready())
            throw std::invalid_argument(
                "G18E2 HEATFX requires G14 source-hour post-FRADJ IAVET");
        // Cannot be called before the REAL selected G17 FRADJ stage.
        // The second SURFVAR temperature is a function of these exact winds.
        const auto& fradj=terrain_.after_fradj();
        if(!surface_.second_stage_wind_matches(fradj.u,fradj.v))
            throw std::invalid_argument(
                "G18E2 HEATFX cannot consume detached/obsolete FRADJ wind");
        const auto candidate=selected_iavet1_heat_after_fradj(
            frame.grid,frame.stations,frame.surface,surface_,controls_);
        heat_.emplace(candidate);
        frame_= &frame;
        hour_index_=frame.hour_index;
        source_end_=frame.input.end;
        previous_=frame.previous;
    }

    [[nodiscard]] const G17CSelectedHeatResult& selected_heat_for(
        const MultiHourFrame& frame) const {
        if(!heat_||&frame!=frame_||frame.hour_index!=hour_index_||
           frame.input.end!=source_end_||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k)
            throw std::logic_error(
                "G18E2 HEATFX source stage belongs to a different G14 transaction");
        return *heat_;
    }

private:
    G17SelectedTerrainFixturePhysics& terrain_;
    const G17B4TwoPassSurfvar& surface_;
    G17CSelectedHeatInputs controls_;
    std::optional<G17CSelectedHeatResult> heat_;
    const MultiHourFrame* frame_=nullptr;
    std::chrono::sys_seconds source_end_{};
    std::size_t hour_index_=0;
    p6::NativeGridMemory previous_;
};
} // namespace cteas::calmet::p6g
