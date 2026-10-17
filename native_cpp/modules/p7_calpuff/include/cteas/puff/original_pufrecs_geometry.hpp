#pragma once

#include <cstddef>

namespace cteas::puff {

// Source-ported CALPUFF 7.2.1 SLGFRAC (calpuff.for L7123-7205).
// All arguments and arithmetic are original REAL*4 in METRES; do not
// mistake the small-length <1.0m threshold for met/sampling grid cells.
struct OriginalSlgfrac {
    float along_m=0.0F;   // RHOA
    float across_m=0.0F;  // RHOC
    float fraction=0.0F;  // FRACS
    float projected_length_m=0.0F; // DXY12, minimum 1.0
    float inverse_length_per_m=0.0F; // RDXY12
};
[[nodiscard]] OriginalSlgfrac original_slgfrac(
    float x_receptor_m,float y_receptor_m,
    float x_end_m,float y_end_m,float x_begin_m,float y_begin_m);

// Scoped original PUFRECS L4946-4985, before the calm / building /
// receptor-specific SIGTY/SIGTZ/GRISE/terrain branches. The public
// interface does not claim full original PUFRECS numerical equivalence.
struct OriginalPufrecsGeometryInputs {
    float x_receptor_m=0.0F,y_receptor_m=0.0F;
    float x_begin_m=0.0F,y_begin_m=0.0F;
    float x_end_m=0.0F,y_end_m=0.0F;
    float sigma_y_begin_m=0.0F,sigma_y_end_m=0.0F;
    float fclip=0.0F;
    float travel_distance_begin_m=0.0F; // XTTB1
    float mean_wind_ms=0.0F; // UAVG, >0 non-calm
    bool clip=false; // LCLIP
};
struct OriginalPufrecsGeometry {
    float fraction=0.0F; // FRAC after clip/source-boundary update
    float along_m=0.0F;  // XR1
    float distance_to_receptor_m=0.0F; // XTT1
    float time_to_receptor_s=0.0F; // TREC
    bool clipped=false;
};
[[nodiscard]] OriginalPufrecsGeometry original_pufrecs_geometry(
    const OriginalPufrecsGeometryInputs& in);

// Convert native CALPUFF MET-grid puff CELLS and sampling-grid integer
// receptor indices to the original REAL*4 PUFRECS geometry in METRES.
// This is an explicit adapter across the PFSAMP/PUFRECS coordinate boundary.
// UAVG and XTTB1 are native COMP outputs, never reconstructed from frozen
// Fortran dump fields. PUFRECS receptor-specific sigma/rise remains separate.
struct OriginalPufrecsGridStepInputs {
    float x_begin_cells=0.0F,y_begin_cells=0.0F;
    float x_end_cells=0.0F,y_end_cells=0.0F;
    float sigma_y_begin_m=0.0F,sigma_y_end_m=0.0F;
    float distance_begin_m=0.0F,mean_wind_ms=0.0F;
    float met_spacing_m=0.0F;
    int ibsamp=0,jbsamp=0,sampling_nx=0,sampling_ny=0;
    float fclip=0.0F;
    bool clip=false;
};
[[nodiscard]] OriginalPufrecsGeometry original_pufrecs_grid_receptor_geometry(
    const OriginalPufrecsGridStepInputs& inputs,
    std::size_t receptor_index);

} // namespace cteas::puff
