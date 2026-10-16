#include "cteas/p6/read_upper.hpp"
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
int main(int argc,char** argv){
  if(argc!=4){std::cerr<<"usage: cteas_p6_read_upper UP.DAT OUTPUT.csv STATION_ID\n";return 2;}
  try{
    const auto up=cteas::calmet::p6::read_upper_2022(argv[1],std::stoi(argv[3]));
    std::ofstream out(argv[2]);
    if(!out)throw std::runtime_error("upper CSV cannot be created");
    out<<"station_id,epoch_begin,epoch_end,level,nlevels,"
          "pressure_hpa,height_msl_m,temperature_k,wd_deg,ws_mps,"
          "height_lgl_m,u_mps,v_mps,height_valid,temp_valid,wind_valid\n";
    out<<std::fixed<<std::setprecision(8);
    std::size_t count=0,missing_wind=0;
    for(const auto& sounding:up.soundings){
      for(std::size_t i=0;i<sounding.data.size();i++){
        const auto& v=sounding.data[i];
        out<<sounding.station_id<<','<<sounding.start.time_since_epoch().count()
           <<','<<sounding.end.time_since_epoch().count()<<','<<i+1
           <<','<<sounding.data.size()<<','<<v.pressure_hpa<<','
           <<v.height_msl<<','<<v.temperature_k<<','
           <<v.wd_deg<<','<<v.ws_mps<<','
           <<v.height_lgl_m<<','<<v.u_mps<<','<<v.v_mps<<','
           <<v.height_valid<<','<<v.temperature_valid<<','<<v.wind_valid<<'\n';
        count++;missing_wind+=!v.wind_valid;
      }
    }
    if(!out)throw std::runtime_error("upper CSV incomplete");
    std::cout<<"P6C_UP_READER soundings="<<up.soundings.size()
             <<" levels="<<count<<" missing_wind_levels="<<missing_wind
             <<" RDUPN_SELECTED_INPUT_CANDIDATE_ONLY\n";return 0;
  }catch(const std::exception& e){
    std::cerr<<"P6C_UP_ERROR "<<e.what()<<'\n';return 1;
  }
}
