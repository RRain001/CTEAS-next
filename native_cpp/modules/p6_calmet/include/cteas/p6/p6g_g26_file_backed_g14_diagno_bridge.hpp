#pragma once
// G26A: SAME live G14 hour: G18E4 PREPDI, G20 WIND1, G21 CGAMMA+
// FRADJ, G22 HEATFX/AIRDEN/ELUSTR/SLOPE, G23 WINDBC/STHEOR/INTER2,
// G24 post-INTER2 WINDBC/SMOOTH/DIVCEL/W, in original source order.
//
// This is a 12-stage SELECTED, TEST-ONLY *compound-stage* integration.
// G22 executes source stages [3..6] as one internally source-ordered
// pure kernel; G23 executes [7..9], G24 executes [10..11]. Only the
// LAST stage of each block makes the output of that block available.
// No source G14 COMP [12..15], P6F [16], memory or clock commit.
// Native production run() deliberately reports Unknown,false.
#include "cteas/p6/p6g_g18e4_prepdi_stage_adapter.hpp"
#include "cteas/p6/p6g_g20_file_backed_wind1_profiles.hpp"
#include "cteas/p6/p6g_g24_file_backed_wind_tail.hpp"
#include <array>
#include <chrono>
#include <cstddef>
#include <memory>
#include <optional>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
class G26SourceFileBackedG14DiagnoBridge final : public MultiHourPhysics {
public:
    G26SourceFileBackedG14DiagnoBridge(
        const UnifiedMultistationHourlyScheduler& owner,
        G18D2StationClockAuthority& clocks,
        const G19FileBackedCase& source)
        :owner_(owner),clocks_(clocks),source_(source),
         prepdi_(owner,clocks,source.original_metinp) {}

    [[nodiscard]] p6::NativeHourStageResult run(
        p6::NativeHourStage, MultiHourFrame&) override {
        // Never allow caller to mistake *selected* composite kernels
        // for production-accepted original G14+COMP+P6F.
        return {p6::NativeHourSource::Unknown,false};
    }

