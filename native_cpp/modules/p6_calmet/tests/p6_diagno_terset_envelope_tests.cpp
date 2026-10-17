// P6D9A in-chain TERSET envelope: original DIAGI L5228
// `if(i3dctw.eq.1)call terset(htopo,hmax,terrad)` with I3DCTW=IWFCOD, which the
// real deck sets to 1. The bridge must build HMAX/HMIN/DISTHMAX/DISTHMIN from
// the caller's terrain and TERRAD instead of accepting them as planes.
// Contract level only; the numeric parity against the unchanged original
// Fortran is the chained source comparison.
#include "cteas/p6/diagno_d9a_selected_bridge.hpp"
#include "cteas/p6/terrain_envelope.hpp"
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
static std::vector<float> terrain_fixture(){
    std::vector<float> terrain(2500);
    for(int j=0;j<50;++j)for(int i=0;i<50;++i)
        terrain[std::size_t(j)*50+std::size_t(i)]=
            100.f+160.f*std::exp(-float((i-21)*(i-21)+(j-24)*(j-24))/90.f);
    return terrain;
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
static void fill_supplied(DiagnoD9SelectedInput& in,
                          const TerrainEnvelope& envelope){
    in.terrain.maximum_terrain_m=envelope.maximum_m;
    in.slope.minimum_terrain_m=envelope.minimum_m;
    in.slope.distance_to_max_terrain_m=envelope.distance_to_maximum_m;
    in.slope.distance_to_min_terrain_m=envelope.distance_to_minimum_m;
}
int main(){
 try{
    auto input=make_input();
    input.terrain.terrain_m=terrain_fixture();
    input.terrain.isurft=-1;
    input.terrain.tinf_k=285.f;
    input.terrain.critfn=1.f;
    input.terrain.lapse_rate_k_per_m.assign(2500,0.006f);
    input.terrain.surface_temperature_k.assign(2500,285.f);
    input.slope.water_first=50;input.slope.water_last=55;
    input.slope.sensible_heat_w_m2.assign(2500,160.f);
    input.slope.landuse.assign(2500,10);
    input.froude_adjustment=true;
    input.slope_flow=true;
    // Caller-supplied envelope (previous contract).
    const auto envelope=terset(input.terrain.terrain_m,50,50,100.f,100.f,15.f);
    fill_supplied(input,envelope);
    const auto supplied=integrate_diagno_d9_selected(input);
    // In-chain envelope: same answer, without the caller planes.
    auto computed=input;
    fill_supplied(computed,envelope);
    computed.terrain.maximum_terrain_m.clear();
    computed.slope.minimum_terrain_m.clear();
    computed.slope.distance_to_max_terrain_m.clear();
    computed.slope.distance_to_min_terrain_m.clear();
    computed.terset_envelope=true;
    computed.terrad_km=15.f;
    const auto in_chain=integrate_diagno_d9_selected(computed);
    require(in_chain.prepared_ug==supplied.prepared_ug&&
            in_chain.prepared_vg==supplied.prepared_vg,
            "in-chain TERSET must reproduce the caller-supplied envelope exactly");
    require(in_chain.final_fields.u_mps==supplied.final_fields.u_mps&&
            in_chain.final_fields.v_mps==supplied.final_fields.v_mps&&
            in_chain.final_fields.w_face_mps==supplied.final_fields.w_face_mps,
            "in-chain TERSET must reproduce the final fields exactly");
    // The envelope really feeds the terrain stages: a short-radius envelope
    // changes both the Froude rotation and the slope flow.
    auto narrow=computed;
    narrow.terrad_km=1.f;
    const auto narrow_result=integrate_diagno_d9_selected(narrow);
    require(narrow_result.prepared_ug!=in_chain.prepared_ug,
            "a different TERRAD must reach the original terrain stages");
    // Single-provider rule and fail-closed surface.
    auto mixed=input;
    mixed.terset_envelope=true;
    mixed.terrad_km=15.f;
    rejected([&]{(void)integrate_diagno_d9_selected(mixed);},
             "D9 accepted a TERSET envelope together with supplied planes");
    auto no_terrain=computed;
    no_terrain.terrain.terrain_m.clear();
    rejected([&]{(void)integrate_diagno_d9_selected(no_terrain);},
             "D9 accepted TERSET without terrain");
    auto bad_radius=computed;
    bad_radius.terrad_km=-1.f;
    rejected([&]{(void)integrate_diagno_d9_selected(bad_radius);},
             "D9 accepted a negative TERRAD");
    auto nonfinite_radius=computed;
    nonfinite_radius.terrad_km=std::nanf("");
    rejected([&]{(void)integrate_diagno_d9_selected(nonfinite_radius);},
             "D9 accepted a nonfinite TERRAD");
    auto short_terrain=computed;
    short_terrain.terrain.terrain_m.pop_back();
    rejected([&]{(void)integrate_diagno_d9_selected(short_terrain);},
             "D9 accepted a truncated terrain grid for TERSET");
    // The kernel itself keeps CALMET's own TERRAD semantics.
    const auto wide=terset(input.terrain.terrain_m,50,50,100.f,100.f,15.f);
    require(wide.maximum_m.size()==2500&&wide.minimum_m.size()==2500,
            "TERSET envelope plane shapes");
    float relief=0.f;
    for(std::size_t n=0;n<2500;++n)
        relief=std::max(relief,wide.maximum_m[n]-wide.minimum_m[n]);
    require(relief>0.f,"TERSET envelope must span the terrain relief");
    std::cout<<"PASS_P6D9A_INCHAIN_TERSET_ENVELOPE_CONTRACT_SOFTWARE_ONLY\n";
    return 0;
 }catch(const std::exception& e){
    std::cerr<<e.what()<<'\n';return 1;
 }
}
