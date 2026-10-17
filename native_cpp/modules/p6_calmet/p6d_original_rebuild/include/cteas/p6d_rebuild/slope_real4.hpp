#pragma once
// Source-first independent port of original CALMET 6.5.0 SLOPE
// (calmet.for L30372-L30605). Original COMMON grid/metgrd/geo semantics
// are provided as explicit inputs, REAL*4 throughout. No old P6 kernel used.
// Actual QH, TERSET HMAX/HMIN/distance and original state are *not* inferred.
#include "cteas/p6d_rebuild/wind1_real4.hpp"
#include <array>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::p6d_rebuild {
struct SlopeReal4Input {
    int nx=50,ny=50,nz=9,iwat1=50,iwat2=55,isurft=-1;
    Real4 dx_m=100.f,dy_m=100.f,tinf_k=285.f;
    std::array<Real4,10> zface_m{0.f,20.f,40.f,80.f,160.f,
                                320.f,640.f,1200.f,2000.f,3000.f};
    std::vector<Real4> topo_m,hmax_m,hmin_m,disthmax_m,disthmin_m;
    std::vector<Real4> qh_w_m2,temp2d_k;
    std::vector<int> landuse;
};
struct SlopeReal4Output {std::vector<Real4> u_mps,v_mps;};

inline SlopeReal4Output slope_source_real4(const SlopeReal4Input& c){
    constexpr std::size_t plane=2500;
    if(c.nx!=50||c.ny!=50||c.nz!=9||c.iwat1>c.iwat2||
       !(c.dx_m>0.f)||!(c.dy_m>0.f)||!(c.tinf_k>0.f)||
       c.topo_m.size()!=plane||c.hmax_m.size()!=plane||
       c.hmin_m.size()!=plane||c.disthmax_m.size()!=plane||
       c.disthmin_m.size()!=plane||c.qh_w_m2.size()!=plane||
       c.temp2d_k.size()!=plane||c.landuse.size()!=plane)
        throw std::invalid_argument("SLOPE original input shape/controls invalid");
    for(const auto* list:{&c.topo_m,&c.hmax_m,&c.hmin_m,&c.disthmax_m,
                          &c.disthmin_m,&c.qh_w_m2,&c.temp2d_k})
        for(Real4 value:*list)
            if(!std::isfinite(value))throw std::invalid_argument(
                "SLOPE original input contains nonfinite value");
    for(int k=0;k<9;++k)
        if(!(c.zface_m[static_cast<std::size_t>(k+1)]>
             c.zface_m[static_cast<std::size_t>(k)]))
            throw std::invalid_argument("SLOPE ZFACE must increase");
    const auto at=[](int i,int j)->std::size_t{
        return static_cast<std::size_t>(j)*50+static_cast<std::size_t>(i);
    };
    SlopeReal4Output out;
    out.u_mps.assign(plane*9,0.f);
    out.v_mps.assign(plane*9,0.f);
    constexpr Real4 rhocp=1229.9f,cdk=.08f,rpd=.017453f,dpr=57.296f;
    const Real4 dxi=real4(0.5f/c.dx_m),dyi=real4(0.5f/c.dy_m);
    for(int j=0;j<50;++j)for(int i=0;i<50;++i){
        const auto p=at(i,j);
        const int lu=c.landuse[p];
        if(lu>=c.iwat1&&lu<=c.iwat2)continue;
        const Real4 temp=(c.isurft>0||c.isurft==-2)?
                         c.tinf_k:c.temp2d_k[p];
        if(!(temp>0.f))throw std::invalid_argument("SLOPE surface T invalid");
        const Real4 htoim1=c.topo_m[at(i>0?i-1:i,j)];
        const Real4 htojm1=c.topo_m[at(i,j>0?j-1:j)];
        const Real4 htoip1=c.topo_m[at(i<49?i+1:i,j)];
        const Real4 htojp1=c.topo_m[at(i,j<49?j+1:j)];
        const Real4 delhi=real4(real4(htoip1-htoim1)*dxi);
        const Real4 delhj=real4(real4(htojp1-htojm1)*dyi);
        const Real4 sint=real4(std::sqrt(
            real4(real4(delhi*delhi)+real4(delhj*delhj))));
        const Real4 aalpha=real4(std::atan(sint));
        if(std::abs(aalpha)<0.009f)continue;
        Real4 sinalf=real4(std::sin(std::abs(aalpha)));
        const Real4 height_diff=c.qh_w_m2[p]<0.f?
            real4(c.hmax_m[p]-c.topo_m[p]):
            real4(c.topo_m[p]-c.hmin_m[p]);
        const Real4 distance=c.qh_w_m2[p]<0.f?
            c.disthmax_m[p]:c.disthmin_m[p];
        const Real4 dcrest=real4(std::sqrt(
            real4(real4(height_diff*height_diff)+
                  real4(distance*distance))));
        const Real4 hd=real4(0.05f*height_diff);
        Real4 uvally=0.f;
        if(hd>0.05f){
            if(c.qh_w_m2[p]<0.f){
                if(!(dcrest>0.f))throw std::invalid_argument(
                    "SLOPE downslope zero crest distance");
                sinalf=std::min(sinalf,real4(height_diff/dcrest));
                Real4 tempmef=real4(real4(-real4(dcrest*cdk))/hd);
                tempmef=std::max(tempmef,-50.f);
                const Real4 force=real4(
                    real4(real4(real4(
                        real4(sinalf*real4(9.81f/temp))*
                        std::abs(c.qh_w_m2[p]))*dcrest)/rhocp)/cdk);
                uvally=real4(-real4(
                    real4(std::pow(force,real4(1.f/3.f)))*
                    real4(std::pow(
                      real4(1.f-real4(std::exp(tempmef))),real4(1.f/3.f)))));
            }else{
                const Real4 force=real4(
                    real4(real4(real4(9.81f/temp)*std::abs(c.qh_w_m2[p]))*
                    height_diff)/rhocp);
                uvally=real4(std::pow(force,real4(1.f/3.f)));
            }
        }
        if(delhi==0.f&&delhj==0.f)continue;
        Real4 theta{};
        if(delhi==0.f)theta=delhj<0.f?270.f:90.f;
        else{
            const Real4 thetp=real4(real4(std::atan(real4(delhj/delhi)))*dpr);
            if(delhi<0.f)theta=real4(thetp+180.f);
            else theta=delhj>0.f?thetp:real4(thetp+360.f);
        }
        Real4 thetd{};
        if(theta>=0.f&&theta<=90.f)thetd=real4(90.f-theta);
        else if(theta>90.f&&theta<=360.f)thetd=real4(450.f-theta);
        else throw std::invalid_argument("SLOPE drainage angle invalid");
        const Real4 ang=real4(real4(270.f-thetd)*rpd);
        const Real4 delu=real4(-real4(real4(std::cos(ang))*uvally));
        const Real4 delv=real4(-real4(real4(std::sin(ang))*uvally));
        for(int k=0;k<9;++k){
            const std::size_t ix=static_cast<std::size_t>(k);
            Real4 ratio=0.f;
            if(hd>c.zface_m[ix+1])ratio=1.f;
            else if(hd>c.zface_m[ix]){
                ratio=real4(real4(hd-c.zface_m[ix])/
                    real4(c.zface_m[ix+1]-c.zface_m[ix]));
            }
            const auto pos=ix*plane+p;
            out.u_mps[pos]=real4(delu*ratio);
            out.v_mps[pos]=real4(delv*ratio);
        }
    }
    return out;
}
} // namespace cteas::p6d_rebuild
