#pragma once
// CALMET 6.5.0 MINIM + WINDBC, original calmet.for L9645-9761
// and L36404-36441; DIVCEL source-scoped L6246-6303.
// Isolated mass-consistency iteration, NOT full DIAGNO integration.
#include "cteas/p6/divcel.hpp"
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>
namespace cteas::calmet::p6 {
struct MinimOutput {
    DivcelInput wind;
    std::vector<float> divergence_per_s;
    std::vector<float> last_divmax_per_s;
};
// Input U/V are cell centers; W is held fixed as in original MINIM.
// Boundary data must be provided from original WIND1/DIAGNO, not guessed.
inline MinimOutput original_minim_scoped(
    DivcelInput in,int niter,float divlim_per_s) {
    if(niter<0||niter>1000||!std::isfinite(divlim_per_s)||divlim_per_s<0.f)
        throw std::invalid_argument("MINIM invalid iterations or DIVLIM");
    // The source-backed DIVCEL validates all array dimensions and finite state.
    auto initial=original_divcel_scoped(in);
    const auto nx=in.nx,ny=in.ny,nz=in.nz;
    const auto plane=std::size_t(nx)*std::size_t(ny);
    std::vector<float> divergence=std::move(initial.divergence_per_s);
    std::vector<float> maxima=std::move(initial.max_abs_per_s);
    auto idx=[&](int i,int j,int k)->std::size_t {
        return std::size_t(k)*plane+std::size_t(j)*std::size_t(nx)+std::size_t(i);
    };
    auto ub_at=[&](int j,int side,int k)->std::size_t {
        return std::size_t(k)*2*std::size_t(ny)+
               std::size_t(side)*std::size_t(ny)+std::size_t(j);
    };
    auto vb_at=[&](int i,int side,int k)->std::size_t {
        return std::size_t(k)*2*std::size_t(nx)+
               std::size_t(side)*std::size_t(nx)+std::size_t(i);
    };
    for(int k=0;k<nz;++k) {
        if(maxima[std::size_t(k)]<=divlim_per_s)continue;
        for(int iter=0;iter<niter;++iter){
            for(int idir=0;idir<4;++idir){
                for(int jj=0;jj<ny;++jj)for(int ii=0;ii<nx;++ii){
                    const int i=(idir==1||idir==3)?nx-ii-1:ii;
                    const int j=(idir==2||idir==3)?ny-jj-1:jj;
                    const auto p=idx(i,j,k);
                    const float div=divergence[p];
                    if(div==0.f)continue;
                    // Original MINIM uses ALPHA1=...=ALPHA4=0.5,
                    // AL1234=2, updates neighbors in place, in four sweeps.
                    const float ut=-2.f*(div*in.dx_m)/2.f;
                    const float vt=-2.f*(div*in.dy_m)/2.f;
                    float uim1=i>0?in.u_mps[idx(i-1,j,k)]:
                                in.ub_west_east_mps[ub_at(j,0,k)];
                    float uip1=i<nx-1?in.u_mps[idx(i+1,j,k)]:
                                 in.ub_west_east_mps[ub_at(j,1,k)];
                    float vjm1=j>0?in.v_mps[idx(i,j-1,k)]:
                                in.vb_south_north_mps[vb_at(i,0,k)];
                    float vjp1=j<ny-1?in.v_mps[idx(i,j+1,k)]:
                                 in.vb_south_north_mps[vb_at(i,1,k)];
                    uip1=uip1+0.5f*ut;
                    uim1=uim1-0.5f*ut;
                    vjp1=vjp1+0.5f*vt;
                    vjm1=vjm1-0.5f*vt;
                    if(i>0)in.u_mps[idx(i-1,j,k)]=uim1;
                    if(i<nx-1)in.u_mps[idx(i+1,j,k)]=uip1;
                    if(j>0)in.v_mps[idx(i,j-1,k)]=vjm1;
                    if(j<ny-1)in.v_mps[idx(i,j+1,k)]=vjp1;
                }
                // Original MINIM recalculates DIVCEL before WINDBC.
                const auto step=original_divcel_scoped(in);
                for(std::size_t p=std::size_t(k)*plane;
                    p<std::size_t(k+1)*plane;++p)
                    divergence[p]=step.divergence_per_s[p];
                maxima[std::size_t(k)]=step.max_abs_per_s[std::size_t(k)];
                // Original WINDBC, not no-flux zero, snapshots edge cells.
                for(int j=0;j<ny;++j){
                    in.ub_west_east_mps[ub_at(j,0,k)]=in.u_mps[idx(0,j,k)];
                    in.ub_west_east_mps[ub_at(j,1,k)]=in.u_mps[idx(nx-1,j,k)];
                }
                for(int i=0;i<nx;++i){
                    in.vb_south_north_mps[vb_at(i,0,k)]=in.v_mps[idx(i,0,k)];
                    in.vb_south_north_mps[vb_at(i,1,k)]=in.v_mps[idx(i,ny-1,k)];
                }
            }
            if(maxima[std::size_t(k)]<=divlim_per_s)break;
        }
    }
    return {std::move(in),std::move(divergence),std::move(maxima)};
}
} // namespace cteas::calmet::p6
