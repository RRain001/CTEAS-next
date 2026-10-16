// Direct CALMET SLOPE original source-port, independent of old CTEAS physics.
#include "cteas/p6d_rebuild/slope_real4.hpp"
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc,char** argv){
 try{
    if(argc!=3)
        throw std::invalid_argument("usage: original_slope INPUT OUTPUT");
    std::ifstream f(argv[1]);
    if(!f)throw std::runtime_error("original SLOPE fixture unavailable");
    cteas::p6d_rebuild::SlopeReal4Input c;
    if(!(f>>c.nx>>c.ny>>c.nz>>c.dx_m>>c.dy_m>>
         c.iwat1>>c.iwat2>>c.isurft>>c.tinf_k))
        throw std::runtime_error("SLOPE source-scoped controls missing");
    for(auto& z:c.zface_m)
        if(!(f>>z))throw std::runtime_error("SLOPE ZFACE truncated");
    auto read=[&](std::vector<float>& values){
        values.resize(2500);
        for(auto& v:values)
            if(!(f>>v))throw std::runtime_error("SLOPE fields truncated");
    };
    read(c.topo_m);read(c.hmax_m);read(c.hmin_m);
    read(c.disthmax_m);read(c.disthmin_m);
    read(c.qh_w_m2);read(c.temp2d_k);
    c.landuse.resize(2500);
    for(auto& v:c.landuse)
        if(!(f>>v))throw std::runtime_error("SLOPE landuse missing");
    std::string extra;
    if(f>>extra)throw std::runtime_error("SLOPE input trailing fields");
    const auto result=cteas::p6d_rebuild::slope_source_real4(c);
    std::ofstream out(argv[2]);
    if(!out)throw std::runtime_error("SLOPE output cannot be written");
    out<<std::setprecision(12)<<"i,j,k,u_mps,v_mps\n";
    for(int k=0;k<9;++k)for(int j=0;j<50;++j)for(int i=0;i<50;++i){
        const auto idx=static_cast<std::size_t>(k)*2500+
                       static_cast<std::size_t>(j)*50+
                       static_cast<std::size_t>(i);
        out<<i+1<<','<<j+1<<','<<k+1<<','
           <<result.u_mps[idx]<<','<<result.v_mps[idx]<<'\n';
    }
    return 0;
 }catch(const std::exception& e){
    std::cerr<<"P6D_ORIGINAL_SLOPE_REBUILD_FAIL: "<<e.what()<<'\n';
    return 1;
 }
}
