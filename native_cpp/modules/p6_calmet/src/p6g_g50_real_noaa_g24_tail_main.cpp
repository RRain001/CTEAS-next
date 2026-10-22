// S4-R1c8a genuine source 2SS1US first-hour G24 diagnostics only.
// Original CALMET reference never enters this executable. G24 is the
// same frozen shared source kernel used by existing G19/G23 route.
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
static void emit(std::ofstream& f,const std::vector<float>& v) {
    f.write(reinterpret_cast<const char*>(v.data()),
            static_cast<std::streamsize>(sizeof(float)*v.size()));
    if(!f)throw std::runtime_error("G50 native G24 payload truncated");
}
int main(int argc,char** argv) {
    try {
        if(argc!=7||std::string(argv[1])!="--real-noaa-firsthour-g24-only"||
           sizeof(float)!=4||std::endian::native!=std::endian::little)
            throw std::invalid_argument(
                "G50 strict source-only met GEO SURF UP binary-output CLI");
        const p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto res=p6g::g48_real_sparse_stheor_first_hour(
            paths,true,true,true);
        constexpr std::size_t cells=82U*85U,layer=9U*cells;
        if(!res.source_p5_raw_wind_unchanged||
           !res.native_shared_g16_sparse_wind1_equal_to_g42||
           !res.firsthour_inter2_candidate_unverified||
           !res.firsthour_g24_tail_unverified.has_value()||
           res.native_g23_inter2_or_g26_ready)
            throw std::logic_error("G50 real source G24 admission failed");
        const auto& g=res.firsthour_g24_tail_unverified->wind;
        if(g.u_mps.size()!=layer||g.v_mps.size()!=layer||
           g.divergence_per_s.size()!=layer||
           g.w_face_mps.size()!=10U*cells||
           g.ub_west_east_mps.size()!=18U*85U||
           g.vb_south_north_mps.size()!=18U*82U)
            throw std::logic_error("G50 original selected tail extent mismatched");
        std::ofstream f(argv[6],std::ios::binary|std::ios::trunc);
        if(!f)throw std::runtime_error("G50 could not create source diagnostic");
        emit(f,g.u_mps);
        emit(f,g.v_mps);
        emit(f,g.w_face_mps);
        emit(f,g.divergence_per_s);
        emit(f,g.ub_west_east_mps);
        emit(f,g.vb_south_north_mps);
        f.close();
        if(!f)throw std::runtime_error("G50 source diagnostic flush failed");
        std::cerr<<"S4R1C8A_REAL_NOAA_NATIVE_G24=PRODUCED_UNVERIFIED "
                    "FIRSTHOUR=TRUE SOURCE_MASK=UNCHANGED "
                    "ORIGINAL_WIND_INJECTION=FALSE G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C8A_G24_DENIED "<<e.what()<<'\n';
        return 2;
    }
}
