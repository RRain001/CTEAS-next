#pragma once
// P6C first source-faithful CALMET terrain influence kernel, original TERSET.
//
// Vendor: CALMET_v6.5.0_L150223/calmet.for TERSET lines 31805-31902.
// Includes Fortran single-precision NINT radius, within-TERRAD Euclidean
// window, strictly larger/smaller updates and distance-to-ultimate-extremum.
// Distances to highest/lowest *initially equal* cell default to zero:
// original leaves them unchanged until a strict inequality is found.
//
// This does NOT implement Froude adjustment FRADJ, slope flow or 3-D wind.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6 {
struct TerrainEnvelope {
    int nx=0,ny=0;
    std::vector<float> maximum_m;
    std::vector<float> minimum_m;
    std::vector<float> distance_to_maximum_m;
    std::vector<float> distance_to_minimum_m;
};
inline TerrainEnvelope terset(const std::vector<float>& heights_m,
                              int nx,int ny,float dx_m,float dy_m,float terrad_km) {
    if(nx<=0||ny<=0||nx>400||ny>400||heights_m.size()!=std::size_t(nx)*std::size_t(ny))
        throw std::invalid_argument("TERSET incorrect physical terrain grid");
    if(!std::isfinite(dx_m)||!std::isfinite(dy_m)||
       !(dx_m>0)||!(dy_m>0)||!std::isfinite(terrad_km)||terrad_km<0)
        throw std::invalid_argument("TERSET invalid grid spacing or TERRAD");
    for(float h:heights_m)
        if(!std::isfinite(h))throw std::invalid_argument("TERSET invalid terrain elevation");
    // A large radius above the domain diameter must not be rejected: CALMET
    // original will search all cells and use their extrema.
    const float dxk=dx_m*0.001f;
    const float dyk=dy_m*0.001f;
    const auto nint_nonnegative=[](float x,int max_cells) {
        if(!std::isfinite(x)||x<0)throw std::invalid_argument("invalid radius ratio");
        // Original IRANGE=NINT(TERRAD/DXK); clipping at the grid dimension
        // is equivalent for the *search bounds* because the grid is finite.
        if(x>static_cast<float>(max_cells))
            return max_cells;
        return static_cast<int>(std::floor(x+0.5f));
    };
    const int ir=nint_nonnegative(terrad_km/dxk,nx);
    const int jr=nint_nonnegative(terrad_km/dyk,ny);
    const auto index=[nx](int i,int j)->std::size_t{
        return std::size_t(j)*std::size_t(nx)+std::size_t(i);
    };
    TerrainEnvelope out;
    out.nx=nx;out.ny=ny;out.maximum_m=heights_m;out.minimum_m=heights_m;
    out.distance_to_maximum_m.assign(heights_m.size(),0.0f);
    out.distance_to_minimum_m.assign(heights_m.size(),0.0f);
    // Original TERSET performs two loops. Sorting, searching only axis
    // neighbors, or using a global bound changes its tie/float semantics.
    for(int j=0;j<ny;++j)for(int i=0;i<nx;++i) {
        const int l1=std::max(0,j-jr),l2=std::min(ny-1,j+jr);
        const int k1=std::max(0,i-ir),k2=std::min(nx-1,i+ir);
        const auto cell=index(i,j);
        for(int l=l1;l<=l2;++l)for(int k=k1;k<=k2;++k) {
            const float xdist=float(k-i)*dxk;
            const float ydist=float(l-j)*dyk;
            const float distance=std::sqrt(xdist*xdist+ydist*ydist);
            if(distance>terrad_km)continue;
            const float h=heights_m[index(k,l)];
            if(h>out.maximum_m[cell]){
                out.distance_to_maximum_m[cell]=distance*1000.0f;
                out.maximum_m[cell]=h;
            }
        }
    }
    for(int j=0;j<ny;++j)for(int i=0;i<nx;++i) {
        const int l1=std::max(0,j-jr),l2=std::min(ny-1,j+jr);
        const int k1=std::max(0,i-ir),k2=std::min(nx-1,i+ir);
        const auto cell=index(i,j);
        for(int l=l1;l<=l2;++l)for(int k=k1;k<=k2;++k) {
            const float xdist=float(k-i)*dxk;
            const float ydist=float(l-j)*dyk;
            const float distance=std::sqrt(xdist*xdist+ydist*ydist);
            if(distance>terrad_km)continue;
            const float h=heights_m[index(k,l)];
            if(h<out.minimum_m[cell]){
                out.distance_to_minimum_m[cell]=distance*1000.0f;
                out.minimum_m[cell]=h;
            }
        }
    }
    return out;
}
} // namespace cteas::calmet::p6
