#pragma once
// CALMET v6.5.0 CLOUD3 L30683-30735: prognostic RH (%) at about 850 mb
// to gridded cloud fraction, including original RH>=99% saturation.
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
inline std::vector<float> cloud3(
    std::size_t nx,std::size_t ny,const std::vector<float>& rh_pct) {
    if(nx==0||ny==0||nx>std::numeric_limits<std::size_t>::max()/ny||
       rh_pct.size()!=nx*ny)
        throw std::invalid_argument("CLOUD3 invalid gridded RH dimensions");
    std::vector<float> cc(nx*ny);
    for(std::size_t j=0;j<ny;++j)for(std::size_t i=0;i<nx;++i){
        const auto k=j*nx+i;
        const float rh=rh_pct[k];
        if(!std::isfinite(rh)||rh<0.f||rh>100.f)
            throw std::invalid_argument("CLOUD3 expects RH in [0,100]%");
        if(rh>=99.f){cc[k]=1.f;continue;}
        const float rhd=rh/100.f;
        cc[k]=0.02f*(-1.f+std::sqrt(1.f+100.f*(1.f-rhd)))/
              (1.f-rhd);
        if(!std::isfinite(cc[k]))
            throw std::invalid_argument("CLOUD3 nonfinite cloud");
    }
    return cc;
}
} // namespace cteas::p6e
