#pragma once

#include "cteas/puff/control.hpp"

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace cteas::puff {

// P7F: CALPUFF 7.2.1 MDRY = 1 dry deposition, restricted to the species
// methods the selected real case uses.
//
// The selected deck (`project/cases/hefei5km_2022_reference_case_20261011`)
// models two species: H-3 with the computed-gas resistance model (method 1)
// and HE-3 with no dry removal (method 0). The resistance network, the
// time-invariant parameters and the uniformly-mixed removal fraction are
// transcribed from the unmodified vendor source
// engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for (VDCOMP, DRYI, DRY and
// the /DRYGAS/ BLOCK DATA constants) and are cross-checked against that file
// and against the compiled vendor routines by CTest.
//
// Deliberately refused, fail closed: MDRY other than 1, particle deposition
// (method 2, needs DRYI/VDP1 size-distribution physics), user-specified
// diurnal deposition velocities (method 3, needs the RDVD input table), the
// Gaussian-puff removal branch (needs the VCBar vertical coupling coefficient),
// and any species list that disagrees with the gas-parameter table.
//
// As in P7D the original REAL*4 state is reproduced on purpose, so results can
// be compared with the vendor routines at float32 level.

using DryDepositionReal = float;

enum class DryDepositionMethod : int {
    none = 0,                 // IDRYFLG = 0, no dry removal
    gas_resistance = 1,       // IDRYFLG = 1, VDCOMP resistance model for gases
    particle_resistance = 2,  // IDRYFLG = 2, not reconstructed
    user_specified = 3,       // IDRYFLG = 3, not reconstructed
};

[[nodiscard]] DryDepositionMethod require_supported_dry_deposition_method(int method,
                                                                         const std::string& species);

// Input Group 7 entry (units exactly as entered in the control file).
struct GasDepositionParameters {
    double diffusivity_cm2_s = 0.0;          // DIFFUSIVITY
    double alpha_star = 0.0;                 // ALPHA STAR
    double reactivity = 0.0;                 // REACTIVITY
    double mesophyll_resistance_s_cm = 0.0;  // MESOPHYLL RESISTANCE
    double henry_law_coefficient = 0.0;      // HENRY'S LAW COEFFICIENT
};

struct DryDepositionSpecies {
    std::string name;                                   // CSPEC / group 3a name
    int modeled = 0;                                    // group 3a column 1
    int emitted = 0;                                    // group 3a column 2
    DryDepositionMethod method = DryDepositionMethod::none; // group 3a column 3
    int output_group = 0;                               // group 3a column 4
    GasDepositionParameters gas;                        // group 7
    bool has_gas_parameters = false;
};

// DRYI-derived, SI-unit dry deposition parameters plus the input group 9
// reference values.
struct DryDepositionSetup {
    std::vector<DryDepositionSpecies> species;
    int deposited_species = 0;                  // NSDD
    double reference_height_m = 0.0;            // ZREF = min(0.5*(ZFACE1+ZFACE2), 10)
    double reference_cuticle_resistance_s_m = 0.0; // RCUTR (s/cm -> s/m)
    double reference_ground_resistance_s_m = 0.0;  // RGR (s/cm -> s/m)
    double reference_reactivity = 0.0;          // REACTR
    double vegetation_state = 1.0;              // IVEG
    int particle_intervals = 9;                 // NINT (recorded, unused)
    // /DRYGAS/ constants, transcribed from the vendor BLOCK DATA.
    double stomatal_constant = 2.3e-8;          // PCONST
    double stomatal_opening_max_m = 2.5e-6;     // BMAX
    double stomatal_opening_min_m = 1.0e-7;     // BMIN
    double radiation_max_w_m2 = 600.0;          // QSWMAX
    double schmidt_coefficient = 2.0;           // DCONST1
    double schmidt_exponent = 0.6666667;        // DCONST2
    double water_transfer_constant = 4.8e-4;    // DCONST3
    double air_viscosity_m2_s = 0.15e-4;        // VAIR (DRYI)
    double von_karman = 0.4;                    // VK (VDCOMP/DRYI)
    // Per-species DRYI outputs (SI units, indexed like `species`).
    std::vector<double> diffusivity_m2_s;       // PDIFF
    std::vector<double> mesophyll_resistance_s_m; // RM
    std::vector<double> cuticle_resistance_s_m; // RCUT
    std::vector<double> ground_resistance_s_m;  // RGG
    std::vector<double> water_ground_term_s_m;  // RGW1
    std::vector<double> deposition_layer_term;  // RD1
};

// Parses input group 3a (species list), group 7 (gas parameters) and group 9
// (miscellaneous dry deposition parameters) from the control text. Fails closed
// on an unsupported method, a missing gas parameter row for a gas species, a
// species-name mismatch with CSPEC, illegal reference values, and MDRY != 1.
[[nodiscard]] DryDepositionSetup dry_deposition_setup_from_control(const std::string& control_text);

// DRYI equivalents: unit conversions and the time-invariant per-species
// parameters (PDIFF, RM, RD1, RCUT, RGG, RGW1) for every COMPUTED-GAS species.
// `dry_deposition_setup_from_control` calls it; the oracle parity harness uses
// it to drive the resistance model with arbitrary reference values.
void finalize_dry_deposition_setup(DryDepositionSetup& setup);

// Per-cell and per-puff state needed by the resistance model.
struct DryDepositionEnvironment {
    double u10_ms = 0.0;                 // U10 (water roughness only)
    double v10_ms = 0.0;                 // V10
    int land_use = 0;                    // ILU (negative = irrigated)
    int water_category_low = 500;        // IWAT1 (vendor default from the LU header)
    int water_category_high = 599;       // IWAT2
    double roughness_m = 0.0;            // Z0 of the cell
    double temperature_k = 0.0;          // TEMPK
    double friction_velocity_ms = 0.0;   // USTAR
    double monin_obukhov_m = 0.0;        // XMONIN
    double leaf_area_index = 0.0;        // XLAI
    double shortwave_w_m2 = 0.0;         // QSW
    int vegetation_state = 1;            // IVEG after the water/irrigated override
};

struct DryDepositionStep {
    std::vector<double> velocity_ms;         // VD(nspec)
    // Exact source-ordered VDCOMP REAL4 component resistances retained
    // for independent original-vs-native precision diagnostics only.
    std::vector<double> deposition_layer_resistance_s_m; // RD
    std::vector<double> canopy_resistance_s_m;           // RC
    std::vector<double> foliage_resistance_s_m;          // RF
    std::vector<double> ground_resistance_s_m;           // RG
    std::vector<double> cuticle_resistance_s_m;          // RCUT
    double source_leaf_area_index=0.0;                   // XLAI
    std::vector<double> boundary_ratio;      // VDPVD(nspec)
    std::vector<double> fraction_remaining;  // FRACDRY(nspec)
    double boundary_diffusivity_m2_s = 0.0;  // DIFFK
    bool water_cell = false;
    double effective_roughness_m = 0.0;      // Z0M
    double psi_heat = 0.0;                   // PSIH
    double atmospheric_resistance_s_m = 0.0; // RA
    int vegetation_state = 1;
};

// VDCOMP equivalent plus the uniformly-mixed removal branch of DRY:
//   fracdry = exp(-vdpvd*vd*dt/lid_height)
// The Gaussian-puff branch (VCBar) is not reconstructed and is refused by the
// caller contract of this function (uniform puffs only).
[[nodiscard]] DryDepositionStep dry_deposition_step(const DryDepositionSetup& setup,
                                                   const DryDepositionEnvironment& environment,
                                                   double lid_height_m, double sampling_step_s,
                                                   double mixing_height_m, double wstar_ms);

// Original DRY calpuff.for L26198–26276 Gaussian puff branch. The
// resistance calculations (VDCOMP) are provided by dry_deposition_step,
// but that older helper's uniform FRACDRY and uniform-only VDPVD
// ratio must NOT be applied to Gaussian puff QM: original DRY keeps
// VDPVD=1, calls VCBAR after SETPUF and uses a different exponent. VCBAR is explicitly input from native P7H (not oracle DGM).
// Only Gaussian codes 1/3/5 (or 11/13/15 slugs) and skipped 4/14/99
// are represented; uniform 2/6/12/16 belong to the other DRY branch.
struct OriginalDryMassResult {
    std::vector<float> fraction_remaining;
    std::vector<float> mixed_mass_after;
    std::vector<float> removed_mass;
    float vcbar_m_inverse=0.0F;
};
using OriginalGaussianDryResult=OriginalDryMassResult;
[[nodiscard]] OriginalGaussianDryResult original_gaussian_dry_mass(
    const DryDepositionStep& resistance, int puff_code,
    float sampling_step_s, float native_vcbar_m_inverse,
    const std::vector<float>& mixed_mass_before);

// Original DRY L26227–26274 uniformly mixed ICODE2/6 uses the
// VDPVD diffusion boundary ratio from VDCOMP and TSAMP/HLID. ICODE4/99
// bypasses both VD and mass changes. The input DRY step contains the
// original REAL4 VDCOMP+uniform removal factors, not Gaussian VCBAR.
[[nodiscard]] OriginalDryMassResult original_uniform_dry_mass(
    const DryDepositionStep& resistance, int puff_code,
    const std::vector<float>& mixed_mass_before);

// Case-level audit: method per species, which options are effective, and the
// derived gas parameters, for CI evidence and docs.
struct DryDepositionAudit {
    int mdry = 1;
    double reference_height_m = 0.0;
    double reference_cuticle_resistance_s_m = 0.0;
    double reference_ground_resistance_s_m = 0.0;
    double reference_reactivity = 0.0;
    int vegetation_state = 1;
    int deposited_species = 0;
    std::vector<std::string> gas_species;
    std::vector<std::string> non_deposited_species;
    std::vector<std::string> unsupported_species;
    std::string note;
};

// Same parsing as dry_deposition_setup_from_control, but returns the audit and
// refuses nothing except invalid input: unsupported methods are reported as
// unsupported instead of aborting, so a case can be triaged before running.
[[nodiscard]] DryDepositionAudit audit_dry_deposition(const std::string& control_text);

} // namespace cteas::puff
