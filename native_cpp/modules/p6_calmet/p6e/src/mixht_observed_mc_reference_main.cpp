#include "cteas/p6e/mixht_observed_mc.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
    int cases=0,nx=0,ny=0,ns=0,nlev=0;
    if(!(std::cin>>cases>>nx>>ny>>ns>>nlev)||
       cases<1||nx<1||ny<1||ns<1||nlev<2)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c){
        cteas::p6e::MixhtObservedMcInput x;
        x.nx=static_cast<std::size_t>(nx);x.ny=static_cast<std::size_t>(ny);
        if(!(std::cin>>x.iupt>>x.constn>>x.zimin>>x.zimax>>
             x.threshl>>x.dptmin>>x.dzzi>>x.onedte>>x.twodte>>
             x.izicrlx>>x.tzicrlx>>x.timestep_s>>x.imixh))return 3;
        x.justa.resize(static_cast<std::size_t>(ns));
        for(auto& order:x.justa)if(!(std::cin>>order))return 4;
        for(auto& buffer:x.sounding){
            buffer.resize(static_cast<std::size_t>(ns));
            for(auto& station:buffer){
                station.height_m.resize(static_cast<std::size_t>(nlev));
                station.temp_k.resize(static_cast<std::size_t>(nlev));
                for(int k=0;k<nlev;++k)
                    if(!(std::cin>>station.height_m[static_cast<std::size_t>(k)]
                       >>station.temp_k[static_cast<std::size_t>(k)]))return 5;
            }
        }
        const auto n=x.nx*x.ny;
        x.qh.resize(n);x.ustar.resize(n);x.el.resize(n);
        x.rho.resize(n);x.cmech.resize(n);x.fcori.resize(n);
        x.landuse.resize(n);x.nearu.resize(n);
        x.initial_zi.resize(n);x.initial_ziconv.resize(n);
        x.initial_dptt.resize(n);
        for(int i=0;i<nx;++i)for(int j=0;j<ny;++j){
            const auto k=static_cast<std::size_t>(j)*x.nx+static_cast<std::size_t>(i);
            if(!(std::cin>>x.qh[k]>>x.ustar[k]>>x.el[k]>>x.rho[k]>>
                 x.cmech[k]>>x.fcori[k]>>x.landuse[k]>>x.nearu[k]>>
                 x.initial_zi[k]>>x.initial_ziconv[k]>>x.initial_dptt[k]))
                return 6;
        }
        try{
            const auto r=cteas::p6e::mixht_observed_mc(x);
            for(int i=0;i<nx;++i)for(int j=0;j<ny;++j){
                const auto k=static_cast<std::size_t>(j)*x.nx+static_cast<std::size_t>(i);
                std::cout<<c<<' '<<i+1<<' '<<j+1<<' '
                         <<r.zi[k]<<' '<<r.ziconv[k]<<' '<<r.dptt[k]<<'\n';
            }
        }catch(const std::exception& e){
            std::cerr<<"MIXHT source-selected MC: "<<e.what()<<'\n';return 7;
        }
    }
}
