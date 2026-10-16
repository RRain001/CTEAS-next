#pragma once
// P6D scoped CALMET 6.5.0 SLOPE (Mahrt/Horst-Doran) candidate.
// Original routine: engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for,
// SUBROUTINE SLOPE, lines 30372-30604.  This is an isolated kernel;
// it does not implement DIAGNO, mass consistency, or full P6D integration.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6 {
struct SlopeInput {
    int nx=0, ny=0, nz=0;
    float dx_m=0, dy_m=0;
    int water_first=0, water_last=0;
    int isurft=-1;
    float domain_temperature_k=0;
    std::vector<float> zface_m;
    std::vector<float> terrain_m, hmax_m, hmin_m;
    std::vector<float> disthmax_m, disthmin_m;
    std::vector<float> sensible_heat_w_m2, surface_temperature_k;
    std::vector<int> landuse;
};
struct SlopeWind {
    // Layout: k * ny * nx + j * nx + i, zero-based, i-fastest.
    std::vector<float> u_mps, v_mps;
};
inline SlopeWind compute_original_slope_scoped(const SlopeInput& in) {
    if (in.nx<2 || in.ny<2 || in.nz<1 || in.nx>400 || in.ny>400 || in.nz>12 ||
        !std::isfinite(in.dx_m) || !std::isfinite(in.dy_m) ||
        in.dx_m<=0 || in.dy_m<=0 || !std::isfinite(in.domain_temperature_k) ||
        in.domain_temperature_k<=0 || in.water_first>in.water_last)
        throw std::invalid_argument("SLOPE invalid dimensions, geometry, temperature or water class");
    const std::size_t cells=std::size_t(in.nx)*std::size_t(in.ny);
    if (in.zface_m.size()!=std::size_t(in.nz+1) ||
        in.terrain_m.size()!=cells || in.hmax_m.size()!=cells ||
        in.hmin_m.size()!=cells || in.disthmax_m.size()!=cells ||
        in.disthmin_m.size()!=cells || in.sensible_heat_w_m2.size()!=cells ||
        in.surface_temperature_k.size()!=cells || in.landuse.size()!=cells)
        throw std::invalid_argument("SLOPE field shape mismatch");
    for (std::size_t k=0;k<in.zface_m.size();++k)
        if (!std::isfinite(in.zface_m[k]) || in.zface_m[k]<0 ||
            (k && in.zface_m[k]<=in.zface_m[k-1]))
            throw std::invalid_argument("SLOPE ZFACE invalid");
    for (std::size_t n=0;n<cells;++n) {
        if (!std::isfinite(in.terrain_m[n]) || !std::isfinite(in.hmax_m[n]) ||
            !std::isfinite(in.hmin_m[n]) || !std::isfinite(in.disthmax_m[n]) ||
            !std::isfinite(in.disthmin_m[n]) ||
            in.disthmax_m[n]<0 || in.disthmin_m[n]<0 ||
            !std::isfinite(in.sensible_heat_w_m2[n]) ||
            !std::isfinite(in.surface_temperature_k[n]) ||
            in.surface_temperature_k[n]<=0 || in.hmin_m[n]>in.terrain_m[n] ||
            in.hmax_m[n]<in.terrain_m[n])
            throw std::invalid_argument("SLOPE missing/invalid terrain, heat flux or temperatures");
    }
    SlopeWind out{std::vector<float>(cells*std::size_t(in.nz),0.0f),
                  std::vector<float>(cells*std::size_t(in.nz),0.0f)};
    constexpr float rhocp=1229.9f;
    constexpr float cdk=8.e-2f;
    constexpr float rpd=0.017453f;
    constexpr float dpr=57.296f;
    const float dxi=0.5f/in.dx_m, dyi=0.5f/in.dy_m;
    const auto at=[&](int i,int j)->std::size_t {
        return std::size_t(j)*std::size_t(in.nx)+std::size_t(i);
    };
    for (int j=0;j<in.ny;++j) for (int i=0;i<in.nx;++i) {
        const auto n=at(i,j);
        if (in.landuse[n]>=in.water_first && in.landuse[n]<=in.water_last)
            continue; // Original SLOPE: water omitted for any sensible heat.
        const float temp=(in.isurft>0 || in.isurft==-2)
            ? in.domain_temperature_k:in.surface_temperature_k[n];
        const float delhi=(in.terrain_m[at(std::min(i+1,in.nx-1),j)]-
                            in.terrain_m[at(std::max(i-1,0),j)])*dxi;
        const float delhj=(in.terrain_m[at(i,std::min(j+1,in.ny-1))]-
                            in.terrain_m[at(i,std::max(j-1,0))])*dyi;
        const float slope=std::sqrt(delhi*delhi+delhj*delhj);
        const float alpha=std::atan(slope);
        if (std::abs(alpha)<0.009f) continue;
        float sinalf=std::sin(std::abs(alpha));
        const bool downhill=in.sensible_heat_w_m2[n]<0.0f;
        const float dh=downhill ? in.hmax_m[n]-in.terrain_m[n]
                                : in.terrain_m[n]-in.hmin_m[n];
        const float distance=downhill?in.disthmax_m[n]:in.disthmin_m[n];
        const float dcrest=std::sqrt(dh*dh+distance*distance);
        const float hd=0.05f*dh;
        float uvally=0.0f;
        if (hd>0.05f) {
            if (downhill) {
                sinalf=std::min(sinalf,dh/dcrest);
                const float tempmef=std::max(-dcrest*cdk/hd,-50.0f);
                const float driven=sinalf*(9.81f/temp)*std::abs(in.sensible_heat_w_m2[n])*
                                    dcrest/rhocp/cdk;
                uvally=-std::pow(driven,1.0f/3.0f)*
                    std::pow(1.0f-std::exp(tempmef),1.0f/3.0f);
            } else {
                const float driven=(9.81f/temp)*std::abs(in.sensible_heat_w_m2[n])*
                                    dh/rhocp;
                uvally=std::pow(driven,1.0f/3.0f);
            }
        }
        float theta=0.0f;
        if (delhi==0.0f) {
            if (delhj==0.0f) continue;
            theta=delhj<0?270.0f:90.0f;
        } else {
            const float theta_p=std::atan(delhj/delhi)*dpr;
            if (delhi<0.0f) theta=theta_p+180.0f;
            if (delhi>0.0f) theta=delhj>0.0f?theta_p:theta_p+360.0f;
        }
        float theta_d=0.0f;
        if (theta>=0.0f && theta<=90.0f) theta_d=90.0f-theta;
        if (theta>90.0f && theta<=360.0f) theta_d=450.0f-theta;
        const float angle=(270.0f-theta_d)*rpd;
        const float delu=-std::cos(angle)*uvally;
        const float delv=-std::sin(angle)*uvally;
        for (int k=0;k<in.nz;++k) {
            float ratio=0.0f;
            if (hd>in.zface_m[std::size_t(k+1)]) ratio=1.0f;
            else if (hd>in.zface_m[std::size_t(k)])
                ratio=(hd-in.zface_m[std::size_t(k)])/
                      (in.zface_m[std::size_t(k+1)]-in.zface_m[std::size_t(k)]);
            const auto idx=std::size_t(k)*cells+n;
            out.u_mps[idx]=delu*ratio;
            out.v_mps[idx]=delv*ratio;
        }
    }
    return out;
}
} // namespace cteas::calmet::p6
