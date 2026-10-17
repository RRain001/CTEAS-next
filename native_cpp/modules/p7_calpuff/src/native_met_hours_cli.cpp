#include "cteas/puff/original_met_hours.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(int argc,char** argv) {
    try {
        if(argc!=2)throw std::invalid_argument("usage: original_met_hours ORIGINAL_MET_DAT");
        std::size_t count=0;
        const auto m=cteas::puff::OriginalMetHourlyReader::read(
            argv[1],[&](const auto&,const auto& s,const auto& h){
                if(!s.present || s.cell_face_m.empty())
                    throw std::runtime_error("original MET missing ZFACE");
                std::cout<<"P7_MET_HOUR "<<count++<<" "<<h.begin.unix_seconds
                         <<" "<<h.end.unix_seconds<<" "
                         <<std::hex<<std::setw(16)<<std::setfill('0')
                         <<h.original_field_fingerprint()
                         <<std::dec<<std::setfill(' ')<<"\n";
            },true);
        if(count!=143 || m.intervals!=143)throw std::runtime_error("not 143h");
        std::cout<<"P7_NATIVE_MET_HOURLY=PASS HOURS=143 FIELDS=6435 "
                    "COMP_MET_INTERPOLATION=NOT_YET_VALIDATED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"P7_NATIVE_MET_HOURLY=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
