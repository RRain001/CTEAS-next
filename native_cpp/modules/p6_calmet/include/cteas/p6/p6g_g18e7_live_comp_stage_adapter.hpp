#pragma once
// G18E7: connect the four existing original G18D4 COMP kernels directly
// to the SAME live G14 frame whose actual selected DIAGNO tail created
// U/V/W, whose STHEOR produced station columns, and whose thermal stages
// produced HEATFX and post-ELUSTR source fields.
// TEST-ONLY selected fixture route, not real-vendor multi-hour science parity.
#include "cteas/p6/p6g_g18d4_comp_stage_adapter.hpp"
#include "cteas/p6/p6g_g18e6_wind_tail_stage_adapter.hpp"
#include <chrono>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <utility>

namespace cteas::calmet::p6g {
class G18E7SelectedLiveCompStageAdapter final : public MultiHourPhysics {
public:
    G18E7SelectedLiveCompStageAdapter(
        const G18E6SelectedWindTailStageAdapter& wind,
        const G18E1SelectedStheorStageAdapter& stheor,
        const G18E2SelectedHeatfxStageAdapter& heat,
        const G18E3SelectedAirdenElustrStageAdapter& elustr,
        G18BUpperHour upper,
        G18ASelectedCompControls mixht,
        G18C1AvemixControls avemix,
        G18C3Temp3dControls temp3d)
        : wind_(wind), stheor_(stheor), heat_(heat), elustr_(elustr),
          upper_(std::move(upper)), mixht_(std::move(mixht)),
          avemix_(avemix), temp3d_(temp3d) {}

    p6::NativeHourStageResult run(
        p6::NativeHourStage, MultiHourFrame&) override {
        return {p6::NativeHourSource::Unknown,false};
    }

    void run_selected(p6::NativeHourStage stage, MultiHourFrame& frame,
                      bool explicitly_test_only) {
        static_assert(p6::kHefeiOriginalStageOrder[12] ==
                      p6::NativeHourStage::CompGridMixht);
        static_assert(p6::kHefeiOriginalStageOrder[15] ==
                      p6::NativeHourStage::CompTemp3d);
        static constexpr p6::NativeHourStage order[]={
            p6::NativeHourStage::CompGridMixht,
            p6::NativeHourStage::CompAvemix,
            p6::NativeHourStage::CompWstarr,
            p6::NativeHourStage::CompTemp3d
        };
        if(!explicitly_test_only || phase_>=4 ||
           stage!=order[phase_] || !frame.source_controls ||
           frame.input.end!=frame.surface.end ||
           upper_.end!=frame.input.end)
            throw std::invalid_argument(
                "G18E7 requires original G14 COMP stage and source hour");
        const auto& physical_wind=wind_.selected_wind_for_comp(frame);
        if(frame.fields.u_mps!=physical_wind.u_mps ||
           frame.fields.v_mps!=physical_wind.v_mps ||
           frame.fields.w_face_mps!=physical_wind.w_face_mps)
            throw std::invalid_argument(
                "G18E7 refuses copied or replaced DIAGNO U/V/W");
        if(phase_==0) {
            const auto& heat=heat_.selected_heat_for(frame);
            const auto& elustr=elustr_.selected_elustr_for(frame);
            const auto& stations=stheor_.stations_for_comp(frame);
            // Reuse original source-tested COMP stage implementation.
            // No independent MIXHT/AVEMIX/WSTAR/TEMP3D formula is written.
            comp_.emplace(heat,elustr,stations,upper_,
                          mixht_,avemix_,temp3d_);
        } else {
            if(!comp_ || &frame!=frame_ ||
               frame.hour_index!=hour_index_ ||
               frame.input.end!=source_end_ ||
               frame.previous.zi_m!=previous_.zi_m ||
               frame.previous.ziconv_m!=previous_.ziconv_m ||
               frame.previous.dptt_k!=previous_.dptt_k)
                throw std::logic_error(
                    "G18E7 COMP crossed authoritative G14 hour/state");
            (void)stheor_.stations_for_comp(frame);
        }
        comp_->run_selected(stage,frame,true);
        if(phase_==0) {
            frame_=&frame;
            source_end_=frame.input.end;
            hour_index_=frame.hour_index;
            previous_=frame.previous;
        }
        ++phase_;
    }

    [[nodiscard]] const G18C4SelectedCandidate& selected_candidate_for(
        const MultiHourFrame& frame) const {
        if(phase_!=4 || !comp_ || &frame!=frame_ ||
           frame.hour_index!=hour_index_ ||
           frame.input.end!=source_end_ ||
           frame.previous.zi_m!=previous_.zi_m ||
           frame.previous.ziconv_m!=previous_.ziconv_m ||
           frame.previous.dptt_k!=previous_.dptt_k)
            throw std::logic_error(
                "G18E7 cannot expose partial or foreign COMP source hour");
        return comp_->selected_candidate();
    }

private:
    const G18E6SelectedWindTailStageAdapter& wind_;
    const G18E1SelectedStheorStageAdapter& stheor_;
    const G18E2SelectedHeatfxStageAdapter& heat_;
    const G18E3SelectedAirdenElustrStageAdapter& elustr_;
    G18BUpperHour upper_;
    G18ASelectedCompControls mixht_;
    G18C1AvemixControls avemix_;
    G18C3Temp3dControls temp3d_;
    std::optional<G18D4SelectedCompStageAdapter> comp_;
    const MultiHourFrame* frame_=nullptr;
    p6::NativeGridMemory previous_;
    std::chrono::sys_seconds source_end_{};
    std::size_t hour_index_=0;
    unsigned phase_=0;
};
} // namespace cteas::calmet::p6g
