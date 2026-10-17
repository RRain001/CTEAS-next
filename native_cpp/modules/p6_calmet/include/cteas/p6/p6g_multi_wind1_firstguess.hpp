#pragma once
// P6G G9 exploratory multi-station WIND1 first-guess generalization.
//
// Directly follows original calmet.for L36204-L36399 source ordering for
// the no-overwater, no-barrier, IEXTRP=-4 selected route. Supports multiple
// land SS and US columns with original sequential calm/missing reweighting. This is a TESTED
// C++ multi-site kernel, NOT yet independent Fortran multi-site equivalence.
// Frozen wind1_firstguess_selected.hpp remains the numerical authority for
// the 50x50x9 single-pair baseline. Do not use this as P6 production physics
// until source CALMET multi-site parity is established.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct Wind1MultiInput {
    int nx=0,ny=0,nz=0;
    float spacing_m=0.f;
    int surface_count=0,upper_count=0,icalm=0;
    // Station ordinal order: all SS first, then all US, from met.inp.
    std::vector<float> station_x_m,station_y_m,surface_speeds_mps;
    std::vector<float> vertical_bias;
    // (k*nstations+l) flattened REAL*4 observed profiles, U/V by layer.
    std::vector<float> station_u_mps,station_v_mps;
    // 1 denotes valid observation; 0 denotes truly missing input.
    std::vector<unsigned char> present;
};
struct Wind1MultiField {
    std::vector<float> u_mps,v_mps;
    int nx=0,ny=0,nz=0;
};
inline Wind1MultiField multi_station_wind1_firstguess(
    const Wind1MultiInput& in) {
    const int n=in.surface_count+in.upper_count;
    if(in.nx<2||in.ny<2||in.nz<1||in.nx>400||in.ny>400||in.nz>12||
       in.surface_count<1||in.upper_count<1||n>479||
       (in.icalm!=0&&in.icalm!=1)||
       !std::isfinite(in.spacing_m)||in.spacing_m<=0.f)
        throw std::invalid_argument("G9 WIND1 grid, source counts or mode invalid");
    const std::size_t cells=static_cast<std::size_t>(in.nx)*
                            static_cast<std::size_t>(in.ny);
    if(cells*static_cast<std::size_t>(in.nz)>4'000'000)
        throw std::invalid_argument("G9 WIND1 cell allocation exceeds 4M budget");
    const auto nc=static_cast<std::size_t>(n);
    const auto nk=static_cast<std::size_t>(in.nz);
    if(in.station_x_m.size()!=nc||in.station_y_m.size()!=nc||
       in.surface_speeds_mps.size()!=static_cast<std::size_t>(in.surface_count)||
       in.vertical_bias.size()!=nk||
       in.station_u_mps.size()!=nk*nc||
       in.station_v_mps.size()!=nk*nc||
       in.present.size()!=nk*nc)
        throw std::invalid_argument("G9 WIND1 profile, flag or coordinate count mismatch");
    for(std::size_t l=0;l<nc;++l)
        if(!std::isfinite(in.station_x_m[l])||
           !std::isfinite(in.station_y_m[l]))
            throw std::invalid_argument("G9 WIND1 invalid local station coordinate");
    for(float speed:in.surface_speeds_mps)
        if(!std::isfinite(speed)||speed<0.f||speed>=998.99f)
            throw std::invalid_argument("G9 WIND1 invalid observed surface speed");
    for(float bias:in.vertical_bias)
        if(!std::isfinite(bias)||bias< -1.f||bias>1.f)
            throw std::invalid_argument("G9 WIND1 BIAS outside [-1,1]");
    for(std::size_t k=0;k<nk;++k)
        for(std::size_t l=0;l<nc;++l){
            const std::size_t z=k*nc+l;
            if(in.present[z]>1)
                throw std::invalid_argument("G9 WIND1 non-boolean validity mask");
            if(in.present[z]&&
               (!std::isfinite(in.station_u_mps[z])||
                !std::isfinite(in.station_v_mps[z])||
                std::abs(in.station_u_mps[z])>=998.99f||
                std::abs(in.station_v_mps[z])>=998.99f))
                throw std::invalid_argument("G9 WIND1 valid profile has missing values");
            if(l<static_cast<std::size_t>(in.surface_count)&&
               in.surface_speeds_mps[l]<1.e-4f&&in.present[z]&&
               (in.station_u_mps[z]!=0.f||in.station_v_mps[z]!=0.f))
                throw std::invalid_argument("G9 WIND1 calm surface with invented profile");
        }
    Wind1MultiField out;
    out.nx=in.nx;out.ny=in.ny;out.nz=in.nz;
    out.u_mps.resize(cells*nk);out.v_mps.resize(cells*nk);
    std::vector<float> raw(nc),base(nc),adjusted(nc);
    const float inv_grid=1.f/in.spacing_m;
    // Mirrors frozen CALMET FIELD1/2 FORTRAN grid order I outer, J inner.
    for(int i=1;i<=in.nx;++i)for(int j=1;j<=in.ny;++j){
        const float xc=static_cast<float>(i)-0.5f;
        const float yc=static_cast<float>(j)-0.5f;
        float total=0.f;
        for(std::size_t l=0;l<nc;++l){
            const float dx=in.station_x_m[l]*inv_grid-xc;
            const float dy=in.station_y_m[l]*inv_grid-yc;
            const float r2=dx*dx+dy*dy;
            raw[l]=r2<1.f?1.f:1.f/r2;
            // Original WIND1 excludes absent surface anemometer
            // observations from the bulk weight normalization (L36239-42).
            if(l<static_cast<std::size_t>(in.surface_count)&&!in.present[l])
                raw[l]=0.f;
            total+=raw[l];
        }
        if(!std::isfinite(total)||total<=0.f)
            throw std::invalid_argument("G9 WIND1 singular inverse-square total");
        const float inverse=1.f/total;
        float surface_base=0.f,upper_base=0.f;
        for(std::size_t l=0;l<nc;++l){
            base[l]=raw[l]*inverse;
            if(l<static_cast<std::size_t>(in.surface_count))
                surface_base+=base[l];
            else upper_base+=base[l];
        }
        if(surface_base<=0.f||upper_base<=0.f)
            throw std::invalid_argument("G9 WIND1 zero surface/upper class share");
        for(std::size_t k=0;k<nk;++k){
            // For exactly one SS/US, these beta/gamma operations reduce
            // to wind1_firstguess_selected's original selected route.
            const float bias=in.vertical_bias[k];
            float beta=0.f,gamma=0.f;
            if(bias>=0.f){
                beta=1.f-bias;
                gamma=(bias+(1.f-bias)*upper_base)/upper_base;
            }else{
                beta=(-bias+(1.f+bias)*surface_base)/surface_base;
                gamma=1.f+bias;
            }
            // Exact selected source control order (calmet.for L36279-36395):
            //   1. BIAS class multiplier by station,
            //   2. each calm land station in ordinal order (ICALM=0),
            //   3. each missing upper-air station in ordinal order,
            //   4. unnormalized REAL*4 U/V accumulation over all stations.
            // This must NOT be replaced by a combined missing-data
            // renormalization: sequential divisions change the floating
            // point result whenever multiple stations are invalid.
            for(std::size_t l=0;l<nc;++l)
                adjusted[l]=(l<static_cast<std::size_t>(in.surface_count)?
                             beta:gamma)*base[l];
            if(in.icalm==0)
                for(int l=0;l<in.surface_count;++l){
                    const std::size_t z=static_cast<std::size_t>(l);
                    if(in.present[z]&&in.surface_speeds_mps[z]<0.0001f&&k>0){
                        const float old=adjusted[z];
                        if(old<0.9999f){
                            const float inv=1.f-old;
                            if(inv<=0.f)
                                throw std::invalid_argument("G9 WIND1 calm sum singular");
                            for(std::size_t ll=0;ll<nc;++ll)
                                if(ll!=z)adjusted[ll]=adjusted[ll]/inv;
                        }else{
                            const float inverse=1.f-base[z];
                            if(inverse<=0.f)
                                throw std::invalid_argument("G9 WIND1 no valid upper for calm");
                            for(std::size_t ll=static_cast<std::size_t>(in.surface_count);
                                ll<nc;++ll)
                                adjusted[ll]=base[ll]/inverse;
                        }
                        adjusted[z]=0.f;
                    }
                }
            if(bias> -0.9999f)
                for(std::size_t l=static_cast<std::size_t>(in.surface_count);
                    l<nc;++l){
                    if(!in.present[k*nc+l]){
                        const float old=adjusted[l];
                        if(old==1.f)
                            throw std::invalid_argument("G9 WIND1 no other valid upper wind");
                        const float denom=1.f-old;
                        if(denom<=0.f)
                            throw std::invalid_argument("G9 WIND1 invalid missing upper weight");
                        for(std::size_t ll=0;ll<nc;++ll)
                            if(ll!=l)adjusted[ll]=adjusted[ll]/denom;
                        adjusted[l]=0.f;
                    }
                }
            float u=0.f,v=0.f;
            bool have=false;
            for(std::size_t l=0;l<nc;++l){
                const float wt=adjusted[l];
                if(wt>0.f&&in.present[k*nc+l])have=true;
                u=u+wt*in.station_u_mps[k*nc+l];
                v=v+wt*in.station_v_mps[k*nc+l];
            }
            if(!have)
                throw std::invalid_argument("G9 WIND1 no usable observations");
            if(!std::isfinite(u)||!std::isfinite(v))
                throw std::invalid_argument("G9 WIND1 nonfinite field");
            const std::size_t idx=k*cells+
                static_cast<std::size_t>(j-1)*static_cast<std::size_t>(in.nx)+
                static_cast<std::size_t>(i-1);
            out.u_mps[idx]=u;out.v_mps[idx]=v;
        }
    }
    return out;
}
} // namespace cteas::calmet::p6g
