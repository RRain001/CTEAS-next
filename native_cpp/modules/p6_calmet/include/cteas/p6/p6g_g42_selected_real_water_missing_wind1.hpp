#pragma once
// S4-R1c1 genuine WATER: original missing/calm SS WIND1 source masks.
// Frozen G9 CALMET selected inverse-square / sequential BIAS / ICALM
// physical kernel remains unmodified. This is not the accepted G16 G14
// stage and cannot publish any scheduler hour or production P6 meteorology.
#include "cteas/p6/p6g_g41_real_water_first_hour_source.hpp"
#include "cteas/p6/p6g_g20_file_backed_wind1_profiles.hpp"
#include "cteas/p6/p6g_multi_wind1_firstguess.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G42SelectedWaterWind1 {
    G16ObservedProfiles source_profiles;
    Wind1MultiField native_firstguess;
    std::size_t missing_observed_surface_sites=0;
    std::size_t calm_observed_surface_sites=0;
    bool g14_g26_production_ready=false;
};

inline G42SelectedWaterWind1 g42_selected_real_water_missing_wind1(
    const MultiHourFrame& frame,
    const G41SelectedNoowWaterFirstHourSource& selected,
    bool explicitly_test_only) {
    if(!explicitly_test_only||frame.hour_index!=0||
       frame.input.end!=selected.source.surface.hourly.front().end)
        throw std::invalid_argument("G42 source-native WIND1 is first-hour only");
    G42SelectedWaterWind1 out;
    out.source_profiles=g41_original_noow_water_source_profiles(
        frame,selected,true);
    const auto& profiles=out.source_profiles;
    const auto ns=frame.stations.surface.size();
    const auto nu=frame.stations.upper.size();
    const auto total=ns+nu;
    const auto n=9*total;
    if(ns<1||nu<1||total>479||profiles.end!=frame.input.end||
       profiles.wind1_u_mps.size()!=n||
       profiles.wind1_v_mps.size()!=n||
       profiles.wind1_present.size()!=n)
        throw std::invalid_argument("G42 wrong source station profiles");
    Wind1MultiInput in;
    in.nx=frame.grid.nx;in.ny=frame.grid.ny;in.nz=9;
    in.spacing_m=frame.grid.grid_km*1000.f;
    in.surface_count=static_cast<int>(ns);
    in.upper_count=static_cast<int>(nu);
    if(!frame.source_controls)
        throw std::invalid_argument("G42 no source wind controls");
    in.icalm=frame.source_controls->icalm;
    in.vertical_bias.assign(frame.source_controls->bias.begin(),
                            frame.source_controls->bias.end());
    in.station_u_mps=profiles.wind1_u_mps;
    in.station_v_mps=profiles.wind1_v_mps;
    in.present=profiles.wind1_present;
    for(std::size_t s=0;s<ns;++s) {
        const auto& station=frame.stations.surface[s];
        const auto& observed=frame.surface.by_station[s];
        if(profiles.station_ids[s]!=station.id)
            throw std::invalid_argument("G42 SS source identity shuffled");
        in.station_x_m.push_back(station.local_x_m);
        in.station_y_m.push_back(station.local_y_m);
        if(!observed.wind_valid) {
            ++out.missing_observed_surface_sites;
            for(std::size_t k=0;k<9;++k)
                if(profiles.wind1_present[k*total+s]!=0U||
                   profiles.wind1_u_mps[k*total+s]!=0.f||
                   profiles.wind1_v_mps[k*total+s]!=0.f)
                    throw std::logic_error(
                        "G42 missing NOAA SS masquerades as valid observation");
            // The scalar zero is purely an inactive G9 input-carrier; the
            // independently source-validated present=0 suppresses weight.
            in.surface_speeds_mps.push_back(0.f);
        } else {
            const float speed=observed.wind_speed_mps;
            if(!std::isfinite(speed)||speed<0.f||speed>=998.99f)
                throw std::invalid_argument("G42 invalid observed SS speed");
            if(speed<1.e-4f) {
                ++out.calm_observed_surface_sites;
                for(std::size_t k=0;k<9;++k)
                    if(profiles.wind1_present[k*total+s]!=1U||
                       profiles.wind1_u_mps[k*total+s]!=0.f||
                       profiles.wind1_v_mps[k*total+s]!=0.f)
                        throw std::logic_error(
                            "G42 observed calm SS is not exact original zero");
            }
            in.surface_speeds_mps.push_back(speed);
        }
    }
    for(std::size_t s=0;s<nu;++s) {
        const auto& station=frame.stations.upper[s];
        if(profiles.station_ids[ns+s]!=station.id)
            throw std::invalid_argument("G42 US source identity shuffled");
        in.station_x_m.push_back(station.local_x_m);
        in.station_y_m.push_back(station.local_y_m);
    }
    // Genuine missing station must never be replaced by a spurious nearby
    // observation; all original weight operations are in frozen G9.
    out.native_firstguess=multi_station_wind1_firstguess(in);
    const auto cells=static_cast<std::size_t>(frame.grid.nx)*
                     static_cast<std::size_t>(frame.grid.ny);
    if(out.native_firstguess.u_mps.size()!=9*cells||
       out.native_firstguess.v_mps.size()!=9*cells)
        throw std::logic_error("G42 incomplete native first guess");
    return out;
}
} // namespace cteas::calmet::p6g
