// Original-independent native first-hour NOAA WSTARR, after genuine AVEMIX.
#include "cteas/p6/p6g_g55_real_comp_wstarr.hpp"
#include <bit>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
namespace p6g=cteas::calmet::p6g;
int main(int argc,char** argv) {
    try {
        if(argc!=7||std::string(argv[1])!="--authentic-noaa-comp-wstarr-only"||
           sizeof(float)!=4||std::endian::native!=std::endian::little)
            throw std::invalid_argument(
                "G55 source-only CLI requires met.inp GEO SURF UP output.bin");
        const p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto r=p6g::g55_native_real_comp_wstarr(paths,true);
        if(!r.firsthour_source_only||r.native_temp3d_ready||
           r.g26_45field_ready||r.six_hour_causal_ready||
           r.wstar_mps.size()!=82U*85U)
            throw std::logic_error("G55 claimed unsupported G26 production");
        std::ofstream f(argv[6],std::ios::binary|std::ios::trunc);
        if(!f)throw std::runtime_error("G55 scientific output not writable");
        f.write(reinterpret_cast<const char*>(r.wstar_mps.data()),
                static_cast<std::streamsize>(
                    r.wstar_mps.size()*sizeof(float)));
        f.close();
        if(!f)throw std::runtime_error("G55 output write incomplete");
        std::cerr<<"S4R1C8G_NATIVE_NOAA_COMP_WSTARR=PRODUCED_UNVERIFIED "
                    "WATER=63 LAND=6907 NO_ORIGINAL_INTERMEDIATE_INPUT=TRUE "
                    "TEMP3D_G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"S4R1C8G_NATIVE_WSTARR_DENIED "<<e.what()<<"\n";
        return 2;
    }
}
