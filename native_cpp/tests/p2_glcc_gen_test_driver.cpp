// Test-only fixture reader: accepts sparse artificial 156MB source. Never
// issue source acceptance; the production CLI requires a fixed official SHA.
#include "cteas/geo/glcc_raw_fractions.hpp"
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
int main(int argc,char** argv){
  if(argc!=10)return 2;
  try{
    using namespace cteas::reconstruction::geo;
    const int epsg=std::stoi(argv[2]);
    const double x=std::stod(argv[3]),y=std::stod(argv[4]),dx=std::stod(argv[5]);
    const auto nx=std::size_t(std::stoul(argv[6])),ny=std::size_t(std::stoul(argv[7]));
    const int mesh=std::stoi(argv[8]);
    const auto r=compute_glcc_gen_replay(argv[1],{x,y,dx,nx,ny},epsg,mesh);
    // Software-only synthetic replay: enabling optional coordinate QA MUST NOT
    // mutate any production GLCC category hits, grid counts, or coverage.
    const auto traced=compute_glcc_gen_replay(argv[1],{x,y,dx,nx,ny},epsg,mesh,true);
    if(traced.counts!=r.counts||traced.cell_samples!=r.cell_samples||
       traced.included!=r.included||traced.outside!=r.outside||
       traced.raw_pixels!=r.raw_pixels||!r.diagnostic_mesh.empty()||
       traced.diagnostic_mesh.size()!=traced.included+traced.outside){
      std::cerr<<"GLCC_QA_MESH_CHANGED_PRODUCTION_COUNTS\n";return 5;
    }
    std::ofstream out(argv[9]);if(!out)return 3;
    out<<"i,j,samples";
    for(int k:kGlccUsgs92Classes)out<<",cat"<<k;
    out<<"\n"<<std::fixed<<std::setprecision(12);
    for(std::size_t j=0;j<ny;++j)for(std::size_t i=0;i<nx;++i){
      const std::size_t cell=j*nx+i;
      out<<i+1<<","<<j+1<<","<<r.cell_samples[cell];
      for(std::size_t k=0;k<kGlccUsgs92Classes.size();++k){
        if(r.cell_samples[cell])out<<","<<r.fraction(i,j,k);
        else out<<",MISSING";
      }
      out<<"\n";
    }
    if(!out)return 4;
    std::cout<<"TEST_SYNTHETIC_ONLY INCLUDED="<<r.included<<" OUTSIDE="<<r.outside
             <<" GLCC_RAW0="<<r.raw_pixels[0]<<" GLCC_RAW16="<<r.raw_pixels[16]<<"\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
