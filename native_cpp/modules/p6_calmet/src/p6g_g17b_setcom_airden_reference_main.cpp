// G17B3 selected C++ numeric oracle for original CALMET SETCOM / AIRDEN.
// stdin: NX NY NSSTA dgrid_m, then NSSTA x/y metres, pressure mb,
// then NY rows of NX TEMP2D Kelvin values. stdout: NEARS and RHO
// in row-major (J,I) for direct original Fortran source numerical parity.
#include "cteas/p6/p6g_g17b_setcom_airden.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
int main() {
    try {
        int nx=0,ny=0,ns=0;float dgrid=0.f;
        if(!(std::cin>>nx>>ny>>ns>>dgrid)||
           nx<2||ny<2||nx>100||ny>100||ns<1||ns>6)
            throw std::invalid_argument("G17B3 input header invalid");
        cteas::calmet::p6g::GeoGrid geo;
        geo.nx=nx;geo.ny=ny;geo.grid_km=dgrid/1000.f;
        cteas::calmet::p6g::StationSet deck;
        cteas::calmet::p6g::SurfaceHour hour;
        for(int i=0;i<ns;++i) {
            cteas::calmet::p6::DeckStation station{};
            cteas::calmet::p6::SurfaceObserved obs{};
            station.id=101+i;
            if(!(std::cin>>station.local_x_m>>station.local_y_m>>
                 obs.pressure_mb))
                throw std::invalid_argument("G17B3 missing source station");
            obs.pressure_valid=true;
            deck.surface.push_back(station);
            hour.by_station.push_back(obs);
        }
        std::vector<float> temperature(static_cast<std::size_t>(nx)*ny);
        for(auto& value:temperature)
            if(!(std::cin>>value))
                throw std::invalid_argument("G17B3 TEMP2D incomplete");
        const auto near=cteas::calmet::p6g::source_setcom_nears(geo,deck);
        const auto density=cteas::calmet::p6g::source_airden_nears(
            near,temperature,hour);
        std::cout<<std::scientific<<std::setprecision(10);
        for(std::size_t k=0;k<near.size();++k)
            std::cout<<near[k]<<" "<<density[k]<<"\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"G17B3_SOURCE_NEARS_AIRDEN_FAIL "<<e.what()<<"\n";
        return 1;
    }
}
