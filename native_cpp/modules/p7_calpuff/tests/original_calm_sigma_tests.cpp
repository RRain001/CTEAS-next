#include "cteas/puff/original_calm_sigma.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
int main(){
 try {
  cteas::puff::OriginalCalmSigmaInput p;
  p.sy0=1;p.sz0=1;p.dt_s=360;p.dx_km=.02F;
  p.uavg=.2F;p.sigv=.45F;p.sigw=.25F;p.el=-100;
  p.tyidr=.001F;p.tzidr=.002F;p.tzisdr=.001F;p.syh=550;p.ayt=.1F;p.thfty=5000;
  const auto z=cteas::puff::original_calm_sigma(p);
  if(!(z.sy>1&&z.sz>1&&z.virty>360&&z.virtz>360))
   throw std::runtime_error("calm sigma did not grow");
  p.dt_s=0;
  const auto same=cteas::puff::original_calm_sigma(p);
  if(same.sy!=p.sy0||same.sz!=p.sz0)
   throw std::runtime_error("zero travel did not retain sigma");
  p.el=120;p.dt_s=360;
  const auto stable=cteas::puff::original_calm_sigma(p);
  if(!(stable.sy>1&&stable.sz>1&&stable.sy==z.sy))
   throw std::runtime_error("original stable sigma branch failed");
  std::cout<<"P7_CALM_IDOPT1_NATIVE_SUBSET=PASS ELS_LE_ZERO=YES"
           <<" STABLE_LOG_SECANT=YES FULL_COMP=NOT_ACCEPTED\n";
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P7_CALM_IDOPT1_NATIVE_SUBSET=FAIL "<<e.what()<<'\n';return 1;
 }
}
