#pragma once
// Original CALMET v6.5.0 MIXHT stable QH<0 path: calmet.for L10411-10682.
// Nighttime mechanical height only, water untouched, original clipping.
// The daytime sounding-constrained MIXDT/MIXHMC/MIXHBG path is NOT implemented.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
struct StableMixingInput {
    std::size_t nx=0,ny=0;
    int water_first=50,water_last=60;
    float constn=2400.0f,zimin=20.0f,zimax=2500.0f;
    std::vector<int> landuse;
    std::vector<float> qh_wm2,ustar_ms,el_m,fcori_s,
                       initial_zi_m,initial_ziconv_m;
};
struct StableMixingResult {
    std::vector<float> zi_m,ziconv_m;
};
inline StableMixingResult mixht_stable(const StableMixingInput& a) {
    if(a.nx==0||a.ny==0||a.nx>std::numeric_limits<std::size_t>::max()/a.ny||
       a.water_first>a.water_last||
       !std::isfinite(a.constn)||a.constn<=0.f||
       !std::isfinite(a.zimin)||a.zimin<0.f||
       !std::isfinite(a.zimax)||a.zimax<a.zimin)
        throw std::invalid_argument("MIXHT invalid grid or mixing height controls");
    const auto n=a.nx*a.ny;
    if(a.landuse.size()!=n||a.qh_wm2.size()!=n||a.ustar_ms.size()!=n||
       a.el_m.size()!=n||a.fcori_s.size()!=n||
       a.initial_zi_m.size()!=n||a.initial_ziconv_m.size()!=n)
        throw std::invalid_argument("MIXHT wrong array extent");
    StableMixingResult r{a.initial_zi_m,a.initial_ziconv_m};
    for(std::size_t j=0;j<a.ny;++j)for(std::size_t i=0;i<a.nx;++i) {
        const auto k=j*a.nx+i;
        if(a.landuse[k]>=a.water_first&&a.landuse[k]<=a.water_last)
            continue;
        if(!std::isfinite(a.qh_wm2[k])||a.qh_wm2[k]>=0.f||
           !std::isfinite(a.ustar_ms[k])||a.ustar_ms[k]<=0.f||
           !std::isfinite(a.el_m[k])||a.el_m[k]<=0.f||
           !std::isfinite(a.fcori_s[k])||a.fcori_s[k]<=0.f)
            throw std::invalid_argument("MIXHT requires stable land state");
        const float zi1=a.constn*std::pow(a.ustar_ms[k],1.5f);
        const float zi2=0.4f*std::sqrt(
            a.ustar_ms[k]*a.el_m[k]/a.fcori_s[k]);
        r.zi_m[k]=std::max(a.zimin,std::min(std::min(zi1,zi2),a.zimax));
        r.ziconv_m[k]=0.f;
        if(!std::isfinite(r.zi_m[k]))
            throw std::invalid_argument("MIXHT nonfinite output");
    }
    return r;
}
} // namespace cteas::p6e
