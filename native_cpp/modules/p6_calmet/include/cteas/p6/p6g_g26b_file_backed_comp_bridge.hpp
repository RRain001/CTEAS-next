#pragma once
// G26B: original-source 2SS+2US selected G14 COMP stage slots [12..15].
// Directly reuse existing G18D4/MIXHT/AVEMIX/WSTARR/TEMP3D native kernels
// with the EXACT G26A live frame, source PREPDI AA/BB, source G22 heat,
// G23 per-station DPTT and G24 physically computed final 3D U/V/W.
// The original SETCOM NEARU grid mapping remains SELECTED TEST-ONLY:
// independent full-original multicenter 45-field source hour unaccepted.
// No P6F [16], no G14 committed memory / station-clock publication.
#include "cteas/p6/p6g_g26_file_backed_g14_diagno_bridge.hpp"
#include "cteas/p6/p6g_g18d4_comp_stage_adapter.hpp"
#include "cteas/p6/p6g_g18d5_source_mixht_controls.hpp"
#include "cteas/p6/p6g_g18b3_upper_choice.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {

inline G18ASelectedCompControls g26b_source_test_comp_controls(
    const MultiHourFrame& frame,const G19FileBackedCase& source,
    bool explicitly_test_only) {
    const auto nx=static_cast<std::size_t>(frame.grid.nx);
    const auto ny=static_cast<std::size_t>(frame.grid.ny);
    const auto n=nx*ny;
    if(!explicitly_test_only||!frame.source_controls||
       source.grid.nx!=frame.grid.nx||
       source.grid.ny!=frame.grid.ny||
       source.grid.landuse!=frame.grid.landuse||
       source.stations.upper.size()!=frame.stations.upper.size()||
       source.stations.surface.size()!=frame.stations.surface.size()||
       source.original_metinp.empty()||
       source.controls.iprog!=0)
        throw std::invalid_argument("G26B source COMP must follow native G26A GEO");
    G18ASelectedCompControls input;
    input.explicitly_test_only=true;
    // S4-B4 strictly gated source-science experiment. No fabricated station,
    // no new numerical formula. C2 cardinality and result remain untouched.
    input.allow_one_one_source_audit=(frame.stations.surface.size()==1 &&
                                     frame.stations.upper.size()==1);
    auto& grid=input.grid_mixht;
    grid.nx=nx;
    grid.ny=ny;
    grid.landuse=frame.grid.landuse;
    grid.water_first=frame.grid.iwat1;
    grid.water_last=frame.grid.iwat2;
    for(int lu:grid.landuse)
        if(lu>=grid.water_first&&lu<=grid.water_last)
            throw std::invalid_argument("G26B source overwater COMP not validated");
    const auto choice=g18b3_source_deck_upper_choice(
        frame.grid,frame.stations,source.original_metinp);
    g18b3_bind_test_only_upper_choice(
        grid,frame.grid,frame.stations,choice,true);
    g18d5_bind_original_mixht_scalars(source.original_metinp,input);
    // Original land SETCOM: FCORI=max(abs(FCORIOL),0.25E-4),
    // CMECH=CONSTB/sqrt(FCORI). Spatially varying FCORIOL>998 refused
    // by the source-selected and original-vendor-checked G23 controls.
    const auto original_station=g23_stheor_original_readcf_controls(
        source,true);
    grid.fcori.assign(n,original_station.fcori_s);
    grid.cmech.assign(n,original_station.cmech);
    input.initial_wstar_mps.assign(n,0.f);
    if(grid.iupt!=-1||grid.nearu.size()!=n||
       grid.fcori.size()!=n||grid.cmech.size()!=n)
        throw std::invalid_argument("G26B source upper choice/FCORI malformed");
    return input;
}

class G26BSourceFileBackedCompBridge final : public MultiHourPhysics {
public:
    G26BSourceFileBackedCompBridge(
        const G26SourceFileBackedG14DiagnoBridge& diagno,
        const G19FileBackedCase& source)
        :diagno_(diagno),source_(source) {}

    [[nodiscard]] p6::NativeHourStageResult run(
        p6::NativeHourStage,MultiHourFrame&) override {
        return {p6::NativeHourSource::Unknown,false};
    }

