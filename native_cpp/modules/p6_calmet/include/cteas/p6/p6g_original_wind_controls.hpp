#pragma once
// G15A: CALMET 6.5.0 source-selected numerical wind controls read from the
// actual met.inp deck. NO driver-local default is allowed to impersonate
// original source controls. Explicit unsupported modes fail closed.
// These are data/provenance controls, NOT a full multi-site acceptance.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>

namespace cteas::calmet::p6g {
struct OriginalWindControls {
    std::array<float,9> bias{};
    // The 10 vertical faces are original ZFACE(NZ+1), never G8 test constants.
    std::array<float,10> zface_m{};
    std::array<int,9> nsmth{},nintr2{};
    float rmin_km{},rmax1_km{},rmax2_km{},rmax3_km{},
          r1_km{},r2_km{};
    int iextrp{},icalm{},iprog{},noobs{},ifradj{},islope{},iobr{};
    bool lvary{};
};
inline std::string source_wind_value(const std::string& deck,
                                     const std::string& key) {
    // Original CALMET decks place multiline arrays between ! KEY = and !.
    // This is NOT a search-and-default parser. Missing/duplicate is fatal.
    const std::regex pattern("!\\s*"+key+"\\s*=\\s*([^!]*)!",
                             std::regex_constants::icase);
    auto it=std::sregex_iterator(deck.begin(),deck.end(),pattern);
    if(it==std::sregex_iterator())
        throw std::invalid_argument("P6G missing original met.inp wind control "+key);
    std::string value=(*it)[1].str();
    ++it;
    if(it!=std::sregex_iterator())
        throw std::invalid_argument("P6G duplicate original met.inp wind control "+key);
    const auto p=value.find_first_not_of(" \t\r\n");
    if(p==std::string::npos)
        throw std::invalid_argument("P6G empty original met.inp wind control "+key);
    const auto last=value.find_last_not_of(" \t\r\n");
    return value.substr(p,last-p+1);
}
inline std::string source_wind_normalize(std::string value){
    for(char& c:value){
        if(c==',')c=' ';
        if(c=='D'||c=='d')c='E';
    }
    return value;
}
inline OriginalWindControls parse_original_wind_controls(
    const std::string& deck){
    OriginalWindControls v;
    const auto single=[&](const std::string& name)->std::string{
        const std::string value=source_wind_normalize(source_wind_value(deck,name));
        std::istringstream in(value);
        std::string one,extra;
        if(!(in>>one)||(in>>extra))
            throw std::invalid_argument("P6G malformed single wind control "+name);
        return one;
    };
    const auto real=[&](const std::string& name){
        const auto value=single(name);
        std::size_t used=0;float out=0.f;
        try{out=std::stof(value,&used);}
        catch(const std::exception&){
            throw std::invalid_argument("P6G nonnumeric wind control "+name);
        }
        if(used!=value.size()||!std::isfinite(out))
            throw std::invalid_argument("P6G invalid REAL4 control "+name);
        return out;
    };
    const auto integer=[&](const std::string& name){
        const auto value=single(name);
        std::size_t used=0;int out=0;
        try{out=std::stoi(value,&used);}
        catch(const std::exception&){
            throw std::invalid_argument("P6G noninteger wind control "+name);
        }
        if(used!=value.size())
            throw std::invalid_argument("P6G invalid integer control "+name);
        return out;
    };
    const auto array=[&](const std::string& name,auto& output){
        std::istringstream in(source_wind_normalize(source_wind_value(deck,name)));
        for(auto& item:output)
            if(!(in>>item))
                throw std::invalid_argument("P6G missing layer control "+name);
        std::string excess;
        if(in>>excess)
            throw std::invalid_argument("P6G too many layer values "+name);
    };
    v.iextrp=integer("IEXTRP");v.icalm=integer("ICALM");
    v.iprog=integer("IPROG");v.noobs=integer("NOOBS");
    v.ifradj=integer("IFRADJ");v.islope=integer("ISLOPE");
    v.iobr=integer("IOBR");
    const auto lvary=single("LVARY");
    if(lvary=="F"||lvary==".FALSE.")v.lvary=false;
    else if(lvary=="T"||lvary==".TRUE.")v.lvary=true;
    else throw std::invalid_argument("P6G malformed LVARY switch");
    v.rmin_km=real("RMIN");v.rmax1_km=real("RMAX1");
    v.rmax2_km=real("RMAX2");v.rmax3_km=real("RMAX3");
    v.r1_km=real("R1");v.r2_km=real("R2");
    array("BIAS",v.bias);
    array("ZFACE",v.zface_m);
    array("NSMTH",v.nsmth);
    array("NINTR2",v.nintr2);
    // READCF calmet.for L26579-L26612 is a mandatory post-parse mutation.
    // In accepted PR #53 realcase_wind_field_main.cpp L280-288, IEXTRP<0
    // forces surface-only first layer BIAS(1)=-1, even when the user's
    // met.inp says BIAS(1)=0. This is source-effective state, not raw input.
    if(v.iextrp<0&&v.noobs!=2)v.bias[0]=-1.f;
    // This is the fully source-scoped path verified by G9/G10/G11. Other
    // modes require their own direct original-Fortran acceptance first.
    if(v.iextrp!=-4||v.iprog!=0||v.noobs!=0||
       (v.icalm!=0&&v.icalm!=1)||v.lvary||v.ifradj!=1||
       v.islope!=1||v.iobr!=0)
        throw std::invalid_argument("P6G wind controls outside vendor-scoped path");
    for(float x:{v.rmin_km,v.rmax1_km,v.rmax2_km,v.rmax3_km,
                 v.r1_km,v.r2_km})
        if(!std::isfinite(x)||x<=0.f)
            throw std::invalid_argument("P6G invalid original radius");
    for(std::size_t k=0;k<v.zface_m.size();++k){
        if(!std::isfinite(v.zface_m[k])||
           (k>0&&!(v.zface_m[k]>v.zface_m[k-1])))
            throw std::invalid_argument("P6G original ZFACE must be finite/increasing");
    }
    for(std::size_t k=0;k<v.bias.size();++k){
        if(!std::isfinite(v.bias[k])||v.bias[k]<-1.f||v.bias[k]>1.f||
           v.nsmth[k]<0||v.nsmth[k]>1000||
           v.nintr2[k]<1||v.nintr2[k]>10000)
            throw std::invalid_argument("P6G unsupported source layer BIAS/NSMTH/NINTR2");
    }
    return v;
}
} // namespace cteas::calmet::p6g
