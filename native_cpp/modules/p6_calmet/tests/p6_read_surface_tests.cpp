#include "cteas/p6/read_surface.hpp"
#include <cstdio>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace cteas::calmet::p6;
void check(bool ok,const char* what) {if(!ok)throw std::runtime_error(what);}
void fixture(const std::string& path,bool bad_clock=false,bool missing_wind=false){
    std::ofstream f(path);
    f<<"SURF.DAT        2.1             Hour Start and End Times with Seconds\n"
      <<"   1\n"<<"Synthetic P6C zero / missing value test\n"<<"NONE    \n"
      <<"UTC+0000\n"<<" 2022   1   0     0  2022   6  23     0    1\n"
      <<"   58321\n";
    for(int n=0;n<143;++n) {
        const int day=n/24+1;
        const int hr=n%24;
        const int nextday=(n+1)/24+1;
        const int nexthr=(n+1)%24;
        f<<"2022 "<<day<<" "<<hr<<" 0 2022 "<<nextday
         <<" "<<(bad_clock && n==24 ? 10 : nexthr)<<" 0\n";
        if(n==0) f<<"0.0 0.0 9999 0 280 50 1013.0 9999\n";
        else if(n==1&&missing_wind) f<<"9999 9999 9999 9999 9999 9999 9999 9999\n";
        else f<<"3.0 150.0 722 5 285 70 1008.1 0\n";
    }
}
int main(){
    try{
        const std::string path="p6_test_surf.dat";
        fixture(path,false,true);
        auto sf=read_surface_2022(path);
        check(sf.station_id==58321&&sf.hourly.size()==143,"station and record count");
        check(sf.hourly.front().obs.wind_valid,"real calm (0,0) is valid");
        check(!sf.hourly.front().obs.precipitation_code_valid,
              "missing precipitation is not zero precipitation");
        check(!sf.hourly.at(1).obs.wind_valid,"both missing wind values");
        check(sf.hourly.at(2).obs.wind_valid&&sf.hourly.at(2).obs.precipitation_code_valid,
              "zero precipitation code is a valid observed code");
        check(sf.hourly.front().end-sf.hourly.front().start==std::chrono::hours{1},
              "hour interval");
        fixture(path,true,false);
        bool thrown=false;
        try{(void)read_surface_2022(path);}catch(const std::runtime_error&){thrown=true;}
        check(thrown,"misordered/misaligned SURF times accepted");
        std::remove(path.c_str());
        std::cout<<"PASS_P6C_SURFACE_FORMATTED_SOFTWARE_ONLY\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<e.what()<<'\n';return 1;
    }
}
