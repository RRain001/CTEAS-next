#include "cteas/p6/inter2_selected.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(int argc,char** argv){
 try{
  if(argc!=3)throw std::invalid_argument("usage: inter2 INPUT FIELD_CSV");
  using namespace cteas::calmet::p6;
  std::ifstream f(argv[1]);if(!f)throw std::runtime_error("input missing");
  Inter2SelectedInput in;in.nx=50;in.ny=50;in.nz=9;
  in.dx_m=100;in.dy_m=100;in.iprog=0;in.noobs=0;in.nbar=0;
  in.water_first=50;in.water_last=55;
  int lvary;
  if(!(f>>in.nstations>>lvary>>in.rmin_km>>in.rmax1_km>>
       in.rmax2_km>>in.rmax3_km>>in.r1_km>>in.r2_km>>
       in.edit>>in.editl))throw std::runtime_error("invalid INTER2 control");
  if(in.nstations<1||in.nstations>479||(lvary!=0&&lvary!=1))
    throw std::invalid_argument("unsupported INTER2 station count/LVARY");
  in.lvary=lvary==1;
  auto read=[&](auto& v,std::size_t n) {
    v.resize(n);for(auto& a:v)if(!(f>>a))
      throw std::runtime_error("truncated INTER2 fields");
  };
  read(in.nintrp_per_layer,9);
  read(in.station_x_km,std::size_t(in.nstations));
  read(in.station_y_km,std::size_t(in.nstations));
  read(in.landuse,2500);
  read(in.station_component_mps,9*std::size_t(in.nstations));
  read(in.step1_mps,22500);
  read(in.observation_weight,22500);
  const auto result=original_inter2_selected(in);
  std::ofstream o(argv[2]);if(!o)throw std::runtime_error("output denied");
  o<<std::setprecision(12)<<"i,j,k,component_mps,station_count,fallback\n";
  for(int k=0;k<9;++k)for(int j=0;j<50;++j)for(int i=0;i<50;++i){
    const auto n=std::size_t(k)*2500+std::size_t(j)*50+std::size_t(i);
    o<<i+1<<','<<j+1<<','<<k+1<<','<<result.component_mps[n]<<','
     <<result.contributing_station_count[n]<<','<<result.nearest_fallback_used[n]<<'\n';
  }
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
