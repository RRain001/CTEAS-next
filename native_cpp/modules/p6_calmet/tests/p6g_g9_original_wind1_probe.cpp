// G9 independent source-lift WIND1 reference fixture. Fortran driver builds
// from the actual vendor calmet.for L36204-L36397 (unchanged source lines).
#include "cteas/p6/p6g_multi_wind1_firstguess.hpp"
#include <iomanip>
#include <iostream>
#include <string>

int main(int argc,char** argv) {
    const bool expanded=argc==2 && std::string(argv[1])=="expanded";
    if(argc>2||(argc==2&&!expanded))return 2;
    using cteas::calmet::p6g::Wind1MultiInput;
    using cteas::calmet::p6g::multi_station_wind1_firstguess;
    Wind1MultiInput in;
    in.nx=expanded?12:3;in.ny=expanded?12:3;in.nz=expanded?9:3;
    in.spacing_m=10000.f;
    in.surface_count=2;in.upper_count=2;in.icalm=0;
    in.station_x_m={10000.f,expanded?100000.f:30000.f,
                    20000.f,expanded?90000.f:50000.f};
    in.station_y_m={10000.f,expanded?100000.f:40000.f,
                    20000.f,expanded?90000.f:50000.f};
    in.surface_speeds_mps={0.f,5.f};
    in.vertical_bias.assign(static_cast<std::size_t>(in.nz),0.f);
    in.vertical_bias[1]=0.3f;in.vertical_bias[2]=-0.2f;
    in.station_u_mps.resize(static_cast<std::size_t>(in.nz)*4);
    in.station_v_mps.resize(static_cast<std::size_t>(in.nz)*4);
    in.present.assign(static_cast<std::size_t>(in.nz)*4,1);
    for(int k=0;k<in.nz;++k){
        in.station_u_mps[k*4+0]=0.f;
        in.station_v_mps[k*4+0]=0.f;
        in.station_u_mps[k*4+1]=3.f;
        in.station_v_mps[k*4+1]=4.f;
        in.station_u_mps[k*4+2]=5.f;
        in.station_v_mps[k*4+2]=-2.f;
        in.station_u_mps[k*4+3]=9.f;
        in.station_v_mps[k*4+3]=10.f;
    }
    in.present[1*4+3]=0;
    in.station_u_mps[1*4+3]=999999.f;
    in.station_v_mps[1*4+3]=999999.f;
    const auto out=multi_station_wind1_firstguess(in);
    std::cout<<std::scientific<<std::setprecision(9);
    for(int k=0;k<in.nz;++k)
        for(int j=0;j<in.ny;++j)
            for(int i=0;i<in.nx;++i){
                const auto idx=static_cast<std::size_t>(k*in.nx*in.ny+j*in.nx+i);
                std::cout<<"GRID "<<i+1<<" "<<j+1<<" "<<k+1<<" "
                         <<out.u_mps[idx]<<" "<<out.v_mps[idx]<<"\n";
            }
}
