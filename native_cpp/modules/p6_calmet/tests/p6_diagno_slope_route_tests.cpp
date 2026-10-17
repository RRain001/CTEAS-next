// P6D9A selected DIAGNO ISLOPE=1 upstream route: original SLOPE L5722-L5723
// plus the L5727-L5732 additive loop, applied after FRADJ and before the
// L5748 boundary snapshot and the L6055/L6059 INTER2 calls. Contract level
// only; the numeric parity against the unchanged original Fortran is the
// chained source comparison.
#include "cteas/p6/diagno_d9a_selected_bridge.hpp"
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
static void fill_terrain(DiagnoD9TerrainBoundary& t,float relief){
    t.isurft=-1;
    t.tinf_k=285.f;
    t.critfn=1.f;
    t.terrain_m.assign(2500,120.f);
    if(relief>0.f)
        for(int j=0;j<50;++j)for(int i=0;i<50;++i)
            t.terrain_m[std::size_t(j)*50+std::size_t(i)]=
                relief+14.f*float(i)+3.f*float(j);
    t.maximum_terrain_m=t.terrain_m;
    for(float& value:t.maximum_terrain_m)value+=950.f;
    t.lapse_rate_k_per_m.assign(2500,0.006f);
    t.surface_temperature_k.assign(2500,285.f);
}
static void fill_slope(DiagnoD9SlopeBoundary& s,bool water,bool heat){
    s.water_first=50;
    s.water_last=55;
    s.minimum_terrain_m.assign(2500,0.f);
    s.distance_to_max_terrain_m.assign(2500,0.f);
    s.distance_to_min_terrain_m.assign(2500,0.f);
    s.sensible_heat_w_m2.assign(2500,0.f);
    s.landuse.assign(2500,10);
    for(std::size_t n=0;n<2500;++n){
        s.minimum_terrain_m[n]=-530.f;
        s.distance_to_max_terrain_m[n]=900.f+12.f*float(n%50);
        s.distance_to_min_terrain_m[n]=1100.f+10.f*float(n/50);
    }
    if(heat)
        for(int j=0;j<50;++j)for(int i=0;i<50;++i)
            s.sensible_heat_w_m2[std::size_t(j)*50+std::size_t(i)]=
                i<25?160.f:-90.f;  // daytime upslope and nighttime downhill
    if(water)
        for(int j=0;j<50;++j)
            if(j%6==0)
                for(int i=0;i<50;++i)
                    s.landuse[std::size_t(j)*50+std::size_t(i)]=52;
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
    fill_terrain(input.terrain,120.f);
    const auto identity=integrate_diagno_d9_selected(input);
    // Original SLOPE needs relief, an established sensible heat flux and
    // enough vertical extent; a zero heat flux must be a strict no-op
    // because the Mahrt velocity scales with |QH|.
    input.slope_flow=true;
    fill_slope(input.slope,false,false);
    const auto no_heat=integrate_diagno_d9_selected(input);
    require(no_heat.prepared_ug==identity.prepared_ug&&
            no_heat.prepared_vg==identity.prepared_vg,
            "D9A original SLOPE must not adjust without a heat flux");
    fill_slope(input.slope,false,true);
    const auto slope=integrate_diagno_d9_selected(input);
    require(slope.prepared_ug!=identity.prepared_ug||
            slope.prepared_vg!=identity.prepared_vg,
            "D9A original SLOPE must add a slope-flow component");
    // SLOPE only adds a slope-flow vector; it must never shrink or rescale
    // the underlying step-one wind beyond that added magnitude.
    float largest_added=0.f;
    for(std::size_t n=0;n<22500;++n){
        const float du=slope.prepared_ug[n]-identity.prepared_ug[n];
        const float dv=slope.prepared_vg[n]-identity.prepared_vg[n];
        largest_added=std::max(largest_added,std::hypot(du,dv));
    }
    require(largest_added>1e-4f,
            "D9A SLOPE slope-flow magnitude must be physically non-zero");
    require(largest_added<10.f,
            "D9A SLOPE slope-flow magnitude must stay physically bounded");
    // Water cells are excluded from the original Mahrt parameterisation.
    fill_slope(input.slope,true,true);
    const auto with_water=integrate_diagno_d9_selected(input);
    int excluded=0;
    for(int j=0;j<50;++j){
        if(j%6!=0)continue;
        for(int i=0;i<50;++i){
            const auto n=std::size_t(j)*50+std::size_t(i);
            for(std::size_t k=0;k<9;++k){
                const auto cell=k*2500+n;
                require(with_water.prepared_ug[cell]==identity.prepared_ug[cell]&&
                        with_water.prepared_vg[cell]==identity.prepared_vg[cell],
                        "D9A original SLOPE must skip water landuse cells");
                ++excluded;
            }
        }
    }
    require(excluded>0,"D9A SLOPE water class must be exercised");
    // Original FRADJ runs before SLOPE; enabling both must differ from each
    // alone and keep the raw WIND1 first guess isolated.
    fill_slope(input.slope,false,true);
    input.froude_adjustment=true;
    const auto both=integrate_diagno_d9_selected(input);
    require(both.raw_first_guess.ug_mps==identity.raw_first_guess.ug_mps,
            "D9A upstream terrain stages must not modify the raw first guess");
    require(both.prepared_ug!=slope.prepared_ug,
            "D9A FRADJ must compose with the SLOPE stage");
    input.froude_adjustment=false;
    // Fail-closed contract surface.
    auto short_hmin=input;
    short_hmin.slope.minimum_terrain_m.pop_back();
    rejected([&]{(void)integrate_diagno_d9_selected(short_hmin);},
             "D9A accepted a truncated SLOPE valley-bottom field");
    auto short_distance=input;
    short_distance.slope.distance_to_max_terrain_m.clear();
    rejected([&]{(void)integrate_diagno_d9_selected(short_distance);},
             "D9A accepted a missing SLOPE birdwise distance field");
    auto short_heat=input;
    short_heat.slope.sensible_heat_w_m2.assign(2499,0.f);
    rejected([&]{(void)integrate_diagno_d9_selected(short_heat);},
             "D9A accepted a truncated SLOPE sensible heat field");
    auto short_landuse=input;
    short_landuse.slope.landuse.assign(100,10);
    rejected([&]{(void)integrate_diagno_d9_selected(short_landuse);},
             "D9A accepted a truncated SLOPE landuse field");
    auto bad_water=input;
    bad_water.slope.water_first=60;
    bad_water.slope.water_last=50;
    rejected([&]{(void)integrate_diagno_d9_selected(bad_water);},
             "D9A accepted an inverted SLOPE water class range");
    auto nonfinite=input;
    nonfinite.slope.sensible_heat_w_m2[0]=std::nanf("");
    rejected([&]{(void)integrate_diagno_d9_selected(nonfinite);},
             "D9A accepted a nonfinite SLOPE sensible heat flux");
    auto double_corrected=input;
    double_corrected.upstream_mode=DiagnoD9UpstreamMode::ExternallyCompletedUpstreamPhysics;
    double_corrected.corrected_first_guess_u_mps.assign(22500,7.f);
    double_corrected.corrected_first_guess_v_mps.assign(22500,-3.f);
    rejected([&]{(void)integrate_diagno_d9_selected(double_corrected);},
             "D9A applied SLOPE on top of an external corrected field");
    std::cout<<"PASS_P6D9A_SELECTED_ISLOPE1_UPSTREAM_ROUTE_SOFTWARE_ONLY\n";
    return 0;
 }catch(const std::exception& e){
    std::cerr<<e.what()<<'\n';return 1;
 }
}
