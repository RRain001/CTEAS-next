#pragma once
// P6G G14B: one file-backed source authority for multi-site CALMET hours.
// The original-format GEO.DAT / SURF.DAT / per-US UP.DAT plus met.inp's
// SSn/USn station roster enter the SAME 17-stage stateful scheduler.
// No synthetic observations, station reordering or original met.dat backfill.
#include "cteas/p6/p6g_unified_hourly.hpp"
#include <array>
#include <cmath>
#include <fstream>
#include <regex>
#include <sstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct CaseInputPaths {
    std::string geo_file;
    std::string surface_file;
    std::vector<std::string> upper_files;
    std::string met_inp_file;
    GeoGridSpec expected_grid{};
    int surface_count=0,upper_count=0;
};

// Source met.inp is the authoritative original CALMET model grid, not a
// GUI-provided centre or independently guessed 10-km test setting.
// Validate every required spatial/vertical control before opening any data.
inline void validate_original_calmet_deck_grid(
    const std::string& deck,const GeoGridSpec& expected,
    int surface_count,int upper_count) {
    const auto field=[&](const std::string& name) {
        const std::regex pattern(
            "!\\s*"+name+"\\s*=\\s*([^!]*)!",
            std::regex_constants::icase);
        auto it=std::sregex_iterator(deck.begin(),deck.end(),pattern);
        if(it==std::sregex_iterator())
            throw std::invalid_argument("G14B met.inp missing source control "+name);
        std::string value=(*it)[1].str();
        ++it;
        if(it!=std::sregex_iterator())
            throw std::invalid_argument("G14B duplicate met.inp control "+name);
        const auto first=value.find_first_not_of(" \t\r\n");
        const auto last=value.find_last_not_of(" \t\r\n");
        if(first==std::string::npos)
            throw std::invalid_argument("G14B empty met.inp control "+name);
        return value.substr(first,last-first+1);
    };
    const auto integer=[&](const std::string& name) {
        auto value=field(name);
        std::size_t used=0;
        int output=0;
        try{output=std::stoi(value,&used);}
        catch(const std::exception&){
            throw std::invalid_argument("G14B noninteger met.inp "+name);
        }
        if(used!=value.size())
            throw std::invalid_argument("G14B malformed met.inp integer "+name);
        return output;
    };
    const auto real=[&](const std::string& name) {
        auto value=field(name);
        std::size_t used=0;
        double output=0.;
        try{output=std::stod(value,&used);}
        catch(const std::exception&){
            throw std::invalid_argument("G14B nonnumeric met.inp "+name);
        }
        if(used!=value.size()||!std::isfinite(output))
            throw std::invalid_argument("G14B malformed met.inp real "+name);
        return output;
    };
    if(field("PMAP")!="UTM"||field("DATUM")!="WGS-84"||
       field("UTMHEM")!=std::string(1,expected.hemisphere)||
       integer("IUTMZN")!=expected.zone||
       integer("NX")!=expected.nx||integer("NY")!=expected.ny||
       integer("NZ")!=9||
       integer("NSSTA")!=surface_count||integer("NUSTA")!=upper_count||
       std::abs(real("DGRIDKM")-expected.spacing_km)>1.e-6||
       std::abs(real("XORIGKM")-expected.xorigin_km)>0.00051||
       std::abs(real("YORIGKM")-expected.yorigin_km)>0.00051)
        throw std::invalid_argument(
            "G14B met.inp grid/station counts disagree with GEO.DAT/model");
    const auto vertical=field("ZFACE");
    std::string values=vertical;
    for(auto& c:values)if(c==',')c=' ';
    std::istringstream input(values);
    std::array<float,10> zface{};
    for(float& value:zface){
        if(!(input>>value)||!std::isfinite(value))
            throw std::invalid_argument("G14B met.inp requires 10 finite ZFACE faces");
    }
    std::string extra;
    if(input>>extra)
        throw std::invalid_argument("G14B met.inp ZFACE exceeds 10 vertical faces");
    for(std::size_t k=1;k<zface.size();++k)
        if(!(zface[k]>zface[k-1]))
            throw std::invalid_argument("G14B met.inp ZFACE is not strictly increasing");
}

inline UnifiedMultistationHourlyScheduler load_unified_multistation_case(
    const CaseInputPaths& paths) {
    if(paths.geo_file.empty()||paths.surface_file.empty()||
       paths.met_inp_file.empty()||paths.surface_count<=0||
       paths.upper_count<=0||
       paths.upper_files.size()!=static_cast<std::size_t>(paths.upper_count))
        throw std::invalid_argument("P6G G14B requires full original-format case files");
    std::ifstream deck_file(paths.met_inp_file);
    if(!deck_file)
        throw std::runtime_error("P6G G14B met.inp unavailable");
    const std::string text((std::istreambuf_iterator<char>(deck_file)),
                           std::istreambuf_iterator<char>());
    if(deck_file.bad()||text.empty())
        throw std::runtime_error("P6G G14B met.inp unreadable");
    validate_original_calmet_deck_grid(
        text,paths.expected_grid,paths.surface_count,paths.upper_count);
    // Source wind controls are materialized exactly once, here, from the
    // same met.inp validated for GEO/SS/US input geometry. READCF effective
    // BIAS(1) mutation belongs to this authoritative model state.
    const auto wind_controls=parse_original_wind_controls(text);
    // GEO.DAT origin and met.inp station origin are taken from one
    // authoritative numerical-grid config, never geographic case centre.
    auto geo=read_geo_dynamic(paths.geo_file,paths.expected_grid);
    auto stations=original_calmet_multi_station_deck(
        text,geo.xorigin_km,geo.yorigin_km,
        paths.surface_count,paths.upper_count);
    std::vector<int> surface_ids,upper_ids;
    surface_ids.reserve(stations.surface.size());
    upper_ids.reserve(stations.upper.size());
    for(const auto& s:stations.surface)surface_ids.push_back(s.id);
    for(const auto& s:stations.upper)upper_ids.push_back(s.id);
    auto surface=read_surface_dynamic(paths.surface_file,surface_ids);
    auto upper=read_upper_station_set(paths.upper_files,upper_ids);
    return UnifiedMultistationHourlyScheduler(
        std::move(geo),std::move(stations),
        std::move(surface),std::move(upper),wind_controls);
}
} // namespace cteas::calmet::p6g
