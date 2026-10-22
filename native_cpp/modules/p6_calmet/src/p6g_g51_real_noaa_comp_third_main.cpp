// S4-R1c8b: genuine NOAA original COMP third SURFVAR via SAME G17B4/G48
// chain using already source-validated G24 final U/V. Forensics only.
#include "cteas/p6/p6g_g48_real_sparse_stheor.hpp"
#include <bit>
#include <cstddef>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
namespace p6g=cteas::calmet::p6g;
int main(int argc,char** argv) {
    try {
        if(argc!=7||std::string(argv[1])!="--real-noaa-comp-third-source-only"||
           sizeof(float)!=4||std::endian::native!=std::endian::little)
            throw std::invalid_argument(
                "G51 source-only CLI requires met.inp GEO SURF UP output.f32");
        const p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto native=p6g::g48_real_sparse_stheor_first_hour(
            paths,true,true,true,true);
        if(!native.source_p5_raw_wind_unchanged||
           !native.native_shared_g16_sparse_wind1_equal_to_g42||
           !native.firsthour_g24_tail_unverified||
           !native.firsthour_comp_third_candidate_unverified||
           native.native_g23_inter2_or_g26_ready||
           native.firsthour_comp_third_temperature_unverified.size()!=82U*85U||
           native.native_valid_station.size()!=1||
           native.missing_wind_skipped!=1)
            throw std::logic_error(
                "G51 actual-water G24 -> G17B4 COMP source handoff incomplete");
        const auto& field=native.firsthour_comp_third_temperature_unverified;
        std::ofstream out(argv[6],std::ios::binary|std::ios::trunc);
        if(!out)
            throw std::runtime_error("G51 destination unavailable");
        out.write(reinterpret_cast<const char*>(field.data()),
                  static_cast<std::streamsize>(field.size()*sizeof(float)));
        out.close();
        if(!out)throw std::runtime_error("G51 third SURFVAR output truncated");
        std::cerr<<"S4R1C8B_NATIVE_REAL_COMP_THIRD=PRODUCED_UNVERIFIED "
                    "NO_FORTRAN_ORACLE_INPUT=TRUE P5_RAW_UNCHANGED=TRUE "
                    "FULL_G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C8B_COMP_THIRD_FAIL_CLOSED "<<e.what()<<"\n";
        return 2;
    }
}
