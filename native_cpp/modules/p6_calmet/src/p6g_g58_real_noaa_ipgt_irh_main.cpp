// S4-R1c8j original-free firsthour IPGT/IRH numerical diagnostic.
// This is NOT a legal 45-field P6F artifact or production G14 actor.
#include "cteas/p6/p6g_g58_real_noaa_ipgt_irh.hpp"
#include <bit>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
namespace p6g=cteas::calmet::p6g;
int main(int argc,char** argv) {
    try{
        if(argc!=7||std::string(argv[1])!="--real-noaa-firsthour-ipgt-irh-only"||
           sizeof(std::int32_t)!=4||std::endian::native!=std::endian::little)
            throw std::invalid_argument("G58 source met GEO SURF UP output.bin required");
        const p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto candidate=p6g::g58_source_noaa_p6f_ipgt_irh(paths,true);
        if(!candidate.source_only_two_integer_fields||
           candidate.p6f_45field_file_ready||
           candidate.g14_six_hour_causal_ready||
           candidate.original_water!=63||
           candidate.original_land!=6907||
           candidate.ipgt.size()!=82U*85U||
           candidate.irh.size()!=82U*85U)
            throw std::logic_error("G58 falsely admitted full CALMET production");
        std::ofstream out(argv[6],std::ios::binary|std::ios::trunc);
        if(!out)throw std::runtime_error("G58 integer diagnostic unwritable");
        out.write(reinterpret_cast<const char*>(candidate.ipgt.data()),
                  static_cast<std::streamsize>(4*candidate.ipgt.size()));
        out.write(reinterpret_cast<const char*>(candidate.irh.data()),
                  static_cast<std::streamsize>(4*candidate.irh.size()));
        out.close();
        if(!out)throw std::runtime_error("G58 integer diagnostic flush failed");
        std::cerr<<"S4R1C8J_REAL_NOAA_NATIVE_INTEGER_FIELDS=PRODUCED_UNVERIFIED "
                    "IPGT_IRH=2 WATER=63 SS=2 US=1 "
                    "ORIGINAL_INTERMEDIATE_INPUT=FALSE FULL45_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"S4R1C8J_NATIVE_INTEGER_DENIED "<<e.what()<<"\n";
        return 2;
    }
}
