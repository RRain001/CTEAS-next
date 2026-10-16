#include "cteas/p6/upper_hourly_wind.hpp"
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
int main(int argc,char** argv){
 if(argc!=4){std::cerr<<"usage: cteas_p6_upper_hourly UP.DAT OUTPUT.csv STATION_ID\n";return 2;}
 try {
  using namespace cteas::calmet::p6;
  const auto upper=read_upper_2022(argv[1],std::stoi(argv[3]));
  const std::vector<float> faces{0,20,40,80,160,320,640,1200,2000,3000};
  auto hours=calmet_prepdi_2022_hours(upper,faces);
  std::ofstream out(argv[2]);
  if(!out)throw std::runtime_error("PREPDI CSV inaccessible");
  out<<"hour_index,end_epoch_s,aa_sounding,bb_sounding,elapsed_s,to_go_s,gap_s,layer,u_mps,v_mps\n"
     <<std::fixed<<std::setprecision(8);
  for(std::size_t i=0;i<hours.size();++i){
    const auto& h=hours[i];
    for(std::size_t k=0;k<h.winds.size();++k){
     out<<i+1<<','<<h.end.time_since_epoch().count()<<','
        <<h.prior_sounding+1<<','<<h.following_sounding+1<<','
        <<h.past_seconds<<','<<h.to_go_seconds<<','<<h.gap_seconds
        <<','<<k+1<<','<<h.winds[k].u_mps<<','<<h.winds[k].v_mps<<'\n';
    }
  }
  if(!out)throw std::runtime_error("PREPDI CSV write incomplete");
  std::cout<<"P6C_PREPDI_143_HOUR_SELECTED_CASE_CANDIDATE_ONLY n="<<hours.size()<<"\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<"P6C_PREPDI_ERROR: "<<e.what()<<'\n';return 1;}
}
