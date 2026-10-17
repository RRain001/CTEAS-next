#pragma once
// CALMET v6.5.0 MIXHMC L11558-11742: Maul-Carson
// convective layer growth for ILAPSE=2 (lapse supplied by upper-air MIXDT).
// This kernel does not determine AA/BB sounding order or invoke MIXDT.
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace cteas::p6e {
struct MixhmcInput {
    float wt_mks=0.f, gamma_kperm=0.001f, threshold_wm2perm=0.f;
    float zimax_m=2500.f,htold_m=100.f,dptt_k=0.f;
    float tht_k=290.f,thtp_k=291.f;
    int izicrlx=0, timestep_s=3600;
    float tzicrlx_s=800.f, dptmin_kperm=0.001f;
    float twodte_s=1080.f,onedte_s=4140.f;
};
struct MixhmcResult {
    float ziconv_m,dptt_k,gamma_kperm,tht_k,thtp_k;
    // Trace only, not part of the source contract: which of the three
    // original exits produced the result. 0 = return without growth
    // (collapse / zero net buoyancy), 1 = IZICRLX relaxation to ZICEQ,
    // 2 = convective growth (the only exit that writes DPTT).
    int branch=0;
    float dpttp1_k=0.f;
};
inline MixhmcResult mixhmc_lapse2(const MixhmcInput& a){
    if(!std::isfinite(a.wt_mks)||!std::isfinite(a.gamma_kperm)||
       !std::isfinite(a.threshold_wm2perm)||a.threshold_wm2perm<0.f||
       !std::isfinite(a.zimax_m)||a.zimax_m<=0.f||
       !std::isfinite(a.htold_m)||a.htold_m<0.f||
       !std::isfinite(a.dptt_k)||!std::isfinite(a.tht_k)||
       !std::isfinite(a.thtp_k)||!std::isfinite(a.tzicrlx_s)||
       a.tzicrlx_s<=0.f||!std::isfinite(a.dptmin_kperm)||
       a.dptmin_kperm<=0.f||!std::isfinite(a.twodte_s)||
       a.twodte_s<=0.f||!std::isfinite(a.onedte_s)||
       a.onedte_s<=0.f||a.timestep_s<=0||(a.izicrlx!=0&&a.izicrlx!=1))
        throw std::invalid_argument("MIXHMC invalid physical inputs or mode");
    constexpr float rho=1.2f,cp=996.f;
    MixhmcResult result{0.f,a.dptt_k,
                        std::max(a.gamma_kperm,a.dptmin_kperm),
                        a.tht_k,a.thtp_k};
    const float wto=a.threshold_wm2perm*a.htold_m/(rho*cp);
    const float buoy=a.wt_mks-wto;
    if(a.izicrlx==0){
        if(buoy<=0.f)return result;
    } else {
        if(a.wt_mks<=0.f)return result;
        if(buoy<=0.f) {
            // THRESH>0 is guaranteed here since WT>0 and WT-WTO<=0.
            const float ziceq=rho*cp*a.wt_mks/a.threshold_wm2perm;
            result.branch=1;
            result.ziconv_m=ziceq+(a.htold_m-ziceq)*
                std::exp(-static_cast<float>(a.timestep_s)/a.tzicrlx_s);
            return result;
        }
    }
    float unsqrt=result.gamma_kperm*a.twodte_s*buoy;
    unsqrt=std::max(unsqrt,0.f);
    const float dpttp1=std::sqrt(unsqrt);
    unsqrt=a.htold_m*a.htold_m+
        2.f*(buoy*a.onedte_s-a.dptt_k*a.htold_m)/result.gamma_kperm;
    unsqrt=std::max(unsqrt,0.f);
    result.dptt_k=dpttp1;
    result.branch=2;
    result.dpttp1_k=dpttp1;
    result.ziconv_m=std::sqrt(unsqrt)+dpttp1/result.gamma_kperm;
    result.ziconv_m=std::max(result.ziconv_m,0.f);
    if(result.ziconv_m>=a.zimax_m)result.ziconv_m=a.zimax_m;
    if(!std::isfinite(result.ziconv_m)||!std::isfinite(result.dptt_k))
        throw std::invalid_argument("MIXHMC nonfinite convective layer");
    return result;
}
} // namespace cteas::p6e
