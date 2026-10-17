#pragma once
// CALMET 6.5.0 Group 7/8 station location input contract.
//
// SSn/USn in met.inp are UTM kilometres. The original CALMET-compatible
// computation starts from those stored REAL*4 coordinates, not from
// stations.csv latitude/longitude or a reconstructed case-grid centre.
// Only the frozen one-surface/one-upper route is currently supported here.
#include <cmath>
#include <limits>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>

namespace cteas::calmet::p6 {

struct DeckStation {
    int id{};
    std::string name;
    float utm_x_km{},utm_y_km{};
    float local_x_m{},local_y_m{};
    float time_zone_hours{};
    float anemometer_height_m{}; // Only SS records provide this field
};

struct DeckStationPair {
    DeckStation surface,upper;
};

inline float station_deck_float(const std::string& token) {
    std::size_t parsed=0;
    float value=0.f;
    try {
        value=std::stof(token,&parsed);
    } catch (const std::exception&) {
        throw std::invalid_argument("CALMET station deck contains invalid number");
    }
    if(parsed!=token.size()||!std::isfinite(value))
        throw std::invalid_argument("CALMET station deck contains nonfinite/trailing number");
    return value;
}

// Original deck logical values are literal T/F. Numeric-only fallback would
// silently interpret LVARY=T as false, changing INTER2/DIAGNO behaviour.
inline bool original_calmet_deck_logical(
    const std::string& deck,const std::string& key,bool fallback) {
    const std::regex assignment(std::string(R"(!\s*)")+key+R"(\s*=\s*([^!]*)!)");
    std::string token;
    bool found=false;
    for(auto it=std::sregex_iterator(deck.begin(),deck.end(),assignment);
        it!=std::sregex_iterator();++it) {
        if(found)throw std::invalid_argument("duplicate CALMET logical control "+key);
        std::istringstream fields((*it)[1].str());
        if(!(fields>>token))
            throw std::invalid_argument("empty CALMET logical control "+key);
        std::string extra;
        if(fields>>extra)
            throw std::invalid_argument("malformed CALMET logical control "+key);
        found=true;
    }
    if(!found)return fallback;
    if(token=="T"||token=="t"||token=="TRUE"||token=="true")return true;
    if(token=="F"||token=="f"||token=="FALSE"||token=="false")return false;
    throw std::invalid_argument("unsupported CALMET logical control "+key);
}

inline DeckStationPair original_calmet_station_deck(
    const std::string& deck,float xorig_km,float yorig_km) {
    if(!std::isfinite(xorig_km)||!std::isfinite(yorig_km))
        throw std::invalid_argument("CALMET station deck origin is not finite");

    // The quoted station name must not be interpreted as numerical input.
    static const std::regex line(
        R"(!\s*(SS|US)([0-9]+)\s*=\s*'([^']*)'\s*([^!]*)!)");
    DeckStationPair result;
    bool have_surface=false,have_upper=false;
    for(auto it=std::sregex_iterator(deck.begin(),deck.end(),line);
        it!=std::sregex_iterator();++it) {
        const bool surface=(*it)[1].str()=="SS";
        const int ordinal=std::stoi((*it)[2].str());
        if(ordinal!=1)
            throw std::invalid_argument(
                "CALMET station deck adapter requires one SS1 and one US1");
        if((surface && have_surface)||(!surface && have_upper))
            throw std::invalid_argument("duplicate CALMET station deck entry");
        DeckStation station;
        station.name=(*it)[3].str();
        if(station.name.empty())
            throw std::invalid_argument("empty CALMET station name");
        std::istringstream fields((*it)[4].str());
        std::string id,x,y,tz,height,extra;
        if(!(fields>>id>>x>>y>>tz)||
           (surface && !(fields>>height))||(fields>>extra))
            throw std::invalid_argument("malformed CALMET station deck fields");
        std::size_t used=0;
        try {
            station.id=std::stoi(id,&used);
        } catch(const std::exception&) {
            throw std::invalid_argument("invalid CALMET station ID");
        }
        if(used!=id.size()||station.id<=0)
            throw std::invalid_argument("invalid CALMET station ID");
        station.utm_x_km=station_deck_float(x);
        station.utm_y_km=station_deck_float(y);
        station.time_zone_hours=station_deck_float(tz);
        if(surface) {
            station.anemometer_height_m=station_deck_float(height);
            if(station.anemometer_height_m<=0.f)
                throw std::invalid_argument(
                    "CALMET SS1 anemometer height must be positive");
        }

        // Do NOT promote the subtract/multiply to double. Retain the
        // REAL*4 evaluation order of the original READCF selected route.
        // calmet.for READCF L27073-27076, L27128-27133 and L27183-27188:
        //   XORIGR=1000.*XORIGKM
        //   XSSTA =1000.*XKM-XORIGR   (same for Y and upper air).
        // Crucial: multiplication is performed before subtraction in REAL*4.
        // Store REAL*4 intermediates independently: do not let a release
        // build contract the multiply and subtract into one fused operation.
        // This conversion happens only once per station, not per grid cell.
        volatile float xorigr=1000.f*xorig_km;
        volatile float yorigr=1000.f*yorig_km;
        volatile float abs_x_m=1000.f*station.utm_x_km;
        volatile float abs_y_m=1000.f*station.utm_y_km;
        station.local_x_m=abs_x_m-xorigr;
        station.local_y_m=abs_y_m-yorigr;
        if(!std::isfinite(station.local_x_m)||
           !std::isfinite(station.local_y_m))
            throw std::invalid_argument("invalid relative CALMET station position");
        if(surface){result.surface=station;have_surface=true;}
        else{result.upper=station;have_upper=true;}
    }
    if(!have_surface||!have_upper)
        throw std::invalid_argument("met.inp must provide both SS1 and US1");
    return result;
}
} // namespace cteas::calmet::p6
