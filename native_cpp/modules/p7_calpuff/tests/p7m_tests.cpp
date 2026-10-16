// P7M CTSG kernel contract tests: hand-derived closed forms, the dispatch
// structure and every fail-closed path. Original-routine parity is checked
// separately by tests/p7m_parity_tests.py against the compiled vendor units.
#include "cteas/puff/ctsg.hpp"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using cteas::puff::CtsgInputs;
using cteas::puff::CtsgResult;
using cteas::puff::CtsgState;
using cteas::puff::SigmaCurvePoint;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7M TEST FAILURE: " + message);
}

void require_close(double observed, double expected, double tolerance, const std::string& what) {
    require(std::abs(observed - expected) <= tolerance,
            what + ": observed " + std::to_string(observed) + " expected " +
                std::to_string(expected) + " tolerance " + std::to_string(tolerance));
}

template <typename Callable>
void require_throw(Callable&& callable, const std::string& what) {
    bool threw = false;
    try {
        callable();
    } catch (const std::exception&) {
        threw = true;
    }
    require(threw, what + " must fail closed");
}

// The deterministic SIGTY/SIGTZ stubs of the oracle driver, in REAL*4.
SigmaCurvePoint stub_sigma_y(double sigma_y0_m, double dx_km, double dt_s) {
    const float s0 = static_cast<float>(sigma_y0_m);
    const float dx = static_cast<float>(dx_km);
    const float dt = static_cast<float>(dt_s);
    SigmaCurvePoint point;
    point.value = static_cast<double>(s0 + 0.5F * dx + 0.1F * dt);
    point.virtual_distance_km = static_cast<double>(s0 * 0.01F);
    point.virtual_time_s = static_cast<double>(s0 * 0.5F);
    return point;
}

SigmaCurvePoint stub_sigma_z(double sigma_z0_m, double dx_km, double dt_s, double height_m) {
    const float s0 = static_cast<float>(sigma_z0_m);
    const float dx = static_cast<float>(dx_km);
    const float dt = static_cast<float>(dt_s);
    const float height = static_cast<float>(height_m);
    SigmaCurvePoint point;
    point.value = static_cast<double>(s0 + 0.3F * dx + 0.2F * dt + 0.01F * height);
    point.virtual_distance_km = static_cast<double>(s0 * 0.02F);
    point.virtual_time_s = static_cast<double>(s0 * 0.4F);
    return point;
}

CtsgState base_state() {
    CtsgState state;
    state.q = 1.0e6;
    state.u = 3.0;
    state.zlid = 200.0;
    state.tstep = 60.0;
    state.frac = 1.0;
    state.sz1 = 2.0;
    state.sy1 = 5.0;
    state.sz2 = 20.0;
    state.sy2 = 60.0;
    state.szr = 20.0;
    state.syr = 60.0;
    state.szmn = 1.0;
    state.symn = 1.0;
    state.hd = 50.0;
    state.ubyn = 1.0;
    state.h = 100.0;
    state.baxi = 1.0 / 2000.0;
    state.r = 0.5;
    state.x12f = -1000.0;
    state.x23f = 1000.0;
    state.xp = -100.0;
    state.zpuff = 10.0;
    state.xpf = 100.0;
    state.t12p = -100.0;
    state.timpg = 20.0;
    state.szimpg = 5.0;
    state.syimpg = 5.0;
    state.xr = 300.0;
    state.isc = 4;
    state.ih = 1;
    state.ip = 1;
    return state;
}

