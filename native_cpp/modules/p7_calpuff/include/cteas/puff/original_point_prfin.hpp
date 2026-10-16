#pragma once
#include "cteas/puff/original_met_hours.hpp"
#include "cteas/puff/original_release_wind.hpp"
#include "cteas/puff/plume_rise.hpp"
#include "cteas/puff/release.hpp"

namespace cteas::puff {

// Original POINTS1 selected METFM=1, no-building, Briggs/PRFPP subset.
// The caller supplies actual grid-relative XY, not absolute UTM kilometers.
// Source/stability branches whose original PTLAPS gradient affects HEFF
// fail closed. The returned values are native calculation outputs, never
// taken from DGM or original puff.con reference records.
struct OriginalPointPrfinRequest {
    float x_cells=0.0F, y_cells=0.0F;
    float stack_height_m=0.0F, diameter_m=0.0F;
    float exit_velocity_ms=0.0F, stack_temperature_k=0.0F;
    float momentum_flux_factor=1.0F; // original Group 13b FMFAC
    float calm_threshold_ms=0.5F;    // original puff.inp WSCALM
    float max_sample_distance_cells=1.0F; // XSAMLEN
    int max_new_puffs=99;            // MXNEW
    float hour_seconds=3600.0F;      // DHR
    // Explicit original RLSMET LCALGRD=true branch. Requires real
    // METFM1 three-dimensional TMET/ZGPT; false retains fail-closed
    // stable behavior until the PTG(1:2) fallback is independently sourced.
    bool use_calmet_profile_lapse=false;
};

struct OriginalPointPrfinResult {
    float ambient_temperature_k=0.0F;
    float mixing_height_m=0.0F;
    int stability_class=0;
    float sqrt_stability_s=0.0F;     // original RLSMET SQRTS for stable PRFIN
    float stack_wind_ms=0.0F, effective_wind_ms=0.0F;
    float release_wind_ms=0.0F;      // WSNEW
    float buoyancy_flux=0.0F, momentum_flux=0.0F;
    float stack_tip_downwash_m=0.0F;
    float x_final_m=0.0F;
    float final_rise_m=0.0F;
    float buoyancy_variance_m2=0.0F; // original POINTS1 BIDSQ=(RISE/3.5)**2
    float effective_height_m=0.0F;   // HEFF
    float mixed_fraction=1.0F;      // FMIX
    float max_layer_height_m=0.0F;   // HMAX
    FinalRise brigg;
    ReleaseCadence release;
};

// The LCALGRD=true stable METFM1 path consumes native REAL4 TMET/ZGPT.
// Unsupported default PTG(1:2), building, and other source branches fail closed.
[[nodiscard]] OriginalPointPrfinResult original_point_prfin_metfm1(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const Calmet21Header& grid,const OriginalPointPrfinRequest& source);
} // namespace cteas::puff
