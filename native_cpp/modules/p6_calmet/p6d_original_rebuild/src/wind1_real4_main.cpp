// Standalone independent CALMET WIND1+neutral SIMILT reconstruction.
// Compatible with the original source driver fixture used by
// reference/compare_original_wind1_firstguess.py. Import NO existing
// OMP-authored P6D numerical routines; only the original-source rebuild.
#include "cteas/p6d_rebuild/similt_neutral_real4.hpp"
#include <array>
#include <cmath>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc,char** argv) {
    try {
        if(argc!=3)
            throw std::invalid_argument("usage: p6d_rebuild_wind1_real4 INPUT OUTPUT");
        std::ifstream in(argv[1]);
        if(!in)throw std::runtime_error("cannot open original WIND1 driver input");
        cteas::p6d_rebuild::Wind1Controls c;
        float roughness=0.f,latitude=0.f,zanem=0.f;
        if(!(in>>c.surface.x_m>>c.surface.y_m>>c.upper.x_m>>c.upper.y_m
               >>c.surface_measured_u>>c.surface_measured_v>>roughness
               >>latitude>>zanem>>c.icalm))
            throw std::runtime_error("malformed original WIND1 driver header");
        for(auto& b:c.bias)
            if(!(in>>b))throw std::runtime_error("original WIND1 BIAS incomplete");
        for(std::size_t k=0;k<cteas::p6d_rebuild::K;++k){
            if(!(in>>c.upper.u_mps[k]>>c.upper.v_mps[k]))
                throw std::runtime_error("original WIND1 upper profile incomplete");
        }
        std::string extra;
        if(in>>extra)throw std::runtime_error("unexpected original WIND1 extra input");
        const auto profile=cteas::p6d_rebuild::original_neutral_similt_profile({
            latitude,zanem,roughness,c.surface_measured_u,c.surface_measured_v
        });
        c.surface.u_mps=profile.u_mps;
        c.surface.v_mps=profile.v_mps;
        const auto fields=cteas::p6d_rebuild::wind1_from_original_station_profiles(c);
        std::ofstream out(argv[2]);
        if(!out)throw std::runtime_error("cannot write rebuilt WIND1 source fields");
        out<<std::scientific<<std::setprecision(13);
        const std::size_t plane=static_cast<std::size_t>(c.nx)*static_cast<std::size_t>(c.ny);
        for(int k=0;k<c.nz;++k)for(int j=0;j<c.ny;++j)for(int i=0;i<c.nx;++i){
            const std::size_t p=static_cast<std::size_t>(k)*plane+
                static_cast<std::size_t>(j)*static_cast<std::size_t>(c.nx)+
                static_cast<std::size_t>(i);
            out<<i+1<<" "<<j+1<<" "<<k+1<<" "
               <<fields.u_mps[p]<<" "<<fields.v_mps[p]<<'\n';
        }
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P6D_SOURCE_REBUILD_FAIL: "<<e.what()<<'\n';
        return 1;
    }
}
