#include "cteas/p6/temperature_faces.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
using namespace cteas::calmet::p6;
static void chk(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
int main(){
 try{
   UpperSounding s;
   for(int i=0;i<5;i++){
       UpperLevel v;
       v.height_lgl_m=100.f*i;
       v.temperature_k=300.f-2.f*i;
       s.data.push_back(v);
   }
   const auto values=calmet_facet_temperatures(s,{0,20,100,200,300});
   chk(values.size()==5&&values[0]==300.f&&values[2]==298.f,
       "FACET at exact first/boundary sounding temp");
   chk(std::abs(values[1]-299.6f)<0.0001f,
       "FACET interpolation linear 0–100 m");
   s.data[1].temperature_k=999.9f;
   auto miss=calmet_facet_temperatures(s,{0,20,100,200});
   chk(std::abs(miss[1]-299.6f)<0.0001f,
       "INTP missing inner temperature uses farther valid bracket");
   s.data[0].temperature_k=999.9f;
   bool bad=false;
   try{(void)calmet_facet_temperatures(s,{0,20});}
   catch(const std::invalid_argument&){bad=true;}
   chk(bad,"FACET bottom missing must fail closed");
   std::cout<<"PASS_P6C_FACET_INTP_SOFTWARE_ONLY\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
