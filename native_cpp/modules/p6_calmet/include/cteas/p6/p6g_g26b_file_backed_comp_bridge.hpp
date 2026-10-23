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
#include "cteas/p6/p6g_g63_real_noaa_g14_comp_mixht.hpp"
#include "cteas/p6e/wstarr.hpp"
#include "cteas/p6e/temp3d_observed_land.hpp"
#include "cteas/p6/p6g_g18b5_upper_temp_faces.hpp"
#include "cteas/p6/p6g_g64_real_noaa_p6f_precommit.hpp"
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
    input.allow_asymmetric_source_audit=
        (frame.stations.surface.size()==1&&frame.stations.upper.size()>=2&&
         frame.stations.upper.size()>=2)||
        (frame.stations.surface.size()>=2&&frame.stations.surface.size()>=2&&
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
        const G19FileBackedCase& source,
        bool explicitly_opt_in_normal_trial=false,
        const G41SelectedNoowWaterFirstHourSource* original_noow_water=nullptr)
        :diagno_(diagno),source_(source),
         original_noow_water_(original_noow_water),
         normal_trial_(explicitly_opt_in_normal_trial) {}

    [[nodiscard]] p6::NativeHourStageResult run(
        p6::NativeHourStage stage,MultiHourFrame& frame) override {
        // S4-F scoped normal-call trial, not an accepted production path.
        // Reuse exactly the same G26B COMP arithmetic and source checks.
        if(!normal_trial_)return {p6::NativeHourSource::Unknown,false};
        run_selected(stage,frame,true);
        return {p6::NativeHourSource::NativeCpp,true};
    }

    void run_selected(p6::NativeHourStage stage,MultiHourFrame& frame,
                      bool explicitly_test_only) {
        if(!explicitly_test_only||
           phase_>=(source_.research_noow_water_source_only?5U:4U)||
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
        if(source_.research_noow_water_source_only) {
            // Original G14 stages 12 MIXHT then 13 AVEMIX, from ONE
            // live frame and the same firsthour original WATER identity.
            // AVEMIX is forbidden without the actual preceding MIXHT.
            // Stages 14..16, clock publication and native G14 commit
            // remain explicitly unaccepted.
            if(!original_noow_water_||frame.hour_index>1||
               // Hour2 is a stage12-only scientific candidate. Never
               // admit AVEMIX, WSTARR, TEMP3D or P6F without distinct
               // second-hour original CALMET physical verification.
               (frame.hour_index==1&&phase_!=0)||
               original_noow_water_->source.original_metinp!=
                   source_.original_metinp)
                throw std::invalid_argument(
                    "G26B genuine water source identity outside selected scope");
            if(phase_==1) {
                const auto& mixed=source_water_mixht_stage12(frame);
                const auto controls=g18c1_parse_original_avemix(
                    source_.original_metinp);
                const auto n=static_cast<std::size_t>(frame.grid.nx)*
                             static_cast<std::size_t>(frame.grid.ny);
                const auto start=static_cast<std::size_t>(controls.ilevzi-1)*n;
                if(start+n>frame.fields.u_mps.size()||
                   start+n>frame.fields.v_mps.size())
                    throw std::invalid_argument(
                        "G26B NOAA original AVEMIX source ILEVZI outside G24");
                const std::vector<float> level_u(
                    frame.fields.u_mps.begin()+start,
                    frame.fields.u_mps.begin()+start+n);
                const std::vector<float> level_v(
                    frame.fields.v_mps.begin()+start,
                    frame.fields.v_mps.begin()+start+n);
                auto averaged=g18c1_original_avemix_rebuild(
                    frame.grid.nx,frame.grid.ny,
                    controls.mnmdav,controls.hafang_deg,
                    frame.grid.grid_km*1000.f,level_u,level_v,
                    mixed.zi_before_avemix_m,
                    mixed.ziconv_before_avemix_m);
                if(averaged.zi_m.size()!=n||
                   averaged.ziconv_m.size()!=n||
                   frame.next.zi_m!=frame.previous.zi_m||
                   frame.next.ziconv_m!=frame.previous.ziconv_m||
                   frame.next.dptt_k!=frame.previous.dptt_k)
                    throw std::logic_error(
                        "G26B G14 stage13 AVEMIX mutated precommit memory");
                water_avemix_stage13_.emplace(std::move(averaged));
                ++phase_;
                return;
            }
            if(phase_==2) {
                // The *same* live G14 G26B stage12/13 physical candidates
                // feed unchanged P6E WSTARR. Standalone G55 is NOT input.
                const auto& averaged=source_water_avemix_stage13(frame);
                if(!water_mixht_stage12_||frame.next.zi_m!=previous_.zi_m||
                   frame.next.ziconv_m!=previous_.ziconv_m||
                   frame.next.dptt_k!=previous_.dptt_k)
                    throw std::logic_error(
                        "G26B G14 WATER WSTARR has no live COMP thermal/prior");
                const auto n=static_cast<std::size_t>(frame.grid.nx)*
                             static_cast<std::size_t>(frame.grid.ny);
                const auto& mixed=*water_mixht_stage12_;
                if(averaged.ziconv_m.size()!=n||
                   mixed.comp_third_qh_wm2.size()!=n||
                   mixed.comp_third_temperature_k.size()!=n||
                   mixed.comp_third_density_kgm3.size()!=n)
                    throw std::invalid_argument(
                        "G26B G14 NOAA WSTARR source array extents invalid");
                p6e::WstarrInput input;
                input.nx=static_cast<std::size_t>(frame.grid.nx);
                input.ny=static_cast<std::size_t>(frame.grid.ny);
                input.water_first=frame.grid.iwat1;
                input.water_last=frame.grid.iwat2;
                input.landuse=frame.grid.landuse;
                input.zi_conv_m=averaged.ziconv_m;
                input.heat_flux_wm2=mixed.comp_third_qh_wm2;
                input.temp_k=mixed.comp_third_temperature_k;
                input.rho_kgm3=mixed.comp_third_density_kgm3;
                input.initial_wstar_ms.assign(n,0.f);
                auto velocity=p6e::wstarr(input);
                if(velocity.size()!=n)
                    throw std::logic_error(
                        "G26B G14 WSTARR current 82x85 grid incomplete");
                for(std::size_t i=0;i<n;++i){
                    if(!std::isfinite(velocity[i])||velocity[i]<0.f)
                        throw std::logic_error(
                            "G26B G14 WSTARR nonfinite/negative");
                    if(frame.grid.landuse[i]>=frame.grid.iwat1&&
                       frame.grid.landuse[i]<=frame.grid.iwat2&&
                       velocity[i]!=0.f)
                        throw std::logic_error(
                            "G26B G14 NOAA neutral WATER WSTAR nonzero");
                }
                water_wstarr_stage14_.emplace(std::move(velocity));
                ++phase_;
                return;
            }
            if(phase_==3) {
                // Actual original G14 stage 15 TEMP3D follows one native
                // MIXHT/AVEMIX/WSTARR on this identical first-hour frame.
                // The original PREPDI AA/BB FACET physical temperature
                // and COMP-third surface T are computed, not imported
                // from any original MET or detached G56 diagnostic.
                const auto& wstar=source_water_wstarr_stage14(frame);
                const auto& upper=diagno_.selected_upper_for_comp(frame);
                if(!water_mixht_stage12_||!water_avemix_stage13_||
                   frame.next.zi_m!=previous_.zi_m||
                   frame.next.ziconv_m!=previous_.ziconv_m||
                   frame.next.dptt_k!=previous_.dptt_k)
                    throw std::logic_error(
                        "G26B native G14 NOAA TEMP3D prior/mixing not staged");
                const auto n=static_cast<std::size_t>(frame.grid.nx)*
                             static_cast<std::size_t>(frame.grid.ny);
                const auto controls=g18c3_parse_original_temp3d_controls(
                    source_.original_metinp);
                const auto faces=g18b5_selected_native_temperature_faces(
                    frame,upper);
                if(controls.itprog!=0||!controls.lcalgrd||
                   faces.end!=frame.input.end||
                   faces.station_ids.size()!=1||
                   faces.face_height_m.size()!=10||
                   faces.aa_face_k.size()!=10||
                   faces.bb_face_k.size()!=10||
                   water_mixht_stage12_->comp_third_temperature_k.size()!=n||
                   water_avemix_stage13_->ziconv_m.size()!=n||
                   wstar.size()!=n)
                    throw std::invalid_argument(
                        "G26B G14 source AA/BB COMP TEMP3D not physical");
                p6e::Temp3dObservedInput input;
                input.nx=static_cast<std::size_t>(frame.grid.nx);
                input.ny=static_cast<std::size_t>(frame.grid.ny);
                input.nz=9;
                input.dgrid_m=frame.grid.grid_km*1000.f;
                input.irad=controls.irad;
                using namespace std::chrono;
                const auto h=duration_cast<hours>(
                    frame.input.end-floor<days>(frame.input.end)).count();
                input.current_hour_utc=static_cast<int>(h%12);
                input.face_z_m=faces.face_height_m;
                input.justa=faces.justa;
                input.past_seconds=faces.past_seconds;
                input.to_go_seconds=faces.to_go_seconds;
                input.aa_face_temp_k=faces.aa_face_k;
                input.bb_face_temp_k=faces.bb_face_k;
                input.surface_temp_k=
                    water_mixht_stage12_->comp_third_temperature_k;
                input.convective_zi_m=water_avemix_stage13_->ziconv_m;
                for(const auto& st:frame.stations.upper) {
                    input.station_x_m.push_back(st.local_x_m);
                    input.station_y_m.push_back(st.local_y_m);
                }
                auto temperature=p6e::temp3d_observed_land(input);
                if(temperature.size()!=9*n)
                    throw std::logic_error(
                        "G26B G14 source TEMP3D nine-layer field missing");
                for(std::size_t i=0;i<n;++i)
                    if(temperature[i]!=input.surface_temp_k[i])
                        throw std::logic_error(
                            "G26B native G14 TEMP3D k1 not COMP third SURFVAR");
                for(float v:temperature)
                    if(!std::isfinite(v)||v<180.f||v>350.f)
                        throw std::logic_error(
                            "G26B G14 TEMP3D nonphysical source temperature");
                water_temp3d_stage15_.emplace(std::move(temperature));
                ++phase_;
                return;
            }
            if(phase_==4) {
                // Stage16 is an in-flight source-only P6F precommit:
                // all 45 fields MUST be prepared from the live actor,
                // not detached G57/G58/G59. G18D1 validates output
                // before updating frame.next or any native fields.
                if(!water_mixht_stage12_||!water_avemix_stage13_||
                   !water_wstarr_stage14_||!water_temp3d_stage15_||
                   frame.next.zi_m!=previous_.zi_m||
                   frame.next.ziconv_m!=previous_.ziconv_m||
                   frame.next.dptt_k!=previous_.dptt_k)
                    throw std::logic_error(
                        "G26B same-hour NOAA G14 P6F has no physical COMP");
                auto prepared=g64_real_noaa_p6f_from_live_g14(
                    frame,source_,*water_mixht_stage12_,
                    *water_avemix_stage13_,
                    *water_wstarr_stage14_,
                    *water_temp3d_stage15_,true);
                if(!prepared.actual_g14_stage16_precommit_validated||
                   prepared.g14_hour_committed||
                   prepared.source_clocks_published||
                   prepared.ready_for_next_hour||
                   prepared.candidate_dataset.hourly.size()!=45)
                    throw std::logic_error(
                        "G26B G14 P6F failed source-native precommit");
                // In-flight native candidate is now staged inside this
                // frame. DO NOT advance the scheduler or publish clocks.
                // G14 atomic commit remains a separate science gate.
                frame.next=prepared.candidate_next;
                frame.fields=prepared.candidate_fields;
                water_p6f_stage16_.emplace(std::move(prepared));
                ++phase_;
                return;
            }
            if(phase_!=0)
                throw std::invalid_argument(
                    "G26B genuine NOAA P6F stage order unsupported");
            auto candidate=g63_real_noaa_g14_comp_mixht_stage12(
                frame,source_,*original_noow_water_,diagno_,true);
            std::size_t valid_ss=0;
            for(const auto& obs:frame.surface.by_station)
                if(obs.wind_valid)++valid_ss;
            if(!candidate.source_native_comp_mixht_uncommitted||
               valid_ss==0||
               candidate.valid_ss!=valid_ss||
               candidate.missing_ss!=frame.stations.surface.size()-valid_ss||
               candidate.water_cells!=63||candidate.land_cells!=6907)
                throw std::logic_error(
                    "G26B native water G14 COMP 12 candidate invalid");
            water_mixht_stage12_.emplace(std::move(candidate));
            live_=&frame;
            hour_index_=frame.hour_index;
            end_=frame.input.end;
            previous_=frame.previous;
            ++phase_;
            return;
        }
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
                    selected.allow_asymmetric_source_audit=
                        (frame.stations.surface.size()==1&&
                         frame.stations.upper.size()>=2&&
                         frame.stations.upper.size()>=2)||
                        (frame.stations.surface.size()>=2&&
                         frame.stations.surface.size()>=2&&
                         frame.stations.upper.size()==1);
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

    [[nodiscard]] const G63RealNoaaG14MixhtStage12& source_water_mixht_stage12(
        const MultiHourFrame& frame) const {
        if(!source_.research_noow_water_source_only||
           phase_!=1||!water_mixht_stage12_||
           &frame!=live_||frame.hour_index!=hour_index_||
           frame.input.end!=end_||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k||
           frame.next.zi_m!=previous_.zi_m||
           frame.next.ziconv_m!=previous_.ziconv_m||
           frame.next.dptt_k!=previous_.dptt_k)
            throw std::logic_error(
                "G26B true native WATER MIXHT stage12 detached or committed");
        return *water_mixht_stage12_;
    }

    [[nodiscard]] const G18C1AvemixOutput& source_water_avemix_stage13(
        const MultiHourFrame& frame) const {
        if(phase_!=2||!water_avemix_stage13_||
           !source_.research_noow_water_source_only||
           &frame!=live_||frame.hour_index!=hour_index_||
           frame.input.end!=end_||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k||
           frame.next.zi_m!=previous_.zi_m||
           frame.next.ziconv_m!=previous_.ziconv_m||
           frame.next.dptt_k!=previous_.dptt_k)
            throw std::logic_error("G26B source WATER AVEMIX detached from G14");
        return *water_avemix_stage13_;
    }

    [[nodiscard]] const std::vector<float>& source_water_wstarr_stage14(
        const MultiHourFrame& frame) const {
        if(phase_!=3||!water_wstarr_stage14_||
           !source_.research_noow_water_source_only||
           &frame!=live_||frame.hour_index!=hour_index_||
           frame.input.end!=end_||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k||
           frame.next.zi_m!=previous_.zi_m||
           frame.next.ziconv_m!=previous_.ziconv_m||
           frame.next.dptt_k!=previous_.dptt_k)
            throw std::logic_error(
                "G26B genuine NOAA WSTARR not staged on same G14 frame");
        return *water_wstarr_stage14_;
    }

    [[nodiscard]] const std::vector<float>& source_water_temp3d_stage15(
        const MultiHourFrame& frame) const {
        if(phase_!=4||!water_temp3d_stage15_||
           !source_.research_noow_water_source_only||
           &frame!=live_||frame.hour_index!=hour_index_||
           frame.input.end!=end_||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k||
           frame.next.zi_m!=previous_.zi_m||
           frame.next.ziconv_m!=previous_.ziconv_m||
           frame.next.dptt_k!=previous_.dptt_k)
            throw std::logic_error(
                "G26B actual NOAA TEMP3D not from uncommitted G14 firsthour");
        return *water_temp3d_stage15_;
    }

    [[nodiscard]] const G64RealNoaaP6FPrecommit& source_water_p6f_stage16(
        const MultiHourFrame& frame) const {
        if(phase_!=5||!water_p6f_stage16_||
           !source_.research_noow_water_source_only||
           &frame!=live_||frame.hour_index!=hour_index_||
           frame.input.end!=end_||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k||
           frame.next.zi_m!=water_p6f_stage16_->candidate_next.zi_m||
           frame.next.ziconv_m!=water_p6f_stage16_->candidate_next.ziconv_m||
           frame.next.dptt_k!=water_p6f_stage16_->candidate_next.dptt_k||
           frame.fields.temperature_k!=
               water_p6f_stage16_->candidate_fields.temperature_k)
            throw std::logic_error("G26B G14 source P6F detached or mutated");
        return *water_p6f_stage16_;
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
    const G41SelectedNoowWaterFirstHourSource* original_noow_water_=nullptr;
    std::optional<G63RealNoaaG14MixhtStage12> water_mixht_stage12_;
    std::optional<G18C1AvemixOutput> water_avemix_stage13_;
    std::optional<std::vector<float>> water_wstarr_stage14_;
    std::optional<std::vector<float>> water_temp3d_stage15_;
    std::optional<G64RealNoaaP6FPrecommit> water_p6f_stage16_;
    bool normal_trial_=false;
    const MultiHourFrame* live_=nullptr;
    p6::NativeGridMemory previous_;
    std::chrono::sys_seconds end_{};
    std::size_t hour_index_=0;
    unsigned phase_=0;
};
} // namespace cteas::calmet::p6g
