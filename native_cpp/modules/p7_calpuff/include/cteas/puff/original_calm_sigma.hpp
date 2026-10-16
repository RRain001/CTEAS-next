#pragma once
// CALPUFF 7.2.1 SIGTY 50962-51022 / SIGTZ 51458-51573.
// Source-derived REAL*4 IDOPTYS=IDOPTZS=1, EL<=0 and EL>0 stable branches.
// MHFTSZ=1 and absent /CSIGMA/ turbulence parameters still fail closed.
#include <cmath>
#include <stdexcept>
namespace cteas::puff {
struct OriginalCalmSigmaInput {
 float sy0=0,sz0=0,dt_s=0,dx_km=0,uavg=0,sigv=0,sigw=0;
 float el=0,tyidr=0,tzidr=0,tzisdr=0,syh=550,ayt=0,thfty=0;
};
struct OriginalCalmSigmaOutput {
 float sy=0,virty=0,virdy=0,sz=0,virtz=0,virdz=0;
};
[[nodiscard]] inline OriginalCalmSigmaOutput original_calm_sigma(
    const OriginalCalmSigmaInput& p) {
    auto need=[](bool b,const char* msg){if(!b)throw std::invalid_argument(msg);};
    const float a[]={p.sy0,p.sz0,p.dt_s,p.dx_km,p.uavg,p.sigv,p.sigw,
                     p.el,p.tyidr,p.tzidr,p.tzisdr,p.syh,p.ayt,p.thfty};
    for(const float v:a)need(std::isfinite(v),"calm SIGTY/SIGTZ nonfinite");
    need(p.sy0>=0&&p.sz0>=0&&p.dt_s>=0&&p.dx_km>=0&&p.uavg>0&&
         p.sigv>0&&p.sigw>0&&p.tyidr>=0&&p.tzidr>=0&&p.tzisdr>0&&
         p.syh>0&&p.ayt>0&&p.thfty>=0,
         "calm SIGTY/SIGTZ missing native turbulence or invalid input");
    constexpr float zero=0.0F,zerosig=0.001F;
    OriginalCalmSigmaOutput r;
    if((p.dt_s>p.thfty&&p.sy0<zerosig)||p.sy0>p.syh) {
        const float tprime=p.syh/p.ayt-p.thfty;
        const float t=p.sy0>p.syh ? (p.sy0/p.ayt-tprime)+p.dt_s : p.dt_s;
        r.sy=p.ayt*(t+tprime);
        r.virty=t;
        r.virdy=p.uavg*t*0.001F;
    } else {
        float t0=zero;
        if(p.sy0>zerosig) {
            const float gama=p.sy0/p.sigv;
            const float beta=gama*(1.0F+0.405F*gama*p.tyidr);
            t0=beta+std::sqrt(beta*beta-gama*gama);
        }
        const float t=t0+p.dt_s;
        r.virty=t;
        r.virdy=p.uavg*t*0.001F;
        if(p.dt_s>zero) {
            const float fy=1.0F/(1.0F+0.9F*std::sqrt(t*p.tyidr));
            r.sy=p.sigv*t*fy;
        } else r.sy=p.sy0;
    }
    float t0=zero;
    if(p.sz0>zerosig){
        const float gama=p.sz0/p.sigw;
        if(p.el<=zero){
            const float beta=gama*(1.0F+0.405F*gama*p.tzidr);
            t0=beta+std::sqrt(beta*beta-gama*gama);
        } else {
            // Verbatim algorithm from vendor SIGTZ L51486-51554.
            const float gamal=std::log(gama);
            float t1=gama;
            float gm1=std::log(t1/(1.0F+0.945F*
                std::pow(p.tzisdr*t1,0.806F)));
            float t1l=std::log(t1);
            const float tcrit=1.2675F/p.tzisdr;
            float t2=t1<=tcrit ? 2.0F*t1 :
                std::pow(gama*0.945F*std::pow(p.tzisdr,0.806F),
                         5.154639F);
            need(std::isfinite(t2)&&t2>zero,"invalid stable SIGTZ seed");
            float gm2=std::log(t2/(1.0F+0.945F*
                std::pow(p.tzisdr*t2,0.806F)));
            float t2l=std::log(t2);
            bool converged=false;
            for(int niter=1;niter<=50;++niter){
                const float denx=t2l-t1l;
                float t3l;
                if(denx==zero)t3l=t2l;
                else {
                    const float gm_diff=gm2-gm1;
                    need(gm_diff!=zero,"singular stable SIGTZ secant");
                    const float fint=(gamal-gm1)/gm_diff;
                    t3l=t1l+fint*denx;
                    const float step=t3l-t2l;
                    const float xstep=0.85F*std::abs(denx);
                    if(std::abs(step)>xstep)t3l=t2l+std::copysign(xstep,step);
                }
                const float t3=std::exp(t3l);
                const float gm3=t3/(1.0F+0.945F*
                    std::pow(p.tzisdr*t3,0.806F));
                const float errsig=(gm3-gama)/gama;
                need(std::isfinite(errsig),"nonfinite stable SIGTZ residual");
                if(std::abs(errsig)<1.0e-4F){
                    t0=t3;converged=true;break;
                }
                t1=t2;t1l=t2l;gm1=gm2;
                t2=t3;t2l=t3l;gm2=std::log(gm3);
            }
            need(converged,"stable SIGTZ secant nonconvergence");
        }
    }
    const float t=t0+p.dt_s;
    r.virtz=t;
    if(p.dt_s>zero){
        const float fz=p.el<=zero ?
            1.0F/(1.0F+0.9F*std::sqrt(p.tzidr*t)) :
            1.0F/(1.0F+0.945F*std::pow(p.tzisdr*t,0.806F));
        r.sz=p.sigw*t*fz;
    } else r.sz=p.sz0;
    r.virdz=t*p.uavg*0.001F;
    need(std::isfinite(r.sy)&&std::isfinite(r.sz)&&
         std::isfinite(r.virty)&&std::isfinite(r.virtz),
         "nonfinite original IDOPT1 turbulence result");
    return r;
}
} // namespace cteas::puff
