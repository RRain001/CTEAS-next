#include "cteas/p6/read_surface.hpp"
#include <chrono>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(int argc,char** argv) {
    if(argc!=3) {
        std::cerr<<"usage: cteas_p6_read_surface SURF.DAT OUTPUT.csv\n";
        return 2;
    }
    try{
        const auto sf=cteas::calmet::p6::read_surface_2022(argv[1]);
        std::ofstream out(argv[2]);
        if(!out)throw std::runtime_error("SURF output CSV unavailable");
        out<<"station_id,start_epoch_s,end_epoch_s,ws,wd,iceil,icc,tempk,irh,pres,ipcode,"
              "wind_valid,temp_valid,rh_valid,pres_valid,ceiling_valid,cloud_valid,precip_valid\n";
        out<<std::fixed<<std::setprecision(6);
        for(const auto& row:sf.hourly){
            const auto start=row.start.time_since_epoch().count();
            const auto end=row.end.time_since_epoch().count();
            const auto& v=row.obs;
            out<<sf.station_id<<','<<start<<','<<end<<','
               <<v.wind_speed_mps<<','<<v.wind_direction_deg<<','
               <<v.ceiling_hundreds_ft<<','<<v.opaque_cloud_tenths<<','
               <<v.temperature_k<<','<<v.humidity_pct<<','
               <<v.pressure_mb<<','<<v.precip_code<<','
               <<v.wind_valid<<','<<v.temperature_valid<<','<<v.humidity_valid
               <<','<<v.pressure_valid<<','<<v.ceiling_valid<<','<<v.cloud_valid
               <<','<<v.precipitation_code_valid<<'\n';
        }
        if(!out)throw std::runtime_error("SURF CSV write incomplete");
        std::cout<<"P6C_SURFACE_FORMATTED_RECORDS="<<sf.hourly.size()
                 <<" SCIENTIFIC_SOURCEDATA_VALIDATION_NOT_CLAIMED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P6C_SURFACE_ERROR "<<e.what()<<'\n';
        return 1;
    }
}
