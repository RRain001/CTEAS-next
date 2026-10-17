#pragma once
// G18D4: selected source-ordered COMP *stage execution* on one G14 frame:
// GRID MIXHT -> AVEMIX -> WSTARR -> TEMP3D; no precomputed end-of-hour
// candidate may impersonate independently completed original CALMET stages.
// Every calculation delegates to already tested G18A/G18C kernels.
// Production MultiHourPhysics::run deliberately remains Unknown/false:
// selected fixture inputs (notably G18A MIXHT coefficients) are NOT
// source-proven 17-stage native CALMET acceptance.
#include "cteas/p6/p6g_g18c4_selected_hour_candidate.hpp"
#include <optional>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
class G18D4SelectedCompStageAdapter final : public MultiHourPhysics {
public:
    G18D4SelectedCompStageAdapter(
        G17CSelectedHeatResult heat,
        G17C2SelectedElustrResult elustr,
        std::vector<G17C3StationDiagi> diagi,
        G18BUpperHour observed_upper,
        G18ASelectedCompControls mixht,
        G18C1AvemixControls avemix,
        G18C3Temp3dControls temp3d)
        : heat_(std::move(heat)),
          elustr_(std::move(elustr)),
          diagi_(std::move(diagi)),
          upper_(std::move(observed_upper)),
          mixht_(std::move(mixht)), avemix_(avemix), temp3d_(temp3d) {}

    // Never mark fixture-sourced partial stages as production NativeCpp.
    p6::NativeHourStageResult run(
        p6::NativeHourStage,MultiHourFrame&) override {
        return {p6::NativeHourSource::Unknown,false};
    }

