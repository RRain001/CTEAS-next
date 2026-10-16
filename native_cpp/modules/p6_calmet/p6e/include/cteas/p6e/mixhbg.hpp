#pragma once
// CALMET v6.5.0 MIXHBG L11304-11545: Batchvarova-Gryning (1991,1994)
// convective mixing height with the original analytical "false images"
// growth solution, THRESH threshold flux, IZICRLX collapse/relaxation
// switch and the two encroachment limits (EL > -500 m and EL <= -500 m).
//
// This is the ILAPSE=2 entry point only: the potential-temperature lapse
// rate above the previous mixing height is supplied by the caller (from the
// selected AA/BB upper-air sounding). The MM5 MIXDT2 lapse search used by
// ILAPSE=1 is deliberately NOT reproduced and the caller must not select it.
//
// Faithful reproduction notes:
//  - REAL*4 arithmetic and the original constants rho=1.2, cp=1005,
//    vonk=0.4, ca=0.2, cb=2.5, cc=8 are preserved.
//  - the original trailing clamp `zicbg=min(h,zimx)` then
//    `zicbg=max(h,zimn)` (both using h) is reproduced verbatim.
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace cteas::p6e {
struct MixhbgInput {
    float wt_mks=0.f;            // surface buoyancy flux <w'theta_v'> (m K/s)
    float gamma_kperm=0.001f;    // lapse rate above previous Zic (K/m)
    float threshold_wm2perm=0.f; // THRESHL threshold buoyancy flux (W/m2/m)
    float zimax_m=2500.f, zimin_m=50.f;
    float ustar_ms=0.2f;         // friction velocity (m/s)
    float el_m=-100.f;           // Monin-Obukhov length (m, negative unstable)
    float zicbgold_m=0.f;        // previous-hour convective mixing height (m)
    float tk_k=290.f;            // surface air temperature (K)
    int izicrlx=0;               // 0 total collapse, 1 relax to equilibrium
    float tzicrlx_s=800.f;       // user relaxation time (s)
    float dptmin_kperm=0.001f;   // minimum stable potential-temperature lapse
    int timestep_s=3600;         // GEN.MET NSECDT timestep (s)
};
struct MixhbgResult { float ziconv_m, gamma_kperm; };
inline float mixhbg_fbg(float zeta,float zetap,float r1,float r2,float r3){
    return zeta*zeta+r1*zeta+r2*std::log(zeta)+r3*std::log(zetap);
}
inline MixhbgResult mixhbg_lapse2(const MixhbgInput& a){
    if(!std::isfinite(a.wt_mks)||!std::isfinite(a.gamma_kperm)||
       !std::isfinite(a.threshold_wm2perm)||a.threshold_wm2perm<0.f||
       !std::isfinite(a.zimax_m)||a.zimax_m<=0.f||
       !std::isfinite(a.zimin_m)||a.zimin_m<0.f||a.zimin_m>=a.zimax_m||
       !std::isfinite(a.ustar_ms)||a.ustar_ms<0.f||
       !std::isfinite(a.el_m)||
       !std::isfinite(a.zicbgold_m)||a.zicbgold_m<0.f||
       !std::isfinite(a.tk_k)||a.tk_k<=0.f||
       !std::isfinite(a.tzicrlx_s)||a.tzicrlx_s<=0.f||
       !std::isfinite(a.dptmin_kperm)||a.dptmin_kperm<=0.f||
       a.timestep_s<=0||(a.izicrlx!=0&&a.izicrlx!=1))
        throw std::invalid_argument("MIXHBG invalid physical inputs or mode");
    constexpr float g=9.81f,rho=1.2f,cp=1005.f;
    constexpr float vonk=0.4f,ca=0.2f,cb=2.5f,cc=8.f;
    MixhbgResult result{0.f,a.gamma_kperm};
    const float h0=std::max(a.zicbgold_m,a.zimin_m);
    const float wto=a.threshold_wm2perm*h0/(rho*cp);
    const float wptp=a.wt_mks-wto;
    if(a.izicrlx==0){
        // No convective growth for positive Lmo or negative net buoyancy.
        if(a.el_m>0.f||wptp<0.f)return result;
        // No net buoyancy flux: keep the previous mixing height.
        if(wptp==0.f){result.ziconv_m=a.zicbgold_m;return result;}
    }else{
        if(a.el_m>0.f||a.wt_mks<0.f)return result;
        if(wptp<=0.f){
            // 0<WT<WTO: relax toward the equilibrium convective height.
            if(a.threshold_wm2perm<=0.f)
                throw std::invalid_argument(
                    "MIXHBG relaxation requires positive threshold flux");
            const float ziceq=rho*cp*a.wt_mks/a.threshold_wm2perm;
            result.ziconv_m=ziceq+(h0-ziceq)*
                std::exp(-static_cast<float>(a.timestep_s)/a.tzicrlx_s);
            return result;
        }
    }
    result.gamma_kperm=std::max(a.gamma_kperm,a.dptmin_kperm);
    const float aa=wptp/result.gamma_kperm;
    const float bb=cc*a.ustar_ms*a.ustar_ms*a.tk_k/(result.gamma_kperm*g);
    const float ccb=cb*vonk*a.el_m;
    const float d=1.f+2.f*ca;
    const float e=1.f+ca;
    const float d3=d*d*d;
    const float zeta0=d*h0-2.f*ccb;
    const float zetap0=e*h0-ccb;
    const float r1=8.f*ccb,r2=r1*ccb,r3=2.f*bb*d3/e;
    const float r4=1.f/(2.f*aa*d3),r5=e/d;
    const float t0=r4*mixhbg_fbg(zeta0,zetap0,r1,r2,r3);
    const float t=static_cast<float>(a.timestep_s);
    const float time=t+t0;
    // First value uses the encroachment limit.
    float h;
    if(a.el_m>-500.f)h=std::sqrt(h0*h0+2.f*d*aa*t);
    else h=std::pow(h0*h0*h0-6.f*aa*ccb*t,0.333f);
    float zeta1=d*h-2.f*ccb,zetap1=e*h-ccb;
    float f1=r4*mixhbg_fbg(zeta1,zetap1,r1,r2,r3)-time;
    h=(zeta1+2.f*ccb)/d;
    bool done=std::fabs(f1)<=1.f;
    if(!done){
        const float f0=-t;
        float zeta2=(f1*zeta0-f0*zeta1)/(f1-f0);
        float zetap2=r5*(zeta2+2.f*ccb)-ccb;
        if(zeta2<=0.f||zetap2<=0.f){
            zeta2=0.5f*(zeta0+zeta1);
            zetap2=r5*(zeta2+2.f*ccb)-ccb;
        }
        float f2=r4*mixhbg_fbg(zeta2,zetap2,r1,r2,r3)-time;
        h=(zeta2+2.f*ccb)/d;
        done=std::fabs(f2)<=1.f;
        if(!done){
            for(int n=0;n<10;++n){
                if(std::fabs(f1-f2)<=1e-10f){done=true;break;}
                const float zeta3=(f1*zeta2-f2*zeta1)/(f1-f2);
                const float zetap3=r5*(zeta3+2.f*ccb)-ccb;
                if(zeta3<=0.f||zetap3<=0.f)break;
                const float f3=r4*mixhbg_fbg(zeta3,zetap3,r1,r2,r3)-time;
                h=(zeta3+2.f*ccb)/d;
                zeta1=zeta2;zetap1=zetap2;zeta2=zeta3;zetap2=zetap3;
                f1=f2;f2=f3;
                if(std::fabs(f3)<=1.f){done=true;break;}
            }
            // Not converged or non-positive arguments: average last two.
            if(!done)h=((zeta1+zeta2)/2.f+2.f*ccb)/d;
        }
    }
    result.ziconv_m=std::min(h,a.zimax_m);
    result.ziconv_m=std::max(h,a.zimin_m);
    if(!std::isfinite(result.ziconv_m)||!std::isfinite(result.gamma_kperm))
        throw std::invalid_argument("MIXHBG nonfinite convective height");
    return result;
}
} // namespace cteas::p6e
