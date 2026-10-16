#pragma once
// Stable P6E surface solar / radiation interface for the real 2022 case.
//
// Answers the three inputs HEATFX needs (calmet.for L7999-8122):
//   1. per-cell mid-timestep sine of solar elevation (SINALPC),
//   2. the MCLOUD=1 station-cloud fraction contract,
//   3. the short-wave formula itself.
//
// Units and dimensions
//   SINALPC      : dimensionless sine of the solar elevation, signed (negative
//                  before sunrise / after sunset), one REAL*4 per cell.
//                  Layout: (j*nx+i), i fastest.
//   cloud cover  : integer tenths 0..10 from the surface observation (RDSN
//                  ICC); fraction = 0.1*ICC, dimensionless.
//   QSW          : W/m**2, clipped at 0.
// Time semantics
//   The SOLAR table has 26 half-hour slots covering 23:30 of the previous day
//   to 00:30 of the next day. For an hourly timestep the original COMP code
//   selects `SINALPC(i,j) = SINALP(i,j,NHRB+2)` (L3862-3872), i.e. the slot at
//   the MIDDLE of the hour that begins at NHRB. `julian_day` and `nhrb` are the
//   beginning time of the interval, matching the CALMET.DAT field clock.
//   `base_timezone_hours` is the AXTZ offset (UTC+0000 -> 0).
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>
#include "cteas/p6e/coordlib_pj09z0.hpp"
#include "cteas/p6e/solar.hpp"
namespace cteas::p6e {
struct SurfaceSolarGrid {
    std::size_t nx=0,ny=0;
    std::vector<float> latitude_deg,longitude_east_deg;
};
// Per-cell latitude / east longitude of the grid cell centres, bit-for-bit
// equal to the original CALMET chain `MICROI -> GLOBE1 -> GLOBE -> COORDS ->
// GTPZ0 -> PJ01Z0 -> PJ09Z0` (COORDLIB GCTP 2.0.2).
//
// (XORIG,YORIG) and DGRID are in METRES, as stored in the CALMET.DAT 2.1
// control record (XORIGR = 1000*xorigkm).  MICROI keeps the projection origin
// in KILOMETRES (`xmap0 = xorigkm`) and forms each cell centre in REAL*4:
//     xkm = xmap0 + (float(i)-0.5)*dgrid*0.001        (i, j are 1-based)
// which `GLOBE`/`COORDS` then scale by 1000 m/km before the COORDLIB inverse.
// `xorigkm` is recovered from the stored metres by an exact-division round
// trip so the REAL*4 cell-centre arithmetic is reproduced, not approximated.
inline SurfaceSolarGrid surface_solar_grid(std::size_t nx,std::size_t ny,
                                           int utm_zone,float xorigin_m,
                                           float yorigin_m,float dgrid_m) {
    if(nx==0||ny==0||nx>static_cast<std::size_t>(-1)/ny||
       !std::isfinite(dgrid_m)||dgrid_m<=0.f||
       !std::isfinite(xorigin_m)||!std::isfinite(yorigin_m))
        throw std::invalid_argument("surface solar grid extent invalid");
    const UtmProjection projection=utm_north_projection(utm_zone);
    const float xmap0=static_cast<float>(static_cast<double>(xorigin_m)*0.001);
    const float ymap0=static_cast<float>(static_cast<double>(yorigin_m)*0.001);
    SurfaceSolarGrid g;
    g.nx=nx;g.ny=ny;
    g.latitude_deg.resize(nx*ny);
    g.longitude_east_deg.resize(nx*ny);
    for(std::size_t i=0;i<nx;++i)
        for(std::size_t j=0;j<ny;++j) {
            const float xkm=xmap0+(static_cast<float>(i+1U)-0.5F)*dgrid_m*0.001F;
            const float ykm=ymap0+(static_cast<float>(j+1U)-0.5F)*dgrid_m*0.001F;
            double lat=0.0,lon=0.0;
            utm_north_to_latlon_deg(projection,
                                    static_cast<double>(xkm)*1000.0,
                                    static_cast<double>(ykm)*1000.0,lat,lon);
            g.latitude_deg[j*nx+i]=static_cast<float>(lat);
            g.longitude_east_deg[j*nx+i]=static_cast<float>(lon);
        }
    return g;
}
// AXTZ (character*8 in CALMET.DAT, e.g. "UTC+0000") -> whole-hour offset.
// Sub-hour offsets round to the nearest hour, matching the REAL*4 arithmetic
// of the original IBTZ usage in SOLAR.
inline int timezone_hours_from_axtz(const std::string& axtz) {
    if(axtz.size()!=8U||axtz.compare(0U,3U,"UTC")!=0||
       (axtz[3]!='+'&&axtz[3]!='-'))
        throw std::invalid_argument("unsupported AXTZ "+axtz);
    const int sign=axtz[3]=='-'?-1:1;
    const int hours=std::stoi(axtz.substr(4U,2U));
    const int minutes=std::stoi(axtz.substr(6U,2U));
    return sign*(hours+(minutes>=30?1:0));
}
// Mid-timestep sine of solar elevation for one hourly interval, per cell.
inline std::vector<float> sinalpc_grid(const SurfaceSolarGrid& g,int julian_day,
                                       int begin_hour,int base_timezone_hours) {
    if(begin_hour<0||begin_hour>23)
        throw std::invalid_argument("begin hour outside 0..23");
    Grid solar;
    solar.nx=g.nx;solar.ny=g.ny;
    solar.lat=g.latitude_deg;
    solar.lon_east=g.longitude_east_deg;
    const auto table=calculate(solar,julian_day,base_timezone_hours);
    const auto slot=static_cast<std::size_t>(begin_hour)+1U; // SINALP(NHRB+2)
    std::vector<float> out(g.nx*g.ny,0.f);
    for(std::size_t j=0;j<g.ny;++j)
        for(std::size_t i=0;i<g.nx;++i)
            out[j*g.nx+i]=table.at(slot,i,j);
    return out;
}
// MCLOUD=1 station-cloud branch of HEATFX L8061-8064:
//   ccfrac = 0.1*ICC(NEARS(i,j))
// `nearest_station_index` is 1-based as in the original NEARS array.
// Missing (999) or out-of-range cloud cover fails closed.
inline float heatfx_cloud_fraction(int opaque_cloud_tenths) {
    if(opaque_cloud_tenths<0||opaque_cloud_tenths>10)
        throw std::invalid_argument(
            "HEATFX MCLOUD=1 cloud cover must be 0..10 tenths");
    return 0.1f*static_cast<float>(opaque_cloud_tenths);
}
// HEATFX L8066-8069. Constants are HA1 HA2 HB1 HB2 of /HFLUX/; the real case
// uses the source defaults HA1=990, HA2=-30, HB1=-0.75, HB2=3.4 (met.lst).
inline float heatfx_shortwave(float sinalpc,float cloud_fraction,
                              float ha1=990.f,float ha2=-30.f,
                              float hb1=-0.75f,float hb2=3.4f) {
    if(!std::isfinite(sinalpc)||!std::isfinite(cloud_fraction)||
       cloud_fraction<0.f||cloud_fraction>1.f)
        throw std::invalid_argument("HEATFX short-wave inputs invalid");
    float value=(ha1*sinalpc+ha2)*(1.f+hb1*std::pow(cloud_fraction,hb2));
    if(value<0.f)value=0.f;
    return value;
}
} // namespace cteas::p6e
