#pragma once
// Selected CALMET 6.5.0 DIAGNO IOBR=1 tail, original calmet.for L6153-L6159
// (O'Brien 1970 vertical-velocity error adjustment, W error proportional to
// height) and L6180 (IF (IOBR .EQ. 1) CALL MINIM(U,V,W,UB,VB,DIV,NITER,DIVLIM)).
// Original CELLZB(K)=ZFACE(K) (calmet.for L5151/L5157); MINIM holds W fixed
// and only relaxes U/V in place while refreshing WINDBC boundaries.
// This is NOT the upstream topology/heat/Froude/slope DIAGNO stages and no
// lake-breeze or ADJUST branch is implemented.
#include "cteas/p6/diagno_segment.hpp"
#include "cteas/p6/minim.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>
namespace cteas::calmet::p6 {
struct DiagnoObrienControls {
    // Original CELLZB(1)=ZFACE(1), i.e. the lowest cell face height (m).
    float cellzb_origin_m=0.f;
    int minim_iterations=0;
    float minim_divergence_limit_per_s=0.f;
};
inline FinalWindSegment original_diagno_obrien_minim(
    FinalWindSegment segment,const std::vector<float>& dz_m,
    float dx_m,float dy_m,const DiagnoObrienControls& controls) {
    const std::size_t nz=dz_m.size();
    if(nz<1||nz>12)
        throw std::invalid_argument("IOBR tail supports at most twelve layers");
    if(!(std::isfinite(controls.cellzb_origin_m)&&controls.cellzb_origin_m>=0.f))
        throw std::invalid_argument("IOBR tail invalid original CELLZB origin");
    for(float z:dz_m)
        if(!(std::isfinite(z)&&z>0.f))
            throw std::invalid_argument("IOBR tail invalid DZ");
    const std::size_t count=segment.u_mps.size();
    if(count==0||count%nz!=0||segment.v_mps.size()!=count||
       segment.divergence_per_s.size()!=count)
        throw std::invalid_argument("IOBR tail U/V/DIV shape mismatch");
    const std::size_t plane=count/nz;
    if(segment.w_face_mps.size()!=plane*(nz+1))
        throw std::invalid_argument("IOBR tail W face shape mismatch");
    if(segment.ub_west_east_mps.size()%(2*nz)!=0||
       segment.vb_south_north_mps.size()%(2*nz)!=0)
        throw std::invalid_argument("IOBR tail boundary shape mismatch");
    const std::size_t ny=segment.ub_west_east_mps.size()/(2*nz);
    const std::size_t nx=segment.vb_south_north_mps.size()/(2*nz);
    if(nx<2||ny<2||nx*ny!=plane)
        throw std::invalid_argument("IOBR tail boundary grid mismatch");

    // Original L6153-L6159: every face above layer K loses the same fraction
    // CELLZB(K+1)/CELLZB(NZP1) of the *unadjusted* top-face W, so the top face
    // becomes exactly zero.
    std::vector<float> cellzb(nz+1);
    cellzb[0]=controls.cellzb_origin_m;
    for(std::size_t k=0;k<nz;++k)cellzb[k+1]=cellzb[k]+dz_m[k];
    const float top_face=cellzb[nz];
    for(std::size_t p=0;p<plane;++p) {
        const float wtop=segment.w_face_mps[nz*plane+p];
        for(std::size_t k=0;k<nz;++k)
            segment.w_face_mps[(k+1)*plane+p]-=
                cellzb[k+1]/top_face*wtop;
    }

    // Original L6180: MINIM relaxes U/V at fixed W, one level at a time.
    DivcelInput minim_in;
    minim_in.nx=int(nx);minim_in.ny=int(ny);minim_in.nz=int(nz);
    minim_in.dx_m=dx_m;minim_in.dy_m=dy_m;minim_in.dz_m=dz_m;
    minim_in.u_mps=segment.u_mps;minim_in.v_mps=segment.v_mps;
    minim_in.w_mps=segment.w_face_mps;
    minim_in.ub_west_east_mps=segment.ub_west_east_mps;
    minim_in.vb_south_north_mps=segment.vb_south_north_mps;
    auto minimized=original_minim_scoped(
        std::move(minim_in),controls.minim_iterations,
        controls.minim_divergence_limit_per_s);
    segment.u_mps=std::move(minimized.wind.u_mps);
    segment.v_mps=std::move(minimized.wind.v_mps);
    segment.divergence_per_s=std::move(minimized.divergence_per_s);
    segment.ub_west_east_mps=std::move(minimized.wind.ub_west_east_mps);
    segment.vb_south_north_mps=std::move(minimized.wind.vb_south_north_mps);
    return segment;
}
} // namespace cteas::calmet::p6
