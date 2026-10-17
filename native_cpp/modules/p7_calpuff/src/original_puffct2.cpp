#include "cteas/puff/original_puffct2.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cteas::puff {
OriginalPuffct2Result original_puffct2(
    const OriginalPuffct2Step& s, float frac) {
    for(float x:{frac,s.x_begin_m,s.y_begin_m,s.z_begin_m,
                 s.x_end_m,s.y_end_m,s.z_end_m,s.terrain_fraction}) {
        if(!std::isfinite(x))
            throw std::invalid_argument(
                "original PUFFCT2 requires finite REAL4 /CURRENT/ and FRAC");
    }
    // Original CALPUFF v7.2.1 PUFFCT2 L21070-21093, preserving the
    // REAL*4 evaluation order and the *asymmetric* upslope/downslope
    // FRACZ1 branches. No interpolation shortcuts or FRAC clipping.
    const float x=s.x_begin_m+frac*(s.x_end_m-s.x_begin_m);
    const float y=s.y_begin_m+frac*(s.y_end_m-s.y_begin_m);
    float z=0.0F;
    const float one=1.0F, zero=0.0F;
    if(s.upslope) {
        if(s.terrain_fraction<=zero) {
            z=s.z_begin_m;
        } else {
            float jump=s.z_end_m-s.z_begin_m;
            if(s.terrain_fraction<one)
                jump=jump/s.terrain_fraction;
            z=s.z_begin_m+std::min(frac,s.terrain_fraction)*jump;
        }
    } else {
        if(s.terrain_fraction>=one) {
            z=s.z_begin_m;
        } else {
            float jump=s.z_end_m-s.z_begin_m;
            if(s.terrain_fraction>zero)
                jump=jump/(one-s.terrain_fraction);
            z=s.z_begin_m+std::max(zero,(frac-s.terrain_fraction))*jump;
        }
    }
    if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))
        throw std::overflow_error("original PUFFCT2 REAL4 output overflow");
    return {x,y,z};
}
OriginalMctadj2ReceptorHeight original_mctadj2_receptor_height(
    const OriginalPuffct2Result& puff,float hgr,float zfinal,
    const OriginalMctadj2ReceptorTerrain& t) {
    for(float v:{puff.x_m,puff.y_m,puff.z_m,hgr,zfinal,
                 t.receptor_ground_elevation_msl,
                 t.terrain_peak_elevation_msl,t.terrain_under_puff_msl,
                 t.brunt_vaisala_s,t.wind_speed_ms,t.receptor_height_m})
        if(!std::isfinite(v))
            throw std::invalid_argument(
                "PUFRECS MCTADJ2 requires finite actual terrain inputs");
    if(t.wind_speed_ms<=0.0F)
        throw std::invalid_argument(
            "PUFRECS MCTADJ2 requires positive native UAVG");
    // Original PUFRECS L5324–5331 for selected MTRANS=1.
    float zpr=puff.z_m;
    if(zfinal>0.0F)zpr=zpr*hgr/zfinal;
    else zpr=0.0F;
    float pole=t.receptor_height_m;
    // Original L5333–5359: BVF=0 leaves receptor pole unchanged.
    if(t.brunt_vaisala_s>0.0F) {
        const float dsel=t.terrain_peak_elevation_msl-
                         t.wind_speed_ms/t.brunt_vaisala_s;
        const float dsh=std::max(0.0F,dsel-t.terrain_under_puff_msl);
        const float zdiff=t.receptor_ground_elevation_msl-dsel;
        if(dsh==0.0F) {
            if(zdiff<0.0F)
                pole=std::max(0.0F,t.receptor_height_m+zdiff);
        } else {
            if(zdiff<0.0F)
                pole=std::max(0.0F,t.receptor_height_m+
                    t.receptor_ground_elevation_msl-t.terrain_under_puff_msl);
            else
                pole=t.receptor_height_m+dsh;
        }
    }
    zpr=std::max(zpr,0.0F);
    if(!std::isfinite(zpr)||!std::isfinite(pole))
        throw std::overflow_error("PUFRECS MCTADJ2 receptor height overflow");
    return {zpr,pole};
}
} // namespace cteas::puff
