#include "cteas/p6/p6g_original_wind_controls.hpp"
#include "cteas/p6/p6g_multi_wind1_firstguess.hpp"
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <exception>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>
using namespace cteas::calmet::p6g;
static void require(bool condition,const char* why){
    if(!condition)throw std::runtime_error(why);
}
template<class F>static void must_reject(F&& f,const char* why){
    bool denied=false;
    try{f();}catch(const std::invalid_argument&){denied=true;}
    require(denied,why);
}
static std::string replace_control(std::string text,const std::string& oldvalue,
                                    const std::string& nextvalue){
    const auto at=text.find(oldvalue);
    require(at!=std::string::npos,"original met.inp control reference missing");
    text.replace(at,oldvalue.size(),nextvalue);
    return text;
}
static Wind1MultiInput make_wind(const OriginalWindControls& controls){
    Wind1MultiInput w;
    w.nx=12;w.ny=12;w.nz=9;w.spacing_m=10000.f;
    w.surface_count=2;w.upper_count=2;
    w.station_x_m={10000.f,105000.f,25000.f,85000.f};
    w.station_y_m={20000.f,105000.f,40000.f,95000.f};
    w.surface_speeds_mps={5.f,6.f};
    w.vertical_bias.assign(controls.bias.begin(),controls.bias.end());
    w.icalm=controls.icalm;
    w.present.assign(36,1);
    w.station_u_mps.resize(36);w.station_v_mps.resize(36);
    for(std::size_t k=0;k<9;++k) {
        w.station_u_mps[k*4]=3.f;w.station_v_mps[k*4]=4.f;
        w.station_u_mps[k*4+1]=-4.f;w.station_v_mps[k*4+1]=5.f;
        w.station_u_mps[k*4+2]=10.f;w.station_v_mps[k*4+2]=-2.f;
        w.station_u_mps[k*4+3]=12.f;w.station_v_mps[k*4+3]=-5.f;
    }
    return w;
}
int main(int argc,char** argv){
    try{
        require(argc==2,"G15 expected original Hefei met.inp path");
        std::ifstream source(argv[1]);
        require(static_cast<bool>(source),"G15 original met.inp unavailable");
        const std::string deck((std::istreambuf_iterator<char>(source)),
                                std::istreambuf_iterator<char>());
        const auto v=parse_original_wind_controls(deck);
        require(v.iextrp==-4&&v.icalm==0&&v.iprog==0&&v.noobs==0&&
                v.ifradj==1&&v.islope==1&&v.iobr==0&&!v.lvary,
                "G15 original Hefei source route differed");
        // The original deck explicitly has BIAS(1)=0, but PR #53's
        // READCF L26579-26612 overrides the effective physical bias to -1.
        require(v.bias[0]==-1.f&&v.bias[1]==0.f,
                "G15 missing original IEXTRP=-4 READCF effective BIAS mutation");
        require(v.rmin_km==0.1f&&v.rmax1_km==100.f&&
                v.rmax2_km==200.f&&v.rmax3_km==200.f&&
                v.r1_km==50.f&&v.r2_km==100.f,
                "G15 original 2022 wind radii were replaced by G8 test constants");
        require(v.zface_m[0]==0.f&&v.zface_m[1]==20.f&&
                v.zface_m[9]==3000.f,
                "G15 source vertical faces were replaced by G8 hardcoding");
        require(v.nsmth[0]==2&&v.nsmth[1]==4&&
                v.nsmth[8]==4&&v.nintr2[0]==99&&v.nintr2[8]==99,
                "G15 original smoothing/station count array incorrect");
        const auto field=multi_station_wind1_firstguess(make_wind(v));
        auto incorrect=make_wind(v);
        incorrect.vertical_bias[0]=0.f;
        const auto old=multi_station_wind1_firstguess(incorrect);
        require(field.u_mps.size()==1296&&old.u_mps.size()==1296,
                "G15 multi-station source field shape incorrect");
        // A change in class BIAS modifies the first layer; this is a
        // real source-numerical sensitivity, not a permissive test tolerance.
        float largest=0.f;
        for(std::size_t i=0;i<144;++i)
            largest=std::max(largest,std::abs(field.u_mps[i]-old.u_mps[i]));
        require(largest>0.01f,"G15 original READCF BIAS has no actual WIND1 numerical effect");
        must_reject([&]{
            (void)parse_original_wind_controls(replace_control(
                deck,"! RMAX1 = 100. !","! RMAX1 = -5. !"));
        },"G15 invalid influence radius accepted");
        must_reject([&]{
            (void)parse_original_wind_controls(
                deck+"\n! RMAX1 = 150. !\n");
        },"G15 duplicate wind source control accepted");
        must_reject([&]{
            (void)parse_original_wind_controls(replace_control(
                deck,"! IEXTRP = -4  !","! IEXTRP = 4 !"));
        },"G15 unsupported extrapolation path accepted");
        must_reject([&]{
            (void)parse_original_wind_controls(replace_control(
                deck,"! LVARY =  F!","! LVARY = T !"));
        },"G15 unsupported varying interpolation radius accepted");
        std::cout<<"PASS_P6G_G15_ORIGINAL_METINP_WIND_CONTROL_SOURCE "
                   "RMIN_RMAX123_R1_R2_BIAS_NSМTH_NINTR2 "
                   "READCF_IEXTRP_MINUS4_BIAS1_MINUS1 "
                   "WIND1_NUMERICAL_SENSITIVITY="<<largest
                   <<" FULL_MULTI_SITE_PHYSICS=NOT_YET_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"FAIL_P6G_G15 "<<e.what()<<"\n";
        return 1;
    }
}
