#pragma once
// S4-R1c8c: source-owned G41 mixed WATER/LAND partition for upcoming
// G26B COMP science. This does not run WATER, MIXHT, AVEMIX or publish
// any 45-field G26 production state. The old G26B all-land guard stands.
#include "cteas/p6/p6g_g41_real_water_first_hour_source.hpp"
#include "cteas/p6/p6g_g18d5_source_mixht_controls.hpp"
#include <chrono>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace cteas::calmet::p6g {
struct G26BRealWaterCompSourcePartition {
    std::chrono::sys_seconds end{};
    std::vector<std::size_t> original_land_cell_ordinals;
    std::vector<std::size_t> original_water_cell_ordinals;
    // Only original READCF scalar metadata; NOT a complete executable
    // G18ASelectedCompControls (NEARU/FCORI/AA-BB are unbound).
    G18ASelectedCompControls readcf_scalars_only;
    bool source_water_comp_physics_accepted=false;
    bool original_causal_comp_history_accepted=false;
    bool g26_45fields_accepted=false;
};
inline G26BRealWaterCompSourcePartition
g26b_real_water_comp_partition_source_only(
    const G41SelectedNoowWaterFirstHourSource& genuine,
    const MultiHourFrame& frame,
    bool explicitly_source_only) {
    const auto& s=genuine.source;
    const auto nx=static_cast<std::size_t>(s.grid.nx);
    const auto ny=static_cast<std::size_t>(s.grid.ny);
    const auto n=nx*ny;
    if(!explicitly_source_only||!frame.source_controls||
       !genuine.water_heat_source.reference_heat.explicitly_test_only||
       genuine.g14_g26_production_ready||
       genuine.water_heat_source.g14_g26_production_ready||
       frame.hour_index!=0||s.surface.hourly.empty()||
       frame.input.end!=s.surface.hourly.front().end||
       frame.surface.end!=frame.input.end||
       nx<2||ny<2||nx>400||ny>400||
       s.grid.landuse.size()!=n||
       frame.grid.nx!=s.grid.nx||frame.grid.ny!=s.grid.ny||
       frame.grid.grid_km!=s.grid.grid_km||
       frame.grid.landuse!=s.grid.landuse||
       frame.grid.terrain_m!=s.grid.terrain_m||
       frame.grid.iwat1!=s.grid.iwat1||
       frame.grid.iwat2!=s.grid.iwat2||
       frame.stations.surface.size()!=s.stations.surface.size()||
       frame.stations.upper.size()!=s.stations.upper.size()||
       frame.surface.by_station.size()!=s.stations.surface.size()||
       genuine.source_setcom_station_to_upper.size()!=s.stations.surface.size())
        throw std::invalid_argument(
            "G26B original WATER COMP source partition detached from G41");
    for(std::size_t k=0;k<frame.stations.surface.size();++k)
        if(frame.stations.surface[k].id!=s.stations.surface[k].id||
           s.surface.station_ids[k]!=s.stations.surface[k].id)
            throw std::invalid_argument(
                "G26B original WATER COMP surface station identity changed");
    for(std::size_t k=0;k<frame.stations.upper.size();++k)
        if(frame.stations.upper[k].id!=s.stations.upper[k].id)
            throw std::invalid_argument(
                "G26B original WATER COMP upper station identity changed");
    G26BRealWaterCompSourcePartition out;
    out.end=frame.input.end;
    for(std::size_t k=0;k<n;++k) {
        const auto lu=s.grid.landuse[k];
        if(lu>=s.grid.iwat1&&lu<=s.grid.iwat2)
            out.original_water_cell_ordinals.push_back(k);
        else
            out.original_land_cell_ordinals.push_back(k);
    }
    if(out.original_water_cell_ordinals.empty()||
       out.original_land_cell_ordinals.empty()||
       out.original_water_cell_ordinals!=
           genuine.water_heat_source.original_water_cell_indices)
        throw std::invalid_argument(
            "G26B genuine source WATER ids cannot be reclassified as land");
    // READCF (not a hard-coded test fixture): IMIXH and MIXHT scalar
    // controls for LAND only. The source WATER routine separately
    // owns the actual neutral NOWSTA=0 water-cell mechanical ZI/QH.
    g18d5_bind_original_mixht_scalars(
        s.original_metinp,out.readcf_scalars_only);
    if(out.readcf_scalars_only.grid_mixht.imixh!=1)
        throw std::invalid_argument(
            "G26B source overwater selected original IMIXH differs");
    // Reject implicit promotion. Real-water G26B physical state remains
    // blocked until original-vs-native full first-hour MIXHT/AVEMIX/WATER.
    return out;
}
} // namespace cteas::calmet::p6g
