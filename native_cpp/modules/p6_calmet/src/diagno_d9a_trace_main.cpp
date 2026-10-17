// P6D9A original-source *synthetic identity upstream* numeric trace.
// THIS IS NOT a replacement for real P6E heat/terrain/slope physics.
#include "cteas/p6/diagno_d9a_selected_bridge.hpp"
#include "cteas/p6/similt_profile.hpp"
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

using namespace cteas::calmet::p6;
int main(int argc,char** argv){
 try{
    if(argc!=8)throw std::invalid_argument(
        "d9a INPUT WIND1_OUT INTER2_OUT FINAL_OUT BOUND_OUT PREPARED_OUT W_OUT");
    std::ifstream f(argv[1]);
    if(!f)throw std::runtime_error("D9A source fixture missing");
    DiagnoD9SelectedInput in;
    in.upstream_mode=DiagnoD9UpstreamMode::SyntheticIdentityForSourceAudit;
    auto& cfg=in.first_guess;
    float su=0.f,sv=0.f,rough=0.f,lat=0.f,height=0.f;
    if(!(f>>cfg.surface_x_relative_m>>cfg.surface_y_relative_m>>
         cfg.upper_x_relative_m>>cfg.upper_y_relative_m>>
         su>>sv>>rough>>lat>>height>>cfg.icalm))
        throw std::runtime_error("D9A WIND1 header missing");
    for(float& bias:cfg.vertical_bias)
        if(!(f>>bias))throw std::runtime_error("D9A missing WIND1 biases");
    auto& s=in.stations;
    s.surface_station_id=58321;
    s.upper_station_id=58424;
    s.surface_observed_u_mps=su;s.surface_observed_v_mps=sv;
    if(std::sqrt(su*su+sv*sv)<0.0001f){
        for(auto& w:s.surface_neutral_profile)w=LayerWind{0.f,0.f};
    }else{
        // WIND1's SIMILT call is neutral and uncapped (calmet.for L36171:
        // ZMO=ZML=10000.), so the trace uses that same selected route.
        const SimiltProfileInput surface{lat,height,rough,su,sv,
            10000.f,10000.f,10000.f,0,{0.f,20.f,40.f,80.f,160.f,320.f,640.f,1200.f,2000.f,3000.f}};
        const auto neutral=original_similt_profile(surface);
        for(std::size_t k=0;k<9;k++)
            s.surface_neutral_profile[k]={neutral.u_mps[k],neutral.v_mps[k]};
    }
    for(std::size_t k=0;k<9;k++){
        auto& wind=s.upper_observed_profile[k];
        if(!(f>>wind.u_mps>>wind.v_mps))
            throw std::runtime_error("D9A upper profile missing");
        cfg.upper_layer_valid[k]=wind.u_mps<999998.f&&wind.v_mps<999998.f;
    }
    in.smoothing_passes.resize(9);
    in.layer_thickness_m.resize(9);
    for(int& p:in.smoothing_passes)
        if(!(f>>p))throw std::runtime_error("D9A smoothing missing");
    for(float& dz:in.layer_thickness_m)
        if(!(f>>dz))throw std::runtime_error("D9A dz missing");
    std::vector<int> nintrp(9);
    for(int& n:nintrp)
        if(!(f>>n))throw std::runtime_error("D9A NINTRP missing");
    float rmin,rmax1,rmax2,rmax3,r1,r2;
    if(!(f>>rmin>>rmax1>>rmax2>>rmax3>>r1>>r2))
        throw std::runtime_error("D9A INTER2 radii missing");
    std::vector<int> landuse(2500);
    for(int& lu:landuse)
        if(!(f>>lu))throw std::runtime_error("D9A landuse missing");
    std::vector<float> weight(22500);
    for(float& wo:weight)
        if(!(f>>wo))throw std::runtime_error("D9A WO observation weight missing");
    for(auto *p:{&in.inter2_u,&in.inter2_v}){
        p->nx=50;p->ny=50;p->nz=9;p->nstations=2;
        p->dx_m=100.f;p->dy_m=100.f;
        p->rmin_km=rmin;p->rmax1_km=rmax1;
        p->rmax2_km=rmax2;p->rmax3_km=rmax3;
        p->r1_km=r1;p->r2_km=r2;
        p->edit=999999.f;p->editl=999998.f;
        p->nintrp_per_layer=nintrp;
        p->station_x_km={cfg.surface_x_relative_m*0.001f,
                         cfg.upper_x_relative_m*0.001f};
        p->station_y_km={cfg.surface_y_relative_m*0.001f,
                         cfg.upper_y_relative_m*0.001f};
        p->landuse=landuse;p->observation_weight=weight;
        p->station_component_mps.resize(18);
        for(float& observed:p->station_component_mps)
            if(!(f>>observed))throw std::runtime_error("D9A station U/V missing");
    }
    int obrien=0;
    if(!(f>>in.cellzb_origin_m>>obrien>>in.minim_iterations>>
         in.minim_divergence_limit_per_s))
        throw std::runtime_error("D9A IOBR/CELLZB/MINIM controls missing");
    if(obrien!=0&&obrien!=1)
        throw std::runtime_error("D9A IOBR flag must be 0 or 1");
    in.obrien_adjustment=obrien==1;
    int froude=0;
    if(!(f>>froude>>in.terrain.isurft>>in.terrain.tinf_k>>in.terrain.critfn))
        throw std::runtime_error("D9A IFRADJ controls missing");
    if(froude!=0&&froude!=1)
        throw std::runtime_error("D9A IFRADJ flag must be 0 or 1");
    in.froude_adjustment=froude==1;
    for(auto* plane:{&in.terrain.terrain_m,&in.terrain.maximum_terrain_m,
                     &in.terrain.lapse_rate_k_per_m,
                     &in.terrain.surface_temperature_k}){
        plane->resize(2500);
        for(float& value:*plane)
            if(!(f>>value))throw std::runtime_error("D9A FRADJ 50x50 field missing");
    }
    int slope=0;
    if(!(f>>slope>>in.slope.water_first>>in.slope.water_last))
        throw std::runtime_error("D9A ISLOPE controls missing");
    if(slope!=0&&slope!=1)
        throw std::runtime_error("D9A ISLOPE flag must be 0 or 1");
    in.slope_flow=slope==1;
    for(auto* plane:{&in.slope.minimum_terrain_m,
                     &in.slope.distance_to_max_terrain_m,
                     &in.slope.distance_to_min_terrain_m,
                     &in.slope.sensible_heat_w_m2}){
        plane->resize(2500);
        for(float& value:*plane)
            if(!(f>>value))throw std::runtime_error("D9A SLOPE 50x50 field missing");
    }
    in.slope.landuse.resize(2500);
    for(int& value:in.slope.landuse)
        if(!(f>>value))throw std::runtime_error("D9A SLOPE landuse missing");
    int ikine=0,terset_selector=0;
    if(!(f>>ikine>>in.alpha>>in.kinematic_iterations>>
         in.kinematic_divergence_limit_per_s>>terset_selector>>
         in.terrad_km))
        throw std::runtime_error("D9A IKINE/ALPHA/MINIM/TERSET controls missing");
    if(ikine!=0&&ikine!=1)
        throw std::runtime_error("D9A IKINE flag must be 0 or 1");
    in.kinematic_route=ikine==1;
    if(terset_selector!=0&&terset_selector!=1)
        throw std::runtime_error("D9A TERSET selector must be 0 or 1");
    in.terset_envelope=terset_selector==1;
    if(in.terset_envelope){
        // The in-chain TERSET kernel owns the envelope; drop the fixture copies
        // so the bridge's single-provider rule stays enforceable.
        in.terrain.maximum_terrain_m.clear();
        in.slope.minimum_terrain_m.clear();
        in.slope.distance_to_max_terrain_m.clear();
        in.slope.distance_to_min_terrain_m.clear();
    }
    std::string extra;
    if(f>>extra)throw std::runtime_error("D9A input trailing data");
    auto out=integrate_diagno_d9_selected(in);
    std::ofstream fg(argv[2]),blend(argv[3]),fin(argv[4]),bound(argv[5]);
    std::ofstream prepared(argv[6]),wface(argv[7]);
    if(!fg||!blend||!fin||!bound||!prepared||!wface)
        throw std::runtime_error("D9A output file unavailable");
    fg<<std::scientific<<std::setprecision(13);
    blend<<std::setprecision(12)<<"i,j,k,u,v\n";
    fin<<std::setprecision(12)<<"i,j,k,u,v,div,w_below,w_above\n";
    prepared<<std::setprecision(12)<<"i,j,k,u_mps,v_mps\n";
    wface<<std::setprecision(12)<<"i,j,face,w_mps\n";
    bound<<std::setprecision(12);
    if(!out.kinematic_w_face_mps.empty())
        for(int k=0;k<10;k++)for(int j=0;j<50;j++)for(int i=0;i<50;i++)
            wface<<i+1<<","<<j+1<<","<<k+1<<","
                 <<out.kinematic_w_face_mps[std::size_t(k)*2500+
                                             std::size_t(j)*50+
                                             std::size_t(i)]<<'\n';
    for(int k=0;k<9;k++)for(int j=0;j<50;j++)for(int i=0;i<50;i++){
        const auto n=std::size_t(k)*2500+std::size_t(j)*50+std::size_t(i);
        fg<<i+1<<" "<<j+1<<" "<<k+1<<" "
          <<out.raw_first_guess.ug_mps[n]<<" "<<out.raw_first_guess.vg_mps[n]<<'\n';
        prepared<<i+1<<","<<j+1<<","<<k+1<<","
                <<out.prepared_ug[n]<<","<<out.prepared_vg[n]<<'\n';
        blend<<i+1<<","<<j+1<<","<<k+1<<","
             <<out.blended_u[n]<<","<<out.blended_v[n]<<'\n';
        fin<<i+1<<","<<j+1<<","<<k+1<<","
           <<out.final_fields.u_mps[n]<<","<<out.final_fields.v_mps[n]<<","
           <<out.final_fields.divergence_per_s[n]<<","
           <<out.final_fields.w_face_mps[n]<<","
           <<out.final_fields.w_face_mps[n+2500]<<'\n';
    }
    for(int k=0;k<9;k++)for(int side=0;side<2;side++){
        for(int j=0;j<50;j++){
            const std::size_t n=std::size_t(k)*100+
                                std::size_t(side)*50+std::size_t(j);
            bound<<"U "<<k+1<<" "<<side+1<<" "<<j+1<<" "
                 <<out.final_fields.ub_west_east_mps[n]<<'\n';
        }
        for(int i=0;i<50;i++){
            const std::size_t n=std::size_t(k)*100+
                                std::size_t(side)*50+std::size_t(i);
            bound<<"V "<<k+1<<" "<<side+1<<" "<<i+1<<" "
                 <<out.final_fields.vb_south_north_mps[n]<<'\n';
        }
    }
    return 0;
 }catch(const std::exception& e){
    std::cerr<<e.what()<<'\n';return 1;
 }
}
