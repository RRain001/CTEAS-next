#pragma once
// S4-R1c8f: genuine first-hour 2SS/1US original sparse NOAA
// G24→COMP third SURFVAR→HEATFX/ELUSTR→WATER+LAND MIXHT.
// Every physical formula belongs to the EXISTING P6E mixht_observed_mc
// and selected G17B4/G17C1/G17C2/G18B/G37/G35/G36 kernels.
// Never accept full COMP/G26 or publish one-hour candidate to scheduler.
#include "cteas/p6/p6g_g48_real_sparse_stheor.hpp"
#include "cteas/p6/p6g_g53_real_water_comp_neutral.hpp"
#include "cteas/p6/p6g_g18b3_upper_choice.hpp"
#include "cteas/p6/p6g_g18d5_source_mixht_controls.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G54NativeLandMixhtCandidate {
    std::chrono::sys_seconds end{};
    std::vector<float> zi_before_avemix_m,ziconv_before_avemix_m,dptt_before_avemix_k;
    std::vector<float> comp_third_heat_k,comp_third_qh_wm2;
    std::vector<float> zi_after_avemix_m,ziconv_after_avemix_m;
    bool native_avemix_candidate_unverified=false;
    std::size_t actual_land_count=0,actual_water_count=0;
    std::size_t source_valid_diagi_count=0,source_missing_diagi_count=0;
    bool sparse_first_hour_research_only=false;
    bool native_avemix_ready=false;
    bool g26_45field_ready=false;
    bool causal_six_hour_ready=false;
};
inline G54NativeLandMixhtCandidate g54_real_noaa_firsthour_land_mixht(
    const G19SourceFilePaths& paths,
    bool expressly_forensic_only) {
    if(!expressly_forensic_only)
        throw std::invalid_argument("G54 default G26B WATER MIXHT admission denied");
    // Both G48 and G53 independently reconstruct physical native wind;
    // no reference Fortran U/V/W, QH, ZI, or DPTT enter the native process.
    const auto accepted=g48_real_sparse_stheor_first_hour(
        paths,true,true,true,true);
    if(!accepted.source_p5_raw_wind_unchanged||
       !accepted.native_shared_g16_sparse_wind1_equal_to_g42||
       !accepted.firsthour_g24_tail_unverified||
       !accepted.firsthour_comp_third_candidate_unverified||
       accepted.native_valid_station.size()!=1||
       accepted.missing_wind_skipped!=1||
       accepted.native_g23_inter2_or_g26_ready)
        throw std::logic_error("G54 cannot start before real G48/G24 source");
    const auto actual_g47=g47_actual_noow_water_after_elustr_slope(paths,true);
    auto source=g41_load_selected_noow_water_first_hour_source(paths,true);
    const auto raw=source.source.surface.hourly.front();
    const auto missfc=g43_original_comp_missfc_source_only(
        source,source.source.surface.hourly.front(),true);
    if(!missfc.source_comp_missfc_complete||
       missfc.G14_G26_production_accepted||
       source.source.stations.surface.size()!=2||
       source.source.stations.upper.size()!=1)
        throw std::logic_error("G54 source COMP nonwind MISSFC not accepted");
    for(std::size_t i=0;i<raw.by_station.size();++i)
        if(raw.by_station[i].wind_valid!=
           missfc.original_comp_resolved.by_station[i].wind_valid||
           raw.by_station[i].wind_speed_mps!=
           missfc.original_comp_resolved.by_station[i].wind_speed_mps)
            throw std::logic_error("G54 transformed original observed wind");
    source.source.surface.hourly.front()=missfc.original_comp_resolved;
    auto scheduler=source.source.make_scheduler();
    const auto frame=scheduler.preview_next_hour();
    const auto& geo=source.source.grid;
    const auto& final=accepted.firsthour_g24_tail_unverified->wind;
    const auto n=static_cast<std::size_t>(geo.nx)*
                 static_cast<std::size_t>(geo.ny);
    if(frame.hour_index!=0||scheduler.completed_hours()!=0||
       frame.input.end!=accepted.firsthour_g24_tail_unverified->end||
       actual_g47.end!=frame.input.end||
       accepted.firsthour_comp_third_temperature_unverified.size()!=n)
        throw std::logic_error("G54 independent source clock or final G24 drift");
    const auto partition=g26b_real_water_comp_partition_source_only(
        source,frame,true);
    // Strictly repeat G17B4 physical SURFVAR passes with exact native
    // G42 first guess, G47 FRADJ correction and G24 final U/V.
    G17B4TwoPassSurfvar surface(
        geo,source.source.stations,source.source.surface,frame.surface,
        source.surface_controls,true);
    const auto& w1=actual_g47.thermal.native_wind1.native_firstguess;
    const auto& fr=actual_g47.thermal.native_fradj.corrected_wind;
    surface.after_wind1_before_fradj(
        frame.input.end,w1.u_mps,w1.v_mps);
    surface.after_fradj_before_heatfx(
        frame.input.end,fr.u,fr.v);
    surface.after_final_diagno_before_comp(
        frame.input.end,final.u_mps,final.v_mps,true);
    if(surface.comp_temperature()!=
       accepted.firsthour_comp_third_temperature_unverified)
        throw std::logic_error("G54 third COMP thermal detached from G51");
    const auto comp_heat=selected_iavet1_heat_after_fradj(
        geo,source.source.stations,frame.surface,surface,
        source.water_heat_source.reference_heat,true,true);
    G17C2SelectedElustrControls elcontrol;
    elcontrol.ipsifcn=0;
    elcontrol.zm_m=0.5f*(frame.source_controls->zface_m[0]+
                        frame.source_controls->zface_m[1]);
    elcontrol.explicitly_test_only=true;
    const auto elustr=selected_iavet1_elustr_after_heatfx(
        geo,source.source.stations,frame.surface,surface,comp_heat,
        {final.u_mps,final.v_mps},elcontrol,true,true);
    if(!elustr.water_state_pending_original_WATER||
       elustr.end!=frame.input.end||
       comp_heat.temperature_k.size()!=n||
       elustr.qh_wm2.size()!=n)
        throw std::logic_error("G54 COMP third ELUSTR not source ready");
    G18ASelectedCompControls c;
    c.explicitly_test_only=true;
    auto& mix=c.grid_mixht;
    mix.nx=static_cast<std::size_t>(geo.nx);
    mix.ny=static_cast<std::size_t>(geo.ny);
    mix.landuse=geo.landuse;
    mix.water_first=geo.iwat1;
    mix.water_last=geo.iwat2;
    const auto choice=g18b3_source_deck_upper_choice(
        geo,source.source.stations,source.source.original_metinp);
    if(choice.iupt!=-1||choice.nearu.size()!=n)
        throw std::invalid_argument("G54 genuine NOAA upper NEARU not selected");
    g18b3_bind_test_only_upper_choice(
        mix,geo,source.source.stations,choice,true);
    g18d5_bind_original_mixht_scalars(source.source.original_metinp,c);
    const auto upper=G18BUpperBufferClock{}.select(frame);
    g18b_bind_physical_upper(mix,frame,upper);
    const auto st_controls=g23_source_stheor_station_controls(
        source.source.original_metinp,
        source.source_setcom_station_to_upper,
        source.water_heat_source.reference_heat.coefficients,
        source.source.stations.surface.size(),true);
    if(!std::isfinite(st_controls.fcori_s)||st_controls.fcori_s<=0.f||
       !std::isfinite(st_controls.cmech)||st_controls.cmech<=0.f)
        throw std::invalid_argument("G54 invalid original SETCOM CMECH/FCORI");
    mix.fcori.assign(n,st_controls.fcori_s);
    mix.cmech.assign(n,st_controls.cmech);
    mix.qh=elustr.qh_wm2;
    mix.ustar=elustr.ustar_mps;
    mix.el=elustr.el_m;
    mix.rho=comp_heat.density_kg_m3;
    mix.initial_zi=frame.previous.zi_m;
    mix.initial_ziconv=frame.previous.ziconv_m;
    mix.initial_dptt=frame.previous.dptt_k;
    if(mix.initial_zi.size()!=n||
       mix.initial_ziconv.size()!=n||
       mix.initial_dptt.size()!=n)
        throw std::logic_error("G54 invalid physical prior COMP memory");
    // Reuse G53 native WATER on the SAME final G24 physical winds.
    const auto water=g53_real_source_g24_neutral_water_reference(
        source,frame,*accepted.firsthour_g24_tail_unverified,true);
    if(water.water.size()!=partition.original_water_cell_ordinals.size()||
       water.end!=frame.input.end)
        throw std::logic_error("G54 original WATER stage not complete");
    for(const auto& w:water.water) {
        const auto k=w.source_index;
        mix.initial_zi[k]=w.mixing.zi_m;
        mix.initial_ziconv[k]=w.mixing.ziconv_m;
        mix.qh[k]=w.neutral.qh_buoyancy_wm2;
        mix.ustar[k]=w.neutral.ustar_mps;
        mix.el[k]=w.neutral.el_m;
    }
    // Original DIAGI is indexed in the full 2SS/1US source ordinal
    // space; one SS legitimately has no observed wind. Never synthesize
    // a second STHEOR, fake its current-hour DPTT or renumber.
    std::vector<unsigned char> seen(n,0);
    for(const auto& site:accepted.native_valid_station) {
        if(site.end!=frame.input.end||site.cell>=n||
           seen[site.cell]++||
           !std::isfinite(site.station_mixing.dptt_for_comp_k))
            throw std::invalid_argument("G54 valid sparse station DPTT rejected");
        mix.initial_dptt[site.cell]=site.station_mixing.dptt_for_comp_k;
    }
    const auto physical=p6e::mixht_observed_mc(mix);
    if(physical.zi.size()!=n||physical.ziconv.size()!=n||
       physical.dptt.size()!=n)
        throw std::logic_error("G54 true shared P6E MIXHT incomplete");
    // This kernel is LAND-only. Both before and after its execution,
    // all G53 WATER ZI/ZICONV must remain untouched.
    for(const auto& w:water.water) {
        if(physical.zi[w.source_index]!=w.mixing.zi_m||
           physical.ziconv[w.source_index]!=w.mixing.ziconv_m)
            throw std::logic_error("G54 true LAND MIXHT changed WATER ZI");
    }
    // Original source AVEMIX over the combined WATER+LAND native MIXHT
    // fields; the result is unverified until independently compared.
    const auto avectrl=g18c1_parse_original_avemix(
        source.source.original_metinp);
    const auto start=static_cast<std::size_t>(avectrl.ilevzi-1)*n;
    if(start+n>final.u_mps.size()||start+n>final.v_mps.size())
        throw std::invalid_argument("G54 original ILEVZI source wind invalid");
    const std::vector<float> level_u(final.u_mps.begin()+start,
                                     final.u_mps.begin()+start+n);
    const std::vector<float> level_v(final.v_mps.begin()+start,
                                     final.v_mps.begin()+start+n);
    const auto averaged=g18c1_original_avemix_rebuild(
        geo.nx,geo.ny,avectrl.mnmdav,avectrl.hafang_deg,
        geo.grid_km*1000.f,level_u,level_v,physical.zi,
        physical.ziconv);
    if(averaged.zi_m.size()!=n||averaged.ziconv_m.size()!=n)
        throw std::logic_error("G54 AVEMIX full real GEO not assembled");
    G54NativeLandMixhtCandidate out;
    out.end=frame.input.end;
    out.zi_after_avemix_m=averaged.zi_m;
    out.ziconv_after_avemix_m=averaged.ziconv_m;
    out.native_avemix_candidate_unverified=true;
    out.zi_before_avemix_m=physical.zi;
    out.ziconv_before_avemix_m=physical.ziconv;
    out.dptt_before_avemix_k=physical.dptt;
    out.comp_third_heat_k=comp_heat.temperature_k;
    out.comp_third_qh_wm2=elustr.qh_wm2;
    out.actual_land_count=partition.original_land_cell_ordinals.size();
    out.actual_water_count=water.water.size();
    out.source_valid_diagi_count=accepted.native_valid_station.size();
    out.source_missing_diagi_count=accepted.missing_wind_skipped;
    out.sparse_first_hour_research_only=true;
    return out;
}
} // namespace cteas::calmet::p6g
