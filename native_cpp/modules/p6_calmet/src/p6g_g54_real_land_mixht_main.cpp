// G54 real NOAA firsthour only: original source→native full-grid MIXHT.
// The executable DOES NOT accept any original intermediate oracle fields.
#include "cteas/p6/p6g_g54_real_land_mixht.hpp"
#include <bit>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace p6g=cteas::calmet::p6g;
static void write(std::ofstream& out,const std::vector<float>& v){
    out.write(reinterpret_cast<const char*>(v.data()),
              static_cast<std::streamsize>(v.size()*sizeof(float)));
    if(!out)throw std::runtime_error("G54 native MIXHT float stream truncated");
}
int main(int argc,char** argv){
    try{
        if(argc!=7||std::string(argv[1])!="--real-noaa-firsthour-land-mixht-only"||
           sizeof(float)!=4||std::endian::native!=std::endian::little)
            throw std::invalid_argument("G54 requires met GEO SURF UP output diagnostic");
        const p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto native=p6g::g54_real_noaa_firsthour_land_mixht(paths,true);
        if(!native.sparse_first_hour_research_only||
           native.native_avemix_ready||native.g26_45field_ready||
           native.causal_six_hour_ready||
           native.actual_water_count!=63||
           native.actual_land_count!=6907||
           native.source_valid_diagi_count!=1||
           native.source_missing_diagi_count!=1||
           native.zi_before_avemix_m.size()!=82U*85U||
           native.ziconv_before_avemix_m.size()!=82U*85U||
           native.dptt_before_avemix_k.size()!=82U*85U)
            throw std::logic_error("G54 fake full COMP stage admission");
        std::ofstream f(argv[6],std::ios::binary|std::ios::trunc);
        if(!f)throw std::runtime_error("G54 native output not writable");
        write(f,native.zi_before_avemix_m);
        write(f,native.ziconv_before_avemix_m);
        write(f,native.dptt_before_avemix_k);
        f.close();
        if(!f)throw std::runtime_error("G54 native diagnostic flush failed");
        std::cerr<<"S4R1C8F_NATIVE_REAL_LAND_MIXHT=PRODUCED_UNVERIFIED "
                    "LAND=6907 WATER=63 VALID_SS=1 MISSING_SS=1 "
                    "ORIGINAL_INTERMEDIATE_INJECTION=FALSE "
                    "AVEMIX_G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"S4R1C8F_NATIVE_LAND_MIXHT_DENIED "<<e.what()<<"\n";
        return 2;
    }
}
