#include "cteas/p6/divcel.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
int main(){
 try{
  using namespace cteas::calmet::p6;
  DivcelInput in;
  in.nx=3;in.ny=3;in.nz=2;in.dx_m=100;in.dy_m=100;in.dz_m={20,40};
  in.u_mps.assign(18,0);in.v_mps.assign(18,0);in.w_mps.assign(27,0);
  in.ub_west_east_mps.assign(12,0);
  in.vb_south_north_mps.assign(12,0);
  auto a=original_divcel_scoped(in);
  if(a.divergence_per_s.size()!=18||a.max_abs_per_s.size()!=2)
    throw std::runtime_error("DIVCEL wrong 3D shape");
  for(float x:a.divergence_per_s)if(x!=0)throw std::runtime_error("nonzero calm div");
  for(float x:a.max_abs_per_s)if(x!=0)throw std::runtime_error("nonzero calm max");
  // Pure W-face vertical flux: 0.2/20 and 0.4/40 = 0.01 s^-1.
  in.w_mps.assign(27,0);
  for(int p=0;p<9;++p){in.w_mps[9+p]=0.2f;in.w_mps[18+p]=0.6f;}
  a=original_divcel_scoped(in);
  for(float x:a.divergence_per_s)
    if(std::abs(x-0.01f)>1.e-7f)
      throw std::runtime_error("incorrect DWDZ");
  // Boundary conditions, not just interior U/V, enter DIVCEL.
  in.ub_west_east_mps[0]=-2.f;  // layer 1 west boundary j=0
  a=original_divcel_scoped(in);
  if(!(a.divergence_per_s[0]>0.01f))
    throw std::runtime_error("west boundary excluded");
  in.dz_m[0]=std::numeric_limits<float>::quiet_NaN();
  bool rejected=false;
  try{(void)original_divcel_scoped(in);}
  catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("invalid DZ not rejected");
  std::cout<<"PASS P6D_DIVCEL_SOFTWARE_ONLY\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
