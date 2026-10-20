#pragma once
// G20: build the original-selected WIND1 station columns from the REAL
// G14 file-backed current-hour SURF, UP/PREPDI, GEO and READCF controls.
// Reuses immutable PR #53 SIMILT/VERTAV and PREPDI kernels without copied
// or synthetic wind columns. This explicitly selected scope is NOT a
// complete multistation DIAGNO/COMP production physics implementation.
#include "cteas/p6/p6g_g16_staged_wind.hpp"
#include "cteas/p6/p6g_g18d7_source_station_cell.hpp"
#include "cteas/p6/similt_profile.hpp"
#include "cteas/p6/vertical_wind_average.hpp"
#include "cteas/p6/upper_hourly_wind.hpp"
#include "cteas/p6e/coordlib_pj09z0.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
inline G16ObservedProfiles g20_file_backed_source_wind1_profiles(
    const MultiHourFrame& frame,bool explicitly_test_only) {
    const auto& grid=frame.grid;
    const auto& stations=frame.stations;
    const auto& surface=frame.surface;
    const auto& in=frame.input;
    const auto ns=stations.surface.size();
    const auto nu=stations.upper.size();
    const auto total=ns+nu;
    const auto cells=static_cast<std::size_t>(grid.nx)*
                      static_cast<std::size_t>(grid.ny);
    if(!explicitly_test_only||!frame.source_controls||
       grid.hemisphere!='N'||grid.nx<2||grid.ny<2||
       ns<1||nu<1||ns>4||nu>4||
       surface.by_station.size()!=ns||in.upper.size()!=nu||
       frame.upper.size()!=nu||surface.end!=in.end||
       surface.end-surface.start!=std::chrono::hours{1}||
       grid.z0_m.size()!=cells||grid.landuse.size()!=cells)
        throw std::invalid_argument(
            "G20 requires audited original-format source 1/1 1/2 2/1 or 2/2 WIND1");
    const auto& readcf=*frame.source_controls;
    if(readcf.iextrp!=-4||readcf.noobs!=0||readcf.iprog!=0)
        throw std::invalid_argument("G20 original IEXTRP WIND1 scope");
    G16ObservedProfiles profiles;
    profiles.end=in.end;
    profiles.station_ids.reserve(total);
    for(const auto& st:stations.surface)profiles.station_ids.push_back(st.id);
    for(const auto& st:stations.upper)profiles.station_ids.push_back(st.id);
    profiles.wind1_u_mps.assign(9*total,0.f);
    profiles.wind1_v_mps.assign(9*total,0.f);
    profiles.wind1_present.assign(9*total,1);
    const auto projection=cteas::p6e::utm_north_projection(grid.zone);
    for(std::size_t s=0;s<ns;++s) {
        const auto& st=stations.surface[s];
        const auto& obs=surface.by_station[s];
        if(!obs.wind_valid||!std::isfinite(obs.wind_speed_mps)||
           !std::isfinite(obs.wind_direction_deg)||
           obs.wind_speed_mps<1.e-4f||obs.wind_speed_mps>=998.99f||
           obs.wind_direction_deg<0.f||obs.wind_direction_deg>360.f)
            throw std::invalid_argument(
                "G20 unsupported missing/calm original surface wind");
        const auto cell=g18d7_source_diagi_station_cell(grid,st);
        if(grid.landuse[cell]>=grid.iwat1&&
           grid.landuse[cell]<=grid.iwat2)
            throw std::invalid_argument("G20 water-site SIMILT not accepted");
        double latitude=0.,longitude=0.;
        cteas::p6e::utm_north_to_latlon_deg(
            projection,static_cast<double>(st.utm_x_km)*1000.0,
            static_cast<double>(st.utm_y_km)*1000.0,
            latitude,longitude);
        if(!std::isfinite(latitude)||!std::isfinite(longitude))
            throw std::invalid_argument("G20 original UTM site projection invalid");
        const float rad=0.0174533f*obs.wind_direction_deg;
        p6::SimiltProfileInput sim;
        sim.station_lat_deg=static_cast<float>(latitude);
        sim.anemometer_height_m=st.anemometer_height_m;
        // Critical: original SETCOM uses Z0 of THIS station's GEO cell;
        // G8's fixed 0.1m was a selected-source exploratory shortcut.
        sim.roughness_m=grid.z0_m[cell];
        sim.anemometer_u_mps=-obs.wind_speed_mps*std::sin(rad);
        sim.anemometer_v_mps=-obs.wind_speed_mps*std::cos(rad);
        sim.obukhov_length_m=10000.f;
        sim.mixing_height_m=10000.f;
        sim.minimum_mixing_height_m=10000.f;
        sim.ipsifcn=0;
        sim.zface_m=readcf.zface_m;
        const auto output=p6::original_similt_profile(sim);
        if(output.levels_filled!=9)
            throw std::invalid_argument("G20 source WIND1 SIMILT incomplete");
        for(std::size_t k=0;k<9;++k) {
            profiles.wind1_u_mps[k*total+s]=output.u_mps[k];
            profiles.wind1_v_mps[k*total+s]=output.v_mps[k];
        }
    }
    const std::vector<float> zface(readcf.zface_m.begin(),
                                   readcf.zface_m.end());
    for(std::size_t site=0;site<nu;++site) {
        const auto& station=frame.upper[site];
        const auto& bound=in.upper[site];
        if(station.station_id!=stations.upper[site].id||
           bound.earlier>=station.soundings.size()||
           bound.later>=station.soundings.size()||
           bound.later!=bound.earlier+1)
            throw std::invalid_argument("G20 source UP identity/bracket mismatch");
        const auto& earlier=station.soundings[bound.earlier];
        const auto& later=station.soundings[bound.later];
        const auto old_layer=p6::calmet_vertav(earlier,zface);
        const auto new_layer=p6::calmet_vertav(later,zface);
        p6::Upper2022 selected;
        selected.station_id=station.station_id;
        selected.pstop_hpa=station.pstop_hpa;
        selected.soundings={earlier,later};
        const auto hour=p6::calmet_prepdi_hour(
            selected,in.end,{old_layer,new_layer});
        if(hour.winds.size()!=9||
           hour.past_seconds!=bound.past_seconds||
           hour.to_go_seconds!=bound.future_seconds||
           hour.gap_seconds!=bound.span_seconds)
            throw std::invalid_argument("G20 source PREPDI wind/clock mismatch");
        for(std::size_t k=0;k<9;++k) {
            const auto u=hour.winds[k].u_mps;
            const auto v=hour.winds[k].v_mps;
            if(!std::isfinite(u)||!std::isfinite(v)||
               std::abs(u)>=998.99f||std::abs(v)>=998.99f)
                throw std::invalid_argument("G20 invalid source upper wind");
            profiles.wind1_u_mps[k*total+ns+site]=u;
            profiles.wind1_v_mps[k*total+ns+site]=v;
        }
    }
    // INTER2 is *not* authorized by this WIND1 data: G18E1 must replace
    // the surface columns with actual stability-capped post-MIXHTST DIAGI
    // after SLOPE and the first WINDBC, before G16 can enter INTER2.
    profiles.inter2_u_mps=profiles.wind1_u_mps;
    profiles.inter2_v_mps=profiles.wind1_v_mps;
    profiles.inter2_present=profiles.wind1_present;
    // G32E: PREPDI upper-air first-layer validity differs between original
    // WIND1 and original DIAGNO INTER2. The independent full original
    // CALMET write-only G32D source profiles for the G19 selected synthetic
    // 2SS/2US fixture have original US1/US2 k=1 EDIT=999, and only
    // G20's neutral upper extrapolation supplies a finite k=1 wind.
    //
    // Keep the frozen G20 WIND1 columns unchanged; represent this
    // source-verified G19 missingness in the *separate* INTER2 columns
    // before handing any profiles to G16. Thus G16's source PREPDI
    // ownership guard stays in force, and G23 may only replace SS
    // profiles after STHEOR, as in the original one-site execution.
    //
    // This is selected G19 forensic science only: the generic original
    // CALMET UP/PREPDI missing-layer policy remains unimplemented and
    // must be source-validated before production multi-site admission.
    // S4-B4: the previous 1SS/1US exploratory gate incorrectly set ALL
    // INTER2 station/height samples missing (999), even the authentic
    // PREPDI US k=2..9 soundings. That excludes the real upper stations
    // from the INTER2 blend and corrupts U/V above the surface. The old C1
    // accepted single-site P6D source uses exactly the opposite rule:
    // original IEXTRP<=0 makes only US k=1 missing; US k>=2 is the true
    // PREPDI interpolated profile. SS DIAGI must separately replace SS
    // observations after MIXHTST; none is inherited from neutral WIND1.
    // No synthetic profile or copied original MET is introduced here.
    if(ns==1&&nu==1) {
        profiles.inter2_present.assign(9*total,0U);
        profiles.inter2_u_mps.assign(9*total,999.f);
        profiles.inter2_v_mps.assign(9*total,999.f);
        for(std::size_t k=1;k<9;++k) {
            const auto idx=k*total+ns;
            profiles.inter2_present[idx]=1U;
            profiles.inter2_u_mps[idx]=profiles.wind1_u_mps[idx];
            profiles.inter2_v_mps[idx]=profiles.wind1_v_mps[idx];
        }
        return profiles;
    }
    // Station identity is validated against the actual original G19
    // deck and UP file for every station above. A literal 58424/58425
    // check here was fixture-only and incorrectly rejected legal IDs.
    if(ns<1||ns>4||nu<1||nu>4||
       zface.front()!=0.f||!(zface[1]>0.f))
        throw std::invalid_argument(
            "G32E original G19 synthetic upper profile scope changed");
    for(std::size_t site=0;site<nu;++site) {
        const auto& upper=frame.upper[site];
        const auto& bound=in.upper[site];
        if(upper.station_id!=stations.upper[site].id||
           bound.earlier>=upper.soundings.size()||
           bound.later>=upper.soundings.size()||
           upper.soundings[bound.earlier].data.size()<2||
           upper.soundings[bound.later].data.size()<2)
            throw std::invalid_argument(
                "G32E G19 original upper sounding source unavailable");
        const auto pos=ns+site; // k=1; physical upper ordinal is SS count + site
        if(!std::isfinite(profiles.wind1_u_mps[pos])||
           !std::isfinite(profiles.wind1_v_mps[pos])||
           profiles.wind1_present[pos]!=1U)
            throw std::invalid_argument(
                "G32E source WIND1 first upper layer not independently available");
        profiles.inter2_present[pos]=0U;
        profiles.inter2_u_mps[pos]=999.f;
        profiles.inter2_v_mps[pos]=999.f;
    }
    return profiles;
}
} // namespace cteas::calmet::p6g
