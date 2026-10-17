#pragma once
// Independent C++20 READ62 JDAT=2, IFMT=1 output for the validated legacy defaults.
// Legacy FSL reader stays in p4_read62.hpp. No Fortran or engine/preprocess changes.
#include "cteas/met_input/p4_read62.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <ostream>
#include <sstream>
#include <string>
#include <vector>

namespace cteas::met_input::p4 {
struct UpdatOptions {
    Timestamp begin, end;
    double pstop_hpa=500.0;
    int station_wmo=0; // FSL ID explicitly supplied by caller; no guessed station geography.
};
struct UpdatStats {
    std::size_t input=0,written=0,skipped_fewer_than_two=0,levels_written=0;
    std::size_t warnings=0;
};
inline std::string fixed_num(double value,int width,int decimals) {
    std::ostringstream o;
    o<<std::fixed<<std::setprecision(decimals)<<std::setw(width)<<value;
    return o.str();
}
inline std::string fixed_int(int value,int width) {
    std::ostringstream o;
    o<<std::setw(width)<<value;
    return o.str();
}
inline std::string fortran_f0(double value,int width) {
    std::ostringstream o;
    o<<std::setw(width-1)<<std::fixed<<std::setprecision(0)<<value<<'.';
    return o.str();
}
inline int doy(Timestamp t) {
    using namespace std::chrono;
    auto first=sys_days{year{t.year}/1/1};
    auto now=sys_days{year{t.year}/static_cast<unsigned>(t.month)/static_cast<unsigned>(t.day)};
    return static_cast<int>((now-first).count()+1);
}
inline std::string updat_record_header(const Timestamp& t,int wmo,std::size_t mlev,std::size_t istop) {
    std::ostringstream o;
    o<<"   6201  "<<fixed_int(wmo,8);
    for(int repeat=0;repeat<2;++repeat)
        o<<"    "<<fixed_int(t.year,4)<<fixed_int(t.month,4)<<fixed_int(t.day,3)
         <<fixed_int(t.hour,3)<<fixed_int(0,5);
    o<<fixed_int(static_cast<int>(mlev),5)<<"   "<<fixed_int(static_cast<int>(istop),5);
    return o.str();
}
inline std::string level_slash(const Level& lv) {
    double pressure=lv.pressure_hpa.value;
    double height=lv.height_m.valid?lv.height_m.value:9999.0;
    // Original READ62 converts °C to K using 273.2 in REAL*4 arithmetic.
    // Match its single-precision arithmetic before decimal output rounding.
    float t=lv.temperature_c.valid
        ? static_cast<float>(static_cast<float>(lv.temperature_c.value)+273.2f)
        : 999.9f;
    int wd=lv.wind_direction_deg.valid
        ? static_cast<int>(lv.wind_direction_deg.value):999;
    int ws=lv.wind_speed_mps.valid
        ? static_cast<int>(lv.wind_speed_mps.value):999;
    std::ostringstream o;
    o<<"   "<<fixed_num(pressure,6,1)<<"/"
     <<fortran_f0(height,5)<<"/"
     <<fixed_num(t,5,1)<<"/"
     <<fixed_int(wd,3)<<"/"
     <<fixed_int(ws,3);
    return o.str();
}
inline void write_updat_header(std::ostream& out,const UpdatOptions& opt) {
    std::string line=std::string("UP.DAT")+std::string(10,' ')+std::string("2.1")+std::string(13,' ')
                     +std::string("Hour Start and End Times with Seconds");
    line.resize(96,' ');
    out<<line<<"\n";
    out<<"   1\n";
    std::string comment="Produced by READ62 Version: 5.661  Level: 110225";
    comment.resize(80,' ');
    out<<comment<<"\n";
    out<<"NONE    \nUTC+0000\n";
    out<<" ";
    for(int i : {opt.begin.year,doy(opt.begin),opt.begin.hour,0,
                 opt.end.year,doy(opt.end),opt.end.hour,0})
        out<<fixed_int(i,5);
    out<<" "<<fortran_f0(opt.pstop_hpa,4)<<fixed_int(2,5)<<fixed_int(1,5)<<"\n";
    out<<"     F    F    F    F\n";
}
inline UpdatStats write_updat(std::ostream& out,const std::vector<Sounding>& soundings,
                             const UpdatOptions& opt) {
    if(opt.station_wmo<=0||opt.pstop_hpa<=0.0)
        throw ParseError("UP.DAT station WMO/PSTOP invalid");
    if(when(opt.end)<when(opt.begin))throw ParseError("reversed UP.DAT time window");
    UpdatStats stats;
    write_updat_header(out,opt);
    for(const auto& sounding:soundings){
        ++stats.input;
        const auto instant=when(sounding.utc);
        if(instant<when(opt.begin)||instant>when(opt.end))continue;
        std::vector<const Level*> valid;
        for(const auto& lv:sounding.levels)valid.push_back(&lv);
        std::size_t istop=valid.size();
        bool reached_pstop=false;
        for(std::size_t i=0;i<valid.size();++i){
            if(valid[i]->pressure_hpa.value<=opt.pstop_hpa){
                istop=i+1;
                reached_pstop=true;
                break;
            }
        }
        if(istop<2){++stats.skipped_fewer_than_two;continue;}
        out<<updat_record_header(sounding.utc,opt.station_wmo,sounding.raw_level_count,istop)<<"\n";
        if(!reached_pstop
           && std::abs(valid[istop-1]->pressure_hpa.value-opt.pstop_hpa)>1.0) {
            out<<" ->->->Top of sounding is below the "<<fixed_num(opt.pstop_hpa,6,1)<<"-mb level\n";
            ++stats.warnings;
        }
        // Fortran JDAT=2 quality notes follow the 6201 header and precede
        // level data. Repair switches are F for the frozen parity contract.
        const auto missing=[](const Level* lv){
            return !lv->height_m.valid||!lv->temperature_c.valid
                ||!lv->wind_direction_deg.valid||!lv->wind_speed_mps.valid;
        };
        auto warn=[&](const char* message){
            out<<"  ->->->"<<message<<"\n";
            ++stats.warnings;
        };
        if(missing(valid.front()))warn("Data at bottom of sounding is missing");
        if(missing(valid[istop-1]))warn("Data at top of sounding is missing");
        if(valid.front()->height_m.valid
           && static_cast<int>(valid.front()->height_m.value)>sounding.station_elevation_m)
            warn("First level in sounding is above surface");
        bool elevation_decreases=false, elevation_missing=false;
        bool temperature_out_of_range=false;
        for(std::size_t i=0;i<istop;++i){
            const auto& level=*valid[i];
            if(!level.height_m.valid)elevation_missing=true;
            if(level.temperature_c.valid){
                const float temp_k=static_cast<float>(
                    static_cast<float>(level.temperature_c.value)+273.2f);
                if(temp_k<175.0f||temp_k>322.0f)temperature_out_of_range=true;
            }
            if(i>0&&level.height_m.valid&&valid[i-1]->height_m.valid
               &&level.height_m.value<=valid[i-1]->height_m.value)
                elevation_decreases=true;
        }
        if(elevation_decreases)warn("Elevation is decreasing with height");
        if(elevation_missing)warn("Elevation missing");
        if(temperature_out_of_range)warn("Invalid temperature (< TMIN or > TMAX)");
        for(std::size_t i=0;i<istop;++i){
            out<<level_slash(*valid[i]);
            if(i%4==3||i+1==istop)out<<"\n";
        }
        ++stats.written;
        stats.levels_written+=istop;
    }
    return stats;
}
} // namespace cteas::met_input::p4
