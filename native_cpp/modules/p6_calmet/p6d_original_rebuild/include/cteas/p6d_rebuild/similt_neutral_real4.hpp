#pragma once
// Independent source-first port: the exact WIND1-invoked *neutral* SIMILT
// route in CALMET 6.5.0 Level 150223, calmet.for L30097-L30370.
//
// In WIND1 L36171-L36195: EL=10000, ZI=10000; IPSIFCN=0.
// Original SIMILT uses REAL*4 except PSIUD's explicitly REAL*8 argument and
// result. PSIUD is NOT called on this neutral route (ELINV=0).
// Other stability branches are UNSUPPORTED here and must be ported and tested
// against the original before replacing full DIAGI. No legacy CTEAS headers.
#include "cteas/p6d_rebuild/wind1_real4.hpp"
#include <array>
#include <cmath>
#include <stdexcept>

namespace cteas::p6d_rebuild {
struct NeutralSimiltInput {
    Real4 latitude_deg{},anemometer_height_m{},roughness_m{};
    Real4 measured_u_mps{},measured_v_mps{};
    std::array<Real4,10> zface_m{
        0.f,20.f,40.f,80.f,160.f,320.f,640.f,1200.f,2000.f,3000.f
    };
};
inline StationWind original_neutral_similt_profile(
    const NeutralSimiltInput& in) {
    if(!(std::isfinite(in.latitude_deg)&&std::isfinite(in.anemometer_height_m)&&
         std::isfinite(in.roughness_m)&&std::isfinite(in.measured_u_mps)&&
         std::isfinite(in.measured_v_mps))||
       in.latitude_deg==0.f||in.anemometer_height_m<=in.roughness_m||
       in.roughness_m<=0.f)
        throw std::invalid_argument("selected SIMILT original neutral controls invalid");
    StationWind out;
    const Real4 ws10=real4(std::sqrt(
        real4(in.measured_u_mps*in.measured_u_mps)+
        real4(in.measured_v_mps*in.measured_v_mps)));
    if(ws10<0.0001f){
        out.u_mps.fill(0.f);
        out.v_mps.fill(0.f);
        return out; // WIND1 L36117-L36126 bypasses original SIMILT on calm.
    }
    const Real4 factor=57.2957795f;
    const Real4 angle=real4(270.f-real4(
        std::atan2(in.measured_v_mps,in.measured_u_mps)*factor));
    Real4 wd1=real4(std::fmod(angle,360.f));
    if(wd1==0.f)wd1=360.f;
    const Real4 xlnz1z0=real4(std::log(real4(
        in.anemometer_height_m/in.roughness_m)));
    const Real4 dh200=12.f;
    const Real4 d1=1.58f,d2=1.f,ztbl2=200.f;
    const Real4 dzan=real4(real4(dh200*d1)*
        real4(1.f-real4(std::exp(real4(
            -real4(d2*in.anemometer_height_m)/ztbl2)))));
    for(std::size_t k=0;k<K;++k){
        const Real4 original_mid=real4(0.5f*real4(
            in.zface_m[k+1]+in.zface_m[k]));
        if(in.zface_m[k+1]>10000.001f)
            throw std::invalid_argument("neutral SIMILT cutoff exceeded");
        if(!(original_mid>in.roughness_m))
            throw std::invalid_argument("neutral SIMILT level intersects z0");
        const Real4 xlnzz0=real4(std::log(real4(
            original_mid/in.roughness_m)));
        const Real4 ws=real4(real4(ws10*xlnzz0)/xlnz1z0);
        const Real4 dwd=real4(real4(dh200*d1)*
            real4(1.f-real4(std::exp(real4(
                -real4(d2*original_mid)/ztbl2)))));
        Real4 wd{};
        if(in.latitude_deg>0.f){
            wd=real4(real4(wd1+dwd)-dzan);
            if(wd>360.f)wd=real4(wd-360.f);
        }else{
            wd=real4(real4(wd1-dwd)+dzan);
            if(wd<=0.f)wd=real4(360.f+wd);
        }
        const Real4 wdrad=real4(0.0174533f*wd);
        out.u_mps[k]=real4(-real4(ws*real4(std::sin(wdrad))));
        out.v_mps[k]=real4(-real4(ws*real4(std::cos(wdrad))));
    }
    return out;
}
} // namespace cteas::p6d_rebuild
