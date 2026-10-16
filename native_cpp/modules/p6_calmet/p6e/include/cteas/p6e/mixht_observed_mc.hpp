#pragma once
// Selected CALMET 6.5.0 MIXHT grid path over LAND with the AA/BB
// older-sounding choice JUSTA and the IUPT override. Both original
// convective-growth closures are selectable exactly as in the source:
//   |IMIXH|=1 Maul-Carson (MIXHMC), |IMIXH|=2 Batchvarova-Gryning (MIXHBG).
// Source CALMET v6.5.0 L10411-10682. Water-cell physics, the IMFXIH sign
// distinction over water, complete COMP AA/BB buffer lifetime and averaged
// heights are NOT here.
#include "cteas/p6e/mixdt.hpp"
#include "cteas/p6e/mixhbg.hpp"
#include "cteas/p6e/mixhmc.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
// Optional per-cell trace of one MIXHT call. Diagnostic only: it records
// the exact term values the kernel acted on, so they can be compared
// against the original's internal-state dump term by term.
// branch: 0 water skip, 1 stable land branch, 2 MIXHMC no-growth return,
// 3 MIXHMC relaxation, 4 MIXHMC convective growth, 5 MIXHBG.
struct MixhtObservedMcTrace {
    bool hit=false;
    int branch=-1;
    float htold_m=0.f,wt_mks=0.f,gamma_mixdt=0.f,dptt_in=0.f;
    float gamma_used=0.f,dpttp1_k=0.f,ziconv_m=0.f,dptt_out=0.f;
    float tht_k=0.f,thtp_k=0.f,tave_k=0.f,bvf=0.f,hmech_m=0.f,zi_m=0.f;
};
struct MixhtObservedMcInput {
    std::size_t nx=0,ny=0;
    int water_first=50,water_last=60,iupt=-1;
    // Original MIXHT IMIXH: magnitude 1 = Maul-Carson (MIXHMC),
    // magnitude 2 = Batchvarova-Gryning (MIXHBG). The sign only selects
    // the over-water scheme, so magnitude is what matters on land.
    int imixh=1;
    // COMP calls WATER/WATERP (L4616-4622) immediately before MIXHT
    // (L4692) and ELUSTR2 calls MIXHTST/MIXHT2ST (L6881/6884) for the single
    // surface-station cell (ist,jst). That cell is therefore processed twice
    // per hour, so when the grid pass enters it the /tjump/ DPTT already
    // holds the current hour's own DPTTP1. Instrumented-dump evidence over
    // 143 h x 2500 cells: the entering DPTT equals the previous hour's
    // output everywhere except that one cell, where it equals the value the
    // hour leaves - and the station cell's whole ZI/WSTAR/T-LEV residual
    // (and its AVEMIX halo) is exactly this. 0 disables the refresh,
    // reproducing the standalone MIXHT harness.
    int dptt_refresh=0;
    std::size_t refresh_i=static_cast<std::size_t>(-1);
    std::size_t refresh_j=static_cast<std::size_t>(-1);
    int izicrlx=0,timestep_s=3600;
    float constn=2400.f,zimin=20.f,zimax=2500.f;
    float threshl=0.02f,dptmin=0.001f,dzzi=200.f;
    float onedte=4140.f,twodte=1080.f,tzicrlx=800.f;
    // first index AA (0) vs BB (1), second index station.
    std::array<std::vector<MixdtSounding>,2> sounding;
    std::vector<int> justa,nearu,landuse;
    std::vector<float> qh,ustar,el,rho,cmech,fcori;
    std::vector<float> initial_zi,initial_ziconv,initial_dptt;
    // Optional single-cell trace capture (see MixhtObservedMcTrace).
    std::size_t trace_i=static_cast<std::size_t>(-1);
    std::size_t trace_j=static_cast<std::size_t>(-1);
    MixhtObservedMcTrace* trace=nullptr;
};
struct MixhtObservedMcResult {
    std::vector<float> zi,ziconv,dptt;
};
inline MixhtObservedMcResult mixht_observed_mc(const MixhtObservedMcInput& a) {
    if(!a.nx||!a.ny||a.nx>std::numeric_limits<std::size_t>::max()/a.ny||
       a.water_first>a.water_last || a.sounding[0].empty() ||
       a.sounding[0].size()!=a.sounding[1].size() ||
       a.sounding[0].size()!=a.justa.size() ||
       (a.iupt!= -1 && (a.iupt<1||
        static_cast<std::size_t>(a.iupt)>a.justa.size())) ||
       (a.imixh!=1&&a.imixh!=-1&&a.imixh!=2&&a.imixh!=-2) ||
       !std::isfinite(a.zimin)||a.zimin<0.f||
       !std::isfinite(a.zimax)||a.zimax<a.zimin||
       !std::isfinite(a.constn)||a.constn<=0.f||
       !std::isfinite(a.threshl)||a.threshl<0.f||
       !std::isfinite(a.dptmin)||a.dptmin<=0.f||
       !std::isfinite(a.dzzi)||a.dzzi<=0.f)
        throw std::invalid_argument("MIXHT MC invalid controls or AA/BB extents");
    const auto n=a.nx*a.ny;
    if(a.nearu.size()!=n||a.landuse.size()!=n||
       a.qh.size()!=n||a.ustar.size()!=n||a.el.size()!=n||
       a.rho.size()!=n||a.cmech.size()!=n||a.fcori.size()!=n||
       a.initial_zi.size()!=n||a.initial_ziconv.size()!=n||
       a.initial_dptt.size()!=n)
        throw std::invalid_argument("MIXHT MC invalid grid extent");
    MixhtObservedMcResult r{a.initial_zi,a.initial_ziconv,a.initial_dptt};
    constexpr float cp=996.f,g=9.81f;
    // Original Fortran loops i first, then j. Each cell is independent.
    for(std::size_t i=0;i<a.nx;++i)for(std::size_t j=0;j<a.ny;++j){
        const auto k=j*a.nx+i;
        const bool tr=a.trace!=nullptr&&i==a.trace_i&&j==a.trace_j;
        if(a.landuse[k]>=a.water_first&&a.landuse[k]<=a.water_last) {
            if(tr){a.trace->hit=true;a.trace->branch=0;}
            continue; // water sentinel remains unchanged
        }
        if(!std::isfinite(a.qh[k])||!std::isfinite(a.ustar[k])||
           a.ustar[k]<=0.f||!std::isfinite(a.el[k])||
           !std::isfinite(a.fcori[k])||a.fcori[k]<=0.f||
           !std::isfinite(a.rho[k])||a.rho[k]<=0.f||
           !std::isfinite(a.cmech[k])||a.cmech[k]<=0.f)
            throw std::invalid_argument("MIXHT MC nonphysical land input");
        if(a.qh[k]<0.f) {
            if(a.el[k]<=0.f)throw std::invalid_argument("MIXHT MC stable EL<=0");
            const float zi1=a.constn*std::pow(a.ustar[k],1.5f);
            const float zi2=0.4f*std::sqrt(a.ustar[k]*a.el[k]/a.fcori[k]);
            const float entering=r.ziconv[k];
            r.zi[k]=std::max(a.zimin,std::min({zi1,zi2,a.zimax}));
            r.ziconv[k]=0.f;
            r.dptt[k]=0.f;
            if(tr){a.trace->hit=true;a.trace->branch=1;a.trace->htold_m=entering;
                   a.trace->ziconv_m=0.f;a.trace->dptt_out=0.f;a.trace->zi_m=r.zi[k];}
            continue;
        }
        const int nearest=a.nearu[k];
        if(nearest<1||static_cast<std::size_t>(nearest)>a.justa.size())
            throw std::invalid_argument("MIXHT MC invalid upper-air station");
        const int st=(a.iupt>0?a.iupt:nearest)-1;
        const std::size_t sk=static_cast<std::size_t>(st);
        // Fortran JUSTA>0: AA older; otherwise BB older.
        const auto buffer=a.justa[sk]>0?0U:1U;
        const float htold=r.ziconv[k];
        const auto& older=a.sounding[buffer][sk];
        const auto sounding=mixdt(older,
                                  htold,a.dzzi,a.dptmin);
        const float wt=a.qh[k]/(a.rho[k]*cp);
        float gamma=sounding.dtheta_k_per_m;
        if(tr){
            a.trace->hit=true;a.trace->htold_m=htold;a.trace->wt_mks=wt;
            a.trace->gamma_mixdt=sounding.dtheta_k_per_m;
            a.trace->dptt_in=r.dptt[k];
            a.trace->tht_k=sounding.tht_k;a.trace->thtp_k=sounding.thtp_k;
        }
        if(a.imixh==2||a.imixh==-2){
            // Original MIXHT IMIXH=2 branch: Batchvarova-Gryning growth.
            // TK is the first face temperature of the selected sounding
            // (tzbb/tzaa(kusta,1)); MIXHBG does not update DPTT.
            const float tk=older.temp_k[0];
            if(!std::isfinite(tk)||tk<=0.f)
                throw std::invalid_argument("MIXHT BG invalid sounding surface temperature");
            MixhbgInput b;
            b.wt_mks=wt;
            b.gamma_kperm=gamma;
            b.threshold_wm2perm=a.threshl;
            b.zimax_m=a.zimax;b.zimin_m=a.zimin;
            b.ustar_ms=a.ustar[k];
            b.el_m=a.el[k];
            b.zicbgold_m=htold;
            b.tk_k=tk;
            b.izicrlx=a.izicrlx;b.timestep_s=a.timestep_s;
            b.tzicrlx_s=a.tzicrlx;
            b.dptmin_kperm=a.dptmin;
            const auto conv=mixhbg_lapse2(b);
            r.ziconv[k]=std::min(a.zimax,conv.ziconv_m);
            // MIXHBG applies the DPTMIN floor to the caller's lapse rate.
            gamma=conv.gamma_kperm;
            if(tr){a.trace->branch=5;a.trace->gamma_used=conv.gamma_kperm;
                   a.trace->ziconv_m=r.ziconv[k];a.trace->dptt_out=r.dptt[k];}
        }else{
            MixhmcInput m;
            m.wt_mks=wt;
            m.gamma_kperm=gamma;
            m.threshold_wm2perm=a.threshl;
            m.zimax_m=a.zimax;m.htold_m=htold;
            m.dptt_k=r.dptt[k];
            if(a.dptt_refresh&&i==a.refresh_i&&j==a.refresh_j) {
                // Original pre-MIXHT refresh of the /tjump/ DPTT: the value
                // handed to the growth is the current hour's DPTTP1.
                constexpr float wto_rho=1.2f,wto_cp=996.f;
                const float gclamp=std::max(gamma,a.dptmin);
                const float buoy=wt-a.threshl*htold/(wto_rho*wto_cp);
                if(buoy>0.f)m.dptt_k=std::sqrt(std::max(gclamp*a.twodte*buoy,0.f));
            }
            m.tht_k=sounding.tht_k;m.thtp_k=sounding.thtp_k;
            if(tr)a.trace->dptt_in=m.dptt_k;
            m.izicrlx=a.izicrlx;m.timestep_s=a.timestep_s;
            m.tzicrlx_s=a.tzicrlx;
            m.dptmin_kperm=a.dptmin;
            m.twodte_s=a.twodte;m.onedte_s=a.onedte;
            const auto conv=mixhmc_lapse2(m);
            r.ziconv[k]=std::min(a.zimax,conv.ziconv_m);
            r.dptt[k]=conv.dptt_k;
            gamma=conv.gamma_kperm;
            if(tr){a.trace->branch=2+conv.branch;a.trace->gamma_used=conv.gamma_kperm;
                   a.trace->dpttp1_k=conv.dpttp1_k;
                   a.trace->ziconv_m=r.ziconv[k];a.trace->dptt_out=r.dptt[k];}
        }
        const float tave=(sounding.thtp_k+sounding.tht_k)/2.f;
        if(!(tave>0.f))throw std::invalid_argument("MIXHT MC nonphysical mean temperature");
        const float bvf=std::pow(g*gamma/tave,0.25f);
        const float hmech=a.cmech[k]*a.ustar[k]/bvf;
        r.zi[k]=std::min(a.zimax,std::max({a.zimin,hmech,r.ziconv[k]}));
        if(tr){a.trace->tave_k=tave;a.trace->bvf=bvf;a.trace->hmech_m=hmech;
               a.trace->zi_m=r.zi[k];}
        if(!std::isfinite(r.zi[k])||!std::isfinite(r.ziconv[k])||
           !std::isfinite(r.dptt[k]))
            throw std::invalid_argument("MIXHT MC produced nonfinite height");
    }
    return r;
}
} // namespace cteas::p6e
