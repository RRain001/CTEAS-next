#include "cteas/p6/wind1_selected_firstguess.hpp"
#include "cteas/p6/similt_profile.hpp"
#include <cmath>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

using namespace cteas::calmet::p6;
int main(int argc,char** argv){
 try{
    if(argc!=3)throw std::invalid_argument("usage: wind1_firstguess INPUT OUTPUT");
    std::ifstream src(argv[1]);
    if(!src)throw std::runtime_error("cannot open selected WIND1 input");
    Wind1FirstGuessSelectedControls cfg;
    float observed_u=0.f, observed_v=0.f, rough=0.f, latitude=0.f,zanem=0.f;
    if(!(src>>cfg.surface_x_relative_m>>cfg.surface_y_relative_m>>
         cfg.upper_x_relative_m>>cfg.upper_y_relative_m>>
         observed_u>>observed_v>>rough>>latitude>>zanem>>cfg.icalm))
        throw std::runtime_error("selected WIND1 header is incomplete");
    for(auto& b:cfg.vertical_bias)
        if(!(src>>b))throw std::runtime_error("missing WIND1 BIAS layer");
    Wind1SelectedStationHour station;
    station.surface_station_id=58321;
    station.upper_station_id=58424;
    station.surface_observed_u_mps=observed_u;
    station.surface_observed_v_mps=observed_v;
    const float first_speed=std::sqrt(observed_u*observed_u+observed_v*observed_v);
    if(first_speed<0.0001f){
        for(auto& w:station.surface_neutral_profile)w=LayerWind{0.f,0.f};
    }else {
        // WIND1's own SIMILT call: neutral and uncapped (L36171 ZMO=ZML=10000.).
        const SimiltProfileInput input{
            latitude,zanem,rough,observed_u,observed_v,
            10000.f,10000.f,10000.f,0,
            {0.f,20.f,40.f,80.f,160.f,320.f,640.f,1200.f,2000.f,3000.f}
        };
        const auto extrapolated=original_similt_profile(input);
        for(std::size_t k=0;k<9;k++){
            station.surface_neutral_profile[k]={
                extrapolated.u_mps[k],extrapolated.v_mps[k]
            };
        }
    }
    for(std::size_t k=0;k<9;k++){
        auto& w=station.upper_observed_profile[k];
        if(!(src>>w.u_mps>>w.v_mps))
            throw std::runtime_error("missing WIND1 upper level");
        // CALMET EDIT=999, EDITL=900. Do not assume the deprecated
        // synthetic 999999 upper-air missing marker.
        cfg.upper_layer_valid[k]=std::abs(w.u_mps)<900.f&&
                                 std::abs(w.v_mps)<900.f;
    }
    std::string remainder;
    if(src>>remainder)throw std::runtime_error("extra WIND1 input fields");
    const auto wind=wind1_firstguess_selected(station,cfg);
    std::ofstream out(argv[2]);
    if(!out)throw std::runtime_error("cannot create WIND1 output");
    out<<std::scientific<<std::setprecision(13);
    const std::size_t cells=static_cast<std::size_t>(cfg.nx)*static_cast<std::size_t>(cfg.ny);
    for(int k=0;k<cfg.nz;k++)for(int j=0;j<cfg.ny;j++)for(int i=0;i<cfg.nx;i++){
        const std::size_t index=static_cast<std::size_t>(k)*cells+
            static_cast<std::size_t>(j)*static_cast<std::size_t>(cfg.nx)+
            static_cast<std::size_t>(i);
        out<<i+1<<" "<<j+1<<" "<<k+1<<" "
           <<wind.ug_mps[index]<<" "<<wind.vg_mps[index]<<'\n';
    }
    return 0;
 }catch(const std::exception& ex){
    std::cerr<<ex.what()<<'\n';
    return 1;
 }
}