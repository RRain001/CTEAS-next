// Standalone original-source DIAGNO tail, independent of old P6D implementation.
// Input/output exactly match unchanged Fortran source-segment oracle driver.
#include "cteas/p6d_rebuild/diagno_tail_real4.hpp"
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc,char** argv){
    try{
        if(argc!=4)
            throw std::invalid_argument("usage: p6d_rebuild_diagno INPUT FIELD_CSV BOUNDARY");
        std::ifstream in(argv[1]);
        if(!in)throw std::runtime_error("cannot open original DIAGNO fixture");
        cteas::p6d_rebuild::DiagnoTailInput c;
        for(auto& value:c.dz_m)
            if(!(in>>value))throw std::runtime_error("DIAGNO DZ truncated");
        for(auto& passes:c.smooth_passes)
            if(!(in>>passes))throw std::runtime_error("DIAGNO NSMTH truncated");
        auto load=[&](std::vector<float>& dst,std::size_t n){
            dst.resize(n);
            for(auto& value:dst)
                if(!(in>>value))throw std::runtime_error("DIAGNO fields truncated");
        };
        load(c.u_mps,22500);load(c.v_mps,22500);
        load(c.ub_mps,900);load(c.vb_mps,900);
        std::string remaining;
        if(in>>remaining)throw std::runtime_error("DIAGNO extra tokens");
        const auto result=cteas::p6d_rebuild::original_diagno_tail_real4(std::move(c));
        std::ofstream out(argv[2]),bc(argv[3]);
        if(!out||!bc)throw std::runtime_error("cannot write DIAGNO source result");
        out<<std::setprecision(12)<<"i,j,k,u,v,div,w_below,w_above\n";
        bc<<std::setprecision(12);
        for(int k=0;k<9;++k)for(int j=0;j<50;++j)for(int i=0;i<50;++i){
            const auto n=static_cast<std::size_t>(k)*2500+
                static_cast<std::size_t>(j)*50+static_cast<std::size_t>(i);
            out<<i+1<<','<<j+1<<','<<k+1<<','<<result.u_mps[n]<<','
               <<result.v_mps[n]<<','<<result.divergence_per_s[n]<<','
               <<result.w_face_mps[n]<<','<<result.w_face_mps[n+2500]<<'\n';
        }
        for(int k=0;k<9;++k)for(int side=0;side<2;++side){
            for(int j=0;j<50;++j)
                bc<<"U "<<k+1<<' '<<side+1<<' '<<j+1<<' '<<
                   result.ub_mps[static_cast<std::size_t>(k)*100+
                      static_cast<std::size_t>(side)*50+
                      static_cast<std::size_t>(j)]<<'\n';
            for(int i=0;i<50;++i)
                bc<<"V "<<k+1<<' '<<side+1<<' '<<i+1<<' '<<
                   result.vb_mps[static_cast<std::size_t>(k)*100+
                      static_cast<std::size_t>(side)*50+
                      static_cast<std::size_t>(i)]<<'\n';
        }
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P6D_DIAGNO_REBUILD_FAIL: "<<e.what()<<'\n';
        return 1;
    }
}
