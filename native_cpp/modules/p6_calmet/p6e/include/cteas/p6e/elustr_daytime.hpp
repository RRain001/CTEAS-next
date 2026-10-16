#pragma once
// CALMET 6.5.0 ELUSTR QH>=0 daytime, L6333-6578.
// Original PSIU(D/COARE and C/v5.53) corrections; water unchanged.
// Stable/night route remains isolated in elustr_stable.hpp.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
struct DaytimeElustrInput {
    std::size_t nx=0,ny=0;
    int water_first=50,water_last=60,ipsifcn=0;
    float zm=10.f;
    std::vector<int> landuse;
    std::vector<float> z0,u1,v1,rho,temp_k,heat_flux_initial,
                       initial_ustar,initial_el;
};
struct DaytimeElustrResult {
    std::vector<float> qh_wm2,ustar_ms,monin_obukhov_m;
};
inline double original_psiud_unstable(double zl) {
    if(!(zl<0.0))throw std::invalid_argument("PSIUD requires negative z/L here");
    const double x=std::pow(1.0-16.0*zl,0.25);
    const double psik=2.0*std::log((1.0+x)/2.0)+
        std::log((1.0+x*x)/2.0)-2.0*std::atan(x)+2.0*std::atan(1.0);
    const double y=std::pow(1.0-10.15*zl,0.3333);
    const double psic=1.5*std::log((1.0+y+y*y)/3.0)-
        std::sqrt(3.0)*std::atan((1.0+2.0*y)/std::sqrt(3.0))+
        4.0*std::atan(1.0)/std::sqrt(3.0);
    const double f=zl*zl/(1.0+zl*zl);
    return (1.0-f)*psik+f*psic;
}
inline float original_psiuc_unstable(float z,float xl) {
    const float rfit=15.f;
    const float x=std::pow(1.f-rfit*z/xl,0.25f);
    return 2.f*std::log(0.5f*(1.f+x))+
        std::log(0.5f*(1.f+x*x))-2.f*std::atan(x)+1.5707963f;
}
inline DaytimeElustrResult elustr_daytime(const DaytimeElustrInput& a) {
    if(!a.nx||!a.ny||a.nx>std::numeric_limits<std::size_t>::max()/a.ny||
       a.water_first>a.water_last||(a.ipsifcn!=0&&a.ipsifcn!=1)||
       !std::isfinite(a.zm)||a.zm<=0.f)
        throw std::invalid_argument("ELUSTR daytime invalid controls");
    const auto n=a.nx*a.ny;
    if(a.landuse.size()!=n||a.z0.size()!=n||a.u1.size()!=n||
       a.v1.size()!=n||a.rho.size()!=n||a.temp_k.size()!=n||
       a.heat_flux_initial.size()!=n||a.initial_ustar.size()!=n||
       a.initial_el.size()!=n)
        throw std::invalid_argument("ELUSTR daytime wrong grid dimensions");
    DaytimeElustrResult r{a.heat_flux_initial,a.initial_ustar,a.initial_el};
    for(std::size_t j=0;j<a.ny;++j) for(std::size_t i=0;i<a.nx;++i) {
        const auto k=j*a.nx+i;
        if(a.landuse[k]>=a.water_first&&a.landuse[k]<=a.water_last)
            continue;
        if(!std::isfinite(a.z0[k])||a.z0[k]<=0.f||a.z0[k]>=a.zm||
           !std::isfinite(a.u1[k])||!std::isfinite(a.v1[k])||
           !std::isfinite(a.rho[k])||a.rho[k]<=0.f||
           !std::isfinite(a.temp_k[k])||a.temp_k[k]<=0.f||
           !std::isfinite(a.heat_flux_initial[k])||a.heat_flux_initial[k]<0.f)
            throw std::invalid_argument("ELUSTR daytime requires QH >= 0 and valid air inputs");
        float ws=std::sqrt(a.u1[k]*a.u1[k]+a.v1[k]*a.v1[k]);
        ws=std::max(ws,0.001f);
        const float xlnzz0=std::log(a.zm/a.z0[k]);
        float xl=-9.9e9f;
        float xustar=std::max(0.4f*ws/xlnzz0,0.05f);
        const float heat=a.heat_flux_initial[k];
        if(heat>0.f) {
            float xlold=xl;
            for(int niter=0;niter<5;++niter) {
                xl=-253.8226f*a.rho[k]*a.temp_k[k]*
                    (xustar*xustar*xustar)/heat;
                float psizl=0.f,psiz0l=0.f;
                if(a.ipsifcn==0) {
                    // Original assigns REAL*4 division to REAL*8 R8
                    // before calling REAL*8 PSIUD; then converts return
                    // to REAL*4 PSIZL and PSIZ0L.
                    const double ratio1=static_cast<double>(a.zm/xl);
                    const double ratio0=static_cast<double>(a.z0[k]/xl);
                    psizl=static_cast<float>(original_psiud_unstable(ratio1));
                    psiz0l=static_cast<float>(original_psiud_unstable(ratio0));
                } else {
                    psizl=original_psiuc_unstable(a.zm,xl);
                    psiz0l=original_psiuc_unstable(a.z0[k],xl);
                }
                const float den=xlnzz0-psizl+psiz0l;
                if(!std::isfinite(den)||den<=0.f)
                    throw std::invalid_argument("ELUSTR daytime nonphysical PSIU denominator");
                xustar=std::max(0.4f*ws/den,0.05f);
                if(std::abs((xl-xlold)/xl)<0.005f)break;
                xlold=xl;
            }
        }
        if(!std::isfinite(xl)||!std::isfinite(xustar))
            throw std::invalid_argument("ELUSTR daytime nonfinite result");
        r.ustar_ms[k]=xustar;
        r.monin_obukhov_m[k]=xl;
    }
    return r;
}
} // namespace cteas::p6e
