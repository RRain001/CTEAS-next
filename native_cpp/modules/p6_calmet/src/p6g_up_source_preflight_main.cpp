// S2-G1B-B1: only check native original-format UP.DAT, never run CALMET.
#include "cteas/p6/read_upper_dynamic.hpp"
#include <algorithm>
#include <chrono>
#include <cstddef>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc,char** argv) {
    try {
        if(argc!=5)
            throw std::invalid_argument(
                "usage: cteas_p6g_up_source_preflight <UP.DAT> <WMO_ID> "
                "<FIRST_MODEL_HOUR_END_EPOCH_S> <LAST_MODEL_HOUR_END_EPOCH_S>");
        const auto station=std::stoi(argv[2]);
        const auto first=std::chrono::sys_seconds{
            std::chrono::seconds{std::stoll(argv[3])}};
        const auto last=std::chrono::sys_seconds{
            std::chrono::seconds{std::stoll(argv[4])}};
        if(last<first || first.time_since_epoch().count()<=0 ||
           (last-first)>std::chrono::hours{24*14} ||
           (last-first)%std::chrono::hours{1}!=std::chrono::seconds{0})
            throw std::invalid_argument(
                "source-only acceptance window invalid (>14 days or nonhourly)");
        const auto series=cteas::calmet::p6g::read_upper_dynamic(argv[1],station);
        const auto& records=series.soundings;
        if(records.size()<2)throw std::runtime_error("fewer than two real soundings");
        std::size_t checked=0;
        for(auto end=first;end<=last;end+=std::chrono::hours{1}) {
            const auto it=std::upper_bound(records.begin(),records.end(),end,
                [](const auto& when,const auto& s){return when<s.end;});
            if(it==records.begin()||it==records.end())
                throw std::runtime_error(
                    "P4 native source lacks authentic bracketing sounding");
            const auto& earlier=*(it-1);
            const auto& later=*it;
            const auto span=std::chrono::duration_cast<std::chrono::seconds>(
                later.end-earlier.end).count();
            if(span<3600||span>14*3600||end<earlier.end||end>=later.end)
                throw std::runtime_error("P6 original PREPDI bracket gap invalid");
            ++checked;
        }
        std::cout<<"PASS_P6G_REAL_NOAA_UP_SOURCE_TIME_BRACKETS"
                 <<" WMO="<<series.station_id
                 <<" HOURS="<<checked
                 <<" ORIGINAL_FORMAT_SOUNDINGS="<<records.size()
                 <<" FIRST_SOUNDING_EPOCH_S="
                 <<records.front().end.time_since_epoch().count()
                 <<" LAST_SOUNDING_EPOCH_S="
                 <<records.back().end.time_since_epoch().count()
                 <<" P6_PHYSICS=NOT_RUN P7=NOT_RUN\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"BLOCKED_P6G_NOAA_UP_SOURCE_PREFLIGHT "<<e.what()<<"\n";
        return 2;
    }
}
