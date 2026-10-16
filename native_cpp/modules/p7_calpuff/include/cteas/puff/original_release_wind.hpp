#pragma once
#include "cteas/puff/original_met_cell.hpp"
#include "cteas/puff/release.hpp"

namespace cteas::puff {

// Selected original WINDSET (calpuff.for L2767-2880), RLSMET's
// METFM=1 / ZFIND / WINDSET / WSNEW upstream for POINTS1.
// Source hashes: WINDSET 2859709d81953b64015bf081906bfd9e41d7eb01fa80e53fca21ef69fd0279d4;
// RLSMET fa6ecc9793b5aced9c735d8b89beb3e3e3b6a5a4570e534674e9c84ab5625357.
// Does not reconstruct full RLSMET dispersion/station/temperature/PTLAPS
// outputs, PRIME and source PRFIN. The caller MUST supply native HEFF.
struct OriginalReleaseWindRequest {
    float x_cells=0.0F;
    float y_cells=0.0F;
    float release_height_m=0.0F;  // RLSMET HTR: native PRFIN HEFF
    float calm_threshold_ms=0.0F; // WSCALM from original control
};
struct OriginalReleaseWind {
    OriginalMetCell cell;
    int layer_1based=0;
    float sampled_height_m=0.0F;
    float wind_speed_raw_ms=0.0F;   // original WINDSET WS before calm adjustment
    float wind_speed_ms=0.0F;       // original RLSMET WS / POINTS1 WSNEW
    float wind_direction_deg=0.0F;  // original WINDSET WD
    float flow_deg=0.0F;            // original RLSMET FLOW before radians
    float flow_rad=0.0F;
    int vector_direction_deg=0;     // original RLSMET IVEC=NINT(FLOW)
    bool calm=false;
};
[[nodiscard]] OriginalReleaseWind original_release_wind_metfm1(
    const OriginalMetHour& hour,const Calmet21Static& statics,
    const OriginalReleaseWindRequest& input);
// POINTS1 L15965-15970: native release height WINDSET at BOTH physical
// HTSTAK and native PRFIN HEFF, then WSNEW=AMAX1(WS_stack,WS_final).
// Omitting the stack wind led to original 143h first divergence at hour 12
// (83 predicted instead of 99 original puffs). The release-height HEFF
// and stack height are explicit upstream inputs: no original PRFIN oracle
// enters the autonomous native solver.
[[nodiscard]] ReleaseCadence original_points1_cadence_from_release_wind(
    const OriginalMetHour& hour,const Calmet21Static& statics,
    const OriginalReleaseWindRequest& position,
    float stack_height_m,const ReleaseCadenceInputs& cadence);
} // namespace cteas::puff
