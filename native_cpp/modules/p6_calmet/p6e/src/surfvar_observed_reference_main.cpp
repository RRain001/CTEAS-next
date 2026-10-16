#include "cteas/p6e/surfvar_observed.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
    int n=0,nx=0,ny=0;
    if(!(std::cin>>n>>nx>>ny)||n<1||nx<1||ny<1)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=n;++c){
        cteas::p6e::ObservedSurface s;
        s.nx=static_cast<std::size_t>(nx);
        s.ny=static_cast<std::size_t>(ny);
        if(!(std::cin>>s.station_temp_k>>s.station_rh_percent))return 3;
        try {
            auto x=cteas::p6e::surfvar_one_station(s);
            for(int i=1;i<=nx;++i)
                for(int j=1;j<=ny;++j){
                    const auto k=static_cast<std::size_t>((j-1)*nx+i-1);
                    std::cout<<c<<' '<<i<<' '<<j<<' '<<x.temp_k[k]
                             <<' '<<x.rh_percent[k]<<' '<<x.ipcode[k]<<'\n';
                }
        } catch(const std::exception& e){
            std::cerr<<"SURFVAR selected error: "<<e.what()<<'\n';
            return 4;
        }
    }
}
