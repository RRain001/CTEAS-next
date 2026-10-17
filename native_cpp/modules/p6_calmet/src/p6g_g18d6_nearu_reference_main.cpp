// G18D6 native P6G source SETCOM NEARU CLI for vendor REAL*4 parity.
#include "cteas/p6/p6g_g18b3_upper_choice.hpp"
#include <iostream>
#include <stdexcept>
int main() {
    try {
        int nx=0,ny=0,nsta=0;
        float spacing=0.f;
        if(!(std::cin>>nx>>ny>>nsta>>spacing)||
           nx<2||ny<2||nx>64||ny>64||nsta<1||nsta>8||
           !(spacing>0.f))
            throw std::invalid_argument("G18D6 invalid original NEARU geometry");
        cteas::calmet::p6g::GeoGrid grid;
        grid.nx=nx;grid.ny=ny;grid.grid_km=spacing/1000.f;
        cteas::calmet::p6g::StationSet stations;
        for(int k=0;k<nsta;++k){
            float x=0.f,y=0.f;
            if(!(std::cin>>x>>y))
                throw std::invalid_argument("G18D6 missing original UP station coordinates");
            cteas::calmet::p6::DeckStation st;
            st.id=58001+k;st.local_x_m=x;st.local_y_m=y;
            stations.upper.push_back(st);
        }
        const auto result=cteas::calmet::p6g::g18b3_source_deck_upper_choice(
            grid,stations,"! IUPT = -1 !");
        for(int j=0;j<ny;++j)
            for(int i=0;i<nx;++i)
                std::cout<<result.nearu[static_cast<std::size_t>(j*nx+i)]<<"\n";
    }catch(const std::exception& e){
        std::cerr<<"G18D6_SOURCE_NEARU_ERROR "<<e.what()<<"\n";
        return 1;
    }
    return 0;
}
