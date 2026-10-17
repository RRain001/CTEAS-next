#pragma once
// CALMET 6.5.0 SURFVAR (L12544-13064) highly scoped selected dry path.
// NOOBS=0, ITPROG=0, IRHPROG=0, NPSTA=0, NSSTA=1, NOWSTA=0,
// land-only single-station interpolation.
//
// IALL (source L12544, L12610, L12878-12883):
//   IALL=0  temperature only; the routine RETURNS before RH/IPCODE, so the
//           caller's IRH2D/IPCODE2D are left untouched.
//   IALL=1  temperature + RH + IPCODE. This is the COMP real-case call
//           (L4567 passes IALL=1); DIAGNO's terrain pre-step passes IALL=0
//           (L5610).
//   IALL=2  all surface variables but WITHOUT the IAVET temperature average.
//   TEMP2D is IDENTICAL for IALL=0 and IALL=1: the only IALL conditions that
//   touch temperature are `if(iall.ne.2)temp2d(i,j)=tprog(i,j,1)` (ITPROG=2
//   only) and `if(iavet.eq.1.and.iall.ne.2)call avetmp(...)`.
// IAVET (source L12878-12881): when 1, AVETMP upwind-averages TEMP2D using the
//   diagnostic wind field, so U/V become a required input.
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>
#include "cteas/p6e/avetmp.hpp"
#include "cteas/p6e/surfvar_multistation.hpp"
namespace cteas::p6e {
struct ObservedSurface {
    std::size_t nx=0,ny=0;
    float station_temp_k=0.0f;
    int station_rh_percent=9999;
    int npsta=0,noobs=0,itprog=0,irhprog=0,nowsta=0;
    bool land_only=true,average_temperature=false;
    // IALL as in the original; default 1 is the COMP real-case call.
    int iall=1;
    // Required only when average_temperature (IAVET=1) and iall!=2.
    std::vector<float> u_ms,v_ms;
    float dgrid_m=100.f;
    int mnmdav=1;
    float hafang_deg=30.f;
    // Preserve source CALMET SURFVAR's single-station REAL*4 interpolation:
    // even one station uses (wt * observed_temp) / wt within TRADKM.
    // Enable only with actual station coordinates and validated met.inp controls.
    bool preserve_single_station_weight_rounding=false;
    float station_x_m=0.f,station_y_m=0.f,tradkm=500.f;
    int irad=1,numts=5;
};
struct SurfaceState {
    std::size_t nx,ny;
    std::vector<float> temp_k;
    // Empty when IALL=0, because the original returns before filling them.
    std::vector<int> rh_percent,ipcode;
};
inline SurfaceState surfvar_one_station(const ObservedSurface& s) {
    if(s.nx==0||s.ny==0||s.nx>static_cast<std::size_t>(-1)/s.ny||
       s.npsta!=0||s.noobs!=0||s.itprog!=0||s.irhprog!=0||
       s.nowsta!=0||!s.land_only||(s.iall!=0&&s.iall!=1&&s.iall!=2))
        throw std::invalid_argument("SURFVAR unsupported selected-case switch");
    if(!std::isfinite(s.station_temp_k)||
       s.station_temp_k<180.0f||s.station_temp_k>350.0f||
       (s.station_rh_percent!=9999 &&
        (s.station_rh_percent<0||s.station_rh_percent>100)))
        throw std::invalid_argument("SURFVAR invalid observed value");
    const auto n=s.nx*s.ny;
    // With exactly one eligible station and no water interpolation,
    // all cells select that station, regardless of radius or IRAD.
    // Missing observed RH invokes original 80% land fallback.
    const int rh=s.station_rh_percent==9999?80:s.station_rh_percent;
    std::vector<float> temperature(n,s.station_temp_k);
    if(s.preserve_single_station_weight_rounding) {
        if(!std::isfinite(s.station_x_m)||!std::isfinite(s.station_y_m)||
           !std::isfinite(s.tradkm)||s.tradkm<0.f||
           !std::isfinite(s.dgrid_m)||s.dgrid_m<=0.f||
           (s.irad!=1&&s.irad!=2)||s.numts<=0)
            throw std::invalid_argument("SURFVAR single-station source weighting controls invalid");
        SurfvarMultistationInput m;
        m.nx=s.nx;m.ny=s.ny;m.dgrid_m=s.dgrid_m;
        // Source RDSURF/TRADKM: km -> grid-cell radius.
        m.trad_grid=(s.tradkm*1000.f)/s.dgrid_m;
        m.irad=s.irad;m.numts=s.numts;
        m.stations.push_back(ObservedSurfaceStation{
            s.station_x_m,s.station_y_m,s.station_temp_k,s.station_rh_percent});
        temperature=surfvar_multistation(m).temp2d_k;
    }
    if(s.average_temperature&&s.iall!=2) {
        // IAVET=1: SURFVAR L12878-12881 calls AVETMP with the diagnostic wind.
        if(s.u_ms.size()!=n||s.v_ms.size()!=n)
            throw std::invalid_argument(
                "SURFVAR IAVET=1 requires the diagnostic u/v field");
        AvetmpInput a;
        a.nx=s.nx;a.ny=s.ny;a.mnmdav=s.mnmdav;a.hafang_deg=s.hafang_deg;
        a.dgrid_m=s.dgrid_m;a.u_ms=s.u_ms;a.v_ms=s.v_ms;
        a.temperature_k=temperature;
        temperature=avetmp(a);
    }
    if(s.iall==0)return {s.nx,s.ny,std::move(temperature),{},{} };
    // Original default initialized IPCODE2D=0; NPSTA=0 skips rain input.
    // This is NOT qualified meteorological precipitation forcing.
    return {s.nx,s.ny,std::move(temperature),
            std::vector<int>(n,rh),std::vector<int>(n,0)};
}
} // namespace cteas::p6e
