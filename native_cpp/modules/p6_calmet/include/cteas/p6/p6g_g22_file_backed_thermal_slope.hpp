#pragma once
// G22 selected 2SS+2US original-file HEATFX/AIRDEN/ELUSTR/SLOPE.
// Uses the SAME live G14 frame, untouched original-source P6E/P6D kernels,
// actual post-FRADJ second IAVET TEMP2D and original BLOCK DATA HFLUX.
// No original multi-station full-hour or original-vendor 45-field acceptance.
#include "cteas/p6/p6g_g21_file_backed_fradj.hpp"
#include "cteas/p6/p6g_g17c2_elustr_handoff.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G22SelectedThermalSlope {
    std::chrono::sys_seconds end{};
    G17CSelectedHeatResult heat;
    G17C2SelectedElustrResult elustr;
    p6::WindUV post_slope_wind;
    std::size_t changed_slope_components=0;
};

// Shared source-selected original SLOPE arithmetic. The existing all-land
// G22 and the real WATER G47 diagnostic both call this exact kernel.
// Unlike production G14, a water opt-in here does not commit hour/state.
struct G22OriginalSlopeAfterElustr {
    p6::WindUV post_slope_wind;
    std::size_t changed_slope_components=0;
};
inline G22OriginalSlopeAfterElustr g22_original_slope_after_elustr(
    const GeoGrid& grid,const OriginalWindControls& source_controls,
    const std::string& original_metinp,const p6::WindUV& post_fradj_wind,
    const G17CSelectedHeatResult& heat,
    const G17C2SelectedElustrResult& elustr,
    bool explicit_water_reference_only=false) {
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    const auto n=nx*ny;
    if(nx<2||ny<2||nx>400||ny>400||
       grid.landuse.size()!=n||
       post_fradj_wind.u.size()!=9*n||post_fradj_wind.v.size()!=9*n||
       heat.temperature_k.size()!=n||
       elustr.qh_wm2.size()!=n||elustr.ustar_mps.size()!=n||
       elustr.el_m.size()!=n||heat.end!=elustr.end)
        throw std::invalid_argument("G22 original source SLOPE extent/provenance invalid");
    for(std::size_t i=0;i<n;++i) {
        if(grid.landuse[i]<grid.iwat1||grid.landuse[i]>grid.iwat2)continue;
        if(!explicit_water_reference_only||
           elustr.qh_wm2[i]!=0.f||elustr.ustar_mps[i]!=0.f||
           elustr.el_m[i]!=0.f)
            throw std::invalid_argument(
                "G22 WATER SLOPE must skip model-only friction prior to WATER");
    }
    // Source SLOPE uses the QH *after* stable ELUSTR, not the earlier
    // HEATFX-only flux, and the SECOND SURFVAR temperature.
    const auto slope_terrain=prepare_g11_terrain(
        grid,static_cast<float>(
            g19_read_real_control(original_metinp,"TERRAD")));
    p6::SlopeInput slope;
    slope.nx=grid.nx;slope.ny=grid.ny;slope.nz=9;
    slope.dx_m=slope_terrain.spacing_m;slope.dy_m=slope_terrain.spacing_m;
    slope.water_first=grid.iwat1;slope.water_last=grid.iwat2;
    slope.isurft=-1;
    slope.domain_temperature_k=heat.temperature_k.front();
    slope.zface_m.assign(source_controls.zface_m.begin(),
                         source_controls.zface_m.end());
    slope.terrain_m=slope_terrain.terrain_m;
    slope.hmax_m=slope_terrain.hmax_m;
    slope.hmin_m=slope_terrain.hmin_m;
    slope.disthmax_m=slope_terrain.dist_hmax_m;
    slope.disthmin_m=slope_terrain.dist_hmin_m;
    slope.sensible_heat_w_m2=elustr.qh_wm2;
    slope.surface_temperature_k=heat.temperature_k;
    slope.landuse=slope_terrain.landuse;
    const auto addition=p6::compute_original_slope_scoped(slope);
    G22OriginalSlopeAfterElustr result;
    result.post_slope_wind=post_fradj_wind;
    if(addition.u_mps.size()!=n*9||addition.v_mps.size()!=n*9)
        throw std::logic_error("G22 source SLOPE correction dimensions invalid");
    for(std::size_t i=0;i<n*9;++i) {
        const auto original_u=result.post_slope_wind.u[i];
        const auto original_v=result.post_slope_wind.v[i];
        result.post_slope_wind.u[i]+=addition.u_mps[i];
        result.post_slope_wind.v[i]+=addition.v_mps[i];
        if(!std::isfinite(result.post_slope_wind.u[i])||
           !std::isfinite(result.post_slope_wind.v[i]))
            throw std::invalid_argument("G22 source SLOPE nonfinite U/V");
        result.changed_slope_components+=
            (result.post_slope_wind.u[i]!=original_u)+
            (result.post_slope_wind.v[i]!=original_v);
    }
    return result;
}
// Fail closed if G21 geometry, original SURF/UP or the wind used for its
// two SURFVAR passes is not identical to the current G14 source hour.
// This adapter does NOT report any production NativeHourStageResult.
inline G22SelectedThermalSlope g22_selected_source_thermal_slope(
    const MultiHourFrame& live,
    const G19FileBackedCase& source,
    const p6::WindUV& original_wind1,
    const G21SelectedFradjFields& fradj,
    bool explicitly_test_only) {
    const auto& grid=live.grid;
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    const auto n=nx*ny;
    if(!explicitly_test_only||!live.source_controls||
       live.input.end!=live.surface.end||live.input.end!=fradj.end||
       source.surface.begin>live.surface.start||
       source.surface.end<live.surface.end||
       source.surface.station_ids.size()!=live.stations.surface.size()||
       source.stations.surface.size()!=live.stations.surface.size()||
       source.grid.nx!=grid.nx||source.grid.ny!=grid.ny||
       source.grid.landuse!=grid.landuse||
       source.grid.terrain_m!=grid.terrain_m||
       original_wind1.u.size()!=n*9||original_wind1.v.size()!=n*9||
       fradj.corrected_wind.u.size()!=n*9||
       fradj.corrected_wind.v.size()!=n*9||
       fradj.temperature_before_k.size()!=n||
       fradj.temperature_after_k.size()!=n)
        throw std::invalid_argument(
            "G22 thermal/SLOPE must consume same file-backed G14 FRADJ hour");
    for(std::size_t i=0;i<live.stations.surface.size();++i)
        if(source.stations.surface[i].id!=live.stations.surface[i].id||
           source.surface.station_ids[i]!=live.stations.surface[i].id)
            throw std::invalid_argument("G22 original SS station ordinal mismatch");

    // Reconstruct the two *existing* source SURFVAR stage adapters on the
    // same observed surface hour; reject any caller-supplied fake TEMP2D.
    G17B4TwoPassSurfvar surfvar(
        grid,live.stations,source.surface,live.surface,source.surface_controls);
    surfvar.after_wind1_before_fradj(
        live.input.end,original_wind1.u,original_wind1.v);
    surfvar.after_fradj_before_heatfx(
        live.input.end,fradj.corrected_wind.u,fradj.corrected_wind.v);
    if(!surfvar.first_stage_wind_matches(original_wind1.u,original_wind1.v)||
       !surfvar.second_stage_wind_matches(
            fradj.corrected_wind.u,fradj.corrected_wind.v)||
       surfvar.first_temperature()!=fradj.temperature_before_k||
       surfvar.final_temperature()!=fradj.temperature_after_k)
        throw std::invalid_argument(
            "G22 source twice-SURFVAR mismatch: cannot inject thermal fixture");

    const auto heat_inputs=g18d3_source_hflux_inputs(
        grid,source.original_metinp,true);
    const auto heat=selected_iavet1_heat_after_fradj(
        grid,live.stations,live.surface,surfvar,heat_inputs);
    const auto nears=source_setcom_nears(grid,live.stations);
    const auto density=source_airden_nears(
        nears,heat.temperature_k,live.surface);
    if(heat.nearest_surface!=nears||heat.density_kg_m3!=density)
        throw std::logic_error("G22 original SETCOM AIRDEN disagrees with HEATFX");
    // Original CALMET READCF sets IPSIFCN internally, *not* through a
    // met.inp IPSIFCN key. Literal unchanged vendor calmet.for:
    //   IF(ICOARE.EQ.0) THEN
    //     ISFCMET=1 ; IPSIFCN=1
    //   ELSE
    //     ISFCMET=0 ; IPSIFCN=0
    // Current G19/G22 SURFVAR scope is ISFCMET=0, so reject ICOARE=0
    // rather than silently running the other source physical path.
    const int icoare=g18c1_source_integer(source.original_metinp,"ICOARE");
    if(icoare<=0)
        throw std::invalid_argument(
            "G22 original ICOARE selects unverified ISFCMET/IPSIFCN path");
    G17C2SelectedElustrControls controls;
    controls.ipsifcn=0; // original READCF selection for ICOARE>0
    controls.zm_m=0.5f*(live.source_controls->zface_m[0]+
                         live.source_controls->zface_m[1]);
    controls.explicitly_test_only=true;
    const auto elustr=selected_iavet1_elustr_after_heatfx(
        grid,live.stations,live.surface,surfvar,heat,
        fradj.corrected_wind,controls);
    if(elustr.end!=live.input.end||elustr.qh_wm2.size()!=n)
        throw std::logic_error("G22 original ELUSTR result has wrong model hour");

    const auto slope=g22_original_slope_after_elustr(
        grid,*live.source_controls,source.original_metinp,
        fradj.corrected_wind,heat,elustr,false);
    G22SelectedThermalSlope result;
    result.end=live.input.end;
    result.heat=heat;
    result.elustr=elustr;
    result.post_slope_wind=slope.post_slope_wind;
    result.changed_slope_components=slope.changed_slope_components;
    return result;
}
} // namespace cteas::calmet::p6g
