#include "cteas/p6/wind1_selected_firstguess.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
using namespace cteas::calmet::p6;
static void check(bool yes,const char* what){
    if(!yes)throw std::runtime_error(what);
}
template<class F> static void fails(F&& fun,const char* message){
    bool rejected=false;
    try{fun();}catch(const std::invalid_argument&){rejected=true;}
    check(rejected,message);
}
int main(){
 try{
    Wind1SelectedStationHour station;
    station.surface_station_id=58321;
    station.upper_station_id=58424;
    station.surface_observed_u_mps=3.f;
    station.surface_observed_v_mps=4.f;
    for(std::size_t k=0;k<9;k++){
        station.surface_neutral_profile[k]=LayerWind{3.f,4.f};
        station.upper_observed_profile[k]=LayerWind{-1.f,6.f};
    }
    Wind1FirstGuessSelectedControls c;
    c.surface_x_relative_m=1000.f;
    c.surface_y_relative_m=1500.f;
    c.upper_x_relative_m=4200.f;
    c.upper_y_relative_m=3000.f;
    auto f=wind1_firstguess_selected(station,c);
    check(f.ug_mps.size()==22500&&f.vg_mps.size()==22500,
          "original 50x50x9 field sizes");
    const std::size_t near_surface=14u*50u+9u;
    const std::size_t near_upper=29u*50u+41u;
    check(f.ug_mps[near_surface]>f.ug_mps[near_upper],
          "inverse-squared weighting must favor nearer observed wind");

    c.vertical_bias[0]=1.f;
    c.vertical_bias[1]=-1.f;
    f=wind1_firstguess_selected(station,c);
    check(std::abs(f.ug_mps[near_surface]+1.f)<1e-5f &&
          std::abs(f.vg_mps[near_surface]-6.f)<1e-5f,
          "BIAS=+1 must select upper wind at level one");
    const std::size_t second=2500u+near_surface;
    check(std::abs(f.ug_mps[second]-3.f)<1e-5f &&
          std::abs(f.vg_mps[second]-4.f)<1e-5f,
          "BIAS=-1 must select surface wind at level two");

    c.vertical_bias.fill(0.f);
    c.upper_layer_valid[2]=false;
    station.upper_observed_profile[2]=LayerWind{999.f,999.f};
    f=wind1_firstguess_selected(station,c);
    const std::size_t missing=5000u+near_surface;
    check(std::abs(f.ug_mps[missing]-3.f)<1e-5f &&
          std::abs(f.vg_mps[missing]-4.f)<1e-5f,
          "missing upper layer must return all weight to surface");
    station.upper_observed_profile[2]=LayerWind{999999.f,999999.f};
    fails([&]{(void)wind1_firstguess_selected(station,c);},
          "legacy 999999 masked upper sentinel must not silently replace original EDIT=999");
    station.upper_observed_profile[2]=LayerWind{999.f,998.f};
    fails([&]{(void)wind1_firstguess_selected(station,c);},
          "partially missing upper layer must reject unequal mask/sentinel");
    station.upper_observed_profile[2]=LayerWind{999.f,999.f};
    c.vertical_bias[2]=1.f;
    fails([&]{(void)wind1_firstguess_selected(station,c);},
          "missing only weighted upper observation must fail");
    c.vertical_bias[2]=0.f;
    c.upper_layer_valid[2]=true;
    station.upper_observed_profile[2]=LayerWind{-1.f,6.f};

    station.surface_observed_u_mps=0.f;
    station.surface_observed_v_mps=0.f;
    for(auto& s:station.surface_neutral_profile)s=LayerWind{0.f,0.f};
    c.icalm=0;
    f=wind1_firstguess_selected(station,c);
    check(std::abs(f.ug_mps[second]+1.f)<5e-4f,
          "ICALM=0 should ignore surface calm aloft (REAL*4 renormalization)");
    c.icalm=1;
    f=wind1_firstguess_selected(station,c);
    check(f.ug_mps[second]>-1.f&&f.ug_mps[second]<0.f,
          "ICALM=1 must retain some surface calm weight");
    station.surface_neutral_profile[4]=LayerWind{1.f,0.f};
    fails([&]{(void)wind1_firstguess_selected(station,c);},
          "calm profile must not have invented wind");
    station.surface_neutral_profile[4]=LayerWind{0.f,0.f};
    c.nbar=1;
    fails([&]{(void)wind1_firstguess_selected(station,c);},
          "unimplemented barrier must fail closed");
    std::cout<<"P6D8B ORIGINAL WIND1 SELECTED FIRST GUESS SOFTWARE PASS\n";
    return 0;
 }catch(const std::exception& e){
    std::cerr<<e.what()<<'\n';return 1;
 }
}