#include "cteas/p6/calmet_station_deck.hpp"
#include "cteas/p6/calmet_station_surface.hpp"
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

using cteas::calmet::p6::original_calmet_station_deck;

static void expect(bool value,const char* msg) {
    if(!value)throw std::runtime_error(msg);
}
template<class F> static void must_fail(F&& f,const char* msg) {
    bool caught=false;
    try { f(); } catch (const std::invalid_argument&) { caught=true; }
    expect(caught,msg);
}

int main(int argc,char** argv) {
 try {
    const std::string deck=R"(
! SS1 ='S1'    583210    513.385   3533.769  0 10.0 !
! US1 ='U1'    58424     513.384   3533.772  0 !
)";
    const auto xy=original_calmet_station_deck(deck,510.885f,3531.269f);
    expect(!cteas::calmet::p6::original_calmet_deck_logical(
        "! LVARY = F !","LVARY",true),"LVARY=F must override fallback");
    expect(cteas::calmet::p6::original_calmet_deck_logical(
        "! LVARY = T !","LVARY",false),"LVARY=T must not be read as numeric 0");
    expect(xy.surface.id==583210&&xy.upper.id==58424,"station ids");
    expect(xy.surface.anemometer_height_m==10.f,
           "SS1 must retain original met.inp anemometer height");
    expect(xy.surface.time_zone_hours==0.f,
           "SS1 must retain original met.inp station time zone");
    {
        const auto alternative=original_calmet_station_deck(
            "! SS1 ='S' 1 513.385 3533.769 0 17.5 !\n"
            "! US1 ='U' 2 513.384 3533.772 0 !",510.885f,3531.269f);
        expect(alternative.surface.anemometer_height_m==17.5f,
               "nondefault SS1 height lost to hardcoded 10 m");
    }
    must_fail([&]{(void)original_calmet_station_deck(
        "! SS1 ='S' 1 513.385 3533.769 0 0 !\n"
        "! US1 ='U' 2 513.384 3533.772 0 !",510.885f,3531.269f);
    },"invalid SS1 measurement height was accepted");
    {
        // Original DIAGI IST/JST and WIND1 z0(ist,jst); synthetic GEO is
        // deliberately NON-uniform to catch the former Z0(1,1) mistake.
        std::vector<float> z0(2500,0.25f);
        z0[25U*50U+25U]=0.83f;
        const auto site=cteas::calmet::p6::original_calmet_station_surface_cell(
            xy.surface.local_x_m,xy.surface.local_y_m,100.f,100.f,50,50);
        expect(site.i_one_based==26&&site.j_one_based==26,
               "REAL*4 station cell is not (26,26)");
        const float roughness=cteas::calmet::p6::original_calmet_station_z0(
            z0,xy.surface.local_x_m,xy.surface.local_y_m,100.f,100.f,50,50);
        expect(roughness==0.83f,
               "WIND1 should get station-cell GEO z0, not first-cell z0");
        const auto low=cteas::calmet::p6::original_calmet_station_surface_cell(
            -1000.f,-1000.f,100.f,100.f,50,50);
        const auto high=cteas::calmet::p6::original_calmet_station_surface_cell(
            9900.f,9900.f,100.f,100.f,50,50);
        expect(low.i_one_based==1&&low.j_one_based==1&&
               high.i_one_based==50&&high.j_one_based==50,
               "original station cell boundary clipping");
    }
    expect(xy.surface.local_x_m==2500.f&&xy.surface.local_y_m==2500.f,
           "surface local geometry");
    expect(std::abs(xy.upper.local_x_m-2498.96875f)<1e-4f,
           "upper single-precision local x; not equirectangular");
    expect(std::abs(xy.upper.local_y_m-2503.0f)<1e-4f,
           "upper single-precision local y; not equirectangular");
    const float from_deck=(1000.f*513.384f)-(1000.f*510.885f);
    expect(std::bit_cast<std::uint32_t>(xy.upper.local_x_m)==
           std::bit_cast<std::uint32_t>(from_deck),
           "single precision multiplication must precede subtraction");
    const auto shifted=original_calmet_station_deck(
        "! SS1 ='A' 1 510.200 3530.100 0 10.0 !\n"
        "! US1 ='B' 2 509.950 3530.050 0 !\n",
        510.000f,3530.000f);
    expect(shifted.surface.local_x_m>0.f&&shifted.upper.local_x_m<0.f,
           "valid outside-grid station must not be clamped");
    must_fail([&]{(void)original_calmet_station_deck(
        "! SS1 ='S' 1 1 2 0 10 !",0.f,0.f);},"missing US1 not rejected");
    must_fail([&]{(void)original_calmet_station_deck(
        deck+"\n! SS1 ='duplicate' 583210 513 3533 0 10 !",510.f,3530.f);
    },"duplicate SS1 not rejected");
    must_fail([&]{(void)original_calmet_station_deck(
        "! SS2 ='S' 1 1 2 0 10 !\n! US1 ='U' 2 1 2 0 !",
        0.f,0.f);},"unsupported SS2 not rejected");
    must_fail([&]{(void)original_calmet_station_deck(
        "! SS1 ='S' 1 1e999 2 0 10 !\n! US1 ='U' 2 1 2 0 !",
        0.f,0.f);},"nonfinite station not rejected");
    if(argc==2) {
        std::ifstream in(argv[1]);
        if(!in)throw std::runtime_error("cannot read frozen met.inp");
        std::ostringstream s;s<<in.rdbuf();
        const auto real=original_calmet_station_deck(s.str(),510.885f,3531.269f);
        expect(real.surface.id==583210&&real.upper.id==58424,
               "frozen input station identities");
        expect(real.surface.local_x_m==2500.f&&real.surface.local_y_m==2500.f,
               "frozen surface UTM station position");
        expect(std::abs(real.upper.local_x_m-2498.96875f)<1e-4f,
               "frozen upper UTM x position");
        expect(std::abs(real.upper.local_y_m-2503.0f)<1e-4f,
               "frozen upper UTM y position");
    }
    std::cout<<"PASS_CALMET_DECK_STATIONS_FLOAT32\n";
    return 0;
 } catch(const std::exception& e) {
    std::cerr<<"FAIL_CALMET_DECK_STATIONS: "<<e.what()<<"\n";
    return 1;
 }
}
