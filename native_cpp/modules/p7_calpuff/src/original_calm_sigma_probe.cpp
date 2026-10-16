#include "cteas/puff/original_calm_sigma.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
 try{
  std::size_t rows=0;int id=0;
  cteas::puff::OriginalCalmSigmaInput p;
  while(std::cin>>id>>p.sy0>>p.sz0>>p.dt_s>>p.dx_km>>p.uavg>>
        p.sigv>>p.sigw>>p.el>>p.tyidr>>p.tzidr>>p.tzisdr>>p.syh>>p.ayt>>p.thfty){
   const auto s=cteas::puff::original_calm_sigma(p);
   std::cout<<id<<' '<<std::scientific<<std::setprecision(10)
            <<s.sy<<' '<<s.virty<<' '<<s.virdy<<' '
            <<s.sz<<' '<<s.virtz<<' '<<s.virdz<<'\n';
   ++rows;
  }
  if(!std::cin.eof())throw std::invalid_argument("malformed input");
  std::cerr<<"P7_NATIVE_CALM_SIGMA_PROBE=PASS ROWS="<<rows<<'\n';
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P7_NATIVE_CALM_SIGMA_PROBE=FAIL "<<e.what()<<'\n';
  return 1;
 }
}
