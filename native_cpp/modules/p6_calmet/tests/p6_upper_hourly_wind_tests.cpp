#include "cteas/p6/upper_hourly_wind.hpp"
#include <chrono>
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace cteas::calmet::p6;
static void check(bool x,const char* msg){if(!x)throw std::runtime_error(msg);}
int main(){
 try{
   using namespace std::chrono;
   Upper2022 profiles;
   auto start=sys_seconds{sys_days{year{2022}/January/1}};
   for(int i=0;i<3;i++){
       UpperSounding s;s.end=start+hours{i*12};s.start=s.end;s.levels=2;
       profiles.soundings.push_back(s);
   }
   std::vector<std::vector<LayerWind>> winds(3,
      std::vector<LayerWind>(2));
   for(int i=0;i<3;i++){
       winds[i][0].u_mps=10.0f*i;
       winds[i][0].v_mps=-20.0f*i;
       winds[i][1].u_mps=1.0f+i;
       winds[i][1].v_mps=2.0f+i;
   }
   auto first=calmet_prepdi_hour(profiles,start+hours{1},winds);
   check(first.prior_sounding==0&&first.following_sounding==1&&
         first.past_seconds==3600&&first.to_go_seconds==39600&&
         first.gap_seconds==43200,"PREPDI first hour bracket end time");
   check(std::abs(first.winds[0].u_mps-10.0f/12)<0.0001f,
         "PREPDI first hour U linear ratio");
   auto twelve=calmet_prepdi_hour(profiles,start+hours{12},winds);
   check(twelve.prior_sounding==1&&twelve.following_sounding==2 &&
         twelve.past_seconds==0 && twelve.to_go_seconds==43200,
         "PREPDI exact sounding time selected as later interval origin");
   check(twelve.winds[0].u_mps==10.0f && twelve.winds[0].v_mps==-20.0f,
         "PREPDI exact sounding winds");
   auto last=calmet_prepdi_hour(profiles,start+hours{23},winds);
   check(last.prior_sounding==1&&last.following_sounding==2,
         "PREPDI late within next 12h interval");
   auto at_start=calmet_prepdi_hour(profiles,start,winds);
   check(at_start.prior_sounding==0 && at_start.past_seconds==0,
         "PREPDI exact initial 00 sounding is mathematically bracketed");
   bool failed=false;
   try{(void)calmet_prepdi_hour(profiles,start+hours{25},winds);}
   catch(const std::invalid_argument&){failed=true;}
   check(failed,"PREPDI unbracketed hour must fail");
   profiles.soundings[2].end=start+hours{27};
   failed=false;
   try{(void)calmet_prepdi_hour(profiles,start+hours{13},winds);}
   catch(const std::invalid_argument&){failed=true;}
   check(failed,"PREPDI >24h gap cannot be silently interpolated");
   std::cout<<"PASS_P6C_PREPDI_HOURLY_CHRONOLOGY_SOFTWARE_ONLY\n";
   return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
