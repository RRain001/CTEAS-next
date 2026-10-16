#include "cteas/p6/diagno_d9a_selected_bridge.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>

using namespace cteas::calmet::p6;
static void require(bool yes,const char* reason){
    if(!yes)throw std::runtime_error(reason);
}
template<class F> static void rejected(F&& f,const char* message) {
    bool caught=false;
    try{f();}catch(const std::invalid_argument&){caught=true;}
    require(caught,message);
}
static DiagnoD9SelectedInput make_input(){
    DiagnoD9SelectedInput in;
    auto& s=in.stations;
    s.surface_station_id=58321;s.upper_station_id=58424;
    s.surface_observed_u_mps=3.f;s.surface_observed_v_mps=4.f;
    for(int k=0;k<9;k++){
        s.surface_neutral_profile[static_cast<std::size_t>(k)]={3.f+0.02f*k,4.f};
        s.upper_observed_profile[static_cast<std::size_t>(k)]={2.f,5.f+0.1f*k};
    }
    in.first_guess.surface_x_relative_m=900.f;
    in.first_guess.surface_y_relative_m=1600.f;
    in.first_guess.upper_x_relative_m=4100.f;
    in.first_guess.upper_y_relative_m=3500.f;
    in.first_guess.vertical_bias={0.f,0.1f,0.2f,0.3f,0.f,-0.1f,-0.2f,0.f,0.f};
    in.smoothing_passes={0,1,2,0,1,2,0,1,0};
    in.layer_thickness_m={20.f,20.f,40.f,80.f,160.f,320.f,560.f,800.f,1000.f};
    for(auto *p:{&in.inter2_u,&in.inter2_v}){
        p->nx=50;p->ny=50;p->nz=9;p->nstations=2;
        p->dx_m=100.f;p->dy_m=100.f;
        p->rmin_km=0.05f;p->rmax1_km=12.f;
        p->rmax2_km=12.f;p->rmax3_km=12.f;
        p->r1_km=0.6f;p->r2_km=1.5f;
        p->edit=999999.f;p->editl=999998.f;
        p->nintrp_per_layer.assign(9,2);
        p->station_x_km={0.9f,4.1f};
        p->station_y_km={1.6f,3.5f};
        p->landuse.assign(2500,10);
        p->observation_weight.assign(22500,0.6f);
        p->station_component_mps.resize(18);
    }
    for(std::size_t k=0;k<9;k++) {
        in.inter2_u.station_component_mps[k*2]=1.5f+0.13f*float(k);
        in.inter2_u.station_component_mps[k*2+1]=2.4f+0.11f*float(k);
        in.inter2_v.station_component_mps[k*2]=-2.f+0.07f*float(k);
        in.inter2_v.station_component_mps[k*2+1]=1.8f+0.05f*float(k);
    }
    in.upstream_mode=DiagnoD9UpstreamMode::SyntheticIdentityForSourceAudit;
    return in;
}
int main(){
 try{
    auto input=make_input();
    auto output=integrate_diagno_d9_selected(input);
    require(output.raw_first_guess.ug_mps.size()==22500 &&
            output.blended_u.size()==22500 &&
            output.blended_v.size()==22500 &&
            output.final_fields.u_mps.size()==22500 &&
            output.final_fields.divergence_per_s.size()==22500 &&
            output.final_fields.w_face_mps.size()==25000,
            "D9A full 50x50x9 and ten-face field shapes");
    require(output.final_fields.ub_west_east_mps.size()==900 &&
            output.final_fields.vb_south_north_mps.size()==900,
            "D9A per-level original WINDBC shape");
    require(output.prepared_ug==output.raw_first_guess.ug_mps,
            "D9A synthetic route must be exact identity");
    require(output.blended_u!=output.prepared_ug,
            "D9A INTER2 U must actually blend observations");
    require(output.blended_v!=output.prepared_vg,
            "D9A INTER2 V must actually blend observations");
    bool nonzero_w=false;
    for(float w:output.final_fields.w_face_mps){
        require(std::isfinite(w),"D9A W nonfinite");
        nonzero_w|=std::abs(w)>1e-6f;
    }
    require(nonzero_w,"D9A W must reflect horizontal divergence");
    input.upstream_mode=DiagnoD9UpstreamMode::Missing;
    rejected([&]{(void)integrate_diagno_d9_selected(input);},
             "D9A missing P6E/terrain/slope intermediate silently accepted");
    input.upstream_mode=DiagnoD9UpstreamMode::SyntheticIdentityForSourceAudit;
    input.corrected_first_guess_u_mps.assign(22500,7.f);
    rejected([&]{(void)integrate_diagno_d9_selected(input);},
             "D9A synthetic identity cannot smuggle corrected physics");
    input.corrected_first_guess_v_mps.assign(22500,-3.f);
    input.upstream_mode=DiagnoD9UpstreamMode::ExternallyCompletedUpstreamPhysics;
    output=integrate_diagno_d9_selected(input);
    require(output.prepared_ug[0]==7.f&&output.prepared_vg[0]==-3.f,
            "D9A external post-physics winds must be used");
    input.corrected_first_guess_u_mps[0]=std::nanf("");
    rejected([&]{(void)integrate_diagno_d9_selected(input);},
             "D9A nonfinite upstream field accepted");
    input.corrected_first_guess_u_mps[0]=7.f;
    input.inter2_v.station_x_km[0]=8.f;
    rejected([&]{(void)integrate_diagno_d9_selected(input);},
             "D9A mismatched WIND1/INTER2 station location accepted");
    input.inter2_v.station_x_km[0]=0.9f;
    input.lake_breeze=true;
    rejected([&]{(void)integrate_diagno_d9_selected(input);},
             "D9A unsupported lake breeze accepted");
    input.lake_breeze=false;
    // Original IOBR=1 tail: O'Brien L6153-L6159 then MINIM L6180, reached
    // only through the explicit optional flag.
    input.upstream_mode=DiagnoD9UpstreamMode::SyntheticIdentityForSourceAudit;
    input.corrected_first_guess_u_mps.clear();
    input.corrected_first_guess_v_mps.clear();
    const auto baseline=integrate_diagno_d9_selected(input);
    // The isolated original Fortran tail fixture starts after L6100 and
    // supplies its own UB/VB (HTFAC=0 surrogate). The real Hefei GEO HTFAC=1
    // instead refreshes WINDBC(U,V) from INTER2 before the tail.
    input.htfac=1.f;
    const auto second_windbc=integrate_diagno_d9_selected(input);
    require(second_windbc.final_fields.w_face_mps!=baseline.final_fields.w_face_mps,
            "HTFAC=1 second WINDBC must change the synthetic tail's W");
    input.htfac=0.f;
    require(integrate_diagno_d9_selected(input).final_fields.w_face_mps==
                baseline.final_fields.w_face_mps,
            "HTFAC=0 source-isolated legacy tail must be deterministic");
    input.htfac=std::nanf("");
    rejected([&]{(void)integrate_diagno_d9_selected(input);},
             "D9A nonfinite HTFAC accepted");
    input.htfac=0.f;
    bool baseline_top_nonzero=false;
    for(std::size_t p=0;p<2500;++p)
        baseline_top_nonzero|=std::abs(
            baseline.final_fields.w_face_mps[9*2500+p])>1e-9f;
    require(baseline_top_nonzero,
            "D9A IOBR=0 baseline needs a nonzero top face");
    input.obrien_adjustment=true;
    input.cellzb_origin_m=0.f;
    input.minim_iterations=3;
    input.minim_divergence_limit_per_s=0.f;
    const auto obrien=integrate_diagno_d9_selected(input);
    for(std::size_t p=0;p<2500;++p)
        require(obrien.final_fields.w_face_mps[9*2500+p]==0.f,
                "D9A original IOBR=1 must cancel the top W face exactly");
    require(obrien.final_fields.w_face_mps!=baseline.final_fields.w_face_mps,
            "D9A IOBR=1 must adjust W");
    std::size_t nonzero_divergence=0,relaxed=0;
    for(std::size_t p=0;p<22500;++p){
        if(baseline.final_fields.divergence_per_s[p]!=0.f)++nonzero_divergence;
        if(obrien.final_fields.u_mps[p]!=baseline.final_fields.u_mps[p]||
           obrien.final_fields.v_mps[p]!=baseline.final_fields.v_mps[p])
            ++relaxed;
    }
    require(nonzero_divergence>0,
            "D9A IOBR=1 baseline needs a divergent field for MINIM");
    require(relaxed>0,"D9A original MINIM must relax U/V");
    input.minim_iterations=-1;
    rejected([&]{(void)integrate_diagno_d9_selected(input);},
             "D9A invalid NITER silently accepted");
    input.minim_iterations=3;
    input.cellzb_origin_m=-1.f;
    rejected([&]{(void)integrate_diagno_d9_selected(input);},
             "D9A negative original CELLZB origin silently accepted");
    input.cellzb_origin_m=0.f;
    input.obrien_adjustment=false;
    input.minim_iterations=0;
    std::cout<<"PASS_P6D9A_SELECTED_WIND1_INTER2_FINAL_SEGMENT_SOFTWARE_ONLY\n";
    return 0;
 }catch(const std::exception& e){
    std::cerr<<e.what()<<'\n';return 1;
 }
}