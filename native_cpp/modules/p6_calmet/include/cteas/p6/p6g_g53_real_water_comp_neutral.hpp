#pragma once
// S4-R1c8d: actual source NOAA G24 final U/V -> neutral WATER (G37/G35/G36).
// Test-only original NOWSTA=0, ITWPROG=0, IMIXH=1 source path.
// This is one-hour WATER original arithmetic, NOT COMP MIXHT, AVEMIX,
// G14 committed memory, G26 45-field emission or production CALMET.
#include "cteas/p6/p6g_g52_real_water_comp_partition.hpp"
#include "cteas/p6/p6g_g37_water_original_fcori_wind_bridge.hpp"
#include "cteas/p6/p6g_g36_original_noow_water_zi.hpp"
#include "cteas/p6/p6g_g24_file_backed_wind_tail.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G53ActualWaterState {
    std::size_t source_index{};
    int original_landuse{};
    float ws10_mps{},fcori_s_inv{};
    G35SelectedWaterNeutralResult neutral;
    G36OriginalWaterZiResult mixing;
};
struct G53ActualWaterCompResult {
    std::chrono::sys_seconds end{};
    std::vector<G53ActualWaterState> water;
    bool genuine_firsthour_water_arithmetic_only=false;
    bool land_mixht_ready=false;
    bool original_causal_memory_ready=false;
    bool g26_45field_ready=false;
};
inline G53ActualWaterCompResult g53_real_source_g24_neutral_water_reference(
    const G41SelectedNoowWaterFirstHourSource& source,
    const MultiHourFrame& frame,
    const G24SourceWindTail& wind,
    bool explicitly_research_only,
    bool opt_in_hour3_comp_stage12_trial=false,
    bool opt_in_hour4_comp_stage12_trial=false,
    bool opt_in_hour5_comp_stage12_trial=false) {
    if(!explicitly_research_only||source.g14_g26_production_ready||
       source.water_heat_source.g14_g26_production_ready||
       wind.end!=frame.input.end)
        throw std::invalid_argument("G53 original real WATER physics requires source-only opt-in");
    const auto partition=g26b_real_water_comp_partition_source_only(
        source,frame,true,opt_in_hour3_comp_stage12_trial,
        opt_in_hour4_comp_stage12_trial,
        opt_in_hour5_comp_stage12_trial);
    if(partition.source_water_comp_physics_accepted||
       partition.g26_45fields_accepted||
       partition.original_causal_comp_history_accepted)
        throw std::logic_error("G53 G52 partition has false physics authority");
    const auto& geo=source.source.grid;
    const auto n=static_cast<std::size_t>(geo.nx)*
                 static_cast<std::size_t>(geo.ny);
    if(wind.wind.u_mps.size()!=9*n||wind.wind.v_mps.size()!=9*n||
       wind.wind.w_face_mps.size()!=10*n||
       partition.original_water_cell_ordinals.size()!=63||
       partition.original_land_cell_ordinals.size()!=n-63)
        throw std::invalid_argument("G53 actual G24 wind or source water GEO invalid");
    const auto& deck=source.source.original_metinp;
    // G37: independently derived original FCORI from READCF and WS10
    // from already validated final G24 layer-1 U/V, NEVER original wind.
    const float fcoriol=g18d5_source_scalar(deck,"FCORIOL");
    G37WaterWindSource real_wind;
    real_wind.nx=geo.nx;real_wind.ny=geo.ny;real_wind.nz=9;
    real_wind.landuse=geo.landuse;
    real_wind.iwat1=geo.iwat1;real_wind.iwat2=geo.iwat2;
    real_wind.final_diagno_u_mps=wind.wind.u_mps;
    real_wind.final_diagno_v_mps=wind.wind.v_mps;
    real_wind.original_fcoriol=fcoriol;
    real_wind.explicit_reference_only=true;
    const auto waterwind=g37_original_fcori_final_wind1_surface_source(real_wind);
    if(waterwind.water_cells!=partition.original_water_cell_ordinals.size()||
       waterwind.g14_g26_production_ready||
       waterwind.original_water_physics_ready)
        throw std::logic_error("G53 source G37 readiness invalid");
    const float constw=g18d5_source_scalar(deck,"CONSTW");
    const float ziminw=g18d5_source_scalar(deck,"ZIMINW");
    const float zimaxw=g18d5_source_scalar(deck,"ZIMAXW");
    G53ActualWaterCompResult out;
    out.end=frame.input.end;
    for(const auto i:partition.original_water_cell_ordinals) {
        G36OriginalWaterZiInputs selected;
        selected.original_neutral.nowsta=g18d5_source_integer(deck,"NOWSTA");
        selected.original_neutral.itwprog=g18d5_source_integer(deck,"ITWPROG");
        selected.original_neutral.icoare=g18d5_source_integer(deck,"ICOARE");
        selected.original_neutral.imixh=g18d5_source_integer(deck,"IMIXH");
        selected.original_neutral.water_first=geo.iwat1;
        selected.original_neutral.water_last=geo.iwat2;
        selected.original_neutral.original_land_category=geo.landuse[i];
        selected.original_neutral.source_ws10_mps=waterwind.ws10_mps[i];
        selected.original_neutral.explicit_reference_only=true;
        selected.original_fcori_s_inv=waterwind.fcori_s_inv[i];
        selected.original_constw=constw;
        selected.original_ziminw_m=ziminw;
        selected.original_zimaxw_m=zimaxw;
        selected.explicit_source_reference_only=true;
        const auto neutral=g35_selected_original_nowsta0_water_reference(
            selected.original_neutral);
        const auto mix=g36_selected_original_nowsta0_zi_source_reference(
            selected);
        if(neutral.g14_g26_physics_ready||mix.g14_g26_production_ready||
           mix.full_original_water_state_ready||
           !std::isfinite(mix.zi_m)||!std::isfinite(neutral.ustar_mps))
            throw std::logic_error("G53 partial source WATER falsely promoted");
        out.water.push_back({i,geo.landuse[i],waterwind.ws10_mps[i],
                             waterwind.fcori_s_inv[i],neutral,mix});
    }
    if(out.water.size()!=63)
        throw std::logic_error("G53 incomplete actual NOAA source-water cardinality");
    out.genuine_firsthour_water_arithmetic_only=true;
    return out;
}
} // namespace cteas::calmet::p6g
