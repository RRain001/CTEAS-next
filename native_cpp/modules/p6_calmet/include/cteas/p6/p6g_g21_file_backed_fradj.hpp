#pragma once
// G21: selected original CALMET DIAGNO WIND1 -> first SURFVAR(IAVET=1)
// -> source PREPDI CGAMMA/SETCOM GAMMA -> TERSET/FRADJ -> second SURFVAR.
// Every numeric input is from G19 original files and the SAME G14 hour.
// Reuse frozen #53 kernels; do not invent TEMP2D, GAMMA, CRITFN or TERRAD.
// This is TEST-ONLY partial stage physics: not a 17-stage or 45-field
// production CALMET, and not yet independent full-case Fortran parity.
#include "cteas/p6/p6g_g19_file_backed_case.hpp"
#include "cteas/p6/p6g_g41_real_water_first_hour_source.hpp"
#include "cteas/p6/p6g_g18b8_gamma_grid.hpp"
#include "cteas/p6/p6g_terrain_hour.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G21SelectedFradjFields {
    std::chrono::sys_seconds end{};
    float source_terrad_km=0.f,source_critfn=0.f;
    std::vector<float> gamma_k_per_m;
    std::vector<float> temperature_before_k,temperature_after_k;
    p6::WindUV corrected_wind;
    std::size_t corrected_uv_values=0;
};

// Caller MUST pass source PREPDI/CGAMMA from G18E4 on this live G14 hour,
// plus G20/G16's actual native WIND1. This function deliberately cannot
// return a NativeHourStageResult or publish any prior-hour G14 state.
inline G21SelectedFradjFields g21_original_source_clock_fradj_kernel(
    const MultiHourFrame& live,
    const G19SourceClockCase& source,
    const G17B4SurfaceControls& surface_controls,
    const G18B4CGammaPrepared& source_cgamma,
    const Wind1MultiField& source_wind1,
    bool explicitly_test_only,
    bool selected_water_reference_only) {
    const auto& grid=live.grid;
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    const auto n=nx*ny;
    if(!explicitly_test_only||!live.source_controls||
       live.input.end!=live.surface.end||
       live.surface.end-live.surface.start!=std::chrono::hours{1}||
       source_cgamma.end!=live.input.end||
       source_cgamma.hour_index!=live.hour_index||
       source_cgamma.lapse.size()!=live.stations.upper.size()||
       source_cgamma.station_ids.size()!=live.stations.upper.size()||
       source_wind1.nx!=grid.nx||source_wind1.ny!=grid.ny||
       source_wind1.nz!=9||source_wind1.u_mps.size()!=n*9||
       source_wind1.v_mps.size()!=n*9||
       grid.hemisphere!='N'||n<4||
       source.surface.station_ids.size()!=live.stations.surface.size()||
       source.surface.begin>live.surface.start||
       source.surface.end<live.surface.end||
       source.stations.surface.size()!=live.stations.surface.size()||
       source.stations.upper.size()!=live.stations.upper.size()||
       source.grid.nx!=grid.nx||source.grid.ny!=grid.ny||
       source.grid.terrain_m!=grid.terrain_m||
       source.grid.landuse!=grid.landuse)
        throw std::invalid_argument(
            "G21 requires same source-file G14 PREPDI/WIND1/GEO/UTC hour");
    for(std::size_t i=0;i<source_cgamma.station_ids.size();++i)
        if(source_cgamma.station_ids[i]!=live.stations.upper[i].id||
           source.stations.upper[i].id!=live.stations.upper[i].id)
            throw std::invalid_argument("G21 source CGAMMA upper station order mismatch");
    for(std::size_t i=0;i<live.stations.surface.size();++i)
        if(source.stations.surface[i].id!=live.stations.surface[i].id||
           source.surface.station_ids[i]!=live.stations.surface[i].id)
            throw std::invalid_argument("G21 source SURF station order mismatch");
    const float terrad=static_cast<float>(
        g19_read_real_control(source.original_metinp,"TERRAD"));
    const float critfn=static_cast<float>(
        g19_read_real_control(source.original_metinp,"CRITFN"));
    if(!std::isfinite(terrad)||terrad<0.f||
       !std::isfinite(critfn)||critfn<0.f)
        throw std::invalid_argument("G21 original TERRAD/CRITFN outside source scope");
    const auto selected_choice=g18b3_source_deck_upper_choice(
        grid,live.stations,source.original_metinp);
    if(selected_choice.iupt!=-1)
        throw std::invalid_argument("G21 unverified source IUPT fixed-station branch");
    const auto gamma=g18b8_source_gamma_from_hour(
        live,selected_choice,source_cgamma,true);
    // Mixed GEO is authorized only through the separately typed G41
    // reference case; ordinary G19 physics still takes the unchanged
    // all-land constructor and fails closed on any WATER cell.
    if(selected_water_reference_only)
        (void)g38_selected_noow_water_hflux_source_only(
            grid,source.original_metinp,true);
    G17B4TwoPassSurfvar two_pass(
        grid,live.stations,source.surface,live.surface,
        surface_controls,selected_water_reference_only);
    two_pass.after_wind1_before_fradj(
        live.input.end,source_wind1.u_mps,source_wind1.v_mps);
    if(!two_pass.first_stage_wind_matches(
            source_wind1.u_mps,source_wind1.v_mps)||
       !two_pass.matches_source_geometry(grid,live.stations))
        throw std::logic_error("G21 first IAVET SURFVAR not sourced from live WIND1");
    const auto static_terrain=prepare_g11_terrain(grid,terrad);
    const auto zface=std::vector<float>(
        live.source_controls->zface_m.begin(),
        live.source_controls->zface_m.end());
    const auto& pre_temp=two_pass.first_temperature();
    if(pre_temp.size()!=n||gamma.gamma_k_per_m.size()!=n)
        throw std::logic_error("G21 source TEMP2D/GAMMA wrong grid size");
    // With original ISURFT=-1, frozen FRADJ uses TEMP2D(i,j) and never
    // TINF; choose TEMP2D[0] only to satisfy the kernel's finite argument.
    // Do NOT use a synthetic constant as a surrogate for observed TEMP2D.
    auto corrected=p6::froude_adjust(
        grid.nx,grid.ny,9,grid.grid_km*1000.f,grid.grid_km*1000.f,
        static_terrain.terrain_m,static_terrain.hmax_m,
        gamma.gamma_k_per_m,pre_temp,-1,pre_temp.front(),critfn,
        zface,{source_wind1.u_mps,source_wind1.v_mps});
    two_pass.after_fradj_before_heatfx(
        live.input.end,corrected.u,corrected.v);
    if(!two_pass.second_stage_wind_matches(corrected.u,corrected.v)||
       !two_pass.second_ready())
        throw std::logic_error("G21 source second IAVET not from corrected FRADJ");
    G21SelectedFradjFields out;
    out.end=live.input.end;
    out.source_terrad_km=terrad;
    out.source_critfn=critfn;
    out.gamma_k_per_m=gamma.gamma_k_per_m;
    out.temperature_before_k=two_pass.first_temperature();
    out.temperature_after_k=two_pass.final_temperature();
    for(std::size_t i=0;i<corrected.u.size();++i) {
        if(!std::isfinite(corrected.u[i])||!std::isfinite(corrected.v[i]))
            throw std::invalid_argument("G21 source FRADJ produces nonfinite wind");
        out.corrected_uv_values+=
            (corrected.u[i]!=source_wind1.u_mps[i])+
            (corrected.v[i]!=source_wind1.v_mps[i]);
    }
    out.corrected_wind=std::move(corrected);
    return out;
}
    
