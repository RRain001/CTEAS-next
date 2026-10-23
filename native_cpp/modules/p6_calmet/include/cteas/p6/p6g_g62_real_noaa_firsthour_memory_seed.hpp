#pragma once
// S4-R1c8n G62: genuine source-native first-hour hidden COMP state bundle.
// The 45 original-format CALMET.DAT fields CANNOT reconstruct ZICONV/DPTT.
// G54, G59 are independently computed from actual source files; do not
// import reference/original Fortran intermediate states as native inputs.
// This is a physical candidate, NOT a G14 transaction, station-clock commit,
// second-hour forcing admission, general G26, or P7 output.
#include "cteas/p6/p6g_g59_real_noaa_firsthour_dataset.hpp"
#include "cteas/p6/p6g_g26b_file_backed_comp_bridge.hpp"
#include "cteas/p6/p6g_g42_selected_real_water_missing_wind1.hpp"
#include "cteas/p6/p6g_g43_comp_missfc_source.hpp"
#include "cteas/p6/p6g_g47_real_water_post_slope.hpp"
#include "cteas/p6/p6g_g48_real_sparse_stheor.hpp"
#include "cteas/p6/p6g_g54_real_land_mixht.hpp"
#include "cteas/p6/p6g_g55_real_comp_wstarr.hpp"
#include <bit>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G62RealNoaaFirstHourMemorySeed {
    std::chrono::sys_seconds source_end{};
    p6::NativeGridMemory post_comp;
    bool source_native_hidden_memory_candidate=false;
    bool firsthour_g59_45_fields_crosschecked=false;
    bool g14_source_preflight_only=false;
    bool g14_prepdi_clocks_staged_unpublished=false;
    bool g14_wind1_source_native_bitwise_verified=false;
    bool g14_fradj_source_native_bitwise_verified=false;
    bool g14_source_missfc_original_wind_untouched=false;
    bool g14_water_thermal_slope_bitwise_verified=false;
    bool g14_real_sparse_stheor_g24_bitwise_verified=false;
    bool g14_water_comp_mixht_stage12_bitwise_verified=false;
    bool g14_water_comp_avemix_stage13_bitwise_verified=false;
    bool g14_water_comp_wstarr_stage14_bitwise_verified=false;
    bool g14_17_stage_transaction_committed=false;
    bool station_clocks_published=false;
    bool second_hour_prior_state_consumed=false;
    bool g26_p7_production=false;
};

