#include "cteas/p6/p6g_multi_wind1_firstguess.hpp"
#include "cteas/p6/wind1_selected_firstguess.hpp"
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace cteas::calmet;
static void check(bool yes,const char* message){
    if(!yes)throw std::runtime_error(message);
}
template<typename F> static void must_fail(F f,const char* what){
    bool rejected=false;
    try{(void)f();}
    catch(const std::invalid_argument&){rejected=true;}
    check(rejected,what);
}
static p6g::Wind1MultiInput pair_input(int nx=50,int ny=50,float spacing=100.f){
    p6g::Wind1MultiInput in;
    in.nx=nx;in.ny=ny;in.nz=9;
    in.spacing_m=spacing;in.surface_count=1;in.upper_count=1;
    in.station_x_m={1000.f,4200.f};
    in.station_y_m={1500.f,3000.f};
    in.surface_speeds_mps={5.f};
    in.vertical_bias.assign(9,0.f);
    in.station_u_mps.resize(18);
    in.station_v_mps.resize(18);
    in.present.assign(18,1);
    for(std::size_t k=0;k<9;++k){
        in.station_u_mps[k*2]=3.f;in.station_v_mps[k*2]=4.f;
        in.station_u_mps[k*2+1]=-1.f;in.station_v_mps[k*2+1]=6.f;
    }
    return in;
}
static p6::Wind1SelectedStationHour frozen_pair_hour(const p6g::Wind1MultiInput& in){
    p6::Wind1SelectedStationHour h;
    h.surface_station_id=58321;h.upper_station_id=58424;
    h.surface_observed_u_mps=in.surface_speeds_mps[0];
    h.surface_observed_v_mps=0.f;
    for(std::size_t k=0;k<9;++k){
        h.surface_neutral_profile[k]=p6::LayerWind{
            in.station_u_mps[k*2],in.station_v_mps[k*2]};
        h.upper_observed_profile[k]=p6::LayerWind{
            in.present[k*2+1]?in.station_u_mps[k*2+1]:999.f,
            in.present[k*2+1]?in.station_v_mps[k*2+1]:999.f};
    }
    return h;
}
static void compare_frozen_pair(const p6g::Wind1MultiInput& in,float tol=0.0f) {
    p6::Wind1FirstGuessSelectedControls ref;
    ref.nx=50;ref.ny=50;ref.nz=9;
    ref.grid_spacing_m=in.spacing_m;
    ref.surface_x_relative_m=in.station_x_m[0];
    ref.surface_y_relative_m=in.station_y_m[0];
    ref.upper_x_relative_m=in.station_x_m[1];
    ref.upper_y_relative_m=in.station_y_m[1];
    ref.icalm=in.icalm;
    for(std::size_t k=0;k<9;++k){
        ref.vertical_bias[k]=in.vertical_bias[k];
        ref.upper_layer_valid[k]=in.present[k*2+1]!=0;
    }
    const auto old=p6::wind1_firstguess_selected(frozen_pair_hour(in),ref);
    const auto now=p6g::multi_station_wind1_firstguess(in);
    check(now.u_mps.size()==old.ug_mps.size()&&
          now.v_mps.size()==old.vg_mps.size(),"pair shapes differ");
    float max_delta=0.f;
    for(std::size_t k=0;k<now.u_mps.size();++k){
        max_delta=std::max(max_delta,std::abs(now.u_mps[k]-old.ug_mps[k]));
        max_delta=std::max(max_delta,std::abs(now.v_mps[k]-old.vg_mps[k]));
    }
    if(max_delta>tol){
        std::cerr<<"G9 FROZEN_PAIR_DELTA "<<max_delta<<" tolerance="<<tol<<"\n";
        throw std::runtime_error("G9 one-pair source-scoped WIND1 parity delta");
    }
}
int main(){
    try{
        auto basic=pair_input();
        compare_frozen_pair(basic);
        basic.vertical_bias[0]=1.f;
        basic.vertical_bias[1]=-1.f;
        compare_frozen_pair(basic);
        basic.vertical_bias.assign(9,0.f);
        basic.present[2*2+1]=0;
        compare_frozen_pair(basic);
        basic.present[2*2+1]=1;
        basic.surface_speeds_mps[0]=0.f;
        for(std::size_t k=0;k<9;++k){
            basic.station_u_mps[2*k]=0.f;
            basic.station_v_mps[2*k]=0.f;
        }
        compare_frozen_pair(basic);
        basic.icalm=1;
        compare_frozen_pair(basic);
        // Multi-site, coarser 10-km and expanded 120x120km test geometry.
        auto multiple=pair_input(12,12,10000.f);
        multiple.surface_count=2;multiple.upper_count=2;
        multiple.station_x_m={10000.f,100000.f,25000.f,80000.f};
        multiple.station_y_m={15000.f,100000.f,30000.f,90000.f};
        multiple.surface_speeds_mps={5.f,8.f};
        multiple.vertical_bias.assign(9,0.f);
        multiple.station_u_mps.resize(36);
        multiple.station_v_mps.resize(36);
        multiple.present.assign(36,1);
        for(std::size_t k=0;k<9;++k){
            multiple.station_u_mps[k*4+0]=3.f;multiple.station_v_mps[k*4+0]=4.f;
            multiple.station_u_mps[k*4+1]=-4.f;multiple.station_v_mps[k*4+1]=5.f;
            multiple.station_u_mps[k*4+2]=1.f;multiple.station_v_mps[k*4+2]=6.f;
            multiple.station_u_mps[k*4+3]=2.f;multiple.station_v_mps[k*4+3]=-5.f;
        }
        const auto four=p6g::multi_station_wind1_firstguess(multiple);
        check(four.u_mps.size()==1296&&four.v_mps.size()==1296,
              "10km 12x12x9 field size");
        const auto near_ss1=static_cast<std::size_t>(1*12+1);
        const auto near_ss2=static_cast<std::size_t>(10*12+10);
        check(four.u_mps[near_ss1]>four.u_mps[near_ss2],
              "expanded domain does not respond to station location");
        // The original L36292-L36345 sequential calm and upper-missing
        // loops cannot be replaced by a single total-weight normalization.
        auto calm=multiple;
        calm.surface_speeds_mps={0.f,0.f};
        for(std::size_t k=0;k<9;++k){
            for(std::size_t l=0;l<2;++l){
                calm.station_u_mps[k*4+l]=0.f;
                calm.station_v_mps[k*4+l]=0.f;
            }
        }
        const auto excluded=p6g::multi_station_wind1_firstguess(calm);
        calm.icalm=1;
        const auto included=p6g::multi_station_wind1_firstguess(calm);
        const auto upper_cell=144u+near_ss1;
        check(std::isfinite(excluded.u_mps[upper_cell])&&
              excluded.u_mps[upper_cell]>included.u_mps[upper_cell],
              "original sequential two-calm-surface exclusion missing");
        auto both_missing=multiple;
        both_missing.present[2u*4u+2u]=0;
        both_missing.present[2u*4u+3u]=0;
        const auto surface_only=p6g::multi_station_wind1_firstguess(both_missing);
        check(std::isfinite(surface_only.u_mps[2u*144u+near_ss1])&&
              surface_only.u_mps[2u*144u+near_ss1]<=3.001f&&
              surface_only.u_mps[2u*144u+near_ss1]>=-4.001f,
              "sequential two-upper-missing redistribution to surface");
        auto first_surface_missing=multiple;
        first_surface_missing.present[0]=0;
        for(std::size_t k=1;k<9;++k)
            first_surface_missing.present[k*4]=0;
        const auto fallback=p6g::multi_station_wind1_firstguess(
            first_surface_missing);
        check(fallback.u_mps[near_ss1]!=four.u_mps[near_ss1],
              "missing ground station must be excluded at bulk weight stage");
        multiple.vertical_bias[0]=1.f;
        const auto upper_forced=p6g::multi_station_wind1_firstguess(multiple);
        check(upper_forced.u_mps[near_ss1]!=four.u_mps[near_ss1],
              "G9 BIAS +1 did not change multi-site surface weighting");
        multiple.vertical_bias[0]=-1.f;
        const auto surface_forced=p6g::multi_station_wind1_firstguess(multiple);
        check(surface_forced.u_mps[near_ss1]!=four.u_mps[near_ss1],
              "G9 BIAS -1 did not change multi-site upper weighting");
        multiple.vertical_bias.assign(9,0.f);
        multiple.present[2*4+2]=0;
        const auto one_missing=p6g::multi_station_wind1_firstguess(multiple);
        check(std::isfinite(one_missing.u_mps[2*144]),
              "single upper missing unexpectedly spoiled multi-site grid");
        multiple.vertical_bias[2]=1.f;
        multiple.present[2*4+3]=0;
        must_fail([&]{return p6g::multi_station_wind1_firstguess(multiple);},
                  "G9 forced missing all uppers must fail closed");
        multiple.vertical_bias.assign(9,0.f);
        multiple.present.assign(36,1);
        multiple.spacing_m=0.f;
        must_fail([&]{return p6g::multi_station_wind1_firstguess(multiple);},
                  "G9 zero grid spacing must fail closed");
        multiple.spacing_m=10000.f;
        multiple.station_x_m.pop_back();
        must_fail([&]{return p6g::multi_station_wind1_firstguess(multiple);},
                  "G9 malformed station arrays must fail closed");
        std::cout<<"PASS P6G_G9_MULTI_WIND1_10KM_EXPANDED_PAIR_SELECTED_PARITY\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"FAIL P6G_G9_WIND1 "<<e.what()<<"\n";return 1;
    }
}