    void run_selected(p6::NativeHourStage stage,MultiHourFrame& frame,
                      bool explicitly_test_only) {
        if(!explicitly_test_only||phase_>=4||
           stage!=p6::kHefeiOriginalStageOrder[12+phase_]||
           !frame.source_controls||
           frame.input.end!=frame.surface.end||
           !diagno_.source_diagno_ready())
            throw std::invalid_argument("G26B unsupported original G14 COMP stage");
        const auto& final_wind=diagno_.selected_wind_for_comp(frame).wind;
        if(frame.fields.u_mps!=final_wind.u_mps||
           frame.fields.v_mps!=final_wind.v_mps||
           frame.fields.w_face_mps!=final_wind.w_face_mps)
            throw std::invalid_argument("G26B source COMP missing original G24 U/V/W");
        if(phase_==0) {
            const auto& station=diagno_.selected_station_for_comp(frame);
            const auto& thermal=diagno_.selected_thermal_for_comp(frame);
            const auto& upper=diagno_.selected_upper_for_comp(frame);
            if(frame.next.zi_m!=frame.previous.zi_m||
               frame.next.ziconv_m!=frame.previous.ziconv_m||
               frame.next.dptt_k!=frame.previous.dptt_k)
                throw std::invalid_argument(
                    "G26B source COMP cannot start after candidate history was mutated");
            // G33C original COMP begins with its own SURFVAR(IALL=1)
            // AFTER G24 has produced the FINAL physical U/V. The G22
            // HEATFX/AIRDEN/ELUSTR was only DIAGNO's slope-flow
            // estimate, not the later COMP thermal state. Independent
            // original G33A/G33B proves first/second/third TEMP2D
            // exactly and exposes 143 stale native COMP temperature
            // cells when G22's second pass is reused.
            //
            // Rebuild source PREPDI's same-hour surface kernel stages
            // from the authoritative G26A G20 WIND1 and G21 FRADJ,
            // then run COMP's IALL=1 third pass on authentic G24 U/V.
            // No original reference numerical fields enter C++.
            const auto& wind1=diagno_.selected_wind1_for_comp(frame);
            const auto& fradj=diagno_.selected_fradj_for_comp(frame);
            G17B4TwoPassSurfvar surface(
                frame.grid,frame.stations,source_.surface,frame.surface,
                source_.surface_controls);
            surface.after_wind1_before_fradj(
                frame.input.end,wind1.u_mps,wind1.v_mps);
            surface.after_fradj_before_heatfx(
                frame.input.end,fradj.corrected_wind.u,
                fradj.corrected_wind.v);
            if(surface.first_temperature()!=fradj.temperature_before_k||
               surface.final_temperature()!=fradj.temperature_after_k||
               surface.final_temperature()!=thermal.heat.temperature_k)
                throw std::logic_error(
                    "G33C COMP reconstruction detached from frozen DIAGNO source");
            surface.after_final_diagno_before_comp(
                frame.input.end,final_wind.u_mps,final_wind.v_mps,true);
            const auto comp_heat=selected_iavet1_heat_after_fradj(
                frame.grid,frame.stations,frame.surface,surface,
                g18d3_source_hflux_inputs(
                    frame.grid,source_.original_metinp,true),true);
            if(g18c1_source_integer(source_.original_metinp,"ICOARE")<=0)
                throw std::invalid_argument(
                    "G33C original COMP unsupported ISFCMET/IPSIFCN");
            G17C2SelectedElustrControls comp_controls;
            comp_controls.ipsifcn=0;
            comp_controls.zm_m=0.5f*(
                frame.source_controls->zface_m[0]+
                frame.source_controls->zface_m[1]);
            comp_controls.explicitly_test_only=true;
            const auto comp_elustr=selected_iavet1_elustr_after_heatfx(
                frame.grid,frame.stations,frame.surface,
                surface,comp_heat,
                {final_wind.u_mps,final_wind.v_mps},
                comp_controls,true);
            // Real source parsers and immutable accepted P6E numerical
            // kernels only: MIXHT/AVEMIX/WSTARR/TEMP3D remain test-only.
            comp_.emplace(
                comp_heat,comp_elustr,station.station_diagi,upper,
                g26b_source_test_comp_controls(frame,source_,true),
                g18c1_parse_original_avemix(source_.original_metinp),
                [&] {
                    auto selected=g18c3_parse_original_temp3d_controls(
                        source_.original_metinp);
                    selected.allow_one_one_source_audit=
                        frame.stations.surface.size()==1&&
                        frame.stations.upper.size()==1;
                    return selected;
                }());
            live_=&frame;
            hour_index_=frame.hour_index;
            end_=frame.input.end;
            previous_=frame.previous;
        } else if(!comp_||&frame!=live_||
                  frame.hour_index!=hour_index_||
                  frame.input.end!=end_||
                  frame.previous.zi_m!=previous_.zi_m||
                  frame.previous.ziconv_m!=previous_.ziconv_m||
                  frame.previous.dptt_k!=previous_.dptt_k) {
            throw std::logic_error("G26B detached G14 COMP from original G26A frame");
        }
        comp_->run_selected(stage,frame,true);
        ++phase_;
    }

