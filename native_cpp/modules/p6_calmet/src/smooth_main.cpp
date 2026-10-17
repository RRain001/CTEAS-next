#include "cteas/p6/smooth.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(int argc,char** argv) {
 try{
  if(argc!=3)throw std::invalid_argument("usage: smooth INPUT OUTPUT");
  using namespace cteas::calmet::p6;
  std::ifstream in(argv[1]);
  if(!in)throw std::runtime_error("input not found");
  SmoothInput s;s.nx=50;s.ny=50;s.nz=9;s.lake_breeze=false;
  auto read=[&](auto& dest,std::size_t n){
    dest.resize(n);for(auto& v:dest)
      if(!(in>>v))throw std::runtime_error("input truncated/invalid");
  };
  read(s.passes_per_layer,9);read(s.u_mps,22500);read(s.v_mps,22500);
  read(s.ub_west_east_mps,900);read(s.vb_south_north_mps,900);
  const auto output=smooth_original_scoped(std::move(s));
  std::ofstream f(argv[2]);
  if(!f)throw std::runtime_error("output not writable");
  f<<std::setprecision(12)<<"i,j,k,u_mps,v_mps\n";
  for(int k=0;k<9;++k)for(int j=0;j<50;++j)for(int i=0;i<50;++i){
    const auto p=std::size_t(k)*2500+std::size_t(j)*50+std::size_t(i);
    f<<i+1<<','<<j+1<<','<<k+1<<','<<output.u_mps[p]<<','
     <<output.v_mps[p]<<'\n';
  }
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
