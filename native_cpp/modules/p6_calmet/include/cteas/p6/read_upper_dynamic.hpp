#pragma once
// P6G G7b: original READ62 UP.DAT 2.1, source-file per upper station.
// Dynamic station IDs, years, soundings and input hours. Frozen P6C reader
// is unchanged; this adapter does not complete CALMET AA/BB COMP execution.
#include "cteas/p6/read_upper.hpp"
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
namespace frozen_upper = cteas::calmet::p6;
struct UpperSeries {
    int station_id{};
    float pstop_hpa{};
    std::chrono::sys_seconds begin,end;
    std::vector<frozen_upper::UpperSounding> soundings;
};
inline void require_upper(bool good,const char* reason) {
    if(!good)throw std::runtime_error(reason);
}
inline std::chrono::sys_seconds upper_utc_julian(int yr,int jul,int hr,int sec) {
    using namespace std::chrono;
    require_upper(yr>=1900&&yr<=2100&&jul>=1&&hr>=0&&hr<=24&&sec==0,
                  "UP.DAT invalid UTC control time");
    const auto first=sys_days{year{yr}/January/1};
    const auto last=sys_days{year{yr+1}/January/1};
    require_upper(jul<=int((last-first).count()),
                  "UP.DAT invalid leap-year Julian day");
    return first+days{jul-1}+hours{hr};
}
inline std::chrono::sys_seconds upper_utc_ymd(
    int yr,int mon,int day,int hr,int sec) {
    using namespace std::chrono;
    const year_month_day ymd{year{yr},month{static_cast<unsigned>(mon)},
                             std::chrono::day{static_cast<unsigned>(day)}};
    require_upper(ymd.ok()&&yr>=1900&&yr<=2100&&hr>=0&&hr<=24&&sec==0,
                  "UP.DAT invalid snapshot UTC time");
    return sys_days{ymd}+hours{hr};
}
inline UpperSeries read_upper_dynamic(
    const std::string& path,int expected_station,
    std::size_t max_soundings=100000,int max_padding_hours=24,
    bool allow_validated_archive_tail=false) {
    using namespace std::chrono;
    require_upper(expected_station>0&&max_soundings>0&&
                  max_padding_hours>=0&&max_padding_hours<=48,
                  "UP.DAT upper-input bounds invalid");
    std::ifstream input(path);
    require_upper(static_cast<bool>(input),"UP.DAT not found");
    const auto first=frozen_upper::up_line(input,"UP.DAT identity absent");
    require_upper(first.size()>=32&&
                  frozen_upper::up_strip(first.substr(0,16))=="UP.DAT"&&
                  frozen_upper::up_strip(first.substr(16,16))=="2.1",
                  "UP.DAT 2.1 formatted input required");
    const int ncomment=frozen_upper::up_int(
        frozen_upper::up_line(input,"UP.DAT comments absent"));
    require_upper(ncomment>=0&&ncomment<=10000,"UP.DAT comment count invalid");
    for(int n=0;n<ncomment;++n)
        (void)frozen_upper::up_line(input,"UP.DAT comments truncated");
    require_upper(frozen_upper::up_strip(
        frozen_upper::up_line(input,"UP.DAT projection absent"))=="NONE",
        "UP.DAT projection not supported");
    require_upper(frozen_upper::up_strip(
        frozen_upper::up_line(input,"UP.DAT UTC absent"))=="UTC+0000",
        "UP.DAT time zone not UTC");
    UpperSeries out;
    out.station_id=expected_station;
    {
        std::istringstream meta(frozen_upper::up_line(
            input,"UP.DAT date/PSTOP/JDAT/IFMT metadata missing"));
        int by,bj,bh,bs,ey,ej,eh,es,jdat,ifmt;
        std::string extra;
        float top{};
        require_upper(static_cast<bool>(meta>>by>>bj>>bh>>bs>>
                      ey>>ej>>eh>>es>>top>>jdat>>ifmt)&&!(meta>>extra),
                      "UP.DAT metadata invalid or extra tokens");
        out.begin=upper_utc_julian(by,bj,bh,bs);
        out.end=upper_utc_julian(ey,ej,eh,es);
        require_upper(out.begin<out.end&&
                      jdat==2&&ifmt==1&&std::isfinite(top)&&
                      top>0.f&&top<=1500.f,
                      "UP.DAT time window or READ62 input control unsupported");
        out.pstop_hpa=top;
    }
    {
        std::istringstream flags(frozen_upper::up_line(
            input,"UP.DAT four quality switches absent"));
        std::string token,extra;
        for(int i=0;i<4;++i){
            require_upper(static_cast<bool>(flags>>token)&&token=="F",
                          "UP.DAT quality flags outside selected READ62 scope");
        }
        require_upper(!(flags>>extra),"UP.DAT quality flags extra token");
    }
    sys_seconds previous{};
    std::string line;
    while(std::getline(input,line)){
        if(frozen_upper::up_strip(line).empty())continue;
        require_upper(line.find("->->->")==std::string::npos,
                      "UP.DAT unresolved P4 warning line");
        std::istringstream record(line);
        int tag,station,by,bm,bd,bh,bs,ey,em,ed,eh,es,nraw,levels;
        std::string extra;
        require_upper(static_cast<bool>(record>>tag>>station>>
                      by>>bm>>bd>>bh>>bs>>ey>>em>>ed>>eh>>es>>nraw>>levels)&&
                      !(record>>extra),
                      "UP.DAT 6201 sounding record invalid");
        require_upper(tag==6201&&station==expected_station&&nraw>=levels&&
                      levels>=1&&levels<=99,
                      "UP.DAT 6201 station/level count invalid");
        frozen_upper::UpperSounding sounding;
        sounding.station_id=station;
        sounding.levels_raw=nraw;sounding.levels=levels;
        sounding.start=upper_utc_ymd(by,bm,bd,bh,bs);
        sounding.end=upper_utc_ymd(ey,em,ed,eh,es);
        require_upper(sounding.start==sounding.end,
                      "UP.DAT only instantaneous soundings supported");
        // READ62 may produce a full annual sounding archive with a shorter
        // CALMET run header (C1 2022: 143h header, 731 valid 00/12 records
        // through 2023-01-01). G19 alone opts into a *bounded trailing*
        // archive: no fabricated data, early records or relaxed ordering.
        // Full original Fortran numerical compatibility is NOT established.
        const bool ordinary_window=
            sounding.end>=out.begin-hours{max_padding_hours}&&
            sounding.end<=out.end+hours{max_padding_hours};
        const bool archive_tail=
            allow_validated_archive_tail &&
            sounding.end>out.end+hours{max_padding_hours} &&
            sounding.end<=out.end+hours{24*366};
        require_upper(ordinary_window||archive_tail,
                      "UP.DAT sounding outside bounded header interval");
        if(!out.soundings.empty())
            require_upper(sounding.end>previous,
                          "UP.DAT observations must increase strictly by time");
        previous=sounding.end;
        sounding.data.reserve(static_cast<std::size_t>(levels));
        while(static_cast<int>(sounding.data.size())<levels){
            const auto heights=frozen_upper::up_line(
                input,"UP.DAT missing fixed-width level records");
            require_upper(!heights.empty()&&heights.size()%29==0&&
                          heights.size()<=116,
                          "UP.DAT fixed-width 29-character RDUPN record malformed");
            const auto count=static_cast<int>(heights.size()/29);
            require_upper(static_cast<int>(sounding.data.size())+count<=levels,
                          "UP.DAT extra level group");
            for(int i=0;i<count;++i)
                sounding.data.push_back(
                    frozen_upper::up_parse_fixed_level(heights.substr(
                        static_cast<std::size_t>(i)*29,29)));
        }
        frozen_upper::up_convert_sounding(sounding);
        out.soundings.push_back(std::move(sounding));
        require_upper(out.soundings.size()<=max_soundings,
                      "UP.DAT sounding count exceeds allocation limit");
    }
    require_upper(!out.soundings.empty(),"UP.DAT contains no usable soundings");
    return out;
}
inline std::vector<UpperSeries> read_upper_station_set(
    const std::vector<std::string>& files,
    const std::vector<int>& deck_station_ids,
    std::size_t max_soundings_per_station=100000,
    bool allow_validated_archive_tail=false) {
    // No arbitrary station-number ceiling: one original-format UP file per
    // source US; hour and sounding allocation are independently bounded.
    require_upper(!files.empty()&&files.size()==deck_station_ids.size(),
                  "UP.DAT station set size/identity mismatch");
    std::set<int> seen;
    std::vector<UpperSeries> result;
    result.reserve(files.size());
    for(std::size_t i=0;i<files.size();++i){
        require_upper(seen.insert(deck_station_ids[i]).second,
                      "UP.DAT duplicate upper-air station in deck");
        result.push_back(read_upper_dynamic(files[i],deck_station_ids[i],
                                           max_soundings_per_station,24,
                                           allow_validated_archive_tail));
    }
    return result;
}
} // namespace cteas::calmet::p6g
