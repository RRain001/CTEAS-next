#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::puff {

// CALPUFF 7.2.1 PTLAPS (calpuff.for L18481-18521, L18555-18556),
// METFM=1 only. Inputs are the original REAL*4 ZGPT layer-center
// elevations and TMET profile in the selected meteorological cell.
// This is NOT a generic lapse-rate regression and does not extrapolate
// missing layers or accept PROFILE.DAT alternatives.
struct OriginalPtlapsResult {
    float gradient_k_per_m=0.0F;   // DTHETA, after DPTMIN
    float temperature_base_k=0.0F; // THT, before clipping
};

[[nodiscard]] inline OriginalPtlapsResult original_ptlaps_metfm1(
    const std::vector<float>& zgpt_m,
    const std::vector<float>& tmet_k,
    float htbase_m,float dptmin_k_per_m,float delz_m) {
    const auto nz=zgpt_m.size();
    if(nz<2U || tmet_k.size()!=nz ||
       !std::isfinite(htbase_m) || !std::isfinite(dptmin_k_per_m) ||
       !std::isfinite(delz_m) || delz_m<=0.0F ||
       dptmin_k_per_m<0.0F)
        throw std::invalid_argument("PTLAPS METFM1 invalid layer/height/gradient");
    for(std::size_t i=0;i<nz;++i) {
        if(!std::isfinite(zgpt_m[i]) || !std::isfinite(tmet_k[i]) ||
           tmet_k[i]<=0.0F ||
           (i>0 && !(zgpt_m[i]>zgpt_m[i-1U])))
            throw std::invalid_argument("PTLAPS METFM1 invalid ZGPT/TMET profile");
    }

    // Original 1-based KL=NZ-1, K=2..NZ and KU=NZ, K=KL+1..NZ.
    std::size_t kl=nz-2U;
    for(std::size_t k=1;k<nz;++k) {
        if(zgpt_m[k]>=htbase_m) {kl=k-1U;break;}
    }
    std::size_t ku=nz-1U;
    const float htpdz=htbase_m+delz_m;
    for(std::size_t k=kl+1U;k<nz;++k) {
        if(zgpt_m[k]>=htpdz) {ku=k;break;}
    }
    float tht=0.0F,grad=0.0F;
    if(ku-kl==1U) {
        grad=0.0098F+(tmet_k[ku]-tmet_k[kl])/
             (zgpt_m[ku]-zgpt_m[kl]);
        tht=tmet_k[kl];
    } else {
        const auto kp=kl+1U;
        tht=tmet_k[kp]-(tmet_k[kp]-tmet_k[kl])*
            (zgpt_m[kp]-htbase_m)/(zgpt_m[kp]-zgpt_m[kl]);
        tht+=0.0F; // retain an observable REAL*4 assignment boundary
        const auto km=ku-1U;
        const float thtp=tmet_k[ku]-(tmet_k[ku]-tmet_k[km])*
            (zgpt_m[ku]-htpdz)/(zgpt_m[ku]-zgpt_m[km]);
        grad=(thtp-tht)/delz_m+0.0098F;
    }
    grad=std::max(grad,dptmin_k_per_m);
    if(!std::isfinite(grad)||!std::isfinite(tht)||tht<=0.0F)
        throw std::invalid_argument("PTLAPS METFM1 nonfinite DTHETA/THT");
    return {grad,tht};
}

// COMP L10893-10896: DELZ=max(ZTOP-ZBOT,10m), BVF=sqrt(g*DTHETA/THT).
[[nodiscard]] inline float original_comp_bvf_metfm1(
    const std::vector<float>& zgpt_m,const std::vector<float>& tmet_k,
    float zbot_m,float ztop_m,float dptmin_k_per_m) {
    if(!std::isfinite(zbot_m)||!std::isfinite(ztop_m)||ztop_m<zbot_m)
        throw std::invalid_argument("COMP BVF invalid puff depth");
    const float dz=std::max(ztop_m-zbot_m,10.0F);
    const auto lapse=original_ptlaps_metfm1(
        zgpt_m,tmet_k,zbot_m,dptmin_k_per_m,dz);
    const float bvf=std::sqrt(
        9.80665F*lapse.gradient_k_per_m/lapse.temperature_base_k);
    if(!std::isfinite(bvf))
        throw std::invalid_argument("COMP BVF invalid source PTLAPS");
    return bvf;
}
} // namespace cteas::puff
