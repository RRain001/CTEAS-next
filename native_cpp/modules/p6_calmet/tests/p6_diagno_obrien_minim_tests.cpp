// P6D9A selected DIAGNO IOBR=1 tail: original L6153-L6159 O'Brien W
// adjustment plus L6180 MINIM, contract-level only. Numerical parity against
// the unchanged original Fortran is the separate chained source comparison.
// DZ and CELLZB values are exact binary fractions so the documented
// CELLZB(K+1)/CELLZB(NZP1) share is checked without rounding slack.
#include "cteas/p6/diagno_obrien_minim.hpp"
#include <cmath>
#include <cstddef>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace cteas::calmet::p6;
static void require(bool yes,const char* reason){
    if(!yes)throw std::runtime_error(reason);
}
template<class F> static void rejected(F&& f,const char* message) {
    bool caught=false;
    try{f();}catch(const std::invalid_argument&){caught=true;}
    require(caught,message);
}
static FinalWindSegment make_segment(){
    constexpr std::size_t nx=4,ny=3,nz=2;
    const std::size_t plane=nx*ny;
    FinalWindSegment segment;
    segment.u_mps.assign(plane*nz,0.f);
    segment.v_mps.assign(plane*nz,0.f);
    segment.divergence_per_s.assign(plane*nz,0.f);
    segment.w_face_mps.assign(plane*(nz+1),0.f);
    segment.ub_west_east_mps.assign(2*ny*nz,0.f);
    segment.vb_south_north_mps.assign(2*nx*nz,0.f);
    for(std::size_t k=0;k<nz;++k)for(std::size_t j=0;j<ny;++j)
        for(std::size_t i=0;i<nx;++i){
            const std::size_t p=k*plane+j*nx+i;
            segment.u_mps[p]=1.5f+0.25f*float(i)+0.5f*float(k);
            segment.v_mps[p]=-0.75f+0.125f*float(j)-0.25f*float(k);
        }
    // Uniform top-face W makes the O'Brien ratio check exact by hand.
    for(std::size_t p=0;p<plane*(nz+1);++p)
        segment.w_face_mps[p]=std::size_t(p/plane)==nz?3.f:0.f;
    return segment;
}
int main(){
 try{
    const std::vector<float> dz={128.f,384.f};
    const FinalWindSegment base=make_segment();
    // L6153-L6159 with CELLZB(1)=0 -> CELLZB={0,128,512}: face 1 keeps an
    // exact 128/512=1/4 share and the top face loses 512/512, i.e. becomes
    // exactly zero.
    DiagnoObrienControls idle;
    idle.cellzb_origin_m=0.f;
    idle.minim_iterations=0;
    idle.minim_divergence_limit_per_s=0.f;
    const auto adjusted=original_diagno_obrien_minim(base,dz,100.f,100.f,idle);
    require(adjusted.w_face_mps.size()==36,"IOBR tail W face shape");
    for(std::size_t p=0;p<12;++p){
        require(adjusted.w_face_mps[p]==0.f,
                "O'Brien must not touch the ground face");
        require(adjusted.w_face_mps[12+p]==-0.75f,
                "O'Brien level one share must be CELLZB(2)/CELLZB(NZP1)");
        require(adjusted.w_face_mps[24+p]==0.f,
                "O'Brien original top face must vanish exactly");
    }
    require(adjusted.u_mps==base.u_mps&&adjusted.v_mps==base.v_mps,
            "MINIM with NITER=0 must not relax U/V");
    // Original CELLZB(1)=ZFACE(1) is not always zero; a nonzero origin must
    // change the share without altering the top-face cancellation.
    auto lifted_controls=idle;
    lifted_controls.cellzb_origin_m=512.f;
    const auto lifted=original_diagno_obrien_minim(base,dz,100.f,100.f,
                                                   lifted_controls);
    for(std::size_t p=0;p<12;++p){
        require(lifted.w_face_mps[12+p]==-1.875f,
                "O'Brien nonzero ZFACE(1) share must be CELLZB(2)/CELLZB(NZP1)");
        require(lifted.w_face_mps[24+p]==0.f,
                "O'Brien top face must vanish for any ZFACE(1)");
    }
    // Divergence handed to MINIM must be the original DIVCEL of the
    // *adjusted* W, not the pre-adjustment state.
    DivcelInput probe;
    probe.nx=4;probe.ny=3;probe.nz=2;probe.dx_m=100.f;probe.dy_m=100.f;
    probe.dz_m=dz;
    probe.u_mps=adjusted.u_mps;probe.v_mps=adjusted.v_mps;
    probe.w_mps=adjusted.w_face_mps;
    probe.ub_west_east_mps=adjusted.ub_west_east_mps;
    probe.vb_south_north_mps=adjusted.vb_south_north_mps;
    const auto expected=original_divcel_scoped(probe);
    require(adjusted.divergence_per_s==expected.divergence_per_s,
            "IOBR tail must report original DIVCEL of the adjusted W");
    require(adjusted.ub_west_east_mps==base.ub_west_east_mps&&
            adjusted.vb_south_north_mps==base.vb_south_north_mps,
            "MINIM with NITER=0 must not move WINDBC boundaries");
    // Original MINIM skips a level whose DIVMAX already satisfies DIVLIM.
    auto skip_controls=idle;
    skip_controls.minim_iterations=4;
    skip_controls.minim_divergence_limit_per_s=1.e9f;
    const auto skipped=original_diagno_obrien_minim(base,dz,100.f,100.f,
                                                    skip_controls);
    require(skipped.u_mps==adjusted.u_mps&&skipped.v_mps==adjusted.v_mps,
            "original MINIM must skip levels with DIVMAX<=DIVLIM");
    // An enforced NITER>0 relaxation with DIVLIM=0 must act on the field.
    auto active_controls=idle;
    active_controls.minim_iterations=3;
    const auto active=original_diagno_obrien_minim(base,dz,100.f,100.f,
                                                   active_controls);
    require(active.u_mps!=adjusted.u_mps||active.v_mps!=adjusted.v_mps,
            "original MINIM must relax U/V when DIVMAX exceeds DIVLIM");
    require(active.w_face_mps==adjusted.w_face_mps,
            "original MINIM holds W fixed");
    // Fail-closed contract surface.
    rejected([&]{(void)original_diagno_obrien_minim(base,{128.f},100.f,100.f,idle);},
             "IOBR tail accepted a mismatched DZ length");
    auto dz_bad=dz;dz_bad[1]=0.f;
    rejected([&]{(void)original_diagno_obrien_minim(base,dz_bad,100.f,100.f,idle);},
             "IOBR tail accepted a nonpositive DZ");
    auto bad_origin=idle;bad_origin.cellzb_origin_m=-1.f;
    rejected([&]{(void)original_diagno_obrien_minim(base,dz,100.f,100.f,bad_origin);},
             "IOBR tail accepted a negative CELLZB origin");
    auto bad_iter=idle;bad_iter.minim_iterations=-1;
    rejected([&]{(void)original_diagno_obrien_minim(base,dz,100.f,100.f,bad_iter);},
             "IOBR tail accepted a negative NITER");
    auto bad_limit=idle;bad_limit.minim_divergence_limit_per_s=-0.5f;
    rejected([&]{(void)original_diagno_obrien_minim(base,dz,100.f,100.f,bad_limit);},
             "IOBR tail accepted a negative DIVLIM");
    auto short_w=base;short_w.w_face_mps.pop_back();
    rejected([&]{(void)original_diagno_obrien_minim(short_w,dz,100.f,100.f,idle);},
             "IOBR tail accepted a truncated W face array");
    auto bad_boundary=base;bad_boundary.vb_south_north_mps.pop_back();
    rejected([&]{(void)original_diagno_obrien_minim(bad_boundary,dz,100.f,100.f,idle);},
             "IOBR tail accepted a truncated WINDBC boundary");
    std::cout<<"PASS_P6D9A_SELECTED_OBRIEN_MINIM_IOBR1_TAIL_SOFTWARE_ONLY\n";
    return 0;
 }catch(const std::exception& e){
    std::cerr<<e.what()<<'\n';return 1;
 }
}
