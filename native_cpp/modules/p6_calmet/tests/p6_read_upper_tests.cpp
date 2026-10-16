#include "cteas/p6/read_upper.hpp"
#include <cstdio>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace cteas::calmet::p6;
void check(bool b,const char* m){if(!b)throw std::runtime_error(m);}
void data(const std::string& path,bool missing_height=false,bool duplicate=false){
  std::ofstream out(path);
  out<<"UP.DAT          2.1             Hour Start and End Times with Seconds\n"
     <<"   1\n"
     <<"P6C original-format synthetic data\n"
     <<"NONE    \nUTC+0000\n"
     <<" 2022    1    0    0 2022    6   23    0 500.    2    1\n"
     <<"     F    F    F    F\n";
  for(int r=0;r<2;r++){
    const int d=r==0?1:6, h=r==0?0:12;
    out<<"   6201  "<<std::setw(8)<<58424
       <<"    "<<std::setw(4)<<2022<<std::setw(4)<<1
       <<std::setw(3)<<d<<std::setw(3)<<h<<std::setw(5)<<0
       <<"    "<<std::setw(4)<<2022<<std::setw(4)<<1
       <<std::setw(3)<<d<<std::setw(3)<<(duplicate?0:h)<<std::setw(5)<<0
       <<std::setw(5)<<2<<"   "<<std::setw(5)<<2<<"\n";
    const auto group=[&](float p,int z,float temp,int wd,int ws){
      out<<"   "<<std::fixed<<std::setprecision(1)<<std::setw(6)<<p
         <<"/"<<std::setw(5)<<z<<"/"<<std::setw(5)<<temp
         <<"/"<<std::setw(3)<<wd<<"/"<<std::setw(3)<<ws;
    };
    group(1000,missing_height?9999:120,280.0f,0,0);
    group(500,5500,259.8f,999,999);
    out<<"\n";
  }
}
int main(){
 try{
   const std::string p="p6_test_upper.dat";
   data(p);
   auto up=read_upper_2022(p,58424);
   check(up.soundings.size()==2&&up.soundings[0].levels==2,
         "two snapshot dataset");
   check(up.soundings[0].data[0].wind_valid&&
         up.soundings[0].data[0].u_mps==0&&
         up.soundings[0].data[0].v_mps==0,"zero calm is measured valid");
   check(up.soundings[0].data[1].height_lgl_m==5380,
         "original first-level-relative ZL");
   check(!up.soundings[0].data[1].wind_valid&&
         up.soundings[0].data[1].u_mps==999,
         "999 wind missing separate from calm");
   check(up.soundings[0].data[0].temperature_valid,
         "original Kelvin sounding temp");
   bool thrown=false;
   try{(void)read_upper_2022(p,58321);}
   catch(const std::runtime_error&){thrown=true;}
   check(thrown,"mismatched station identity must reject");
   data(p,true);
   thrown=false;
   try{(void)read_upper_2022(p,58424);}
   catch(const std::runtime_error&){thrown=true;}
   check(thrown,"missing height must not be invented");
   data(p,false,true);
   thrown=false;
   try{(void)read_upper_2022(p,58424);}
   catch(const std::runtime_error&){thrown=true;}
   check(thrown,"non-instantaneous snapshot must reject");
   std::remove(p.c_str());
   std::cout<<"PASS_P6C_UPPER_RDUPN_SOFTWARE_ONLY\n";return 0;
 }catch(const std::exception& ex){
   std::cerr<<"P6C UPTEST "<<ex.what()<<'\n';return 1;
 }
}
