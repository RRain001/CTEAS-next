#pragma once
// Independent source-first REAL*4 port of the selected original DIAGNO tail.
// calmet.for SMOOTH L30606-L30681; DIVCEL L6246-L6303;
// WINDBC L36404-L36441; DIAGNO call sequence L6119-L6148.
// Source form is **in-place** SMOOTH: reusing already updated west/south cells
// is intentional. DIVCEL is run with all W=0 for every K before integrating
// W from below, then WINDBC runs layer by layer. No OMP CTEAS P6 code included.
//
// Scope frozen 50x50x9, no lake breeze, IOBR=0, no terrain minims.
// Upstream U/V and original UB/VB boundary snapshots are REQUIRED inputs;
// their independent generation is an upstream reconstruction and not inferred.
#include "cteas/p6d_rebuild/wind1_real4.hpp"
#include <array>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::p6d_rebuild {
struct DiagnoTailInput {
    int nx=50,ny=50,nz=9;
    Real4 dx_m=100.f,dy_m=100.f;
    std::array<Real4,9> dz_m{};
    std::array<int,9> smooth_passes{};
    std::vector<Real4> u_mps,v_mps;
    // Boundary indices [k][side: west/east or south/north][j or i].
    std::vector<Real4> ub_mps,vb_mps;
};
struct DiagnoTailOutput {
    std::vector<Real4> u_mps,v_mps,w_face_mps,divergence_per_s;
    std::vector<Real4> ub_mps,vb_mps;
};
inline DiagnoTailOutput original_diagno_tail_real4(DiagnoTailInput in){
    constexpr int nx=50,ny=50,nz=9;
    constexpr std::size_t plane=static_cast<std::size_t>(nx)*ny;
    if(in.nx!=nx||in.ny!=ny||in.nz!=nz||
       in.u_mps.size()!=plane*nz||in.v_mps.size()!=plane*nz||
       in.ub_mps.size()!=static_cast<std::size_t>(nz)*2*ny||
       in.vb_mps.size()!=static_cast<std::size_t>(nz)*2*nx||
       !std::isfinite(in.dx_m)||in.dx_m<=0.f||
       !std::isfinite(in.dy_m)||in.dy_m<=0.f)
        throw std::invalid_argument("unverified DIAGNO tail grid or boundary inputs");
    for(int k=0;k<nz;++k){
        if(!(in.dz_m[static_cast<std::size_t>(k)]>0.f)||
           in.smooth_passes[static_cast<std::size_t>(k)]<0||
           in.smooth_passes[static_cast<std::size_t>(k)]>100)
            throw std::invalid_argument("DIAGNO invalid layer control");
    }
    for(const auto* data:{&in.u_mps,&in.v_mps,&in.ub_mps,&in.vb_mps})
        for(Real4 value:*data)
            if(!std::isfinite(value))
                throw std::invalid_argument("nonfinite original DIAGNO input");
    const auto at=[](int i,int j,int k)->std::size_t {
        return static_cast<std::size_t>(k)*plane+
            static_cast<std::size_t>(j)*nx+static_cast<std::size_t>(i);
    };
    const auto ub=[](int j,int side,int k)->std::size_t {
        return static_cast<std::size_t>(k)*2*ny+
            static_cast<std::size_t>(side)*ny+static_cast<std::size_t>(j);
    };
    const auto vb=[](int i,int side,int k)->std::size_t {
        return static_cast<std::size_t>(k)*2*nx+
            static_cast<std::size_t>(side)*nx+static_cast<std::size_t>(i);
    };
    // CALMET SMOOTH processes one layer, then one pass, then J, then I,
    // overwriting U/V at the current cell immediately (not double-buffered).
    for(int k=0;k<nz;++k)for(int pass=0;pass<in.smooth_passes[static_cast<std::size_t>(k)];++pass){
        for(int j=0;j<ny;++j)for(int i=0;i<nx;++i){
            const auto self=at(i,j,k);
            const Real4 u_now=in.u_mps[self],v_now=in.v_mps[self];
            const Real4 uim1=i>0?in.u_mps[at(i-1,j,k)]:in.ub_mps[ub(j,0,k)];
            const Real4 ujm1=j>0?in.u_mps[at(i,j-1,k)]:u_now;
            const Real4 vim1=i>0?in.v_mps[at(i-1,j,k)]:v_now;
            const Real4 vjm1=j>0?in.v_mps[at(i,j-1,k)]:in.vb_mps[vb(i,0,k)];
            const Real4 uip1=i<nx-1?in.u_mps[at(i+1,j,k)]:in.ub_mps[ub(j,1,k)];
            const Real4 ujp1=j<ny-1?in.u_mps[at(i,j+1,k)]:u_now;
            const Real4 vip1=i<nx-1?in.v_mps[at(i+1,j,k)]:v_now;
            const Real4 vjp1=j<ny-1?in.v_mps[at(i,j+1,k)]:in.vb_mps[vb(i,1,k)];
            const Real4 sumu=real4(real4(real4(uip1+uim1)+ujp1)+ujm1);
            const Real4 sumv=real4(real4(real4(vip1+vim1)+vjp1)+vjm1);
            in.u_mps[self]=real4(real4(0.5f*u_now)+real4(0.125f*sumu));
            in.v_mps[self]=real4(real4(0.5f*v_now)+real4(0.125f*sumv));
        }
    }
    std::vector<Real4> w(plane*(nz+1),0.f),div(plane*nz,0.f);
    const Real4 dxi=real4(1.f/real4(2.f*in.dx_m));
    const Real4 dyi=real4(1.f/real4(2.f*in.dy_m));
    for(int k=0;k<nz;++k){
        const Real4 dzi=real4(1.f/in.dz_m[static_cast<std::size_t>(k)]);
        for(int j=0;j<ny;++j)for(int i=0;i<nx;++i){
            const auto self=at(i,j,k);
            const Real4 uph=i<nx-1?in.u_mps[at(i+1,j,k)]:in.ub_mps[ub(j,1,k)];
            const Real4 umh=i>0?in.u_mps[at(i-1,j,k)]:in.ub_mps[ub(j,0,k)];
            const Real4 vph=j<ny-1?in.v_mps[at(i,j+1,k)]:in.vb_mps[vb(i,1,k)];
            const Real4 vmh=j>0?in.v_mps[at(i,j-1,k)]:in.vb_mps[vb(i,0,k)];
            const Real4 dudx=real4(real4(uph-umh)*dxi);
            const Real4 dvdy=real4(real4(vph-vmh)*dyi);
            const Real4 dwdz=real4(real4(w[self+plane]-w[self])*dzi);
            div[self]=real4(real4(dudx+dvdy)+dwdz);
        }
    }
    // All DIVCEL layers above are finished before W is integrated.
    for(int k=0;k<nz;++k){
        for(std::size_t p=0;p<plane;++p){
            const auto n=static_cast<std::size_t>(k)*plane+p;
            w[n+plane]=real4(real4(-real4(in.dz_m[static_cast<std::size_t>(k)]*
                                     div[n]))+w[n]);
        }
        // Original WINDBC(U,V,UB,VB,K) at the end of each W layer.
        for(int j=0;j<ny;++j){
            in.ub_mps[ub(j,0,k)]=in.u_mps[at(0,j,k)];
            in.ub_mps[ub(j,1,k)]=in.u_mps[at(nx-1,j,k)];
        }
        for(int i=0;i<nx;++i){
            in.vb_mps[vb(i,0,k)]=in.v_mps[at(i,0,k)];
            in.vb_mps[vb(i,1,k)]=in.v_mps[at(i,ny-1,k)];
        }
    }
    return {std::move(in.u_mps),std::move(in.v_mps),std::move(w),
            std::move(div),std::move(in.ub_mps),std::move(in.vb_mps)};
}
} // namespace cteas::p6d_rebuild