    // G18D4 selected fixture gate. The stage supplied here must match
    // the NEXT COMP entry in immutable PR #53 kHefeiOriginalStageOrder.
    // It is not a second hourly scheduler; G14 alone selects input hour.
    void run_selected(p6::NativeHourStage stage,MultiHourFrame& frame,
                      bool explicitly_test_only) {
        static constexpr p6::NativeHourStage sequence[]={
            p6::NativeHourStage::CompGridMixht,
            p6::NativeHourStage::CompAvemix,
            p6::NativeHourStage::CompWstarr,
            p6::NativeHourStage::CompTemp3d};
        if(!explicitly_test_only||stage_index_>=4||
           stage!=sequence[stage_index_]||
           (bound_&&(frame.hour_index!=hour_index_||
                     frame.input.end!=source_end_||
                     &frame!=bound_frame_||
                     frame.previous.zi_m!=previous_snapshot_.zi_m||
                     frame.previous.ziconv_m!=previous_snapshot_.ziconv_m||
                     frame.previous.dptt_k!=previous_snapshot_.dptt_k||
                     frame.fields.u_mps!=wind_u_snapshot_||
                     frame.fields.v_mps!=wind_v_snapshot_||
                     frame.fields.w_face_mps!=wind_w_snapshot_||
                     frame.next.zi_m!=pending_next_.zi_m||
                     frame.next.ziconv_m!=pending_next_.ziconv_m||
                     frame.next.dptt_k!=pending_next_.dptt_k))||
           !frame.source_controls||
           frame.input.end!=frame.surface.end||
           upper_.end!=frame.input.end||
           heat_.end!=frame.input.end||
           elustr_.end!=frame.input.end)
            throw std::invalid_argument("G18D4 original COMP stage or source hour mismatch");
        if(stage_index_==0) {
            const auto pre=selected_comp_mixht_with_observed_upper(
                frame,heat_,elustr_,diagi_,upper_,mixht_);
            mixed_.emplace(pre);
            // Freeze the exact live G14 frame and all upstream
            // DIAGNO/previous-COMP fields between the four original COMP
            // stages. A cloned frame with the same UTC stamp is NOT valid.
            bound_=true;
            hour_index_=frame.hour_index;
            source_end_=frame.input.end;
            bound_frame_=&frame;
            previous_snapshot_=frame.previous;
            pending_next_=frame.next;
            wind_u_snapshot_=frame.fields.u_mps;
            wind_v_snapshot_=frame.fields.v_mps;
            wind_w_snapshot_=frame.fields.w_face_mps;
        }else if(stage_index_==1) {
            averaged_.emplace(g18c1_selected_after_mixht(
                frame,*mixed_,avemix_,true));
        }else if(stage_index_==2) {
            conv_.emplace(g18c2_wstarr_after_avemix(
                frame,*mixed_,*averaged_,heat_,elustr_,true));
        }else{
            // TEMP3D must consume actual physical AA/BB FACET profiles
            // for this same source hour and POST-AVEMIX ZICONV.
            const auto faces=g18b5_selected_native_temperature_faces(
                frame,upper_);
            temperature_.emplace(g18c3_selected_native_temp3d(
                frame,upper_,faces,heat_,*conv_,temp3d_,true));
            result_.emplace(g18c4_assemble_selected_hour(
                frame,heat_,elustr_,*conv_,*temperature_,true));
            // A G14 candidate, NOT a committed earlier-hour history.
            frame.next=result_->candidate_memory;
            frame.fields=result_->candidate_fields;
        }
        ++stage_index_;
    }
    // G28 literal vendor AVEMIX audit: expose only the genuine source
    // MIXHT BEFORE averaging and source AVEMIX result AFTER execution.
    // Neither snapshot is an accepted/committed multi-hour G14 state.
    [[nodiscard]] const G18ASelectedCompResult& source_mixht_before_avemix(
        const MultiHourFrame& frame) const {
        if(stage_index_<1||!mixed_||!bound_||&frame!=bound_frame_||
           frame.hour_index!=hour_index_||frame.input.end!=source_end_||
           frame.previous.zi_m!=previous_snapshot_.zi_m||
           frame.previous.ziconv_m!=previous_snapshot_.ziconv_m||
           frame.previous.dptt_k!=previous_snapshot_.dptt_k)
            throw std::logic_error("G28 original MIXHT input not from live G14 COMP");
        return *mixed_;
    }
    [[nodiscard]] const G18C1AvemixOutput& source_avemix_after_mixht(
        const MultiHourFrame& frame) const {
        (void)source_mixht_before_avemix(frame);
        if(stage_index_<2||!averaged_)
            throw std::logic_error("G28 source AVEMIX not executed");
        return *averaged_;
    }
    [[nodiscard]] const G18C3SelectedTemperature& source_temp3d_before_assembly(
        const MultiHourFrame& frame) const {
        (void)source_mixht_before_avemix(frame);
        if(stage_index_!=4||!temperature_||!result_)
            throw std::logic_error("G29B requested unexecuted source TEMP3D");
        return *temperature_;
    }
    // G33D: only the actual completed COMP [12..15] owns the output
    // HEATFX/TEMP2D/RHO/QSW fields. G22's earlier DIAGNO heat is for
    // slope-flow computation and must never be recycled into final P6F.
    [[nodiscard]] const G17CSelectedHeatResult& source_comp_heat_for_p6f(
        const MultiHourFrame& frame) const {
        (void)source_mixht_before_avemix(frame);
        if(!selected_complete()||!result_||
           heat_.end!=frame.input.end||
           heat_.temperature_k.size()!=
              static_cast<std::size_t>(frame.grid.nx)*
              static_cast<std::size_t>(frame.grid.ny))
            throw std::logic_error(
                "G33D P6F surface heat requested before completed COMP source");
        return heat_;
    }
    [[nodiscard]] bool selected_complete() const noexcept {
        return stage_index_==4&&result_.has_value();
    }
    [[nodiscard]] const G18C4SelectedCandidate& selected_candidate() const {
        if(!selected_complete())
            throw std::logic_error("G18D4 COMP source stages incomplete");
        return *result_;
    }
private:
    G17CSelectedHeatResult heat_;
    G17C2SelectedElustrResult elustr_;
    std::vector<G17C3StationDiagi> diagi_;
    G18BUpperHour upper_;
    G18ASelectedCompControls mixht_;
    G18C1AvemixControls avemix_;
    G18C3Temp3dControls temp3d_;
    std::optional<G18ASelectedCompResult> mixed_;
    std::optional<G18C1AvemixOutput> averaged_;
    std::optional<G18C2SourceCompAfterAverage> conv_;
    std::optional<G18C3SelectedTemperature> temperature_;
    std::optional<G18C4SelectedCandidate> result_;
    std::size_t stage_index_=0,hour_index_=0;
    std::chrono::sys_seconds source_end_{};
    const MultiHourFrame* bound_frame_=nullptr;
    p6::NativeGridMemory previous_snapshot_,pending_next_;
    std::vector<float> wind_u_snapshot_,wind_v_snapshot_,wind_w_snapshot_;
    bool bound_=false;
};
} // namespace cteas::calmet::p6g