// Existing all-land G19 downstream call signature preserved verbatim.
// Its G17B4 default water rejection remains in force.
inline G21SelectedFradjFields g21_selected_original_file_fradj(
    const MultiHourFrame& live,
    const G19FileBackedCase& source,
    const G18B4CGammaPrepared& source_cgamma,
    const Wind1MultiField& source_wind1,
    bool explicitly_test_only) {
    return g21_original_source_clock_fradj_kernel(
        live,source,source.surface_controls,source_cgamma,source_wind1,
        explicitly_test_only,false);
}

// New standalone first-hour real-WATER reference. Never accepts a weak
// G19 source directly: only the G41 immutable original water control type.
inline G21SelectedFradjFields g41_real_water_first_hour_native_fradj(
    const MultiHourFrame& live,
    const G41SelectedNoowWaterFirstHourSource& selected,
    const G18B4CGammaPrepared& source_cgamma,
    const Wind1MultiField& source_wind1,
    bool explicitly_test_only) {
    if(!explicitly_test_only||live.hour_index!=0||
       selected.first_hour_native_wind1_fradj_ready||
       selected.g24_native_final_wind_ready||
       selected.g14_g26_production_ready)
        throw std::invalid_argument(
            "G41 first-hour WATER reference cannot promote G14/G24");
    return g21_original_source_clock_fradj_kernel(
        live,selected.source,selected.surface_controls,
        source_cgamma,source_wind1,true,true);
}

} // namespace cteas::calmet::p6g
