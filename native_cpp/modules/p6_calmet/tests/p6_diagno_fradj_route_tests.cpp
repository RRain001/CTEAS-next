// P6D9A selected DIAGNO IFRADJ=1 upstream route: original FRADJ L5643-L5644
// applied to the step-one winds before the L5748 boundary snapshot and the
// L6055/L6059 INTER2 calls. Contract level only; the numeric parity against
// the unchanged original Fortran is the chained source comparison.
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
static void fill_froude(DiagnoD9TerrainBoundary& f,bool flat){
    f.isurft=-1;
    f.tinf_k=285.f;
    f.critfn=1.f;
    f.terrain_m.assign(2500,flat?0.f:120.f);
    if(!flat)
        for(int j=0;j<50;++j)for(int i=0;i<50;++i)
            f.terrain_m[std::size_t(j)*50+std::size_t(i)]=
                100.f+160.f*std::exp(-float((i-21)*(i-21)+(j-24)*(j-24))/90.f);
    f.maximum_terrain_m=f.terrain_m;
    if(!flat)
        for(float& value:f.maximum_terrain_m)value+=400.f;
    f.lapse_rate_k_per_m.assign(2500,0.006f);
    f.surface_temperature_k.assign(2500,285.f);
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
    const auto identity=integrate_diagno_d9_selected(input);
    require(identity.prepared_ug==identity.raw_first_guess.ug_mps&&
            identity.prepared_vg==identity.raw_first_guess.vg_mps,
            "D9A identity route must leave the step-one field untouched");
    // Original FRADJ needs terrain relief, subcritical Froude numbers and an
    // upslope wind; a flat 0 m terrain envelope must be a strict no-op.
    input.froude_adjustment=true;
    fill_froude(input.terrain,true);
    const auto flat=integrate_diagno_d9_selected(input);
    require(flat.prepared_ug==identity.prepared_ug&&
            flat.prepared_vg==identity.prepared_vg,
            "D9A original FRADJ must not adjust flat calm terrain");
    fill_froude(input.terrain,false);
    const auto froude=integrate_diagno_d9_selected(input);
    require(froude.prepared_ug!=identity.prepared_ug||
            froude.prepared_vg!=identity.prepared_vg,
            "D9A original FRADJ must adjust the step-one winds over relief");
    require(froude.raw_first_guess.ug_mps==identity.raw_first_guess.ug_mps,
            "D9A FRADJ must not modify the raw WIND1 first guess output");
    require(froude.final_fields.u_mps!=identity.final_fields.u_mps||
            froude.final_fields.v_mps!=identity.final_fields.v_mps,
            "D9A FRADJ must propagate into the final wind field");
    // Original FRADJ only rotates the horizontal vector, so the speed at
    // every adjusted cell is preserved exactly.
    for(std::size_t n=0;n<22500;++n){
        const float before=std::hypot(identity.prepared_ug[n],
                                      identity.prepared_vg[n]);
        const float after=std::hypot(froude.prepared_ug[n],
                                     froude.prepared_vg[n]);
        if(before!=after)
            require(std::abs(before-after)<=1e-4f*std::max(before,1.f),
                    "D9A FRADJ must preserve the step-one wind speed");
    }
    // The upper levels are outside the terrain envelope and must survive.
    for(std::size_t n=8*2500;n<22500;++n)
        require(froude.prepared_ug[n]==identity.prepared_ug[n]&&
                froude.prepared_vg[n]==identity.prepared_vg[n],
                "D9A FRADJ must not touch levels above the terrain envelope");
    // Fail-closed contract surface.
    auto short_terrain=input;
    short_terrain.terrain.terrain_m.pop_back();
    rejected([&]{(void)integrate_diagno_d9_selected(short_terrain);},
             "D9A accepted a truncated FRADJ terrain field");
    auto missing_heat=input;
    missing_heat.terrain.surface_temperature_k.clear();
    rejected([&]{(void)integrate_diagno_d9_selected(missing_heat);},
             "D9A accepted a missing FRADJ surface temperature field");
    auto bad_critfn=input;
    bad_critfn.terrain.critfn=-1.f;
    rejected([&]{(void)integrate_diagno_d9_selected(bad_critfn);},
             "D9A accepted a negative FRADJ critical Froude number");
    auto bad_tinf=input;
    bad_tinf.terrain.tinf_k=0.f;
    rejected([&]{(void)integrate_diagno_d9_selected(bad_tinf);},
             "D9A accepted a nonpositive FRADJ domain temperature");
    auto nonfinite=input;
    nonfinite.terrain.lapse_rate_k_per_m[0]=std::nanf("");
    rejected([&]{(void)integrate_diagno_d9_selected(nonfinite);},
             "D9A accepted a nonfinite FRADJ lapse rate");
    auto double_corrected=input;
    double_corrected.upstream_mode=DiagnoD9UpstreamMode::ExternallyCompletedUpstreamPhysics;
    double_corrected.corrected_first_guess_u_mps.assign(22500,7.f);
    double_corrected.corrected_first_guess_v_mps.assign(22500,-3.f);
    rejected([&]{(void)integrate_diagno_d9_selected(double_corrected);},
             "D9A applied FRADJ on top of an external corrected field");
    std::cout<<"PASS_P6D9A_SELECTED_IFRADJ1_UPSTREAM_ROUTE_SOFTWARE_ONLY\n";
    return 0;
 }catch(const std::exception& e){
    std::cerr<<e.what()<<'\n';return 1;
 }
}
