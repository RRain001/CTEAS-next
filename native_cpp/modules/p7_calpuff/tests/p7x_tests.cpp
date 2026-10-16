// P7X contract test: the ported step integration against hand-computed vendor
// semantics, plus every fail-closed refusal.
#include "cteas/puff/step_integration.hpp"

#include <bit>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

int failures = 0;
int checks = 0;

void check(bool condition, const std::string& what) {
    ++checks;
    if (!condition) {
        ++failures;
        std::cerr << "FAIL: " << what << '\n';
    }
}

void check_close(double got, double want, double tolerance, const std::string& what) {
    ++checks;
    if (!(std::abs(got - want) <= tolerance)) {
        ++failures;
        std::cerr << "FAIL: " << what << " got=" << got << " want=" << want << '\n';
    }
}

template <typename Callable>
void check_refuses(Callable&& callable, const std::string& what) {
    ++checks;
    try {
        callable();
        ++failures;
        std::cerr << "FAIL: " << what << " did not refuse\n";
    } catch (const std::invalid_argument&) {
        // expected
    }
}

} // namespace

int main() {
    using namespace cteas::puff;

    // New point-source puff: NSAM = NINT(SECDT/TEMIT0), TSAMP = TEMIT0, NSSTR = IPNO.
    SamplingCadenceInputs cadence;
    cadence.new_puff = true;
    cadence.source_type = 1;
    cadence.emission_period_s = 3600.0 / 54.0;
    cadence.step_seconds = 3600.0;
    cadence.release_number = 1;
    cadence.grid_spacing_m = 100.0;
    auto computed = sampling_cadence(cadence);
    check(computed.sampling_steps == 54, "new puff NSAM = NINT(SECDT/TEMIT0)");
    check_close(computed.sampling_step_s, 3600.0 / 54.0, 1.0e-3, "new puff TSAMP = TEMIT0");
    check_close(computed.reference_step_s, computed.sampling_step_s, 1.0e-9, "REFTSAMP = TSAMP");
    check(computed.start_substep == 1, "NSSTR = IPNO");
    check(computed.old_flag == 0, "IOLD = 0 for a new puff");
    check(computed.subsampling, "LSUBSAM holds while NSAM < MXSAM");
    cadence.release_number = 7;
    check(sampling_cadence(cadence).start_substep == 7, "NSSTR follows IPNO");

    // Old puff: NSAM = NINT(WS*SECDT/(XSAMLEN*XGRIDM) + 1), clamped by MXSAM.
    SamplingCadenceInputs old;
    old.new_puff = false;
    old.step_seconds = 3600.0;
    old.wind_speed_ms = 1.5;
    old.grid_spacing_m = 100.0;
    old.x_sam_len = 1.0;
    computed = sampling_cadence(old);
    // SMXI2 = SECDT/(XSAMLEN*XGRIDM) = 36, so NSAM = NINT(1.5*36+1) = 55.
    check(computed.sampling_steps == 55, "old puff NSAM = NINT(WS*SMXI2 + 1)");
    check_close(computed.sampling_step_inverse, 1.0 / 55.0, 1.0e-6, "old puff XSAMI = 1/NSAM");
    check_close(computed.sampling_step_s, 3600.0 / 55.0, 1.0e-2, "old puff TSAMP = SECDT*XSAMI");
    check(computed.start_substep == 1, "old puffs start at substep 1");
    check(computed.subsampling, "LSUBSAM holds while NSAM < MXSAM");
    old.wind_speed_ms = 0.01;   // NSAM = NINT(0.01*36+1) = 1
    computed = sampling_cadence(old);
    check(computed.sampling_steps == 1, "old puff NSAM floors at 1");
    check_close(computed.sampling_step_s, 3600.0, 1.0e-2, "old puff TSAMP = SECDT/NSAM");
    old.wind_speed_ms = 100.0;  // NSAM = NINT(100*36+1) -> clamped by MXSAM
    computed = sampling_cadence(old);
    check(computed.sampling_steps == 99, "old puff NSAM is clamped by MXSAM");
    check(!computed.subsampling, "LSUBSAM is off once NSAM reaches MXSAM");

    // Substep length: FSTEP = WS*TSAMP/(XSAMLEN*XGRIDM).
    SubstepInputs substep;
    substep.sampling_step_s = 3600.0 / 54.0;
    substep.wind_speed_ms = 1.5;
    substep.puff = true;
    substep.subsampling = true;
    substep.grid_spacing_m = 100.0;
    substep.x_sam_len = 1.0;
    substep.substep_index = 1;
    substep.sampling_steps = 54;
    auto step = substep_length(substep);
    check_close(step.step_distance, 1.0, 1.0e-5, "FSTEP for the deck's first substep");
    check(!step.split, "no split when FSTEP <= 1");
    check_close(step.step_s, 3600.0 / 54.0, 1.0e-3, "the substep keeps TSAMP");

    substep.wind_speed_ms = 3.0;      // FSTEP = 2.0 -> a full XSAMLEN substep
    step = substep_length(substep);
    check(step.split, "FSTEP >= 2 splits the substep");
    check_close(step.step_s, (3600.0 / 54.0) / 2.0, 1.0e-2, "TSAMP is divided by FSTEP");

    substep.wind_speed_ms = 2.25;     // FSTEP = 1.5, last substep -> two halves
    substep.substep_index = 54;
    substep.sampling_steps = 54;
    step = substep_length(substep);
    check(step.split, "1 < FSTEP < 2 on the last substep splits");
    check_close(step.step_s, 0.5 * (3600.0 / 54.0), 1.0e-2, "the last substep halves TSAMP");

    substep.substep_index = 10;       // not the last substep -> a full XSAMLEN
    step = substep_length(substep);
    check_close(step.step_s, (3600.0 / 54.0) / 1.5, 1.0e-2, "a non-final substep divides by FSTEP");

    // An emitted-now slug is not altered; a non-subsampled step is not either.
    substep.free_slug = true;
    substep.puff = false;
    substep.wind_speed_ms = 3.0;
    check(substep_length(substep).split, "a free slug still takes substeps");
    substep.free_slug = false;
    check(!substep_length(substep).split, "a slug attached to the source is not altered");
    substep.free_slug = true;
    substep.subsampling = false;
    check(!substep_length(substep).split, "LSUBSAM off means no substeps");

    // Position update: DX = U*TSAMP in meters, then in outermost grid units.
    AdvanceInputs advance;
    advance.x_cells = 25.0;
    advance.y_cells = 25.0;
    advance.u_ms = -0.5793;
    advance.v_ms = 1.3557;
    advance.step_s = 66.666666;
    advance.grid_spacing_m = 100.0;
    advance.wind_speed_ms = std::hypot(-0.5793, 1.3557);
    const auto moved = advance_puff(advance);
    check_close(moved.x_cells, 25.0 + (-0.5793 * 66.666666) / 100.0, 1.0e-5, "XNEW");
    check_close(moved.y_cells, 25.0 + (1.3557 * 66.666666) / 100.0, 1.0e-5, "YNEW");
    check_close(moved.distance_m, advance.wind_speed_ms * 66.666666, 1.0e-4, "DISTM = WS*TSAMP");
    check_close(moved.dx_cells, (-0.5793 * 66.666666) / 100.0, 1.0e-6, "DXOLD in grid units");
    // Frozen ORIGINAL CALPUFF 2022 COMP DGM (202200101 record 1685,
    // 202200103 record 5671). They expose one-ULP discrepancies when the
    // original REAL*4 XGRIDMI multiplication is incorrectly replaced with
    // mathematically equivalent division by DGRIDM. No epsilon is allowed.
    AdvanceInputs vendor_y{};
    vendor_y.x_cells = 25.52056884765625F;
    vendor_y.y_cells = 30.92965316772461F;
    vendor_y.u_ms = 0.18750369548797607F;
    vendor_y.v_ms = 2.267062187194824F;
    vendor_y.wind_speed_ms = 2.2748029232025146F;
    vendor_y.step_s = 43.37349319458008F;
    vendor_y.grid_spacing_m = 100.0F;
    const auto locked_y = advance_puff(vendor_y);
    check(std::bit_cast<std::uint32_t>(static_cast<float>(locked_y.y_cells)) ==
              0x41ff4dbcU, "2022 DGM record 1685 YNEW must be vendor REAL4 bit exact");
    check(locked_y.x_cells == static_cast<double>(25.601896286010742F),
          "2022 DGM record 1685 XNEW must be vendor REAL4 exact");
    check(locked_y.distance_m == static_cast<double>(98.66614532470703F),
          "2022 DGM record 1685 DISTM must be vendor REAL4 exact");

    AdvanceInputs vendor_x{};
    vendor_x.x_cells = 30.62416648864746F;
    vendor_x.y_cells = 38.316463470458984F;
    vendor_x.u_ms = 1.6575729846954346F;
    vendor_x.v_ms = -0.9095627665519714F;
    vendor_x.wind_speed_ms = 1.8907279968261719F;
    vendor_x.step_s = 52.889686584472656F;
    vendor_x.grid_spacing_m = 100.0F;
    const auto locked_x = advance_puff(vendor_x);
    check(std::bit_cast<std::uint32_t>(static_cast<float>(locked_x.x_cells)) ==
              0x41fc01beU, "2022 DGM record 5671 XNEW must be vendor REAL4 bit exact");
    check(locked_x.y_cells == static_cast<double>(37.83539962768555F),
          "2022 DGM record 5671 YNEW must be vendor REAL4 exact");
    check(locked_x.distance_m == static_cast<double>(100.00000762939453F),
          "2022 DGM record 5671 DISTM must be vendor REAL4 exact");

    // GETCELL: the single-domain GRIDIJ path (truncate then add one, then the
    // full-precision adjustment).
    CellLookupInputs cell;
    cell.nx = 50;
    cell.ny = 50;
    cell.domains = 1;
    cell.domain = 1;
    cell.nest_factor = 1.0;
    cell.x_cells = 25.0;
    cell.y_cells = 25.0;
    auto located = grid_cell(cell);
    check(located.i == 26 && located.j == 26, "grid cell at 25.0 cells is (26,26)");
    check(located.domain == 1, "the selected domain is the only one");
    cell.x_cells = 24.999;
    located = grid_cell(cell);
    check(located.i == 25, "a fraction below a cell edge stays in the lower cell");
    cell.x_cells = 0.0;
    cell.y_cells = 0.0;
    located = grid_cell(cell);
    check(located.i == 1 && located.j == 1, "the origin is cell (1,1)");
    cell.x_cells = 49.999;
    cell.y_cells = 49.999;
    located = grid_cell(cell);
    check(located.i == 50 && located.j == 50, "the last cell is reachable");
    cell.x_cells = 80.0;      // beyond the domain: nudged just inside
    cell.y_cells = 80.0;
    located = grid_cell(cell);
    check(located.i == 50 && located.j == 50, "a position beyond the edge is nudged inside");
    cell.x_cells = -10.0;
    cell.y_cells = -10.0;
    located = grid_cell(cell);
    check(located.i == 1 && located.j == 1, "a position before the origin is nudged inside");

    // SETPUF's /CURRENT/ coordinate publication (metres) and the stored position.
    CurrentCoordinateInputs current;
    current.x_begin_cells = 25.0;
    current.y_begin_cells = 25.0;
    current.z_begin_m = 136.404;
    current.x_end_cells = 24.6138;
    current.y_end_cells = 25.9038;
    current.grid_spacing_m = 100.0;
    current.step_s = 66.666666;
    const auto published = current_coordinates(current);
    check_close(published.x_begin_m, 2500.0, 1.0e-3, "xb1 = XPB*DGRID");
    check_close(published.y_begin_m, 2500.0, 1.0e-3, "yb1 = YPB*DGRID");
    check_close(published.x_end_m, 2461.38, 1.0e-2, "xe1 = XNEW*DGRID");
    check_close(published.y_end_m, 2590.38, 1.0e-2, "ye1 = YNEW*DGRID");
    check_close(published.z_end_m, 136.404, 1.0e-3, "ze1 without settling keeps the height");
    current.settling_velocity_ms = 0.01;
    const auto settled = current_coordinates(current);
    check_close(settled.z_end_m, 136.404 - 0.01 * 66.666666, 1.0e-3, "ze1 drops with settling");
    check_close(settled.stored_z_m, settled.z_end_m, 1.0e-9, "ZPB stores the settled height");
    current.settling_velocity_ms = 100.0;
    check_close(current_coordinates(current).z_end_m, 0.0, 1.0e-9, "ze1 is floored at the ground");

    // Fail-closed refusals.
    SamplingCadenceInputs bad = cadence;
    bad.source_type = 2;
    check_refuses([&] { (void)sampling_cadence(bad); }, "refuses ISTYPE=2 (VARSAM)");
    bad = cadence;
    bad.emission_period_s = 0.0;
    check_refuses([&] { (void)sampling_cadence(bad); }, "refuses a zero emission period");
    bad = cadence;
    bad.step_seconds = 0.0;
    check_refuses([&] { (void)sampling_cadence(bad); }, "refuses a zero time step");
    bad = cadence;
    bad.grid_spacing_m = 0.0;
    check_refuses([&] { (void)sampling_cadence(bad); }, "refuses a zero grid spacing");
    SubstepInputs bad_step = substep;
    bad_step.sampling_step_s = 0.0;
    check_refuses([&] { (void)substep_length(bad_step); }, "refuses a zero TSAMP");
    bad_step = substep;
    bad_step.sampling_steps = 0;
    check_refuses([&] { (void)substep_length(bad_step); }, "refuses NSAM=0");
    AdvanceInputs bad_advance = advance;
    bad_advance.grid_spacing_m = 0.0;
    check_refuses([&] { (void)advance_puff(bad_advance); }, "refuses a zero grid spacing");
    bad_advance = advance;
    bad_advance.step_s = std::nan("");
    check_refuses([&] { (void)advance_puff(bad_advance); }, "refuses a NaN step");
    CurrentCoordinateInputs bad_current = current;
    bad_current.step_s = 0.0;
    check_refuses([&] { (void)current_coordinates(bad_current); },
                  "refuses a zero step in the /CURRENT/ publication");
    bad_current = current;
    bad_current.settling_velocity_ms = -1.0;
    check_refuses([&] { (void)current_coordinates(bad_current); }, "refuses a negative settling");
    CellLookupInputs bad_cell = cell;
    bad_cell.domains = 2;
    check_refuses([&] { (void)grid_cell(bad_cell); }, "GETCELL refuses nested domains");
    bad_cell = cell;
    bad_cell.domain = 2;
    check_refuses([&] { (void)grid_cell(bad_cell); }, "GETCELL refuses a non-outer domain");
    bad_cell = cell;
    bad_cell.nx = 0;
    check_refuses([&] { (void)grid_cell(bad_cell); }, "GETCELL refuses an empty domain");

    std::cout << "P7X_STEP_INTEGRATION_CONTRACT=" << (failures == 0 ? "PASS" : "FAIL")
              << " CHECKS=" << checks << " FAILURES=" << failures << '\n';
    return failures == 0 ? 0 : 1;
}
