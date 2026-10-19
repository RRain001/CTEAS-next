// G1B-B2 original NOAA -> native P5 SURF.DAT independent P6 reader.
// Strictly input-only: cannot execute CALMET winds or CALPUFF puffs.
#include "cteas/p6/read_surface_dynamic.hpp"
#include <chrono>
#include <cstdlib>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc,char** argv) {
    try {
        if(argc<4)
            throw std::invalid_argument(
                "usage: cteas_p6g_surf_source_preflight <SURF.DAT> <HOURS> <IFSTN1> [IFSTN2 ...]");
        const auto hours=std::stoi(argv[2]);
        if(hours<1||hours>48)
            throw std::invalid_argument("source-only acceptance must be 1-48h");
        std::vector<int> ids;
        for(int k=3;k<argc;++k)ids.push_back(std::stoi(argv[k]));
        const auto raw=cteas::calmet::p6g::read_surface_dynamic(argv[1],ids,48,100000,4800000);
        if(static_cast<int>(raw.hourly.size())!=hours)
            throw std::runtime_error("native SURF source hours disagree with case research time");
        if(raw.station_ids!=ids)
            throw std::runtime_error("native SURF source station ID/order differs from selected ISD");
        std::size_t populated=0,missing=0,wind_valid=0;
        for(const auto& hour:raw.hourly){
            if(hour.by_station.size()!=ids.size())
                throw std::runtime_error("SURF original per-hour station cardinality drift");
            for(const auto& obs:hour.by_station){
                if(obs.temperature_valid||obs.humidity_valid||obs.pressure_valid)++populated;
                else ++missing;
                if(obs.wind_valid)++wind_valid;
            }
        }
        if(populated==0||wind_valid==0)
            throw std::runtime_error("native source parsed no real meteorological observation");
        std::cout<<"PASS_P6G_REAL_NOAA_NATIVE_SURF_SOURCE_HOURLY"
                 <<" HOURS="<<hours
                 <<" NSSTA="<<ids.size()
                 <<" POPULATED_STATION_HOURS="<<populated
                 <<" MISSING_STATION_HOURS="<<missing
                 <<" VALID_WIND_STATION_HOURS="<<wind_valid
                 <<" SS_IDS=";
        for(std::size_t i=0;i<ids.size();++i)
            std::cout<<(i?",":"")<<ids[i];
        std::cout<<" P6_PHYSICS=NOT_RUN P7=NOT_RUN\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"BLOCKED_P6G_REAL_NOAA_SURF_SOURCE "<<e.what()<<"\n";
        return 2;
    }
}
