#pragma once
// P6C selected original CALMET 6.5.0 RDHD + RDSN formatted SURF.DAT
// calmet.for L14862-14927, L23556-23636.
//
// Only SURF.DAT v2.1 / IFORMS=2 / NSSTA=1 / PMAP NONE / UTC+0000,
// the frozen 2022 P5 virtual-station reference path. No fake station
// outside study, no rainfall inference from missing IPCODE.
// Original SURF.DAT one-hour records have explicit start and end times.
#include <chrono>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6 {
struct SurfaceObserved {
    float wind_speed_mps=9999.f,wind_direction_deg=9999.f;
    int ceiling_hundreds_ft=9999,opaque_cloud_tenths=9999;
    float temperature_k=9999.f,pressure_mb=9999.f;
    int humidity_pct=9999,precip_code=9999;
    bool wind_valid=false,temperature_valid=false,humidity_valid=false,
         pressure_valid=false,ceiling_valid=false,cloud_valid=false,
         precipitation_code_valid=false;
};
struct SurfaceInterval {
    std::chrono::sys_seconds start,end;
    SurfaceObserved obs;
};
struct Surface2022 {
    int station_id=0;
    std::vector<SurfaceInterval> hourly;
};
inline void surf_require(bool ok,const char* msg) {
    if(!ok)throw std::runtime_error(msg);
}
inline std::string surf_line(std::istream& stream,const char* reason) {
    std::string s;
    surf_require(static_cast<bool>(std::getline(stream,s)),reason);
    return s;
}
inline std::string surf_trim(const std::string& x) {
    auto first=x.find_first_not_of(" \t\n\r");
    if(first==std::string::npos)return {};
    return x.substr(first,x.find_last_not_of(" \t\n\r")-first+1);
}
inline int surf_int(double x) {
    surf_require(std::isfinite(x) && x>=-2.1e9 && x<=2.1e9 &&
                static_cast<double>(static_cast<int>(x))==x,
                "SURF field expected integer");
    return static_cast<int>(x);
}
inline std::chrono::sys_seconds surf_time(int year,int jul,int hour,int secs) {
    using namespace std::chrono;
    const std::chrono::year y{year};
    surf_require(y.ok()&&year==2022&&jul>=1&&jul<=365&&
                 hour>=0&&hour<=24&&secs>=0&&secs<3600,
                 "SURF time not supported for frozen 2022 hourly reference");
    return sys_days{y/January/1}+days{jul-1}+hours{hour}+seconds{secs};
}
inline Surface2022 read_surface_2022(const std::string& path) {
    using namespace std::chrono;
    std::ifstream in(path);
    surf_require(static_cast<bool>(in),"SURF.DAT file unavailable");
    auto first=surf_line(in,"missing SURF identity");
    surf_require(first.size()>=32 &&
                 surf_trim(first.substr(0,16))=="SURF.DAT" &&
                 surf_trim(first.substr(16,16))=="2.1",
                 "only SURF.DAT v2.1 formatted supported");
    {
        const auto cc=surf_line(in,"missing SURF comment count");
        std::istringstream scan(cc);
        int n=0;
        surf_require(static_cast<bool>(scan>>n)&&n>=0&&n<=10000,
                     "SURF comment count");
        for(int k=0;k<n;++k)(void)surf_line(in,"missing SURF comment");
    }
    surf_require(surf_trim(surf_line(in,"missing SURF PMAP"))=="NONE",
                 "only P6C original SURF PMAP NONE supported");
    surf_require(surf_trim(surf_line(in,"missing SURF time zone"))=="UTC+0000",
                 "only UTC+0000 surface data accepted");
    Surface2022 result;
    {
        std::istringstream meta(surf_line(in,"missing SURF start/end metadata"));
        int sy=0,sj=0,sh=0,ss=0,ey=0,ej=0,eh=0,es=0,number=0;
        surf_require(static_cast<bool>(meta>>sy>>sj>>sh>>ss>>ey>>ej>>eh>>es>>number),
                     "SURF start/end metadata incomplete");
        surf_require(number==1,"selected original P6 reference requires one surface station");
        surf_require(surf_time(sy,sj,sh,ss)==sys_days{year{2022}/January/1} &&
                     surf_time(ey,ej,eh,es)==sys_days{year{2022}/January/6}+hours{23},
                     "SURF header is not original 2022 143h interval");
    }
    {
        std::istringstream id(surf_line(in,"SURF station identifiers absent"));
        surf_require(static_cast<bool>(id>>result.station_id)&&result.station_id>0,
                     "invalid SURF station id");
        std::string excess;
        surf_require(!(id>>excess),"unexpected extra SURF station");
    }
    result.hourly.reserve(143);
    sys_seconds expected=sys_days{year{2022}/January/1};
    for(int record=0;record<143;++record) {
        std::istringstream ts(surf_line(in,"missing SURF hourly timestamp"));
        int sy=0,sj=0,sh=0,ss=0,ey=0,ej=0,eh=0,es=0;
        surf_require(static_cast<bool>(ts>>sy>>sj>>sh>>ss>>ey>>ej>>eh>>es),
                     "invalid SURF hourly timestamp");
        SurfaceInterval row;
        row.start=surf_time(sy,sj,sh,ss);
        row.end=surf_time(ey,ej,eh,es);
        surf_require(row.start==expected&&row.end-row.start==hours{1},
                     "SURF hourly time continuity or duration mismatch");
        expected=row.end;
        std::istringstream fields(surf_line(in,"missing SURF observation data"));
        double ws,wd,tmp,pre;
        int cei,cloud,rh,code;
        surf_require(static_cast<bool>(fields>>ws>>wd>>cei>>cloud>>tmp>>rh>>pre>>code),
                     "SURF record incomplete");
        std::string extra;
        surf_require(!(fields>>extra),"extra SURF record fields");
        for(double x:{ws,wd,tmp,pre})
            surf_require(std::isfinite(x)&&std::abs(x)<=9999.99,
                         "SURF nonfinite or invalid real");
        row.obs.wind_speed_mps=static_cast<float>(ws);
        row.obs.wind_direction_deg=static_cast<float>(wd);
        row.obs.ceiling_hundreds_ft=cei;
        row.obs.opaque_cloud_tenths=cloud;
        row.obs.temperature_k=static_cast<float>(tmp);
        row.obs.humidity_pct=rh;
        row.obs.pressure_mb=static_cast<float>(pre);
        row.obs.precip_code=code;
        // Original RDSN missing values are >=9998 (9999). Zero calm
        // wind is a perfectly valid observation when both components exist.
        row.obs.wind_valid=ws<9998.0&&wd<9998.0&&ws>=0.0&&
                           wd>=0.0&&wd<=360.0;
        row.obs.temperature_valid=tmp<9998.0&&tmp>0;
        row.obs.humidity_valid=rh<9998&&rh>=0&&rh<=100;
        row.obs.pressure_valid=pre<9998.0&&pre>0;
        row.obs.ceiling_valid=cei<9998&&cei>=0;
        row.obs.cloud_valid=cloud<9998&&cloud>=0&&cloud<=10;
        row.obs.precipitation_code_valid=code<9998&&code>=0;
        result.hourly.push_back(row);
    }
    surf_require(expected==sys_days{year{2022}/January/6}+hours{23},
                 "SURF final hour endpoint mismatch");
    std::string leftover;
    while(std::getline(in,leftover))
        surf_require(surf_trim(leftover).empty(),
                     "SURF has surplus/misaligned records");
    return result;
}
} // namespace cteas::calmet::p6
