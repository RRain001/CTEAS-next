#pragma once
// CALMET v6.5.0 WSTARR (calmet.for L36884-36949), isolated land cells.
// Convective velocity scale w*: after mixing-height/heat-flux integration.
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
struct WstarrInput {
    std::size_t nx=0,ny=0;
    int water_first=50,water_last=60;
    std::vector<float> zi_conv_m,heat_flux_wm2,temp_k,rho_kgm3,initial_wstar_ms;
    std::vector<int> landuse;
};
inline std::vector<float> wstarr(const WstarrInput& x) {
    if(!x.nx||!x.ny||x.nx>std::numeric_limits<std::size_t>::max()/x.ny||
       x.water_first>x.water_last)
        throw std::invalid_argument("WSTARR invalid dimensions/water category");
    const auto n=x.nx*x.ny;
    if(x.zi_conv_m.size()!=n||x.heat_flux_wm2.size()!=n||
       x.temp_k.size()!=n||x.rho_kgm3.size()!=n||
       x.initial_wstar_ms.size()!=n||x.landuse.size()!=n)
        throw std::invalid_argument("WSTARR invalid array extent");
    std::vector<float> out=x.initial_wstar_ms;
    for(std::size_t j=0;j<x.ny;++j)for(std::size_t i=0;i<x.nx;++i){
        const auto k=j*x.nx+i;
        // Original skips overwater without touching its w* field.
        if(x.landuse[k]>=x.water_first&&x.landuse[k]<=x.water_last)continue;
        const float qh=x.heat_flux_wm2[k];
        if(!std::isfinite(qh))
            throw std::invalid_argument("WSTARR nonfinite heat flux");
        if(qh<=0.f){out[k]=0.f;continue;}
        if(!std::isfinite(x.zi_conv_m[k])||x.zi_conv_m[k]<0.f||
           !std::isfinite(x.temp_k[k])||x.temp_k[k]<=0.f||
           !std::isfinite(x.rho_kgm3[k])||x.rho_kgm3[k]<=0.f)
            throw std::invalid_argument("WSTARR invalid convective state");
        const float xscale=9.81f*qh*x.zi_conv_m[k]/
                            (x.temp_k[k]*x.rho_kgm3[k]*996.f);
        out[k]=std::pow(xscale,0.3333333f);
        if(!std::isfinite(out[k]))
            throw std::invalid_argument("WSTARR nonfinite velocity");
    }
    return out;
}
} // namespace cteas::p6e
