#pragma once
// Original-source-only reconstruction of full on-land SIMILT, IPSIFCN=0.
// Fortran: calmet.for L30097-L30370, PSIUD L35629-L35672.
// Original SIMILT state is mostly REAL*4. Function PSIUD and its arguments
// are explicitly REAL*8. Preserve this boundary rather than converting
// everything to float or everything to double. This implementation does not
// import any earlier OMP-developed CTEAS physics algorithm.
//
// Unsupported: IPSIFCN=1 (PSIUC), overwater, more than one station, or the
// generation of EL/ZI/ZICONV by upstream MIXHTST/ELUSTR. Those must arrive as
// original-source-validated REAL*4 state and be ported separately.
#include "cteas/p6d_rebuild/wind1_real4.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>

namespace cteas::p6d_rebuild {

struct SimiltReal4Input {
    Real4 latitude_deg{},anemometer_height_m{},roughness_m{};
    Real4 measured_u_mps{},measured_v_mps{};
    Real4 monin_obukhov_length_m=10000.f;
    Real4 mixing_height_m=10000.f;
    Real4 minimum_mixing_height_m=10000.f;
    int ipsifcn=0;
    std::array<Real4,10> zface_m{
        0.f,20.f,40.f,80.f,160.f,320.f,640.f,1200.f,2000.f,3000.f
    };
};
struct SimiltReal4Result {
    StationWind profile;
    int levels_filled=0;
};

// Original PSIUD is REAL*8, including ZL, X, Y, F, C and the return value.
// Fortran REAL literals are promoted when combined with REAL*8 expressions.
inline double original_psiud_real8(double zl) {
    if(!std::isfinite(zl))throw std::invalid_argument("PSIUD nonfinite ZL");
    if(zl<0.0){
        const double x=std::pow(1.0-16.0*zl,0.25);
        const double psik=2.0*std::log((1.0+x)/2.0)
            +std::log((1.0+x*x)/2.0)-2.0*std::atan(x)
            +2.0*std::atan(1.0);
        const double y=std::pow(1.0-10.15*zl,static_cast<double>(0.3333f));
        const double sqr3=static_cast<double>(std::sqrt(3.f));
        const double psic=1.5*std::log((1.0+y+y*y)/3.0)
            -sqr3*std::atan((1.0+2.0*y)/sqr3)
            +4.0*std::atan(1.0)/sqr3;
        const double f=zl*zl/(1.0+zl*zl);
        return (1.0-f)*psik+f*psic;
    }
    const double c=std::min(50.0,0.35*zl);
    return -((1.0+zl)+static_cast<double>(0.6667f)*
             (zl-14.28)/std::exp(c)+8.525);
}

inline SimiltReal4Result similt_source_real4(const SimiltReal4Input& in){
    if(in.ipsifcn!=0)
        throw std::invalid_argument("PSIUC/COARE IPSIFCN=1 not source-ported");
    if(!(std::isfinite(in.latitude_deg)&&
         std::isfinite(in.anemometer_height_m)&&
         std::isfinite(in.roughness_m)&&
         std::isfinite(in.measured_u_mps)&&std::isfinite(in.measured_v_mps)&&
         std::isfinite(in.monin_obukhov_length_m)&&
         std::isfinite(in.mixing_height_m)&&
         std::isfinite(in.minimum_mixing_height_m))||
       in.anemometer_height_m<=in.roughness_m||
       in.roughness_m<=0.f)
        throw std::invalid_argument("unsupported SIMILT station state");
    SimiltReal4Result result;
    result.profile.u_mps.fill(999999.f);
    result.profile.v_mps.fill(999999.f);
    Real4 eladj=in.monin_obukhov_length_m;
    if(std::abs(eladj)<real4(5.f*in.roughness_m)){
        if(eladj<0.f)eladj=real4(-5.f*in.roughness_m);
        else eladj=real4(5.f*in.roughness_m);
    }
    const Real4 elinv=std::abs(eladj)>=10000.f
        ?0.f:real4(1.f/eladj);
    const Real4 ws1=real4(std::sqrt(
        real4(in.measured_u_mps*in.measured_u_mps)+
        real4(in.measured_v_mps*in.measured_v_mps)));
    const Real4 angle=real4(270.f-real4(
        std::atan2(in.measured_v_mps,in.measured_u_mps)*57.2957795f));
    Real4 wd1=real4(std::fmod(angle,360.f));
    if(wd1==0.f)wd1=360.f;
    const Real4 xlnz1z0=real4(std::log(
        real4(in.anemometer_height_m/in.roughness_m)));
    auto psi=[&](Real4 height) -> Real4 {
        if(std::abs(elinv)<0.00005f)return 0.f;
        // In Fortran: r8=zzanem/eladj (both REAL*4); PSIM=PSIUD(r8),
        // the function returns REAL*8 then is stored to REAL*4.
        const Real4 zl=real4(height/eladj);
        return real4(static_cast<Real4>(
            original_psiud_real8(static_cast<double>(zl))));
    };
    const Real4 psim1=psi(in.anemometer_height_m);
    const std::array<Real4,9> eltbli{
        -0.03333333f,-0.01f,-0.0027027f,0.f,0.002857f,
        0.007692f,0.0166667f,0.05f,0.1111111f};
    const std::array<Real4,9> dhtbl2{12.f,10.f,9.f,12.f,18.f,28.f,35.f,38.f,39.f};
    Real4 dh200=dhtbl2.back();
    if(std::abs(elinv)<0.00005f) {
        dh200=dhtbl2[3];
    }else{
        for(std::size_t i=0;i<9;++i){
            if(eltbli[i]>=elinv){
                if(i==0){dh200=dhtbl2[0];}
                else{
                    dh200=real4(dhtbl2[i-1]+real4(
                        real4(real4(dhtbl2[i]-dhtbl2[i-1])*
                              real4(elinv-eltbli[i-1]))/
                        real4(eltbli[i]-eltbli[i-1])));
                }
                break;
            }
        }
    }
    const Real4 d1=1.58f,d2=1.f,ztbl2=200.f;
    auto turning_angle=[&](Real4 height) -> Real4 {
        const Real4 exponent=real4(-real4(d2*height)/ztbl2);
        return real4(real4(dh200*d1)*
            real4(1.f-real4(std::exp(exponent))));
    };
    const Real4 dzan=turning_angle(in.anemometer_height_m);
    const Real4 cutoff=std::max(real4(in.mixing_height_m+0.001f),
                                in.minimum_mixing_height_m);
    for(std::size_t k=0;k<K;++k){
        if(in.zface_m[k+1]>cutoff)break;
        const Real4 mid=real4(0.5f*real4(in.zface_m[k+1]+in.zface_m[k]));
        const Real4 xlnzz0=real4(std::log(real4(mid/in.roughness_m)));
        const Real4 psim=psi(mid);
        const Real4 numerator=real4(ws1*real4(xlnzz0-psim));
        const Real4 denominator=real4(xlnz1z0-psim1);
        if(denominator==0.f)
            throw std::invalid_argument("SIMILT zero stability normalization");
        const Real4 ws=real4(numerator/denominator);
        const Real4 dwd=turning_angle(mid);
        Real4 wd{};
        if(in.latitude_deg>0.f){
            wd=real4(real4(wd1+dwd)-dzan);
            if(wd>360.f)wd=real4(wd-360.f);
        }else{
            wd=real4(real4(wd1-dwd)+dzan);
            if(wd<=0.f)wd=real4(360.f+wd);
        }
        const Real4 wdrad=real4(0.0174533f*wd);
        result.profile.u_mps[k]=real4(-real4(ws*real4(std::sin(wdrad))));
        result.profile.v_mps[k]=real4(-real4(ws*real4(std::cos(wdrad))));
        result.levels_filled=static_cast<int>(k)+1;
    }
    return result;
}
} // namespace cteas::p6d_rebuild