    [[nodiscard]] const G18ASelectedCompResult& source_mixht_before_avemix(
        const MultiHourFrame& frame) const {
        if(phase_<1||!comp_||&frame!=live_||
           frame.hour_index!=hour_index_||frame.input.end!=end_||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k)
            throw std::logic_error("G28 requested source MIXHT from foreign/unfinished G14");
        return comp_->source_mixht_before_avemix(frame);
    }
    [[nodiscard]] const G18C1AvemixOutput& source_avemix_after_mixht(
        const MultiHourFrame& frame) const {
        (void)source_mixht_before_avemix(frame);
        if(phase_<2)
            throw std::logic_error("G28 requires original source AVEMIX after MIXHT");
        return comp_->source_avemix_after_mixht(frame);
    }
    [[nodiscard]] const G18C3SelectedTemperature& source_temp3d_input_and_result(
        const MultiHourFrame& frame) const {
        if(phase_!=4||!comp_||&frame!=live_||
           frame.hour_index!=hour_index_||frame.input.end!=end_||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k)
            throw std::logic_error("G29B foreign or unfinished native TEMP3D");
        return comp_->source_temp3d_before_assembly(frame);
    }
    [[nodiscard]] const G17CSelectedHeatResult& source_comp_heat_for_p6f(
        const MultiHourFrame& frame) const {
        if(phase_!=4||!comp_||&frame!=live_||
           frame.hour_index!=hour_index_||frame.input.end!=end_||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k)
            throw std::logic_error(
                "G33D cannot publish DIAGNO or cross-hour density as P6F COMP");
        return comp_->source_comp_heat_for_p6f(frame);
    }
    [[nodiscard]] bool source_comp_ready() const noexcept {
        return phase_==4&&comp_.has_value()&&comp_->selected_complete();
    }
    [[nodiscard]] const G18C4SelectedCandidate& selected_p6f_candidate(
        const MultiHourFrame& frame) const {
        if(!source_comp_ready()||&frame!=live_||
           frame.hour_index!=hour_index_||frame.input.end!=end_||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k)
            throw std::logic_error("G26B premature/foreign source COMP for P6F");
        const auto& candidate=comp_->selected_candidate();
        if(frame.next.zi_m!=candidate.candidate_memory.zi_m||
           frame.next.ziconv_m!=candidate.candidate_memory.ziconv_m||
           frame.next.dptt_k!=candidate.candidate_memory.dptt_k||
           frame.fields.u_mps!=candidate.candidate_fields.u_mps||
           frame.fields.v_mps!=candidate.candidate_fields.v_mps||
           frame.fields.w_face_mps!=candidate.candidate_fields.w_face_mps||
           frame.fields.temperature_k!=candidate.candidate_fields.temperature_k||
           frame.fields.qh_wm2!=candidate.candidate_fields.qh_wm2||
           frame.fields.ustar_mps!=candidate.candidate_fields.ustar_mps||
           frame.fields.el_m!=candidate.candidate_fields.el_m||
           frame.fields.wstar_mps!=candidate.candidate_fields.wstar_mps)
            throw std::logic_error("G26B candidate COMP state or P6F fields mutated");
        return candidate;
    }
private:
    const G26SourceFileBackedG14DiagnoBridge& diagno_;
    const G19FileBackedCase& source_;
    std::optional<G18D4SelectedCompStageAdapter> comp_;
    const MultiHourFrame* live_=nullptr;
    p6::NativeGridMemory previous_;
    std::chrono::sys_seconds end_{};
    std::size_t hour_index_=0;
    unsigned phase_=0;
};
} // namespace cteas::calmet::p6g