void test_munu() {
    // MUNU (calpuff.for L24865-24967).
    const auto on_axis = cteas::puff::elliptic_coordinates(0, 2.0, 0.0, 1.0);
    require_close(on_axis.nu, 0.0, 1.0e-6, "point on the positive x-axis has nu = 0");
    require_close(on_axis.mu, std::log(2.0), 1.0e-5, "mu of (2,0) with a unit circle");
    const auto origin = cteas::puff::elliptic_coordinates(0, 0.0, 0.0, 0.5);
    require_close(origin.nu, 1.5707963, 1.0e-6, "nu at the origin is pi/2");
    require_close(origin.mu, 0.0, 1.0e-12, "mu at the origin is zero");
    const auto negative_y = cteas::puff::elliptic_coordinates(1, 0.0, -1.0, 0.5);
    require_close(negative_y.nu, 3.0 * 1.5707963, 1.0e-5, "nu on the negative y-axis");
    require_close(negative_y.mu, 0.0, 1.0e-12, "muflag 1 leaves mu at zero");
    // A symmetric hill (r = 1) uses the atan2 branch for an interior point.
    const auto symmetric = cteas::puff::elliptic_coordinates(0, 0.5, 0.5, 1.0);
    require_close(symmetric.nu, 0.7853981, 1.0e-6, "nu of (0.5,0.5) with r = 1");
    // The vendor MUNU is undefined for a point on the major axis inside the
    // ellipse of a non-circular hill: SQRT(XSQ-RSQM1) is negative. The port
    // reproduces that (NaN) instead of inventing a value.
    require(std::isnan(cteas::puff::elliptic_coordinates(0, 0.5, 0.0, 2.0).mu),
            "MUNU reproduces the vendor's undefined in-ellipse on-axis case");
    require_throw([] { (void)cteas::puff::elliptic_coordinates(2, 1.0, 1.0, 1.0); },
                  "muflag outside 0/1");
    require_throw([] { (void)cteas::puff::elliptic_coordinates(0, 1.0, 1.0, -1.0); },
                  "negative axis ratio");
}

void test_ireg_and_bi() {
    require(cteas::puff::region_index(-5.0, 0.0, 10.0) == 1, "region upwind");
    require(cteas::puff::region_index(5.0, 0.0, 10.0) == 2, "region between the boundaries");
    require(cteas::puff::region_index(15.0, 0.0, 10.0) == 3, "region downwind");
    require(cteas::puff::region_index(0.0, 0.0, 0.0) == 2, "boundary point is region 2");

    // BI (calpuff.for L22229-22263): b = 2*(exp(-afac*argm**2)+exp(-afac*argp**2)).
    const float afac = 0.01F;
    const float argm = -5.0F;
    const float argp = 30.0F;
    // The vendor routine is REAL*4, so the closed form is evaluated in REAL*4.
    const float expected = 2.0F * (std::exp(-afac * argm * argm) + std::exp(-afac * argp * argp));
    require_close(cteas::puff::reflection_b(afac, argm, argp), expected, 1.0e-12, "BI closed form");
    // Above the EXP cut-off (EXPMAX = 69) the terms are exactly zero.
    require(cteas::puff::reflection_b(1.0, 100.0, 100.0) == 0.0, "BI beyond the exp cut-off");
}

void test_bjil() {
    // BJIL (calpuff.for L22318-22363): both terms vanish for a zero-height puff
    // on the axis with no sigma spread.
    require(cteas::puff::reflection_bjil(0.5, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0) == 0.0,
            "BJIL is zero for ej = eoi = b1 = szosq = szpsq = 0");
    // Closed form for a single-sigma case: with szpsq = 0 the two terms coincide.
    const double ak = 0.25;
    const double b1 = 0.0;
    const double ej = 4.0;
    const double eoi = 2.0;
    const double szsq = 16.0;
    const double szosq = 0.0;
    const double szpsq = 0.0;
    // REAL*4 throughout, like the vendor routine.
    const float akf = static_cast<float>(ak);
    const float b1f = static_cast<float>(b1);
    const float ejf = static_cast<float>(ej);
    const float eoif = static_cast<float>(eoi);
    const float szsqf = static_cast<float>(szsq);
    const float szosqf = static_cast<float>(szosq);
    const float szpsqf = static_cast<float>(szpsq);
    const float dum = 0.5F / szsqf;
    const float b2 = ejf * szosqf;
    const float b3 = eoif * szpsqf;
    const float exarg1 = dum * (ejf - eoif) * (ejf - eoif);
    const float exarg2 = dum * (ejf + eoif) * (ejf + eoif);
    const float expected =
        std::exp(-exarg1) * (std::erf(akf * (b1f + b2 + b3)) + std::erf(akf * (b1f - b2 - b3))) +
        std::exp(-exarg2) * (std::erf(akf * (b1f + b2 - b3)) + std::erf(akf * (b1f - b2 + b3)));
    require_close(cteas::puff::reflection_bjil(ak, b1, ej, eoi, szsq, szosq, szpsq), expected,
                  1.0e-6, "BJIL closed form");
    require_throw([] { (void)cteas::puff::reflection_bjil(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0); },
                  "BJIL with a zero sigma-z square");
}

