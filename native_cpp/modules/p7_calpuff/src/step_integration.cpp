#include "cteas/puff/step_integration.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = StepReal;

constexpr R kZero = 0.0F;
constexpr R kOne = 1.0F;
constexpr R kHalf = 0.5F;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7X step integration: " + message);
}

R to_real(double value, const char* what) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(std::string("P7X step integration: ") + what +
                                    " must be finite");
    }
    return static_cast<R>(value);
}

} // namespace

SamplingCadence sampling_cadence(const SamplingCadenceInputs& inputs) {
    // COMP L10136-10147 (old puff) and L10158-10318 (new puff), REAL*4.
    require_true(inputs.step_seconds > 0.0, "SECDT must be positive");
    require_true(inputs.grid_spacing_m > 0.0, "the met grid spacing must be positive");
    require_true(inputs.max_sampling_steps >= 1, "MXSAM must be at least 1");
    const R secdt = to_real(inputs.step_seconds, "SECDT");
    const R spacing = to_real(inputs.grid_spacing_m, "the grid spacing");
    const R x_sam_len = to_real(inputs.x_sam_len, "XSAMLEN");
    require_true(x_sam_len > kOne - kHalf, "XSAMLEN must be positive");

    SamplingCadence cadence;
    if (!inputs.new_puff) {
        // Old puff: the number of sampling steps follows the distance the puff
        // would travel in one time step, in local grid units.
        cadence.old_flag = 1;
        const R ws = to_real(inputs.wind_speed_ms, "WS");
        const R smxi2 = secdt * (kOne / x_sam_len) * (kOne / spacing);
        R nsam = std::round(ws * smxi2 + kOne);
        nsam = std::min(nsam, static_cast<R>(inputs.max_sampling_steps));
        cadence.sampling_steps = static_cast<int>(nsam);
        require_true(cadence.sampling_steps >= 1, "the sampling-step count must be positive");
        cadence.sampling_step_inverse = static_cast<double>(kOne / static_cast<R>(
            cadence.sampling_steps));
        cadence.start_substep = 1;
        cadence.sampling_step_s = static_cast<double>(secdt *
                                                      static_cast<R>(cadence.sampling_step_inverse));
    } else {
        // New puff: the vendor only reconstructs the constant point-source path
        // (ISTYPE=1) and refuses the variable-emission, area, line and road
        // source paths, whose cadence comes from VARSAM and friends.
        require_true(inputs.source_type == 1,
                     "only ISTYPE=1 (a point source with a constant emission period) is "
                     "reconstructed; the other source types need VARSAM/NEWAR1/NEWLN1/NEWVL1/"
                     "NEWBC/NEWRD1, which are not reconstructed");
        require_true(inputs.emission_period_s > 0.0, "TEMIT0 must be positive");
        const R temit0 = to_real(inputs.emission_period_s, "TEMIT0");
        R nsam = std::round(secdt / temit0);
        require_true(nsam >= kOne, "the sampling-step count must be positive");
        cadence.sampling_steps = static_cast<int>(nsam);
        cadence.start_substep = inputs.release_number;
        cadence.old_flag = 0;
        cadence.sampling_step_s = static_cast<double>(temit0);
    }
    cadence.reference_step_s = cadence.sampling_step_s;
    // The vendor stops using substeps once NSAM reaches MXSAM.
    cadence.subsampling = cadence.sampling_steps < inputs.max_sampling_steps;
    return cadence;
}

Substep substep_length(const SubstepInputs& inputs) {
    // COMP L10548-10582, REAL*4.
    require_true(inputs.sampling_step_s > 0.0, "TSAMP must be positive");
    require_true(inputs.grid_spacing_m > 0.0, "the met grid spacing must be positive");
    require_true(inputs.sampling_steps >= 1, "NSAM must be at least 1");
    const R ws = to_real(inputs.wind_speed_ms, "WS");
    R tsamp = to_real(inputs.sampling_step_s, "TSAMP");
    const R xgridmi = kOne / to_real(inputs.grid_spacing_m, "the grid spacing");
    const R xsamleni = kOne / to_real(inputs.x_sam_len, "XSAMLEN");

    Substep result;
    result.step_distance = kOne;
    const bool emitted_now = inputs.puff || inputs.free_slug;
    if (emitted_now && inputs.subsampling) {
        // The step distance in local grid units must not exceed XSAMLEN.
        const R fstep = ws * tsamp * xgridmi * xsamleni;
        result.step_distance = static_cast<double>(fstep);
        if (fstep > kOne) {
            if (fstep >= 2.0F || inputs.substep_index < inputs.sampling_steps) {
                // Take a full XSAMLEN this sub-step.
                tsamp = tsamp / fstep;
            } else {
                // The last step with 1 < FSTEP < 2 is split in two equal halves.
                tsamp = kHalf * tsamp;
            }
            result.split = true;
        }
    }
    result.step_s = static_cast<double>(tsamp);
    return result;
}

