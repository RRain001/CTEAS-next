#pragma once
// G18D6: selected original SETCOM NEARU(IST,JST) -> station STHEOR
// upper-air ordinal. The underlying G18B3 entire grid NEARU now has
// an independent literal-vendor Fortran REAL*4 numerical parity test.
// Only original pinned IUPT=-1 and inside-GEO land-station branch;
// full G14 production station physics/45-field parity still requires gates.
#include "cteas/p6/p6g_g18b3_upper_choice.hpp"
#include "cteas/p6/p6g_g18d7_source_station_cell.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6g {
inline std::vector<std::size_t> g18d6_station_uppers_from_source_setcom(
    const GeoGrid& grid,const StationSet& stations,
    const std::string& original_metinp,bool explicitly_test_only) {
    const auto choice=g18b3_source_deck_upper_choice(
        grid,stations,original_metinp);
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    const auto n=nx*ny;
    if(!explicitly_test_only||choice.iupt!=-1||
       choice.nearu.size()!=n||grid.landuse.size()!=n||
       stations.surface.size()<2||stations.upper.size()<2)
        throw std::invalid_argument(
            "G18D6 source selected NEARU station STHEOR scope not accepted");
    const float dx=grid.grid_km*1000.f;
    if(!std::isfinite(dx)||dx<=0.f)
        throw std::invalid_argument("G18D6 source DGRID invalid");
    std::vector<std::size_t> indices;
    indices.reserve(stations.surface.size());
    for(const auto& station:stations.surface) {
        if(station.id<=0||!std::isfinite(station.local_x_m)||
           !std::isfinite(station.local_y_m)||
           station.local_x_m<0.f||station.local_y_m<0.f||
           station.local_x_m>=static_cast<float>(nx)*dx||
           station.local_y_m>=static_cast<float>(ny)*dx)
            throw std::invalid_argument(
                "G18D6 STHEOR source station lies outside local GEO");
        // DIAGI REAL*4 division+addition precedes integer truncation.
        // Preserve original STHEOR grid-cell ownership at ULP boundaries.
        const auto cell=g18d7_source_diagi_station_cell(grid,station);
        if(grid.landuse[cell]>=grid.iwat1&&
           grid.landuse[cell]<=grid.iwat2)
            throw std::invalid_argument("G18D6 water station STHEOR not accepted");
        const int ordinal=choice.nearu[cell];
        if(ordinal<1||static_cast<std::size_t>(ordinal)>stations.upper.size())
            throw std::invalid_argument("G18D6 source NEARU upper index invalid");
        indices.push_back(static_cast<std::size_t>(ordinal-1));
    }
    return indices;
}
} // namespace cteas::calmet::p6g
