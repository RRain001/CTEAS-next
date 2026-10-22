// S4-R1c7f: genuine NOAA first-hour mixed-water selected G16 INTER2
// diagnostic output only. No original MET, U/V oracle, or Fortran trace
// enters the native execution. Its numerical acceptance is external.
#include "cteas/p6/p6g_g48_real_sparse_stheor.hpp"
#include <bit>
#include <cstddef>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace p6g=cteas::calmet::p6g;

static void emit(std::ofstream& out,const std::vector<float>& x) {
    out.write(reinterpret_cast<const char*>(x.data()),
              static_cast<std::streamsize>(x.size()*sizeof(float)));
    if(!out)throw std::runtime_error("G49 native INTER2 binary output truncated");
}
int main(int argc,char** argv) {
    try {
        if(argc!=7||std::string(argv[1])!="--genuine-source-inter2-diagnostic"||
           sizeof(float)!=4||std::endian::native!=std::endian::little)
            throw std::invalid_argument(
                "G49 must opt in with met.inp GEO SURF UP outfile on little endian REAL4");
        p6g::G19SourceFilePaths paths{argv[2],argv[3],argv[4],{argv[5]}};
        const auto calculated=p6g::g48_real_sparse_stheor_first_hour(
            paths,true,true);
        constexpr std::size_t layer_values=82U*85U*9U;
        if(!calculated.firsthour_inter2_candidate_unverified||
           !calculated.native_shared_g16_sparse_wind1_equal_to_g42||
           !calculated.source_p5_raw_wind_unchanged||
           calculated.native_g23_inter2_or_g26_ready||
           calculated.firsthour_inter2_u_unverified.size()!=layer_values||
           calculated.firsthour_inter2_v_unverified.size()!=layer_values||
           calculated.native_valid_station.size()!=1||
           calculated.missing_wind_skipped!=1)
            throw std::logic_error(
                "G49 genuine NOAA native G16 post-INTER2 source scope invalid");
        std::ofstream output(argv[6],std::ios::binary|std::ios::trunc);
        if(!output)
            throw std::runtime_error("G49 cannot create diagnostic output");
        emit(output,calculated.firsthour_inter2_u_unverified);
        emit(output,calculated.firsthour_inter2_v_unverified);
        output.close();
        if(!output)throw std::runtime_error("G49 native binary flush failed");
        std::cerr<<"S4R1C7F_GENUINE_82X85X9_NATIVE_G16_INTER2=PRODUCED_UNVERIFIED "
                    "SOURCE_WIND_MASK=UNCHANGED NO_ORIGINAL_WIND_INJECTION=TRUE "
                    "G24_G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C7F_REAL_INTER2_FAIL_CLOSED "<<e.what()<<'\n';
        return 2;
    }
}