    void run_selected(p6::NativeHourStage stage,MultiHourFrame& frame,
                      bool explicitly_test_only) {
        if(!explicitly_test_only||phase_>=12||
           stage!=p6::kHefeiOriginalStageOrder[phase_]||
           !frame.source_controls||!owner_.has_original_controls()||
           owner_.completed_hours()!=frame.hour_index||
           source_.grid.nx!=frame.grid.nx||
           source_.grid.ny!=frame.grid.ny||
           source_.grid.landuse!=frame.grid.landuse||
           source_.grid.terrain_m!=frame.grid.terrain_m)
            throw std::invalid_argument(
                "G26 G14 selected source stage wrong order/provenance or COMP boundary");
        if(phase_==0) {
            // This source-preflight binds the actual committed memory
            // address, raw SURF/UP/GEO provenance and detached AA/BB +
            // CGAMMA clock candidates, without publication.
            prepdi_.run_selected(stage,frame,true);
            live_=&frame;
            previous_=frame.previous;
            hour_index_=frame.hour_index;
            source_end_=frame.input.end;
        } else {
            verify_frame(frame);
            if(frame.next.zi_m!=previous_.zi_m||
               frame.next.ziconv_m!=previous_.ziconv_m||
               frame.next.dptt_k!=previous_.dptt_k)
                throw std::logic_error("G26 DIAGNO prematurely modified COMP next memory");
        }
        switch(phase_) {
        case 0:
            if(prepdi_.selected_gamma_for(frame).end!=frame.input.end)
                throw std::logic_error("G26 original source CGAMMA hour absent");
            break;
        case 1: {
            profiles_.emplace(g20_file_backed_source_wind1_profiles(frame,true));
            wind_.emplace(*profiles_);
            const auto result=wind_->run(stage,frame);
            if(!result.completed||
               result.source!=p6::NativeHourSource::NativeCpp||
               !wind_->selected_result().wind1_complete)
                throw std::runtime_error("G26 native G20 source WIND1 failed");
            break;
        }
        case 2:
            if(!wind_)
                throw std::logic_error("G26 source WIND1 prerequisite missing");
            g21_.emplace(g21_selected_original_file_fradj(
                frame,source_,prepdi_.selected_gamma_for(frame),
                wind_->selected_result().first_guess,true));
            break;
        case 3:
            // G22 is physically ordered inside this one source-bound
            // kernel; 3..6 are NOT independently committed callbacks.
            g22_.emplace(g22_selected_source_thermal_slope(
                frame,source_,
                {wind_->selected_result().first_guess.u_mps,
                 wind_->selected_result().first_guess.v_mps},
                *g21_,true));
            break;
        case 4:
            if(!g22_||g22_->heat.density_kg_m3.empty())
                throw std::logic_error("G26 bundled AIRDEN incomplete");
            break;
        case 5:
            if(!g22_||g22_->elustr.qh_wm2.empty())
                throw std::logic_error("G26 bundled ELUSTR incomplete");
            break;
        case 6:
            if(!g22_||g22_->post_slope_wind.u.empty())
                throw std::logic_error("G26 bundled SLOPE incomplete");
            break;
        case 7:
        case 8:
            // G23's verified compound order FIRST WINDBC -> STHEOR ->
            // INTER2 is executed at the final [9] checkpoint.
            // No partially completed G23 result is made accessible.
            if(!g22_||!profiles_)
                throw std::logic_error("G26 STHEOR/BC source prerequisite missing");
            break;
        case 9:
            g23_.emplace(g23_source_stheor_diagi_inter2(
                frame,source_,*profiles_,*g21_,*g22_,true));
            break;
        case 10:
            if(!g23_||g23_->inter2_u.component_mps.empty()||
               g23_->inter2_v.component_mps.empty())
                throw std::logic_error("G26 source INTER2/second WINDBC missing");
            break;
        case 11: {
            g24_.emplace(g24_selected_original_wind_tail(
                frame,source_,*g23_,true));
            // First DIAGNO -> COMP handoff: authentic source-computed
            // 3-D wind plus current HEATFX/ELUSTR only. TEMP3D, WSTAR
            // and current grid MIXHT/AVEMIX remain ABSENT; no G14 commit.
            frame.fields.u_mps=g24_->wind.u_mps;
            frame.fields.v_mps=g24_->wind.v_mps;
            frame.fields.w_face_mps=g24_->wind.w_face_mps;
            frame.fields.qh_wm2=g22_->elustr.qh_wm2;
            frame.fields.ustar_mps=g22_->elustr.ustar_mps;
            frame.fields.el_m=g22_->elustr.el_m;
            if(!frame.fields.temperature_k.empty()||
               !frame.fields.wstar_mps.empty())
                throw std::logic_error("G26 source DIAGNO used forged downstream COMP fields");
            break;
        }
        default:
            throw std::logic_error("G26 source stage beyond known DIAGNO");
        }
        verify_frame(frame);
        if(frame.next.zi_m!=previous_.zi_m||
           frame.next.ziconv_m!=previous_.ziconv_m||
           frame.next.dptt_k!=previous_.dptt_k)
            throw std::logic_error("G26 selected source DIAGNO changed prior COMP state");
        ++phase_;
    }

