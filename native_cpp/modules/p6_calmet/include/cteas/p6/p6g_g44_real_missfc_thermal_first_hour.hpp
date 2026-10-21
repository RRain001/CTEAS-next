#pragma once
// S4-R1c3: REAL NOAA original COMP MISSFC -> native selected
// WIND1/FRADJ/SURFVAR/HEATFX/AIRDEN/ELUSTR in first HOUR only.
// A detached G43 source-owned copy is the ONLY source of model-internal
// nonwind repair. Never mutate P5 SURF or default G19/G26 production.
#include "cteas/p6/p6g_g43_comp_missfc_source.hpp"
#include "cteas/p6/p6g_g42_selected_real_water_missing_wind1.hpp"
#include "cteas/p6/p6g_g21_file_backed_fradj.hpp"
#include "cteas/p6/p6g_g39_selected_water_thermal_reference.hpp"
#include "cteas/p6/p6g_g18d2_station_clock_transaction.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>

namespace cteas::calmet::p6g {

struct G44RealMissfcThermalFirstHour {
    G43OriginalMissfcHour source_missfc;
    G42SelectedWaterWind1 native_wind1;
    G21SelectedFradjFields native_fradj;
    G39SelectedWaterHeatAfterFradj native_heat;
    bool p5_raw_unchanged=false;
    bool model_hour_committed=false;
    bool accepted_for_g24_or_g26=false;
};

// Caller must provide actual immutable CALMET/NOAA file paths, not any
// prepared original Fortran wind, density, surface T, or 45-field output.
// This function neither consumes nor emits an original reference trace.
inline G44RealMissfcThermalFirstHour g44_native_missfc_thermal_first_hour(
    const G19SourceFilePaths& paths,bool explicit_real_reference_only) {
    if(!explicit_real_reference_only)
        throw std::invalid_argument("G44 original-real thermal must opt in");
    auto selected=g41_load_selected_noow_water_first_hour_source(paths,true);
    if(selected.source.stations.surface.size()!=2||
       selected.source.stations.upper.size()!=1||
       selected.source.surface.hourly.size()!=6||
       selected.water_heat_source.original_water_cell_indices.size()!=63)
        throw std::invalid_argument(
            "G44 actual NOAA 2SS/1US/6h/63-water source scope required");

    // Preserve *input* and P5 source series. G43 validates the source-hour
    // reference, and repairs only original model-internal nonwind fields.
    const auto original_raw=selected.source.surface.hourly.front();
    auto repaired=g43_original_comp_missfc_source_only(
        selected,selected.source.surface.hourly.front(),true);
    if(!repaired.source_comp_missfc_complete||
       repaired.G14_G26_production_accepted||
       repaired.original_raw.by_station.size()!=2||
       repaired.original_comp_resolved.by_station.size()!=2)
        throw std::logic_error("G44 G43 original source invalid");
    bool unchanged=true;
    for(std::size_t s=0;s<2;++s) {
        const auto& old=original_raw.by_station[s];
        const auto& current=selected.source.surface.hourly.front().by_station[s];
        if(old.wind_valid!=current.wind_valid||
           old.wind_speed_mps!=current.wind_speed_mps||
           old.wind_direction_deg!=current.wind_direction_deg||
           old.pressure_valid!=current.pressure_valid||
           old.pressure_mb!=current.pressure_mb||
           old.temperature_valid!=current.temperature_valid||
           old.temperature_k!=current.temperature_k)
            unchanged=false;
    }
    if(!unchanged)
        throw std::logic_error("G44 P5 raw station fields illegally modified");
    // Only the detached, test-only source-owned CALMET COMP copy is changed.
    selected.source.surface.hourly.front()=repaired.original_comp_resolved;
    const auto& resolved=selected.source.surface.hourly.front();
    for(std::size_t s=0;s<2;++s) {
        const auto& original=original_raw.by_station[s];
        const auto& x=resolved.by_station[s];
        if(!x.pressure_valid||!x.temperature_valid||!x.cloud_valid||
           !x.humidity_valid||!x.ceiling_valid||
           x.wind_valid!=original.wind_valid||
           x.wind_speed_mps!=original.wind_speed_mps||
           x.wind_direction_deg!=original.wind_direction_deg)
            throw std::invalid_argument("G44 source MISSFC did not resolve nonwind");
    }

    auto scheduler=selected.source.make_scheduler();
    auto frame=scheduler.preview_next_hour();
    G18D2StationClockAuthority clock;
    const auto prep=clock.prepare_selected(
        scheduler,selected.source.original_metinp,true);
    auto native_wind=g42_selected_real_water_missing_wind1(
        frame,selected,true);
    const auto& wind1=native_wind.native_firstguess;
    auto fradj=g41_real_water_first_hour_native_fradj(
        frame,selected,prep.cgamma,wind1,true);
    G17B4TwoPassSurfvar two_pass(
        selected.source.grid,selected.source.stations,
        selected.source.surface,frame.surface,
        selected.surface_controls,true);
    two_pass.after_wind1_before_fradj(
        frame.input.end,wind1.u_mps,wind1.v_mps);
    two_pass.after_fradj_before_heatfx(
        frame.input.end,fradj.corrected_wind.u,
        fradj.corrected_wind.v);
    if(two_pass.first_temperature()!=fradj.temperature_before_k||
       two_pass.final_temperature()!=fradj.temperature_after_k)
        throw std::logic_error("G44 G21 genuine SURFVAR state divergent");
    const auto& z=selected.source.controls.zface_m;
    if(z[0]!=0.f||z[1]<=0.f)
        throw std::invalid_argument("G44 original ZFACE not source validated");
    const float zm=0.5f*(z[0]+z[1]);
    auto heat=g39_original_noow_water_postfradj_thermal_reference(
        selected.source.grid,selected.source.stations,
        resolved,two_pass,fradj.corrected_wind,
        selected.source.original_metinp,zm,true);
    if(heat.water_ustar_el_zi_ready||heat.g22_g24_wind_ready||
       heat.g14_g26_production_ready||
       heat.selected_original_water_cells!=63||
       scheduler.completed_hours()!=0||clock.has_published_hour())
        throw std::logic_error("G44 unaccepted water physical state published");
    G44RealMissfcThermalFirstHour out;
    out.source_missfc=std::move(repaired);
    out.native_wind1=std::move(native_wind);
    out.native_fradj=std::move(fradj);
    out.native_heat=std::move(heat);
    out.p5_raw_unchanged=unchanged;
    return out;
}
} // namespace cteas::calmet::p6g
