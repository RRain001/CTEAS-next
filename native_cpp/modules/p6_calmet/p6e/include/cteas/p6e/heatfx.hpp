#pragma once
// CALMET 6.5.0 exact selected HEATFX formula (calmet.for L7999-8122).
// Output QSW for ALL cells, QH for land; water QH remains untouched.
// Original single-precision constants are maintained for reproducibility.
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
struct HeatFluxInput {
    std::size_t nx=0,ny=0;
    int mcloud=1,water_first=50,water_last=60;
    float ha1=0,ha2=0,hb1=0,hb2=0,hc1=0,hc2=0,hc3p1=0;
    std::vector<int> station_cloud; // tenths, indexed by 1-based NEARS
    std::vector<int> nearest,landuse;
    std::vector<float> sun,temp_k,cloud_grid,albedo,bowen,soil_heat_fraction,anthropogenic_wm2;
    std::vector<float> initial_qh; // original water cells: HEATFX leaves QH unchanged
};
struct HeatFluxResult {
    std::vector<float> shortwave_wm2,sensible_wm2;
};
inline HeatFluxResult heatfx(const HeatFluxInput& a) {
    if(!a.nx||!a.ny||a.nx>std::numeric_limits<std::size_t>::max()/a.ny ||
       a.mcloud<1||a.mcloud>4||a.water_first>a.water_last ||
       !std::isfinite(a.ha1)||!std::isfinite(a.ha2)||
       !std::isfinite(a.hb1)||!std::isfinite(a.hb2)||
       !std::isfinite(a.hc1)||!std::isfinite(a.hc2)||
       !std::isfinite(a.hc3p1)||a.hc3p1==0.0f)
        throw std::invalid_argument("HEATFX invalid control");
    const auto n=a.nx*a.ny;
    if(a.nearest.size()!=n||a.landuse.size()!=n||
       a.sun.size()!=n||a.temp_k.size()!=n||a.cloud_grid.size()!=n||
       a.albedo.size()!=n||a.bowen.size()!=n||
       a.soil_heat_fraction.size()!=n||a.anthropogenic_wm2.size()!=n||
       a.initial_qh.size()!=n)
        throw std::invalid_argument("HEATFX array dimensions");
    HeatFluxResult r{std::vector<float>(n,0.f),a.initial_qh};
    for(std::size_t j=0;j<a.ny;++j)
        for(std::size_t i=0;i<a.nx;++i) {
            const auto k=j*a.nx+i;
            if(!std::isfinite(a.sun[k])||a.sun[k]<-1.000001f||
               a.sun[k]>1.000001f||!std::isfinite(a.temp_k[k])||
               a.temp_k[k]<180.0f||a.temp_k[k]>350.0f||
               !std::isfinite(a.albedo[k])||a.albedo[k]<0.f||a.albedo[k]>1.f||
               !std::isfinite(a.bowen[k])||a.bowen[k]<0.f||
               !std::isfinite(a.soil_heat_fraction[k])||
               a.soil_heat_fraction[k]<0.f||a.soil_heat_fraction[k]>1.f||
               !std::isfinite(a.anthropogenic_wm2[k])||
               !std::isfinite(a.initial_qh[k]))
                throw std::invalid_argument("HEATFX invalid gridded values");
            float ccfrac=0.f;
            if(a.mcloud>1) {
                ccfrac=a.cloud_grid[k];
                if(!std::isfinite(ccfrac)||ccfrac<0.f||ccfrac>1.f)
                    throw std::invalid_argument("HEATFX invalid gridded cloud");
            } else {
                const int ns=a.nearest[k];
                if(ns<1||static_cast<std::size_t>(ns)>a.station_cloud.size())
                    throw std::invalid_argument("HEATFX nearest station index");
                const int cloud=a.station_cloud[static_cast<std::size_t>(ns-1)];
                if(cloud<0||cloud>10)
                    throw std::invalid_argument("HEATFX invalid station cloud");
                ccfrac=0.1f*static_cast<float>(cloud);
            }
            // CALMET original: short wave computed before water skip and
            // night/day branch. Do not impose sunrise clipping on input sine.
            const float sw=(a.ha1*a.sun[k]+a.ha2)*
                           (1.f+a.hb1*std::pow(ccfrac,a.hb2));
            if(!std::isfinite(sw))throw std::invalid_argument("HEATFX nonfinite QSW");
            r.shortwave_wm2[k]=std::fmax(sw,0.f);
            if(a.landuse[k]>=a.water_first&&a.landuse[k]<=a.water_last)
                continue;
            if(a.sun[k]<=0.f){r.sensible_wm2[k]=-0.1f;continue;}
            const float tk=a.temp_k[k];
            // `temp2d(i,j)**6` / `**4` have INTEGER exponents, so gfortran
            // evaluates them by repeated multiplication, not libm `powf`:
            //   x**4 == (x*x)*(x*x),  x**6 == ((x*x)*(x*x))*(x*x)
            // (verified against gfortran-11 -O0).  Using std::pow here differs
            // by 1-2 ULP, which the sunrise-hours net-radiation cancellation
            // amplifies into the QH/EL/WSTAR residual.
            const float tk2=tk*tk;
            const float tk4=tk2*tk2;
            const float tk6=tk4*tk2;
            const float qstar=((1.f-a.albedo[k])*r.shortwave_wm2[k]+
                               a.hc1*tk6-
                               5.67e-8f*tk4+a.hc2*ccfrac)/
                               a.hc3p1;
            r.sensible_wm2[k]=a.bowen[k]*
                (qstar*(1.f-a.soil_heat_fraction[k])+a.anthropogenic_wm2[k])/
                (1.f+a.bowen[k]);
            if(!std::isfinite(r.sensible_wm2[k]))
                throw std::invalid_argument("HEATFX nonfinite QH");
        }
    return r;
}
} // namespace cteas::p6e