inline G62RealNoaaFirstHourMemorySeed g62_real_noaa_firsthour_memory_seed(
    const G19SourceFilePaths& paths, bool explicitly_forensic_only) {
    if(!explicitly_forensic_only)
        throw std::invalid_argument("G62 hidden memory cannot enter production");
    // G54's post-LAND MIXHT DPTT and post-AVEMIX ZI/ZICONV are separate
    // *physical* arrays and must remain three distinct native REAL4 planes.
    const auto physical=g54_real_noaa_firsthour_land_mixht(paths,true);
    const auto file=g59_source_noaa_firsthour_dataset(paths,true);
    const auto source=g41_load_selected_noow_water_first_hour_source(paths,true);
    // The unchanged Fortran COMP performs MISSFC before DIAGNO.
    // Keep P5/SURF original observations untouched. G43 generates a
    // detached source-owned model-internal copy of ONLY the five nonwind
    // fields, and leaves genuine absent surface wind + precipitation
    // unchanged; no original result/trace may enter the native model.
    const auto resolved=g43_original_comp_missfc_source_only(
        source,source.source.surface.hourly.front(),true);
    if(!resolved.source_comp_missfc_complete||
       resolved.G14_G26_production_accepted||
       resolved.original_raw.by_station.size()!=2||
       resolved.original_comp_resolved.by_station.size()!=2)
        throw std::logic_error("G14 source original COMP MISSFC unavailable");
    for(std::size_t i=0;i<2;++i) {
        const auto& before=resolved.original_raw.by_station[i];
        const auto& after=resolved.original_comp_resolved.by_station[i];
        if(before.wind_valid!=after.wind_valid||
           before.wind_speed_mps!=after.wind_speed_mps||
           before.wind_direction_deg!=after.wind_direction_deg||
           before.precip_code!=after.precip_code||
           before.precipitation_code_valid!=after.precipitation_code_valid||
           !after.cloud_valid||!after.temperature_valid||
           !after.pressure_valid||!after.humidity_valid||
           !after.ceiling_valid)
            throw std::logic_error(
                "G14 cannot turn a missing NOAA observation into calm or alter P5");
    }
    // Reconstruct the SAME physical model-internal source snapshot on
    // independent audit and G14 paths, never touch raw P5 source.
    auto reference_source=source;
    reference_source.source.surface.hourly.front()=
        resolved.original_comp_resolved;
    // The SAME stronger G19 G14-source admission used by accepted C2,
    // now opt-in for original G38 neutral WATER controls. Stage-zero
    // PREPDI is prepared on the authoritative next frame; there is no
    // separate clock authority, no externally written prior ZICONV, and
    // no fabricated G14 17-stage commit or second-hour promotion.
    auto g14_source=g19_load_original_source_case(paths,true);
    g14_source.surface.hourly.front()=resolved.original_comp_resolved;
    auto scheduler=g14_source.make_scheduler();
    auto frame=scheduler.preview_next_hour();
    G18D2StationClockAuthority station_clocks;
    // Real G26A, not a second PREPDI or G41 physics scheduler: execute
    // native stage 0 PREPDI then stage 1 WIND1 on this very same frame.
    // Independent G42 parity is comparison-only, never fed into the actor.
    G26SourceFileBackedG14DiagnoBridge g14_diagno(
        scheduler,station_clocks,g14_source);
    g14_diagno.run_selected(p6::kHefeiOriginalStageOrder[0],frame,true);
    g14_diagno.run_selected(p6::kHefeiOriginalStageOrder[1],frame,true);
    const auto& live_wind1=g14_diagno.selected_source_wind1_after_stage(frame);
    const auto independent_wind1=
        g42_selected_real_water_missing_wind1(frame,reference_source,true);
    constexpr std::size_t n=82U*85U;
    const auto real4_equal=[](const std::vector<float>& a,
                              const std::vector<float>& b) {
        if(a.size()!=b.size())return false;
        for(std::size_t i=0;i<a.size();++i)
            if(std::bit_cast<std::uint32_t>(a[i])!=
               std::bit_cast<std::uint32_t>(b[i]))return false;
        return true;
    };
    if(!real4_equal(live_wind1.u_mps,independent_wind1.native_firstguess.u_mps)||
       !real4_equal(live_wind1.v_mps,independent_wind1.native_firstguess.v_mps))
        throw std::logic_error(
            "G26 actual G14 sparse NOAA WIND1 differs from independent G42");
    // Continue the VERY SAME native G26A G14 candidate to original
    // FRADJ stage 2, without publishing AA/BB, CGAMMA or 3-grid memory.
    // For cross-path checks, G41 consumes only source-owned observations
    // and G18E4 staged gamma, never an original CALMET output oracle.
    const auto& staged_gamma=g14_diagno.selected_source_gamma_after_stage(frame);
    g14_diagno.run_selected(p6::kHefeiOriginalStageOrder[2],frame,true);
    const auto& live_fradj=g14_diagno.selected_source_fradj_after_stage(frame);
    const auto reference_fradj=g41_real_water_first_hour_native_fradj(
        frame,reference_source,staged_gamma,
        independent_wind1.native_firstguess,true);
    if(!real4_equal(live_fradj.corrected_wind.u,
                    reference_fradj.corrected_wind.u)||
       !real4_equal(live_fradj.corrected_wind.v,
                    reference_fradj.corrected_wind.v)||
       !real4_equal(live_fradj.gamma_k_per_m,
                    reference_fradj.gamma_k_per_m)||
       !real4_equal(live_fradj.temperature_before_k,
                    reference_fradj.temperature_before_k)||
       !real4_equal(live_fradj.temperature_after_k,
                    reference_fradj.temperature_after_k)||
       live_fradj.corrected_wind.u.size()!=9*n||
       live_fradj.corrected_wind.v.size()!=9*n||
       live_fradj.gamma_k_per_m.size()!=n||
       live_fradj.temperature_before_k.size()!=n||
       live_fradj.temperature_after_k.size()!=n)
        throw std::logic_error(
            "G26 same-frame NOAA G21 FRADJ differs from G41 source parity");
    // Stages 3..6 preserve the original G14 order and re-use accepted
    // G39 WATER HEATFX/ELUSTR plus original G22 SLOPE kernel. These
    // four checkpoints are the same live frame as PREPDI/WIND1/FRADJ.
    // G47 provides an independent *native/source* cross-path, not a
    // Fortran oracle and never becomes the actor's input.
    for(std::size_t k=3;k<=6;++k)
        g14_diagno.run_selected(p6::kHefeiOriginalStageOrder[k],frame,true);
    const auto& live_thermal=
        g14_diagno.selected_source_water_thermal_after_stage(frame);
    const auto independent_thermal=
        g47_actual_noow_water_after_elustr_slope(paths,true);
    const auto& g47=independent_thermal.thermal.native_heat;
    if(live_thermal.end!=frame.input.end||
       independent_thermal.end!=frame.input.end||
       !real4_equal(live_thermal.heat.temperature_k,
                    g47.heat.temperature_k)||
       !real4_equal(live_thermal.heat.density_kg_m3,
                    g47.heat.density_kg_m3)||
       !real4_equal(live_thermal.elustr.qh_wm2,
                    g47.elustr.qh_wm2)||
       !real4_equal(live_thermal.elustr.ustar_mps,
                    g47.elustr.ustar_mps)||
       !real4_equal(live_thermal.elustr.el_m,
                    g47.elustr.el_m)||
       !real4_equal(live_thermal.post_slope_wind.u,
                    independent_thermal.slope.post_slope_wind.u)||
       !real4_equal(live_thermal.post_slope_wind.v,
                    independent_thermal.slope.post_slope_wind.v)||
       live_thermal.heat.temperature_k.size()!=n||
       live_thermal.heat.density_kg_m3.size()!=n||
       live_thermal.elustr.qh_wm2.size()!=n||
       live_thermal.elustr.ustar_mps.size()!=n||
       live_thermal.elustr.el_m.size()!=n||
       live_thermal.post_slope_wind.u.size()!=9*n||
       live_thermal.post_slope_wind.v.size()!=9*n)
        throw std::logic_error(
            "G26 same-frame NOAA G22 thermal/SLOPE differs from source G47");
    // True first-hour G26A stages 7..11, not a stand-alone G48 oracle:
    // original station STHEOR/DIAGI, INTER2, WINDBC/SMOOTH/DIVCEL/W
    // consume the same previously calculated G22 thermal and the
    // untouched original prior-hour COMP source state.
    for(std::size_t k=7;k<=11;++k)
        g14_diagno.run_selected(p6::kHefeiOriginalStageOrder[k],frame,true);
    const auto& live_g23=g14_diagno.selected_station_for_comp(frame);
    const auto& live_g24=g14_diagno.selected_wind_for_comp(frame);
    const auto independently_source_native=
        g48_real_sparse_stheor_first_hour(paths,true,true,true,false);
    if(!independently_source_native.firsthour_inter2_candidate_unverified||
       !independently_source_native.firsthour_g24_tail_unverified||
       !independently_source_native.source_p5_raw_wind_unchanged||
       !independently_source_native.native_shared_g16_sparse_wind1_equal_to_g42||
       independently_source_native.missing_wind_skipped!=1||
       independently_source_native.native_valid_station.size()!=1||
       live_g23.station_diagi.size()!=1||
       live_g23.station_diagi[0].surface_id!=
           independently_source_native.native_valid_station[0].surface_id||
       !real4_equal(live_g23.inter2_u.component_mps,
                    independently_source_native.firsthour_inter2_u_unverified)||
       !real4_equal(live_g23.inter2_v.component_mps,
                    independently_source_native.firsthour_inter2_v_unverified)||
       !real4_equal(live_g24.wind.u_mps,
                    independently_source_native.firsthour_g24_tail_unverified->wind.u_mps)||
       !real4_equal(live_g24.wind.v_mps,
                    independently_source_native.firsthour_g24_tail_unverified->wind.v_mps)||
       !real4_equal(live_g24.wind.w_face_mps,
                    independently_source_native.firsthour_g24_tail_unverified->wind.w_face_mps)||
       live_g23.inter2_u.component_mps.size()!=9*n||
       live_g23.inter2_v.component_mps.size()!=9*n||
       live_g24.wind.u_mps.size()!=9*n||
       live_g24.wind.v_mps.size()!=9*n||
       live_g24.wind.w_face_mps.size()!=10*n||
       frame.fields.u_mps!=live_g24.wind.u_mps||
       frame.fields.v_mps!=live_g24.wind.v_mps||
       frame.fields.w_face_mps!=live_g24.wind.w_face_mps)
        throw std::logic_error(
            "G26 real NOAA same-frame STHEOR/INTER2/G24 disagrees with independent G48");
    // Actual G26B, not G54, executes stage12 from this G26A live frame.
    // The independent frozen real G54 case is re-run ONLY for comparison.
    // Absent stages 13..16 remain forbidden, including scheduler commit.
    G26BSourceFileBackedCompBridge g14_comp(
        g14_diagno,g14_source,false,&source);
    g14_comp.run_selected(p6::kHefeiOriginalStageOrder[12],frame,true);
    const auto& live_mix=g14_comp.source_water_mixht_stage12(frame);
    const auto standalone_mix=g54_real_noaa_firsthour_land_mixht(paths,true);
    if(!live_mix.source_native_comp_mixht_uncommitted||
       !standalone_mix.sparse_first_hour_research_only||
       standalone_mix.native_avemix_ready||
       standalone_mix.g26_45field_ready||
       live_mix.end!=frame.input.end||
       standalone_mix.end!=frame.input.end||
       live_mix.water_cells!=63||live_mix.land_cells!=6907||
       live_mix.valid_ss!=1||live_mix.missing_ss!=1||
       !real4_equal(live_mix.zi_before_avemix_m,
                    standalone_mix.zi_before_avemix_m)||
       !real4_equal(live_mix.ziconv_before_avemix_m,
                    standalone_mix.ziconv_before_avemix_m)||
       !real4_equal(live_mix.dptt_before_avemix_k,
                    standalone_mix.dptt_before_avemix_k)||
       !real4_equal(live_mix.comp_third_temperature_k,
                    standalone_mix.comp_third_heat_k)||
       !real4_equal(live_mix.comp_third_qh_wm2,
                    standalone_mix.comp_third_qh_wm2)||
       !real4_equal(live_mix.comp_third_density_kgm3,
                    standalone_mix.comp_third_density_kgm3)||
       !real4_equal(live_mix.comp_third_ustar_mps,
                    standalone_mix.comp_third_ustar_mps)||
       !real4_equal(live_mix.comp_third_el_m,
                    standalone_mix.comp_third_el_m)||
       live_mix.zi_before_avemix_m.size()!=n||
       live_mix.ziconv_before_avemix_m.size()!=n||
       live_mix.dptt_before_avemix_k.size()!=n||
       live_mix.comp_third_temperature_k.size()!=n||
       live_mix.comp_third_qh_wm2.size()!=n||
       live_mix.comp_third_density_kgm3.size()!=n||
       live_mix.comp_third_ustar_mps.size()!=n||
       live_mix.comp_third_el_m.size()!=n||
       frame.next.zi_m!=frame.previous.zi_m||
       frame.next.ziconv_m!=frame.previous.ziconv_m||
       frame.next.dptt_k!=frame.previous.dptt_k)
        throw std::logic_error(
            "G26B stage12 same G14 NOAA WATER+LAND MIXHT differs from native G54");
    // G26B stage 13 computes the actual original AVEMIX on the same
    // live G14 frame and its uncommitted stage12 MIXHT candidate.
    // Compare only afterwards to independently sourced G54; a detached
    // G54 AVEMIX must never become the actor's initial physical field.
    g14_comp.run_selected(p6::kHefeiOriginalStageOrder[13],frame,true);
    const auto& live_ave=g14_comp.source_water_avemix_stage13(frame);
    if(!real4_equal(live_ave.zi_m,standalone_mix.zi_after_avemix_m)||
       !real4_equal(live_ave.ziconv_m,standalone_mix.ziconv_after_avemix_m)||
       live_ave.zi_m.size()!=n||live_ave.ziconv_m.size()!=n||
       frame.next.zi_m!=frame.previous.zi_m||
       frame.next.ziconv_m!=frame.previous.ziconv_m||
       frame.next.dptt_k!=frame.previous.dptt_k)
        throw std::logic_error(
            "G26B real native G14 AVEMIX does not match G54 post-COMP memory");
    // Execute ACTUAL G26B stage14 on this same G14 actor, using only
    // stage12 COMP-third T/QH/RHO and stage13 post-AVEMIX ZICONV.
    // The stand-alone G55 path is recomputed ONLY to compare native bits.
    g14_comp.run_selected(p6::kHefeiOriginalStageOrder[14],frame,true);
    const auto& actual_wstarr=g14_comp.source_water_wstarr_stage14(frame);
    const auto standalone_wstarr=g55_native_real_comp_wstarr(paths,true);
    if(!standalone_wstarr.firsthour_source_only||
       standalone_wstarr.g26_45field_ready||
       standalone_wstarr.native_temp3d_ready||
       standalone_wstarr.six_hour_causal_ready||
       standalone_wstarr.end!=frame.input.end||
       actual_wstarr.size()!=n||
       standalone_wstarr.wstar_mps.size()!=n||
       !real4_equal(actual_wstarr,standalone_wstarr.wstar_mps)||
       frame.next.zi_m!=frame.previous.zi_m||
       frame.next.ziconv_m!=frame.previous.ziconv_m||
       frame.next.dptt_k!=frame.previous.dptt_k)
        throw std::logic_error(
            "G26B G14 source NOAA stage14 WSTARR not exact native G55");
    // Stage 15 TEMP3D is still NOT ADMITTED. No previous/next memory
    // mutation, stage skipping, clock publish or G14 commit is legal.
    bool stage15_denied=false;
    try {
        g14_comp.run_selected(p6::kHefeiOriginalStageOrder[15],frame,true);
    } catch(const std::invalid_argument&) {
        stage15_denied=true;
    }
    if(!stage15_denied||
       frame.next.zi_m!=frame.previous.zi_m||
       frame.next.ziconv_m!=frame.previous.ziconv_m||
       frame.next.dptt_k!=frame.previous.dptt_k)
        throw std::logic_error(
            "G26B unverified G14 stage15 TEMP3D was inadvertently admitted");
    if(frame.grid.nx!=82||frame.grid.ny!=85||
       frame.stations.surface.size()!=2||frame.stations.upper.size()!=1||
       source.source.surface.hourly.size()!=6||
       !g14_source.research_noow_water_source_only||
       g14_source.source_water_cells.size()!=63||
       g14_source.original_metinp!=source.source.original_metinp||
       g14_source.grid.landuse!=source.source.grid.landuse||
       g14_source.stations.surface.size()!=source.source.stations.surface.size()||
       g14_source.stations.upper.size()!=source.source.stations.upper.size()||
       g14_diagno.selected_checkpoints()!=12||
       !g14_diagno.source_diagno_ready()||
       g14_diagno.clocks_published()||
       station_clocks.has_published_hour()||
       scheduler.completed_hours()!=0||
       independent_wind1.missing_observed_surface_sites!=1||
       live_wind1.u_mps.size()!=9*n||
       live_wind1.v_mps.size()!=9*n||
       frame.hour_index!=0||scheduler.completed_hours()!=0||
       physical.end!=frame.input.end||
       !physical.sparse_first_hour_research_only||
       !physical.native_avemix_candidate_unverified||
       physical.native_avemix_ready||
       physical.g26_45field_ready||physical.causal_six_hour_ready||
       physical.actual_land_count!=6907||physical.actual_water_count!=63||
       !file.firsthour_source_native_45_record_dataset||
       file.g14_six_hour_causal||file.g26_production||file.p7_accepted||
       file.dataset.hourly.size()!=45||file.dataset.header.irlg!=1||
       physical.zi_after_avemix_m.size()!=n||
       physical.ziconv_after_avemix_m.size()!=n||
       physical.dptt_before_avemix_k.size()!=n||
       frame.previous.zi_m.size()!=n||
       frame.previous.ziconv_m.size()!=n||
       frame.previous.dptt_k.size()!=n)
        throw std::invalid_argument(
            "G62 actual firsthour original-source physics/clock incomplete");

    // The signed-zero distinction matters for REAL4 COMMON state. Do not
    // compare rounded strings or copy the CALMET.DAT ZI into COMP memory.
    const cteas::p6f::Calmet21Field* serialized_zi=nullptr;
    for(const auto& field:file.dataset.hourly)
        if(field.label=="ZI      ") {
            if(serialized_zi)
                throw std::logic_error("G62 duplicate P6F ZI source record");
            serialized_zi=&field;
        }
    if(!serialized_zi||serialized_zi->integer||
       serialized_zi->real_values.size()!=n||
       cteas::p6f::instant_seconds(serialized_zi->end)!=
           frame.input.end.time_since_epoch().count())
        throw std::logic_error(
            "G62 firsthour P6F and native COMP hour identity changed");
    for(std::size_t k=0;k<n;++k) {
        const float z=physical.zi_after_avemix_m[k];
        const float zc=physical.ziconv_after_avemix_m[k];
        const float dptt=physical.dptt_before_avemix_k[k];
        if(!std::isfinite(z)||!std::isfinite(zc)||!std::isfinite(dptt)||
           z<0.f||zc<0.f||z==9999.f||zc==9999.f||dptt==9999.f||
           std::bit_cast<std::uint32_t>(z)!=
               std::bit_cast<std::uint32_t>(serialized_zi->real_values[k]))
            throw std::logic_error(
                "G62 hidden COMP source-memory / serialized firsthour ZI drift");
        // The first-hour source contract begins with original COMMON zero;
        // it must not silently inherit an unrelated warm-start state.
        if(frame.previous.zi_m[k]!=0.f||
           frame.previous.ziconv_m[k]!=0.f||
           frame.previous.dptt_k[k]!=0.f)
            throw std::logic_error(
                "G62 source firsthour initial COMMON memory not cold");
    }
    G62RealNoaaFirstHourMemorySeed result;
    result.source_end=physical.end;
    result.post_comp.zi_m=physical.zi_after_avemix_m;
    result.post_comp.ziconv_m=physical.ziconv_after_avemix_m;
    result.post_comp.dptt_k=physical.dptt_before_avemix_k;
    result.source_native_hidden_memory_candidate=true;
    result.firsthour_g59_45_fields_crosschecked=true;
    result.g14_source_preflight_only=true;
    result.g14_prepdi_clocks_staged_unpublished=true;
    result.g14_wind1_source_native_bitwise_verified=true;
    result.g14_fradj_source_native_bitwise_verified=true;
    result.g14_source_missfc_original_wind_untouched=true;
    result.g14_water_thermal_slope_bitwise_verified=true;
    result.g14_real_sparse_stheor_g24_bitwise_verified=true;
    result.g14_water_comp_mixht_stage12_bitwise_verified=true;
    result.g14_water_comp_avemix_stage13_bitwise_verified=true;
    result.g14_water_comp_wstarr_stage14_bitwise_verified=true;
    return result;
}
} // namespace cteas::calmet::p6g
