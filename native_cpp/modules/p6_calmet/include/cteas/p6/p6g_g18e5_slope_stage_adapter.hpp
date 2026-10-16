#pragma once
// G18E5: execute the frozen G17/PR #53 SLOPE kernel at original G14
// DIAGNO slot 6, using the SAME selected G18E2 HEATFX and G18E3 ELUSTR
// physical state. Stable ELUSTR may replace HEATFX QH; do not re-use
// the pre-ELUSTR flux or the pre-FRADJ SURFVAR temperature.
// Fixture-scoped only: no production MultiHourPhysics acceptance.
#include "cteas/p6/p6g_g18e3_airden_elustr_stage_adapter.hpp"
#include <chrono>
#include <cstddef>
#include <stdexcept>

namespace cteas::calmet::p6g {
class G18E5SelectedSlopeStageAdapter final : public MultiHourPhysics {
public:
    G18E5SelectedSlopeStageAdapter(
        G17SelectedTerrainFixturePhysics& terrain,
        const G18E2SelectedHeatfxStageAdapter& heat,
        const G18E3SelectedAirdenElustrStageAdapter& elustr)
        : terrain_(terrain), heat_(heat), elustr_(elustr) {}

    p6::NativeHourStageResult run(
        p6::NativeHourStage, MultiHourFrame&) override {
        return {p6::NativeHourSource::Unknown,false};
    }

    void run_selected(p6::NativeHourStage stage, MultiHourFrame& frame,
                      bool explicitly_test_only) {
        static_assert(p6::kHefeiOriginalStageOrder[6] ==
                      p6::NativeHourStage::DiagnoSlope);
        if(!explicitly_test_only || completed_ ||
           stage!=p6::kHefeiOriginalStageOrder[6] ||
           !frame.source_controls || frame.input.end!=frame.surface.end)
            throw std::invalid_argument(
                "G18E5 SLOPE requires original G14 post-ELUSTR stage");
        const auto& heat=heat_.selected_heat_for(frame);
        const auto& elustr=elustr_.selected_elustr_for(frame);
        if(heat.end!=frame.input.end || elustr.end!=frame.input.end ||
           elustr.qh_wm2.size()!=heat.temperature_k.size())
            throw std::invalid_argument(
                "G18E5 SLOPE heat/ELUSTR source-hour mismatch");
        // G17's original SLOPE implementation already validates the
        // post-FRADJ temperature and calls the unmodified PR #53 kernel.
        terrain_.provide_slope_heat(elustr.selected_slope_fixture(heat));
        const auto result=terrain_.run(stage,frame);
        if(!result.completed || result.source!=p6::NativeHourSource::NativeCpp)
            throw std::runtime_error(
                "G18E5 native SLOPE kernel rejected source ELUSTR QH");
        frame_=&frame;
        hour_index_=frame.hour_index;
        source_end_=frame.input.end;
        previous_=frame.previous;
        completed_=true;
    }

    [[nodiscard]] const p6::WindUV& selected_slope_wind_for(
        const MultiHourFrame& frame) const {
        if(!completed_ || &frame!=frame_ ||
           frame.hour_index!=hour_index_ || frame.input.end!=source_end_ ||
           frame.previous.zi_m!=previous_.zi_m ||
           frame.previous.ziconv_m!=previous_.ziconv_m ||
           frame.previous.dptt_k!=previous_.dptt_k)
            throw std::logic_error(
                "G18E5 SLOPE result crossed original G14 transaction");
        return terrain_.after_slope();
    }

private:
    G17SelectedTerrainFixturePhysics& terrain_;
    const G18E2SelectedHeatfxStageAdapter& heat_;
    const G18E3SelectedAirdenElustrStageAdapter& elustr_;
    const MultiHourFrame* frame_=nullptr;
    p6::NativeGridMemory previous_;
    std::chrono::sys_seconds source_end_{};
    std::size_t hour_index_=0;
    bool completed_=false;
};
} // namespace cteas::calmet::p6g
