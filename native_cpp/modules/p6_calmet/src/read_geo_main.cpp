#include "cteas/p6/read_geo.hpp"
#include <cstddef>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
int main(int argc,char** argv){
    if(argc!=5){
        std::cerr<<"usage: cteas_p6_read_geo GEO.DAT OUT.csv ORIGINAL_XORIGKM ORIGINAL_YORIGKM\n";
        return 2;
    }
    try {
        auto geo=cteas::calmet::p6::read_geo_50(argv[1],
            std::stod(argv[3]),std::stod(argv[4]));
        std::ofstream out(argv[2]);
        if(!out)throw std::runtime_error("cannot write P6C GEO field CSV");
        out<<"i,j,landuse,elevation_m,z0_m,albedo,bowen,hcg,qf,lai\n";
        out<<std::fixed<<std::setprecision(9);
        for(int j=0;j<50;++j)for(int i=0;i<50;++i){
            const auto n=static_cast<std::size_t>(j*50+i);
            out<<i+1<<','<<j+1<<','<<geo.landuse[n]<<','
               <<geo.terrain_m[n]<<','<<geo.z0_m[n]<<','
               <<geo.albedo[n]<<','<<geo.bowen[n]<<','
               <<geo.hcg[n]<<','<<geo.qf[n]<<','<<geo.lai[n]<<'\n';
        }
        if(!out)throw std::runtime_error("P6C GEO output incomplete");
        std::cout<<"P6C_READGE_SELECTED_PATH_CANDIDATE_ONLY 2500 cells, 8 fields\n";
        return 0;
    }catch(const std::exception& ex){
        std::cerr<<"P6C_READGE_ERROR: "<<ex.what()<<'\n';
        return 1;
    }
}
