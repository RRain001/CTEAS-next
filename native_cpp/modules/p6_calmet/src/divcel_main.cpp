#include "cteas/p6/divcel.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(int argc,char** argv){
 try{
  if(argc!=4)throw std::invalid_argument("usage: divcel INPUT CSV_OUT DIVMAX_OUT");
  using namespace cteas::calmet::p6;
  DivcelInput in;
  in.nx=50;in.ny=50;in.nz=9;in.dx_m=100;in.dy_m=100;
  std::ifstream f(argv[1]);
  if(!f)throw std::runtime_error("input not found");
  auto read=[&](std::vector<float>& arr,std::size_t n){
    arr.resize(n);
    for(auto& x:arr)if(!(f>>x))throw std::runtime_error("truncated DIVCEL data");
  };
  read(in.dz_m,9);
  read(in.u_mps,22500);read(in.v_mps,22500);read(in.w_mps,25000);
  read(in.ub_west_east_mps,900);read(in.vb_south_north_mps,900);
  const auto out=original_divcel_scoped(in);
  std::ofstream csv(argv[2]),maxf(argv[3]);
  if(!csv||!maxf)throw std::runtime_error("output not writable");
  csv<<std::setprecision(12)<<"i,j,k,div_per_s\n";
  maxf<<std::setprecision(12);
  for(int k=0;k<9;++k) {
    for(int j=0;j<50;++j)for(int i=0;i<50;++i) {
      const auto t=std::size_t(k)*2500+std::size_t(j)*50+std::size_t(i);
      csv<<i+1<<','<<j+1<<','<<k+1<<','<<out.divergence_per_s[t]<<'\n';
    }
    maxf<<k+1<<' '<<out.max_abs_per_s[std::size_t(k)]<<'\n';
  }
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
