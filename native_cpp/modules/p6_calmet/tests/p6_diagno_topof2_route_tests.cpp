// P6D9A selected DIAGNO IKINE=1 pre-blend kinematic route: original W zeroing
// L5615-L5616, TOPOF2 L5621-L5622 and the pre-blend MINIM call L5628-L5629
// with the L5598-L5600 WINDBC snapshot. Completeness branch only: the frozen
// real deck has IKINE=0 so this route is not the real-case path. Numerical
// parity against the unchanged original Fortran is the chained comparison.
#include "cteas/p6/diagno_d9a_selected_bridge.hpp"
#include "cteas/p6/topof2.hpp"
#include <algorithm>
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
static void fill_terrain(DiagnoD9TerrainBoundary& t){
    t.isurft=-1;
    t.tinf_k=285.f;
    t.critfn=1.f;
    t.terrain_m.assign(2500,100.f);
    for(int j=0;j<50;++j)for(int i=0;i<50;++i)
        t.terrain_m[std::size_t(j)*50+std::size_t(i)]=
            100.f+160.f*std::exp(-float((i-21)*(i-21)+(j-24)*(j-24))/90.f);
    t.maximum_terrain_m=t.terrain_m;
    for(float& value:t.maximum_terrain_m)value+=400.f;
    t.lapse_rate_k_per_m.assign(2500,0.006f);
    t.surface_temperature_k.assign(2500,285.f);
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
    fill_terrain(input.terrain);
    const auto identity=integrate_diagno_d9_selected(input);
    require(identity.kinematic_w_face_mps.empty(),
            "D9A must not emit a kinematic W field when IKINE is disabled");
    // Original IKINE=1 route.
    input.kinematic_route=true;
    input.alpha=0.f;
    input.kinematic_iterations=0;
    input.kinematic_divergence_limit_per_s=0.f;
    const auto topof2_only=integrate_diagno_d9_selected(input);
    require(topof2_only.kinematic_w_face_mps.size()==25000,
            "D9A original TOPOF2 must emit ten faces per column");
    bool nonzero=false;
    for(float value:topof2_only.kinematic_w_face_mps){
        require(std::isfinite(value),"D9A TOPOF2 W must be finite");
        nonzero|=std::abs(value)>1e-9f;
    }
    require(nonzero,"D9A TOPOF2 W must reflect terrain relief and flow");
    // ALPHA scales the non-terrain-following part of the decay profile; with
    // a flat field ALPHA is still inert, and nonzero ALPHA must change W.
    auto scaled=input;
    scaled.alpha=0.1f;
    const auto with_alpha=integrate_diagno_d9_selected(scaled);
    require(with_alpha.kinematic_w_face_mps!=topof2_only.kinematic_w_face_mps,
            "D9A original ALPHA must scale the TOPOF2 profile");
    // Original MINIM then relaxes U/V at fixed W.
    auto relaxed=input;
    relaxed.alpha=0.1f;
    relaxed.kinematic_iterations=50;
    relaxed.kinematic_divergence_limit_per_s=5.e-6f;
    const auto minim=integrate_diagno_d9_selected(relaxed);
    require(minim.prepared_ug!=identity.prepared_ug||
            minim.prepared_vg!=identity.prepared_vg,
            "D9A pre-blend MINIM must relax the step-one winds");
    require(minim.kinematic_w_face_mps==with_alpha.kinematic_w_face_mps,
            "D9A pre-blend MINIM must hold the TOPOF2 W field fixed");
    // Flat terrain removes the topographic forcing entirely.
    auto flat=input;
    flat.terrain.terrain_m.assign(2500,120.f);
    flat.terrain.maximum_terrain_m.assign(2500,520.f);
    const auto flat_result=integrate_diagno_d9_selected(flat);
    float largest=0.f;
    for(float value:flat_result.kinematic_w_face_mps)
        largest=std::max(largest,std::abs(value));
    require(largest<=1e-4f,"D9A TOPOF2 must vanish over flat terrain");
    // Isolated kernel contract surface.
    Topof2Input kernel;
    kernel.nx=50;kernel.ny=50;kernel.nz=9;
    kernel.dx_m=100.f;kernel.dy_m=100.f;
    kernel.isurft=-1;kernel.tinf_k=285.f;kernel.alpha=0.1f;
    kernel.dz_m=input.layer_thickness_m;
    kernel.cellzb_m={0.f,20.f,40.f,80.f,160.f,320.f,640.f,1200.f,2000.f,3000.f};
    kernel.terrain_m=flat.terrain.terrain_m;
    kernel.lapse_rate_k_per_m.assign(2500,0.006f);
    kernel.surface_temperature_k.assign(2500,285.f);
    const std::vector<float> winds(22500,2.f);
    const auto flat_w=original_topof2_w(kernel,winds,winds);
    require(flat_w.size()==25000,"TOPOF2 W face shape");
    for(float value:flat_w)
        require(std::abs(value)<=1e-5f,
                "TOPOF2 must produce no vertical velocity over flat terrain");
    auto short_dz=kernel;
    short_dz.dz_m.pop_back();
    rejected([&]{(void)original_topof2_w(short_dz,winds,winds);},
             "TOPOF2 accepted a truncated DZ profile");
    auto bad_alpha=kernel;
    bad_alpha.alpha=std::nanf("");
    rejected([&]{(void)original_topof2_w(bad_alpha,winds,winds);},
             "TOPOF2 accepted a nonfinite ALPHA");
    auto bad_temp=kernel;
    bad_temp.surface_temperature_k[0]=0.f;
    rejected([&]{(void)original_topof2_w(bad_temp,winds,winds);},
             "TOPOF2 accepted a nonpositive surface temperature");
    auto short_winds=kernel;
    const std::vector<float> truncated(100,1.f);
    rejected([&]{(void)original_topof2_w(short_winds,truncated,winds);},
             "TOPOF2 accepted a truncated U field");
    // Bridge fail-closed surface.
    auto missing=input;
    missing.terrain.lapse_rate_k_per_m.clear();
    rejected([&]{(void)integrate_diagno_d9_selected(missing);},
             "D9A accepted a missing TOPOF2 lapse rate field");
    auto bad_coefficient=input;
    bad_coefficient.alpha=std::nanf("");
    rejected([&]{(void)integrate_diagno_d9_selected(bad_coefficient);},
             "D9A accepted a nonfinite ALPHA");
    auto external=input;
    external.upstream_mode=DiagnoD9UpstreamMode::ExternallyCompletedUpstreamPhysics;
    external.corrected_first_guess_u_mps.assign(22500,7.f);
    external.corrected_first_guess_v_mps.assign(22500,-3.f);
    rejected([&]{(void)integrate_diagno_d9_selected(external);},
             "D9A applied the kinematic route on an external corrected field");
    std::cout<<"PASS_P6D9A_SELECTED_IKINE1_TOPOF2_PREBLEND_ROUTE_SOFTWARE_ONLY\n";
    return 0;
 }catch(const std::exception& e){
    std::cerr<<e.what()<<'\n';return 1;
 }
}
