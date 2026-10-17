#include "cteas/puff/rise_wind.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = AdvectionReal;

constexpr R kZero = 0.0F;
constexpr R kOne = 1.0F;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7W RISEWIND: " + message);
}

R to_real(double value, const char* what) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(std::string("P7W RISEWIND: ") + what + " must be finite");
    }
    return static_cast<R>(value);
}

} // namespace

RiseWindResult transitional_rise_wind(const RiseWindInputs& inputs,
                                      const RiseHeightLookup& rise_height,
                                      const StepWindLookup& step_wind) {
    // RISEWIND (calpuff.for L67162-67300), REAL*4.
    require_true(static_cast<bool>(rise_height), "a gradual-rise lookup must be provided");
    require_true(static_cast<bool>(step_wind), "an advective-wind lookup must be provided");
    require_true(inputs.iterations >= 1, "NCOUNT must be at least 1");
    require_true(inputs.step_seconds > 0.0, "the step duration must be positive");

    // The vendor's ucalm is this routine's own data value.
    const R ucalm = static_cast<R>(kRiseWindCalmSpeedMs);

    // Wind at final rise.
    R ufnl = to_real(inputs.u_final_ms, "the final-rise u");
    R vfnl = to_real(inputs.v_final_ms, "the final-rise v");

    // Puff top/bottom at the start of the step (gradual rise).
    const R xfinal = to_real(inputs.final_distance_m, "the final-rise distance");
    const R zfinal = to_real(inputs.final_height_m, "the final-rise height");
    const R dzb = to_real(inputs.dz_m, "dzb");
    const R dt = to_real(inputs.step_seconds, "the step duration");
    R xbeg = to_real(inputs.start_distance_m, "the start distance");
    R rbeg = xbeg < xfinal ? to_real(rise_height(static_cast<double>(xbeg)), "the rise height")
                           : zfinal;
    R rtop = rbeg + dzb;
    R rbot = std::max(rbeg - dzb, kZero);

    // Wind at the beginning of the step during the rise. The vendor overwrites
    // its WS argument here, so the incoming speed only has to be finite.
    (void)to_real(inputs.wind_speed_ms, "the incoming wind speed");
    auto begin = step_wind(static_cast<double>(rbot), static_cast<double>(rtop));
    const R ub = to_real(begin.u_ms, "the start-of-step u");
    const R vb = to_real(begin.v_ms, "the start-of-step v");
    const R wsb = std::sqrt(ub * ub + vb * vb);
    R ws = std::max(wsb, ucalm);
    R uadv = ufnl;
    R vadv = vfnl;

    int icount = 0;
    for (;;) {
        ++icount;

        // Step length for the current wind speed.
        const R dxb = ws * dt;

        // Puff range from the beginning to the end of the step (rise only).
        const R xend = xbeg + dxb;
        const R rend = xend < xfinal ? to_real(rise_height(static_cast<double>(xend)), "the rise")
                                     : zfinal;
        if (rend >= rbeg) {
            // Rising.
            rbot = rbeg - dzb;
            rtop = rend + dzb;
        } else {
            // Falling (the V6.23 trap: it may lead to ZBOT > ZTOP in ADVECT).
            rbot = rend - dzb;
            rtop = rbeg + dzb;
        }
        rbot = std::max(rbot, kZero);

        // Average wind in the rise layer.
        const auto average = step_wind(static_cast<double>(rbot), static_cast<double>(rtop));
        const R ugr = to_real(average.u_ms, "the rise-layer u");
        const R vgr = to_real(average.v_ms, "the rise-layer v");

        // Average wind during the step.
        if (xend > xfinal) {
            const R ffinal = kOne - xfinal / xend;
            uadv = (kOne - ffinal) * ugr + ffinal * ufnl;
            vadv = (kOne - ffinal) * vgr + ffinal * vfnl;
        } else {
            uadv = ugr;
            vadv = vgr;
        }
        ws = std::sqrt(uadv * uadv + vadv * vadv);

        // Refine the estimate of the average wind (limited by NCOUNT).
        if (icount >= inputs.iterations) break;
    }

    RiseWindResult result;
    result.u_ms = static_cast<double>(uadv);
    result.v_ms = static_cast<double>(vadv);
    result.wind_speed_ms = static_cast<double>(ws);
    result.passes = icount;
    return result;
}

} // namespace cteas::puff
