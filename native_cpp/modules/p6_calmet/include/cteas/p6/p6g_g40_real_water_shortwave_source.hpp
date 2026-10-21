#pragma once
// S4-R1b. Real NOAA source-only independent WATER HEATFX shortwave.
// QSW for all cells uses unchanged frozen P6E solar and HEATFX kernels;
// only WATER cells are output. The native first/second post-FRADJ
// temperatures, land QH/ELUSTR and G24/G26 wind are NOT claimed.
#include "cteas/p6/p6g_g19_file_backed_case.hpp"
#include "cteas/p6/p6g_g38_selected_noow_water_hflux_source.hpp"
#include "cteas/p6/p6g_g17b_setcom_airden.hpp"
#include "cteas/p6e/surface_solar.hpp"
#include "cteas/p6e/surfvar_multistation.hpp"
#include "cteas/p6e/heatfx.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G40WaterRadiationRecord {
    int one_based_i=0,one_based_j=0,utc_hour_end=0;
    int category=0,nearest_station_ordinal=0,cloud_tenths=0;
    float solar_sine=0.f,qsw_wm2=0.f,qh_water_wm2=0.f;
    float observed_temperature_carrier_k=0.f;
};
struct G40SelectedOriginalWaterShortwave {
    std::vector<G40WaterRadiationRecord> rows;
    bool post_fradj_iavet_two_pass_accepted=false;
    bool land_thermal_elustr_accepted=false;
    bool native_g24_wind_accepted=false;
    bool native_g14_g26_production_accepted=false;
};
inline G40SelectedOriginalWaterShortwave
g40_real_source_water_shortwave(const G19SourceClockCase& source,
                               bool reference_only) {
    using namespace std::chrono;
    if(!reference_only)
        throw std::invalid_argument("G40 cannot assert water production");
    const auto& grid=source.grid;
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    const auto n=nx*ny;
    if(source.surface.hourly.empty()||
       source.stations.surface.size()!=source.surface.station_ids.size()||
       source.controls.noobs!=0)
        throw std::invalid_argument("G40 genuine observed source missing");
    // Original input deck configures ICLOUD; MCLOUD is an INTERNAL
    // vendor runtime flag, not a met.inp setting. The authentic B0
    // ICLOUD=0 branch uses original station cloud in HEATFX (MCLOUD<=1).
    if(g18c1_source_integer(source.original_metinp,"ICLOUD")!=0)
        throw std::invalid_argument(
            "G40 source shortwave only accepts original ICLOUD=0 station clouds");
    const auto gate=g38_selected_noow_water_hflux_source_only(
        grid,source.original_metinp,true);
    if(gate.original_water_cell_indices.empty())
        throw std::invalid_argument("G40 requires original actual water GEO");
    const auto nearest=source_setcom_nears(grid,source.stations);
    const auto solar=p6e::surface_solar_grid(nx,ny,grid.zone,
        grid.xorigin_km*1000.f,grid.yorigin_km*1000.f,
        grid.grid_km*1000.f);
    const auto original_surfvar=parse_g17b4_surface_controls(
        source.original_metinp);
    p6e::SurfvarMultistationInput spatial;
    spatial.nx=nx;spatial.ny=ny;spatial.dgrid_m=grid.grid_km*1000.f;
    spatial.irad=original_surfvar.source.irad;
    spatial.numts=original_surfvar.source.numts;
    spatial.trad_grid=original_surfvar.source.trad_km/grid.grid_km;
    G40SelectedOriginalWaterShortwave result;
    for(const auto& hour:source.surface.hourly) {
        if(hour.by_station.size()!=source.stations.surface.size()||
           hour.end-hour.start!=hours{1})
            throw std::invalid_argument("G40 source RDSN station clock mismatch");
        spatial.stations.clear();
        std::vector<int> clouds;
        for(std::size_t s=0;s<hour.by_station.size();++s) {
            const auto& obs=hour.by_station[s];
            const auto& loc=source.stations.surface[s];
            // The real NOAA 583140 sparse station may lack a temperature
            // hour. Original SURFVAR does NOT fabricate it: RDSN supplies
            // 9999 and SURFVAR skips this station when interpolating T.
            // The dense genuine 583210 station supplies the valid T field.
            // Cloud is independently mandatory for MCLOUD=1 HEATFX and
            // remains source-owned; never repair or synthesize it here.
            if(!obs.cloud_valid||
               (obs.temperature_valid&&(!std::isfinite(obs.temperature_k)||
                obs.temperature_k<180.f||obs.temperature_k>350.f))||
               obs.opaque_cloud_tenths<0||obs.opaque_cloud_tenths>10)
                throw std::invalid_argument(
                    "G40 missing original station cloud or invalid VALID observed T");
            clouds.push_back(obs.opaque_cloud_tenths);
            spatial.stations.push_back({loc.local_x_m,loc.local_y_m,
                obs.temperature_valid?obs.temperature_k:9999.f,
                obs.humidity_valid?obs.humidity_pct:9999});
        }
        // Real measured SURFVAR interpolation provides a valid temperature
        // carrier for frozen HEATFX. QSW algebra never depends on temperature.
        // This carrier is NOT the post-FRADJ second IAVET temperature, so
        // no LAND QH is returned or treated as physics-accepted.
        const auto raw=p6e::surfvar_multistation(spatial);
        const auto start_day=floor<days>(hour.start);
        const auto year_start=sys_days{year_month_day{start_day}.year()/January/1};
        const int julian=static_cast<int>((start_day-year_start).count())+1;
        const int utc_begin=static_cast<int>(
            duration_cast<hours>(hour.start-start_day).count());
        const auto end_day=floor<days>(hour.end);
        const int utc_end=static_cast<int>(
            duration_cast<hours>(hour.end-end_day).count());
        auto sun=p6e::sinalpc_grid(solar,julian,utc_begin,0);
        p6e::HeatFluxInput input;
        input.nx=nx;input.ny=ny;input.mcloud=1;
        input.water_first=grid.iwat1;input.water_last=grid.iwat2;
        const auto& coef=gate.reference_heat.coefficients;
        input.ha1=coef.ha1;input.ha2=coef.ha2;
        input.hb1=coef.hb1;input.hb2=coef.hb2;
        input.hc1=coef.hc1;input.hc2=coef.hc2;input.hc3p1=coef.hc3p1;
        input.station_cloud=std::move(clouds);
        input.nearest=nearest;input.landuse=grid.landuse;
        input.sun=std::move(sun);input.temp_k=raw.temp2d_k;
        input.cloud_grid.assign(n,0.f);
        input.albedo=grid.albedo;input.bowen=grid.bowen;
        input.soil_heat_fraction=grid.hcg;
        input.anthropogenic_wm2=grid.qf;
        input.initial_qh=gate.reference_heat.initial_water_qh_wm2;
        const auto heat=p6e::heatfx(input);
        for(const auto k:gate.original_water_cell_indices) {
            const int s=nearest[k];
            if(s<1||static_cast<std::size_t>(s)>input.station_cloud.size()||
               heat.sensible_wm2[k]!=0.f||!std::isfinite(heat.shortwave_wm2[k]))
                throw std::logic_error("G40 WATER shortwave source invalid");
            result.rows.push_back({
                static_cast<int>(k%nx+1),static_cast<int>(k/nx+1),
                utc_end,grid.landuse[k],s,
                input.station_cloud[static_cast<std::size_t>(s-1)],
                input.sun[k],heat.shortwave_wm2[k],
                heat.sensible_wm2[k],input.temp_k[k]});
        }
    }
    if(result.rows.size()!=gate.original_water_cell_indices.size()*
                           source.surface.hourly.size())
        throw std::logic_error("G40 missing original WATER record count");
    return result;
}
} // namespace cteas::calmet::p6g
