#pragma once
// G17C1: source-ordered IAVET=1 second SURFVAR -> SOLAR/HEATFX/AIRDEN.
// Reuse the immutable PR #53 P6E kernels; do NOT duplicate their formulas.
// The external heat coefficients and water QH are explicitly TEST-only.
// This selected adapter is NOT a complete multi-station hourly P6E/COMP stage.
#include "cteas/p6/p6g_g17_staged_terrain.hpp"
#include "cteas/p6/p6g_observed_thermal_hour.hpp"
#include "cteas/p6e/surface_solar.hpp"
#include "cteas/p6e/heatfx.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G17CSelectedHeatInputs {
    G12HeatCoefficients coefficients{};
    std::vector<float> initial_water_qh_wm2;
    bool explicitly_test_only=false;
};
struct G17CSelectedHeatResult {
    std::chrono::sys_seconds end{};
    std::vector<float> temperature_k;
    std::vector<float> sun_sine,shortwave_wm2,sensible_heat_wm2;
    std::vector<float> density_kg_m3;
    std::vector<int> nearest_surface;

    // The result can feed the existing G17 scoped terrain adapter, but it
    // must NEVER be promoted to a complete native HEATFX/COMP stage.
    [[nodiscard]] G17SlopeHeatSource selected_slope_fixture() const {
        return {end,TerrainHourProvenance::SyntheticReferenceFixture,
                sensible_heat_wm2,temperature_k};
    }
};
inline G17CSelectedHeatResult selected_iavet1_heat_after_fradj(
    const GeoGrid& grid,const StationSet& stations,const SurfaceHour& hour,
    const G17B4TwoPassSurfvar& source,
    const G17CSelectedHeatInputs& fixture,
    bool original_comp_third_pass=false) {
    using namespace std::chrono;
    if(!fixture.explicitly_test_only||
       !source.first_ready()||!source.second_ready()||
       source.end()!=hour.end||
       (original_comp_third_pass&&!source.comp_ready())||
       !source.matches_source_geometry(grid,stations)||
       hour.end-hour.start!=hours{1}||
       grid.nx<2||grid.ny<2||grid.nx>400||grid.ny>400||
       !std::isfinite(grid.grid_km)||grid.grid_km<=0.f||
       !std::isfinite(grid.xorigin_km)||!std::isfinite(grid.yorigin_km)||
       grid.hemisphere!='N'||grid.zone<1||grid.zone>60||
       // Original source-selected one-SS all-land HEATFX is well-defined:
       // G17B4 now accepts one *observed* station and SETCOM/AIRDEN use
       // actual source-order indices; still forbid zero SS and >6.
       stations.surface.empty()||stations.surface.size()>6||
       hour.by_station.size()!=stations.surface.size())
        throw std::invalid_argument("G17C source-hour/IAVET=1 selected heat scope");
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    const auto n=nx*ny;
    const auto& final_temperature=original_comp_third_pass?
        source.comp_temperature():source.final_temperature();
    if(final_temperature.size()!=n||
       grid.landuse.size()!=n||grid.albedo.size()!=n||
       grid.bowen.size()!=n||grid.hcg.size()!=n||
       grid.qf.size()!=n||fixture.initial_water_qh_wm2.size()!=n)
        throw std::invalid_argument("G17C source GEO/HEATFX field mismatch");
    for(int land:grid.landuse)
        if(land>=grid.iwat1&&land<=grid.iwat2)
            throw std::invalid_argument("G17C water IAVET=1 branch not accepted");
    std::vector<int> clouds;
    clouds.reserve(stations.surface.size());
    for(const auto& obs:hour.by_station) {
        if(!obs.cloud_valid||obs.opaque_cloud_tenths<0||
           obs.opaque_cloud_tenths>10)
            throw std::invalid_argument("G17C missing original observed station cloud");
        clouds.push_back(obs.opaque_cloud_tenths);
    }
    // CALMET SETCOM NEARS: source-coordinate order, never a fixture map.
    const auto nearest=source_setcom_nears(grid,stations);
    const auto density=source_airden_nears(nearest,final_temperature,hour);

    // Reuse the verified source SOLAR mid-interval calculation, UTC+0000.
    const auto date=floor<days>(hour.start);
    const auto yearstart=sys_days{year_month_day{date}.year()/January/1};
    const int julian=static_cast<int>((date-yearstart).count())+1;
    const int begin_hour=static_cast<int>(
        duration_cast<hours>(hour.start-date).count());
    const auto coordinates=p6e::surface_solar_grid(
        nx,ny,grid.zone,grid.xorigin_km*1000.f,
        grid.yorigin_km*1000.f,grid.grid_km*1000.f);
    const auto sun=p6e::sinalpc_grid(coordinates,julian,begin_hour,0);

    p6e::HeatFluxInput heat;
    heat.nx=nx;heat.ny=ny;heat.mcloud=1;
    heat.water_first=grid.iwat1;heat.water_last=grid.iwat2;
    const auto& c=fixture.coefficients;
    heat.ha1=c.ha1;heat.ha2=c.ha2;heat.hb1=c.hb1;heat.hb2=c.hb2;
    heat.hc1=c.hc1;heat.hc2=c.hc2;heat.hc3p1=c.hc3p1;
    heat.station_cloud=std::move(clouds);
    heat.nearest=nearest;heat.landuse=grid.landuse;heat.sun=sun;
    heat.temp_k=final_temperature; // second, POST-FRADJ SURFVAR exclusively
    heat.cloud_grid.assign(n,0.f); // unused for original MCLOUD=1
    heat.albedo=grid.albedo;heat.bowen=grid.bowen;
    heat.soil_heat_fraction=grid.hcg;
    heat.anthropogenic_wm2=grid.qf;
    heat.initial_qh=fixture.initial_water_qh_wm2;
    const auto flux=p6e::heatfx(heat);
    return {hour.end,final_temperature,sun,flux.shortwave_wm2,
            flux.sensible_wm2,density,nearest};
}
} // namespace cteas::calmet::p6g
