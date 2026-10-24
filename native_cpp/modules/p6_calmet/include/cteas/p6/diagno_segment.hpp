#pragma once
// Selected CALMET 6.5.0 DIAGNO no-lake-breeze, IOBR=0 final-wind segment:
// original calmet.for L6119-L6148: SMOOTH, initialize W, DIVCEL all
// layers, vertical W integration, WINDBC boundaries each layer.
// This does not implement WIND1, INTER2, or upstream full DIAGNO.
#include "cteas/p6/smooth.hpp"
#include "cteas/p6/divcel.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6 {
struct FinalWindSegment {
    std::vector<float> u_mps,v_mps,w_face_mps,divergence_per_s;
    std::vector<float> ub_west_east_mps,vb_south_north_mps;
};
inline FinalWindSegment original_smooth_divcel_w(
    SmoothInput winds,float dx_m,float dy_m,const std::vector<float>& dz_m,
    bool obrien_adjustment=false,
    std::vector<float>* test_only_post_smooth_u=nullptr,
    std::vector<float>* test_only_post_smooth_v=nullptr) {
    if(obrien_adjustment)
        throw std::invalid_argument("DIAGNO selected IOBR=0 only");
    const int nx=winds.nx,ny=winds.ny,nz=winds.nz;
    // Keep original boundary winds from initial guessed / interpolated wind
    // through SMOOTH and DIVCEL. WIND BC is refreshed only AFTER the
    // original computes ALL layer divergences and integrates W.
    auto ub=std::move(winds.ub_west_east_mps);
    auto vb=std::move(winds.vb_south_north_mps);
    winds.ub_west_east_mps=ub;
    winds.vb_south_north_mps=vb;
    auto smoothed=smooth_original_scoped(std::move(winds));
    // Optional observational snapshot at original DIAGNO stage100,
    // before DIVCEL. No new arithmetic or mutation of the live wind.
    if(test_only_post_smooth_u)
        *test_only_post_smooth_u=smoothed.u_mps;
    if(test_only_post_smooth_v)
        *test_only_post_smooth_v=smoothed.v_mps;
    const auto plane=std::size_t(nx)*std::size_t(ny);
    DivcelInput divin;
    divin.nx=nx;divin.ny=ny;divin.nz=nz;
    divin.dx_m=dx_m;divin.dy_m=dy_m;divin.dz_m=dz_m;
    divin.u_mps=smoothed.u_mps;divin.v_mps=smoothed.v_mps;
    divin.w_mps.assign(plane*(std::size_t(nz)+1),0.f);
    divin.ub_west_east_mps=ub;
    divin.vb_south_north_mps=vb;
    // Original stage computes DIVCEL for *all* K while W is zero.
    const auto divergence=original_divcel_scoped(divin);
    auto w=std::move(divin.w_mps);
    for(int k=0;k<nz;++k) {
        for(std::size_t p=0;p<plane;++p) {
            const auto row=std::size_t(k)*plane+p;
            w[row+plane]=-dz_m[std::size_t(k)]*
                         divergence.divergence_per_s[row]+w[row];
        }
        // Original WINDBC updates edges after each W-layer integration.
        const auto at=[nx,plane](int i,int j,int layer)->std::size_t {
            return std::size_t(layer)*plane+
                   std::size_t(j)*std::size_t(nx)+std::size_t(i);
        };
        for(int j=0;j<ny;++j) {
            const auto lo=std::size_t(k)*2*std::size_t(ny)+std::size_t(j);
            ub[lo]=smoothed.u_mps[at(0,j,k)];
            ub[lo+std::size_t(ny)]=smoothed.u_mps[at(nx-1,j,k)];
        }
        for(int i=0;i<nx;++i) {
            const auto lo=std::size_t(k)*2*std::size_t(nx)+std::size_t(i);
            vb[lo]=smoothed.v_mps[at(i,0,k)];
            vb[lo+std::size_t(nx)]=smoothed.v_mps[at(i,ny-1,k)];
        }
    }
    return {std::move(smoothed.u_mps),std::move(smoothed.v_mps),
            std::move(w),divergence.divergence_per_s,
            std::move(ub),std::move(vb)};
}
} // namespace cteas::calmet::p6
