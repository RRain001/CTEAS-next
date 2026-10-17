#pragma once
// G17C2 selected DIAGNO ELUSTR: reuse PR #53 original-Fortran-audited
// stable and daytime P6E kernels. NO ELUSTR physical formula is duplicated.
// This adapter requires G17C1 test-only heat inputs and is NOT production
// native MultiHourPhysics; no cross-hour DIAGI/COMP or P6F is implied.
#include "cteas/p6/p6g_g17c_iavet1_heat_handoff.hpp"
#include "cteas/p6e/elustr_stable.hpp"
#include "cteas/p6e/elustr_daytime.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G17C2SelectedElustrControls {
    // Original CALMET PSIU choice, caller must read from original met.inp.
    int ipsifcn=0;
    float zm_m=0.f; // source 0.5*(ZFACE(1)+ZFACE(2))
    bool explicitly_test_only=false;
};
struct G17C2SelectedElustrResult {
    std::chrono::sys_seconds end{};
    std::vector<float> qh_wm2,ustar_mps,el_m;
    std::size_t stable_cells=0,daytime_cells=0;
    [[nodiscard]] G17SlopeHeatSource selected_slope_fixture(
        const G17CSelectedHeatResult& heat) const {
        if(end!=heat.end||qh_wm2.size()!=heat.temperature_k.size())
            throw std::invalid_argument("G17C2 SLOPE heat/temperature mismatch");
        // Original source calls ELUSTR before SLOPE; stable ELUSTR may
        // replace HEATFX's QH. Never forward the stale pre-ELUSTR QH.
        return {end,TerrainHourProvenance::SyntheticReferenceFixture,
                qh_wm2,heat.temperature_k};
    }
    // Deliberately no NativeHourStageResult: these values are fixture-scoped.
};
inline G17C2SelectedElustrResult selected_iavet1_elustr_after_heatfx(
    const GeoGrid& grid,const StationSet& stations,const SurfaceHour& hour,
    const G17B4TwoPassSurfvar& source,
    const G17CSelectedHeatResult& heat,
    const p6::WindUV& genuine_post_fradj_wind,
    const G17C2SelectedElustrControls& controls,
    bool original_comp_third_pass=false) {
    if(!controls.explicitly_test_only||
       controls.ipsifcn<0||controls.ipsifcn>1||
       !std::isfinite(controls.zm_m)||controls.zm_m<=0.f||
       source.end()!=hour.end||heat.end!=hour.end||
       !source.first_ready()||!source.second_ready()||
       (original_comp_third_pass&&!source.comp_ready())||
       !source.matches_source_geometry(grid,stations)||
       !(original_comp_third_pass?
           source.comp_stage_wind_matches(
               genuine_post_fradj_wind.u,genuine_post_fradj_wind.v):
           source.second_stage_wind_matches(
               genuine_post_fradj_wind.u,genuine_post_fradj_wind.v))||
       heat.temperature_k!=(original_comp_third_pass?
           source.comp_temperature():source.final_temperature()))
        throw std::invalid_argument("G17C2 selected ELUSTR source stages not joined");
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    const auto n=nx*ny;
    if(grid.nx<2||grid.ny<2||grid.nx>400||grid.ny>400||
       grid.landuse.size()!=n||grid.z0_m.size()!=n||
       heat.sensible_heat_wm2.size()!=n||heat.density_kg_m3.size()!=n||
       heat.nearest_surface.size()!=n||
       genuine_post_fradj_wind.u.size()!=n*9||
       genuine_post_fradj_wind.v.size()!=n*9||
       hour.by_station.size()!=stations.surface.size())
        throw std::invalid_argument("G17C2 ELUSTR missing source grid field");
    std::vector<int> clouds;
    clouds.reserve(stations.surface.size());
    for(const auto& obs:hour.by_station) {
        if(!obs.cloud_valid||obs.opaque_cloud_tenths<0||
           obs.opaque_cloud_tenths>10)
            throw std::invalid_argument("G17C2 missing source station cloud");
        clouds.push_back(obs.opaque_cloud_tenths);
    }
    // A source-selected HEATFX/AIRDEN result must agree with source SETCOM
    // for the same geometry and source station order.
    if(heat.nearest_surface!=source_setcom_nears(grid,stations)||
       heat.density_kg_m3!=source_airden_nears(
           heat.nearest_surface,heat.temperature_k,hour))
        throw std::invalid_argument("G17C2 AIRDEN/NEARS mismatched source hour");

    // Use original PR #53 branch-specific numerical kernels untouched:
    // mask the inactive branch as water (original kernels skip water),
    // then merge only the active cells into a single source-state field.
    std::vector<int> stable_mask=grid.landuse;
    std::vector<int> daytime_mask=grid.landuse;
    G17C2SelectedElustrResult out;
    out.end=hour.end;
    out.qh_wm2=heat.sensible_heat_wm2;
    out.ustar_mps.assign(n,0.f);
    out.el_m.assign(n,0.f);
    for(std::size_t k=0;k<n;++k) {
        if(grid.landuse[k]>=grid.iwat1&&grid.landuse[k]<=grid.iwat2)
            throw std::invalid_argument("G17C2 water ELUSTR not source-accepted");
        if(!std::isfinite(grid.z0_m[k])||grid.z0_m[k]<=0.f||
           grid.z0_m[k]>=controls.zm_m||
           !std::isfinite(out.qh_wm2[k])||
           !std::isfinite(genuine_post_fradj_wind.u[k])||
           !std::isfinite(genuine_post_fradj_wind.v[k]))
            throw std::invalid_argument("G17C2 invalid roughness, QH or source wind");
        if(out.qh_wm2[k]<0.f) {
            daytime_mask[k]=grid.iwat1;
            ++out.stable_cells;
        } else {
            stable_mask[k]=grid.iwat1;
            ++out.daytime_cells;
        }
    }
    p6e::StableElustr stable;
    stable.nx=nx;stable.ny=ny;stable.mcloud=1;
    stable.water_first=grid.iwat1;stable.water_last=grid.iwat2;
    stable.zm=controls.zm_m;stable.landuse=std::move(stable_mask);
    stable.nearest=heat.nearest_surface;
    stable.station_cloud=clouds;
    stable.z0=grid.z0_m;
    stable.u1.assign(genuine_post_fradj_wind.u.begin(),
                     genuine_post_fradj_wind.u.begin()+static_cast<std::ptrdiff_t>(n));
    stable.v1.assign(genuine_post_fradj_wind.v.begin(),
                     genuine_post_fradj_wind.v.begin()+static_cast<std::ptrdiff_t>(n));
    stable.rho=heat.density_kg_m3;
    stable.temp_k=heat.temperature_k;
    stable.cloud_grid.assign(n,0.f);
    stable.heat_flux_initial=heat.sensible_heat_wm2;
    const auto stable_out=p6e::stable_elustr(stable);

    p6e::DaytimeElustrInput day;
    day.nx=nx;day.ny=ny;day.water_first=grid.iwat1;day.water_last=grid.iwat2;
    day.ipsifcn=controls.ipsifcn;day.zm=controls.zm_m;
    day.landuse=std::move(daytime_mask);
    day.z0=grid.z0_m;day.u1=stable.u1;day.v1=stable.v1;
    day.rho=heat.density_kg_m3;day.temp_k=heat.temperature_k;
    day.heat_flux_initial=heat.sensible_heat_wm2;
    day.initial_ustar.assign(n,0.05f);
    day.initial_el.assign(n,-9.9e9f);
    const auto day_out=p6e::elustr_daytime(day);
    for(std::size_t k=0;k<n;++k) {
        if(heat.sensible_heat_wm2[k]<0.f) {
            out.qh_wm2[k]=stable_out.qh_wm2[k];
            out.ustar_mps[k]=stable_out.ustar_ms[k];
            out.el_m[k]=stable_out.monin_obukhov_m[k];
        } else {
            out.qh_wm2[k]=day_out.qh_wm2[k];
            out.ustar_mps[k]=day_out.ustar_ms[k];
            out.el_m[k]=day_out.monin_obukhov_m[k];
        }
        if(!std::isfinite(out.qh_wm2[k])||
           !std::isfinite(out.ustar_mps[k])||out.ustar_mps[k]<0.05f||
           !std::isfinite(out.el_m[k]))
            throw std::invalid_argument("G17C2 native P6E ELUSTR nonfinite output");
    }
    return out;
}
} // namespace cteas::calmet::p6g
