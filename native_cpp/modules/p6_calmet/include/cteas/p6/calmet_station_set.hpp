#pragma once
// P6G dynamic READCF station list, CALMET Group 7/8 strict source controls.
// Independent adapter; original frozen SS1/US1 parser remains unchanged.
// Local metre mapping retains individual REAL*4 multiplies and subtracts.
#include "cteas/p6/calmet_station_deck.hpp"
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct StationSet {
    std::vector<cteas::calmet::p6::DeckStation> surface,upper;
};

inline StationSet original_calmet_multi_station_deck(
    const std::string& deck,float xorig_km,float yorig_km,
    int expected_surface,int expected_upper) {
    if(!std::isfinite(xorig_km)||!std::isfinite(yorig_km)||
       expected_surface<1||expected_upper<1)
        throw std::invalid_argument("invalid dynamic CALMET station-count/origin");
    StationSet result;
    std::set<int> surface_ordinals,upper_ordinals;
    std::set<int> surface_ids,upper_ids;
    static const std::regex line(
        R"(!\s*(SS|US)([0-9]+)\s*=\s*'([^']*)'\s*([^!]*)!)");
    for(auto it=std::sregex_iterator(deck.begin(),deck.end(),line);
        it!=std::sregex_iterator();++it) {
        const bool surface=(*it)[1].str()=="SS";
        const int ordinal=std::stoi((*it)[2].str());
        const int expected=surface?expected_surface:expected_upper;
        if(ordinal<1||ordinal>expected)
            throw std::invalid_argument("CALMET SSn/USn ordinal outside declared count");
        auto& ordinal_set=surface?surface_ordinals:upper_ordinals;
        if(!ordinal_set.insert(ordinal).second)
            throw std::invalid_argument("duplicate CALMET SSn/USn ordinal");
        cteas::calmet::p6::DeckStation station;
        station.name=(*it)[3].str();
        if(station.name.empty())
            throw std::invalid_argument("empty CALMET station name");
        std::istringstream fields((*it)[4].str());
        std::string id,x,y,tz,height,extra;
        if(!(fields>>id>>x>>y>>tz)||
           (surface&&!(fields>>height))||(fields>>extra))
            throw std::invalid_argument("malformed SSn/USn fields");
        try{
            std::size_t used=0;
            station.id=std::stoi(id,&used);
            if(used!=id.size()||station.id<=0)
                throw std::invalid_argument("invalid station ID");
        }catch(const std::exception&){
            throw std::invalid_argument("invalid station ID");
        }
        auto& ids=surface?surface_ids:upper_ids;
        if(!ids.insert(station.id).second)
            throw std::invalid_argument("duplicate station identity in group");
        station.utm_x_km=cteas::calmet::p6::station_deck_float(x);
        station.utm_y_km=cteas::calmet::p6::station_deck_float(y);
        station.time_zone_hours=cteas::calmet::p6::station_deck_float(tz);
        if(surface){
            station.anemometer_height_m=
                cteas::calmet::p6::station_deck_float(height);
            if(station.anemometer_height_m<=0)
                throw std::invalid_argument("SS anemometer height must be positive");
        }
        // Replicate READCF REAL*4 mapping (no FMA) even on Release compilers.
        volatile float ox=1000.f*xorig_km,oy=1000.f*yorig_km;
        volatile float ax=1000.f*station.utm_x_km;
        volatile float ay=1000.f*station.utm_y_km;
        station.local_x_m=ax-ox;station.local_y_m=ay-oy;
        if(!std::isfinite(station.local_x_m)||!std::isfinite(station.local_y_m))
            throw std::invalid_argument("nonfinite CALMET local metre position");
        (surface?result.surface:result.upper).push_back(
            std::move(station));
    }
    if(static_cast<int>(surface_ordinals.size())!=expected_surface||
       static_cast<int>(upper_ordinals.size())!=expected_upper)
        throw std::invalid_argument("missing SSn/USn entries in model deck");
    // The Fortran arrays use ordinal order regardless of order in the .inp.
    // Rebuild using one scan for ordinals and a second to sort without relying
    // on station identifiers being numerically ordered.
    const auto reorder=[&](std::vector<cteas::calmet::p6::DeckStation>& rows,
                           const std::string& prefix) {
        std::vector<cteas::calmet::p6::DeckStation> ordered(rows.size());
        static const std::regex ord(
            R"(!\s*(SS|US)([0-9]+)\s*=\s*'([^']*)'\s*([^!]*)!)");
        std::size_t idx=0;
        for(auto it=std::sregex_iterator(deck.begin(),deck.end(),ord);
            it!=std::sregex_iterator();++it) {
            if((*it)[1].str()!=prefix)continue;
            const auto ordinal=static_cast<std::size_t>(std::stoul((*it)[2].str()));
            ordered[ordinal-1]=rows.at(idx++);
        }
        rows=std::move(ordered);
    };
    reorder(result.surface,"SS");
    reorder(result.upper,"US");
    return result;
}
} // namespace cteas::calmet::p6g
