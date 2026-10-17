#include "cteas/p6e/pgtstb.hpp"
#include <iostream>
#include <stdexcept>
int main(int argc,char**) {
    if(argc!=1)return 2;
    int cases=0,nx=0,ny=0,ns=0;
    if(!(std::cin>>cases>>nx>>ny>>ns)||cases<=0||nx<=0||ny<=0||ns<=0)
        return 3;
    try {
        for(int c=1;c<=cases;++c) {
            cteas::p6e::PgtInput in;
            in.nx=static_cast<std::size_t>(nx);
            in.ny=static_cast<std::size_t>(ny);
            if(!(std::cin>>in.mcloud>>in.water_first>>in.water_last))return 4;
            in.station_cloud.resize(static_cast<std::size_t>(ns));
            in.station_ceil.resize(static_cast<std::size_t>(ns));
            for(int s=0;s<ns;++s)
                if(!(std::cin>>in.station_cloud[static_cast<std::size_t>(s)]
                            >>in.station_ceil[static_cast<std::size_t>(s)]))
                    return 5;
            const auto n=in.nx*in.ny;
            in.u10.resize(n);in.v10.resize(n);in.sinalp.resize(n);
            in.ccgrid.resize(n);in.ceilgrid.resize(n);
            in.landuse.resize(n);in.nearest.resize(n);
            for(std::size_t i=0;i<in.nx;++i)
                for(std::size_t j=0;j<in.ny;++j) {
                    const auto k=j*in.nx+i;
                    if(!(std::cin>>in.u10[k]>>in.v10[k]>>in.sinalp[k]
                                >>in.landuse[k]>>in.nearest[k]
                                >>in.ccgrid[k]>>in.ceilgrid[k]))
                        return 6;
                }
            const auto out=cteas::p6e::pgtstb(in);
            for(std::size_t i=0;i<in.nx;++i)
                for(std::size_t j=0;j<in.ny;++j)
                    std::cout<<c<<' '<<i+1<<' '<<j+1<<' '
                             <<out[j*in.nx+i]<<'\n';
        }
    } catch(const std::exception& e) {
        std::cerr<<"P6E PGTSTB "<<e.what()<<'\n';
        return 7;
    }
}
