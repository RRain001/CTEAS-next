// REAL*4 station MIXHTST forensic driver. Previous COMP state and fluxes
// are provided explicitly from source-locked forensic fixtures; they are
// NOT autonomous inputs and cannot constitute P6D full U/V/W acceptance.
#include "cteas/p6/read_upper.hpp"
#include "cteas/p6/station_mixhtst.hpp"
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc,char** argv){
  try {
    if(argc!=4)throw std::invalid_argument("usage: station_mixhtst_probe UP.DAT INPUT.tsv OUTPUT.csv");
    auto upper=cteas::calmet::p6::read_upper_2022(argv[1],58424);
    std::ifstream in(argv[2]);std::ofstream out(argv[3]);
    if(!in||!out)throw std::runtime_error("station MIXHTST input/output unavailable");
    int expected=0;
    if(!(in>>expected)||expected!=143)throw std::runtime_error("station MIXHTST fixture requires 143 hours");
    out<<"hour,ZI_M,ZICONV_M,DPTT_K\n"<<std::setprecision(10);
    const auto first=std::chrono::sys_days{std::chrono::year{2022}/1/1};
    for(int hour=1;hour<=expected;++hour){
      int h=0;
      cteas::calmet::p6::StationMixhtstInput physics;
      if(!(in>>h>>physics.previous.zi_m>>physics.previous.ziconv_m>>
           physics.previous.dptt_k>>physics.qh_wm2>>physics.ustar_mps>>
           physics.el_m>>physics.rho_kg_m3))
        throw std::runtime_error("station MIXHTST input record missing");
      if(h!=hour)throw std::runtime_error("station MIXHTST reordered hours");
      const auto begin=std::chrono::sys_seconds(first)+std::chrono::hours(hour-1);
      const cteas::calmet::p6::UpperSounding* older=nullptr;
      for(const auto& s:upper.soundings){
        if(s.end<=begin)older=&s;
        else break;
      }
      if(!older)throw std::runtime_error("MIXHTST has no preceding thermal sounding");
      for(const auto& level:older->data){
        if(!level.height_valid)
          throw std::runtime_error("MIXHTST invalid thermal sounding height");
        physics.older_sounding.height_m.push_back(level.height_lgl_m);
        physics.older_sounding.temp_k.push_back(
            level.temperature_valid?level.temperature_k:9999.f);
      }
      physics.fcori_s=1.e-4f;
      physics.cmech=1.41f/std::sqrt(physics.fcori_s);
      physics.izicrlx=1;physics.imixh=1;
      const auto result=cteas::calmet::p6::station_mixhtst(physics);
      out<<hour<<","<<result.zii_to_similt_m<<","
         <<result.ziconv_after_m<<","<<result.dptt_for_comp_k<<"\n";
    }
    std::string extra;
    if(in>>extra)throw std::runtime_error("extra MIXHTST fixture records");
    if(!out)throw std::runtime_error("MIXHTST output failure");
    std::cout<<"P6D_STATION_MIXHTST_FORENSIC_143H_COMPLETE\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
