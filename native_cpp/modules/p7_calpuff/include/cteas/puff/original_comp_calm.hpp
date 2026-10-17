#pragma once
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cteas::puff {

// CALPUFF 7.2.1 COMP L10516-10528, immediately after ADVECT/RISEWIND
// and before FSTEP. This is *transport* handling, not SETPUF's later
// IDOPTY=IDOPTZ=1 dispersion branch (which must be separately reconstructed).
// Original Fortran REAL*4 and original U/V asymmetry are intentional.
struct OriginalCompCalmTransport {
    float u_ms=0.0F;
    float v_ms=0.0F;
    float wind_speed_ms=0.0F;
    bool calm=false;
};
[[nodiscard]] inline OriginalCompCalmTransport original_comp_calm_transport(
    float u_ms,float v_ms,float wind_speed_ms,float wscalm_ms) {
    if(!std::isfinite(u_ms)||!std::isfinite(v_ms)||
       !std::isfinite(wind_speed_ms)||!std::isfinite(wscalm_ms)||
       wind_speed_ms<0.0F||wscalm_ms<=0.0F)
        throw std::invalid_argument("COMP requires finite nonnegative winds and positive WSCALM");
    // The vendor does NOT replace all speeds below WSCALM by WSCALM.
    // It uses UCALM=0.001 m/s as a numerical guard, and only changes
    // VADV when abs(VADV) is itself below UCALM. UADV is unchanged.
    OriginalCompCalmTransport out{u_ms,v_ms,wind_speed_ms,false};
    constexpr float ucalm=0.001F;
    if(out.wind_speed_ms<wscalm_ms) {
        out.calm=true;
        if(std::abs(out.v_ms)<ucalm)out.v_ms=ucalm;
        out.wind_speed_ms=std::max(out.wind_speed_ms,ucalm);
    }
    return out;
}

} // namespace cteas::puff
