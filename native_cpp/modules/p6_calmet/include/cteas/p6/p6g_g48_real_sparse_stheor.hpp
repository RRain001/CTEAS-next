#pragma once
// S4-R1c7b: use existing G17C3 original station physical kernels on genuine
// 2SS+1US source, without creating a site-specific STHEOR formula.
// Original missing station wind remains invalid, not zero/calm.
#include "cteas/p6/p6g_g47_real_water_post_slope.hpp"
#include "cteas/p6/p6g_g23_file_backed_stheor_inter2.hpp"
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G48RealSparseStheor {
    std::vector<G17C3StationDiagi> native_valid_station;
    std::vector<std::size_t> source_valid_surface_ordinals;
    std::size_t original_surface_station_count=0;
    std::size_t missing_wind_skipped=0;
    bool source_p5_raw_wind_unchanged=false;
    bool native_g23_inter2_or_g26_ready=false;
};

inline G48RealSparseStheor g48_real_sparse_stheor_first_hour(
    const G19SourceFilePaths& paths,bool explicit_reference_only) {
    if(!explicit_reference_only)
        throw std::invalid_argument("G48 real station STHEOR requires test-only opt-in");
    // G47 uses exactly accepted G42/G21/G39/G22 C++ kernels.
    const auto g47=g47_actual_noow_water_after_elustr_slope(paths,true);
    auto selected=g41_load_selected_noow_water_first_hour_source(paths,true);
    const auto raw=selected.source.surface.hourly.front();
    const auto repaired=g43_original_comp_missfc_source_only(
        selected,selected.source.surface.hourly.front(),true);
    if(!g47.source_raw_p5_unchanged||
       !repaired.source_comp_missfc_complete||
       repaired.G14_G26_production_accepted||
       raw.by_station.size()!=2||
       selected.source.stations.upper.size()!=1)
        throw std::logic_error("G48 genuine source and original MISSFC disconnected");
    // Reconstitute the SAME source-owned original COMP internal nonwind
    // materialization. No change to raw P5 observation records.
    selected.source.surface.hourly.front()=repaired.original_comp_resolved;
    for(std::size_t s=0;s<raw.by_station.size();++s) {
        const auto& before=raw.by_station[s];
        const auto& after=selected.source.surface.hourly.front().by_station[s];
        if(before.wind_valid!=after.wind_valid||
           before.wind_speed_mps!=after.wind_speed_mps||
           before.wind_direction_deg!=after.wind_direction_deg||
           before.precip_code!=after.precip_code)
            throw std::logic_error("G48 illegally replaced raw wind/precip");
    }
    auto scheduler=selected.source.make_scheduler();
    const auto frame=scheduler.preview_next_hour();
    if(frame.hour_index!=0||
       frame.input.end!=g47.end||
       frame.input.end!=g47.thermal.native_heat.heat.end||
       frame.input.end!=g47.thermal.native_fradj.end)
        throw std::logic_error("G48 cross-source NOAA first-hour clock drift");
    const auto& original_wind1=
        g47.thermal.native_wind1.native_firstguess;
    const auto& fradj=g47.thermal.native_fradj.corrected_wind;
    G17B4TwoPassSurfvar twice(
        selected.source.grid,selected.source.stations,
        selected.source.surface,frame.surface,
        selected.surface_controls,true);
    twice.after_wind1_before_fradj(
        frame.input.end,original_wind1.u_mps,original_wind1.v_mps);
    twice.after_fradj_before_heatfx(
        frame.input.end,fradj.u,fradj.v);
    if(twice.final_temperature()!=
       g47.thermal.native_heat.heat.temperature_k)
        throw std::logic_error("G48 real G17B4/G39 source temperatures differ");
    const auto ctrl=g23_source_stheor_station_controls(
        selected.source.original_metinp,
        selected.source_setcom_station_to_upper,
        selected.water_heat_source.reference_heat.coefficients,
        selected.source.stations.surface.size(),true);
    auto native=selected_station_diagi_from_previous_comp(
        frame,twice,g47.thermal.native_heat.heat,ctrl,
        true); // ONLY difference: skip genuine source missing SS wind
    G48RealSparseStheor result;
    result.original_surface_station_count=raw.by_station.size();
    result.native_valid_station=std::move(native);
    for(std::size_t s=0;s<raw.by_station.size();++s) {
        if(raw.by_station[s].wind_valid)
            result.source_valid_surface_ordinals.push_back(s+1);
        else
            ++result.missing_wind_skipped;
    }
    if(result.missing_wind_skipped!=1||
       result.native_valid_station.size()!=1||
       result.source_valid_surface_ordinals.size()!=1||
       result.native_valid_station.front().surface_id!=
         selected.source.stations.surface[
           result.source_valid_surface_ordinals.front()-1].id||
       scheduler.completed_hours()!=0)
        throw std::logic_error(
            "G48 real first-hour original sparse STHEOR count/identity mismatch");
    result.source_p5_raw_wind_unchanged=true;
    return result;
}
} // namespace cteas::calmet::p6g
