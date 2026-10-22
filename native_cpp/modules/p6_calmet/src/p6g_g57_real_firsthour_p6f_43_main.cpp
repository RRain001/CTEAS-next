// S4-R1c8i: original-independent native 43 REAL4 first-hour P6F
// data-only candidate. Strict label and field order, no header/static
// records, no integer IPGT/IRH, no six-hour G14 commit.
#include "cteas/p6/p6g_g57_real_firsthour_p6f_43.hpp"
#include <bit>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
namespace p6g=cteas::calmet::p6g;
int main(int argc,char** argv) {
    try {
        if(argc!=7||std::string(argv[1])!="--real-noaa-p6f-43real-firsthour-only"||
           sizeof(float)!=4||std::endian::native!=std::endian::little)
            throw std::invalid_argument("G57 source met GEO SURF UP output.bin required");
        const p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto data=p6g::g57_noaa_real_43_output_fields(paths,true);
        if(!data.source_firsthour_43real_only||
           data.original_ipgt_irh_verified||data.g26_45field_ready||
           data.six_hour_causal_ready||
           data.source_land!=6907||data.source_water!=63||
           data.fields.size()!=43)
            throw std::logic_error("G57 source fields falsely marked production");
        std::ofstream out(argv[6],std::ios::binary|std::ios::trunc);
        if(!out)throw std::runtime_error("G57 source 43 real file unwritable");
        for(const auto& record:data.fields) {
            out.write(record.first.data(),8);
            out.write(reinterpret_cast<const char*>(record.second.data()),
                static_cast<std::streamsize>(record.second.size()*sizeof(float)));
        }
        out.close();
        if(!out)throw std::runtime_error("G57 source real output incomplete");
        std::cerr<<"S4R1C8I_REAL_NOAA_NATIVE_P6F_REAL_FIELDS=PRODUCED_UNVERIFIED "
                    "REAL_FIELDS=43 INTEGER_IPGT_IRH=NOT_ACCEPTED "
                    "NO_ORIGINAL_MET_FIELD_INPUT=TRUE G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"S4R1C8I_NATIVE_REAL_P6F_FAIL_CLOSED "<<e.what()<<"\n";
        return 2;
    }
}
