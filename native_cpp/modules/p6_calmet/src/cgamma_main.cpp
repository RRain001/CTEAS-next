#include "cteas/p6/cgamma.hpp"
#include <chrono>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace cteas::calmet::p6;
int main(int argc,char** argv){
 if(argc!=5) {
  std::cerr<<"usage: cteas_p6_cgamma UP.DAT ORIGINAL_CGAMMA_FORCING.csv OUT.csv STATION_ID\n";
  return 2;
 }
 try{
  const auto upper=read_upper_2022(argv[1],std::stoi(argv[4]));
  const std::vector<float> faces{0,20,40,80,160,320,640,1200,2000,3000};
  const auto timeline=comp_selected_2022_hours(upper,faces);
  std::ifstream in(argv[2]);
  std::ofstream out(argv[3]);
  if(!in||!out)throw std::runtime_error("CGAMMA source forcing/output unavailable");
  std::string line;
  if(!std::getline(in,line))
    throw std::runtime_error("CGAMMA forcing header missing");
  if(!line.empty()&&line.back()=='\r')line.pop_back();
  if(line!="hour_index,end_epoch_s,zupt_m,ziconv_m,original_gamma")
    throw std::runtime_error("CGAMMA expected exact original forcing schema");
  CGammaState state;
  out<<"hour_index,end_epoch_s,zupt_m,ziconv_m,candidate_gamma,branch\n";
  out<<std::fixed<<std::setprecision(10);
  std::size_t n=0;
  while(std::getline(in,line)) {
    if(line.empty())continue;
    if(n>=143)throw std::runtime_error("CGAMMA forcing longer than 143h");
    std::istringstream row(line);
    std::string token;std::vector<std::string> cols;
    while(std::getline(row,token,','))cols.push_back(token);
    if(cols.size()!=5)throw std::runtime_error("CGAMMA forcing malformed row");
    const auto ix=std::stoi(cols[0]);
    const auto epoch=std::stoll(cols[1]);
    const auto zupt=std::stof(cols[2]);
    const auto conv=std::stof(cols[3]);
    if(ix!=static_cast<int>(n+1) ||
       epoch!=timeline[n].interpolated.end.time_since_epoch().count())
       throw std::runtime_error("CGAMMA source clock mismatch");
    const auto value=state.calculate(upper,timeline[n],zupt,conv);
    out<<ix<<','<<epoch<<','<<zupt<<','<<conv<<','
       <<value.kelvin_per_m<<','<<value.branch<<'\n';
    ++n;
  }
  if(n!=143||!out)throw std::runtime_error("CGAMMA forcing incomplete");
  std::cout<<"P6C_SELECTED_CGAMMA_ORIGINAL_ZICONV_ROWS="<<n
           <<" VERTICAL_T_LAPSE_STATE_CANDIDATE\n";
  return 0;
 }catch(const std::exception& e) {
  std::cerr<<"P6C_CGAMMA_ERROR: "<<e.what()<<'\n';return 1;
 }
}
