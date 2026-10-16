#pragma once
// P6G G12: dynamic 10km multi-site SURFVAR→HEATFX selected-source bridge.
//
// TEMP2D uses original-format SURF.DAT observed per-site temperatures via
// source-selected P6E SURFVAR, not a fabricated gridded temperature field.
// QH uses source-selected P6E HEATFX with ALL radiation, cloud, nearest site,
// and coefficients explicitly provided by caller. The G12 test fixture
// supplies synthetic radiation/coefficients and a separate GAMMA grid.
// This IS NOT verified full P6E model forcing or a production thermal state.
// No silent default sun, cloud, GAMMA or sensible heat.
#include "cteas/p6/p6g_terrain_hour.hpp"
#include "cteas/p6/observation_input_contract.hpp"
#include "cteas/p6e/surfvar_multistation.hpp"
#include "cteas/p6e/heatfx.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G12HeatCoefficients {
    float ha1=0.f,ha2=0.f,hb1=0.f,hb2=0.f,hc1=0.f,hc2=0.f,hc3p1=0.f;
};
struct G12ExplicitSolarHeat {
    std::chrono::sys_seconds end{};
    // No production acceptance: supplied synthetic irradiance / original
    // parameter inputs are an independent, required audit control.
    bool synthetic_radiation_fixture=false;
    int irad=1,numts=2;
    float trad_grid=20.f;
    int isurft=-1;
    float domain_temperature_k=0.f,critfn=0.f;
    std::optional<G12HeatCoefficients> coefficients;
    std::vector<float> sun_sine;         // one per GEO cell, explicit input
    std::vector<int> nearest_surface;    // CALMET NEARS 1-based, explicit
    std::vector<float> lapse_k_per_m;    // source CGAMMA not yet accepted
    std::vector<float> initial_water_qh_wm2;
};
struct G12ThermalResult {
    TerrainHourG11 thermal;
    std::vector<float> shortwave_wm2;
    std::vector<int> humidity_pct,precip_code;
};
inline G12ThermalResult source_selected_g12_thermal_hour(
    const StationSet& deck,const SurfaceSeries& series,
    const SurfaceHour& hour,const GeoGrid& geo,
    const G12ExplicitSolarHeat& forcing) {
    const std::size_t nx=static_cast<std::size_t>(geo.nx);
    const std::size_t ny=static_cast<std::size_t>(geo.ny);
    if(geo.nx<2||geo.ny<2||geo.nx>400||geo.ny>400||
       deck.surface.size()<2||deck.surface.size()>6||
       deck.surface.size()!=hour.by_station.size()||
       series.station_ids.size()!=deck.surface.size()||
       hour.start<series.begin||hour.end>series.end||
       !std::isfinite(geo.grid_km)||geo.grid_km<=0.f||
       forcing.end!=hour.end||hour.end-hour.start!=std::chrono::hours{1}||
       !forcing.synthetic_radiation_fixture||!forcing.coefficients||
       forcing.isurft!=-1||!std::isfinite(forcing.critfn)||
       forcing.critfn<0.f||!std::isfinite(forcing.domain_temperature_k)||
       forcing.domain_temperature_k<=0.f||
       geo.iwat1>geo.iwat2)
        throw std::invalid_argument("G12 selected multi-site SURFVAR/HEATFX hour or provenance invalid");
    const auto n=nx*ny;
    if(geo.terrain_m.size()!=n||geo.landuse.size()!=n||
       geo.albedo.size()!=n||geo.bowen.size()!=n||
       geo.hcg.size()!=n||geo.qf.size()!=n||
       forcing.sun_sine.size()!=n||
       forcing.nearest_surface.size()!=n||
       forcing.lapse_k_per_m.size()!=n||
       forcing.initial_water_qh_wm2.size()!=n)
        throw std::invalid_argument("G12 incomplete independent GEO radiation or GAMMA fields");
    cteas::p6e::SurfvarMultistationInput surface_input;
    surface_input.nx=nx;surface_input.ny=ny;
    surface_input.dgrid_m=geo.grid_km*1000.f;
    surface_input.irad=forcing.irad;
    surface_input.numts=forcing.numts;
    surface_input.trad_grid=forcing.trad_grid;
    surface_input.stations.reserve(deck.surface.size());
    std::vector<int> station_cloud;
    station_cloud.reserve(deck.surface.size());
    for(std::size_t k=0;k<deck.surface.size();++k) {
        if(series.station_ids[k]!=deck.surface[k].id)
            throw std::invalid_argument("G12 SURF station ID/order disagrees with met.inp SSn");
        const auto& observed=hour.by_station[k];
        const auto& location=deck.surface[k];
        if(!observed.cloud_valid)
            throw std::invalid_argument("G12 missing station cloud; HEATFX cannot infer it");
        cteas::p6e::ObservedSurfaceStation s;
        s.x_m=location.local_x_m;s.y_m=location.local_y_m;
        s.temp_k=observed.temperature_valid?observed.temperature_k:9999.f;
        s.rh_pct=observed.humidity_valid?observed.humidity_pct:9999;
        surface_input.stations.push_back(s);
        station_cloud.push_back(observed.opaque_cloud_tenths);
    }
    const auto observed=cteas::p6e::surfvar_multistation(surface_input);
    const auto& coeff=*forcing.coefficients;
    cteas::p6e::HeatFluxInput heat;
    heat.nx=nx;heat.ny=ny;
    heat.mcloud=1;
    heat.water_first=geo.iwat1;heat.water_last=geo.iwat2;
    heat.ha1=coeff.ha1;heat.ha2=coeff.ha2;
    heat.hb1=coeff.hb1;heat.hb2=coeff.hb2;
    heat.hc1=coeff.hc1;heat.hc2=coeff.hc2;heat.hc3p1=coeff.hc3p1;
    heat.station_cloud=std::move(station_cloud);
    heat.nearest=forcing.nearest_surface;
    heat.landuse=geo.landuse;
    heat.sun=forcing.sun_sine;
    // HEATFX requires a correctly sized cloud-grid workspace even for
    // MCLOUD=1, where station-cloud values (via NEARS) are authoritative.
    // Zeros here are unreachable scratch storage, not inferred cloud data.
    heat.cloud_grid.assign(n,0.f);
    heat.temp_k=observed.temp2d_k;
    heat.albedo=geo.albedo;
    heat.bowen=geo.bowen;
    heat.soil_heat_fraction=geo.hcg;
    heat.anthropogenic_wm2=geo.qf;
    heat.initial_qh=forcing.initial_water_qh_wm2;
    // Full original HEATFX and SURFVAR are independent source-matched
    // kernels, but their input forcing is not real P6E acceptance yet.
    const auto flux=cteas::p6e::heatfx(heat);
    G12ThermalResult out;
    out.thermal.end=hour.end;
    out.thermal.provenance=
        TerrainHourProvenance::ObservedSurfvarSyntheticSolarFixture;
    out.thermal.isurft=forcing.isurft;
    out.thermal.domain_temperature_k=forcing.domain_temperature_k;
    out.thermal.critfn=forcing.critfn;
    out.thermal.lapse_k_per_m=forcing.lapse_k_per_m;
    out.thermal.temperature_k=observed.temp2d_k;
    out.thermal.sensible_heat_w_m2=flux.sensible_wm2;
    out.shortwave_wm2=flux.shortwave_wm2;
    out.humidity_pct=observed.rh2d_pct;
    out.precip_code=observed.ipcode2d;
    return out;
}
} // namespace cteas::calmet::p6g
