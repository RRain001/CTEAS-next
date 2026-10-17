#pragma once

#include "cteas/puff/original_precision.hpp"

namespace cteas::puff {

// P7X: the inline step integration of COMP (calpuff.for), transcribed from the
// unmodified vendor source and cross-checked against it by CTest:
//   * the sampling cadence   L10136-10147 (old puff) and L10158-10318 (new puff)
//   * the substep length     L10548-10582 (the XSAMLEN constraint)
//   * the position update    L10607-10619 (DX/DY, DISTM, XNEW/YNEW)
// These spans are pinned by reference/p7x_source_anchor.py, which fails the gate
// on drift. Everything is REAL*4 internally, like the vendor.

using StepReal = VendorPuffCommonReal;

struct SamplingCadenceInputs {
    bool new_puff = true;              // IOLD=0 (released during this time step)
    int source_type = 1;               // ISTYPE (only the point source is reconstructed)
    double emission_period_s = 0.0;    // TEMIT0
    double step_seconds = 0.0;         // SECDT
    int release_number = 1;            // IPNO
    double wind_speed_ms = 0.0;        // WS
    double x_sam_len = 1.0;            // XSAMLEN
    double grid_spacing_m = 0.0;       // XGRIDM of the outermost met domain
    int max_sampling_steps = 99;       // MXSAM
};

struct SamplingCadence {
    int sampling_steps = 0;            // NSAM
    int start_substep = 1;             // NSSTR
    int old_flag = 0;                  // IOLD
    double sampling_step_inverse = 0.0;// XSAMI (old puffs only)
    double sampling_step_s = 0.0;      // TSAMP
    double reference_step_s = 0.0;     // REFTSAMP
    bool subsampling = false;          // LSUBSAM
};

[[nodiscard]] SamplingCadence sampling_cadence(const SamplingCadenceInputs& inputs);

struct SubstepInputs {
    double sampling_step_s = 0.0;      // TSAMP entering the substep
    double wind_speed_ms = 0.0;        // WS
    bool puff = true;                  // LPUFF
    bool free_slug = true;             // (LSLUG .AND. IFREE.NE.0)
    bool subsampling = false;          // LSUBSAM
    double grid_spacing_m = 0.0;       // XGRIDM (mdstep)
    double x_sam_len = 1.0;            // XSAMLEN
    int substep_index = 1;             // KSAM
    int sampling_steps = 0;            // NSAM
};

struct Substep {
    double step_s = 0.0;               // the TSAMP actually used
    double step_distance = 1.0;        // FSTEP (grid units)
    bool split = false;
};

[[nodiscard]] Substep substep_length(const SubstepInputs& inputs);

struct AdvanceInputs {
    double x_cells = 0.0;              // XOLD (outermost met grid units)
    double y_cells = 0.0;              // YOLD
    double u_ms = 0.0;                 // UADV
    double v_ms = 0.0;                 // VADV
    double step_s = 0.0;               // TSAMP
    double grid_spacing_m = 0.0;       // the outermost met grid spacing
    double wind_speed_ms = 0.0;        // WS
};

struct Advance {
    double x_cells = 0.0;              // XNEW
    double y_cells = 0.0;              // YNEW
    double dx_cells = 0.0;             // DXOLD
    double dy_cells = 0.0;             // DYOLD
    double distance_m = 0.0;           // DISTM
};

[[nodiscard]] Advance advance_puff(const AdvanceInputs& inputs);

// GETCELL (calpuff.for L82482-82742): the met grid cell and domain holding a
// position. Only the single-domain GRIDIJ path is reconstructed - the deck runs
// one met domain - and the nested-domain and other coordinate-type paths are
// refused instead of approximated.
struct CellLookupInputs {
    double x_cells = 0.0;              // X (GRIDIJ: cell lengths from the domain origin)
    double y_cells = 0.0;              // Y
    double dx_cells = 0.0;             // DX (usually zero)
    double dy_cells = 0.0;             // DY
    int nx = 0;                        // NXM(1)
    int ny = 0;                        // NYM(1)
    int domains = 1;                   // NGRID
    int domain = 1;                    // IDOM
    double nest_factor = 1.0;          // NESTFAC(1)
};

struct CellLookup {
    int i = 0;                         // ICELL
    int j = 0;                         // JCELL
    int domain = 1;                    // KDOM
};

[[nodiscard]] CellLookup grid_cell(const CellLookupInputs& inputs);

// SETPUF's /CURRENT/ coordinate publication (L48673-48723): the step's begin and
// end coordinates in metres, the begin/mid/end heights, and the updated stored
// position. The sigma and virtual-potential-temperature publication that SETPUF
// also performs needs SIGTY/SIGTZ, HEFTRAN, CTADJ2 and WALLTRAP, which are not
// reconstructed here, so only the coordinate part is ported.
struct CurrentCoordinateInputs {
    double x_begin_cells = 0.0;        // XPB
    double y_begin_cells = 0.0;        // YPB
    double z_begin_m = 0.0;            // ZPB
    double x_end_cells = 0.0;          // XNEW
    double y_end_cells = 0.0;          // YNEW
    double grid_spacing_m = 0.0;       // the outermost met grid spacing
    double settling_velocity_ms = 0.0; // VSETL (zero for a gas with no settling)
    double step_s = 0.0;               // TSAMP
};

struct CurrentCoordinates {
    double x_begin_m = 0.0;            // XB1
    double y_begin_m = 0.0;            // YB1
    double z_begin_m = 0.0;            // ZB1
    double x_end_m = 0.0;              // XE1
    double y_end_m = 0.0;              // YE1
    double z_end_m = 0.0;              // ZE1 (after gravitational settling)
    double stored_x_cells = 0.0;       // XPB after the step
    double stored_y_cells = 0.0;       // YPB after the step
    double stored_z_m = 0.0;           // ZPB after the step
};

[[nodiscard]] CurrentCoordinates current_coordinates(const CurrentCoordinateInputs& inputs);

} // namespace cteas::puff
