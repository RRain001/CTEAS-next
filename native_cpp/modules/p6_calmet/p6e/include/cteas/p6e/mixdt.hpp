#pragma once
// Original CALMET 6.5.0 MIXDT (calmet.for L10005-10201).
// Computes lapse above the *previous* convective mixing height from
// the selected older AA/BB upper-air temperature sounding.
// Selecting JUSTA, IUPT, or temporal interpolation belongs to the caller.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
struct MixdtSounding {
    std::vector<float> height_m;
    std::vector<float> temp_k;
};
struct MixdtResult {
    float tht_k, thtp_k, dtheta_k_per_m;
};
inline MixdtResult mixdt(const MixdtSounding& s, float htold_m,
                        float dzzi_m, float dptmin_k_per_m) {
    const auto n=s.height_m.size();
    if(n<2||s.temp_k.size()!=n||!std::isfinite(htold_m)||
       !std::isfinite(dzzi_m)||dzzi_m<=0.f||
       !std::isfinite(dptmin_k_per_m)||dptmin_k_per_m<=0.f)
        throw std::invalid_argument("MIXDT invalid sounding extent or controls");
    for(std::size_t k=0;k<n;++k) {
        if(!std::isfinite(s.height_m[k])||!std::isfinite(s.temp_k[k])||
           (k>0 && !(s.height_m[k]>s.height_m[k-1])))
            throw std::invalid_argument("MIXDT nonmonotonic levels or nonfinite observation");
    }
    // Preserve original strict-height branching and 999.9-0.01 missing
    // threshold; do not join over the absence of a valid upper bracket.
    auto bracket=[&](float z) {
        std::size_t below=n,above=n;
        for(std::size_t k=0;k<n;++k) {
            if(s.height_m[k]>z)break;
            if(s.temp_k[k]<999.89f)below=k;
        }
        if(below==n)
            throw std::invalid_argument("MIXDT no valid sounding level at or below requested height");
        for(std::size_t k=below+1;k<n;++k) {
            if(s.height_m[k]>z && s.temp_k[k]<999.89f) {
                above=k;break;
            }
        }
        if(above==n)
            throw std::invalid_argument("MIXDT no valid sounding level above requested height");
        const float upper=s.temp_k[above],lower=s.temp_k[below];
        const float zu=s.height_m[above],zl=s.height_m[below];
        return upper-(upper-lower)*(zu-z)/(zu-zl);
    };
    const float tht=bracket(htold_m);
    const float thtp=bracket(htold_m+dzzi_m);
    // Same floating-point operation order as source.
    const float dtheta=std::max((thtp-tht)/dzzi_m+0.0098f,dptmin_k_per_m);
    if(!std::isfinite(tht)||!std::isfinite(thtp)||!std::isfinite(dtheta))
        throw std::invalid_argument("MIXDT nonfinite output");
    return {tht,thtp,dtheta};
}
} // namespace cteas::p6e
