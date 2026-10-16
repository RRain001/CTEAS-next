// G18D7: real G18D7 station cell helper, compared independently with
// literal original CALMET DIAGI REAL*4 assignments and DIAGNO clamping.
#include "cteas/p6/p6g_g18d7_source_station_cell.hpp"
#include <cstddef>
#include <iostream>
#include <stdexcept>

int main() {
    using cteas::calmet::p6g::GeoGrid;
    using cteas::calmet::p6::DeckStation;
    using cteas::calmet::p6g::g18d7_source_diagi_station_cell;
    std::size_t count=0;
    if(!(std::cin>>count)||count==0||count>10000) return 2;
    try {
        for(std::size_t k=0;k<count;++k) {
            GeoGrid grid{};
            DeckStation station{};
            float dgrid_m=0.f;
            if(!(std::cin>>grid.nx>>grid.ny>>dgrid_m>>
                              station.local_x_m>>station.local_y_m))
                return 3;
            grid.grid_km=dgrid_m/1000.f;
            const auto cell=g18d7_source_diagi_station_cell(grid,station);
            const auto nx=static_cast<std::size_t>(grid.nx);
            std::cout<<(cell%nx+1)<<" "<<(cell/nx+1)<<"\n";
        }
    } catch(const std::exception& e) {
        std::cerr<<"G18D7_SOURCE_SCOPE_REJECT "<<e.what()<<"\n";
        return 4;
    }
    return 0;
}
