#pragma once

#include "cteas/puff/ctsg.hpp"
#include "cteas/puff/original_precision.hpp"

namespace cteas::puff {

// P7P: the per-step bookkeeping of CALPUFF 7.2.1's SETPUF, transcribed from the
// unmodified vendor source and cross-checked against it by CTest:
//   SETPUF step bookkeeping  calpuff.for L48373-48399 (distances, travel times,
//                            mean transport speed and the CALM determination)
//   SETPUF state update      calpuff.for L48706-48723 (gravitational settling,
//                            the total distance/time counters, end-of-step
//                            position)
//   SETCSIG                  calpuff.for L52504-52619 (the /CSIGMA/ selection
//                            state and the Heffter transition time)
//
// SETPUF's sigma computation (the SIGTY/SIGTZ calls with their virtuals), the
// rise-table/WAKE_TAB handling, the MCTADJ=2 height adjustment (CTADJ2) and the
// PRIME wake treatment are NOT reconstructed; the callers of this module refuse
// them. The vendor keeps its state in REAL*4, so everything here is REAL*4
// internally and converts to double only in the reported results.

using StepReal = VendorPuffCommonReal;

// The step bookkeeping block (SETPUF L48373-48399).
struct StepBookkeepingInputs {
    double total_distance_m = 0.0;      // XTOTB(II)
    double total_time_s = 0.0;          // TMTOTB(II)
    double step_distance_m = 0.0;       // DISTM
    double step_seconds = 0.0;          // TSAMP
    double km_per_m = 0.0;              // DM2KM
    double wind_speed_ms = 0.0;         // WS
    double calm_wind_threshold = 0.0;   // WSCALM
    int downwash_code = 0;              // IDW0(II)
    double x_final_m = 0.0;             // XFINAL(II)
    int dispersion_y_option = 3;        // IDOPTY
    int dispersion_z_option = 3;        // IDOPTZ
};

struct StepBookkeeping {
    double distance_begin_m = 0.0;      // XTTB1
    double distance_end_m = 0.0;        // XTTE1
    double time_begin_s = 0.0;          // TB1
    double time_end_s = 0.0;            // TE1
    double mid_distance_km = 0.0;       // DMIDKM
    double mid_time_s = 0.0;            // TMID
    double mean_speed_ms = 0.0;         // UAVG
    double speed_kps = 0.0;             // UKPS
    bool calm = false;                  // LCALM
    int dispersion_y_option = 0;        // IDOPTY (overridden in a calm hour)
    int dispersion_z_option = 0;        // IDOPTZ
    int downwash_code = 0;              // IDW0(II)
    double x_final_m = 0.0;             // XFINAL(II)
};

[[nodiscard]] StepBookkeeping step_bookkeeping(const StepBookkeepingInputs& inputs);

// The state-update block (SETPUF L48706-48723).
struct StepUpdateInputs {
    double height_end_m = 0.0;          // ZE1
    double settling_velocity_ms = 0.0;  // VGRAV(1,1)
    int plume_tilt = 0;                 // MTILT
    double step_seconds = 0.0;          // TSAMP
    double step_distance_m = 0.0;       // DISTM
    double total_distance_m = 0.0;      // XTOTB(II)
    double total_time_s = 0.0;          // TMTOTB(II)
    double x_new_km = 0.0;              // XNEW
    double y_new_km = 0.0;              // YNEW
};

struct StepUpdate {
    double height_end_m = 0.0;          // ZE1 after settling
    double total_distance_m = 0.0;      // XTOTB(II) after the step
    double total_time_s = 0.0;          // TMTOTB(II) after the step
    double x_km = 0.0;                  // XPB
    double y_km = 0.0;                  // YPB
    double z_km = 0.0;                  // ZPB
};

[[nodiscard]] StepUpdate apply_step_update(const StepUpdateInputs& inputs);

// SETCSIG: the /CSIGMA/ selection state.
struct SigmaParameterInputs {
    int dispersion_y_option = 3;        // IDOPTY
    int dispersion_z_option = 3;        // IDOPTZ
    int urban = 0;                      // IRU
    double mean_speed_ms = 0.0;         // UAVG
    int stability_class = 4;            // KST (conditioned to <= 6)
    double obukhov_length_m = 0.0;      // EL
    double brunt_vaisala_s = 0.0;       // BVF
    double sigma_v_ms = 0.0;            // TSIGV
    double sigma_w_ms = 0.0;            // TSIGW
    double min_sigma_y_m = 0.0;         // SYMIN
    double min_sigma_z_m = 0.0;         // SZMIN
    double height_m = 0.0;              // ZHT
    double mixing_height_m = 0.0;       // ZMIX
    int cell_x = 0;                     // IX
    int cell_y = 0;                     // IY
    int met_domain = 0;                 // MD
    int heffter_sigma_z = 0;            // MHFTSZ (from /FLAGS/)
    int tau_ly = 0;                     // MTAULY (from /FLAGS/); 1 is refused
    double sigma_y_heffter_m = 300.0;   // SYH (/CSIGMA/, BLOCK DATA value 300)
};

struct SigmaParameterState {
    int dispersion_y_option = 0;        // IDOPTYS
    int dispersion_z_option = 0;        // IDOPTZS
    int urban = 0;                      // IRUS
    double mean_speed_ms = 0.0;         // UAVGS
    int stability_class = 0;            // KSTABS
    double obukhov_length_m = 0.0;      // ELS
    double brunt_vaisala_s = 0.0;       // BVFS
    int heffter_sigma_z = 0;            // MHFTSZS
    double sigma_v_ms = 0.0;            // TSIGVS
    double sigma_w_ms = 0.0;            // TSIGWS
    double min_sigma_y_m = 0.0;         // SYMINS
    double min_sigma_z_m = 0.0;         // SZMINS
    int cell_x = 0;                     // IXCELL
    int cell_y = 0;                     // IYCELL
    int met_domain = 0;                 // MDCELL
    double sigma_z_heffter_m = 0.0;     // SZH (= SYH)
    double heffter_transition_time_s = 0.0;      // THFTY
    double heffter_transition_distance_km = 0.0; // DHFTY
    double tau_inverse = 0.0;           // TYIDR (only with MTAULY = 1)
};

// SETCSIG equivalent. The SIGTY call that produces the Heffter transition pair
// is an explicit dependency (the vendor curves themselves carry the P7D parity
// evidence), and MTAULY = 1 is refused because TAULY is not reconstructed.
[[nodiscard]] SigmaParameterState set_sigma_parameters(const SigmaParameterInputs& inputs,
                                                       const SigmaYCurve& sigma_y_curve);

} // namespace cteas::puff
