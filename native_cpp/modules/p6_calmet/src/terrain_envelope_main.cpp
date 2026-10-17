#include "cteas/p6/terrain_envelope.hpp"
#include <cstddef>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc,char** argv){
    if(argc!=5){
        std::cerr<<"usage: cteas_p6_terset INPUT_50x50_ROW_ASCENDING.txt OUT.csv DX_METRES TERRAD_KM\n";
        return 2;
    }
    try {
        std::ifstream in(argv[1]);
        if(!in)throw std::runtime_error("input terrain unavailable");
        std::vector<float> heights(2500);
        for(float& h:heights)if(!(in>>h))throw std::runtime_error("short terrain values");
        std::string extra;
        if(in>>extra)throw std::runtime_error("terrain has trailing fields");
        const float dx=std::stof(argv[3]);
        const float terrad=std::stof(argv[4]);
        auto out=cteas::calmet::p6::terset(heights,50,50,dx,dx,terrad);
        std::ofstream file(argv[2]);
        if(!file)throw std::runtime_error("cannot create output");
        file<<"i,j,hmax_m,hmin_m,disthmax_m,disthmin_m\n";
        file<<std::fixed<<std::setprecision(6);
        for(int j=0;j<50;++j)for(int i=0;i<50;++i){
            const std::size_t n=std::size_t(j)*50+std::size_t(i);
            file<<i+1<<','<<j+1<<','<<out.maximum_m[n]<<','
                <<out.minimum_m[n]<<','<<out.distance_to_maximum_m[n]
                <<','<<out.distance_to_minimum_m[n]<<'\n';
        }
        if(!file)throw std::runtime_error("output incomplete");
        std::cout<<"PASS_P6C_SOURCE_KERNEL_TERSET_CANDIDATE_ONLY cells=2500 radius_km="
                 <<terrad<<"\n";
        return 0;
    }catch(const std::exception& ex){
        std::cerr<<"P6_TERSET_ERROR: "<<ex.what()<<'\n';
        return 1;
    }
}
