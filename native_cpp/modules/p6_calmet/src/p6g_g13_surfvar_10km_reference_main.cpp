// G13: source parity CLI carries the actual grid spacing (metres).
// The older P6E fixture assumes 100 m; it cannot validate 10 km physics.
#include "cteas/p6e/surfvar_multistation.hpp"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main() {
    int cases=0,nx=0,ny=0,ns=0;
    float spacing_m=0.f;
    if(!(std::cin>>cases>>nx>>ny>>ns>>spacing_m)||
       cases<1||nx!=12||ny!=12||ns!=2||
       !std::isfinite(spacing_m)||spacing_m!=10000.f)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c) {
        cteas::p6e::SurfvarMultistationInput x;
        x.nx=static_cast<std::size_t>(nx);
        x.ny=static_cast<std::size_t>(ny);
        x.dgrid_m=spacing_m;  // mandatory, no inherited 100 m default
        if(!(std::cin>>x.irad>>x.numts>>x.trad_grid))return 3;
        x.stations.resize(static_cast<std::size_t>(ns));
        for(auto& s:x.stations)
            if(!(std::cin>>s.x_m>>s.y_m>>s.temp_k>>s.rh_pct))return 4;
        try {
            const auto out=cteas::p6e::surfvar_multistation(x);
            for(int i=0;i<nx;++i)for(int j=0;j<ny;++j) {
                const auto k=static_cast<std::size_t>(j)*x.nx+
                    static_cast<std::size_t>(i);
                std::cout<<c<<' '<<i+1<<' '<<j+1<<' '
                         <<out.temp2d_k[k]<<' '<<out.rh2d_pct[k]
                         <<' '<<out.ipcode2d[k]<<'\n';
            }
        }catch(const std::exception& e) {
            std::cerr<<"G13 10km source SURFVAR "<<e.what()<<'\n';
            return 5;
        }
    }
}
