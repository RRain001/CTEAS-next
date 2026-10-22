// S4-R1c8j original-free true NOAA two P6F INTEGER4 fields.
// Output 2 fixed 8-byte labels, each exactly 6970 little-endian INT4s.
#include "cteas/p6/p6g_g58_real_p6f_ipgt_irh.hpp"
#include <bit>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
namespace p6g=cteas::calmet::p6g;
int main(int argc,char** argv) {
    try {
        if(argc!=7||std::string(argv[1])!="--real-noaa-p6f-ipgt-irh-firsthour-only"||
           sizeof(std::int32_t)!=4||std::endian::native!=std::endian::little)
            throw std::invalid_argument("G58 requires source MET GEO SURF UP output.bin");
        const p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto r=p6g::g58_noaa_real_ipgt_irh(paths,true);
        if(!r.actual_source_firsthour_only||
           r.integer_values_original_verified||r.full45_p6f_accepted||
           r.causal_sixhour_accepted||
           r.ipgt.size()!=82U*85U||r.irh.size()!=82U*85U||
           r.source_water!=63||r.source_land!=6907)
            throw std::logic_error("G58 falsely asserted P6F admission");
        std::ofstream f(argv[6],std::ios::binary|std::ios::trunc);
        if(!f)throw std::runtime_error("G58 candidate output unwritable");
        const auto write=[&](const char* label,
                              const std::vector<std::int32_t>& data){
            f.write(label,8);
            f.write(reinterpret_cast<const char*>(data.data()),
                    static_cast<std::streamsize>(
                        data.size()*sizeof(std::int32_t)));
        };
        write("IPGT    ",r.ipgt);
        write("IRH     ",r.irh);
        f.close();
        if(!f)throw std::runtime_error("G58 output truncated");
        std::cerr<<"S4R1C8J_NATIVE_NOAA_INTEGER2=PRODUCED_UNVERIFIED "
                    "LAND=6907 WATER=63 INPUT_ORIGINAL_OUTPUT=FALSE "
                    "FULL45_G26_SIXHOUR_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"S4R1C8J_NATIVE_INTEGER2_DENIED "<<e.what()<<"\n";
        return 2;
    }
}
