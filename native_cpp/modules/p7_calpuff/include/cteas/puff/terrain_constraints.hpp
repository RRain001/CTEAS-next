#pragma once

#include <functional>

namespace cteas::puff {

// P7R: the MCTADJ=2 terrain constraints of CALPUFF 7.2.1, transcribed from the
// unmodified vendor source and cross-checked against it by CTest:
//   CTADJ2   calpuff.for L20542-20835  (strain-induced dispersion adjustment and
//                                       the stable-flow puff-height change)
//   WALLTRAP calpuff.for L21745-21894  (sigma-y limit in narrow valleys)
//
// Both read the gridded terrain state (/GRID/ `relief(5,...)`, `ivalw(...)`,
// `dzval` and /METHD/ `elev`, `xgridm`) through the vendor's `GETCELL`/`GETELEV`
// lookups. Those lookups are explicit dependencies here and a missing one fails
// closed. TRELIEF (L21205-21545), which builds `relief`/`ivalw` from the CALMET
// elevation grid, is NOT reconstructed.
//
// Everything is REAL*4 internally, like the vendor routines.

using TerrainReal = float;

// The terrain state the vendor reads through GETELEV/GETCELL and the /GRID/ and
// /METHD/ arrays.
struct TerrainLookup {
    // GETELEV: bilinear terrain elevation (m MSL) at a met-grid position.
    std::function<double(double x, double y)> elevation_msl;
    // /METHD/ ELEV: the cell elevation (m MSL) at a met-grid position.
    std::function<double(double x, double y)> cell_elevation_msl;
    // /GRID/ RELIEF(corner, cell): directional relief (m) at a met-grid position.
    // Corner 1 = north-south, 2 = north-east/south-west, 3 = east-west,
    // 4 = south-east/north-west, 5 = peak elevation near the trajectory.
    std::function<double(double x, double y, int corner)> relief;
    // /GRID/ IVALW(level, cell): valley width in grid units, or -1 for "none".
    std::function<int(double x, double y, int level)> valley_width;
};

// CTADJ2: the strain adjustment for one step.
struct TerrainStrainInputs {
    double sigma_ratio = 1.0;           // R (sigma-z start / end, pre-strain)
    double puff_height_start_m = 0.0;   // ZPOLD
    double x_old = 0.0, y_old = 0.0;    // met-grid units
    double x_new = 0.0, y_new = 0.0;
    double sigma_z_start_m = 0.0;       // SZOLD
    double brunt_vaisala_s = 0.0;       // BVF
    double wind_speed_ms = 0.0;         // WS
    double grid_spacing_m = 0.0;        // DGRID
};

struct TerrainStrain {
    double strain = 1.0;                // STRAIN
    double puff_height_end_m = 0.0;     // ZPNEW
    double fraction_beyond = 0.0;       // FRACZ
    bool upslope = false;               // LUP
};

[[nodiscard]] TerrainStrain terrain_strain(const TerrainStrainInputs& inputs,
                                           const TerrainLookup& terrain);

// WALLTRAP: the valley constraint on sigma-y.
struct WallTrapInputs {
    double sigma_y_begin_m = 0.0;       // SYB
    double sigma_y_end_m = 0.0;         // SYE (revised in place by the vendor)
    double puff_height_m = 0.0;         // Z
    double x_begin = 0.0, y_begin = 0.0;
    double x_end = 0.0, y_end = 0.0;
    double brunt_vaisala_s = 0.0;       // BVF
    double wind_speed_ms = 0.0;         // WS
    double valley_layer_thickness_m = 0.0;   // DZVAL
    double grid_spacing_m = 0.0;             // XGRIDM
    int max_valley_levels = 10;              // MXVALZ
};

struct WallTrap {
    double sigma_y_end_m = 0.0;         // SYE after the constraint
    bool trapped = false;               // ITRAP == 1
};

[[nodiscard]] WallTrap wall_trap(const WallTrapInputs& inputs, const TerrainLookup& terrain);

} // namespace cteas::puff
