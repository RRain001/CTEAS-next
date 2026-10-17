#pragma once

namespace cteas::puff {

// The REAL*4 variables in original CALPUFF /CURRENT/ consumed by
// PUFFCT2 (calpuff.for L21035-21096). Positions are METRES relative to
// the CALMET computational origin, NOT sampling-grid indices.
// FRACZ1/LUP1 must come from native CTADJ2/SETPUF; inventing them from
// receptor terrain would break the original step history.
struct OriginalPuffct2Step {
    float x_begin_m=0.0F, y_begin_m=0.0F, z_begin_m=0.0F;
    float x_end_m=0.0F, y_end_m=0.0F, z_end_m=0.0F;
    float terrain_fraction=0.0F;   // /CURRENT/ FRACZ1
    bool upslope=false;            // /CURRENT/ LUP1
};
struct OriginalPuffct2Result {
    float x_m=0.0F, y_m=0.0F, z_m=0.0F;
};

// Exact source-ordered standalone PUFFCT2 port. FRAC can extend beyond
// [0,1] because PUFRECS performs FCLIP/extrapolation; do not clamp it.
// This solves receptor-specific puff HEIGHT only, not PUFRECS MCTADJ=2
// pole-height/relief adjustments or CTADJ2 terrain state production.
[[nodiscard]] OriginalPuffct2Result original_puffct2(
    const OriginalPuffct2Step& step, float fraction);

// PUFRECS MCTADJ=2 terrain-specific receptor pole, L5321–5375.
// The caller supplies actual RELIEF/GETELEV terrain values; none are
// inferred from the puff or filled from default zeros.
struct OriginalMctadj2ReceptorTerrain {
    float receptor_ground_elevation_msl=0.0F; // ZRTERR
    float terrain_peak_elevation_msl=0.0F;    // RELIEF(5)
    float terrain_under_puff_msl=0.0F;        // GETELEV(XR1,YR1)
    float brunt_vaisala_s=0.0F;              // BVF
    float wind_speed_ms=0.0F;                // UAVG
    float receptor_height_m=0.0F;            // Z
};
struct OriginalMctadj2ReceptorHeight {
    float puff_height_above_ground_m=0.0F; // ZPR after MTRANS=1
    float pole_height_m=0.0F;              // ZRPOLE
};
[[nodiscard]] OriginalMctadj2ReceptorHeight original_mctadj2_receptor_height(
    const OriginalPuffct2Result& puff_position,
    float gradual_rise_height_m, float final_rise_height_m,
    const OriginalMctadj2ReceptorTerrain& terrain);

} // namespace cteas::puff
