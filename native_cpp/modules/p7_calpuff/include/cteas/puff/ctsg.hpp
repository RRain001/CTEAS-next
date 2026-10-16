#pragma once

#include <cstddef>
#include <functional>
#include <string>
#include <vector>

namespace cteas::puff {

// P7I: CTSG support blocks of CALPUFF 7.2.1, transcribed from the unmodified
// vendor source and cross-checked against it by CTest:
//   QATR  calpuff.for L25406-25520  (Romberg integrator used by UPPER/LOWER)
//   TFAC  calpuff.for L25765-25813  (terrain flow-distortion interpolation)
//
// These are the parts of the CTSG dependency closure that are self-contained
// and can be closed with original-source parity. The remaining CTSG closure
// (CTSG/CTREC/CTPAR/MUNU/LOWER/UPPER plus BI/BJIL/FLOPUFF and the /CTPASS/
// state) is listed precisely in the reconstruction ledger.

// QATR status flags, as documented in the vendor routine.
enum class QuadratureStatus : int {
    converged = 0,   // IER=0
    diverging = 1,   // IER=1
    no_convergence = 2, // IER=2
};

struct QuadratureResult {
    double value = 0.0;
    QuadratureStatus status = QuadratureStatus::no_convergence;
};

// QATR equivalent: Romberg integration of `integrand` over [lower, upper] with
// fractional tolerance `eps` and at most `dimension` extrapolation levels.
// `dimension` is bounded like the vendor's integer*2 guard (jj <= 32000).
[[nodiscard]] QuadratureResult integrate_romberg(double lower, double upper, double eps,
                                                 int dimension,
                                                 const std::function<double(double)>& integrand);

// TFAC equivalent: interpolate the terrain flow-distortion factors at position
// `x` along the trajectory. Outside [begin, end] the factors are unity, exactly
// as the vendor routine does.
struct TerrainFactors {
    double top = 1.0;     // TH
    double lateral = 1.0; // TL
    double total = 1.0;   // TU = 1/(TH*TL)
};

// ROTATE equivalent (calpuff.for L25522-25549): rotate (x, y) through `angle`
// radians, the coordinate transform CTREC/CTPAR use.
struct RotatedPoint {
    double x = 0.0;
    double y = 0.0;
};

[[nodiscard]] RotatedPoint rotate_xy(double x, double y, double angle_rad);

[[nodiscard]] TerrainFactors terrain_factors(double x_m, double begin_m, double end_m,
                                             double spacing_m,
                                             const std::vector<double>& top_factors,
                                             const std::vector<double>& lateral_factors);

// ---------------------------------------------------------------------------
// P7M: CTSG kernel of CALPUFF 7.2.1, transcribed from the unmodified vendor
// source and cross-checked against it by CTest:
//   MUNU  calpuff.for L24865-24967   (elliptical coordinates of a point)
//   IREG  calpuff.for L24576-24597   (CTSG region index)
//   BI    calpuff.for L22229-22263   (constant sigma-z reflection helper)
//   BJI   calpuff.for L22265-22316   (reflection helper for UPPER)
//   BJIL  calpuff.for L22318-22363   (reflection helper for LOWER)
//   SIGMA calpuff.for L25551-25645   (nearest-known-sigma restart wrapper)
//   CTREC calpuff.for L22841-22921   (receptor position in the CTSG frames)
//   PUFFC calpuff.for L25286-25404   (receptor-on-a-pole / flat puff sampling)
//   LOWER calpuff.for L24657-24863   (concentration below the dividing streamline)
//   CTSG  calpuff.for L22923-23112   (terrain kernel dispatch; lower-segment branch)
//
// The /CTPASS/ state is an explicit input here (no hidden common block) and a
// missing field fails closed. CTPAR (the puff-trajectory terrain parameters) and
// UPPER (the above-dividing-streamline branch, which needs FLOPUFF) are NOT
// ported: the state carries CTPAR's outputs, and CTSG fails closed when it would
// have to call CTPAR or UPPER.
//
// Vendor constant reproduction: the /CONST/ values are set by CTINIT
// (calpuff.for L22412-22434) EXCEPT RT2PI, which the vendor never initializes
// (no DATA statement anywhere in the file writes it; the five `data ... rt2pi`
// statements in calpuff.for belong to routines that do not include const.puf).
// The original therefore evaluates the "puff mixed in the vertical" branch of
// LOWER/PUFFC as RT2PI*sz/zlid = 0. The port reproduces that exactly.

// Elliptical coordinates (MU, NU) of a point referenced to an ellipse whose
// x-axis is the major axis (MUNU). `mu_flag == 1` skips the MU calculation.
struct EllipticCoordinates {
    double mu = 0.0;
    double nu = 0.0;
};

[[nodiscard]] EllipticCoordinates elliptic_coordinates(int mu_flag, double x_scaled,
                                                       double y_scaled, double axis_ratio);

// IREG: 1 upwind of the first boundary, 3 beyond the second, 2 between them.
[[nodiscard]] int region_index(double x, double x12, double x23);

// BI: B(E,Eo) for a virtually constant sigma-z.
[[nodiscard]] double reflection_b(double afac, double argm, double argp);

// BJI: B(E,Eo) used by UPPER (needs SZESQ and SZOSQ of the /CTPASS/ state; the
// vendor routine does not read SZPSQ).
[[nodiscard]] double reflection_bji(double ak, double dm, double dp, double d0, double eoimh,
                                    double eoiph, double ej, double szesq, double szosq);

// BJIL: B(E,Eo) used by LOWER (needs szsq, szosq and szpsq of /CTPASS/).
[[nodiscard]] double reflection_bjil(double ak, double b1, double ej, double eoi, double szsq,
                                     double szosq, double szpsq);

// A SIGTY/SIGTZ evaluation, mirroring the vendor argument/return convention:
// value plus the virtual time (s) and virtual distance (km) of the result.
struct SigmaCurvePoint {
    double value = 0.0;
    double virtual_time_s = 0.0;
    double virtual_distance_km = 0.0;
};

using SigmaYCurve = std::function<SigmaCurvePoint(double sigma_y0_m, double dx_km, double dt_s)>;
using SigmaZCurve = std::function<SigmaCurvePoint(double sigma_z0_m, double dx_km, double dt_s,
                                                  double height_m)>;

// SIGMA equivalent: sigma at puff age `t` starting from the nearest of the three
// known values (start, receptor and end of step). ITYPE is 1 for sigma-y and 2
// for sigma-z. The SIGTY/SIGTZ curves are explicit dependencies: this module
// does not carry the dispersion state.
//
// Vendor asymmetry reproduced verbatim: the sigma-y branch passes the advanced
// (DKM, TSEC) pair to the forward SIGTY call, while the sigma-z branch passes
// the REVERSE outputs (VDZ, VTZ) to the forward SIGTZ call and only uses TSEC
// for the "is the age positive" test.
[[nodiscard]] double sigma_restart(int itype, double puff_height_m, double speed_ms, double t_s,
                                   double sigma_start_m, double start_age_s, double sigma_end_m,
                                   double step_s, double sigma_receptor_m, double fraction,
                                   const SigmaYCurve& sigma_y_curve,
                                   const SigmaZCurve& sigma_z_curve);

// The /CTPASS/ state of the CTSG kernel. Everything the ported units read from
// the vendor common block is an explicit field here. The CTPAR outputs (the
// hill-centred flow geometry) must be supplied by the caller: CTPAR itself is
// not reconstructed, and CTSG refuses to run when it would have to call it.
struct CtsgState {
    // CTSG argument list / puff and receptor state.
    double q = 0.0;                            // Q, mass in the puff (g)
    double u = 0.0;                            // U, transport speed (m/s)
    double zlid = 0.0;                         // ZLID, mixing lid (m)
    double xp = 0.0, yp = 0.0, zpuff = 0.0;    // puff position at the start of the step (m)
    int isc = 0;                               // stability class
    double zrec = 0.0;                         // receptor height (m)
    double xr = 0.0, yr = 0.0;                 // receptor position (m)
    int ih = 0;                                // current hill (previous call)
    int ip = 0;                                // current puff (previous call)
    int ir = 0;                                // current receptor
    double tstep = 0.0;                        // step duration (s)
    double tstart = 0.0;                       // puff age at the start of the step (s)
    double sz1 = 0.0, sz2 = 0.0;               // sigma-z at start/end of the step (m)
    double sy1 = 0.0, sy2 = 0.0;               // sigma-y at start/end of the step (m)
    double szr = 0.0, syr = 0.0;               // sigma-z / sigma-y at the receptor (m)
    double szmn = 0.0, symn = 0.0;             // minimum sigmas (m)
    double frac = 0.0;                         // fraction of the step to the receptor
    // CTPAR outputs (explicit; CTPAR is not ported).
    double hd = 0.0;                           // dividing-streamline height (m)
    double ubyn = 0.0;                         // U/N (m/s)
    double h = 0.0;                            // relief (m)
    double zgrid = 0.0;                        // hill base-plane height (m MSL)
    double xc = 0.0, yc = 0.0;                 // hill centre (m)
    double rotflo = 0.0, rotang = 0.0, alfw = 0.0;
    double beta = 0.0, cbeta = 1.0, d = 0.0;   // beta frame and off-axis distance (m)
    double baxi = 0.0;                         // 1 / major axis (1/m)
    double r = 1.0;                            // axis ratio
    double x12f = 0.0, x23f = 0.0, xob = 0.0;  // region boundaries (m)
    double xpf = 0.0, ypf = 0.0;               // puff at the end of the step, flow frame (m)
    double t12p = 0.0;                         // travel time boundary(1,2) -> puff (s)
    double timpg = 0.0;                        // puff age at impingement (s)
    double szimpg = 0.0, syimpg = 0.0;         // sigmas at the impingement point (m)
    // CTREC outputs.
    double xrf = 0.0, yrf = 0.0;               // receptor in the hill/flow frame (m)
    double xre = 0.0, yre = 0.0;               // receptor in the ellipse frame (m)
    double xrb = 0.0, yrb = 0.0;               // receptor in the beta frame (m)
    int iregu = 0, iregl = 0;                  // regions above / below Hd
    double t12ru = 0.0, t12rl = 0.0;           // travel times from boundary(1,2) (s)
};

// CTREC equivalent: updates xrf/yrf, xre/yre, xrb/yrb, iregu/iregl, t12ru/t12rl.
void receptor_geometry(CtsgState& state);

// PUFFC equivalent. IMODE is 0 (flat), 1 (receptor on a pole) or 2 (pole plus
// stagnation-streamline offset). Returns the concentration (g/m**3).
[[nodiscard]] double puff_concentration(const CtsgState& state, int imode, double zpole_m,
                                        double dpole_m);

// LOWER equivalent: concentration due to puff material below the dividing
// streamline (g/m**3).
[[nodiscard]] double lower_segment(const CtsgState& state, const SigmaYCurve& sigma_y_curve,
                                   const SigmaZCurve& sigma_z_curve);

// CTSG arguments that are not part of the persistent /CTPASS/ state.
struct CtsgInputs {
    int receptor_index = 1;        // IRIN
    int puff_index = 1;            // IPIN
    int hill_index = 0;            // IHIN
    double start_age_s = 0.0;      // TIN (age of the puff at the start of the step)
    double receptor_x_m = 0.0;     // XRCTM(IRIN)
    double receptor_y_m = 0.0;     // YRCTM(IRIN)
};

struct CtsgResult {
    double concentration = 0.0;      // CONC (g/m**3)
    double flat_concentration = 0.0; // CFLAT (g/m**3)
};

// CTSG equivalent, restricted to the reconstructed branches. Fails closed when
// the vendor would call CTPAR (a different puff, hill or time step) or UPPER
// (receptor above the dividing streamline with the flow in the upper region).
//
// The vendor also derives TWOKZ/TWOKY (the diffusivities over the step) here.
// Nothing in the reconstructed kernel reads them: they are consumed by CTPAR
// (not ported) and by the CTSG debug print, so they are not part of this port.
[[nodiscard]] CtsgResult ctsg(CtsgState state, const CtsgInputs& inputs,
                              const SigmaYCurve& sigma_y_curve,
                              const SigmaZCurve& sigma_z_curve);

// The vendor /CONST/ values the kernel uses, exposed for the source-parity test
// (not for configuration). `rt2pi` is the value the original actually runs with,
// which is zero because CTINIT never initialises it.
struct CtsgConstants {
    double rt2pi = 0.0;
    double small = 0.0;
    double expmax = 0.0;
    double epsrefl = 0.0;
    int max_reflections = 0;
};

[[nodiscard]] CtsgConstants ctsg_constants();

} // namespace cteas::puff
