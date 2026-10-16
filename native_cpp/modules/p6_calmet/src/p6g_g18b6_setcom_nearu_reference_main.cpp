// G18B6 C++ original SETCOM NEARU numerical oracle.
// stdin: NX NY NUSTA DGRID_M, then source-order US X/Y coordinates in m.
// stdout: nearest upper-station ordinal (1-based) for each grid cell in
// J-major, I-minor order, matching the original Fortran GRID NEARU array.
// It deliberately invokes production G18B3 rather than a test reimplementation.
#include "cteas/p6/p6g_g18b3_upper_choice.hpp"
#include <iostream>
#include <stdexcept>
int main() {
    try {
        int nx=0,ny=0,nu=0;
        float dgrid=0.f;
        if(!(std::cin>>nx>>ny>>nu>>dgrid)||
           nx<2||ny<2||nx>100||ny>100||nu<1||nu>6)
            throw std::invalid_argument("G18B6 invalid source input extent");
        cteas::calmet::p6g::GeoGrid grid;
        grid.nx=nx;grid.ny=ny;grid.grid_km=dgrid/1000.f;
        cteas::calmet::p6g::StationSet stations;
        for(int k=0;k<nu;++k) {
            cteas::calmet::p6::DeckStation us{};
            us.id=58424+k;
            if(!(std::cin>>us.local_x_m>>us.local_y_m))
                throw std::invalid_argument("G18B6 missing original US coordinate");
            stations.upper.push_back(us);
        }
        // A minimal source-equivalent IUPT control is sufficient for
        // SETCOM: IUPT does not modify nearest-US geometry.
        const auto result=cteas::calmet::p6g::g18b3_source_deck_upper_choice(
            grid,stations,"! IUPT = -1 !");
        for(const int nearest:result.nearu)
            std::cout<<nearest<<"\n";
        return 0;
    }catch(const std::exception& ex){
        std::cerr<<"G18B6_CPP_SETCOM_NEARU_FAIL "<<ex.what()<<"\n";
        return 1;
    }
}
