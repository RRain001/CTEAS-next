// Standalone source-first INTER2 parity executable, without old P6D includes.
#include "cteas/p6d_rebuild/inter2_real4.hpp"
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc,char** argv){
    try{
        if(argc!=3)
            throw std::invalid_argument("usage: p6d_rebuild_inter2 INPUT OUTPUT_CSV");
        std::ifstream in(argv[1]);
        if(!in)throw std::runtime_error("INTER2 original input unavailable");
        cteas::p6d_rebuild::Inter2SelectedSourceInput c;
        int lvary=0;
        if(!(in>>c.nstations>>lvary>>c.rmin_km>>c.rmax1_km>>
             c.rmax2_km>>c.rmax3_km>>c.r1_km>>c.r2_km>>c.edit>>c.editl))
            throw std::runtime_error("INTER2 original control truncated");
        if(lvary!=0&&lvary!=1)
            throw std::invalid_argument("INTER2 invalid LVARY");
        c.lvary=lvary==1;
        for(auto& value:c.nintrp)
            if(!(in>>value))throw std::runtime_error("INTER2 NINTRP truncated");
        if(c.nstations<=0||c.nstations>479)
            throw std::invalid_argument("INTER2 station count out of selected scope");
        auto read=[&](auto& vec,std::size_t n){
            vec.resize(n);
            for(auto& value:vec)
                if(!(in>>value))throw std::runtime_error("INTER2 input field truncated");
        };
        const auto ns=static_cast<std::size_t>(c.nstations);
        read(c.station_x_km,ns);read(c.station_y_km,ns);
        read(c.landuse,2500);read(c.observations,9*ns);
        read(c.first_guess,22500);read(c.wo,22500);
        std::string extra;
        if(in>>extra)throw std::runtime_error("unexpected INTER2 input");
        const auto result=cteas::p6d_rebuild::inter2_source_real4(c);
        std::ofstream out(argv[2]);
        if(!out)throw std::runtime_error("cannot write INTER2 result");
        out<<std::setprecision(12)<<"i,j,k,component_mps,station_count,fallback\n";
        for(int k=0;k<9;++k)for(int j=0;j<50;++j)for(int i=0;i<50;++i){
            const auto ix=static_cast<std::size_t>(k)*2500+
                static_cast<std::size_t>(j)*50+static_cast<std::size_t>(i);
            out<<i+1<<','<<j+1<<','<<k+1<<','
               <<result.field[ix]<<','<<result.contributors[ix]<<','
               <<result.lvary_fallback[ix]<<'\n';
        }
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P6D_INTER2_REBUILD_FAIL: "<<e.what()<<'\n';
        return 1;
    }
}