void test_sigma() {
    const auto y = cteas::puff::SigmaYCurve(stub_sigma_y);
    const auto z = cteas::puff::SigmaZCurve(stub_sigma_z);
    // The vendor returns the start-of-step sigma without evaluating any curve
    // when the sigma does not grow.
    require_close(cteas::puff::sigma_restart(1, 10.0, 3.0, 500.0, 7.0, 0.0, 7.0, 60.0, 7.0, 1.0,
                                             y, z),
                  7.0, 0.0, "SIGMA shortcut when s1 == s2");
    // Closed form of the wrapper with the stub curve: the nearest known age is
    // the receptor value (20 m at t = 60 s), the stub virtual time of 20 m is
    // 10 s and its virtual distance is 0.2 km, so tsec = 70 s, dkm = 0.38 km and
    // the forward stub evaluation gives 0.5*0.38 + 0.1*70 = 7.19 m.
    require_close(cteas::puff::sigma_restart(1, 10.0, 3.0, 120.0, 2.0, 0.0, 20.0, 60.0, 20.0, 1.0,
                                             y, z),
                  7.19, 1.0e-4, "SIGMA closed form through the stub sigma-y curve");
    // Sigma-z uses the same wrapper but the stub z curve: its virtual time of
    // 20 m is 8 s and its virtual distance 0.4 km. The vendor passes the REVERSE
    // pair (0.4 km, 8 s) to the forward SIGTZ call, so the result is
    // 0.3*0.4 + 0.2*8 + 0.01*10 = 1.82 m (the advanced TSEC/DKM pair is only
    // used for the positivity test).
    const double expected_z = 0.3 * 0.4 + 0.2 * 8.0 + 0.01 * 10.0;
    require_close(cteas::puff::sigma_restart(2, 10.0, 3.0, 120.0, 2.0, 0.0, 20.0, 60.0, 20.0, 1.0,
                                             y, z),
                  expected_z, 1.0e-3, "SIGMA closed form through the stub sigma-z curve");
    require_throw([&] {
        (void)cteas::puff::sigma_restart(3, 10.0, 3.0, 120.0, 2.0, 0.0, 20.0, 60.0, 20.0, 1.0, y,
                                         z);
    }, "SIGMA with an invalid itype");
    require_throw([&] {
        (void)cteas::puff::sigma_restart(1, 10.0, 3.0, 120.0, 2.0, 0.0, 20.0, 60.0, 20.0, 1.0,
                                         cteas::puff::SigmaYCurve(), z);
    }, "SIGMA without a sigma-y curve");
}

void test_ctrec() {
    CtsgState state = base_state();
    state.xr = 0.0;
    state.yr = 0.0;
    state.xc = 0.0;
    state.yc = 0.0;
    state.x12f = -100.0;
    state.x23f = 100.0;
    state.xob = 0.0;
    state.zrec = 0.0;
    cteas::puff::receptor_geometry(state);
    require_close(state.xrf, 0.0, 0.0, "unrotated receptor x");
    require_close(state.yrf, 0.0, 0.0, "unrotated receptor y");
    require(state.iregu == 2, "receptor between the boundaries is region 2");
    require(state.iregl == 2, "receptor on the lower boundary is region 2");
    require_close(state.t12ru, 100.0 / 3.0, 1.0e-4, "upper travel time");
    require_close(state.t12rl, 0.0, 0.0, "lower travel time on the boundary");
    // A rotated frame moves the receptor out of region 2 in the beta frame.
    CtsgState rotated = base_state();
    rotated.beta = 0.5;
    rotated.cbeta = std::cos(0.5);
    rotated.xr = 0.0;
    rotated.yr = 0.0;
    rotated.xc = 0.0;
    rotated.yc = 0.0;
    rotated.xob = 0.0;
    rotated.zrec = 0.0;
    cteas::puff::receptor_geometry(rotated);
    require(rotated.iregl == 2, "beta rotation keeps the boundary point in region 2");
    require_throw([] {
        CtsgState broken = base_state();
        broken.u = 0.0;
        cteas::puff::receptor_geometry(broken);
    }, "CTREC with a zero transport speed");
}

