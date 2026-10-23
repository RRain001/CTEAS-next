#pragma once
// S4-R1c8r: ACTUAL G26B selected stage-12 original-water MIXHT on the SAME
// live G14 frame. This code uses the current G26A G24 U/V/W, native G43
// COMP-internal SURF data, the current G23 valid SS DIAGI (not fake calm),
// PREPDI UP/NEARU and previous G14 ZI/ZICONV/DPTT.
// Entirely independent of detached G54; reference G54 is comparison-only.
// This one stage is NOT completed COMP, AVEMIX/WSTARR/TEMP3D, G14 commit,
// next-hour forcing, P6F, or general-purpose P6/P7 admission.
#include "cteas/p6/p6g_g26_file_backed_g14_diagno_bridge.hpp"
#include "cteas/p6/p6g_g53_real_water_comp_neutral.hpp"
#include "cteas/p6/p6g_g18b3_upper_choice.hpp"
#include "cteas/p6/p6g_g18d5_source_mixht_controls.hpp"
#include "cteas/p6e/mixht_observed_mc.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G63RealNoaaG14MixhtStage12 {
    std::chrono::sys_seconds end{};
    std::vector<float> zi_before_avemix_m;
    std::vector<float> ziconv_before_avemix_m;
    std::vector<float> dptt_before_avemix_k;
    std::vector<float> comp_third_temperature_k;
    std::vector<float> comp_third_qh_wm2;
    std::vector<float> comp_third_density_kgm3;
    std::vector<float> comp_third_ustar_mps;
    std::vector<float> comp_third_el_m;
    // Original P6F writes neutral WATER USTAR/EL; retain the unmodified
    // COMP-third fields above for independent G54 stage12 parity.
    std::vector<float> p6f_water_reconciled_ustar_mps;
    std::vector<float> p6f_water_reconciled_el_m;
    // P6F stage16 must use current COMP source SOLAR/SETCOM quantities;
    // never steal shortwave/PGT geometry from independent G54/G59.
    std::vector<float> comp_third_shortwave_wm2;
    std::vector<float> comp_third_sun_sine;
    std::vector<int> comp_third_nearest_surface;
    std::size_t valid_ss=0,missing_ss=0,water_cells=0,land_cells=0;
    bool source_native_comp_mixht_uncommitted=false;
};

