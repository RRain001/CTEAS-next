#pragma once
// Scoped CALMET 6.5.0 UP.DAT v2.1 RDHDU/RDUPN (NOT legacy RDUP).
// Vendor calmet.for RDHDU L15222-15280 and RDUPN L24119-24287.
// Only P4 READ62 (JDAT=2, IFMT=1, PMAP=NONE, UTC+0000) generated
// real Hefei 2022 UPPER-AIR data. No source-data interpolation.
// Rejects silent mismatch in station ID, header, count, time sequence,
// malformed fixed-width level field, altitude and missingness.
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6 {
inline void up_require(bool yes,const char* message) {
    if(!yes)throw std::runtime_error(message);
}
inline std::string up_strip(const std::string& s) {
    auto a=s.find_first_not_of(" \t\n\r");
    if(a==std::string::npos)return {};
    return s.substr(a,s.find_last_not_of(" \t\n\r")-a+1);
}
inline std::string up_line(std::istream& in,const char* message) {
    std::string result;
    up_require(static_cast<bool>(std::getline(in,result)),message);
    return result;
}
inline float up_real(const std::string& token) {
    std::string t=up_strip(token);
    up_require(!t.empty(),"UP.DAT missing numeric cell");
    std::size_t n=0;
    float result=0;
    try {result=std::stof(t,&n);}
    catch(const std::exception&) {throw std::runtime_error("UP.DAT nonnumeric cell");}
    up_require(n==t.size()&&std::isfinite(result),"UP.DAT invalid real cell");
    return result;
}
inline int up_int(const std::string& token) {
    std::string t=up_strip(token);
    up_require(!t.empty(),"UP.DAT missing integer cell");
    std::size_t n=0;
    int result=0;
    try{result=std::stoi(t,&n);}
    catch(const std::exception&){throw std::runtime_error("UP.DAT invalid integer cell");}
    up_require(n==t.size(),"UP.DAT trailing characters in integer");
    return result;
}
inline std::chrono::sys_seconds up_timestamp(
    int year,int month,int day,int hour,int seconds) {
    using namespace std::chrono;
    const year_month_day date{std::chrono::year{year},
        std::chrono::month{static_cast<unsigned>(month)},
        std::chrono::day{static_cast<unsigned>(day)}};
    up_require(date.ok()&&year>=2022&&year<=2023 &&
               hour>=0&&hour<=24&&seconds>=0&&seconds<=3600,
               "UP.DAT invalid timestamp or non-study year");
    return sys_days{date}+hours{hour}+std::chrono::seconds{seconds};
}
struct UpperLevel {
    float pressure_hpa{},height_msl{},temperature_k{},wd_deg{},ws_mps{};
    float height_lgl_m{},u_mps{},v_mps{};
    bool height_valid{},temperature_valid{},wind_valid{};
};
struct UpperSounding {
    int station_id=0;
    std::chrono::sys_seconds start,end;
    int levels_raw=0,levels=0;
    std::vector<UpperLevel> data;
};
struct Upper2022 {
    int station_id=0;
    float pstop_hpa{};
    std::vector<UpperSounding> soundings;
};
inline UpperLevel up_parse_fixed_level(const std::string& s) {
    // RDUPN Fortran FORMAT(4(3x,f6.1,1x,f5.0,1x,f5.1,1x,f3.0,1x,f3.0))
    up_require(s.size()==29,"UP.DAT slash level group not 29 characters");
    up_require(s[9]=='/'&&s[15]=='/'&&s[21]=='/'&&s[25]=='/',
               "UP.DAT malformed original RDUPN slash delimiters");
    UpperLevel v;
    v.pressure_hpa=up_real(s.substr(3,6));
    v.height_msl=up_real(s.substr(10,5));
    v.temperature_k=up_real(s.substr(16,5));
    v.wd_deg=up_real(s.substr(22,3));
    v.ws_mps=up_real(s.substr(26,3));
    v.height_valid=v.height_msl<9998.0f;
    v.temperature_valid=v.temperature_k<998.99f;
    v.wind_valid=v.wd_deg<998.99f&&v.ws_mps<998.99f;
    return v;
}
inline void up_convert_sounding(UpperSounding& s) {
    up_require(!s.data.empty(),"UP.DAT no sounding levels");
    const float base=s.data.front().height_msl;  // RDUPN ZB=ZLAA(1)
    for(auto& layer:s.data){
        // In selected input, original RDUPN with ICONVRT=1 would STOP
        // if any level height >= 9998. Reject rather than invent altitude.
        up_require(layer.height_valid,"UP.DAT missing level height (RDUPN fails)");
        layer.height_lgl_m=layer.height_msl-base;
        if(layer.wind_valid) {
            const float dir=0.0174533f*layer.wd_deg;
            layer.u_mps=-layer.ws_mps*std::sin(dir);
            layer.v_mps=-layer.ws_mps*std::cos(dir);
        } else {
            layer.u_mps=999.0f;layer.v_mps=999.0f;
        }
    }
}
inline Upper2022 read_upper_2022(const std::string& path,int expected_station) {
    using namespace std::chrono;
    up_require(expected_station>0,"UP.DAT expected station ID absent");
    std::ifstream in(path);
    up_require(static_cast<bool>(in),"UP.DAT file not found");
    std::string header=up_line(in,"UP.DAT identity absent");
    up_require(header.size()>=32 &&
       up_strip(header.substr(0,16))=="UP.DAT" &&
       up_strip(header.substr(16,16))=="2.1","only upper data version 2.1");
    const int ncomment=up_int(up_line(in,"UP.DAT comment count absent"));
    up_require(ncomment>=0&&ncomment<=10000,"UP.DAT comment count invalid");
    for(int i=0;i<ncomment;i++)(void)up_line(in,"UP.DAT missing comment");
    up_require(up_strip(up_line(in,"UP.DAT projection absent"))=="NONE",
               "unsupported UP.DAT projection");
    up_require(up_strip(up_line(in,"UP.DAT UTC zone absent"))=="UTC+0000",
               "UP.DAT time zone must be UTC+0000");
    Upper2022 out;out.station_id=expected_station;
    {
        std::istringstream row(up_line(in,"UP.DAT time metadata absent"));
        int yb,jb,hb,sb,ye,je,he,se,jdat,ifmt;
        float top;
        up_require(static_cast<bool>(row>>yb>>jb>>hb>>sb>>
                          ye>>je>>he>>se>>top>>jdat>>ifmt),
                    "UP.DAT time control malformed");
        up_require(yb==2022&&ye==2022&&jb==1&&hb==0&&sb==0 &&
                   je==6&&he==23&&se==0,"UP.DAT not matching 2022 143h reference");
        up_require(std::abs(top-500.0f)<0.001f&&jdat==2&&ifmt==1,
                   "unsupported original READ62 control JDAT/IFMT/PSTOP");
        out.pstop_hpa=top;
    }
    {
        std::istringstream flags(up_line(in,"UP.DAT quality switches missing"));
        std::array<std::string,4> values;
        for(auto& val:values)up_require(static_cast<bool>(flags>>val),
                                       "UP.DAT missing switch");
        for(const auto& val:values)
            up_require(val=="F","selected upstream quality flags not F");
    }
    sys_seconds previous{};
    while(true) {
        std::string line;
        if(!std::getline(in,line))break;
        if(up_strip(line).empty())continue;
        up_require(line.find("->->->")==std::string::npos,
                   "P4 warning survived final normalization");
        std::istringstream row(line);
        int tag=0,station=0,y1=0,m1=0,d1=0,h1=0,sec1=0,
            y2=0,m2=0,d2=0,h2=0,sec2=0,nraw=0,n=0;
        up_require(static_cast<bool>(row>>tag>>station>>y1>>m1>>d1>>h1>>sec1>>
                    y2>>m2>>d2>>h2>>sec2>>nraw>>n),
                   "malformed UP.DAT 6201 sounding header");
        std::string extra;
        up_require(!(row>>extra),"UP.DAT unexpected 6201 fields");
        up_require(tag==6201&&station==expected_station&&nraw>=n&&n>=1&&n<=99,
                   "UP.DAT sounding identity/level count not selected scope");
        UpperSounding entry;
        entry.station_id=station;entry.levels_raw=nraw;entry.levels=n;
        entry.start=up_timestamp(y1,m1,d1,h1,sec1);
        entry.end=up_timestamp(y2,m2,d2,h2,sec2);
        up_require(entry.start==entry.end,"UP.DAT 2.1 expected instantaneous snapshot");
        if(!out.soundings.empty())
            up_require(entry.end>previous,"UP.DAT sounding times not increasing");
        previous=entry.end;
        entry.data.reserve(static_cast<std::size_t>(n));
        while(static_cast<int>(entry.data.size())<n) {
            std::string record=up_line(in,"UP.DAT missing sounding level line");
            up_require(record.size()%29==0&&record.size()<=116,
                       "UP.DAT level line violates 29-character RDUPN format");
            const int groups=static_cast<int>(record.size()/29);
            up_require(groups>0&&static_cast<int>(entry.data.size())+groups<=n,
                       "UP.DAT level group count inconsistent");
            for(int k=0;k<groups;k++)
                entry.data.push_back(up_parse_fixed_level(record.substr(
                    static_cast<std::size_t>(k*29),29)));
        }
        up_convert_sounding(entry);
        out.soundings.push_back(std::move(entry));
        up_require(out.soundings.size()<=1000,"unexpected UP.DAT sounding volume");
    }
    up_require(!out.soundings.empty(),"UP.DAT empty");
    up_require(out.soundings.front().end<=sys_days{year{2022}/January/1}+hours{12},
               "UP.DAT missing first usable sounding");
    up_require(out.soundings.back().end>=sys_days{year{2022}/January/6}+hours{12},
               "UP.DAT missing end-window sounding");
    return out;
}
} // namespace cteas::calmet::p6
