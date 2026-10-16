#pragma once

#include <functional>

#include "cteas/puff/advection.hpp"

namespace cteas::puff {

// P7W: RISEWIND (calpuff.for L67162-67300), transcribed from the unmodified
// vendor source and cross-checked against it by CTest.
//
// RISEWIND computes the mean wind components for the transitional rise range: it
// iterates NCOUNT times, each pass taking the plume's rise height at the start and
// end of a step of length WS*DT and averaging the advective wind over the rise
// layer [RBOT, RTOP], blending with the final-rise wind once the puff passes the
// distance of final rise.
//
// The two vendor dependencies are injected, exactly as the caller supplies them:
//   * the gradual-rise height GRISE(x) -> HTGRISE (P7N's ported
//     `gradual_plume_height` for the reconstructed branches);
//   * the advective wind ADVECT(zbot, ztop) (P7V's ported `advective_wind` for
//     METFM=1, which the deck selects).
// Nothing else is hidden state: the puff's travel distance, the final-rise
// distance and height, the step length and the incoming wind are all explicit.

using RiseHeightLookup = std::function<double(double x_m)>;
using StepWindLookup = std::function<AdvectiveWind(double z_bottom_m, double z_top_m)>;

struct RiseWindInputs {
    bool puff = true;                    // LPUFF
    int iterations = 2;                  // NCOUNT (the vendor's COMP data ncount/2/)
    double dz_m = 0.0;                   // DZB: centre to top at the start of the step
    double start_distance_m = 0.0;       // XBEG (XTOTB for a puff, the mean for a slug)
    double final_distance_m = 0.0;       // XFINAL: distance of final rise
    double final_height_m = 0.0;         // ZFINAL: plume height at final rise
    double step_seconds = 0.0;           // DT
    double u_final_ms = 0.0;             // UADV at final rise (ADVECT's return)
    double v_final_ms = 0.0;             // VADV at final rise
    double wind_speed_ms = 0.0;          // WS entering the routine
};

struct RiseWindResult {
    double u_ms = 0.0;                   // transport u after the rise adjustment
    double v_ms = 0.0;
    double wind_speed_ms = 0.0;
    int passes = 0;                      // how many passes ran (the vendor's ICOUNT)
};

// The vendor's minimum transport wind speed (RISEWIND's own data ucalm/0.001/).
inline constexpr double kRiseWindCalmSpeedMs = 0.001;

[[nodiscard]] RiseWindResult transitional_rise_wind(const RiseWindInputs& inputs,
                                                    const RiseHeightLookup& rise_height,
                                                    const StepWindLookup& step_wind);

} // namespace cteas::puff
