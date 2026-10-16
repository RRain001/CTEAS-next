#include "cteas/p6e/elustr_stable.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
    int cases=0,nx=0,ny=0,ns=0;
    if(!(std::cin>>cases>>nx>>ny>>ns)||cases<1||nx<1||ny<1||ns<1)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c){
        cteas::p6e::StableElustr x;
        x.nx=static_cast<std::size_t>(nx);x.ny=static_cast<std::size_t>(ny);
        if(!(std::cin>>x.mcloud>>x.water_first>>x.water_last>>x.zm))return 3;
        x.station_cloud.resize(static_cast<std::size_t>(ns));
        for(int s=0;s<ns;++s)
            if(!(std::cin>>x.station_cloud[static_cast<std::size_t>(s)]))return 4;
        const auto n=x.nx*x.ny;
        x.landuse.resize(n);x.nearest.resize(n);x.z0.resize(n);
        x.u1.resize(n);x.v1.resize(n);x.rho.resize(n);
        x.temp_k.resize(n);x.cloud_grid.resize(n);x.heat_flux_initial.resize(n);
        for(std::size_t i=0;i<x.nx;++i)for(std::size_t j=0;j<x.ny;++j){
            const auto k=j*x.nx+i;
            if(!(std::cin>>x.z0[k]>>x.u1[k]>>x.v1[k]>>x.rho[k]
                 >>x.temp_k[k]>>x.cloud_grid[k]>>x.landuse[k]
                 >>x.nearest[k]>>x.heat_flux_initial[k]))return 5;
        }
        try{
            const auto r=cteas::p6e::stable_elustr(x);
            for(std::size_t i=0;i<x.nx;++i)for(std::size_t j=0;j<x.ny;++j){
                const auto k=j*x.nx+i;
                std::cout<<c<<' '<<i+1<<' '<<j+1<<' '
                         <<r.qh_wm2[k]<<' '<<r.ustar_ms[k]
                         <<' '<<r.monin_obukhov_m[k]<<'\n';
            }
        } catch(const std::exception& e){
            std::cerr<<"P6E ELUSTR "<<e.what()<<'\n';return 6;
        }
    }
}
