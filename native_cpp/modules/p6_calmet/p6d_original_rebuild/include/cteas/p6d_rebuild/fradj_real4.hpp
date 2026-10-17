#pragma once
// Original-only FRADJ source-port from unmodified CALMET 6.5.0, calmet.for
// L7289-L7455. No dependency on any existing CTEAS P6D numerical routine.
// All state (except user integer ISURFT) and numerical operations are REAL*4.
// This kernel consumes original upstream GAMMA, HTOPO, HMAX, TEMP2D and WIND1
// output; generation of those states and full DIAGNO orchestration are
// explicitly outside this kernel's acceptance scope.
#include "cteas/p6d_rebuild/wind1_real4.hpp"
#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::p6d_rebuild {
struct FradjReal4Input {
    int nx=50,ny=50,nz=9,isurft=-1;
    Real4 dx_m=100.f,dy_m=100.f,tinf_k=285.f,critfn=1.f;
    std::array<Real4,10> zface_m{
        0.f,20.f,40.f,80.f,160.f,320.f,640.f,1200.f,2000.f,3000.f
    };
    std::vector<Real4> terrain_m,highest_m,gamma_kpm,temp2d_k,u_mps,v_mps;
};
struct FradjReal4Output {
    std::vector<Real4> u_mps,v_mps;
    std::size_t adjusted_cells=0;
};
inline FradjReal4Output fradj_source_real4(FradjReal4Input in) {
    constexpr std::size_t plane=2500;
    if(in.nx!=50||in.ny!=50||in.nz!=9||
       in.terrain_m.size()!=plane||in.highest_m.size()!=plane||
       in.gamma_kpm.size()!=plane||in.temp2d_k.size()!=plane||
       in.u_mps.size()!=9*plane||in.v_mps.size()!=9*plane||
       !(std::isfinite(in.dx_m)&&in.dx_m>0.f)||
       !(std::isfinite(in.dy_m)&&in.dy_m>0.f)||
       !(std::isfinite(in.tinf_k)&&in.tinf_k>0.f)||
       !(std::isfinite(in.critfn)&&in.critfn>=0.f))
        throw std::invalid_argument("FRADJ source-first invalid grid/control");
    for(auto v:in.zface_m)if(!std::isfinite(v))
        throw std::invalid_argument("FRADJ invalid ZFACE");
    for(int k=0;k<9;++k)if(in.zface_m[static_cast<std::size_t>(k+1)]<=
                        in.zface_m[static_cast<std::size_t>(k)])
        throw std::invalid_argument("FRADJ original vertical grid must increase");
    for(auto* v:{&in.terrain_m,&in.highest_m,&in.gamma_kpm,
                 &in.temp2d_k,&in.u_mps,&in.v_mps})
        for(Real4 x:*v)if(!std::isfinite(x))
            throw std::invalid_argument("FRADJ nonfinite inputs");
    constexpr Real4 tau=-0.01f,rpd=0.017453f,dpr=57.296f;
    const Real4 dxi=real4(0.5f/in.dx_m);
    const Real4 dyi=real4(0.5f/in.dy_m);
    std::size_t nchanged=0;
    for(int j=0;j<50;++j)for(int i=0;i<50;++i){
        const std::size_t p=static_cast<std::size_t>(j)*50+
                             static_cast<std::size_t>(i);
        const auto topo=[&](int x,int y)->Real4 {
            return in.terrain_m[static_cast<std::size_t>(y)*50+
                                static_cast<std::size_t>(x)];
        };
        const Real4 gamma2=real4(in.gamma_kpm[p]-tau);
        const Real4 htoim1=topo(i>0?i-1:i,j),htojm1=topo(i,j>0?j-1:j);
        const Real4 htoip1=topo(i<49?i+1:i,j),htojp1=topo(i,j<49?j+1:j);
        Real4 delhi=real4(real4(htoip1-htoim1)*dxi);
        Real4 delhj=real4(real4(htojp1-htojm1)*dyi);
        if(std::abs(delhi)<0.00015f&&std::abs(delhj)<0.00015f)
            delhi=delhj=0.f;
        const Real4 temp=in.isurft==-1?in.temp2d_k[p]:in.tinf_k;
        if(!(temp>0.f))throw std::invalid_argument("FRADJ negative surface T");
        for(int k=0;k<9;++k) {
            const std::size_t n=static_cast<std::size_t>(k)*plane+p;
            const Real4 u=in.u_mps[n],v=in.v_mps[n];
            const Real4 speed=real4(std::sqrt(real4(real4(u*u)+real4(v*v))));
            if(speed<=0.f)continue;
            const Real4 dz=real4(in.zface_m[static_cast<std::size_t>(k+1)]-
                                in.zface_m[static_cast<std::size_t>(k)]);
            const Real4 obs_height=real4(in.highest_m[p]-
                real4(real4(in.terrain_m[p]+in.zface_m[static_cast<std::size_t>(k)])+
                      real4(dz/2.f)));
            if(obs_height<=0.f||gamma2<=0.f)continue;
            const Real4 floater=real4(real4(real4(9.8f*gamma2)/temp));
            const Real4 denom=real4(real4(std::sqrt(floater))*obs_height);
            if(!(denom>0.f))continue;
            const Real4 froude=real4(speed/denom);
            if(froude>in.critfn)continue;
            if(delhi==0.f&&delhj==0.f)continue;
            Real4 theta=0.f;
            if(delhi==0.f)theta=delhj<0.f?270.f:90.f;
            else{
                const Real4 thetp=real4(real4(std::atan(real4(delhj/delhi)))*dpr);
                if(delhi<0.f)theta=real4(thetp+180.f);
                else theta=delhj>0.f?thetp:real4(thetp+360.f);
            }
            Real4 thetd=0.f;
            if(theta>=0.f&&theta<=90.f)thetd=real4(90.f-theta);
            else if(theta>90.f&&theta<=360.f)thetd=real4(450.f-theta);
            else throw std::invalid_argument("FRADJ source theta outside 0-360");
            const Real4 ang=real4(real4(270.f-thetd)*rpd);
            const Real4 drx=real4(-real4(std::cos(ang)));
            const Real4 dry=real4(-real4(std::sin(ang)));
            const Real4 un=real4(u/speed),vn=real4(v/speed);
            const Real4 aa=real4(real4(drx*un)+real4(dry*vn));
            if(aa<=0.f)continue;
            const Real4 tt=real4(real4(-real4(dry*un))+real4(drx*vn));
            const Real4 tax=tt>0.f?real4(-dry):dry;
            const Real4 tay=tt>0.f?drx:real4(-drx);
            in.u_mps[n]=real4(tax*speed);
            in.v_mps[n]=real4(tay*speed);
            ++nchanged;
        }
    }
    return {std::move(in.u_mps),std::move(in.v_mps),nchanged};
}
} // namespace cteas::p6d_rebuild
