#pragma once
#include "cteas/puff/original_met_cell.hpp"
#include "cteas/puff/plume_rise.hpp"
#include "cteas/puff/rise_wind.hpp"

namespace cteas::puff {

// Native METFM=1 / GRISE / RISEWIND bridge. Physical rise-state parameters
// are the caller's independently computed POINTS1/PRFIN data; DGM is never
// an input. This is the CALPUFF point-puff selected branch, not the full
// COMP sampling/splitting scheduler or a final Hefei original oracle.
struct OriginalRiseMetInputs {
    float x_cells=0.0F;
    float y_cells=0.0F;
    float start_distance_m=0.0F;      // puff XTOTB
    float final_distance_m=0.0F;      // XFINAL
    float step_seconds=0.0F;          // selected COMP DT
    float rise_half_depth_m=0.0F;     // DZB after native PUFFDZ/COMP
    int rise_iterations=2;           // vendor NCOUNT=2
    PlumeRiseState plume;             // native POINTS1/PRFIN source state
};
struct OriginalRiseMetResult {
    OriginalMetCell cell;
    AdvectiveWind final_rise_wind;
    RiseWindResult adjusted;
    PlumeRiseResult initial_rise;
};

// Calls the real native original CALMET wind column, the source-ported
// GRISE branch and the source-ported original RISEWIND iteration. It does
// not fill in any missing PRFIN, PUFFDZ or CALLING COMP state with guesses.
[[nodiscard]] OriginalRiseMetResult original_rise_wind_met(
    const OriginalMetHour& hour,const Calmet21Static& statics,
    const OriginalRiseMetInputs& inputs);

} // namespace cteas::puff
