#pragma once
// S4-R1c6: actual first-hour 2SS+1US no-overwater-observation
// G43 MISSFC -> G44 G39 -> ORIGINAL G22 SLOPE. No G23/G24 or G14 commit.
// Shared p6::compute_original_slope_scoped source kernel; no oracle inputs.
#include "cteas/p6/p6g_g44_real_missfc_thermal_first_hour.hpp"
#include "cteas/p6/p6g_g22_file_backed_thermal_slope.hpp"
#include <chrono>
#include <stdexcept>
namespace cteas::calmet::p6g {
struct G47RealWaterPostSlope {
    G44RealMissfcThermalFirstHour thermal;
    G22OriginalSlopeAfterElustr slope;
    std::chrono::sys_seconds end{};
    std::size_t original_water_cells=0;
    bool source_raw_p5_unchanged=false;
    bool native_g23_g24_g26_accepted=false;
};
inline G47RealWaterPostSlope g47_actual_noow_water_after_elustr_slope(
    const G19SourceFilePaths& paths,bool selected_original_reference_only) {
    if(!selected_original_reference_only)
        throw std::invalid_argument("G47 genuine water SLOPE is reference-only");
    auto selected=g41_load_selected_noow_water_first_hour_source(paths,true);
    if(selected.source.grid.nx!=82||selected.source.grid.ny!=85||
       selected.source.surface.hourly.size()!=6||
       selected.source.stations.surface.size()!=2||
       selected.source.stations.upper.size()!=1||
       selected.water_heat_source.original_water_cell_indices.size()!=63)
        throw std::invalid_argument("G47 missing actual 2SS1US water source");
    G47RealWaterPostSlope result;
    result.thermal=g44_native_missfc_thermal_first_hour(paths,true);
    if(!result.thermal.p5_raw_unchanged||
       result.thermal.model_hour_committed||
       result.thermal.accepted_for_g24_or_g26)
        throw std::logic_error("G47 unauthorized physical G14 commitment");
    const auto& original=selected.source;
    if(result.thermal.native_fradj.end!=original.surface.hourly.front().end||
       result.thermal.native_heat.heat.end!=
           original.surface.hourly.front().end||
       result.thermal.native_heat.elustr.end!=
           original.surface.hourly.front().end)
        throw std::logic_error("G47 original and native stage clock drift");
    result.slope=g22_original_slope_after_elustr(
        original.grid,original.controls,original.original_metinp,
        result.thermal.native_fradj.corrected_wind,
        result.thermal.native_heat.heat,
        result.thermal.native_heat.elustr,
        true);
    result.end=original.surface.hourly.front().end;
    result.original_water_cells=63;
    result.source_raw_p5_unchanged=true;
    return result;
}
} // namespace cteas::calmet::p6g
