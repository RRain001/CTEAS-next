#pragma once
// Original CALMET 6.5.0 DIVCEL, calmet.for L6246-6303.
// Divergence at terrain-conformal cell faces. Isolated source-scoped kernel;
// not MINIM convergence or full 3-D diagnostic wind reconstruction.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6 {
struct DivcelInput {
    int nx=0,ny=0,nz=0;
    float dx_m=0,dy_m=0;
    std::vector<float> dz_m;
    // k-major, j-major, i-fastest arrays. W contains nz+1 faces.
    std::vector<float> u_mps,v_mps,w_mps;
    // Per-k: [west j=0..ny-1, east j=0..ny-1].
    std::vector<float> ub_west_east_mps;
    // Per-k: [south i=0..nx-1, north i=0..nx-1].
    std::vector<float> vb_south_north_mps;
};
struct DivcelOutput {
    std::vector<float> divergence_per_s; // k-major, i fastest
    std::vector<float> max_abs_per_s;    // one per vertical layer
};
inline DivcelOutput original_divcel_scoped(const DivcelInput& in) {
    if(in.nx<2||in.ny<2||in.nz<1||in.nx>400||in.ny>400||in.nz>12||
       !std::isfinite(in.dx_m)||!std::isfinite(in.dy_m)||
       in.dx_m<=0.f||in.dy_m<=0.f)
        throw std::invalid_argument("DIVCEL invalid grid");
    const auto n=std::size_t(in.nx)*std::size_t(in.ny);
    const auto kmax=std::size_t(in.nz);
    if(in.dz_m.size()!=kmax||in.u_mps.size()!=n*kmax||
       in.v_mps.size()!=n*kmax||in.w_mps.size()!=n*(kmax+1)||
       in.ub_west_east_mps.size()!=std::size_t(in.ny)*2*kmax||
       in.vb_south_north_mps.size()!=std::size_t(in.nx)*2*kmax)
        throw std::invalid_argument("DIVCEL input shape mismatch");
    const auto check=[](const std::vector<float>& a) {
        for(float x:a)if(!std::isfinite(x))
            throw std::invalid_argument("DIVCEL missing/nonfinite velocity");
    };
    check(in.u_mps);check(in.v_mps);check(in.w_mps);
    check(in.ub_west_east_mps);check(in.vb_south_north_mps);
    for(float z:in.dz_m)if(!std::isfinite(z)||z<=0.f)
        throw std::invalid_argument("DIVCEL invalid dz");
    DivcelOutput out{std::vector<float>(n*kmax,0.f),
                      std::vector<float>(kmax,0.f)};
    // Original HTOP=1.0 and accumulates DIVMAX initialized -1e9 per layer.
    const float dxi=1.f/(2.f*in.dx_m),dyi=1.f/(2.f*in.dy_m);
    for(int k=0;k<in.nz;++k) {
        const float dzi=1.f/in.dz_m[std::size_t(k)];
        float divmax=-1.e9f;
        for(int j=0;j<in.ny;++j)for(int i=0;i<in.nx;++i) {
            const auto p=std::size_t(j)*std::size_t(in.nx)+std::size_t(i);
            const auto t=std::size_t(k)*n+p;
            const auto east=std::size_t(k)*(2*std::size_t(in.ny))+
                            std::size_t(in.ny)+std::size_t(j);
            const auto west=std::size_t(k)*(2*std::size_t(in.ny))+std::size_t(j);
            const auto north=std::size_t(k)*(2*std::size_t(in.nx))+
                             std::size_t(in.nx)+std::size_t(i);
            const auto south=std::size_t(k)*(2*std::size_t(in.nx))+std::size_t(i);
            const float uph=(i==in.nx-1)?in.ub_west_east_mps[east]:
                             in.u_mps[t+1];
            const float umh=(i==0)?in.ub_west_east_mps[west]:
                             in.u_mps[t-1];
            const float vph=(j==in.ny-1)?in.vb_south_north_mps[north]:
                             in.v_mps[t+std::size_t(in.nx)];
            const float vmh=(j==0)?in.vb_south_north_mps[south]:
                             in.v_mps[t-std::size_t(in.nx)];
            const float wph=in.w_mps[t+n],wmh=in.w_mps[t];
            const float dudx=(uph-umh)*dxi;
            const float dvdy=(vph-vmh)*dyi;
            const float dwdz=(wph-wmh)*dzi;
            const float div=(dudx+dvdy)+dwdz;
            if(!std::isfinite(div))
                throw std::invalid_argument("DIVCEL divergence overflow");
            out.divergence_per_s[t]=div;
            divmax=std::max(std::abs(div),divmax);
        }
        out.max_abs_per_s[std::size_t(k)]=divmax;
    }
    return out;
}
} // namespace cteas::calmet::p6
