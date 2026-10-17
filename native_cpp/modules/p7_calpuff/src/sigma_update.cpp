#include "cteas/puff/sigma_update.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = SigmaUpdateReal;

constexpr R kZero = 0.0F;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7Q sigma update: " + message);
}

void require_finite(double value, const std::string& what) {
    require_true(std::isfinite(value), what + " must be finite");
}

R to_real(double value, const char* what) {
    require_finite(value, what);
    return static_cast<R>(value);
}

R curve_value(double value, const char* what) {
    const R converted = to_real(value, what);
    require_true(std::isfinite(static_cast<double>(converted)), what);
    return converted;
}

} // namespace

SigmaStep sigma_step(const SigmaStepInputs& inputs, const SigmaYCurve& sigma_y_curve,
                     const SigmaZCurve& sigma_z_curve) {
    // SETPUF L48505-48536, REAL*4.
    require_true(static_cast<bool>(sigma_y_curve) && static_cast<bool>(sigma_z_curve),
                 "both dispersion curves must be supplied");
    const R sigma_y_start = to_real(inputs.sigma_y_start_m, "SIGYB");
    const R sigma_z_start = to_real(inputs.sigma_z_start_m, "SIGZB");
    const R puff_height = to_real(inputs.puff_height_m, "puff height");
    const R mid_time = to_real(inputs.mid_time_s, "midpoint time");
    const R mid_distance = to_real(inputs.mid_distance_km, "midpoint distance");
    require_true(sigma_y_start >= kZero && sigma_z_start >= kZero,
                 "the start-of-step sigmas must not be negative");

    SigmaStep result;
    result.gaussian_vertical = (inputs.puff_code % 2) == 1;

    // SIGMA-Y: the virtual pair of the start-of-step sigma, then the midpoint and
    // the end of the step advanced by the step's half-distance and half-time.
    const auto y_begin =
        sigma_y_curve(static_cast<double>(sigma_y_start), 0.0, 0.0);
    result.sigma_y_begin_m = curve_value(y_begin.value, "sigma-y at the start");
    const R vty_begin = to_real(y_begin.virtual_time_s, "sigma-y virtual time at the start");
    const R vdy_begin = to_real(y_begin.virtual_distance_km, "sigma-y virtual distance at the start");
    result.virtual_time_y_begin_s = static_cast<double>(vty_begin);
    result.virtual_distance_y_begin_km = static_cast<double>(vdy_begin);

    const R time_mid = vty_begin + mid_time;
    const R distance_mid = vdy_begin + mid_distance;
    const auto y_mid = sigma_y_curve(0.0, static_cast<double>(distance_mid),
                                     static_cast<double>(time_mid));
    result.sigma_y_mid_m = curve_value(y_mid.value, "sigma-y at the midpoint");
    const R vty_mid = to_real(y_mid.virtual_time_s, "sigma-y virtual time at the midpoint");
    const R vdy_mid = to_real(y_mid.virtual_distance_km, "sigma-y virtual distance at the midpoint");
    result.virtual_time_y_mid_s = static_cast<double>(vty_mid);
    result.virtual_distance_y_mid_km = static_cast<double>(vdy_mid);

    const R time_end = time_mid + mid_time;
    const R distance_end = distance_mid + mid_distance;
    const auto y_end = sigma_y_curve(0.0, static_cast<double>(distance_end),
                                     static_cast<double>(time_end));
    result.sigma_y_end_m = curve_value(y_end.value, "sigma-y at the end");
    result.virtual_time_y_end_s = y_end.virtual_time_s;
    result.virtual_distance_y_end_km = y_end.virtual_distance_km;

    // SIGMA-Z: the start-of-step sigma is carried through unchanged unless the
    // puff is Gaussian in the vertical.
    result.sigma_z_begin_m = static_cast<double>(sigma_z_start);
    result.sigma_z_mid_m = static_cast<double>(sigma_z_start);
    result.sigma_z_end_m = static_cast<double>(sigma_z_start);
    if (result.gaussian_vertical) {
        const auto z_begin = sigma_z_curve(static_cast<double>(sigma_z_start), 0.0, 0.0,
                                           static_cast<double>(puff_height));
        result.sigma_z_begin_m = curve_value(z_begin.value, "sigma-z at the start");
        const R vtz_begin = to_real(z_begin.virtual_time_s, "sigma-z virtual time at the start");
        const R vdz_begin =
            to_real(z_begin.virtual_distance_km, "sigma-z virtual distance at the start");
        result.virtual_time_z_begin_s = static_cast<double>(vtz_begin);
        result.virtual_distance_z_begin_km = static_cast<double>(vdz_begin);

        const R ztime_mid = vtz_begin + mid_time;
        const R zdistance_mid = vdz_begin + mid_distance;
        const auto z_mid = sigma_z_curve(0.0, static_cast<double>(zdistance_mid),
                                         static_cast<double>(ztime_mid),
                                         static_cast<double>(puff_height));
        result.sigma_z_mid_m = curve_value(z_mid.value, "sigma-z at the midpoint");
        const R vtz_mid = to_real(z_mid.virtual_time_s, "sigma-z virtual time at the midpoint");
        const R vdz_mid =
            to_real(z_mid.virtual_distance_km, "sigma-z virtual distance at the midpoint");
        result.virtual_time_z_mid_s = static_cast<double>(vtz_mid);
        result.virtual_distance_z_mid_km = static_cast<double>(vdz_mid);

        const R ztime_end = ztime_mid + mid_time;
        const R zdistance_end = zdistance_mid + mid_distance;
        const auto z_end = sigma_z_curve(0.0, static_cast<double>(zdistance_end),
                                         static_cast<double>(ztime_end),
                                         static_cast<double>(puff_height));
        result.sigma_z_end_m = curve_value(z_end.value, "sigma-z at the end");
        result.virtual_time_z_end_s = z_end.virtual_time_s;
        result.virtual_distance_z_end_km = z_end.virtual_distance_km;
    }
    return result;
}

