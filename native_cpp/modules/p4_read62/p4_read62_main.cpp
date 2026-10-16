#include "cteas/met_input/p4_updat.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <stdexcept>

using namespace cteas::met_input::p4;
static Timestamp parse_iso(const std::string& s){
    // Require YYYY-MM-DDTHH:MMZ; explicit UTC for forensic parity.
    if(s.size()!=17||s[4]!='-'||s[7]!='-'||s[10]!='T'||s[13]!=':'||s.substr(15)!="0Z")
       throw ParseError("timestamp must be YYYY-MM-DDTHH:00Z");
    Timestamp t{std::stoi(s.substr(0,4)),std::stoi(s.substr(5,2)),
                std::stoi(s.substr(8,2)),std::stoi(s.substr(11,2))};
    (void)when(t);
    return t;
}
int main(int argc,char** argv) {
    try {
        if(argc!=7)throw std::runtime_error(
            "usage: cteas_p4_read62 FSL_PATH UPDAT_PATH START_UTC END_UTC PSTOP_HPA WMO_ID\n"
            "UTC format YYYY-MM-DDTHH:00Z; validated baseline JDAT=2 IFMT=1, flags F");
        std::ifstream in(argv[1]);
        if(!in)throw std::runtime_error("cannot open FSL");
        UpdatOptions opt;
        opt.begin=parse_iso(argv[3]);
        opt.end=parse_iso(argv[4]);
        opt.pstop_hpa=std::stod(argv[5]);
        opt.station_wmo=std::stoi(argv[6]);
        Options fsl;
        fsl.pstop_hpa=opt.pstop_hpa;
        const auto soundings=read_fsl(in,fsl);
        if(!soundings.empty()) {
            std::cout << "P4_CPP_EFFECTIVE_COORD " << std::fixed << std::setprecision(6)
                << soundings.front().station_lat_deg << " "
                << soundings.front().station_lon_deg << "\n";
        }
        std::ofstream out(argv[2]);
        if(!out)throw std::runtime_error("cannot create UP.DAT");
        const auto stats=write_updat(out,soundings,opt);
        std::cout<<"P4_CPP_UPDAT_OK input="<<stats.input
                 <<" written="<<stats.written
                 <<" levels="<<stats.levels_written
                 <<" warnings="<<stats.warnings<<"\n";
        if(stats.written==0)throw std::runtime_error("no matching soundings in time window");
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P4_CPP_UPDAT_ERROR: "<<e.what()<<"\n";
        return 2;
    }
}
