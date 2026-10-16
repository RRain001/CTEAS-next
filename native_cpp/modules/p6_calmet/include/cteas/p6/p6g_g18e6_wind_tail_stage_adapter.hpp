#pragma once
// G18E6: route four already-implemented G17 original DIAGNO wind stages
// through one source-hour G14 frame: first WINDBC [7], INTER2 [9],
// post-INTER2 HTFAC=1 WINDBC [10], SMOOTH/DIVCEL/W [11].
// Source STHEOR [8] must execute between stages 7 and 9. This is a
// TEST-ONLY selected-stage integration, NOT full CALMET production parity.
#include "cteas/p6/p6g_g18e1_stheor_stage_adapter.hpp"
#include "cteas/p6/p6g_g18e5_slope_stage_adapter.hpp"
#include <chrono>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
class G18E6SelectedWindTailStageAdapter final : public MultiHourPhysics {
public:
    G18E6SelectedWindTailStageAdapter(
        G17SelectedTerrainFixturePhysics& terrain,
        const G18E5SelectedSlopeStageAdapter& slope)
        : terrain_(terrain), slope_(slope) {}

    p6::NativeHourStageResult run(
        p6::NativeHourStage, MultiHourFrame&) override {
        return {p6::NativeHourSource::Unknown,false};
    }

    void bind_stheor_stage(
        const G18E1SelectedStheorStageAdapter& stheor,
        const MultiHourFrame& frame, bool explicitly_test_only) {
        if(!explicitly_test_only || phase_!=1 || stheor_ ||
           !frame_ || &frame!=frame_)
            throw std::invalid_argument(
                "G18E6 station observations cannot be bound outside G14 STHEOR");
        verify_frame(frame);
        // This is the actual G18E1 stage [8] result, not the independent
        // direct-call G17C3 comparison vector or neutral WIND1 columns.
        (void)stheor.stations_for_comp(frame);
        stheor_=&stheor;
    }

    void run_selected(p6::NativeHourStage stage, MultiHourFrame& frame,
                      bool explicitly_test_only) {
        static_assert(p6::kHefeiOriginalStageOrder[7] ==
                      p6::NativeHourStage::DiagnoWindbcFirstGuess);
        static_assert(p6::kHefeiOriginalStageOrder[9] ==
                      p6::NativeHourStage::DiagnoInter2);
        static_assert(p6::kHefeiOriginalStageOrder[10] ==
                      p6::NativeHourStage::DiagnoWindbcPostInter2Htfac1);
        static_assert(p6::kHefeiOriginalStageOrder[11] ==
                      p6::NativeHourStage::DiagnoSmoothDivcelW);
        static constexpr p6::NativeHourStage stages[]={
            p6::NativeHourStage::DiagnoWindbcFirstGuess,
            p6::NativeHourStage::DiagnoInter2,
            p6::NativeHourStage::DiagnoWindbcPostInter2Htfac1,
            p6::NativeHourStage::DiagnoSmoothDivcelW
        };
        if(!explicitly_test_only || !frame.source_controls ||
           phase_>=4 || stage!=stages[phase_] ||
           frame.input.end!=frame.surface.end)
            throw std::invalid_argument(
                "G18E6 wrong original G14 wind stage or fixture provenance");
        if(phase_==0) {
            // SLOPE must have completed on the SAME live hour with
            // corrected HEATFX/ELUSTR forcing and untouched prior state.
            (void)slope_.selected_slope_wind_for(frame);
        } else {
            verify_frame(frame);
            if(phase_==1) {
                if(!stheor_ || !stheor_->selected_complete())
                    throw std::logic_error(
                        "G18E6 cannot enter INTER2 without original STHEOR");
                (void)stheor_->stations_for_comp(frame);
            }
        }
        const auto result=terrain_.run(stage,frame);
        if(!result.completed || result.source!=p6::NativeHourSource::NativeCpp)
            throw std::runtime_error(
                "G18E6 existing native G17 DIAGNO wind stage not completed");
        if(phase_==0) {
            frame_=&frame;
            hour_index_=frame.hour_index;
            source_end_=frame.input.end;
            previous_=frame.previous;
        } else if(phase_==1) {
            // The original boundary snapshots belong to the PRE-INTER2
            // first WINDBC, and must remain available after blending.
            const auto& wind=terrain_.wind_stages();
            original_ub_=wind.original_ub_west_east_mps;
            original_vb_=wind.original_vb_south_north_mps;
        } else if(phase_==3) {
            const auto& wind=terrain_.wind_stages();
            if(wind.original_ub_west_east_mps!=original_ub_ ||
               wind.original_vb_south_north_mps!=original_vb_)
                throw std::runtime_error(
                    "G18E6 final wind erased source first-WINDBC boundary");
            const auto& last=terrain_.selected_final_wind();
            if(frame.fields.u_mps!=last.u_mps ||
               frame.fields.v_mps!=last.v_mps ||
               frame.fields.w_face_mps!=last.w_face_mps)
                throw std::runtime_error(
                    "G18E6 final source U/V/W failed G14 physical handoff");
        }
        ++phase_;
    }

    [[nodiscard]] const p6::FinalWindSegment& selected_wind_for_comp(
        const MultiHourFrame& frame) const {
        if(phase_!=4)
            throw std::logic_error(
                "G18E6 incomplete source final U/V/W before COMP");
        verify_frame(frame);
        return terrain_.selected_final_wind();
    }

    [[nodiscard]] unsigned completed_wind_stages() const noexcept {
        return phase_;
    }

private:
    void verify_frame(const MultiHourFrame& frame) const {
        if(&frame!=frame_ || frame.hour_index!=hour_index_ ||
           frame.input.end!=source_end_ ||
           frame.previous.zi_m!=previous_.zi_m ||
           frame.previous.ziconv_m!=previous_.ziconv_m ||
           frame.previous.dptt_k!=previous_.dptt_k)
            throw std::logic_error(
                "G18E6 DIAGNO wind source crossed G14 live frame or prior-hour state");
    }
    G17SelectedTerrainFixturePhysics& terrain_;
    const G18E5SelectedSlopeStageAdapter& slope_;
    const G18E1SelectedStheorStageAdapter* stheor_=nullptr;
    const MultiHourFrame* frame_=nullptr;
    p6::NativeGridMemory previous_;
    std::chrono::sys_seconds source_end_{};
    std::size_t hour_index_=0;
    unsigned phase_=0;
    std::vector<float> original_ub_,original_vb_;
};
} // namespace cteas::calmet::p6g
