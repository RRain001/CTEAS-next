#include "cteas/p6/similt_profile.hpp"
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(int argc,char**argv){
 try{
  if(argc!=3)throw std::invalid_argument("usage: similt_profile INPUT OUTPUT");
  std::ifstream f(argv[1]);
  if(!f)throw std::runtime_error("SIMILT input missing");
  cteas::calmet::p6::SimiltProfileInput in;
  int iextrp=0;
  if(!(f>>in.station_lat_deg>>in.anemometer_height_m>>in.roughness_m>>
       in.anemometer_u_mps>>in.anemometer_v_mps>>in.obukhov_length_m>>
       in.mixing_height_m>>in.minimum_mixing_height_m>>iextrp>>in.ipsifcn))
    throw std::runtime_error("SIMILT input incomplete");
  // The selected route is the IABS(IEXTRP)=4 similarity branch only.
  if(iextrp!=-4)throw std::runtime_error("SIMILT input must select IEXTRP=-4");
  for(std::size_t k=0;k<10;++k)
    if(!(f>>in.zface_m[k]))throw std::runtime_error("SIMILT zface incomplete");
  const auto o=cteas::calmet::p6::original_similt_profile(in);
  std::ofstream out(argv[2]);
  if(!out)throw std::runtime_error("SIMILT output missing");
  out<<std::setprecision(12);
  out<<o.levels_filled<<'\n';
  for(std::size_t k=0;k<9;++k)
    out<<k+1<<' '<<o.u_mps[k]<<' '<<o.v_mps[k]<<'\n';
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
