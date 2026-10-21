#pragma once
// S4-Q: strictly input-level CALMET SETCOM FCORIOL and COMP WATER WS10
// source contract. This is NOT a native G14/G26 physical-water authorization.
// Original calmet.for @437f43bb L9605-9614 and L32715-32716.
// When FCORIOL>998 original calls GLOBE for each latitude; until that
// projection is independently validated we REJECT rather than silently
// substituting a constant or a homegrown approximate WGS84 inverse.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G37WaterWindSource {
    int nx=0,ny=0,nz=0;
    std::vector<int> landuse;
    int iwat1=50,iwat2=55;
    std::vector<float> final_diagno_u_mps,final_diagno_v_mps;
    float original_fcoriol=0.f;
    // This struct may be created from independently traced original U/V
    // for proof of arithmetic, or from current native G24 final wind.
    // Neither source alone licenses full physics or source-site accuracy.
    bool explicit_reference_only=false;
};
struct G37WaterWindResult {
    std::vector<float> fcori_s_inv,ws10_mps;
    std::size_t water_cells=0;
    bool original_water_physics_ready=false;
    bool g14_g26_production_ready=false;
};
inline G37WaterWindResult
g37_original_fcori_final_wind1_surface_source(const G37WaterWindSource& a) {
    if(!a.explicit_reference_only)
        throw std::invalid_argument("G37 WATER wind/FCORI is reference-only");
    const auto nx=static_cast<std::size_t>(a.nx);
    const auto ny=static_cast<std::size_t>(a.ny);
    const auto nz=static_cast<std::size_t>(a.nz);
    if(nx<2||ny<2||nz!=9||nx>400||ny>400||
       nx>250000/ny||a.landuse.size()!=nx*ny||
       a.iwat1>a.iwat2||a.iwat1!=50||a.iwat2!=55||
       a.final_diagno_u_mps.size()!=nx*ny*nz||
       a.final_diagno_v_mps.size()!=nx*ny*nz)
        throw std::invalid_argument("G37 first-level source array or historical water LU malformed");
    if(!std::isfinite(a.original_fcoriol)||
       a.original_fcoriol>998.f)
        throw std::invalid_argument(
            "G37 latitude-varying original GLOBE FCORI requires separate vendor projection parity");
    // Literal original SETCOM when FCORIOL is an explicitly supplied value:
    // fcori(i,j)=max(abs(fcoriol),0.25e-4).
    const float fcori=std::max(std::abs(a.original_fcoriol),0.25e-4f);
    if(!std::isfinite(fcori)||fcori<=0.f)
        throw std::invalid_argument("G37 original FCORIOL invalid");
    G37WaterWindResult out;
    out.fcori_s_inv.assign(nx*ny,fcori);
    out.ws10_mps.assign(nx*ny,0.f);
    for(std::size_t k=0;k<nx*ny;++k) {
        if(a.landuse[k]<a.iwat1||a.landuse[k]>a.iwat2)continue;
        const float u=a.final_diagno_u_mps[k];
        const float v=a.final_diagno_v_mps[k];
        if(!std::isfinite(u)||!std::isfinite(v))
            throw std::invalid_argument("G37 selected original water wind nonfinite");
        // Original COMP calls WATER(u,v,...) where WATER's u10/v10
        // rank-two dummy aliases the FIRST of nine source wind planes.
        // Original REAL*4 sqrt(u10(i,j)**2+v10(i,j)**2).
        const float ws=std::sqrt(u*u+v*v);
        if(!std::isfinite(ws))
            throw std::invalid_argument("G37 native original first-level WS10 overflow");
        out.ws10_mps[k]=ws;
        ++out.water_cells;
    }
    if(out.water_cells==0)
        throw std::invalid_argument("G37 selected WATER source has no water");
    return out;
}
} // namespace cteas::calmet::p6g
