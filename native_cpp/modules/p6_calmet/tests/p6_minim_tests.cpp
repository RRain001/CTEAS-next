#include "cteas/p6/minim.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
int main() {
 try {
  using namespace cteas::calmet::p6;
  DivcelInput in;in.nx=3;in.ny=3;in.nz=1;in.dx_m=100;in.dy_m=100;
  in.dz_m={20};in.u_mps.assign(9,0);in.v_mps.assign(9,0);
  in.w_mps.assign(18,0);in.ub_west_east_mps.assign(6,0);
  in.vb_south_north_mps.assign(6,0);
  for(int p=0;p<9;++p)in.w_mps[9+p]=0.2f;
  const auto skip=original_minim_scoped(in,0,0);
  for(float u:skip.wind.u_mps)if(u!=0)throw std::runtime_error("NITER=0 changed U");
  for(float v:skip.wind.v_mps)if(v!=0)throw std::runtime_error("NITER=0 changed V");
  const auto a=original_minim_scoped(in,2,0.f);
  bool adjusted=false;
  for(float x:a.wind.u_mps)if(x!=0)adjusted=true;
  for(float x:a.wind.v_mps)if(x!=0)adjusted=true;
  if(!adjusted)throw std::runtime_error("MINIM failed to adjust nonzero DIVCEL");
  for(int j=0;j<3;++j){
    if(a.wind.ub_west_east_mps[std::size_t(j)]!=a.wind.u_mps[std::size_t(j)*3]||
       a.wind.ub_west_east_mps[3+std::size_t(j)]!=a.wind.u_mps[std::size_t(j)*3+2])
       throw std::runtime_error("WINDBC U not refreshed");
  }
  for(int i=0;i<3;++i){
    if(a.wind.vb_south_north_mps[std::size_t(i)]!=a.wind.v_mps[std::size_t(i)]||
       a.wind.vb_south_north_mps[3+std::size_t(i)]!=a.wind.v_mps[6+std::size_t(i)])
       throw std::runtime_error("WINDBC V not refreshed");
  }
  bool rejected=false;
  try{(void)original_minim_scoped(in,2,std::numeric_limits<float>::quiet_NaN());}
  catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("nonfinite DIVLIM accepted");
  std::cout<<"PASS P6D_MINIM_SOFTWARE_ONLY\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
