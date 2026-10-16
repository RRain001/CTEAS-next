// Original FRADJ in isolation: 2022 50x50x9 REAL*4, upstream terrain
// maxima/GAMMA/TEMP2D/first-guess fields supplied by the test fixture.
// This CLI does not call any existing OMP P6D numerical algorithm.
#include "cteas/p6d_rebuild/fradj_real4.hpp"
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc,char** argv){
  try {
    if(argc!=4)throw std::invalid_argument(
        "usage: p6d_original_fradj INPUT OUTPUT ISURFT");
    std::ifstream f(argv[1]);
    if(!f)throw std::runtime_error("cannot open FRADJ source fixture");
    cteas::p6d_rebuild::FradjReal4Input p;
    p.isurft=std::stoi(argv[3]);
    auto read=[&](std::vector<float>& values,std::size_t count){
        values.resize(count);
        for(auto& v:values)
            if(!(f>>v))throw std::runtime_error("FRADJ input truncated");
    };
    read(p.terrain_m,2500);
    read(p.highest_m,2500);
    read(p.gamma_kpm,2500);
    read(p.temp2d_k,2500);
    read(p.u_mps,22500);
    read(p.v_mps,22500);
    std::string tail;
    if(f>>tail)throw std::runtime_error("extra original FRADJ input fields");
    const auto answer=cteas::p6d_rebuild::fradj_source_real4(std::move(p));
    std::ofstream out(argv[2]);
    if(!out)throw std::runtime_error("cannot write FRADJ source parity output");
    out<<std::setprecision(12)<<"i,j,k,u_mps,v_mps\n";
    for(int k=0;k<9;++k)for(int j=0;j<50;++j)for(int i=0;i<50;++i){
        const std::size_t n=static_cast<std::size_t>(k)*2500+
           static_cast<std::size_t>(j)*50+static_cast<std::size_t>(i);
        out<<i+1<<','<<j+1<<','<<k+1<<','
           <<answer.u_mps[n]<<','<<answer.v_mps[n]<<'\n';
    }
    return 0;
  }catch(const std::exception& e){
    std::cerr<<"P6D_FRADJ_SOURCE_REBUILD_FAIL: "<<e.what()<<'\n';
    return 1;
  }
}
