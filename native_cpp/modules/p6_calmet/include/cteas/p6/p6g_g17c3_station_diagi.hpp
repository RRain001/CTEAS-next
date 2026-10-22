#pragma once
// G17C3: >=1SS/>=1US selected source-ordered STHEOR/ELUSTR2 -> MIXHTST -> DIAGI SIMILT.
// Reuses the frozen PR #53 kernels. External SS->US association and
// meteorological numerical controls are TEST-SCOPED until original multi-site
// SETCOM/STHEOR station selection and full COMP state pass independent parity.
// NEVER marks full CALMET DIAGNO/COMP native acceptance.
#include "cteas/p6/p6g_g17c2_elustr_handoff.hpp"
#include "cteas/p6/p6g_g18d7_source_station_cell.hpp"
#include "cteas/p6/station_elustr2.hpp"
#include "cteas/p6/station_mixhtst.hpp"
#include "cteas/p6/similt_profile.hpp"
#include "cteas/p6e/coordlib_pj09z0.hpp"
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G17C3StationControls {
    // The exact original STHEOR NEARU/site correspondence remains a
    // source-selection dependency: never silently use US1 for every SS.
    std::vector<std::size_t> upper_ordinal_for_surface; // zero based
    G12HeatCoefficients heat_coefficients{};
    float zimin_m=50.f,zimax_m=3000.f,constn=2400.f,dptmin_kperm=.001f;
    float dzzi_m=200.f,threshl=0.f,onedte_s=4140.f,twodte_s=1080.f;
    float tzicrlx_s=800.f,fcori_s=1.e-4f,cmech=100.f;
    int ipsifcn=0,imixh=1,izicrlx=1;
    bool explicitly_test_only=false;
};
struct G17C3StationDiagi {
    int surface_id=0,upper_id=0;
    std::size_t cell=0,levels_filled=0;
    std::chrono::sys_seconds end{};
    p6::StationElustr2Flux station_flux{};
    p6::StationMixhtstResult station_mixing{};
    p6::SimiltProfileOutput diagi_profile{};
    // DPTT from MIXHTST is a mutation for *current* COMP grid input,
    // never a replacement for the immutable prior-hour state.
};
inline std::vector<G17C3StationDiagi> selected_station_diagi_from_previous_comp(
    const MultiHourFrame& frame,
    const G17B4TwoPassSurfvar& surfvar,
    const G17CSelectedHeatResult& heat,
    const G17C3StationControls& ctrl,
    bool explicitly_original_sparse_surface_wind=false) {
    using namespace std::chrono;
    const auto& grid=frame.grid;
    const auto& deck=frame.stations;
    const auto n=static_cast<std::size_t>(grid.nx)*static_cast<std::size_t>(grid.ny);
    if(!ctrl.explicitly_test_only||ctrl.ipsifcn!=0||
       (ctrl.imixh!=1&&ctrl.imixh!=-1&&ctrl.imixh!=2&&ctrl.imixh!=-2)||
       ctrl.upper_ordinal_for_surface.size()!=deck.surface.size()||
       !frame.source_controls||
       frame.surface.end!=frame.input.end||heat.end!=frame.input.end||
       frame.surface.end-frame.surface.start!=hours{1}||
       !surfvar.first_ready()||!surfvar.second_ready()||
       !surfvar.matches_source_geometry(grid,deck)||
       surfvar.end()!=frame.input.end||
       heat.temperature_k!=surfvar.final_temperature()||
       heat.sun_sine.size()!=n||heat.density_kg_m3.size()!=n||
       grid.z0_m.size()!=n||grid.landuse.size()!=n||
       grid.albedo.size()!=n||grid.bowen.size()!=n||
       grid.hcg.size()!=n||grid.qf.size()!=n||
       frame.previous.zi_m.size()!=n||
       frame.previous.ziconv_m.size()!=n||
       frame.previous.dptt_k.size()!=n||
       grid.hemisphere!='N'||grid.zone<1||grid.zone>60||
       !std::isfinite(ctrl.fcori_s)||ctrl.fcori_s<=0.f||
       !std::isfinite(ctrl.cmech)||ctrl.cmech<=0.f)
        throw std::invalid_argument("G17C3 STHEOR/COMP source scope missing");
    // CALMET 6.5.0 READCF L26359/L26368 requires >=1 SS and >=1 US
    // for selected NOOBS=0. DIAGI L5099/L5125/L5137 loops actual counts;
    // STHEOR L31111 operates on one station ordinal. Keep all observed
    // bracket/validity/identity/terrain checks below unchanged.
    if(deck.surface.empty()||deck.upper.empty()||
       frame.upper.size()!=deck.upper.size()||
       frame.input.upper.size()!=deck.upper.size()||
       frame.surface.by_station.size()!=deck.surface.size()||
       ctrl.heat_coefficients.hc3p1==0.f)
        throw std::invalid_argument("G17C3 station or heat input invalid");

    const auto projection=cteas::p6e::utm_north_projection(grid.zone);
    std::vector<G17C3StationDiagi> result;
    result.reserve(deck.surface.size());
    for(std::size_t i=0;i<deck.surface.size();++i) {
        const auto& station=deck.surface[i];
        const auto& obs=frame.surface.by_station[i];
        // Original actual sparse SURF: a genuinely missing observed wind
        // contributes no STHEOR/SIMILT station column. Keep the original
        // ordinal, site geometry and P5 mask; never turn it into calm zero.
        // Only an explicit research opt-in may skip source-invalid winds.
        if(!obs.wind_valid&&explicitly_original_sparse_surface_wind)
            continue;
        const auto upper_id=ctrl.upper_ordinal_for_surface[i];
        if(upper_id>=deck.upper.size()||
           frame.upper[upper_id].station_id!=deck.upper[upper_id].id||
           !obs.wind_valid||!obs.pressure_valid||!obs.cloud_valid||
           !std::isfinite(station.anemometer_height_m)||
           station.anemometer_height_m<=0.f||
           !std::isfinite(station.utm_x_km)||station.utm_x_km<=0.f||
           !std::isfinite(station.utm_y_km)||station.utm_y_km<=0.f)
            throw std::invalid_argument("G17C3 missing source SS/US identity or observed forcing");
        // READCF local metres: reject an out-of-domain station instead of
        // silently clamping its STHEOR cell to the boundary.
        const float dx=grid.grid_km*1000.f;
        if(station.local_x_m<0.f||station.local_y_m<0.f||
           station.local_x_m>=static_cast<float>(grid.nx)*dx||
           station.local_y_m>=static_cast<float>(grid.ny)*dx)
            throw std::invalid_argument("G17C3 station outside source GEO");
        const auto cell=g18d7_source_diagi_station_cell(grid,station);
        if(grid.landuse[cell]>=grid.iwat1&&grid.landuse[cell]<=grid.iwat2)
            throw std::invalid_argument("G17C3 station WATER2 not source-accepted");
        // Select the newest sounding at or before the model HOUR START,
        // never the interpolated future sounding or another upper station.
        const auto& profiles=frame.upper[upper_id].soundings;
        const p6::UpperSounding* older=nullptr;
        for(const auto& sounding:profiles) {
            if(sounding.end<=frame.surface.start)older=&sounding;
            else break;
        }
        if(!older||older->data.size()<2)
            throw std::invalid_argument("G17C3 no older observed thermal UP sounding");
        p6e::MixdtSounding sounding;
        for(const auto& layer:older->data) {
            sounding.height_m.push_back(layer.height_lgl_m);
            sounding.temp_k.push_back(layer.temperature_valid?
                                      layer.temperature_k:9999.f);
        }
        if(!std::isfinite(obs.wind_speed_mps)||obs.wind_speed_mps<0.001f||
           !std::isfinite(obs.wind_direction_deg)||obs.wind_direction_deg<0.f||
           obs.wind_direction_deg>360.f||!std::isfinite(obs.pressure_mb)||
           obs.pressure_mb<=0.f||obs.opaque_cloud_tenths<0||
           obs.opaque_cloud_tenths>10)
            throw std::invalid_argument("G17C3 unsupported calm/missing original SURF");
        const float rad=0.0174533f*obs.wind_direction_deg;
        const float u=-obs.wind_speed_mps*std::sin(rad);
        const float v=-obs.wind_speed_mps*std::cos(rad);
        p6::StationElustr2Input flux;
        flux.surface_u_mps=u;flux.surface_v_mps=v;
        flux.zmid1_m=0.5f*(frame.source_controls->zface_m[0]+
                           frame.source_controls->zface_m[1]);
        flux.anemometer_m=station.anemometer_height_m;
        flux.z0_m=grid.z0_m[cell];
        flux.solar_sine=heat.sun_sine[cell];
        flux.temp_k=heat.temperature_k[cell];
        flux.rho_kg_m3=0.3484321f*obs.pressure_mb/flux.temp_k;
        flux.cloud_tenths=obs.opaque_cloud_tenths;
        flux.ipsifcn=ctrl.ipsifcn;
        const auto& c=ctrl.heat_coefficients;
        flux.ha1=c.ha1;flux.ha2=c.ha2;flux.hb1=c.hb1;flux.hb2=c.hb2;
        flux.hc1=c.hc1;flux.hc2=c.hc2;flux.hc3p1=c.hc3p1;
        flux.albedo=grid.albedo[cell];flux.bowen=grid.bowen[cell];
        flux.hcg=grid.hcg[cell];flux.qf=grid.qf[cell];
        const auto station_flux=p6::station_elustr2_flux(flux);
        if(!station_flux.extrapolate)
            throw std::invalid_argument("G17C3 calm STHEOR station not scoped");
        p6::StationMixhtstInput mix;
        mix.previous={frame.previous.zi_m[cell],
                      frame.previous.ziconv_m[cell],
                      frame.previous.dptt_k[cell]};
        mix.older_sounding=std::move(sounding);
        mix.qh_wm2=station_flux.sensible_wm2;
        mix.ustar_mps=station_flux.friction_velocity_mps;
        mix.el_m=station_flux.monin_obukhov_m;
        mix.rho_kg_m3=flux.rho_kg_m3;
        mix.zimin_m=ctrl.zimin_m;mix.zimax_m=ctrl.zimax_m;
        mix.constn=ctrl.constn;
        mix.dptmin_kperm=ctrl.dptmin_kperm;mix.dzzi_m=ctrl.dzzi_m;
        mix.threshl=ctrl.threshl;mix.onedte_s=ctrl.onedte_s;
        mix.twodte_s=ctrl.twodte_s;mix.tzicrlx_s=ctrl.tzicrlx_s;
        mix.imixh=ctrl.imixh;mix.izicrlx=ctrl.izicrlx;
        mix.landuse=grid.landuse[cell];
        mix.water_first=grid.iwat1;mix.water_last=grid.iwat2;
        mix.fcori_s=ctrl.fcori_s;mix.cmech=ctrl.cmech;
        const auto mixing=p6::station_mixhtst(mix);
        double latitude=0.,longitude=0.;
        cteas::p6e::utm_north_to_latlon_deg(
            projection,static_cast<double>(station.utm_x_km)*1000.0,
            static_cast<double>(station.utm_y_km)*1000.0,latitude,longitude);
        if(!std::isfinite(latitude)||latitude<=0.||latitude>90.)
            throw std::invalid_argument("G17C3 invalid station source latitude");
        p6::SimiltProfileInput diagi;
        diagi.station_lat_deg=static_cast<float>(latitude);
        diagi.anemometer_height_m=station.anemometer_height_m;
        diagi.roughness_m=grid.z0_m[cell];
        diagi.anemometer_u_mps=u;diagi.anemometer_v_mps=v;
        diagi.obukhov_length_m=station_flux.monin_obukhov_m;
        diagi.mixing_height_m=mixing.zii_to_similt_m;
        diagi.minimum_mixing_height_m=ctrl.zimin_m;
        diagi.zface_m=frame.source_controls->zface_m;
        diagi.ipsifcn=ctrl.ipsifcn;
        const auto profile=p6::original_similt_profile(diagi);
        result.push_back({station.id,deck.upper[upper_id].id,cell,
                          profile.levels_filled,frame.input.end,
                          station_flux,mixing,profile});
    }
    return result;
}
// The already validated G16 WIND1 neutral profiles must be preserved.
// Only DIAGI's surface columns may be replaced by the source-station
// STHEOR/MIXHTST output, leaving PREPDI upper-air columns intact.
inline G16ObservedProfiles merge_g17c3_surface_diagi(
    G16ObservedProfiles profiles,
    const StationSet& station_set,
    const std::vector<G17C3StationDiagi>& selected) {
    const auto ns=station_set.surface.size();
    const auto nu=station_set.upper.size();
    const auto total=ns+nu;
    if(selected.size()!=ns||profiles.station_ids.size()!=total||
       profiles.wind1_u_mps.size()!=total*9||
       profiles.wind1_v_mps.size()!=total*9||
       profiles.inter2_u_mps.size()!=total*9||
       profiles.inter2_v_mps.size()!=total*9||
       profiles.inter2_present.size()!=total*9)
        throw std::invalid_argument("G17C3 DIAGI station-profile geometry invalid");
    for(std::size_t i=0;i<total;++i)
        if(profiles.station_ids[i]!=(i<ns?station_set.surface[i].id:
                                       station_set.upper[i-ns].id))
            throw std::invalid_argument("G17C3 DIAGI station ordinal mismatch");
    for(std::size_t i=0;i<ns;++i) {
        const auto& src=selected[i];
        if(src.surface_id!=station_set.surface[i].id||
           src.end!=profiles.end||src.levels_filled>9||
           src.levels_filled<1)
            throw std::invalid_argument("G17C3 DIAGI stale/shuffled SS output");
        for(std::size_t k=0;k<9;++k) {
            const auto index=k*total+i;
            const bool valid=k<src.levels_filled;
            profiles.inter2_u_mps[index]=valid?
                src.diagi_profile.u_mps[k]:999.f;
            profiles.inter2_v_mps[index]=valid?
                src.diagi_profile.v_mps[k]:999.f;
            profiles.inter2_present[index]=valid?1U:0U;
        }
    }
    return profiles;
}
} // namespace cteas::calmet::p6g
