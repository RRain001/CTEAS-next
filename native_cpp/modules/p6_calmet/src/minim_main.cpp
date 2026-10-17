#include "cteas/p6/minim.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
int main(int argc,char** argv){
 try {
  if(argc!=4)throw std::invalid_argument("usage: minim INPUT CSV_OUT BOUNDARY_OUT");
  using namespace cteas::calmet::p6;
  std::ifstream f(argv[1]);if(!f)throw std::runtime_error("input not found");
  int niter;float divlim;
  if(!(f>>niter>>divlim))throw std::runtime_error("invalid MINIM control");
  DivcelInput in;in.nx=50;in.ny=50;in.nz=9;in.dx_m=100;in.dy_m=100;
  auto read=[&](std::vector<float>& dst,std::size_t n){
    dst.resize(n);for(auto& x:dst)
      if(!(f>>x))throw std::runtime_error("MINIM input truncated");
  };
  read(in.dz_m,9);read(in.u_mps,22500);read(in.v_mps,22500);
  read(in.w_mps,25000);read(in.ub_west_east_mps,900);
  read(in.vb_south_north_mps,900);
  const auto out=original_minim_scoped(std::move(in),niter,divlim);
  std::ofstream csv(argv[2]),bounds(argv[3]);
  if(!csv||!bounds)throw std::runtime_error("output not writable");
  csv<<std::setprecision(12)<<"i,j,k,u_mps,v_mps,div_per_s\n";
  bounds<<std::setprecision(12);
  for(int k=0;k<9;++k)for(int j=0;j<50;++j)for(int i=0;i<50;++i){
    const auto p=std::size_t(k)*2500+std::size_t(j)*50+std::size_t(i);
    csv<<i+1<<','<<j+1<<','<<k+1<<','<<out.wind.u_mps[p]<<','
       <<out.wind.v_mps[p]<<','<<out.divergence_per_s[p]<<'\n';
  }
  for(int k=0;k<9;++k){
    for(int side=0;side<2;++side){
      for(int j=0;j<50;++j)
        bounds<<"U "<<k+1<<' '<<side+1<<' '<<j+1<<' '<<
          out.wind.ub_west_east_mps[std::size_t(k)*100+std::size_t(side)*50+std::size_t(j)]<<'\n';
      for(int i=0;i<50;++i)
        bounds<<"V "<<k+1<<' '<<side+1<<' '<<i+1<<' '<<
          out.wind.vb_south_north_mps[std::size_t(k)*100+std::size_t(side)*50+std::size_t(i)]<<'\n';
    }
  }
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
