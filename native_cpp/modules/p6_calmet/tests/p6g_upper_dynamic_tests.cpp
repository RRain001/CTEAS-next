#include "cteas/p6/read_upper_dynamic.hpp"
#include "cteas/p6/read_upper.hpp"
#include <chrono>
#include <cstdio>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std::chrono;

static void check(bool ok,const char* message){
    if(!ok)throw std::runtime_error(message);
}
static int jul(sys_seconds t){
    const auto d=floor<days>(t);
    const auto y=year_month_day{d}.year();
    return int((d-sys_days{y/January/1}).count())+1;
}
static void sounding(std::ostream& out,int station,sys_seconds at,
                     bool bad_height=false,bool bad_id=false){
    const auto d=year_month_day{floor<days>(at)};
    const int hour=int(duration_cast<hours>(at-floor<days>(at)).count());
    out<<" 6201 "<<(bad_id?station+1:station)
       <<" "<<int(d.year())<<" "<<unsigned(d.month())<<" "<<unsigned(d.day())
       <<" "<<hour<<" 0 "
       <<int(d.year())<<" "<<unsigned(d.month())<<" "<<unsigned(d.day())
       <<" "<<hour<<" 0 2 2\n";
    const auto group=[&](float p,int height,float temp,int wd,int ws) {
        out<<"   "<<std::fixed<<std::setprecision(1)<<std::setw(6)<<p
           <<"/"<<std::setw(5)<<height<<"/"<<std::setw(5)<<temp
           <<"/"<<std::setw(3)<<wd<<"/"<<std::setw(3)<<ws;
    };
    group(1000,bad_height?9999:120,280.0f,0,0);
    group(500,5500,259.8f,999,999);
    out<<"\n";
}
static void fixture(const std::string& path,int station,
                    sys_seconds start,sys_seconds end,
                    const std::vector<sys_seconds>& times,
                    bool bad_height=false,bool wrong_station=false,
                    bool bad_header_jul=false){
    std::ofstream out(path);
    check(static_cast<bool>(out),"cannot create UP.DAT fixture");
    out<<"UP.DAT          2.1             Hour Start and End Times with Seconds\n"
       <<"1\nP6G original READ62 synthetic\nNONE\nUTC+0000\n";
    out<<int(year_month_day{floor<days>(start)}.year())<<" "
       <<(bad_header_jul?366:jul(start))<<" 0 0 "
       <<int(year_month_day{floor<days>(end)}.year())<<" "
       <<jul(end)<<" "<<int(duration_cast<hours>(end-floor<days>(end)).count())
       <<" 0 500.0 2 1\nF F F F\n";
    for(const auto t:times)
        sounding(out,station,t,bad_height,wrong_station);
}
static void equal_frozen(const cteas::calmet::p6::UpperLevel& a,
                         const cteas::calmet::p6::UpperLevel& b){
    check(a.pressure_hpa==b.pressure_hpa&&a.height_msl==b.height_msl&&
          a.temperature_k==b.temperature_k&&a.wd_deg==b.wd_deg&&
          a.ws_mps==b.ws_mps&&a.height_lgl_m==b.height_lgl_m&&
          a.u_mps==b.u_mps&&a.v_mps==b.v_mps&&
          a.height_valid==b.height_valid&&
          a.temperature_valid==b.temperature_valid&&
          a.wind_valid==b.wind_valid,"frozen RDUPN field/mask mismatch");
}
int main(){
    const std::string f1="p6g_upper_u1.dat";
    const std::string f2="p6g_upper_u2.dat";
    try{
        const auto b=sys_days{year{2022}/January/1};
        const auto e=sys_days{year{2022}/January/6}+hours{23};
        fixture(f1,58424,b,e,{b,b+hours{132}});
        const auto frozen=cteas::calmet::p6::read_upper_2022(f1,58424);
        const auto variable=cteas::calmet::p6g::read_upper_dynamic(f1,58424);
        check(variable.station_id==58424&&variable.pstop_hpa==500.0f&&
              variable.soundings.size()==frozen.soundings.size(),"frozen UP metadata");
        for(std::size_t i=0;i<variable.soundings.size();++i){
            const auto& old=frozen.soundings[i];
            const auto& now=variable.soundings[i];
            check(old.start==now.start&&old.end==now.end&&
                  old.levels==now.levels&&old.levels_raw==now.levels_raw,
                  "frozen soundings metadata mismatch");
            for(std::size_t k=0;k<now.data.size();++k)
                equal_frozen(old.data.at(k),now.data[k]);
        }
        const auto begin=sys_days{year{2023}/December/31};
        const auto finish=sys_days{year{2024}/January/1}+hours{23};
        const auto a=begin+hours{12};
        const auto c=sys_days{year{2024}/January/1};
        const auto d=c+hours{12};
        fixture(f1,58424,begin,finish,{a,c,d});
        fixture(f2,58425,begin,finish,{a,c,d});
        const auto many=cteas::calmet::p6g::read_upper_station_set(
            {f1,f2},{58424,58425});
        check(many.size()==2&&many[0].soundings.size()==3&&
              many[1].soundings.size()==3&&many[0].station_id==58424&&
              many[1].station_id==58425,"two upper stations across new year");
        check(many[0].soundings[1].end==c&&many[0].soundings[2].end==d,
              "2023/2024 sounding ordering");
        check(many[0].soundings[0].data[0].wind_valid&&
              many[0].soundings[0].data[0].u_mps==0,
              "original RDUPN valid calm wind lost");
        check(!many[1].soundings[2].data[1].wind_valid,
              "original RDUPN missing wind flag lost");
        const auto leap=sys_days{year{2024}/February/29};
        const auto leap_end=sys_days{year{2024}/March/1}+hours{23};
        fixture(f1,58424,leap,leap_end,{leap,leap+hours{12},leap+hours{24}});
        check(cteas::calmet::p6g::read_upper_dynamic(f1,58424).soundings.size()==3,
              "2024 leap-day upper input invalid");
        bool rejected=false;
        try{(void)cteas::calmet::p6g::read_upper_dynamic(f1,58425);}
        catch(const std::runtime_error&){rejected=true;}
        check(rejected,"upper station identity mismatch not rejected");
        rejected=false;
        try{(void)cteas::calmet::p6g::read_upper_station_set({f1,f1},{58424,58424});}
        catch(const std::runtime_error&){rejected=true;}
        check(rejected,"duplicate upper station deck not rejected");
        rejected=false;
        try{(void)cteas::calmet::p6g::read_upper_dynamic(f1,58424,2);}
        catch(const std::runtime_error&){rejected=true;}
        check(rejected,"max sounding limit ignored");
        fixture(f1,58424,leap,leap_end,{leap,leap+hours{12}},true);
        rejected=false;
        try{(void)cteas::calmet::p6g::read_upper_dynamic(f1,58424);}
        catch(const std::runtime_error&){rejected=true;}
        check(rejected,"invalid height passed RDUPN");
        fixture(f1,58424,leap,leap_end,{leap+hours{12},leap});
        rejected=false;
        try{(void)cteas::calmet::p6g::read_upper_dynamic(f1,58424);}
        catch(const std::runtime_error&){rejected=true;}
        check(rejected,"nonmonotonic sounding time not rejected");
        fixture(f1,58424,begin,finish,{a,c,d},false,false,true);
        rejected=false;
        try{(void)cteas::calmet::p6g::read_upper_dynamic(f1,58424);}
        catch(const std::runtime_error&){rejected=true;}
        check(rejected,"invalid 2023 Julian day 366 accepted");
        std::remove(f1.c_str());std::remove(f2.c_str());
        std::cout<<"PASS P6G_UPPER_TWO_STATIONS_CROSSYEAR_LEAP_FROZEN_PARITY\n";
        return 0;
    }catch(const std::exception& ex){
        std::remove(f1.c_str());std::remove(f2.c_str());
        std::cerr<<"P6G_UPPER_DYNAMIC_FAIL "<<ex.what()<<"\n";return 1;
    }
}
