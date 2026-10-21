#pragma once
// S4-R1c1: a new strongly scoped source/clock-to-first-hour WIND1/FRADJ
// water-only research admission. Never convertible to G19FileBackedCase.
// Original land-only G19B/G22/G26 production code is not modified.
#include "cteas/p6/p6g_g19_file_backed_case.hpp"
#include "cteas/p6/p6g_g38_selected_noow_water_hflux_source.hpp"
#include <cstddef>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G41SelectedNoowWaterFirstHourSource {
    G19SourceClockCase source;
    G17B4SurfaceControls surface_controls;
    G38SelectedNoowWaterHfluxSource water_heat_source;
    std::vector<std::size_t> source_setcom_station_to_upper;
    bool first_hour_native_wind1_fradj_ready=false;
    bool g24_native_final_wind_ready=false;
    bool g14_g26_production_ready=false;
};
static_assert(!std::is_convertible_v<G41SelectedNoowWaterFirstHourSource,
                                    G19FileBackedCase>);
inline G41SelectedNoowWaterFirstHourSource
g41_load_selected_noow_water_first_hour_source(
    const G19SourceFilePaths& paths,bool explicit_water_reference_only) {
    if(!explicit_water_reference_only)
        throw std::invalid_argument("G41 NOOW water first hour requires opt-in");
    G41SelectedNoowWaterFirstHourSource out;
    out.source=g19_load_source_clock_only(paths);
    const auto& s=out.source;
    if(s.stations.surface.size()<1||s.stations.upper.size()<1||
       s.surface.hourly.empty())
        throw std::invalid_argument("G41 actual SS/US source missing");
    out.water_heat_source=g38_selected_noow_water_hflux_source_only(
        s.grid,s.original_metinp,true);
    // Real original SETCOM station-to-grid ownership remains over LAND.
    // Do not allow a water surface observation to masquerade as a land site.
    out.source_setcom_station_to_upper=
        g18d6_station_uppers_from_source_setcom(
            s.grid,s.stations,s.original_metinp,true);
    out.surface_controls=parse_g17b4_surface_controls(s.original_metinp);
    if(out.surface_controls.source.iavet!=1||
       s.controls.ifradj!=1||s.controls.islope!=1||
       out.source_setcom_station_to_upper.size()!=s.stations.surface.size()||
       out.water_heat_source.original_water_cell_indices.empty())
        throw std::invalid_argument(
            "G41 selected original physical path not supported for water");
    const auto first=s.make_scheduler().preview_next_hour();
    if(first.hour_index!=0||first.input.end!=s.surface.hourly.front().end||
       first.surface.by_station.size()!=s.stations.surface.size())
        throw std::logic_error("G41 G19 first real hour detached");
    return out;
}
} // namespace cteas::calmet::p6g
