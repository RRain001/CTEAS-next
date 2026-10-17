#pragma once

#include "cteas/puff/original_precision.hpp"
#include <cstddef>
#include <vector>

namespace cteas::puff {

// P7V: the advection units of CALPUFF 7.2.1, transcribed from the unmodified
// vendor source and cross-checked against it by CTest:
//   ZFIND  calpuff.for L18381-18419  (the layer containing a height)
//   ADVWND calpuff.for L2438-2538    (vertically-averaged wind over a layer)
//   ADVECT calpuff.for L2540-2765    (the advective-wind dispatch)
//   PUFFDZ calpuff.for L2882-3005    (the puff's vertical extent)
//
// ADVECT's METFM=1 path (3-D gridded met: copy the cell's U/V profile and call
// ADVWND) is the locked deck's path. METFM 2/3 (POWLAW) and 4/5 (XTPRF) are
// refused because those routines are not reconstructed. Everything is REAL*4
// internally, like the vendor.

using AdvectionReal = VendorPuffCommonReal;

// ZFIND equivalent: the 1-based layer containing `height_m` in a face-height
// array. `height` below the first face gives 1; above the last face gives
// nz (the vendor returns NZP1-1).
[[nodiscard]] int find_layer(double height_m, const std::vector<double>& face_heights_m);

// ADVWND equivalent: the depth-weighted average wind between zbot and ztop.
struct LayerAverageInputs {
    std::vector<double> u_ms;                  // per layer, 1-based order
    std::vector<double> v_ms;
    std::vector<double> face_heights_m;        // nz + 1 entries
    double z_bottom_m = 0.0;                   // ZBOT
    double z_top_m = 0.0;                      // ZTOP
};

struct LayerAverage {
    double u_ms = 0.0;                         // UAVE
    double v_ms = 0.0;                         // VAVE
};

[[nodiscard]] LayerAverage layer_average_wind(const LayerAverageInputs& inputs);

// ADVECT equivalent for the reconstructed path.
struct AdvectiveWindInputs {
    int met_format = 1;                        // METFM (only 1 is reconstructed)
    std::vector<double> u_profile_ms;          // the cell's U profile (nz entries)
    std::vector<double> v_profile_ms;          // the cell's V profile
    std::vector<double> face_heights_m;        // nz + 1 entries
    double z_bottom_m = 0.0;
    double z_top_m = 0.0;
};

struct AdvectiveWind {
    double u_ms = 0.0;                         // UADV
    double v_ms = 0.0;                         // VADV
};

[[nodiscard]] AdvectiveWind advective_wind(const AdvectiveWindInputs& inputs);

// PUFFDZ equivalent: the puff's vertical extent at the end of the previous step.
struct PuffExtentInputs {
    int puff_code = 1;                         // ICODE
    bool puff = true;                          // LPUFF (false for a slug)
    int stability_class = 0;                   // ISTAB
    double puff_height_m = 0.0;                // HTMET
    double mixing_height_m = 0.0;              // DPBL
    double sigma_z_begin_m = 0.0;              // SIGZB
    double sigma_z_end_m = 0.0;                // SIGZE (slugs only)
    double previous_mixing_height_m = 0.0;     // ZIOLD
    double maximum_mixing_height_m = 0.0;      // ZIMAX
    double layer_bottom_m = 0.0;               // ZFACE(ILAYER)
    double layer_top_m = 0.0;                  // ZFACE(ILAYER+1)
    std::vector<double> mixed_layer_mass;      // QM(1..NSPEC, II)
    std::vector<double> above_layer_mass;      // QU(1..NSPEC, II)
};

struct PuffExtent {
    double z_top_m = 0.0;                      // ZTOP
    double z_bottom_m = 0.0;                   // ZBOT
};

[[nodiscard]] PuffExtent puff_extent(const PuffExtentInputs& inputs);

} // namespace cteas::puff
