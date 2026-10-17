#pragma once
// CALMET 6.5.0 original SMOOTH (calmet.for L30606–30681).
// Source-scoped, one selected branch only: LLBREZE=.FALSE.
// Sequential in-place i-fastest,j-next,k-next; DO K, DO pass, DO J, DO I.
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6 {
struct SmoothInput {
    int nx=0,ny=0,nz=0;
    bool lake_breeze=false;
    std::vector<int> passes_per_layer;
    // k * nx*ny + j*nx + i
    std::vector<float> u_mps,v_mps;
    // U boundary: [k][side 0 west/1 east][j]; V boundary [k][side 0 south/1 north][i]
    std::vector<float> ub_west_east_mps, vb_south_north_mps;
};
struct SmoothOutput {
    std::vector<float> u_mps,v_mps;
};
inline SmoothOutput smooth_original_scoped(SmoothInput in) {
    if(in.nx<2||in.ny<2||in.nz<1||in.nx>400||in.ny>400||in.nz>12)
        throw std::invalid_argument("SMOOTH invalid grid");
    if(in.lake_breeze)
        throw std::invalid_argument("SMOOTH LLBREZE box branch not supported");
    const std::size_t plane=std::size_t(in.nx)*std::size_t(in.ny);
    const std::size_t nz=std::size_t(in.nz);
    if(in.passes_per_layer.size()!=nz||in.u_mps.size()!=plane*nz||
       in.v_mps.size()!=plane*nz||
       in.ub_west_east_mps.size()!=2*std::size_t(in.ny)*nz||
       in.vb_south_north_mps.size()!=2*std::size_t(in.nx)*nz)
        throw std::invalid_argument("SMOOTH input shape mismatch");
    for(int count:in.passes_per_layer)
        if(count<0||count>1000)
            throw std::invalid_argument("SMOOTH invalid smoothing passes");
    const auto finite=[](const auto& v) {
        for(float x:v)if(!std::isfinite(x))
            throw std::invalid_argument("SMOOTH invalid wind or boundary");
    };
    finite(in.u_mps);finite(in.v_mps);
    finite(in.ub_west_east_mps);finite(in.vb_south_north_mps);
    const auto at=[&](int i,int j,int k)->std::size_t{
        return std::size_t(k)*plane+std::size_t(j)*std::size_t(in.nx)+std::size_t(i);
    };
    const auto ub_at=[&](int j,int side,int k)->std::size_t{
        return std::size_t(k)*2*std::size_t(in.ny)+
               std::size_t(side)*std::size_t(in.ny)+std::size_t(j);
    };
    const auto vb_at=[&](int i,int side,int k)->std::size_t{
        return std::size_t(k)*2*std::size_t(in.nx)+
               std::size_t(side)*std::size_t(in.nx)+std::size_t(i);
    };
    for(int k=0;k<in.nz;++k) {
        for(int pass=0;pass<in.passes_per_layer[std::size_t(k)];++pass) {
            for(int j=0;j<in.ny;++j)for(int i=0;i<in.nx;++i) {
                const auto p=at(i,j,k);
                const float uim1=(i>0)?in.u_mps[at(i-1,j,k)]:
                             in.ub_west_east_mps[ub_at(j,0,k)];
                const float ujm1=(j>0)?in.u_mps[at(i,j-1,k)]:in.u_mps[p];
                const float vim1=(i>0)?in.v_mps[at(i-1,j,k)]:in.v_mps[p];
                const float vjm1=(j>0)?in.v_mps[at(i,j-1,k)]:
                             in.vb_south_north_mps[vb_at(i,0,k)];
                const float uip1=(i<in.nx-1)?in.u_mps[at(i+1,j,k)]:
                             in.ub_west_east_mps[ub_at(j,1,k)];
                const float ujp1=(j<in.ny-1)?in.u_mps[at(i,j+1,k)]:in.u_mps[p];
                const float vip1=(i<in.nx-1)?in.v_mps[at(i+1,j,k)]:in.v_mps[p];
                const float vjp1=(j<in.ny-1)?in.v_mps[at(i,j+1,k)]:
                             in.vb_south_north_mps[vb_at(i,1,k)];
                // Original Fortran REAL*4 source expression and assignment order.
                in.u_mps[p]=0.5f*in.u_mps[p]+0.125f*(uip1+uim1+ujp1+ujm1);
                in.v_mps[p]=0.5f*in.v_mps[p]+0.125f*(vip1+vim1+vjp1+vjm1);
            }
        }
    }
    return {std::move(in.u_mps),std::move(in.v_mps)};
}
} // namespace cteas::calmet::p6
