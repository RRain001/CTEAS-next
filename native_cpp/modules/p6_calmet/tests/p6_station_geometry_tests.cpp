#include "cteas/p6/station_geometry.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>
using namespace cteas::calmet::p6;
void check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
int main(){
    try{
        const std::vector<float> faces{0,20,40,80,160,320,640,1200,2000,3000};
        const auto mid=original_layer_midpoints(faces);
        check(mid.size()==9 && mid[0]==10 && mid[1]==30 && mid.back()==2500,
              "original vertical center heights");
        check(upper_reference_cell({0,0},50,50,100).i==1,"upper SW corner");
        check(upper_reference_cell({50,49},50,50,100).i==2,"upper half-cell rule");
        check(upper_reference_cell({4999,-999},50,50,100).i==50,"upper exterior clipped");
        check(upper_reference_cell({4999,-999},50,50,100).j==1,"upper southern exterior clipped");
        check(wind_station_cell({4999,-150},100).i==50,"wind station truncation");
        check(wind_station_cell({4999,-150},100).j==0,"negative fractional truncation");
        check(wind_station_cell({-200,0},100).i==-1,"far exterior station must not be silently clipped");
        std::vector<float> z0(2500,.05f);
        auto m=surface_station_mapping({5100,-300},50,50,100,z0,10,8);
        check(m.wind_station_cell.i==52 && m.wind_station_cell.j==-2,
              "original unsnapped station coordinates preserved");
        check(m.bounded_surface_cell.i==50 && m.bounded_surface_cell.j==1,
              "original station roughness lookup clips to nearest boundary");
        check(std::isfinite(m.zlogsta) && m.zlogsta>1,
              "first-center logarithmic wind adjustment at 8m anemometer");
        bool thrown=false;
        try{(void)first_layer_log_wind_factor(10,.05f,.05f);}
        catch(const std::invalid_argument&){thrown=true;}
        check(thrown,"zero log denominator must fail closed");
        thrown=false;
        try{(void)upper_reference_cell({std::numeric_limits<float>::quiet_NaN(),0},50,50,100);}
        catch(const std::invalid_argument&){thrown=true;}
        check(thrown,"NaN station cannot be mapped");
        std::cout<<"PASS P6C_STATION_GEOMETRY_SOFTWARE_ONLY\n";
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
