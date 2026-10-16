#pragma once
// CALMET 6.5.0 ELUSTR2 (calmet.for 6580-6896), station-only land physics
// from the actual DIAGNO STHEOR path. This deliberately differs from
// gridded ELUSTR: station U/V are anemometer winds; its log uses ZMID(1)
// but unstable PSIU uses ZZANEM, and there is no 0.5 m/s gridded wind floor.
// Pure step: caller supplies independently computed solar/temperature/density,
// geophysical parameters and observations. MIXHTST/SIMILT is a later step.
#include "cteas/p6e/elustr_daytime.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cteas::calmet::p6 {
struct StationElustr2Input {
    float surface_u_mps=0.f,surface_v_mps=0.f;
    float zmid1_m=10.f,anemometer_m=10.f,z0_m=0.25f;
    float solar_sine=0.f,temp_k=290.f,rho_kg_m3=1.2f;
    int cloud_tenths=0,ipsifcn=0;
    float ha1=990.f,ha2=-30.f,hb1=-0.75f,hb2=3.4f;
    float hc1=5.31e-13f,hc2=60.f,hc3p1=1.12f;
    float albedo=0.2f,bowen=1.f,hcg=0.f,qf=0.f;
};
struct StationElustr2Flux {
    bool extrapolate=false;
    float sensible_wm2=0.f,friction_velocity_mps=0.f,monin_obukhov_m=0.f;
    float shortwave_wm2=0.f;
};
inline StationElustr2Flux station_elustr2_flux(const StationElustr2Input& a) {
    if (!(a.zmid1_m>0.f&&a.anemometer_m>0.f&&a.z0_m>0.f&&
          a.z0_m<a.zmid1_m&&a.temp_k>0.f&&a.rho_kg_m3>0.f&&
          a.hc3p1>0.f&&a.bowen>=0.f&&a.cloud_tenths>=0&&
          a.cloud_tenths<=10&&(a.ipsifcn==0||a.ipsifcn==1) &&
          std::isfinite(a.solar_sine)&&std::isfinite(a.surface_u_mps)&&
          std::isfinite(a.surface_v_mps)))
        throw std::invalid_argument("ELUSTR2 invalid station input");
    const float ws=std::sqrt(a.surface_u_mps*a.surface_u_mps+
                             a.surface_v_mps*a.surface_v_mps);
    StationElustr2Flux out;
    if(ws<0.001f)return out; // literal original early return
    out.extrapolate=true;
    constexpr float vk=0.4f;
    const float xlnzz0=std::log(a.zmid1_m/a.z0_m);
    const float ccfrac=0.1f*static_cast<float>(a.cloud_tenths);
    float qsw=(a.ha1*a.solar_sine+a.ha2)*
              (1.f+a.hb1*std::pow(ccfrac,a.hb2));
    qsw=std::max(qsw,0.f);
    out.shortwave_wm2=qsw;
    float qqh=-0.1f;
    if(a.solar_sine>0.f){
        const float qstar=((1.f-a.albedo)*qsw+
            a.hc1*std::pow(a.temp_k,6.f)-
            5.67e-8f*std::pow(a.temp_k,4.f)+a.hc2*ccfrac)/a.hc3p1;
        qqh=a.bowen*(qstar*(1.f-a.hcg)+a.qf)/(1.f+a.bowen);
    }
    if(qqh>=0.f){
        float xl=-9.9e9f;
        float ustar=std::max(vk*ws/xlnzz0,0.05f);
        if(qqh>0.f){
            float xlold=xl;
            for(int n=0;n<5;++n){
                xl=-253.8226f*a.rho_kg_m3*a.temp_k*
                   std::pow(ustar,3.f)/qqh;
                float psizl=0.f,psiz0l=0.f;
                if(a.ipsifcn==0){
                    // Source assigns REAL*4 z/L to REAL*8 r8 before PSIUD.
                    const double p=static_cast<double>(a.anemometer_m/xl);
                    const double q=static_cast<double>(a.z0_m/xl);
                    psizl=static_cast<float>(cteas::p6e::original_psiud_unstable(p));
                    psiz0l=static_cast<float>(cteas::p6e::original_psiud_unstable(q));
                }else{
                    psizl=cteas::p6e::original_psiuc_unstable(a.anemometer_m,xl);
                    psiz0l=cteas::p6e::original_psiuc_unstable(a.z0_m,xl);
                }
                ustar=std::max(vk*ws/(xlnzz0-psizl+psiz0l),0.05f);
                if(std::abs((xl-xlold)/xl)<0.005f)break;
                xlold=xl;
            }
        }
        out.friction_velocity_mps=ustar;
        out.monin_obukhov_m=xl;
    }else{
        // Original ELUSTR2 at 6824-6866. Its stable branch uses the actual
        // station WS (no gridded ELUSTR 0.5 m/s floor).
        const float theta1=0.09f*(1.f-5.e-3f*
            static_cast<float>(a.cloud_tenths*a.cloud_tenths));
        const float cdn=vk/xlnzz0;
        const float theta2=a.temp_k*cdn*ws*ws/(184.428f*a.zmid1_m);
        float thetas=std::max(std::min(theta1,theta2),1.e-9f);
        float u02=46.107f*a.zmid1_m*thetas/a.temp_k;
        float cu2=std::max(0.f,ws*ws-4.f*u02/cdn);
        float ustar=std::max(0.5f*cdn*(ws+std::sqrt(cu2)),0.05f);
        if(ustar*thetas>0.05f){
            for(int n=0;n<3;++n){
                thetas=0.05f/ustar;
                u02=46.107f*a.zmid1_m*thetas/a.temp_k;
                cu2=std::max(0.f,ws*ws-4.f*u02/cdn);
                ustar=0.5f*cdn*(ws+std::sqrt(cu2));
                if(ustar*thetas<=1.05f*0.05f)break;
            }
        }
        qqh=-996.f*a.rho_kg_m3*ustar*thetas;
        out.friction_velocity_mps=ustar;
        out.monin_obukhov_m=-253.8226f*a.rho_kg_m3*a.temp_k*
                           std::pow(ustar,3.f)/qqh;
    }
    out.sensible_wm2=qqh;
    if(!std::isfinite(out.sensible_wm2)||
       !std::isfinite(out.friction_velocity_mps)||
       !std::isfinite(out.monin_obukhov_m))
        throw std::runtime_error("ELUSTR2 nonfinite station state");
    return out;
}
} // namespace cteas::calmet::p6
