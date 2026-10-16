#pragma once

#include <cstddef>
#include <functional>
#include <string>
#include <vector>

namespace cteas::puff {

// P7H: vertical coupling coefficients of CALPUFF 7.2.1, transcribed from the
// unmodified vendor source and cross-checked against it by CTest:
//   VCOUP  calpuff.for L53711-53864  (self-contained reflection/well-mixed kernel)
//   VCBAR  calpuff.for L53866-54088  (per-step space/time average for a puff or slug)
//   CTADJ  calpuff.for L20480-20540  (terrain adjustment of the plume height)
//
// The vendor's terrain *lookup* (GETELEV/GETCELL over the met grid) is NOT
// ported: callers pass a lookup function, and MCTADJ 1/3 fails closed when no
// lookup is supplied. MTILT=1 needs the puff's ZFINAL value, which is part of
// the state below. Everything is REAL*4 in the original and is reproduced here
// in single precision for exact comparison.

using CouplingReal = float;

struct VcoupInputs {
    int puff_code = 0;                 // ICODE (1..6, 11..16, 99)
    double receptor_height_m = 0.0;    // ZR
    double source_height_m = 0.0;      // ZS
    double sigma_z_m = 0.0;            // SZ
    double lid_height_m = 0.0;         // HLID0
    double lid_max_m = 0.0;            // HLIDMAX0 (>= HLID0 for mixed cases)
};

// VCOUP equivalent, in 1/m.
[[nodiscard]] double vertical_coupling(const VcoupInputs& inputs);

// /CURRENT/ and /PUFF/ state VCBAR reads.
struct PuffSampleState {
    int puff_code = 1;                 // ICODE
    double x_begin1 = 0.0, y_begin1 = 0.0, z_begin1 = 0.0, sigma_z_begin1 = 0.0;
    double sigma_z_mid = 0.0;          // SZM1, sigma-z at the middle of the step
    double x_end1 = 0.0, y_end1 = 0.0, z_end1 = 0.0, sigma_z_end1 = 0.0;
    double x_begin2 = 0.0, y_begin2 = 0.0, z_begin2 = 0.0, sigma_z_begin2 = 0.0;
    double x_end2 = 0.0, y_end2 = 0.0, z_end2 = 0.0, sigma_z_end2 = 0.0;
    double time_begin1 = 0.0, time_end1 = 0.0, time_begin2 = 0.0, time_end2 = 0.0;
    double settling_velocity_ms = 0.0; // VSETL
    double final_height_m = 0.0;       // ZFINAL(ip)
};

using CouplingTerrainLookup = std::function<double(double x_km, double y_km)>;

struct VcbarInputs {
    PuffSampleState state;
    bool slug = false;                 // MFACT0 != 0
    double lid_height_m = 0.0;         // HLID
    double plume_path_coefficient = 1.0; // PPCOEF
    bool calm = false;                 // LCALM (the vendor halts when true)
    int terrain_adjustment = 0;        // MCTADJ
    int plume_tilt = 0;                // MTILT
    double grid_spacing_m = 0.0;       // DGRIDI (MCTADJ 1/3 only)
    double stack_height_m = 0.0;       // HT0(ip)
    double stack_base_elevation_m = 0.0; // ELBASE(ip)
    CouplingTerrainLookup terrain;     // GETELEV equivalent (MCTADJ 1/3 only)
};

// VCBAR equivalent, in 1/m.
[[nodiscard]] double vertical_coupling_bar(const VcbarInputs& inputs);

// CTADJ equivalent: adjusted puff height above ground (m).
[[nodiscard]] double terrain_adjustment(double terrain_elevation_m, double height_m,
                                        double stack_height_m, double stack_base_elevation_m,
                                        double plume_path_coefficient, int terrain_adjustment);

} // namespace cteas::puff
