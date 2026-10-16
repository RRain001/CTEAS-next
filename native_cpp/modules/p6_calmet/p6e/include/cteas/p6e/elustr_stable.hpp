#pragma once
// CALMET v6.5.0 ELUSTR: original NIGHT/STABLE path (QH<0), L6333-6578.
// Retains original 0.5 m/s stable wind floor and 3-step theta* iteration.
// Daytime nonnegative QH and full ELUSTR integration are NOT supported.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
struct StableElustr {
    std::size_t nx=0,ny=0;
    int mcloud=1,water_first=50,water_last=60;
    float zm=10.f;
    std::vector<int> landuse,nearest,station_cloud;
    std::vector<float> z0,u1,v1,rho,temp_k,cloud_grid,heat_flux_initial;
    float water_sentinel=-7777.f;
};
struct StableElustrResult {
    std::vector<float> qh_wm2,ustar_ms,monin_obukhov_m;
};
inline StableElustrResult stable_elustr(const StableElustr& a) {
    if(!a.nx||!a.ny||a.nx>static_cast<std::size_t>(-1)/a.ny||
       a.mcloud<1||a.mcloud>4||a.water_first>a.water_last||
       !std::isfinite(a.zm)||a.zm<=0.f||
       !std::isfinite(a.water_sentinel))
        throw std::invalid_argument("ELUSTR invalid control");
    const auto n=a.nx*a.ny;
    if(a.landuse.size()!=n||a.nearest.size()!=n||
       a.z0.size()!=n||a.u1.size()!=n||a.v1.size()!=n||
       a.rho.size()!=n||a.temp_k.size()!=n||
       a.cloud_grid.size()!=n||a.heat_flux_initial.size()!=n)
        throw std::invalid_argument("ELUSTR wrong field dimensions");
    StableElustrResult r{a.heat_flux_initial,
                        std::vector<float>(n,a.water_sentinel),
                        std::vector<float>(n,a.water_sentinel)};
    for(std::size_t j=0;j<a.ny;++j) for(std::size_t i=0;i<a.nx;++i) {
        const auto k=j*a.nx+i;
        if(a.landuse[k]>=a.water_first&&a.landuse[k]<=a.water_last)
            continue;
        if(!std::isfinite(a.z0[k])||a.z0[k]<=0.f||a.z0[k]>=a.zm||
           !std::isfinite(a.u1[k])||!std::isfinite(a.v1[k])||
           !std::isfinite(a.rho[k])||a.rho[k]<=0.f||
           !std::isfinite(a.temp_k[k])||a.temp_k[k]<=0.f||
           !std::isfinite(a.heat_flux_initial[k])||a.heat_flux_initial[k]>=0.f)
            throw std::invalid_argument("ELUSTR invalid stable field");
        int jcc=0;
        if(a.mcloud>1) {
            if(!std::isfinite(a.cloud_grid[k])||a.cloud_grid[k]<0.f||
               a.cloud_grid[k]>1.f)
                throw std::invalid_argument("ELUSTR invalid gridded cloud");
            jcc=static_cast<int>(10.f*a.cloud_grid[k]+0.5f);
        } else {
            const int id=a.nearest[k];
            if(id<1||static_cast<std::size_t>(id)>a.station_cloud.size())
                throw std::invalid_argument("ELUSTR missing nearest station");
            jcc=a.station_cloud[static_cast<std::size_t>(id-1)];
            if(jcc<0||jcc>10)
                throw std::invalid_argument("ELUSTR invalid station cloud");
        }
        // Source calculates WS=max(sqrt(U²+V²),0.001) before stable floor.
        float ws=std::sqrt(a.u1[k]*a.u1[k]+a.v1[k]*a.v1[k]);
        ws=std::max(ws,0.001f);
        const float xlnzz0=std::log(a.zm/a.z0[k]);
        ws=std::max(ws,0.5f);
        const float theta1=0.09f*(1.f-5.e-3f*static_cast<float>(jcc*jcc));
        const float cdn=0.4f/xlnzz0;
        const float theta2=a.temp_k[k]*cdn*(ws*ws)/(184.428f*a.zm);
        float thetas=std::max(std::min(theta1,theta2),1.e-9f);
        float u02=46.107f*a.zm*thetas/a.temp_k[k];
        float cu2=std::max(0.f,ws*ws-4.f*u02/cdn);
        float ustar=std::max(0.5f*cdn*(ws+std::sqrt(cu2)),0.05f);
        constexpr float xcrit=0.05f;
        if(ustar*thetas>xcrit){
            constexpr float toler=1.05f*xcrit;
            for(int attempt=0;attempt<3;++attempt){
                thetas=xcrit/ustar;
                u02=46.107f*a.zm*thetas/a.temp_k[k];
                cu2=std::max(0.f,ws*ws-4.f*u02/cdn);
                ustar=0.5f*cdn*(ws+std::sqrt(cu2));
                if(ustar*thetas<=toler)break;
            }
        }
        const float heat=-996.f*a.rho[k]*ustar*thetas;
        const float length=-253.8226f*a.rho[k]*a.temp_k[k]*
                           (ustar*ustar*ustar)/heat;
        if(!std::isfinite(ustar)||!std::isfinite(heat)||!std::isfinite(length))
            throw std::invalid_argument("ELUSTR nonfinite stable result");
        r.ustar_ms[k]=ustar;r.qh_wm2[k]=heat;r.monin_obukhov_m[k]=length;
    }
    return r;
}
} // namespace cteas::p6e
