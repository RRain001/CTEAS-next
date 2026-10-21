#pragma once
// Issue #40 S4-R1c4a: six genuine successive NOAA observed-source hours,
// actual 2SS/1US wind interpolation only. Not a G14 hourly executor.
// Unlike CGAMMA/MIXHTST/COMP, WIND1 depends on the current observed
// surface+PREPDI UP winds and source BIAS/ICALM, NOT prior ZICONV/ZI.
// No previous-memory guess is consumed or silently committed. Never
// promote this diagnostic as six-hour G21/G39/45-field physics.
#include "cteas/p6/p6g_g42_selected_real_water_missing_wind1.hpp"
#include <chrono>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G45SixHourWaterWind1 {
    std::vector<G42SelectedWaterWind1> hours;
    std::vector<std::chrono::sys_seconds> source_end_utc;
    std::size_t original_water_cells=0;
    bool original_p5_surf_mutated=false;
    bool original_previous_ziconv_accepted=false;
    bool g21_g39_g24_g26_accepted=false;
};

inline G45SixHourWaterWind1 g45_selected_source_six_hour_wind1(
    const G19SourceFilePaths& paths,bool explicit_six_hour_reference_only) {
    if(!explicit_six_hour_reference_only)
        throw std::invalid_argument(
            "G45 requires six-hour original-source WIND1 science opt-in");
    const auto selected=g41_load_selected_noow_water_first_hour_source(
        paths,true);
    const auto& source=selected.source;
    if(source.stations.surface.size()!=2||
       source.stations.upper.size()!=1||
       source.surface.hourly.size()!=6||
       source.grid.nx!=82||source.grid.ny!=85||
       source.grid.grid_km!=1.f||
       selected.water_heat_source.original_water_cell_indices.size()!=63)
        throw std::invalid_argument(
            "G45 unaccepted external water wind source size/site/time scope");
    // The authoritative source binder is used for all six hours rather
    // than manufacturing a new clock or cycling the first-hour fixture.
    const auto actual_input=bind_original_calmet_station_inputs(
        source.stations,source.surface,source.upper);
    const auto single_scheduler=source.make_scheduler();
    if(actual_input.size()!=6||single_scheduler.planned_hours()!=6||
       single_scheduler.completed_hours()!=0)
        throw std::logic_error(
            "G45 real source input hour clocks not bound");
    const auto original_raw=source.surface.hourly;
    const auto n=static_cast<std::size_t>(source.grid.nx)*
                 static_cast<std::size_t>(source.grid.ny);
    // The selected WIND1 kernel NEVER dereferences frame.previous or
    // writes frame.next. Empty provenance is intentional: do not imply
    // previous-hour ZICONV/CGAMMA has been computed or carried.
    p6::NativeGridMemory not_accepted_previous;
    G45SixHourWaterWind1 result;
    result.hours.reserve(6);
    result.source_end_utc.reserve(6);
    result.original_water_cells=63;
    for(std::size_t h=0;h<6;++h) {
        const auto& obs=source.surface.hourly[h];
        const auto& input=actual_input[h];
        if(input.end!=obs.end||
           obs.end-obs.start!=std::chrono::hours{1}||
           (h>0&&(obs.start!=source.surface.hourly[h-1].end||
                   input.end!=actual_input[h-1].end+
                       std::chrono::hours{1})))
            throw std::invalid_argument("G45 six actual NOAA hours discontinuous");
        MultiHourFrame frame{
            h,source.grid,source.stations,obs,input,source.upper,
            &source.controls,not_accepted_previous,not_accepted_previous,{}
        };
        auto wind=g42_selected_real_water_missing_wind1_kernel(
            frame,selected,true,true);
        if(wind.g14_g26_production_ready||
           wind.native_firstguess.nx!=82||
           wind.native_firstguess.ny!=85||
           wind.native_firstguess.nz!=9||
           wind.native_firstguess.u_mps.size()!=9*n||
           wind.native_firstguess.v_mps.size()!=9*n||
           wind.source_profiles.end!=obs.end)
            throw std::logic_error("G45 native source-only WIND1 invalid");
        result.source_end_utc.push_back(obs.end);
        result.hours.push_back(std::move(wind));
    }
    for(std::size_t h=0;h<6;++h) {
        const auto& old=original_raw[h];
        const auto& now=source.surface.hourly[h];
        if(old.start!=now.start||old.end!=now.end||
           old.by_station.size()!=now.by_station.size())
            throw std::logic_error("G45 P5 source timing was changed");
        for(std::size_t i=0;i<old.by_station.size();++i)
            if(old.by_station[i].wind_valid!=now.by_station[i].wind_valid||
               old.by_station[i].wind_speed_mps!=now.by_station[i].wind_speed_mps||
               old.by_station[i].wind_direction_deg!=now.by_station[i].wind_direction_deg||
               old.by_station[i].pressure_valid!=now.by_station[i].pressure_valid||
               old.by_station[i].pressure_mb!=now.by_station[i].pressure_mb||
               old.by_station[i].temperature_valid!=now.by_station[i].temperature_valid||
               old.by_station[i].temperature_k!=now.by_station[i].temperature_k)
                throw std::logic_error(
                    "G45 modified original P5 sparse surface source");
    }
    return result;
}
} // namespace cteas::calmet::p6g
