#pragma once
// Independent CALMET 6.5.0 INTER2 source-first selected C++ port.
// Original calmet.for L8124-L8616. Selected flags: IPROG=0, NOOBS=0,
// NBAR=0, grid 50x50x9. Supports LVARY, actual layer-wise NINTRP,
// land/water RMAX1-3 and WO observations. Does not include OMP CTEAS code.
//
// Critical original precision: RS/FIELD1/FIELD2/WO are REAL*4, but WT,
// WT2/WT3 are explicitly DOUBLE PRECISION (calmet.for L8242-8243).
// Preserve REAL4 expression evaluation before converting its result to REAL8
// and REAL4 destination rounding after mixed-precision accumulation.
#include "cteas/p6d_rebuild/wind1_real4.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::p6d_rebuild {
struct Inter2SelectedSourceInput {
    int nx=50,ny=50,nz=9;
    int nstations=0,iprog=0,noobs=0,nbar=0,water_first=50,water_last=55;
    bool lvary=false;
    Real4 dx_m=100.f,dy_m=100.f;
    Real4 rmin_km{},rmax1_km{},rmax2_km{},rmax3_km{},r1_km{},r2_km{};
    Real4 edit=999999.f,editl=999998.f;
    std::array<int,9> nintrp{};
    std::vector<Real4> station_x_km,station_y_km;
    std::vector<int> landuse;
    // Level-major K, then station L, matching original STDAT1(K,L).
    std::vector<Real4> observations;
    std::vector<Real4> first_guess;
    std::vector<Real4> wo;
};
struct Inter2SelectedSourceOutput {
    std::vector<Real4> field;
    std::vector<int> contributors;
    std::vector<int> lvary_fallback;
};
inline Inter2SelectedSourceOutput inter2_source_real4(
    const Inter2SelectedSourceInput& in) {
    constexpr int nx=50,ny=50,nz=9;
    constexpr std::size_t plane=2500;
    const auto nst=static_cast<std::size_t>(in.nstations);
    if(in.nx!=nx||in.ny!=ny||in.nz!=nz||
       in.nstations<1||in.nstations>479||in.iprog!=0||
       in.noobs!=0||in.nbar!=0||in.water_first>in.water_last||
       in.station_x_km.size()!=nst||in.station_y_km.size()!=nst||
       in.landuse.size()!=plane||in.observations.size()!=nst*nz||
       in.first_guess.size()!=plane*nz||in.wo.size()!=plane*nz||
       !std::isfinite(in.dx_m)||!std::isfinite(in.dy_m)||
       in.dx_m<=0.f||in.dy_m<=0.f||
       !(in.rmin_km>0.f&&in.rmax1_km>0.f&&in.rmax2_km>0.f&&
         in.rmax3_km>0.f&&in.r1_km>0.f&&in.r2_km>0.f))
        throw std::invalid_argument("unsupported original INTER2 scoped inputs");
    for(int k=0;k<nz;++k)
        if(in.nintrp[static_cast<std::size_t>(k)]<1||
           in.nintrp[static_cast<std::size_t>(k)]>in.nstations)
            throw std::invalid_argument("INTER2 NINTRP out of range");
    for(const auto* values:{
        &in.station_x_km,&in.station_y_km,&in.observations,
        &in.first_guess,&in.wo})
        for(Real4 v:*values)
            if(!std::isfinite(v))
                throw std::invalid_argument("INTER2 invalid observation or grid value");
    const Real4 dxk=real4(in.dx_m*0.001f);
    const Real4 dyk=real4(in.dy_m*0.001f);
    const Real4 rmax=std::max({in.rmax1_km,in.rmax2_km,in.rmax3_km});
    Inter2SelectedSourceOutput o;
    o.field.assign(plane*nz,0.f);
    o.contributors.assign(plane*nz,0);
    o.lvary_fallback.assign(plane*nz,0);

    for(int j=1;j<=ny;++j)for(int i=1;i<=nx;++i){
        const Real4 x=real4(real4(static_cast<Real4>(i)-0.5f)*dxk);
        const Real4 y=real4(real4(static_cast<Real4>(j)-0.5f)*dyk);
        const int land_cat=in.landuse[static_cast<std::size_t>(j-1)*nx+i-1];
        const bool is_land=land_cat<in.water_first||land_cat>in.water_last;
        std::vector<Real4> distance(nst,in.edit);
        std::array<Real4,9> min_distance;
        std::array<int,9> min_station{};
        min_distance.fill(9.9e9f);
        for(std::size_t l=0;l<nst;++l){
            bool valid_any=false;
            for(int k=0;k<nz;++k)
                if(in.observations[static_cast<std::size_t>(k)*nst+l]<in.editl)
                    valid_any=true;
            if(!valid_any)continue;
            const Real4 rsx=real4(x-in.station_x_km[l]);
            const Real4 rsy=real4(y-in.station_y_km[l]);
            const Real4 rs2=real4(real4(rsx*rsx)+real4(rsy*rsy));
            Real4 rs=real4(std::sqrt(rs2));
            if(in.lvary)for(int k=0;k<nz;++k){
                if(in.observations[static_cast<std::size_t>(k)*nst+l]<in.editl
                   &&rs<min_distance[static_cast<std::size_t>(k)]) {
                    min_distance[static_cast<std::size_t>(k)]=rs;
                    min_station[static_cast<std::size_t>(k)]=static_cast<int>(l)+1;
                }
            }
            if(rs<in.rmin_km)rs=in.rmin_km;
            if(rs<=rmax)distance[l]=rs;
        }
        // FMINF sorts the stations by clipped RS and preserves initial
        // station order on equal RS (FMINF uses the first strict minimum).
        std::vector<int> order(nst);
        for(std::size_t l=0;l<nst;++l)order[l]=static_cast<int>(l);
        std::stable_sort(order.begin(),order.end(),[&](int a,int b){
            return distance[static_cast<std::size_t>(a)]<
                   distance[static_cast<std::size_t>(b)];
        });
        for(int k=0;k<nz;++k){
            const std::size_t at=static_cast<std::size_t>(k)*plane+
                static_cast<std::size_t>(j-1)*nx+static_cast<std::size_t>(i-1);
            const Real4 r=k==0?in.r1_km:in.r2_km;
            const Real4 max_r=is_land?(k==0?in.rmax1_km:in.rmax2_km):
                                      in.rmax3_km;
            std::vector<int> chosen;
            for(int l:order){
                const std::size_t ix=static_cast<std::size_t>(l);
                if(distance[ix]>in.editl)break;
                if(in.observations[static_cast<std::size_t>(k)*nst+ix]>in.editl)
                    continue;
                if(distance[ix]>max_r)continue;
                chosen.push_back(l);
                if(static_cast<int>(chosen.size())>=
                   in.nintrp[static_cast<std::size_t>(k)])break;
            }
            Real4 fallback_distance=0.f;
            if(chosen.empty()&&in.lvary){
                const int closest=min_station[static_cast<std::size_t>(k)]-1;
                if(closest<0)
                    throw std::invalid_argument("INTER2 LVARY no valid station");
                chosen.push_back(closest);
                fallback_distance=std::max(
                    min_distance[static_cast<std::size_t>(k)],in.rmin_km);
                o.lvary_fallback[at]=1;
            }
            Real4 field1=0.f,field2=0.f;
            for(int l:chosen){
                const std::size_t ix=static_cast<std::size_t>(l);
                const Real4 rs=o.lvary_fallback[at]?fallback_distance:distance[ix];
                const Real4 rs_sq=real4(rs*rs);
                // Original WT is REAL*8, but WO/(RS**2) has REAL*4 operands.
                const double wt=static_cast<double>(real4(in.wo[at]/rs_sq));
                field1=real4(static_cast<Real4>(
                    static_cast<double>(field1)+
                    static_cast<double>(in.observations[
                        static_cast<std::size_t>(k)*nst+ix])*wt));
                field2=real4(static_cast<Real4>(
                    static_cast<double>(field2)+wt));
            }
            const double wt3=static_cast<double>(real4(
                1.f/real4(r*r)));
            const double blended=(static_cast<double>(field1)+
                static_cast<double>(in.first_guess[at])*wt3)/
                (static_cast<double>(field2)+wt3);
            if(!std::isfinite(blended))
                throw std::invalid_argument("INTER2 nonfinite weighted blend");
            o.field[at]=real4(static_cast<Real4>(blended));
            o.contributors[at]=static_cast<int>(chosen.size());
        }
    }
    return o;
}
} // namespace cteas::p6d_rebuild
