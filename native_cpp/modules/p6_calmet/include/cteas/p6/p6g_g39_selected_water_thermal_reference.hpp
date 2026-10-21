#pragma once
// S4-R1a: a separately opt-in, source-gated HEATFX/ELUSTR *intermediate*
// for original no-overwater-observation WATER. No G22/G26 production bridge.
// Reuses the EXISTING original-validated P6E SURFVAR, HEATFX, stable/day ELUSTR
// physical kernels. ELUSTR skips water; WATER must later compute water
// USTAR, EL, WT/QH and ZI from the final DIAGNO wind.
#include "cteas/p6/p6g_g38_selected_noow_water_hflux_source.hpp"
#include "cteas/p6/p6g_g17c2_elustr_handoff.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6g {
struct G39SelectedWaterHeatAfterFradj {
    G17CSelectedHeatResult heat;
    G17C2SelectedElustrResult elustr;
    std::size_t selected_original_water_cells=0;
    bool water_ustar_el_zi_ready=false;
    bool g22_g24_wind_ready=false;
    bool g14_g26_production_ready=false;
};
inline G39SelectedWaterHeatAfterFradj
g39_original_noow_water_postfradj_thermal_reference(
    const GeoGrid& grid,const StationSet& stations,const SurfaceHour& hour,
    const G17B4TwoPassSurfvar& twice,
    const p6::WindUV& actual_post_fradj_wind,
    const std::string& actual_original_metinp,float original_zm_m,
    bool explicit_source_reference_only) {
    if(!explicit_source_reference_only)
        throw std::invalid_argument("G39 cannot run implied water production");
    const auto original=g38_selected_noow_water_hflux_source_only(
        grid,actual_original_metinp,true);
    if(!twice.first_ready()||!twice.second_ready()||
       !twice.matches_source_geometry(grid,stations)||
       !twice.second_stage_wind_matches(
           actual_post_fradj_wind.u,actual_post_fradj_wind.v)||
       twice.end()!=hour.end||
       !std::isfinite(original_zm_m)||original_zm_m<=0.f)
        throw std::invalid_argument(
            "G39 requires same original SURFVAR 2-pass post-FRADJ wind and source hour");
    auto heat=selected_iavet1_heat_after_fradj(
        grid,stations,hour,twice,original.reference_heat,false,true);
    // Original READCF ICOARE=10 -> ISFCMET=0 / IPSIFCN=0
    // (pinned CALMET SETCOM path), not inferred from water surface physics.
    G17C2SelectedElustrControls elustr_control;
    elustr_control.ipsifcn=0;
    elustr_control.zm_m=original_zm_m;
    elustr_control.explicitly_test_only=true;
    auto elustr=selected_iavet1_elustr_after_heatfx(
        grid,stations,hour,twice,heat,actual_post_fradj_wind,
        elustr_control,false,true);
    if(!elustr.water_state_pending_original_WATER||
       elustr.end!=hour.end||
       elustr.qh_wm2.size()!=grid.landuse.size()||
       heat.sensible_heat_wm2.size()!=grid.landuse.size())
        throw std::logic_error("G39 original WATER stage remains uncomputed");
    for(const auto cell:original.original_water_cell_indices) {
        if(heat.sensible_heat_wm2[cell]!=0.f||
           elustr.qh_wm2[cell]!=0.f||
           elustr.ustar_mps[cell]!=0.f||
           elustr.el_m[cell]!=0.f)
            throw std::logic_error(
                "G39 ELUSTR must not synthesize water USTAR/EL before WATER");
    }
    G39SelectedWaterHeatAfterFradj out;
    out.heat=std::move(heat);
    out.elustr=std::move(elustr);
    out.selected_original_water_cells=original.original_water_cell_indices.size();
    return out;
}
} // namespace cteas::calmet::p6g