void test_puffc() {
    CtsgState state = base_state();
    state.zpuff = 0.0;
    state.szr = 2.0;
    state.syr = 20.0;
    state.zrec = 0.0;
    state.zlid = 1.0e6;
    // The vertical factor is the exact two-term sum when the reflection terms
    // are below the EXP cut-off (a very high lid).
    const double sz = state.szr;
    const double sy = state.syr;
    const double t1mtr = -(state.t12p + state.t12rl);
    const double t2mtr = state.tstep + t1mtr;
    const double dum = state.u / (std::sqrt(2.0) * sy);
    const double co = state.q * (std::erf(t2mtr * dum) - std::erf(t1mtr * dum)) /
                      (state.tstep * 4.0 * 3.1415927 * state.u * sy * sz);
    const double dely = state.yrf - state.ypf;
    const double fy = std::exp(-0.5 * (dely * dely) / (sy * sy));
    const double fz = 2.0 * std::exp(-0.5 * (state.zpuff * state.zpuff) / (sz * sz));
    require_close(cteas::puff::puff_concentration(state, 0, 0.0, 0.0), co * fy * fz, 1.0e-3,
                  "PUFFC no-reflection closed form");
    // A receptor before the puff's release time has no concentration.
    CtsgState early = state;
    early.timpg = -1.0e6;
    early.t12rl = 0.0;
    require(cteas::puff::puff_concentration(early, 0, 0.0, 0.0) == 0.0,
            "PUFFC with a non-positive age");
    // Mode 0 forces the pole height to zero, mode 2 uses the passed offset.
    require_close(cteas::puff::puff_concentration(state, 0, 999.0, 0.0),
                  cteas::puff::puff_concentration(state, 1, 0.0, 0.0), 0.0,
                  "PUFFC mode 0 ignores the pole height");
    require(cteas::puff::puff_concentration(state, 2, 0.0, 1.0e6) == 0.0,
            "PUFFC mode 2 far off the stagnation streamline");
    // The RT2PI quirk: a puff mixed in the vertical returns zero.
    CtsgState mixed = state;
    mixed.szr = 400.0;
    require(cteas::puff::puff_concentration(mixed, 0, 0.0, 0.0) == 0.0,
            "PUFFC vertical-mixing branch is zero because the vendor RT2PI is zero");
    require_throw([&] { (void)cteas::puff::puff_concentration(state, 3, 0.0, 0.0); },
                  "PUFFC with an invalid mode");
}

void test_lower() {
    const auto y = cteas::puff::SigmaYCurve(stub_sigma_y);
    const auto z = cteas::puff::SigmaZCurve(stub_sigma_z);
    CtsgState state = base_state();
    state.zrec = 0.0;
    state.zpuff = 0.0;
    state.sz1 = 2.0;
    state.sz2 = 2.0;
    state.szr = 2.0;
    state.szimpg = 2.0;
    state.d = 0.0;
    state.xr = 300.0;
    state.yr = 0.0;
    state.xc = 0.0;
    state.yc = 0.0;
    cteas::puff::receptor_geometry(state);
    const double value = cteas::puff::lower_segment(state, y, z);
    // sz == szimpg and zpuff == zrec == 0 make szp zero and BI(ak,0,0) = 4, so
    // the reflection series is exactly twofz = 4 and fz = 2. SIGMA picks the
    // receptor sigma (60 m) as the nearest known value: its stub virtual time is
    // 30 s and its virtual distance 0.6 km, so tsec = 90 s, dkm = 0.78 km and the
    // forward stub evaluation gives sy = 0.5*0.78 + 0.1*90 = 9.39 m, inside
    // [sy1, sy2].
    const double sz = 2.0;
    const double sy = 0.5 * 0.78 + 0.1 * 90.0;
    const double t1mtr = -(state.t12p + state.t12rl);
    const double t2mtr = state.tstep + t1mtr;
    const double dum = state.u / (std::sqrt(2.0) * sy);
    const double co = state.q * (std::erf(t2mtr * dum) - std::erf(t1mtr * dum)) /
                      (state.tstep * 4.0 * 3.1415927 * state.u * sy * sz);
    require_close(value, co * 2.0, std::abs(co) * 1.0e-4, "LOWER closed form for the BI branch");

    CtsgState early = state;
    early.timpg = -1.0e6;
    early.t12rl = 0.0;
    require(cteas::puff::lower_segment(early, y, z) == 0.0, "LOWER with a non-positive age");

    CtsgState mixed = base_state();
    mixed.szimpg = 400.0;
    mixed.sz2 = 400.0;
    mixed.szr = 400.0;
    mixed.zrec = 0.0;
    require(cteas::puff::lower_segment(mixed, y, z) == 0.0,
            "LOWER vertical-mixing branch is zero because the vendor RT2PI is zero");

    CtsgState past = base_state();
    past.t12p = 1.0e6;
    require(cteas::puff::lower_segment(past, y, z) == 0.0,
            "LOWER returns zero when the puff has already passed the receptor");
    require_throw([&] {
        (void)cteas::puff::lower_segment(base_state(), cteas::puff::SigmaYCurve(),
                                         cteas::puff::SigmaZCurve());
    }, "LOWER without the sigma curves");
}