    [[nodiscard]] unsigned selected_checkpoints() const noexcept {return phase_;}
    [[nodiscard]] bool source_diagno_ready() const noexcept {
        return phase_==12&&g24_.has_value()&&g23_.has_value()&&
               g22_.has_value()&&g21_.has_value();
    }
    [[nodiscard]] const G23SelectedSourceStheorInter2& selected_station_for_comp(
        const MultiHourFrame& frame) const {
        if(!source_diagno_ready())throw std::logic_error(
            "G26 station STHEOR not available before completed DIAGNO");
        verify_frame(frame);
        return *g23_;
    }
    [[nodiscard]] const G24SourceWindTail& selected_wind_for_comp(
        const MultiHourFrame& frame) const {
        if(!source_diagno_ready())throw std::logic_error(
            "G26 final wind unavailable before completed DIAGNO");
        verify_frame(frame);
        return *g24_;
    }
    // G33C: expose the exact same-hour native source WIND1 and FRADJ
    // already executed by G26A, solely to reconstruct the original
    // THIRD COMP SURFVAR. No oracle fields, new stage shortcuts,
    // duplicate source clocks or production admission are introduced.
    [[nodiscard]] const Wind1MultiField& selected_wind1_for_comp(
        const MultiHourFrame& frame) const {
        if(!source_diagno_ready()||!wind_)
            throw std::logic_error("G33C WIND1 required before original COMP");
        verify_frame(frame);
        return wind_->selected_result().first_guess;
    }
    [[nodiscard]] const G21SelectedFradjFields& selected_fradj_for_comp(
        const MultiHourFrame& frame) const {
        if(!source_diagno_ready()||!g21_)
            throw std::logic_error("G33C post-FRADJ wind missing before COMP");
        verify_frame(frame);
        return *g21_;
    }
    [[nodiscard]] const G22SelectedThermalSlope& selected_thermal_for_comp(
        const MultiHourFrame& frame) const {
        if(!source_diagno_ready())throw std::logic_error(
            "G26 source G22 heat/ELUSTR absent before completed DIAGNO");
        verify_frame(frame);
        return *g22_;
    }
    [[nodiscard]] const G18BUpperHour& selected_upper_for_comp(
        const MultiHourFrame& frame) const {
        if(!source_diagno_ready())throw std::logic_error(
            "G26 original PREPDI AA/BB upper not ready for COMP");
        verify_frame(frame);
        return prepdi_.selected_upper_for(frame);
    }
    void require_station_clock_preflight(const MultiHourFrame& frame) const {
        if(!source_diagno_ready())throw std::logic_error(
            "G26 source G14 cannot preflight before final wind");
        verify_frame(frame);
        prepdi_.require_publishable_before_g14_commit(frame);
    }
    // G34B: publish the G18D2 prepared AA/BB/CGAMMA clock candidates
    // exclusively after G14 accepts the 17th P6F stage and memory commit.
    // Selected/test-only: does NOT admit the G26 production run() interface.
    [[nodiscard]] bool try_publish_after_selected_g14_commit_noexcept() noexcept {
        if(!source_diagno_ready()||owner_.completed_hours()!=hour_index_+1)
            return false;
        return prepdi_.try_publish_after_completed_g14_hour_noexcept();
    }
    [[nodiscard]] bool clocks_published() const noexcept {
        return clocks_.has_published_hour();
    }
private:
    void verify_frame(const MultiHourFrame& frame) const {
        if(!live_||live_!=&frame||frame.hour_index!=hour_index_||
           frame.input.end!=source_end_||
           &frame.previous!=&owner_.committed_memory()||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k||
           // Previous accepted hour MUST have published both station clocks.
           // The old first-hour-only guard erroneously rejected every
           // subsequent G14 frame as soon as hour zero was committed.
           (hour_index_==0 ? clocks_.has_published_hour() :
            (!clocks_.has_published_hour()||
             clocks_.latest_upper_hour()!=frame.surface.start||
             clocks_.latest_gamma_hour()!=frame.surface.start)))
            throw std::logic_error(
                "G26 source frame detached, prior-hour COMP mutated or station clocks stale");
    }
    const UnifiedMultistationHourlyScheduler& owner_;
    G18D2StationClockAuthority& clocks_;
    const G19FileBackedCase& source_;
    G18E4SelectedPrepdiStageAdapter prepdi_;
    const MultiHourFrame* live_=nullptr;
    p6::NativeGridMemory previous_;
    std::chrono::sys_seconds source_end_{};
    std::size_t hour_index_=0;
    unsigned phase_=0;
    std::optional<G16ObservedProfiles> profiles_;
    std::optional<G16SelectedWindPhysics> wind_;
    std::optional<G21SelectedFradjFields> g21_;
    std::optional<G22SelectedThermalSlope> g22_;
    std::optional<G23SelectedSourceStheorInter2> g23_;
    std::optional<G24SourceWindTail> g24_;
};
} // namespace cteas::calmet::p6g
