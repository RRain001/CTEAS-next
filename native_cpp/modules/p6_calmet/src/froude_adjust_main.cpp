#include "cteas/p6/froude_adjust.hpp"
#include "cteas/p6/terrain_envelope.hpp"
#include <array>
#include <cstddef>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc,char** argv){
    if(argc!=6){
        std::cerr<<"usage: cteas_p6_fradj INPUT.txt OUT.csv TERRAD_KM CRITFN ISURFT\n";
        return 2;
    }
    try {
        std::ifstream in(argv[1]);
        if(!in)throw std::runtime_error("FRADJ source unavailable");
        constexpr int nx=50,ny=50,nz=9;
        constexpr std::size_t cells=2500,count=22500;
        const std::array<float,10> face={0,20,40,80,160,320,640,1200,2000,3000};
        std::vector<float> terrain(cells),gamma(cells),temp(cells);
        cteas::calmet::p6::WindUV winds{
            std::vector<float>(count),std::vector<float>(count)};
        auto next=[&](std::vector<float>& v){
            for(float& x:v)if(!(in>>x))throw std::runtime_error("truncated FRADJ input");
        };
        next(terrain);next(gamma);next(temp);next(winds.u);next(winds.v);
        std::string extra;
        if(in>>extra)throw std::runtime_error("unexpected FRADJ fields");
        const auto env=cteas::calmet::p6::terset(
            terrain,nx,ny,100.0f,100.0f,std::stof(argv[3]));
        winds=cteas::calmet::p6::froude_adjust(
            nx,ny,nz,100.0f,100.0f,
            terrain,env.maximum_m,gamma,temp,
            std::stoi(argv[5]),285.0f,std::stof(argv[4]),
            std::vector<float>(face.begin(),face.end()),std::move(winds));
        std::ofstream out(argv[2]);
        if(!out)throw std::runtime_error("cannot open FRADJ output");
        out<<"i,j,k,u_mps,v_mps\n"<<std::fixed<<std::setprecision(8);
        for(int k=0;k<nz;++k)for(int j=0;j<ny;++j)for(int i=0;i<nx;++i){
            const auto n=std::size_t(k)*cells+std::size_t(j)*50+std::size_t(i);
            out<<i+1<<','<<j+1<<','<<k+1<<','<<winds.u[n]<<','<<winds.v[n]<<'\n';
        }
        if(!out)throw std::runtime_error("FRADJ output incomplete");
        std::cout<<"P6D_FRADJ_CANDIDATE_ONLY fields=45000\n";
        return 0;
    }catch(const std::exception& ex){
        std::cerr<<"P6D_FRADJ_ERROR: "<<ex.what()<<'\n';return 1;
    }
}