SigmaAdjust adjust_sigmas(const SigmaAdjustInputs& inputs) {
    // SETPUF L48570-48604 (sigma-y) and L48635-48668 (sigma-z), REAL*4.
    R syb1 = to_real(inputs.sigma_y_begin_m, "SYB1");
    R sym1 = to_real(inputs.sigma_y_mid_m, "SYM1");
    R sye1 = to_real(inputs.sigma_y_end_m, "SYE1");
    R szb1 = to_real(inputs.sigma_z_begin_m, "SZB1");
    R szm1 = to_real(inputs.sigma_z_mid_m, "SZM1");
    R sze1 = to_real(inputs.sigma_z_end_m, "SZE1");
    const R bid = to_real(inputs.final_rise_variance_m2, "BIDFNL");
    const R sy0sq = to_real(inputs.initial_sigma_y_squared_m2, "SY0SQ");
    require_true(bid >= kZero && sy0sq >= kZero, "BIDFNL and SY0SQ must not be negative");

    SigmaAdjust result;
    // Sigma-y: sigmas must grow with time, then the store and the quadrature.
    if (syb1 > sym1) sym1 = syb1;
    if (sym1 > sye1) sye1 = sym1;
    result.stored_sigma_y_m = static_cast<double>(sye1);
    const R sysq = bid + sy0sq;
    result.sigma_y_quadrature_m2 = static_cast<double>(sysq);
    if (sysq > kZero) {
        syb1 = std::sqrt(syb1 * syb1 + sysq);
        sym1 = std::sqrt(sym1 * sym1 + sysq);
        sye1 = std::sqrt(sye1 * sye1 + sysq);
    }
    if (inputs.calm) result.minimum_sigma_y_m = static_cast<double>(sym1);

    // Sigma-z: the same treatment, only for a Gaussian vertical distribution.
    if (inputs.gaussian_vertical) {
        if (szb1 > szm1) szm1 = szb1;
        if (szm1 > sze1) sze1 = szm1;
        result.stored_sigma_z_m = static_cast<double>(sze1);
        if (bid > kZero) {
            szb1 = std::sqrt(szb1 * szb1 + bid);
            szm1 = std::sqrt(szm1 * szm1 + bid);
            sze1 = std::sqrt(sze1 * sze1 + bid);
        }
        if (inputs.calm) result.minimum_sigma_z_m = static_cast<double>(szm1);
    } else {
        result.stored_sigma_z_m = 0.0;
    }

    result.sigma_y_begin_m = static_cast<double>(syb1);
    result.sigma_y_mid_m = static_cast<double>(sym1);
    result.sigma_y_end_m = static_cast<double>(sye1);
    result.sigma_z_begin_m = static_cast<double>(szb1);
    result.sigma_z_mid_m = static_cast<double>(szm1);
    result.sigma_z_end_m = static_cast<double>(sze1);
    return result;
}

