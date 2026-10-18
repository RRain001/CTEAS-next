#pragma once
// P6G G7: CALMET SURF.DAT v2.1 (IFORMS=2) dynamic, multi-station,
// arbitrary UTC hourly window. Strict RDHD/RDSN formatted-input subset.
// DO NOT replace the validated frozen read_surface_2022 or bypass its
// integration tests until original CALMET multi-site parity is complete.
#include "cteas/p6/read_surface.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
namespace frozen = cteas::calmet::p6;

struct SurfaceHour {
    std::chrono::sys_seconds start,end;
    // Indexed in SURF.DAT station-ID header order, corresponding to met.inp SSn.
    std::vector<frozen::SurfaceObserved> by_station;
};
struct SurfaceSeries {
    std::vector<int> station_ids;
    std::chrono::sys_seconds begin,end;
    std::vector<SurfaceHour> hourly;
};

inline void require_surf(bool condition,const char* reason) {
    if(!condition)throw std::runtime_error(reason);
}
inline std::string line_surf(std::istream& input,const char* error) {
    std::string result;
    require_surf(static_cast<bool>(std::getline(input,result)),error);
    return result;
}
inline int julian_int(const std::string& value) {
    std::size_t used=0;
    int n=0;
    try{n=std::stoi(value,&used);}
    catch(const std::exception&){throw std::runtime_error("invalid SURF timestamp field");}
    require_surf(used==value.size(),"SURF timestamp has trailing characters");
    return n;
}
inline std::chrono::sys_seconds utc_julian(int y,int j,int h,int s,
                                            bool allow_midnight_24) {
    using namespace std::chrono;
    require_surf(y>=1900&&y<=2100&&j>=1&&h>=0&&h<=24&&s==0,
                 "SURF UTC year/day/hour/second invalid");
    require_surf(h!=24||allow_midnight_24,
                 "SURF interval start cannot use hour 24");
    const auto year_begin=sys_days{year{y}/January/1};
    const auto next_begin=sys_days{year{y+1}/January/1};
    require_surf(j<=int((next_begin-year_begin).count()),"SURF leap-year Julian day invalid");
    return year_begin+days{j-1}+hours{h};
}
inline std::pair<std::chrono::sys_seconds,std::chrono::sys_seconds>
read_surf_bounds(const std::string& row,bool header=false) {
    std::istringstream in(row);
    std::string words[8];
    for(auto& word:words)
        require_surf(static_cast<bool>(in>>word),"SURF time fields missing");
    std::string excess;
    // Header ends with a station count; caller handles it.
    if(!header)require_surf(!(in>>excess),"SURF time record contains surplus tokens");
    auto begin=utc_julian(julian_int(words[0]),julian_int(words[1]),
                          julian_int(words[2]),julian_int(words[3]),false);
    auto end=utc_julian(julian_int(words[4]),julian_int(words[5]),
                        julian_int(words[6]),julian_int(words[7]),true);
    require_surf(begin<end,"SURF time interval reversed or empty");
    return {begin,end};
}
inline frozen::SurfaceObserved parse_surface_fields(const std::string& row) {
    std::istringstream in(row);
    double ws,wd,tmp,pre;
    int cei,cloud,rh,code;
    require_surf(static_cast<bool>(in>>ws>>wd>>cei>>cloud>>tmp>>rh>>pre>>code),
                 "SURF station hourly observation missing fields");
    std::string extra;
    require_surf(!(in>>extra),"SURF station hourly observation has extra fields");
    for(const auto x:{ws,wd,tmp,pre})
        require_surf(std::isfinite(x)&&std::abs(x)<=9999.99,
                     "SURF observation outside supported real range");
    frozen::SurfaceObserved o;
    o.wind_speed_mps=static_cast<float>(ws);
    o.wind_direction_deg=static_cast<float>(wd);
    o.ceiling_hundreds_ft=cei;
    o.opaque_cloud_tenths=cloud;
    o.temperature_k=static_cast<float>(tmp);
    o.humidity_pct=rh;
    o.pressure_mb=static_cast<float>(pre);
    o.precip_code=code;
    // Flags match the selected frozen RDSN input rule. CALMET wind calm = 0
    // is valid, IPCODE=9999 is MISSING, not "zero precipitation".
    o.wind_valid=ws<9998.0&&wd<9998.0&&ws>=0&&wd>=0&&wd<=360;
    o.temperature_valid=tmp<9998.0&&tmp>0;
    o.humidity_valid=rh<9998&&rh>=0&&rh<=100;
    o.pressure_valid=pre<9998.0&&pre>0;
    o.ceiling_valid=cei<9998&&cei>=0;
    o.cloud_valid=cloud<9998&&cloud>=0&&cloud<=10;
    o.precipitation_code_valid=code<9998&&code>=0;
    return o;
}
inline SurfaceSeries read_surface_dynamic(
    const std::string& path,const std::vector<int>& declared_station_ids={},
    std::size_t max_hours=200000,
    std::size_t max_stations=static_cast<std::size_t>(std::numeric_limits<int>::max()),
    std::size_t max_hour_station_slots=2000000) {
    using namespace std::chrono;
    require_surf(max_hours>=1&&max_stations>=1&&max_hour_station_slots>=1,
                 "SURF bounds cannot be zero");
    std::ifstream in(path);
    require_surf(static_cast<bool>(in),"cannot open P6G SURF.DAT");
    const auto first=line_surf(in,"missing SURF.DAT identity");
    require_surf(first.size()>=32&&
                 frozen::surf_trim(first.substr(0,16))=="SURF.DAT"&&
                 frozen::surf_trim(first.substr(16,16))=="2.1",
                 "P6G accepts only formatted SURF.DAT 2.1");
    {
        std::istringstream cc(line_surf(in,"SURF comment count absent"));
        int n=0;std::string extra;
        require_surf(static_cast<bool>(cc>>n)&&!(cc>>extra)&&n>=0&&n<=10000,
                     "malformed SURF comment count");
        for(int k=0;k<n;++k)(void)line_surf(in,"truncated SURF header comment");
    }
    require_surf(frozen::surf_trim(line_surf(in,"SURF PMAP absent"))=="NONE",
                 "unsupported SURF PMAP");
    require_surf(frozen::surf_trim(line_surf(in,"SURF time zone absent"))=="UTC+0000",
                 "unsupported SURF time zone");
    const auto metadata=line_surf(in,"missing SURF time bounds/station count");
    const auto bounds=read_surf_bounds(metadata,true);
    SurfaceSeries result;
    result.begin=bounds.first;result.end=bounds.second;
    int station_count=0;
    {
        std::istringstream scan(metadata);
        std::string value;
        for(int i=0;i<8;++i)require_surf(static_cast<bool>(scan>>value),
                                          "SURF metadata timestamp missing");
        std::string token,extra;
        require_surf(static_cast<bool>(scan>>token)&&!(scan>>extra),
                     "SURF metadata station count malformed");
        station_count=julian_int(token);
    }
    require_surf(station_count>0&&static_cast<std::size_t>(station_count)<=max_stations,
                 "SURF station count exceeds permitted bounds");
    require_surf(duration_cast<seconds>(result.end-result.begin).count()%3600==0,
                 "SURF header window must contain whole UTC hours");
    const auto n_hours=static_cast<std::size_t>(
        duration_cast<hours>(result.end-result.begin).count());
    require_surf(n_hours>=1&&n_hours<=max_hours,"SURF window exceeds hour budget");
    require_surf(n_hours<=max_hour_station_slots/
                 static_cast<std::size_t>(station_count),
                 "SURF hour x station allocation exceeds safe cell budget");
    std::set<int> ids;
    for(int n=0;n<station_count;++n) {
        std::istringstream scan(line_surf(in,"SURF station ID row missing"));
        int id=0;std::string extra;
        require_surf(static_cast<bool>(scan>>id)&&!(scan>>extra)&&id>0&&
                     ids.insert(id).second,
                     "SURF station IDs must be unique positive integers");
        result.station_ids.push_back(id);
    }
    if(!declared_station_ids.empty())
        require_surf(result.station_ids==declared_station_ids,
                     "SURF station IDs/order differ from met.inp SSn");
    result.hourly.reserve(n_hours);
    auto expected=result.begin;
    for(std::size_t t=0;t<n_hours;++t) {
        const auto hour_bounds=read_surf_bounds(
            line_surf(in,"SURF hourly time record missing"));
        require_surf(hour_bounds.first==expected&&
                     hour_bounds.second-hour_bounds.first==hours{1},
                     "SURF gap/overlap/nonhourly or reordered time record");
        SurfaceHour hour;
        hour.start=hour_bounds.first;hour.end=hour_bounds.second;
        hour.by_station.reserve(result.station_ids.size());
        for(std::size_t s=0;s<result.station_ids.size();++s)
            hour.by_station.push_back(parse_surface_fields(
                line_surf(in,"SURF truncated station observations")));
        result.hourly.push_back(std::move(hour));
        expected=hour_bounds.second;
    }
    require_surf(expected==result.end,"SURF final endpoint differs from header");
    std::string extra;
    while(std::getline(in,extra))
        require_surf(frozen::surf_trim(extra).empty(),"SURF unexpected trailing records");
    return result;
}
} // namespace cteas::calmet::p6g
