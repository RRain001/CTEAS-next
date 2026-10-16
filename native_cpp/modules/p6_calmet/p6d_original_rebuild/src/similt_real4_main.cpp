// Standalone independent source-first original SIMILT, not a wrapper over
// the previous OMP-authored P6D implementation. Input/output contract equals
// native_cpp/modules/p6_calmet/reference/compare_original_similt_profile.py.
#include "cteas/p6d_rebuild/similt_profile_real4.hpp"
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc,char** argv){
    try{
        if(argc!=3)throw std::invalid_argument(
            "usage: p6d_rebuild_similt_real4 INPUT OUTPUT");
        std::ifstream in(argv[1]);
        if(!in)throw std::runtime_error("cannot read original SIMILT input");
        cteas::p6d_rebuild::SimiltReal4Input p;
        int iextrp=0;
        if(!(in>>p.latitude_deg>>p.anemometer_height_m>>p.roughness_m
              >>p.measured_u_mps>>p.measured_v_mps
              >>p.monin_obukhov_length_m>>p.mixing_height_m
              >>p.minimum_mixing_height_m>>iextrp>>p.ipsifcn))
            throw std::runtime_error("original SIMILT state incomplete");
        if(iextrp!=-4)
            throw std::invalid_argument("only original IEXTRP=-4 scoped input");
        for(auto& f:p.zface_m)
            if(!(in>>f))throw std::runtime_error("SIMILT ZFACE incomplete");
        std::string extra;
        if(in>>extra)throw std::invalid_argument("extra SIMILT input tokens");
        const auto result=cteas::p6d_rebuild::similt_source_real4(p);
        std::ofstream out(argv[2]);
        if(!out)throw std::runtime_error("cannot write original SIMILT output");
        out<<result.levels_filled<<'\n';
        out<<std::scientific<<std::setprecision(13);
        for(std::size_t k=0;k<cteas::p6d_rebuild::K;++k)
            out<<k+1<<" "<<result.profile.u_mps[k]<<" "
               <<result.profile.v_mps[k]<<'\n';
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P6D_SOURCE_SIMILT_FAIL: "<<e.what()<<'\n';
        return 1;
    }
}
