#include "cteas/p6e/mixht_stable.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
    int cases=0,nx=0,ny=0;
    if(!(std::cin>>cases>>nx>>ny)||cases<1||nx<1||ny<1)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c) {
        cteas::p6e::StableMixingInput x;
        x.nx=static_cast<std::size_t>(nx);x.ny=static_cast<std::size_t>(ny);
        if(!(std::cin>>x.water_first>>x.water_last>>x.constn
            >>x.zimin>>x.zimax))return 3;
        const auto n=x.nx*x.ny;
        x.landuse.resize(n);x.qh_wm2.resize(n);x.ustar_ms.resize(n);
        x.el_m.resize(n);x.fcori_s.resize(n);x.initial_zi_m.resize(n);
        x.initial_ziconv_m.resize(n);
        for(std::size_t i=0;i<x.nx;++i)for(std::size_t j=0;j<x.ny;++j){
            const auto k=j*x.nx+i;
            if(!(std::cin>>x.qh_wm2[k]>>x.ustar_ms[k]>>x.el_m[k]
                 >>x.fcori_s[k]>>x.landuse[k]>>x.initial_zi_m[k]
                 >>x.initial_ziconv_m[k]))return 4;
        }
        try{
            auto r=cteas::p6e::mixht_stable(x);
            for(std::size_t i=0;i<x.nx;++i)for(std::size_t j=0;j<x.ny;++j){
                const auto k=j*x.nx+i;
                std::cout<<c<<' '<<i+1<<' '<<j+1<<' '
                         <<r.zi_m[k]<<' '<<r.ziconv_m[k]<<'\n';
            }
        }catch(const std::exception& e){
            std::cerr<<"P6E MIXHT "<<e.what()<<'\n';return 5;
        }
    }
}
