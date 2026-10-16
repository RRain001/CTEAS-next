#include "cteas/p6e/wstarr.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
    int cases=0,nx=0,ny=0;
    if(!(std::cin>>cases>>nx>>ny)||cases<1||nx<1||ny<1)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c){
        cteas::p6e::WstarrInput x;
        x.nx=static_cast<std::size_t>(nx);
        x.ny=static_cast<std::size_t>(ny);
        if(!(std::cin>>x.water_first>>x.water_last))return 3;
        const auto n=x.nx*x.ny;
        x.zi_conv_m.resize(n);x.heat_flux_wm2.resize(n);
        x.temp_k.resize(n);x.rho_kgm3.resize(n);
        x.initial_wstar_ms.resize(n);x.landuse.resize(n);
        for(std::size_t i=0;i<x.nx;++i)for(std::size_t j=0;j<x.ny;++j){
            const auto k=j*x.nx+i;
            if(!(std::cin>>x.zi_conv_m[k]>>x.heat_flux_wm2[k]
                >>x.temp_k[k]>>x.rho_kgm3[k]>>x.landuse[k]
                >>x.initial_wstar_ms[k]))return 4;
        }
        try{
            auto z=cteas::p6e::wstarr(x);
            for(std::size_t i=0;i<x.nx;++i)for(std::size_t j=0;j<x.ny;++j){
                const auto k=j*x.nx+i;
                std::cout<<c<<' '<<i+1<<' '<<j+1<<' '<<z[k]<<'\n';
            }
        }catch(const std::exception& e){
            std::cerr<<"P6E WSTARR "<<e.what()<<'\n';return 5;
        }
    }
}
