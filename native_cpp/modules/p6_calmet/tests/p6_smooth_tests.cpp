#include "cteas/p6/smooth.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
int main() {
 try{
  using namespace cteas::calmet::p6;
  SmoothInput a;a.nx=4;a.ny=3;a.nz=2;
  a.passes_per_layer={0,0};a.u_mps.assign(24,2.f);a.v_mps.assign(24,-1.f);
  a.ub_west_east_mps.assign(12,0.f);a.vb_south_north_mps.assign(16,0.f);
  auto zero=smooth_original_scoped(a);
  for(float x:zero.u_mps)if(x!=2.f)throw std::runtime_error("zero-pass U changed");
  for(float x:zero.v_mps)if(x!=-1.f)throw std::runtime_error("zero-pass V changed");
  a.passes_per_layer={1,0};
  const auto one=smooth_original_scoped(a);
  if(one.u_mps[0]==a.u_mps[0]||one.v_mps[0]==a.v_mps[0])
    throw std::runtime_error("boundary of first layer was ignored");
  for(int n=12;n<24;++n)
    if(one.u_mps[std::size_t(n)]!=a.u_mps[std::size_t(n)]||
       one.v_mps[std::size_t(n)]!=a.v_mps[std::size_t(n)])
      throw std::runtime_error("unselected layer modified");
  a.lake_breeze=true;
  bool rejected=false;
  try{(void)smooth_original_scoped(a);}catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("unsupported lake breeze accepted");
  a.lake_breeze=false;
  a.u_mps[0]=std::numeric_limits<float>::quiet_NaN();
  rejected=false;
  try{(void)smooth_original_scoped(a);}catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("missing U wind accepted");
  std::cout<<"PASS P6D_SMOOTH_SOFTWARE_ONLY\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