void test_ctsg_dispatch() {
    const auto y = cteas::puff::SigmaYCurve(stub_sigma_y);
    const auto z = cteas::puff::SigmaZCurve(stub_sigma_z);
    CtsgInputs inputs;
    inputs.puff_index = 1;
    inputs.hill_index = 1;
    inputs.start_age_s = 0.0;

    // Receptor below Hd, downwind: the lower-segment branch.
    CtsgState below = base_state();
    below.xr = 300.0;
    below.yr = 0.0;
    below.zrec = 0.0;
    inputs.receptor_x_m = below.xr;
    inputs.receptor_y_m = below.yr;
    const CtsgResult below_result = cteas::puff::ctsg(below, inputs, y, z);
    CtsgState below_geometry = below;
    cteas::puff::receptor_geometry(below_geometry);
    require(below_geometry.iregl != 1, "the downwind receptor is not upwind of the hill");
    const double expected_lower = cteas::puff::lower_segment(below_geometry, y, z);
    require_close(below_result.concentration, expected_lower, std::abs(expected_lower) * 1.0e-12,
                  "CTSG below Hd dispatches to LOWER");
    require(below_result.flat_concentration != 0.0, "CTSG always reports the flat comparison");

    // Receptor below Hd and upwind: the receptor-on-a-pole branch.
    CtsgState upwind = base_state();
    upwind.xr = -300.0;
    upwind.yr = -40.0;
    upwind.d = 40.0;
    upwind.zrec = 0.0;
    inputs.receptor_x_m = upwind.xr;
    inputs.receptor_y_m = upwind.yr;
    const CtsgResult upwind_result = cteas::puff::ctsg(upwind, inputs, y, z);
    CtsgState upwind_geometry = upwind;
    cteas::puff::receptor_geometry(upwind_geometry);
    require(upwind_geometry.iregl == 1, "the upwind receptor is in the lower region 1");
    require_close(upwind_result.concentration,
                  cteas::puff::puff_concentration(upwind_geometry, 2, 0.0, 40.0),
                  std::abs(upwind_result.concentration) * 1.0e-12,
                  "CTSG below Hd upwind dispatches to PUFFC(2)");

    // A different time step makes the vendor call CTPAR, which is not ported.
    CtsgInputs other_step = inputs;
    other_step.start_age_s = 120.0;
    require_throw([&] { (void)cteas::puff::ctsg(below, other_step, y, z); },
                  "CTSG when CTPAR would be required");
    // A receptor above Hd and downwind needs UPPER.
    CtsgState above = base_state();
    above.zrec = 60.0;
    above.xr = 300.0;
    inputs.receptor_x_m = above.xr;
    inputs.receptor_y_m = above.yr;
    require_throw([&] { (void)cteas::puff::ctsg(above, inputs, y, z); },
                  "CTSG when UPPER would be required");
}

void test_constants() {
    const auto constants = cteas::puff::ctsg_constants();
    // The vendor never initialises RT2PI in /CONST/, so the original evaluates
    // the vertical-mixing branch as zero; the port reproduces that.
    require_close(constants.rt2pi, 0.0, 0.0, "RT2PI as the vendor leaves it");
    require_close(constants.small, 1.0e-6, 1.0e-12, "SMALL");
    require_close(constants.expmax, 69.0, 0.0, "EXPMAX");
    require_close(constants.epsrefl, 0.01, 1.0e-9, "EPSREFL");
    require(constants.max_reflections == 50, "MXREFL");
}

} // namespace

int main() {
    try {
        test_munu();
        test_ireg_and_bi();
        test_bjil();
        test_sigma();
        test_ctrec();
        test_puffc();
        test_lower();
        test_ctsg_dispatch();
        test_constants();
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    std::cout << "P7M_CTSG_KERNEL_CONTRACT=PASS\n";
    return 0;
}
