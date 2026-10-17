#pragma once

#include "cteas/puff/original_precision.hpp"
#include <cstddef>
#include <vector>

namespace cteas::puff {

// P7O: the CALPUFF 7.2.1 release scheduler for the locked deck's constant point
// source, transcribed from the unmodified vendor source and cross-checked
// against it by CTest:
//   INJECT          calpuff.for L18561-18696  (release mass split + puff code)
//   POINTS1 cadence calpuff.for L15975-16002  (puffs per hour, emission duration)
//   POINTS1 state   calpuff.for L16120-16176  (release-time state of a new puff)
//   puff age        SWAP L19366 zeroes TMTOTB at release, SETPUF L48718 adds
//                   TSAMP every step
//
// Not reconstructed, and refused by the callers of this module: SETPUF's
// per-step puff update (distances, sigmas, rise table, gravitational settling),
// SWAP/ROLLDN (array management), RLSMET (the wind at the final rise, which the
// cadence uses when the met model provides profiles) and PTLAPS (the met-model
// inversion gradient).

using ReleaseReal = VendorPuffCommonReal;

// The release cadence of one source over one emission hour:
//   NPUFFS = min(max(INT(WSNEW*XTMP1(MD)) + 1, 1), MXNEW);  DT = DHR/NPUFFS
struct ReleaseCadenceInputs {
    double wind_speed_ms = 0.0;          // WSNEW (stack wind, or the wind at final rise)
    double emission_interval = 1.0;      // XTMP1(MD), 1.0 when NSPT1 = 0
    int max_puffs = 99;                  // MXNEW
    double hour_seconds = 3600.0;        // DHR
};

struct ReleaseCadence {
    int puff_count = 0;                  // NPUFFS
    double emission_duration_s = 0.0;    // DT
    int new_puffs = 0;                   // NEWPT1 (doubled for a PRIME cavity source)
};

[[nodiscard]] ReleaseCadence release_cadence(const ReleaseCadenceInputs& inputs);

// INJECT: the release mass split between the mixed layer and the layer above.
struct InjectionInputs {
    int species_count = 0;               // NSPEC
    double emission_duration_s = 0.0;    // DT
    int step_index = 0;                  // MFACT0
    double effective_height_m = 0.0;     // HEFF
    double max_layer_height_m = 0.0;     // HMAX
    double mixing_height_m = 0.0;        // DPBL
    double mass_fraction_mixed = 1.0;    // FMIX
    int stability_class = 0;             // ISTAB
    int gaussian_distribution = 0;       // MGAUSS
    std::vector<double> emission_rate;   // Q(1..NSPEC)
};

struct InjectionResult {
    int puff_code = 0;                   // IPUFFCD
    double unlimited_mixing_height_m = 0.0;  // ZIMAX
    double previous_mixing_height_m = 0.0;   // ZIOLD
    std::vector<double> mixed_layer_mass;    // QM
    std::vector<double> above_layer_mass;    // QU
};

[[nodiscard]] InjectionResult inject_emissions(const InjectionInputs& inputs);

// The release-time state of a new puff (POINTS1 L16120-16176). The fields are
// named after the vendor arrays they are assigned to.
struct NewPuffInputs {
    double source_x_km = 0.0;            // XPT1GRD(I)
    double source_y_km = 0.0;            // YPT1GRD(I)
    double base_elevation_m = 0.0;       // ELSTAK(I)
    double sigma_y_source_m = 0.0;       // SYSRC
    double sigma_z_source_m = 0.0;       // SZSRC
    double effective_height_m = 0.0;     // HEFF
    double x_final_m = 0.0;              // XF
    double final_rise_variance_m2 = 0.0; // BIDSQ
    double buoyancy_flux = 0.0;          // FLUXB
    double momentum_flux = 0.0;          // FLUXM
    double x_final_buoyancy_m = 0.0;     // XFINB
    double x_final_momentum_m = 0.0;     // XFINM
    double z_final_buoyancy_m = 0.0;     // ZFINB
    double z_final_momentum_m = 0.0;     // ZFINM
    double stack_tip_downwash_m = 0.0;   // TIPDW
    double stack_height_m = 0.0;         // HTSTAK(I)
    double exit_velocity_ms = 0.0;       // EXITW(I)
    double diameter_m = 0.0;             // DIAM(I)
    double emission_duration_s = 0.0;    // DT
    double stack_wind_speed_ms = 0.0;    // WS
    int stability_class = 0;             // ISTAB
    double sqrt_stability_s = 0.0;       // SQRTS
    int urban = 0;                       // IRU
    double sigma_v_ms = 0.0;             // TSIGV
    double sigma_w_ms = 0.0;             // TSIGW
    double obukhov_length_m = 0.0;       // EL
    double plume_path_exponent = 0.0;    // PLX
    int downwash_code = 0;               // IDW
    double building_height_m = 0.0;      // HB
    double building_width_m = 0.0;       // HW
    double effective_height2_m = 0.0;    // HEFF2
    double streamline_height_m = 0.0;    // ZLY
    double wake_radius_m = 0.0;          // RINIT
    double wake_xshift_m = 0.0;          // XSHIFT
    double initial_sigma_y_m = 0.0;      // SYINI
    double initial_sigma_z_m = 0.0;      // SZINI
    int release_index = 1;               // J
    int source_index = 1;                // I
    int source_type = 1;                 // ITYPE
};

struct NewPuffState {
    double x_km = 0.0, y_km = 0.0;             // XPB, YPB
    double tibl_height_m = 0.0;                // ZITIBL
    double base_elevation_m = 0.0;             // ELBASE
    double sigma_y_m = 0.0, sigma_z_m = 0.0;   // SIGYB, SIGZB
    double final_height_m = 0.0;               // ZFINAL
    double height_begin_m = 0.0, height_end_m = 0.0;  // ZPB, ZPE
    double x_final_m = 0.0;                    // XFINAL
    double final_rise_variance_m2 = 0.0;       // BIDFNL
    double buoyancy_flux = 0.0, momentum_flux = 0.0;  // FB, FM
    double x_final_buoyancy_m = 0.0, x_final_momentum_m = 0.0;  // XBFIN, XMFIN
    double z_final_buoyancy_m = 0.0, z_final_momentum_m = 0.0;  // ZBFIN, ZMFIN
    double stack_tip_downwash_m = 0.0;         // STIPDW
    int split_flag = 0;                        // ISPLIT
    double stack_height_m = 0.0;               // HT0
    double exit_velocity_ms = 0.0;             // EXITW0
    double diameter_m = 0.0;                   // DIAM0
    double emission_duration_s = 0.0;          // TEMIT0
    double stack_wind_speed_ms = 0.0;          // WS0
    int stability_class = 0;                   // ISTAB0
    double sqrt_stability_s = 0.0;             // SQRTS0
    int urban = 0;                             // IRU0
    double sigma_v_ms = 0.0, sigma_w_ms = 0.0; // SIGV0, SIGW0
    double obukhov_length_m = 0.0;             // EL0
    double plume_path_exponent = 0.0;          // PLEXPO0
    double wind_ratio = 0.0;                   // SRAT0
    int downwash_code = 0;                     // IDW0
    double building_height_m = 0.0, building_width_m = 0.0;  // HB0, HW0
    double effective_height2_m = 0.0;          // HEFF20
    double streamline_height_m = 0.0;          // ZLY0
    double wake_radius_m = 0.0;                // R0
    double wake_xshift_m = 0.0;                // XSHIFT0
    double source_sigma_y_m = 0.0, source_sigma_z_m = 0.0;  // SYSRC0, SZSRC0
    double sigma_y0_m = 0.0, sigma_z0_m = 0.0; // SY0, SZ0
    int release_index = 0;                     // IRLSNUM
    int source_index = 0;                      // ISRCNUM
    int source_type = 0;                       // ISRCTYP
};

[[nodiscard]] NewPuffState new_puff_state(const NewPuffInputs& inputs);

// The vendor age rule: a puff created during the current step starts at age 0
// (SWAP(i,0) zeroes TMTOTB) and SETPUF adds TSAMP every step.
[[nodiscard]] double advance_puff_age(double age_s, double step_s);

} // namespace cteas::puff
