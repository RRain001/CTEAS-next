#pragma once
// CALMET v6.5.0 SURFVAR L12544-13064, all-land multistation observed
// TEMP/RH interpolation, IAVET=0 ITPROG=0 IRHPROG=0 NPSTA=0 IALL=1.
// Distances and weight caps reproduce IRAD 1 or 2 and NUMTS/TRAD.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
struct ObservedSurfaceStation {
    float x_m=0.f,y_m=0.f,temp_k=9999.f;
    int rh_pct=9999;
};
struct SurfvarMultistationInput {
    std::size_t nx=0,ny=0;
    float dgrid_m=100.f,trad_grid=3.f;
    int irad=1,numts=4;
    std::vector<ObservedSurfaceStation> stations;
};
struct SurfvarMultistationResult {
    std::vector<float> temp2d_k;
    std::vector<int> rh2d_pct,ipcode2d;
};
struct ObsFieldDistance {
    float distance;
    std::size_t station;
};
inline float interpolate_surfvar_field(
    const SurfvarMultistationInput& x,const std::vector<ObsFieldDistance>& eligible,
    bool humidity) {
    if(eligible.empty()) {
        if(humidity)return 80.f; // original no eligible RH overland
        throw std::invalid_argument("SURFVAR no eligible observed temperature station");
    }
    if(eligible[0].distance>x.trad_grid) {
        const auto& s=x.stations[eligible[0].station];
        return humidity?static_cast<float>(s.rh_pct):s.temp_k;
    }
    float sumwt=0.f,tsurf=0.f;
    int nused=0;
    for(const auto& e:eligible){
        if(e.distance>x.trad_grid||nused>=x.numts)break;
        float dist=e.distance;
        if(x.irad==2)dist=dist*dist;
        const float wt=dist<1.f?1.f:1.f/dist;
        const auto& s=x.stations[e.station];
        sumwt+=wt;
        tsurf+=wt*(humidity?static_cast<float>(s.rh_pct):s.temp_k);
        ++nused;
    }
    if(!(sumwt>0.f)||!std::isfinite(tsurf))
        throw std::invalid_argument("SURFVAR nonfinite inverse-distance sum");
    return tsurf/sumwt;
}
inline SurfvarMultistationResult surfvar_multistation(const SurfvarMultistationInput& x) {
    if(x.nx==0||x.ny==0||x.nx>std::numeric_limits<std::size_t>::max()/x.ny||
       !std::isfinite(x.dgrid_m)||x.dgrid_m<=0.f||
       !std::isfinite(x.trad_grid)||x.trad_grid<0.f||
       (x.irad!=1&&x.irad!=2)||x.numts<=0||
       // No hard station-count cap: selected source data owns station
       // cardinality; checked grid sizing and available memory bound runs.
       // Preserve original SURFVAR pairwise selection-sort and REAL4 sums.
       x.stations.empty())
        throw std::invalid_argument("SURFVAR selected multistation control invalid");
    bool valid_temp=false;
    for(const auto& s:x.stations){
        if(!std::isfinite(s.x_m)||!std::isfinite(s.y_m)||
           !std::isfinite(s.temp_k))
            throw std::invalid_argument("SURFVAR invalid observed station");
        if(s.temp_k<9998.99f){
            if(s.temp_k<180.f||s.temp_k>350.f)
                throw std::invalid_argument("SURFVAR physical temperature out of range");
            valid_temp=true;
        }
        if(s.rh_pct!=9999&&(s.rh_pct<0||s.rh_pct>100))
            throw std::invalid_argument("SURFVAR invalid station humidity");
    }
    if(!valid_temp)throw std::invalid_argument("SURFVAR no usable temperature station");
    const auto n=x.nx*x.ny;
    SurfvarMultistationResult r{std::vector<float>(n,288.f),
        std::vector<int>(n,80),std::vector<int>(n,0)};
    const float dgridi=1.f/x.dgrid_m;
    for(std::size_t i=0;i<x.nx;++i){
        const float xc=static_cast<float>(i+1)-0.5f;
        for(std::size_t j=0;j<x.ny;++j){
            const float yc=static_cast<float>(j+1)-0.5f;
            std::vector<ObsFieldDistance> tlist, rhlist;
            for(std::size_t st=0;st<x.stations.size();++st){
                const auto& s=x.stations[st];
                const float dx=s.x_m*dgridi-xc;
                const float dy=s.y_m*dgridi-yc;
                const float r2=dx*dx+dy*dy;
                const float dist=std::sqrt(r2);
                if(s.temp_k<9998.99f)tlist.push_back({dist,st});
                if(s.rh_pct<9999)rhlist.push_back({dist,st});
            }
            // Reproduce original CALMET SURFVAR pairwise selection-sort.
            // Swaps can indirectly reorder equal-distance stations.
            // std::stable_sort changes which station reaches NUMTS.
            auto original_sort=[](std::vector<ObsFieldDistance>& values){
                for(std::size_t ii=0;ii<values.size();++ii)
                    for(std::size_t jj=ii+1;jj<values.size();++jj)
                        if(values[ii].distance>values[jj].distance)
                            std::swap(values[ii],values[jj]);
            };
            original_sort(tlist);
            original_sort(rhlist);
            const auto k=j*x.nx+i;
            r.temp2d_k[k]=interpolate_surfvar_field(x,tlist,false);
            const float interp_rh=interpolate_surfvar_field(x,rhlist,true);
            r.rh2d_pct[k]=static_cast<int>(interp_rh); // Fortran INT truncates
        }
    }
    return r;
}
} // namespace cteas::p6e
