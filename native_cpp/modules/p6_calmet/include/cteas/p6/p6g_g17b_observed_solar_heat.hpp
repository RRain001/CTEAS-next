#pragma once
// G17B1: file-observed SURFVAR + computed source SOLAR + source HEATFX.
// These P6E kernels are immutable #53 originals. Radiation is NEVER a
// synthetic array: it is derived from WGS84 UTM and the actual SURF UTC hour.
// HEATFX ancillary nearest-site, source coefficients, water QH and lapse
// remain explicit fixture inputs, NOT proven multi-station source authority.
// Therefore results remain fixture-scoped; they cannot complete G14 hourly
// P6E/COMP or promote P6G to production without separate real-case parity.
#include "cteas/p6/p6g_g17_staged_terrain.hpp"
#include "cteas/p6/p6g_observed_thermal_hour.hpp"
#include "cteas/p6/p6g_g17b_setcom_airden.hpp"
#include "cteas/p6/p6g_original_surfvar_controls.hpp"
#include "cteas/p6e/surface_solar.hpp"
#include "cteas/p6e/surfvar_multistation.hpp"
#include "cteas/p6e/heatfx.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <vector>
#include <utility>

namespace cteas::calmet::p6g {
struct G17BExplicitAncillaryFixture {
    // Site-specific control that has NOT yet been tied to original READCF
    // across arbitrary multistation cases. No magic default is permitted.
    int irad=0,numts=0;
    float trad_grid=0.f;
    // Optional authentic original met.inp control binding. If supplied,
    // reject IAVET=1 (not implemented), and exact IRAD/NUMTS/TRAD mismatch.
    // Absence remains legal ONLY in fixture-marked selected tests.
    std::optional<OriginalSurfvarControls> original_surfvar_controls;
    G12HeatCoefficients coefficients{};
    int isurft=-1;
    float domain_temperature_k=0.f,critfn=0.f;
    // Optional comparison oracle ONLY; never used as physical NEARS.
    // Original SETCOM computes nearest stations from original GEO/SS.
    std::vector<int> nearest_surface;
    std::vector<float> initial_water_qh_wm2,lapse_k_per_m;
    bool explicitly_test_only=false;      // must never be used for production
};
struct G17BObservedSolarResult {
    std::chrono::sys_seconds end{};
    p6e::SurfvarMultistationResult observed;
    std::vector<float> sun_sine,shortwave_wm2,sensible_heat_wm2;
    std::vector<int> nearest_surface;
    std::vector<float> density_kg_m3;
    G17FradjSource fradj_fixture;
    G17SlopeHeatSource slope_fixture;
};

inline G17BObservedSolarResult observed_solar_heat_selected(
    const GeoGrid& grid,const StationSet& stations,
    const SurfaceSeries& series,const SurfaceHour& hour,
    const G17BExplicitAncillaryFixture& fixture) {
    using namespace std::chrono;
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    if(grid.nx<2||grid.ny<2||grid.nx>400||grid.ny>400||
       !std::isfinite(grid.grid_km)||grid.grid_km<=0.f||
       !std::isfinite(grid.xorigin_km)||!std::isfinite(grid.yorigin_km)||
       grid.hemisphere!='N'||grid.zone<1||grid.zone>60||
       stations.surface.size()<2||stations.surface.size()>6||
       series.station_ids.size()!=stations.surface.size()||
       hour.by_station.size()!=stations.surface.size()||
       hour.start<series.begin||hour.end>series.end||
       hour.end-hour.start!=hours{1}||
       !fixture.explicitly_test_only||
       fixture.isurft!=-1||fixture.irad<1||fixture.irad>2||
       fixture.numts<1||!std::isfinite(fixture.trad_grid)||
       fixture.trad_grid<0.f||
       !std::isfinite(fixture.domain_temperature_k)||
       fixture.domain_temperature_k<=0.f||
       !std::isfinite(fixture.critfn)||fixture.critfn<0.f)
        throw std::invalid_argument("G17B original-format SURF/SOLAR scope invalid");
    if(fixture.original_surfvar_controls)
        require_selected_iavet0(*fixture.original_surfvar_controls,
                                grid.grid_km,fixture.irad,
                                fixture.numts,fixture.trad_grid);
    const auto count=nx*ny;
    if(grid.landuse.size()!=count||grid.albedo.size()!=count||
       grid.bowen.size()!=count||grid.hcg.size()!=count||
       grid.qf.size()!=count||
       (!fixture.nearest_surface.empty()&&
        fixture.nearest_surface.size()!=count)||
       fixture.initial_water_qh_wm2.size()!=count||
       fixture.lapse_k_per_m.size()!=count||
       grid.iwat1>grid.iwat2)
        throw std::invalid_argument("G17B source GEO / ancillary field mismatch");
    for(std::size_t s=0;s<stations.surface.size();++s) {
        if(series.station_ids[s]!=stations.surface[s].id)
            throw std::invalid_argument("G17B shuffled SURF station identity");
        if(!hour.by_station[s].cloud_valid)
            throw std::invalid_argument("G17B missing original RDSN cloud cover");
    }
    p6e::SurfvarMultistationInput surface;
    surface.nx=nx;surface.ny=ny;
    surface.dgrid_m=grid.grid_km*1000.f;
    surface.irad=fixture.irad;surface.numts=fixture.numts;
    surface.trad_grid=fixture.trad_grid;
    std::vector<int> clouds;
    for(std::size_t i=0;i<stations.surface.size();++i) {
        const auto& obs=hour.by_station[i];
        const auto& s=stations.surface[i];
        surface.stations.push_back({s.local_x_m,s.local_y_m,
            obs.temperature_valid?obs.temperature_k:9999.f,
            obs.humidity_valid?obs.humidity_pct:9999});
        clouds.push_back(obs.opaque_cloud_tenths);
    }
    const auto field=p6e::surfvar_multistation(surface);
    // CALMET SETCOM initializes NEARS before RDSN/COMP. It is always
    // derived with source REAL*4 cell centres and met.inp station order,
    // never copied from the synthetic G12/G8 nearest-station fixtures.
    const auto nearest=source_setcom_nears(grid,stations);
    if(!fixture.nearest_surface.empty()&&
       fixture.nearest_surface!=nearest)
        throw std::invalid_argument("G17B fixture NEARS differs from source SETCOM");
    // AIRDEN L2096-2097: measured PRES at source NEARS, observed TEMP2D.
    const auto density=source_airden_nears(nearest,field.temp2d_k,hour);
    // Original COMP interval starts at the SURF.DAT hour-start.
    // No system clock or local-time conversion enters this computation.
    const auto date=floor<days>(hour.start);
    const auto yearstart=sys_days{year_month_day{date}.year()/January/1};
    const int julian=static_cast<int>((date-yearstart).count())+1;
    const int begin_hour=static_cast<int>(
        duration_cast<hours>(hour.start-date).count());
    const auto coordinate=p6e::surface_solar_grid(
        nx,ny,grid.zone,grid.xorigin_km*1000.f,
        grid.yorigin_km*1000.f,grid.grid_km*1000.f);
    // SURF parser is scoped strictly to UTC+0000, hence source IBTZ=0.
    const auto sun=p6e::sinalpc_grid(coordinate,julian,begin_hour,0);
    p6e::HeatFluxInput heat;
    heat.nx=nx;heat.ny=ny;
    heat.mcloud=1;heat.water_first=grid.iwat1;heat.water_last=grid.iwat2;
    heat.ha1=fixture.coefficients.ha1;
    heat.ha2=fixture.coefficients.ha2;
    heat.hb1=fixture.coefficients.hb1;
    heat.hb2=fixture.coefficients.hb2;
    heat.hc1=fixture.coefficients.hc1;
    heat.hc2=fixture.coefficients.hc2;
    heat.hc3p1=fixture.coefficients.hc3p1;
    heat.station_cloud=std::move(clouds);
    heat.nearest=nearest;
    heat.landuse=grid.landuse;
    heat.sun=sun;
    heat.temp_k=field.temp2d_k;
    // For MCLOUD=1, original HEATFX uses station-cloud NEARS; grid cloud
    // workspace is unreferenced, but still allocated for the native kernel.
    heat.cloud_grid.assign(count,0.f);
    heat.albedo=grid.albedo;heat.bowen=grid.bowen;
    heat.soil_heat_fraction=grid.hcg;
    heat.anthropogenic_wm2=grid.qf;
    heat.initial_qh=fixture.initial_water_qh_wm2;
    const auto flux=p6e::heatfx(heat);
    G17BObservedSolarResult result;
    result.end=hour.end;
    result.observed=field;
    result.sun_sine=sun;
    result.shortwave_wm2=flux.shortwave_wm2;
    result.sensible_heat_wm2=flux.sensible_wm2;
    result.nearest_surface=nearest;
    result.density_kg_m3=density;
    result.fradj_fixture.end=hour.end;
    result.fradj_fixture.provenance=TerrainHourProvenance::SyntheticReferenceFixture;
    result.fradj_fixture.isurft=fixture.isurft;
    result.fradj_fixture.domain_temperature_k=fixture.domain_temperature_k;
    result.fradj_fixture.critfn=fixture.critfn;
    result.fradj_fixture.lapse_k_per_m=fixture.lapse_k_per_m;
    result.fradj_fixture.temperature_k=field.temp2d_k;
    result.slope_fixture.end=hour.end;
    result.slope_fixture.provenance=TerrainHourProvenance::SyntheticReferenceFixture;
    result.slope_fixture.temperature_k=field.temp2d_k;
    result.slope_fixture.sensible_heat_w_m2=flux.sensible_wm2;
    return result;
}
} // namespace cteas::calmet::p6g
