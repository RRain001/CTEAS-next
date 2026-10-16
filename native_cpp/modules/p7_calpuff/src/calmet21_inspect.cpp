#include "cteas/puff/calmet21.hpp"
#include <exception>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    if (argc<2 || argc>3 || (argc==3 && std::string(argv[2])!="--hefei-2022")) {
        std::cerr<<"Usage: cteas_p7_calmet21_inspect MET.DAT [--hefei-2022]\n";
        return 2;
    }
    try {
        const auto r=cteas::puff::Calmet21Reader::read(argv[1], {}, argc==3);
        std::cout<<"P7B_CALMET21_FIELD_DECODE=PASS\n"
                 <<"NX="<<r.header.nx<<"\n"
                 <<"NY="<<r.header.ny<<"\n"
                 <<"NZ="<<r.header.nz<<"\n"
                 <<"DX_M="<<r.header.dx_m<<"\n"
                 <<"TZ="<<r.header.timezone<<"\n"
                 <<"INTERVALS="<<r.intervals<<"\n"
                 <<"HOURLY_FIELDS="<<r.hourly_fields<<"\n"
                 <<"NONHOURLY_HEADER_RECORDS="<<r.metadata_records<<"\n"
                 <<"FIRST_UNIX_SEC="<<r.first_begin.unix_seconds
                 <<" END_UNIX_SEC="<<r.final_end.unix_seconds<<"\n"
                 <<"P7B_ORIGINAL_FORTRAN_NUMERICAL_PARITY=UNVERIFIED\n";
    } catch (const std::exception& e) {
        std::cerr<<"P7B_CALMET21_FIELD_DECODE=FAIL: "<<e.what()<<"\n";
        return 1;
    }
}
