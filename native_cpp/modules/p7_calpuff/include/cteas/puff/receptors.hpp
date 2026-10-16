#pragma once

#include "cteas/puff/control.hpp"
#include "cteas/puff/original_grid_coords.hpp"
#include "cteas/puff/coupling.hpp"

#include <cstddef>
#include <string>
#include <vector>

namespace cteas::puff {

// P7E: receptor geometry and the puff-to-receptor sampling accumulation of
// CALPUFF 7.2.1, restricted to the pieces the selected real case needs.
//
// The locked Hefei 2022 deck uses gridded receptors (LSAMP=T, IBSAMP..IESAMP =
// 1..50, MESHDN=1) and an empty discrete receptor subgroup, so the receptor
// geometry is derived from the sampling grid. The sampling integrals come from
// the vendor routine PFSAMP (calpuff.for L4683-4751) and the horizontal
// accumulation from CALCPF's gridded-receptor branch; both are transcribed and
// cross-checked against the unmodified vendor source by CTest.
//
// Not reconstructed, and refused by the callers of this module: the vertical
// coupling coefficient VCBar (so the vertical factor is an explicit input), the
// CTSG concentration kernel (terrain factors, upper/lower splits, slugs, wind
// shear, PDF), the area/line/volume source sampling, and the receptor-specific
// averaging (AVET) machinery of the original output stage.

struct Receptor {
    double x_km = 0.0;               // receptor X in met-grid km
    double y_km = 0.0;               // receptor Y in met-grid km
    double ground_elevation_m = 0.0; // terrain elevation (0 when unknown)
    double height_m = 0.0;           // receptor height above ground
};

struct ReceptorSet {
    bool gridded = true;
    int sampling_nx = 0, sampling_ny = 0;   // NX/NY of the sampling grid
    int ibsamp = 0, jbsamp = 0, iesamp = 0, jesamp = 0;
    int mesh_down = 1;                      // MESHDN
    double spacing_km = 0.0;                // DGRIDKM/MESHDN
    std::vector<Receptor> grid;             // row-major, i fastest (gridded receptors)
    std::vector<Receptor> discrete;         // subgroup 17b receptors (may be empty)
};

// Parses the sampling-grid parameters, the computational-grid indices and the
// discrete receptor subgroup from the control text. Fails closed on malformed
// indices, a sampling grid outside the computational grid, a non-positive
// spacing, a receptor outside the met grid, non-finite values, and on a deck
// that enables neither gridded nor discrete receptors.
[[nodiscard]] ReceptorSet receptors_from_control(const std::string& control_text);
// Selected original QA geometry: replace only the gridded XY positions using
// the original CALMET REAL*4 origin; other P7E sampling physics is unchanged.
// Scope: MESHDN=1, with a matching CALMET/control grid spacing.
[[nodiscard]] ReceptorSet receptors_from_original_met_grid(
    const std::string& control_text, const OriginalMetGridFrame& met);

// PFSAMP equivalent: the two sampling integrals for a puff moving from
// (x_old, y_old) to (x_new, y_new) relative to one receptor.
// Original CALPUFF PFSCRN (calpuff.for L4619-4680): REAL*4 geometric
// nearest-approach screen using the END-of-step puff radius. All XY and
// radius**2 values MUST use the same frame (vendor sampling-grid cells).
struct PuffScreeningResult {
    double closest_distance_squared = 0.0;
    bool has_impact = false;
    bool calm_midpoint_branch = false;
};
[[nodiscard]] PuffScreeningResult original_puff_screen(
    double x_old,double y_old,double x_new,double y_new,
    double x_receptor,double y_receptor,double puff_radius_squared);

struct SamplingIntegrals {
    double i1 = 0.0;
    double i2 = 0.0;
    bool low_wind_branch = false;   // A < 1e-4 shortcut in the vendor routine
};

[[nodiscard]] SamplingIntegrals puff_sampling_integrals(double x_old_km, double y_old_km,
                                                       double x_new_km, double y_new_km,
                                                       double x_receptor_km, double y_receptor_km,
                                                       double sigma_y_at_receptor_m,
                                                       double closest_approach_squared_km2);

// CALCPF gridded-receptor accumulation for one species over one sampling step:
//   dinv = ASDF/(2*pi*sigma_y_rec**2); t2 = xi2*dinv; t1 = xi1*dinv - t2
//   concentration += vdpvd*vertical_factor*time_fraction*(q_old*t1 + q_new*t2)
// The vertical factor (VCBar) and the deposition ratio (VDPVD) are explicit
// inputs because those layers are not reconstructed here.
struct ReceptorAccumulationInputs {
    double mass_old = 0.0;             // QOLD for this species (mass units)
    double mass_new = 0.0;             // QNEW
    double sigma_y_at_receptor_m = 0.0;
    double closest_approach_squared_km2 = 0.0;
    double vertical_factor = 0.0;      // F1 from VCBar (per metre)
    double time_fraction = 0.0;        // TFRACT in (0,1]
    double deposition_ratio = 1.0;     // VDPVD
    double area_source_factor = 1.0;   // ASDF, nominally 1.0
};

[[nodiscard]] double receptor_concentration_increment(
    const SamplingIntegrals& integrals, const ReceptorAccumulationInputs& inputs);

// Coupling-aware accumulation: the vertical factor F1 is taken from the
// reconstructed VCBAR instead of being supplied by the caller.
[[nodiscard]] double receptor_concentration_increment_with_coupling(
    const SamplingIntegrals& integrals, const ReceptorAccumulationInputs& inputs,
    const VcbarInputs& coupling);

// PFSAMP's ERFDIF dependency, exposed for the source-parity test.
[[nodiscard]] double erf_difference(double x1, double x2);

} // namespace cteas::puff
