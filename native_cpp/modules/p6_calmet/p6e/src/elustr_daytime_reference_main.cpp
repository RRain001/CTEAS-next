#include "cteas/p6e/elustr_daytime.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
    int cases=0,nx=0,ny=0;
    if(!(std::cin>>cases>>nx>>ny)||cases<1||nx<1||ny<1)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c) {
        cteas::p6e::DaytimeElustrInput a;
        a.nx=static_cast<std::size_t>(nx);a.ny=static_cast<std::size_t>(ny);
        if(!(std::cin>>a.ipsifcn>>a.water_first>>a.water_last>>a.zm))return 3;
        const auto n=a.nx*a.ny;
        a.landuse.resize(n);a.z0.resize(n);a.u1.resize(n);a.v1.resize(n);
        a.rho.resize(n);a.temp_k.resize(n);a.heat_flux_initial.resize(n);
        a.initial_ustar.resize(n);a.initial_el.resize(n);
        for(std::size_t i=0;i<a.nx;++i)for(std::size_t j=0;j<a.ny;++j) {
            const auto k=j*a.nx+i;
            if(!(std::cin>>a.z0[k]>>a.u1[k]>>a.v1[k]>>a.rho[k]
                 >>a.temp_k[k]>>a.heat_flux_initial[k]>>a.landuse[k]))
                return 4;
            a.initial_ustar[k]=-7777.f;a.initial_el[k]=-7777.f;
        }
        try{
            auto r=cteas::p6e::elustr_daytime(a);
            for(std::size_t i=0;i<a.nx;++i)for(std::size_t j=0;j<a.ny;++j) {
                const auto k=j*a.nx+i;
                std::cout<<c<<' '<<i+1<<' '<<j+1<<' '
                         <<r.qh_wm2[k]<<' '<<r.ustar_ms[k]
                         <<' '<<r.monin_obukhov_m[k]<<'\n';
            }
        }catch(const std::exception& e){
            std::cerr<<"ELUSTR daytime "<<e.what()<<'\n';return 5;
        }
    }
}
