#include "cteas/p6/observation_input_contract.hpp"
#include <chrono>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std::chrono;
using cteas::calmet::p6g::StationSet;
using cteas::calmet::p6g::SurfaceSeries;
using cteas::calmet::p6g::UpperSeries;
using cteas::calmet::p6g::bind_original_calmet_station_inputs;

static void check(bool good,const char* why) {
    if(!good)throw std::runtime_error(why);
}
static UpperSeries upper_station(int id,
                                 const std::vector<sys_seconds>& snapshots) {
    UpperSeries series;
    series.station_id=id;
    series.pstop_hpa=500;
    for(const auto t:snapshots){
        cteas::calmet::p6::UpperSounding v;
        v.station_id=id;v.start=t;v.end=t;
        series.soundings.push_back(v);
    }
    return series;
}
static bool rejected(const StationSet& deck,SurfaceSeries surf,
                     std::vector<UpperSeries> ups,
                     int minsep=3600,int maxsep=14*3600,
                     std::size_t capacity=2000000) {
    try{
        (void)bind_original_calmet_station_inputs(
            deck,surf,ups,minsep,maxsep,capacity);
    }catch(const std::invalid_argument&){return true;}
    return false;
}
int main(){
    try{
        const std::string deck_text=
            "! US2 = 'U2' 58425 514.000 3533.000 0 !\n"
            "! SS2 = 'S2' 58322 512.000 3533.000 0 12.0 !\n"
            "! US1 = 'U1' 58424 513.000 3532.000 0 !\n"
            "! SS1 = 'S1' 58321 511.000 3532.000 0 10.0 !\n";
        const auto deck=cteas::calmet::p6g::original_calmet_multi_station_deck(
            deck_text,510.885f,3531.269f,2,2);
        const auto begin=sys_days{year{2023}/December/31}+hours{22};
        SurfaceSeries surf;
        surf.begin=begin;surf.end=begin+hours{5};
        surf.station_ids={58321,58322};
        for(int i=0;i<5;++i) {
            cteas::calmet::p6g::SurfaceHour row;
            row.start=begin+hours{i};row.end=row.start+hours{1};
            row.by_station.resize(2);
            surf.hourly.push_back(row);
        }
        const auto jan1=sys_days{year{2024}/January/1};
        std::vector<UpperSeries> ups{
            upper_station(58424,{jan1-hours{12},jan1,jan1+hours{12}}),
            upper_station(58425,{jan1-hours{12},jan1,jan1+hours{12}})};
        const auto joined=bind_original_calmet_station_inputs(deck,surf,ups);
        check(joined.size()==5&&joined[0].upper.size()==2,
              "2 SURF x 2 UP hourly coverage");
        check(joined[0].end==jan1-hours{1}&&
              joined[0].upper[0].earlier==0&&
              joined[0].upper[0].later==1&&
              joined[0].upper[0].past_seconds==11*3600&&
              joined[0].upper[0].future_seconds==3600,
              "hour 23 first upper bracket");
        check(joined[1].end==jan1&&
              joined[1].upper[0].earlier==1&&
              joined[1].upper[0].later==2,
              "model hour exactly at observation uses next following sounding");
        check(joined[4].upper[1].span_seconds==12*3600,
              "multi-upper independent PREPDI bracket duration");
        auto bad_surface=surf;
        bad_surface.station_ids={58322,58321};
        check(rejected(deck,bad_surface,ups),
              "SURF station order mismatch should fail");
        auto bad_upper=ups;
        bad_upper[0].station_id=58425;
        check(rejected(deck,surf,bad_upper),
              "UP station order mismatch should fail");
        auto no_future=ups;
        no_future[1].soundings.pop_back();
        check(rejected(deck,surf,no_future),
              "upper future missing on later model hour should fail");
        auto sparse=ups;
        sparse[1].soundings={
            upper_station(58425,{jan1-hours{16},jan1+hours{16}}).soundings[0],
            upper_station(58425,{jan1-hours{16},jan1+hours{16}}).soundings[1]};
        check(rejected(deck,surf,sparse),
              "upper separation exceeds 14-hour policy");
        check(rejected(deck,surf,ups,3600,14*3600,5),
              "bounded station-hour budget was ignored");
        bad_surface=surf;
        bad_surface.hourly[2].end+=hours{1};
        check(rejected(deck,bad_surface,ups),
              "noncontinuous or nonhourly surface row passed");
        std::cout<<"PASS P6G_MULTI_SURF_UP_HOURLY_BRACKETS_CROSSYEAR_INPUT_ONLY\n";
        return 0;
    }catch(const std::exception& ex){
        std::cerr<<"P6G_INPUT_BRACKET_FAIL "<<ex.what()<<"\n";
        return 1;
    }
}
