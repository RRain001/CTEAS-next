#pragma once
#include <vector>

namespace cteas::puff {

// Native REAL*4 translation of CALPUFF 7.2.1 VMASS, original calpuff.for
// lines 11667-11950. Inputs/outputs are the complete per-puff two-layer
// vertical mass state, not original-oracle DGM records.
struct VmassInputs {
    int puff_code=0;          // ICODE; 1..6 puff, 11..16 slug
    int stability_class=0;    // ISTAB (1..6)
    int plume_tilt=0;         // MTILT
    float pbl_height_m=0;     // DPBL
    float height_begin_m=0;   // ZPB
    float height_end_m=0;     // ZPE (slugs only)
    float sigma_z_begin_m=0;  // SIGZB
    float sigma_z_end_m=0;    // SIGZE (slugs only)
    float ziold_m=0;          // ZIOLD
    float zimax_m=0;          // ZIMAX
    std::vector<float> mass_mixed; // QM
    std::vector<float> mass_above; // QU
};
struct VmassResult {
    int puff_code=0;
    float reflecting_lid_m=0; // HLID: passes to COMP after VMASS
    float ziold_m=0;
    float zimax_m=0;
    std::vector<float> mass_mixed;
    std::vector<float> mass_above;
};

// Source-ordered branches 4 / 2,6 / 3,5 stable / 1 / 3 / 5.
// Includes splitting/merging, partial entrainment, and tilt threshold.
// Original VMASS itself does not apply COMP's later max(ZIMAX,HLID).
[[nodiscard]] VmassResult original_vmass(const VmassInputs& input);
} // namespace cteas::puff
