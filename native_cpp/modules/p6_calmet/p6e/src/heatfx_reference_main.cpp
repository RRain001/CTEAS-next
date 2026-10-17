#include "cteas/p6e/heatfx.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
    int cases=0,nx=0,ny=0,ns=0;
    if(!(std::cin>>cases>>nx>>ny>>ns)||cases<1||nx<1||ny<1||ns<1)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c){
        cteas::p6e::HeatFluxInput a;
        a.nx=static_cast<std::size_t>(nx);a.ny=static_cast<std::size_t>(ny);
        if(!(std::cin>>a.mcloud>>a.water_first>>a.water_last
                     >>a.ha1>>a.ha2>>a.hb1>>a.hb2>>a.hc1
                     >>a.hc2>>a.hc3p1))return 3;
        a.station_cloud.resize(static_cast<std::size_t>(ns));
        for(int k=0;k<ns;++k)
            if(!(std::cin>>a.station_cloud[static_cast<std::size_t>(k)]))return 4;
        auto cells=a.nx*a.ny;
        a.nearest.resize(cells);a.landuse.resize(cells);a.sun.resize(cells);
        a.temp_k.resize(cells);a.cloud_grid.resize(cells);
        a.albedo.resize(cells);a.bowen.resize(cells);
        a.soil_heat_fraction.resize(cells);a.anthropogenic_wm2.resize(cells);
        a.initial_qh.resize(cells);
        for(std::size_t i=0;i<a.nx;++i)
            for(std::size_t j=0;j<a.ny;++j){
                const auto pos=j*a.nx+i;
                if(!(std::cin>>a.sun[pos]>>a.temp_k[pos]>>a.landuse[pos]
                      >>a.nearest[pos]>>a.cloud_grid[pos]>>a.albedo[pos]
                      >>a.bowen[pos]>>a.soil_heat_fraction[pos]
                      >>a.anthropogenic_wm2[pos]>>a.initial_qh[pos]))
                    return 5;
            }
        try{
            const auto r=cteas::p6e::heatfx(a);
            for(std::size_t i=0;i<a.nx;++i)
                for(std::size_t j=0;j<a.ny;++j){
                    const auto k=j*a.nx+i;
                    std::cout<<c<<' '<<i+1<<' '<<j+1<<' '
                             <<r.shortwave_wm2[k]<<' '<<r.sensible_wm2[k]<<'\n';
                }
        }catch(const std::exception& e){
            std::cerr<<"HEATFX "<<e.what()<<'\n';return 6;
        }
    }
}
