// Real NOAA first-hour native P6F CALMET.DAT 2.1 45-field preview.
// Source P1-P5 only, test-only; causal six-hour G14/P7 disabled.
#include "cteas/p6/p6g_g59_real_noaa_firsthour_45file.hpp"
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
namespace p6g=cteas::calmet::p6g;
int main(int argc,char** argv){
    try {
        if(argc!=7||std::string(argv[1])!="--authentic-noaa-firsthour-45file-only")
            throw std::invalid_argument(
                "G59 requires original-source met.inp GEO SURF UP and destination");
        const p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto x=p6g::g59_native_noaa_firsthour_45file(paths,true);
        if(!x.test_only_firsthour_legal_file||
           x.full_sixhour_causal_g14_ready||x.p7_ready||
           x.native_hourly_fields!=45||x.native_real!=43||
           x.native_integer!=2)
            throw std::logic_error("G59 false causal G14/P7 admission");
        std::ofstream f(argv[6],std::ios::binary|std::ios::trunc);
        if(!f)throw std::runtime_error("G59 native P6F destination unwritable");
        f.write(reinterpret_cast<const char*>(x.calmet_dat21.data()),
                static_cast<std::streamsize>(x.calmet_dat21.size()));
        f.close();
        if(!f)throw std::runtime_error("G59 native one-hour P6F incomplete");
        std::cerr<<"S4R1C8K_REAL_NOAA_NATIVE_P6F_45FILE="
                    "PRODUCED_UNVERIFIED FIRSTHOUR=1 43_REAL=YES 2_INT=YES "
                    "SOURCE_GEOMETRY=TRUE FORTRAN_HOURLY_INJECTION=FALSE "
                    "G14_SIXHOUR_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"S4R1C8K_NATIVE_P6F_DENIED "<<e.what()<<"\n";
        return 2;
    }
}
