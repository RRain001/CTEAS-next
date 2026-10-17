#include "cteas/p6e/temp3d_observed_land.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main() {
    int cases=0,nx=0,ny=0,nz=0,ns=0;
    if(!(std::cin>>cases>>nx>>ny>>nz>>ns)||
       cases<1||nx<1||ny<1||nz<2||ns<1)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c) {
        cteas::p6e::Temp3dObservedInput a;
        a.nx=static_cast<std::size_t>(nx);
        a.ny=static_cast<std::size_t>(ny);
        a.nz=static_cast<std::size_t>(nz);
        if(!(std::cin>>a.irad>>a.current_hour_utc>>a.dgrid_m))return 3;
        a.face_z_m.resize(static_cast<std::size_t>(nz+1));
        for(auto& v:a.face_z_m)if(!(std::cin>>v))return 4;
        a.justa.resize(static_cast<std::size_t>(ns));
        a.station_x_m.resize(static_cast<std::size_t>(ns));
        a.station_y_m.resize(static_cast<std::size_t>(ns));
        a.aa_face_temp_k.resize(static_cast<std::size_t>(ns*(nz+1)));
        a.bb_face_temp_k.resize(static_cast<std::size_t>(ns*(nz+1)));
        for(int st=0;st<ns;++st)
            if(!(std::cin>>a.justa[static_cast<std::size_t>(st)]
                 >>a.station_x_m[static_cast<std::size_t>(st)]
                 >>a.station_y_m[static_cast<std::size_t>(st)]))return 5;
        for(int st=0;st<ns;++st)for(int k=0;k<=nz;++k){
            const auto p=static_cast<std::size_t>(st*(nz+1)+k);
            if(!(std::cin>>a.aa_face_temp_k[p]>>a.bb_face_temp_k[p]))return 6;
        }
        const auto n=static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny);
        a.surface_temp_k.resize(n);a.convective_zi_m.resize(n);
        for(int i=0;i<nx;++i)for(int j=0;j<ny;++j){
            const auto k=static_cast<std::size_t>(j)*static_cast<std::size_t>(nx)+
                static_cast<std::size_t>(i);
            if(!(std::cin>>a.surface_temp_k[k]>>a.convective_zi_m[k]))return 7;
        }
        try {
            auto y=cteas::p6e::temp3d_observed_land(a);
            for(int i=0;i<nx;++i)for(int j=0;j<ny;++j)for(int k=0;k<nz;++k){
                const auto ix=static_cast<std::size_t>(k)*n+
                    static_cast<std::size_t>(j)*a.nx+static_cast<std::size_t>(i);
                std::cout<<c<<' '<<i+1<<' '<<j+1<<' '<<k+1<<' '<<y[ix]<<'\n';
            }
        }catch(const std::exception& e){
            std::cerr<<"TEMP3D selected observed land "<<e.what()<<'\n';return 8;
        }
    }
}
