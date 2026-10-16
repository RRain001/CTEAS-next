#pragma once
// CALMET 6.5.0 VERTAV (calmet.for L32253–32402).
// The original VERTAV inserts interpolated face winds, then integrates
// a piecewise linear wind profile through each model layer. Original
// float32 arithmetic intentionally retained, including +1000 translation.
// Distinct from PREPDI's subsequent AA/BB temporal interpolation.
#include "cteas/p6/read_upper.hpp"
#include <array>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6 {
struct LayerWind {
    float u_mps{},v_mps{};
};
inline std::vector<LayerWind> calmet_vertav(
    const UpperSounding& sounding,const std::vector<float>& zface) {
    if(zface.size()<2||zface.size()>13||sounding.data.empty())
        throw std::invalid_argument("VERTAV invalid layers/sounding");
    std::vector<float> u,v,z;
    u.reserve(sounding.data.size()+zface.size());
    v.reserve(sounding.data.size()+zface.size());
    z.reserve(sounding.data.size()+zface.size());
    for (const auto& layer:sounding.data) {
        // Original source threshold xmissm=999.0-0.01.
        if(layer.u_mps>=998.99f||layer.v_mps>=998.99f)continue;
        if(!std::isfinite(layer.u_mps)||!std::isfinite(layer.v_mps)||
           !std::isfinite(layer.height_lgl_m))
            throw std::invalid_argument("VERTAV nonfinite sounding");
        u.push_back(layer.u_mps+1000.0f);
        v.push_back(layer.v_mps+1000.0f);
        z.push_back(layer.height_lgl_m);
    }
    if(u.size()<2)throw std::invalid_argument("VERTAV fewer than 2 wind levels");
    for(std::size_t k=0;k<zface.size();++k){
        if(!std::isfinite(zface[k])||
           (k>0 && zface[k]<=zface[k-1]))
            throw std::invalid_argument("VERTAV invalid face geometry");
        const float bound=zface[k];
        if(bound==0.f)continue; // original does not insert face z=0.
        std::size_t upper=0;
        bool found=false,exact=false;
        for(std::size_t j=1;j<z.size();++j){
            if(z[j]>=bound){
                found=true;
                if(z[j]==bound){exact=true;break;}
                upper=j;break;
            }
        }
        if(!found)throw std::invalid_argument("VERTAV grid face above top wind level");
        if(exact)continue;
        if(z[upper]<=z[upper-1])throw std::invalid_argument("VERTAV non-increasing wind height");
        const float rat=(z[upper]-bound)/(z[upper]-z[upper-1]);
        const float uc=u[upper]-(u[upper]-u[upper-1])*rat;
        const float vc=v[upper]-(v[upper]-v[upper-1])*rat;
        u.insert(u.begin()+static_cast<std::ptrdiff_t>(upper),uc);
        v.insert(v.begin()+static_cast<std::ptrdiff_t>(upper),vc);
        z.insert(z.begin()+static_cast<std::ptrdiff_t>(upper),bound);
    }
    std::vector<std::size_t> face_indices(zface.size());
    std::size_t first=0;
    for(std::size_t k=0;k<zface.size();++k){
        bool found=false;
        for(std::size_t j=first;j<z.size();++j){
            if(z[j]==zface[k]){
                face_indices[k]=j;
                first=j+1;
                found=true;break;
            }
        }
        if(!found)throw std::invalid_argument("VERTAV face not in interpolated sounding");
    }
    std::vector<LayerWind> out(zface.size()-1);
    for(std::size_t k=0;k<out.size();++k){
        float sumu=0.0f,sumv=0.0f;
        for(std::size_t j=face_indices[k]+1;j<=face_indices[k+1];++j){
            const float dz=z[j]-z[j-1];
            const float min_u=std::min(u[j-1],u[j]);
            const float min_v=std::min(v[j-1],v[j]);
            sumu=sumu+(min_u+0.5f*std::abs(u[j]-u[j-1]))*dz;
            sumv=sumv+(min_v+0.5f*std::abs(v[j]-v[j-1]))*dz;
        }
        const float inverse=1.0f/(zface[k+1]-zface[k]);
        out[k]={sumu*inverse-1000.0f,sumv*inverse-1000.0f};
    }
    return out;
}
} // namespace cteas::calmet::p6