Advance advance_puff(const AdvanceInputs& inputs) {
    // COMP L10607-10619, REAL*4. Positions are in the outermost met grid units.
    require_true(inputs.grid_spacing_m > 0.0, "the met grid spacing must be positive");
    require_true(inputs.step_s > 0.0, "the step length must be positive");
    const R uadv = to_real(inputs.u_ms, "UADV");
    const R vadv = to_real(inputs.v_ms, "VADV");
    const R tsamp = to_real(inputs.step_s, "TSAMP");
    const R ws = to_real(inputs.wind_speed_ms, "WS");
    const R spacing = to_real(inputs.grid_spacing_m, "the grid spacing");

    // First in meters, then in met grid units.
    const R dxoldm = uadv * tsamp;
    const R dyoldm = vadv * tsamp;
    const R distance = ws * tsamp;
    // COMP (original XGRIDMI): compute the inverse grid spacing ONCE in
    // original REAL*4, then multiply each metre displacement by XGRIDMI.
    // A mathematically equivalent 'dxoldm / spacing' changes the rounding
    // sequence and diverges from unmodified Fortran by one ULP at locked
    // Hefei 2022 DGM record 1685 (hour 2, puff 55, YNEW).
    const R xgridmi = kOne / spacing;
    const R dxmold = dxoldm * xgridmi;
    const R dymold = dyoldm * xgridmi;
    Advance advance;
    advance.dx_cells = static_cast<double>(dxmold);
    advance.dy_cells = static_cast<double>(dymold);
    advance.distance_m = static_cast<double>(distance);
    advance.x_cells = static_cast<double>(to_real(inputs.x_cells, "XOLD") + dxmold);
    advance.y_cells = static_cast<double>(to_real(inputs.y_cells, "YOLD") + dymold);
    return advance;
}

CellLookup grid_cell(const CellLookupInputs& inputs) {
    // GETCELL L82559-82720, REAL*4, the single-domain GRIDIJ path.
    require_true(inputs.domains == 1,
                 "only one met domain is reconstructed; nested domains need the "
                 "GRIDNEST plumbing, which is not reconstructed");
    require_true(inputs.domain == 1, "only met domain 1 is reconstructed");
    require_true(inputs.nx > 0 && inputs.ny > 0, "the domain must have cells");
    require_true(inputs.nest_factor > 0.0, "the nesting factor must be positive");
    const R delta1 = kHalf / to_real(inputs.nest_factor, "the nesting factor");
    R x1 = to_real(inputs.x_cells, "x");
    R y1 = to_real(inputs.y_cells, "y");
    const R dx1 = to_real(inputs.dx_cells, "dx");
    const R dy1 = to_real(inputs.dy_cells, "dy");
    // Keep a location that leaves the outer domain just inside its border.
    x1 = std::min(x1, static_cast<R>(inputs.nx) - delta1 - dx1);
    x1 = std::max(x1, kZero - dx1);
    y1 = std::min(y1, static_cast<R>(inputs.ny) - delta1 - dy1);
    y1 = std::max(y1, kZero - dy1);

    // The single-domain loop: the cell index is the truncated coordinate plus one.
    CellLookup lookup;
    lookup.domain = 1;
    const R xk = x1;
    const R yk = y1;
    require_true(xk + dx1 >= kZero && yk + dy1 >= kZero,
                 "the vendor halts when no valid cell is found for the location");
    lookup.i = static_cast<int>(xk + dx1) + 1;
    lookup.j = static_cast<int>(yk + dy1) + 1;
    require_true(lookup.i >= 1 && lookup.i <= inputs.nx && lookup.j >= 1 &&
                     lookup.j <= inputs.ny,
                 "the vendor halts when no valid cell is found for the location");

    // Final adjustment with the full precision of the input data.
    R ix0 = to_real(inputs.x_cells, "x") + dx1 + kOne;
    R iy0 = to_real(inputs.y_cells, "y") + dy1 + kOne;
    ix0 = std::max(kOne, ix0);
    iy0 = std::max(kOne, iy0);
    lookup.i = std::min(static_cast<int>(ix0), inputs.nx);
    lookup.j = std::min(static_cast<int>(iy0), inputs.ny);
    return lookup;
}

CurrentCoordinates current_coordinates(const CurrentCoordinateInputs& inputs) {
    // SETPUF L48673-48723, REAL*4. Puff coordinates in /CURRENT/ are metres.
    require_true(inputs.grid_spacing_m > 0.0, "the met grid spacing must be positive");
    const R spacing = to_real(inputs.grid_spacing_m, "the grid spacing");
    const R x_begin = to_real(inputs.x_begin_cells, "XPB");
    const R y_begin = to_real(inputs.y_begin_cells, "YPB");
    const R z_begin = to_real(inputs.z_begin_m, "ZPB");
    const R x_end = to_real(inputs.x_end_cells, "XNEW");
    const R y_end = to_real(inputs.y_end_cells, "YNEW");
    const R settling = to_real(inputs.settling_velocity_ms, "VSETL");
    const R tsamp = to_real(inputs.step_s, "TSAMP");
    require_true(tsamp > 0.0, "the step length must be positive");
    require_true(settling >= 0.0, "the settling velocity must not be negative");

    CurrentCoordinates result;
    result.x_begin_m = static_cast<double>(x_begin * spacing);
    result.y_begin_m = static_cast<double>(y_begin * spacing);
    result.z_begin_m = static_cast<double>(z_begin);
    result.x_end_m = static_cast<double>(x_end * spacing);
    result.y_end_m = static_cast<double>(y_end * spacing);
    // The end height drops with gravitational settling, floored at the ground.
    R z_end = z_begin - settling * tsamp;
    z_end = std::max(z_end, kZero);
    result.z_end_m = static_cast<double>(z_end);
    result.stored_x_cells = static_cast<double>(x_end);
    result.stored_y_cells = static_cast<double>(y_end);
    result.stored_z_m = static_cast<double>(z_end);
    return result;
}

} // namespace cteas::puff
