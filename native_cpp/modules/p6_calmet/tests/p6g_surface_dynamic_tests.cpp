#include "cteas/p6/read_surface_dynamic.hpp"
#include "cteas/p6/read_surface.hpp"
#include <chrono>
#include <cmath>
#include <cstdio>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std::chrono;
using cteas::calmet::p6g::read_surface_dynamic;

static void check(bool good,const char* reason) {
    if(!good)throw std::runtime_error(reason);
}
static int doy(sys_seconds t) {
    const auto d=floor<days>(t);
    const auto yearpart=year_month_day{d};
    return static_cast<int>((d-sys_days{yearpart.year()/January/1}).count())+1;
}
static void stamp(std::ostream& out,sys_seconds t,bool is_end=false) {
    const bool hour24=is_end&&t==floor<days>(t);
    if(hour24)t-=hours{1};
    const year_month_day ymd{floor<days>(t)};
    const auto hour=hour24?24:static_cast<int>(
        duration_cast<hours>(t-floor<days>(t)).count());
    out<<int(ymd.year())<<" "<<doy(t)<<" "<<hour<<" 0";
}
static void field(std::ostream& out,int station,int hour) {
    if(station==0&&hour==0)
        out<<"0.0 0.0 9999 0 280 50 1013.0 9999\n";
    else if(station==1&&hour==1)
        out<<"9999 9999 9999 9999 9999 9999 9999 9999\n";
    else
        out<<3.0+station<<" 150.0 722 5 285 70 1008.1 0\n";
}
static void fixture(const std::string& file,sys_seconds begin,
                    int n_hours,const std::vector<int>& ids,
                    int corrupt_time=-1,bool append_extra=false) {
    const auto end=begin+hours{n_hours};
    std::ofstream out(file);
    check(bool(out),"cannot create SURF fixture");
    out<<"SURF.DAT        2.1             Hour Start and End Times with Seconds\n"
       <<"   1\nP6G generated original format\nNONE    \nUTC+0000\n";
    stamp(out,begin);out<<" ";stamp(out,end,true);out<<" "<<ids.size()<<"\n";
    for(const auto id:ids)out<<id<<"\n";
    for(int n=0;n<n_hours;++n) {
        auto at=begin+hours{n};
        stamp(out,at);out<<" ";
        if(n==corrupt_time)stamp(out,at+hours{2},true);
        else stamp(out,at+hours{1},true);
        out<<"\n";
        for(std::size_t s=0;s<ids.size();++s)field(out,static_cast<int>(s),n);
    }
    if(append_extra)out<<"UNEXPECTED RECORD\n";
}
static void equal_observation(const cteas::calmet::p6::SurfaceObserved& a,
                              const cteas::calmet::p6::SurfaceObserved& b) {
    check(a.wind_speed_mps==b.wind_speed_mps&&
          a.wind_direction_deg==b.wind_direction_deg&&
          a.ceiling_hundreds_ft==b.ceiling_hundreds_ft&&
          a.opaque_cloud_tenths==b.opaque_cloud_tenths&&
          a.temperature_k==b.temperature_k&&
          a.pressure_mb==b.pressure_mb&&
          a.humidity_pct==b.humidity_pct&&a.precip_code==b.precip_code&&
          a.wind_valid==b.wind_valid&&a.temperature_valid==b.temperature_valid&&
          a.humidity_valid==b.humidity_valid&&a.pressure_valid==b.pressure_valid&&
          a.ceiling_valid==b.ceiling_valid&&a.cloud_valid==b.cloud_valid&&
          a.precipitation_code_valid==b.precipitation_code_valid,
          "frozen single-station value/validity mismatch");
}
int main() {
    const std::string file="p6g_surface_dynamic_test.dat";
    try {
        const auto frozen_begin=sys_days{year{2022}/January/1};
        fixture(file,frozen_begin,143,{58321});
        const auto original=cteas::calmet::p6::read_surface_2022(file);
        const auto dynamic=read_surface_dynamic(file,{58321});
        check(dynamic.hourly.size()==143&&dynamic.station_ids[0]==58321,
              "frozen 143h dynamic records/count");
        for(std::size_t n=0;n<dynamic.hourly.size();++n) {
            check(dynamic.hourly[n].start==original.hourly[n].start&&
                  dynamic.hourly[n].end==original.hourly[n].end,
                  "single-station frozen time mismatch");
            equal_observation(dynamic.hourly[n].by_station[0],
                              original.hourly[n].obs);
        }
        // #84: 2024 genuine-data case needs a single virtual station and
        // correct (2024-02-28 00, 2024-03-01 00] hour-ending chronology.
        const auto single_leap_begin=sys_days{year{2024}/February/28};
        fixture(file,single_leap_begin,48,{471520});
        const auto single_leap=read_surface_dynamic(file,{471520},48,1,48);
        check(single_leap.hourly.size()==48&&single_leap.station_ids.size()==1,
              "single virtual-station 48h preflight cardinality");
        check(single_leap.hourly[24].start==sys_days{year{2024}/February/29}&&
              single_leap.hourly[47].end==sys_days{year{2024}/March/1},
              "2024 Feb29 single-station hour-ending chronology");
        const auto cross_begin=sys_days{year{2023}/December/31}+hours{22};
        fixture(file,cross_begin,5,{58321,58322,58323});
        const auto cross=read_surface_dynamic(file,{58321,58322,58323});
        check(cross.hourly.size()==5&&cross.station_ids.size()==3,
              "3-station 2023/24 surface sequence");
        check(cross.hourly[1].end==sys_days{year{2024}/January/1},
              "year-boundary h24 midnight timestamp");
        check(cross.hourly[0].by_station[0].wind_valid&&
              cross.hourly[0].by_station[0].wind_speed_mps==0.0f,
              "zero calm wind must remain valid");
        check(!cross.hourly[0].by_station[0].precipitation_code_valid,
              "missing precipitation must not be counted as dry");
        check(!cross.hourly[1].by_station[1].wind_valid,
              "multi-station source missing mask");
        check(cross.hourly[2].by_station[2].wind_valid&&
              cross.hourly[2].by_station[2].wind_speed_mps==5.0f,
              "multi-station ID column mapping");
        const auto leap_begin=sys_days{year{2024}/February/29}+hours{22};
        fixture(file,leap_begin,4,{58321,58322});
        const auto leap=read_surface_dynamic(file,{58321,58322});
        check(leap.hourly.size()==4&&
              leap.hourly[2].start==sys_days{year{2024}/March/1},
              "leap-year February day 366 chronology");
        // Mismatched station IDs or order must be rejected before execution.
        bool failed=false;
        try{(void)read_surface_dynamic(file,{58322,58321});}
        catch(const std::runtime_error&){failed=true;}
        check(failed,"met.inp station order mismatch accepted");
        fixture(file,cross_begin,5,{58321,58321});
        failed=false;
        try{(void)read_surface_dynamic(file);}
        catch(const std::runtime_error&){failed=true;}
        check(failed,"duplicate SURF station ID accepted");
        fixture(file,cross_begin,5,{58321,58322},2);
        failed=false;
        try{(void)read_surface_dynamic(file);}
        catch(const std::runtime_error&){failed=true;}
        check(failed,"misaligned SURF interval accepted");
        fixture(file,cross_begin,5,{58321,58322},-1,true);
        failed=false;
        try{(void)read_surface_dynamic(file);}
        catch(const std::runtime_error&){failed=true;}
        check(failed,"surplus SURF record accepted");
        fixture(file,cross_begin,5,{58321,58322});
        failed=false;
        try{(void)read_surface_dynamic(file,{},4);}
        catch(const std::runtime_error&){failed=true;}
        check(failed,"SURF maximum hourly interval allocation not enforced");
        failed=false;
        try{(void)read_surface_dynamic(file,{},5,1);}
        catch(const std::runtime_error&){failed=true;}
        check(failed,"SURF max station allocation not enforced");
        failed=false;
        try{(void)read_surface_dynamic(file,{},5,2,9);}
        catch(const std::runtime_error&){failed=true;}
        check(failed,"SURF combined 5 hour x 2 station budget ignored");
        std::remove(file.c_str());
        std::cout<<"PASS P6G_MULTISTATION_MULTIYEAR_SURF_FORMAT_AND_143H_FROZEN_FIELDS\n";
        return 0;
    }catch(const std::exception& e) {
        std::remove(file.c_str());
        std::cerr<<"P6G_SURF_DYNAMIC_FAIL "<<e.what()<<'\n';
        return 1;
    }
}
