#pragma once
// G17B3 selected-source SURFVAR gates: real original CALMET met.inp may
// request IAVET=1 spatial averaging, which the existing multi-station
// selected SURFVAR kernel does NOT implement. Never silently treat this as
// IAVET=0 or as proof of complete P6E thermal-state equivalence.
#include "cteas/p6/p6g_original_wind_controls.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>

namespace cteas::calmet::p6g {
struct OriginalSurfvarControls {
    int irad{},numts{},iavet{},itprog{},irhprog{},npsta{};
    float trad_km{};
};
inline OriginalSurfvarControls parse_original_surfvar_controls(
    const std::string& original_deck) {
    const auto integer=[&](const std::string& key) {
        const auto text=source_wind_value(original_deck,key);
        std::size_t used=0;
        int value=0;
        try{value=std::stoi(text,&used);}
        catch(const std::exception&){
            throw std::invalid_argument("G17B invalid original integer "+key);
        }
        if(used!=text.size())throw std::invalid_argument(
            "G17B extra characters in original "+key);
        return value;
    };
    const auto real=[&](const std::string& key) {
        const auto text=source_wind_normalize(source_wind_value(original_deck,key));
        std::size_t used=0;float value=0.f;
        try{value=std::stof(text,&used);}
        catch(const std::exception&){
            throw std::invalid_argument("G17B invalid original float "+key);
        }
        if(used!=text.size()||!std::isfinite(value))
            throw std::invalid_argument("G17B invalid float "+key);
        return value;
    };
    OriginalSurfvarControls result;
    result.irad=integer("IRAD");
    result.numts=integer("NUMTS");
    result.iavet=integer("IAVET");
    result.itprog=integer("ITPROG");
    result.irhprog=integer("IRHPROG");
    result.npsta=integer("NPSTA");
    result.trad_km=real("TRADKM");
    if((result.irad!=1&&result.irad!=2)||result.numts<1||
       result.numts>1000||result.trad_km<0.f||
       (result.iavet!=0&&result.iavet!=1)||
       result.itprog<0||result.irhprog<0||result.npsta<0)
        throw std::invalid_argument("G17B original SURFVAR physical controls invalid");
    return result;
}
inline void require_selected_iavet0(
    const OriginalSurfvarControls& original,
    float grid_km,int requested_irad,int requested_numts,
    float requested_trad_grid) {
    if(!std::isfinite(grid_km)||grid_km<=0.f||
       !std::isfinite(requested_trad_grid)||requested_trad_grid<0.f)
        throw std::invalid_argument("G17B selected SURFVAR grid invalid");
    if(original.iavet!=0||original.itprog!=0||
       original.irhprog!=0||original.npsta!=0)
        throw std::invalid_argument(
            "G17B real met.inp needs IAVET or other SURFVAR path not yet implemented");
    const float trad_grid=original.trad_km/grid_km;
    if(original.irad!=requested_irad||
       original.numts!=requested_numts||
       std::abs(trad_grid-requested_trad_grid)>0.000001f)
        throw std::invalid_argument("G17B selected SURFVAR controls diverge from met.inp");
}
} // namespace cteas::calmet::p6g