SigmaUpdateResult sigma_update(const SigmaUpdateInputs& inputs, const SigmaYCurve& sigma_y_curve,
                               const SigmaZCurve& sigma_z_curve,
                               const OriginalTerrainSigmaInputs* terrain) {
    SigmaUpdateResult result;
    result.step = sigma_step(inputs.step, sigma_y_curve, sigma_z_curve);
    if(terrain) {
        // Original SETPUF CALPUFF L48616-48631:
        // SIGTZ start/mid/end are first computed, then CTADJ2(mid),
        // SIGTZ(strained_mid,0,0,ZPB), CTADJ2(end), and SIGTZ again.
        // FRACZ1/LUP1 from the END call are later read by PUFFCT2.
        require_true(terrain->lookup!=nullptr,
                     "MCTADJ2 requires native TRELIEF/GETELEV lookups");
        require_true(result.step.gaussian_vertical,
                     "MCTADJ2 Gaussian-only sigma branch selected");
        const R grid=to_real(terrain->met_spacing_m,"native terrain DGRID");
        const R wind=to_real(terrain->wind_speed_ms,"native terrain WS");
        require_true(grid>0.0F && wind>0.0F,
                     "MCTADJ2 needs positive native grid/wind");
        const R xb=to_real(terrain->x_begin_cells,"CTADJ2 XPB");
        const R yb=to_real(terrain->y_begin_cells,"CTADJ2 YPB");
        const R xe=to_real(terrain->x_end_cells,"CTADJ2 XNEW");
        const R ye=to_real(terrain->y_end_cells,"CTADJ2 YNEW");
        const R zpb=to_real(terrain->z_begin_m,"CTADJ2 ZPB");
        const R bvf=to_real(terrain->brunt_vaisala_s,"CTADJ2 BVF");
        const R sb=to_real(inputs.step.sigma_z_start_m,"SIGZB");
        R sm=to_real(result.step.sigma_z_mid_m,"SETPUF SZM1");
        R se=to_real(result.step.sigma_z_end_m,"SETPUF SZE1");
        require_true(sm>0.0F && se>0.0F,
                     "MCTADJ2 sigma ratio denominator is zero");
        const R xm=0.5F*(xb+xe),ym=0.5F*(yb+ye);
        const auto ct=[&](R r,R endx,R endy){
            return terrain_strain({
                .sigma_ratio=r,.puff_height_start_m=zpb,
                .x_old=xb,.y_old=yb,.x_new=endx,.y_new=endy,
                .sigma_z_start_m=sb,.brunt_vaisala_s=bvf,
                .wind_speed_ms=wind,.grid_spacing_m=grid
            },*terrain->lookup);
        };
        const auto mid=ct(sb/sm,xm,ym);
        const R strained_mid=sm*to_real(mid.strain,"CTADJ2 midpoint STRAIN");
        const auto mid_sigma=sigma_z_curve(strained_mid,0.0,0.0,zpb);
        sm=curve_value(mid_sigma.value,"SETPUF terrain midpoint SZM1");
        result.step.sigma_z_mid_m=sm;
        result.step.virtual_time_z_mid_s=
            to_real(mid_sigma.virtual_time_s,"CTADJ2 midpoint VTZM1");
        result.step.virtual_distance_z_mid_km=
            to_real(mid_sigma.virtual_distance_km,"CTADJ2 midpoint VDZ M1");
        const R end_ratio=sb/se;
        const R end_sigma_unstrained=se;
        const auto end=ct(end_ratio,xe,ye);
        const R end_strain=to_real(end.strain,"CTADJ2 end STRAIN");
        const R strained_end=se*end_strain;
        const auto end_sigma=sigma_z_curve(strained_end,0.0,0.0,zpb);
        se=curve_value(end_sigma.value,"SETPUF terrain end SZE1");
        result.step.sigma_z_end_m=se;
        result.step.virtual_time_z_end_s=
            to_real(end_sigma.virtual_time_s,"CTADJ2 end VTZE1");
        result.step.virtual_distance_z_end_km=
            to_real(end_sigma.virtual_distance_km,"CTADJ2 end VDZE1");
        result.terrain=OriginalTerrainSigmaState{
            .z_mid_m=to_real(mid.puff_height_end_m,"CTADJ2 ZM1"),
            .z_end_m=to_real(end.puff_height_end_m,"CTADJ2 ZE1"),
            .fracz_end=to_real(end.fraction_beyond,"CTADJ2 FRACZ1"),
            .upslope_end=end.upslope,
            .end_ratio=end_ratio,
            .end_sigma_before_strain_m=end_sigma_unstrained,
            .end_strain=end_strain,
            .end_sigma_adjusted_m=strained_end,
            .end_sigma_after_sigtz_m=se,
            .end_virtual_distance_km=to_real(
                end_sigma.virtual_distance_km,"SETPUF original VDZE1")
        };
    }
    SigmaAdjustInputs adjust;
    adjust.sigma_y_begin_m = result.step.sigma_y_begin_m;
    adjust.sigma_y_mid_m = result.step.sigma_y_mid_m;
    adjust.sigma_y_end_m = result.step.sigma_y_end_m;
    adjust.sigma_z_begin_m = result.step.sigma_z_begin_m;
    adjust.sigma_z_mid_m = result.step.sigma_z_mid_m;
    adjust.sigma_z_end_m = result.step.sigma_z_end_m;
    adjust.final_rise_variance_m2 = inputs.final_rise_variance_m2;
    adjust.initial_sigma_y_squared_m2 = inputs.initial_sigma_y_squared_m2;
    adjust.calm = inputs.calm;
    adjust.gaussian_vertical = result.step.gaussian_vertical;
    result.adjust = adjust_sigmas(adjust);
    return result;
}

} // namespace cteas::puff
