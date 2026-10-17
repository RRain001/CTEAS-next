#pragma once
// CALMET v6.5.0 original PGTSTB calmet.for L13295-13498.
// Turner-Pasquill-Gifford class for LAND cells; water is not computed.
// Real 2022 COMP integration and cloud provenance remain separate gates.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
inline constexpr int missing_pgt = -999;
struct PgtInput {
    std::size_t nx = 0,ny = 0;
    int mcloud = 1, water_first = 50, water_last = 60;
    // All gridded arrays indexed (j*nx+i), nearest station ONE-based.
    std::vector<float> u10,v10,sinalp,ccgrid;
    std::vector<int> nearest,landuse,ceilgrid;
    // Original station ICC is measured in tenths, ceiling in 100 feet.
    std::vector<int> station_cloud,station_ceil;
};
inline std::vector<int> pgtstb(const PgtInput& x) {
    if(x.nx==0||x.ny==0||x.nx>static_cast<std::size_t>(-1)/x.ny||
       x.mcloud<1||x.mcloud>4||x.water_first>x.water_last)
        throw std::invalid_argument("PGTSTB dimensions/mode");
    const std::size_t n=x.nx*x.ny;
    if(x.u10.size()!=n||x.v10.size()!=n||x.sinalp.size()!=n||
       x.ccgrid.size()!=n||x.nearest.size()!=n||x.landuse.size()!=n||
       x.ceilgrid.size()!=n||x.station_cloud.empty()||
       x.station_cloud.size()!=x.station_ceil.size())
        throw std::invalid_argument("PGTSTB arrays/stations");
    // Fortran DATA jstab(12,7), array storage order column major.
    static constexpr int jstab[7][12]={
        {6,6,6,6,6,6,5,5,5,5,4,4},
        {6,6,6,5,5,5,4,4,4,4,4,4},
        {4,4,4,4,4,4,4,4,4,4,4,4},
        {3,3,3,4,4,4,4,4,4,4,4,4},
        {2,2,2,3,3,3,3,3,3,4,4,4},
        {1,2,2,2,2,2,2,3,3,3,3,4},
        {1,1,1,1,1,2,2,2,2,3,3,3}
    };
    static constexpr float scrit[3]={0.258819f,0.5735764f,0.8660254f};
    std::vector<int> out(n,missing_pgt);
    for(std::size_t j=0;j<x.ny;++j) for(std::size_t i=0;i<x.nx;++i) {
        const std::size_t cell=j*x.nx+i;
        if(x.landuse[cell]>=x.water_first&&x.landuse[cell]<=x.water_last)
            continue;
        const int ns=x.nearest[cell];
        if(ns<1||static_cast<std::size_t>(ns)>x.station_cloud.size())
            throw std::invalid_argument("PGTSTB invalid nearest station");
        if(!std::isfinite(x.u10[cell])||!std::isfinite(x.v10[cell])||
           !std::isfinite(x.sinalp[cell])||x.sinalp[cell]<-1.000001f||
           x.sinalp[cell]>1.000001f)
            throw std::invalid_argument("PGTSTB invalid wind/solar");
        if(x.mcloud>=2 &&
           (!std::isfinite(x.ccgrid[cell])||x.ccgrid[cell]<0.0f||
            x.ccgrid[cell]>1.0f))
            throw std::invalid_argument("PGTSTB invalid gridded cloud");
        const int ceiling = x.mcloud>=3 ? x.ceilgrid[cell] :
                                                x.station_ceil[static_cast<std::size_t>(ns-1)];
        if(ceiling<0)throw std::invalid_argument("PGTSTB invalid ceiling");
        const int cc=x.mcloud>1 ? static_cast<int>(10.0f*x.ccgrid[cell]+0.5f) :
                                x.station_cloud[static_cast<std::size_t>(ns-1)];
        if(cc<0||cc>10)throw std::invalid_argument("PGTSTB cloud outside tenths");
        int ic=-2;
        if(x.sinalp[cell]<=0.0f) {
            if(cc>4) {
                ic=-1;
                if(cc==10&&ceiling<70)ic=0;
            }
        } else {
            int iri=4;
            for(int k=0;k<3;++k)if(x.sinalp[cell]<=scrit[k]){iri=k+1;break;}
            ic=iri;
            if(cc>5) {
                if(cc==10) {
                    if(ceiling<70)ic=0;
                    else if(ceiling<160)ic=std::max(iri-2,1);
                    else ic=std::max(iri-1,1);
                } else {
                    if(ceiling<70)ic=std::max(iri-2,1);
                    else if(ceiling<160)ic=std::max(iri-1,1);
                }
            }
        }
        // The original computes float32 sqrt, knots and truncates (positive).
        const float knot=1.9438f*std::sqrt(x.u10[cell]*x.u10[cell]+
                                           x.v10[cell]*x.v10[cell])+0.5f;
        if(!std::isfinite(knot)||knot>static_cast<float>(2147483647))
            throw std::invalid_argument("PGTSTB wind overflow");
        const int speed=std::clamp(static_cast<int>(knot),1,12);
        if(ic< -2||ic>4)throw std::logic_error("PGTSTB category out of range");
        out[cell]=jstab[ic+2][speed-1];
    }
    return out;
}
} // namespace cteas::p6e
