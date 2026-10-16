#include "cteas/puff/transport.hpp"
#include <exception>
#include <iomanip>
#include <iostream>
#include <string>
int main(int argc,char** argv) {
    if(argc!=4 || std::string(argv[3])!="--historical-2023") {
        std::cerr<<"usage: cteas_p7c_met_replay puff.inp met.dat --historical-2023\n";
        return 2;
    }
    try {
        const auto control=cteas::puff::ControlFile::read_file(argv[1]);
        const auto selected=cteas::puff::validate_selected_dry_inputs(control);
        const auto source=cteas::puff::point_source_from_control(control);
        const auto result=cteas::puff::replay_calmet_winds(argv[2],selected,source,true);
        std::cout<<std::setprecision(17)
            <<"P7C_2023_PRESCRIBED_WIND_REPLAY=PASS_SOFTWARE_ONLY\n"
            <<"P7C_NOT_ORIGINAL_PUFF_PARITY=TRUE\n"
            <<"P7C_REAL_MET_HOURS="<<result.wind_hours<<"\n"
            <<"P7C_TRANSPORT_SUBSTEPS="<<result.substeps<<"\n"
            <<"P7C_TOTAL_PACKETS="<<result.mass.total<<"\n"
            <<"P7C_ACTIVE_PACKETS="<<result.mass.active<<"\n";
        for(std::size_t s=0;s<result.mass.released.size();++s) {
            std::cout<<"P7C_SPECIES_"<<s<<"_EMITTED="<<result.mass.released[s]<<"\n"
                     <<"P7C_SPECIES_"<<s<<"_INVENTORY="<<result.mass.inventory[s]<<"\n"
                     <<"P7C_SPECIES_"<<s<<"_OUTFLOW="<<result.mass.outflow[s]<<"\n";
        }
    } catch(const std::exception& e) {
        std::cerr<<"P7C_2023_PRESCRIBED_WIND_REPLAY=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
