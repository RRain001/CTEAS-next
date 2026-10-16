#include "cteas/p6/wind1_selected_station_hour.hpp"
#include <chrono>
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <utility>

using namespace cteas::calmet::p6;

static void ensure(bool good,const char* why){
    if(!good)throw std::runtime_error(why);
}
template<typename Fn> static void rejects(Fn&& invoke,const char* why){
    bool rejected=false;
    try{invoke();}catch(const std::invalid_argument&){rejected=true;}
    ensure(rejected,why);
}
int main(){
 try{
    using namespace std::chrono;
    const auto origin=sys_seconds{sys_days{year{2022}/January/1}};
    SurfaceInterval s;
    s.start=origin;s.end=origin+hours{1};
    s.obs.wind_valid=true;
    s.obs.wind_speed_mps=5.f;
    s.obs.wind_direction_deg=270.f; // wind FROM west => eastward U
    s.obs.precipitation_code_valid=false; // dry wind does not invent rain
    UpperHour upper;
    upper.end=s.end;
    upper.winds.assign(9,LayerWind{2.f,-1.f});
    for(std::size_t k=0;k<upper.winds.size();k++){
        upper.winds[k].u_mps+=static_cast<float>(k);
    }
    auto result=wind1_selected_station_hour(s,58321,upper,58424,
                                           31.939774f,10.f,0.1f);
    ensure(result.surface_station_id==58321&&result.upper_station_id==58424,
           "station identity propagation");
    ensure(result.hour_end==s.end,"model hour must be SURF ending UTC");
    ensure(std::abs(result.surface_observed_u_mps-5.f)<0.0001f,
           "WIND1 meteorological 270-degree direction to eastward U");
    ensure(std::abs(result.surface_observed_v_mps)<0.0001f,
           "WIND1 west wind should have near zero northward component");
    ensure(std::abs(result.surface_neutral_profile[0].u_mps-5.f)<0.0001f,
           "SIMILT neutral 10m wind must reproduce 10m observation");
    ensure(result.upper_observed_profile[8].u_mps==10.f &&
           result.upper_observed_profile[0].v_mps==-1.f,
           "PREPDI nine-layer observations must be preserved");
    ensure(!s.obs.precipitation_code_valid,
           "WIND1 must not turn missing rain into measured zero");
    s.obs.wind_direction_deg=0.f;
    result=wind1_selected_station_hour(s,58321,upper,58424,
                                       31.939774f,10.f,0.1f);
    ensure(std::abs(result.surface_observed_u_mps)<0.0001f &&
           std::abs(result.surface_observed_v_mps+5.f)<0.0001f,
           "north FROM wind should be southward V");

    s.obs.wind_valid=false;
    rejects([&]{(void)wind1_selected_station_hour(s,58321,upper,58424,
                          31.939774f,10.f,0.1f);},"missing surface mask");
    s.obs.wind_valid=true;s.obs.wind_speed_mps=0.f;
    rejects([&]{(void)wind1_selected_station_hour(s,58321,upper,58424,
                          31.939774f,10.f,0.1f);},"calm must remain unsupported");
    s.obs.wind_speed_mps=5.f;s.obs.wind_direction_deg=361.f;
    rejects([&]{(void)wind1_selected_station_hour(s,58321,upper,58424,
                          31.939774f,10.f,0.1f);},"invalid direction must fail");
    s.obs.wind_direction_deg=270.f;
    upper.end+=hours{1};
    rejects([&]{(void)wind1_selected_station_hour(s,58321,upper,58424,
                          31.939774f,10.f,0.1f);},"mismatched SURF/UP time");
    upper.end=s.end;
    upper.winds.pop_back();
    rejects([&]{(void)wind1_selected_station_hour(s,58321,upper,58424,
                          31.939774f,10.f,0.1f);},"nine layers required");
    upper.winds.emplace_back(999.f,0.f);
    rejects([&]{(void)wind1_selected_station_hour(s,58321,upper,58424,
                          31.939774f,10.f,0.1f);},"upper missing sentinel");
    upper.winds.back()=LayerWind{1.f,1.f};
    rejects([&]{(void)wind1_selected_station_hour(s,0,upper,58424,
                          31.939774f,10.f,0.1f);},"invalid station id");
    // The SIMILT port now covers both hemispheres (the southern branch backs
    // the wind); a southern station must produce a finite profile.
    {
        const auto south=wind1_selected_station_hour(s,58321,upper,58424,
                                                     -31.939774f,10.f,0.1f);
        if(!std::isfinite(south.surface_neutral_profile[0].u_mps)||
           !std::isfinite(south.surface_neutral_profile[8].v_mps))
            throw std::runtime_error("southern SIMILT profile must be finite");
    }
    std::cout<<"P6D8 WIND1 HOURLY SELECTED OBS ADAPTER SOFTWARE PASS\n";
    return 0;
 }catch(const std::exception& ex){
    std::cerr<<ex.what()<<'\n';
    return 1;
 }
}