inline G63RealNoaaG14MixhtStage12 g63_real_noaa_g14_comp_mixht_stage12(
    const MultiHourFrame& live,
    const G19FileBackedCase& source,
    const G41SelectedNoowWaterFirstHourSource& original,
    const G26SourceFileBackedG14DiagnoBridge& diagno,
    bool explicitly_forensic_only,
    bool opt_in_hour3_comp_stage12_trial=false) {
    const auto& geo=live.grid;
    const auto n=static_cast<std::size_t>(geo.nx)*
                 static_cast<std::size_t>(geo.ny);
    if(!explicitly_forensic_only||
       !source.research_noow_water_source_only||
       !diagno.source_diagno_ready()||
       geo.nx!=82||geo.ny!=85||
       ((live.hour_index>1&&!opt_in_hour3_comp_stage12_trial)||
        live.hour_index>2||
        (opt_in_hour3_comp_stage12_trial&&live.hour_index!=2))||
       live.stations.surface.size()!=2||live.stations.upper.size()!=1||
       source.source_water_cells.size()!=63||
       original.source.surface.hourly.size()!=6||
       source.original_metinp!=original.source.original_metinp||
       original.source.grid.landuse!=geo.landuse||
       original.source.grid.terrain_m!=geo.terrain_m||
       source.surface.hourly.size()!=6||
       source.surface.hourly[live.hour_index].end!=live.input.end||
       original.source.surface.hourly[live.hour_index].end!=live.input.end||
       source.surface.hourly[live.hour_index].start!=live.surface.start||
       original.source.surface.hourly[live.hour_index].start!=live.surface.start||
       (live.hour_index==1&&
        live.surface.start!=source.surface.hourly[0].end)||
       (live.hour_index==2&&
        live.surface.start!=source.surface.hourly[1].end)||
       live.input.end!=live.surface.end||
       live.previous.zi_m.size()!=n||
       live.previous.ziconv_m.size()!=n||
       live.previous.dptt_k.size()!=n||
       live.next.zi_m!=live.previous.zi_m||
       live.next.ziconv_m!=live.previous.ziconv_m||
       live.next.dptt_k!=live.previous.dptt_k)
        throw std::invalid_argument(
            "G63 authentic NOAA first-hour live G14 COMP source/prior not accepted");
    const auto& g24=diagno.selected_wind_for_comp(live);
    const auto& station=diagno.selected_station_for_comp(live);
    const auto& wind1=diagno.selected_wind1_for_comp(live);
    const auto& fradj=diagno.selected_fradj_for_comp(live);
    const auto& thermal=diagno.selected_thermal_for_comp(live);
    const auto& upper=diagno.selected_upper_for_comp(live);
    if(g24.end!=live.input.end||station.end!=live.input.end||
       upper.end!=live.input.end||
       station.station_diagi.empty()||
       station.station_diagi.size()>live.stations.surface.size()||
       live.fields.u_mps!=g24.wind.u_mps||
       live.fields.v_mps!=g24.wind.v_mps||
       live.fields.w_face_mps!=g24.wind.w_face_mps||
       g24.wind.u_mps.size()!=9*n||
       g24.wind.v_mps.size()!=9*n||
       g24.wind.w_face_mps.size()!=10*n||
       thermal.heat.temperature_k.size()!=n)
        throw std::invalid_argument(
            "G63 first-hour COMP cannot read fabricated final G26A wind");
    // Station MIXHTST column identity must reflect CURRENT original P5
    // wind validity, not the preceding hour's sparse station count.
    std::size_t station_ordinal=0;
    for(std::size_t i=0;i<live.surface.by_station.size();++i) {
        if(!live.surface.by_station[i].wind_valid)continue;
        if(station_ordinal>=station.station_diagi.size()||
           station.station_diagi[station_ordinal].surface_id!=
             live.stations.surface[i].id)
            throw std::logic_error(
                "G63 true NOAA hour-two COMP source STHEOR ordinal drift");
        ++station_ordinal;
    }
    if(station_ordinal!=station.station_diagi.size())
        throw std::logic_error("G63 current-hour COMP station mask mismatch");
    // Original COMP's third IAVET SURFVAR follows final DIAGNO G24.
    // The earlier G22 heat is a slope-flow estimate, not COMP heat.
    G17B4TwoPassSurfvar surface(
        geo,live.stations,source.surface,live.surface,
        source.surface_controls,true);
    surface.after_wind1_before_fradj(
        live.input.end,wind1.u_mps,wind1.v_mps);
    surface.after_fradj_before_heatfx(
        live.input.end,fradj.corrected_wind.u,fradj.corrected_wind.v);
    if(surface.first_temperature()!=fradj.temperature_before_k||
       surface.final_temperature()!=fradj.temperature_after_k||
       surface.final_temperature()!=thermal.heat.temperature_k)
        throw std::logic_error(
            "G63 original COMP SURFVAR not from live G14 G21/G22");
    surface.after_final_diagno_before_comp(
        live.input.end,g24.wind.u_mps,g24.wind.v_mps,true);
    const auto original_heat=g38_selected_noow_water_hflux_source_only(
        geo,source.original_metinp,true);
    const auto heat=selected_iavet1_heat_after_fradj(
        geo,live.stations,live.surface,surface,
        original_heat.reference_heat,true,true);
    G17C2SelectedElustrControls controls;
    controls.ipsifcn=0;
    controls.zm_m=0.5f*(live.source_controls->zface_m[0]+
                        live.source_controls->zface_m[1]);
    controls.explicitly_test_only=true;
    const auto elustr=selected_iavet1_elustr_after_heatfx(
        geo,live.stations,live.surface,surface,heat,
        {g24.wind.u_mps,g24.wind.v_mps},controls,true,true);
    if(!elustr.water_state_pending_original_WATER||
       heat.end!=live.input.end||elustr.end!=live.input.end||
       heat.temperature_k.size()!=n||
       heat.density_kg_m3.size()!=n||
       elustr.qh_wm2.size()!=n||
       elustr.ustar_mps.size()!=n||
       elustr.el_m.size()!=n)
        throw std::logic_error("G63 original third COMP thermal not physical");
    const auto water=g53_real_source_g24_neutral_water_reference(
        original,live,g24,true,opt_in_hour3_comp_stage12_trial);
    if(!water.genuine_firsthour_water_arithmetic_only||
       water.land_mixht_ready||water.original_causal_memory_ready||
       water.water.size()!=63||water.end!=live.input.end)
        throw std::logic_error("G63 original NOAA G53 WATER was promoted");

    p6e::MixhtObservedMcInput mix;
    mix.nx=static_cast<std::size_t>(geo.nx);
    mix.ny=static_cast<std::size_t>(geo.ny);
    mix.landuse=geo.landuse;
    mix.water_first=geo.iwat1;
    mix.water_last=geo.iwat2;
    const auto choice=g18b3_source_deck_upper_choice(
        geo,live.stations,source.original_metinp);
    if(choice.iupt!=-1||choice.nearu.size()!=n)
        throw std::invalid_argument("G63 genuine NOAA source NEARU not scoped");
    g18b3_bind_test_only_upper_choice(
        mix,geo,live.stations,choice,true);
    G18ASelectedCompControls original_controls;
    original_controls.grid_mixht=mix;
    g18d5_bind_original_mixht_scalars(source.original_metinp,original_controls);
    mix=std::move(original_controls.grid_mixht);
    g18b_bind_physical_upper(mix,live,upper);
    const auto source_st=g23_stheor_original_readcf_controls(source,true);
    if(!std::isfinite(source_st.fcori_s)||source_st.fcori_s<=0.f||
       !std::isfinite(source_st.cmech)||source_st.cmech<=0.f)
        throw std::invalid_argument("G63 real READCF FCORI/CMECH invalid");
    mix.fcori.assign(n,source_st.fcori_s);
    mix.cmech.assign(n,source_st.cmech);
    mix.qh=elustr.qh_wm2;
    mix.ustar=elustr.ustar_mps;
    mix.el=elustr.el_m;
    mix.rho=heat.density_kg_m3;
    // One authoritative previous-COMP state, never original Fortran oracle.
    mix.initial_zi=live.previous.zi_m;
    mix.initial_ziconv=live.previous.ziconv_m;
    mix.initial_dptt=live.previous.dptt_k;
    std::vector<unsigned char> encountered(n,0);
    for(const auto& water_cell:water.water) {
        const auto k=water_cell.source_index;
        if(k>=n||encountered[k]++)
            throw std::invalid_argument("G63 duplicate original WATER ordinal");
        mix.initial_zi[k]=water_cell.mixing.zi_m;
        // Original CALMET v6.5.0 WATER() L32964-33030 computes a
        // *local scalar* ZICONV and stores its result in ZICOLD(I,J).
        // It does NOT write the global gridded ZICONV(I,J). Following
        // MIXHT() skips WATER cells, so the global grid retains the
        // previous hour's AVEMIX ZICONV at these cells until the next
        // AVEMIX call. Preserve G14 committed memory here, rather than
        // overwriting it with G36's source-local neutral ZICONV=0.
        // This distinction is invisible during cold hour one (prior=0),
        // but affects real sixhour WSTAR and TEMP3D starting hour two.
        if(!std::isfinite(live.previous.ziconv_m[k])||
           live.previous.ziconv_m[k]<0.f)
            throw std::invalid_argument(
                "G63 invalid previous global WATER ZICONV");
        mix.qh[k]=water_cell.neutral.qh_buoyancy_wm2;
        mix.ustar[k]=water_cell.neutral.ustar_mps;
        mix.el[k]=water_cell.neutral.el_m;
    }
    for(const auto& site:station.station_diagi) {
        if(site.end!=live.input.end||site.cell>=n||encountered[site.cell]++||
           !std::isfinite(site.station_mixing.dptt_for_comp_k))
            throw std::invalid_argument("G63 native original SS MIXHTST source changed");
        mix.initial_dptt[site.cell]=site.station_mixing.dptt_for_comp_k;
    }
    const auto physical=p6e::mixht_observed_mc(mix);
    if(physical.zi.size()!=n||physical.ziconv.size()!=n||
       physical.dptt.size()!=n)
        throw std::logic_error("G63 genuine native mixed WATER+LAND MIXHT incomplete");
    for(const auto& w:water.water)
        if(physical.zi[w.source_index]!=w.mixing.zi_m||
           physical.ziconv[w.source_index]!=
               live.previous.ziconv_m[w.source_index])
            throw std::logic_error(
                "G63 MIXHT corrupted water ZI or inherited global ZICONV");
    // Original G14 frame remains untouched until all 17 physical stages
    // and a valid source-native P6F precommit succeed atomically.
    if(live.next.zi_m!=live.previous.zi_m||
       live.next.ziconv_m!=live.previous.ziconv_m||
       live.next.dptt_k!=live.previous.dptt_k)
        throw std::logic_error("G63 precommit stage12 mutated G14 memory");
    G63RealNoaaG14MixhtStage12 result;
    result.end=live.input.end;
    result.zi_before_avemix_m=std::move(physical.zi);
    result.ziconv_before_avemix_m=std::move(physical.ziconv);
    result.dptt_before_avemix_k=std::move(physical.dptt);
    result.comp_third_temperature_k=heat.temperature_k;
    result.comp_third_qh_wm2=elustr.qh_wm2;
    result.comp_third_density_kgm3=heat.density_kg_m3;
    result.comp_third_ustar_mps=elustr.ustar_mps;
    result.comp_third_el_m=elustr.el_m;
    // mix.ustar/el were copied from live COMP-third and updated ONLY at
    // source-identified WATER cells using G53 neutral physical arithmetic.
    // These are native P6F output fields, NOT imported G54/G57/G59 values.
    result.p6f_water_reconciled_ustar_mps=std::move(mix.ustar);
    result.p6f_water_reconciled_el_m=std::move(mix.el);
    if(result.p6f_water_reconciled_ustar_mps.size()!=n||
       result.p6f_water_reconciled_el_m.size()!=n)
        throw std::logic_error("G63 P6F WATER USTAR/EL invalid grid extents");
    for(std::size_t i=0;i<n;++i) {
        if(!encountered[i]) {
            if(result.p6f_water_reconciled_ustar_mps[i]!=
                   result.comp_third_ustar_mps[i]||
               result.p6f_water_reconciled_el_m[i]!=
                   result.comp_third_el_m[i])
                throw std::logic_error(
                    "G63 native P6F LAND USTAR/EL was unexpectedly modified");
        }
    }
    result.comp_third_shortwave_wm2=heat.shortwave_wm2;
    result.comp_third_sun_sine=heat.sun_sine;
    result.comp_third_nearest_surface=heat.nearest_surface;
    result.valid_ss=station.station_diagi.size();
    result.missing_ss=live.stations.surface.size()-result.valid_ss;
    result.water_cells=water.water.size();
    result.land_cells=n-result.water_cells;
    result.source_native_comp_mixht_uncommitted=true;
    return result;
}
} // namespace cteas::calmet::p6g
