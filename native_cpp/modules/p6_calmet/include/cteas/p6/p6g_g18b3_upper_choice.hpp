#pragma once
// G18B3: source-deck IUPT and REAL*4 selected SETCOM-style grid/US
// nearest-station mapping, with explicit provenance and fail-closed scope.
// This is NOT yet independent original Fortran NEARU parity or complete COMP.
#include "cteas/p6/p6g_original_wind_controls.hpp"
#include "cteas/p6/calmet_station_set.hpp"
#include "cteas/p6/read_geo_dynamic.hpp"
#include "cteas/p6e/mixht_observed_mc.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6g {
struct G18B3UpperChoice {
    int iupt=-1; // original CALMET -1: each cell's NEARU; >0: one US
    std::vector<int> nearu; // source station ordinal, 1-based, not ID
    bool independently_fortran_verified=false;
};
inline int g18b3_parse_original_iupt(const std::string& metinp,
                                     std::size_t upper_count) {
    if(upper_count==0||upper_count>1000)
        throw std::invalid_argument("G18B3 upper station count invalid");
    const auto value=source_wind_normalize(source_wind_value(metinp,"IUPT"));
    std::size_t used=0;int requested=0;
    try{requested=std::stoi(value,&used);}
    catch(const std::exception&){
        throw std::invalid_argument("G18B3 noninteger source met.inp IUPT");
    }
    if(used!=value.size()||(requested!=-1&&
       (requested<=0||static_cast<std::size_t>(requested)>upper_count)))
        throw std::invalid_argument("G18B3 original IUPT not a valid US ordinal");
    return requested;
}
inline G18B3UpperChoice g18b3_source_deck_upper_choice(
    const GeoGrid& grid,const StationSet& station_set,
    const std::string& source_metinp) {
    const auto iupt=g18b3_parse_original_iupt(source_metinp,
                                               station_set.upper.size());
    if(grid.nx<2||grid.ny<2||grid.nx>400||grid.ny>400||
       !std::isfinite(grid.grid_km)||grid.grid_km<=0.f||
       station_set.upper.empty()||station_set.upper.size()>1000)
        throw std::invalid_argument("G18B3 grid/UP count outside selected scope");
    const float dgrid=grid.grid_km*1000.f;
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    G18B3UpperChoice out;
    out.iupt=iupt;
    out.nearu.resize(nx*ny);
    // Same REAL*4 gridpoint convention as source-backed G17B SETCOM
    // NEARS: (I-.5)*DGRID, (J-.5)*DGRID, strict '<' keeps first tie.
    // Verification of the original CALMET NEARU selector is still required:
    // never mark this unreviewed multi-US mapping as vendor accepted.
    for(std::size_t i=1;i<=nx;++i) {
        const float x=(static_cast<float>(i)-0.5f)*dgrid;
        for(std::size_t j=1;j<=ny;++j) {
            const float y=(static_cast<float>(j)-0.5f)*dgrid;
            float shortest=1.e37f;
            int ordinal=0;
            for(std::size_t s=0;s<station_set.upper.size();++s){
                const auto& st=station_set.upper[s];
                if(st.id<=0||!std::isfinite(st.local_x_m)||
                   !std::isfinite(st.local_y_m))
                    throw std::invalid_argument("G18B3 invalid original upper station identity/UTM");
                const float dx=st.local_x_m-x;
                const float dy=st.local_y_m-y;
                const float d2=dx*dx+dy*dy;
                if(!std::isfinite(d2))
                    throw std::invalid_argument("G18B3 upper station distance overflow");
                if(d2<shortest){shortest=d2;ordinal=static_cast<int>(s)+1;}
            }
            if(ordinal<1)
                throw std::invalid_argument("G18B3 no valid UP station for cell");
            out.nearu[(j-1)*nx+(i-1)]=ordinal;
        }
    }
    return out;
}
inline void g18b3_bind_test_only_upper_choice(
    p6e::MixhtObservedMcInput& mixed,const GeoGrid& grid,
    const StationSet& stations,const G18B3UpperChoice& choice,
    bool explicitly_test_only) {
    const auto n=static_cast<std::size_t>(grid.nx)*
                 static_cast<std::size_t>(grid.ny);
    if(!explicitly_test_only||choice.independently_fortran_verified||
       choice.nearu.size()!=n||(choice.iupt!=-1&&
       (choice.iupt<1||static_cast<std::size_t>(choice.iupt)>stations.upper.size())))
        throw std::invalid_argument("G18B3 NEARU source parity still not accepted");
    for(const int ordinal:choice.nearu)
        if(ordinal<=0||static_cast<std::size_t>(ordinal)>stations.upper.size())
            throw std::invalid_argument("G18B3 NEARU index outside original US count");
    mixed.iupt=choice.iupt;
    mixed.nearu=choice.nearu;
}
} // namespace cteas::calmet::p6g
