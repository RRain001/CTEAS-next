#pragma once
// Original CALMET 6.5.0 TOPOF2, calmet.for L31904-L32078, DIAGNO L5621-5622.
// Terrain-induced vertical velocity in terrain-following coordinates.
// Original constants TAU=-0.01, HINV=500, decay cutoff 50, 9.8 are REAL*4.
// TOPOF2 only writes W; the horizontal winds are read, never modified.
// Isolated source-scoped kernel, not a full DIAGNO claim.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6 {
struct Topof2Input {
    int nx=0,ny=0,nz=0;
    float dx_m=0,dy_m=0;
    int isurft=-1;
    float tinf_k=0.f;
    float alpha=0.f;
    std::vector<float> dz_m;                  // original DZ, nz entries
    std::vector<float> cellzb_m;              // original CELLZB, nz+1 faces
    std::vector<float> terrain_m;             // HTOPO, nx*ny
    std::vector<float> lapse_rate_k_per_m;    // GAMMA, nx*ny
    std::vector<float> surface_temperature_k; // TEMP2D, nx*ny
};
inline std::vector<float> original_topof2_w(
    const Topof2Input& in,const std::vector<float>& u_mps,
    const std::vector<float>& v_mps) {
    if(in.nx<2||in.ny<2||in.nz<1||in.nx>400||in.ny>400||in.nz>12)
        throw std::invalid_argument("TOPOF2 invalid grid");
    if(!(std::isfinite(in.dx_m)&&std::isfinite(in.dy_m)&&
         in.dx_m>0.f&&in.dy_m>0.f))
        throw std::invalid_argument("TOPOF2 invalid grid spacing");
    if(!std::isfinite(in.alpha))
        throw std::invalid_argument("TOPOF2 invalid ALPHA coefficient");
    const std::size_t cells=std::size_t(in.nx)*std::size_t(in.ny);
    const std::size_t nz=std::size_t(in.nz);
    if(in.dz_m.size()!=nz||in.cellzb_m.size()!=nz+1||
       in.terrain_m.size()!=cells||in.lapse_rate_k_per_m.size()!=cells||
       in.surface_temperature_k.size()!=cells||
       u_mps.size()!=cells*nz||v_mps.size()!=cells*nz)
        throw std::invalid_argument("TOPOF2 input field shape");
    for(float z:in.dz_m)
        if(!(std::isfinite(z)&&z>0.f))
            throw std::invalid_argument("TOPOF2 invalid DZ");
    for(float z:in.cellzb_m)
        if(!std::isfinite(z))
            throw std::invalid_argument("TOPOF2 invalid CELLZB");
    for(std::size_t n=0;n<cells;++n){
        if(!std::isfinite(in.terrain_m[n])||
           !std::isfinite(in.lapse_rate_k_per_m[n])||
           !std::isfinite(in.surface_temperature_k[n]))
            throw std::invalid_argument("TOPOF2 missing terrain or stability input");
        const float temperature=(in.isurft>0||in.isurft==-2)
            ? in.tinf_k:in.surface_temperature_k[n];
        if(!(std::isfinite(temperature)&&temperature>0.f))
            throw std::invalid_argument("TOPOF2 invalid surface temperature");
    }
    for(float value:u_mps)if(!std::isfinite(value))
        throw std::invalid_argument("TOPOF2 nonfinite U");
    for(float value:v_mps)if(!std::isfinite(value))
        throw std::invalid_argument("TOPOF2 nonfinite V");

    constexpr float tau=-0.01f;
    constexpr float hinv=500.f;
    const std::size_t plane=cells;
    const auto at=[&](int i,int j,int k)->std::size_t {
        return std::size_t(k)*plane+std::size_t(j)*std::size_t(in.nx)+
               std::size_t(i);
    };
    const float dxi=0.5f/in.dx_m,dyi=0.5f/in.dy_m;
    // Original: W is XMIT-zeroed before the call and W1 is a local profile.
    std::vector<float> w(plane*(nz+1),0.f);
    std::vector<float> w1(nz+1);
    for(int j=0;j<in.ny;++j)for(int i=0;i<in.nx;++i){
        const float temperature=(in.isurft>0||in.isurft==-2)
            ? in.tinf_k:in.surface_temperature_k[std::size_t(j)*
                std::size_t(in.nx)+std::size_t(i)];
        const float gamma2=in.lapse_rate_k_per_m[std::size_t(j)*
            std::size_t(in.nx)+std::size_t(i)]-tau;
        const float stability=gamma2<0.f?-1.f:
            std::sqrt(9.8f*gamma2/temperature);
        float bk;
        if(stability<=0.f)bk=2.f/hinv;
        else {
            const float speed=std::max(std::hypot(u_mps[at(i,j,in.nz-1)],
                                                 v_mps[at(i,j,in.nz-1)]),
                                       1.e-6f);
            bk=stability/speed;
        }
        const float delhi=(in.terrain_m[std::size_t(j)*std::size_t(in.nx)+
                             std::size_t(std::min(i+1,in.nx-1))]-
                           in.terrain_m[std::size_t(j)*std::size_t(in.nx)+
                             std::size_t(std::max(i-1,0))])*dxi;
        const float delhj=(in.terrain_m[std::size_t(std::min(j+1,in.ny-1))*
                             std::size_t(in.nx)+std::size_t(i)]-
                           in.terrain_m[std::size_t(std::max(j-1,0))*
                             std::size_t(in.nx)+std::size_t(i)])*dyi;
        const float wtopo=u_mps[at(i,j,0)]*delhi+v_mps[at(i,j,0)]*delhj;
        w1[0]=wtopo;
        w[at(i,j,0)]=wtopo;
        for(int k=0;k<in.nz;++k){
            float bkz=bk*in.cellzb_m[std::size_t(k)+1];
            if(bkz>50.f)bkz=50.f;
            w1[std::size_t(k)+1]=wtopo*std::exp(-bkz);
            const float dzi=1.f/in.dz_m[std::size_t(k)];
            const float dwdz1=(w1[std::size_t(k)+1]-w1[std::size_t(k)])*dzi;
            const float dwdz=in.alpha*dwdz1;
            w[at(i,j,k+1)]=dwdz/dzi+w[at(i,j,k)];
        }
        // Original terrain-following transform on every face.
        w[at(i,j,0)]=w[at(i,j,0)]-u_mps[at(i,j,0)]*delhi-
                     v_mps[at(i,j,0)]*delhj;
        for(int k=0;k<in.nz;++k)
            w[at(i,j,k+1)]=w[at(i,j,k+1)]-u_mps[at(i,j,k)]*delhi-
                           v_mps[at(i,j,k)]*delhj;
    }
    return w;
}
} // namespace cteas::calmet::p6
