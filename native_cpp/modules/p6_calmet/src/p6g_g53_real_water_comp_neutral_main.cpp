// S4-R1c8d actual G41+G24 WIND driven G37/G35/G36 native WATER
// reference-only. Original water state never enters this program.
#include "cteas/p6/p6g_g48_real_sparse_stheor.hpp"
#include "cteas/p6/p6g_g53_real_water_comp_neutral.hpp"
#include <cmath>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
namespace p6g=cteas::calmet::p6g;
template<class F>void rejects(F f,const char* msg) {
    bool fail=false;
    try{f();}catch(const std::invalid_argument&){fail=true;}
    if(!fail)throw std::logic_error(msg);
}
int main(int argc,char** argv) {
    try {
        if(argc!=7||std::string(argv[1])!="--actual-noaa-g24-neutral-water-only")
            throw std::invalid_argument("G53 requires source-only met GEO SURF UP output.csv");
        const p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto real=p6g::g41_load_selected_noow_water_first_hour_source(
            paths,true);
        auto scheduler=real.source.make_scheduler();
        const auto frame=scheduler.preview_next_hour();
        const auto g24=p6g::g48_real_sparse_stheor_first_hour(
            paths,true,true,true,true);
        if(!g24.source_p5_raw_wind_unchanged||
           !g24.native_shared_g16_sparse_wind1_equal_to_g42||
           !g24.firsthour_comp_third_candidate_unverified||
           !g24.firsthour_g24_tail_unverified.has_value()||
           g24.native_g23_inter2_or_g26_ready)
            throw std::logic_error("G53 actual source G24 final wind not ready");
        const auto& wind=*g24.firsthour_g24_tail_unverified;
        const auto result=p6g::g53_real_source_g24_neutral_water_reference(
            real,frame,wind,true);
        if(!result.genuine_firsthour_water_arithmetic_only||
           result.land_mixht_ready||
           result.original_causal_memory_ready||
           result.g26_45field_ready||result.water.size()!=63)
            throw std::logic_error("G53 WATER falsely admitted G26 production");
        rejects([&]{
            (void)p6g::g53_real_source_g24_neutral_water_reference(
                real,frame,wind,false);
        },"G53 missing source opt-in did not fail closed");
        auto changed=wind;
        changed.wind.u_mps[result.water.front().source_index]=
            std::numeric_limits<float>::quiet_NaN();
        rejects([&]{
            (void)p6g::g53_real_source_g24_neutral_water_reference(
                real,frame,changed,true);
        },"G53 nonfinite final real G24 U accepted");
        std::ofstream f(argv[6],std::ios::trunc);
        if(!f)throw std::runtime_error("G53 cannot create numeric source report");
        f<<std::setprecision(9)
         <<"i,j,landuse,ws10,fcori,z0,ustar,el,zi,zimech,ziconv,zicold,qh,wstar,wt,pgt\n";
        const auto nx=static_cast<std::size_t>(real.source.grid.nx);
        for(const auto& v:result.water) {
            f<<v.source_index%nx+1<<','<<v.source_index/nx+1<<','
             <<v.original_landuse<<','<<v.ws10_mps<<','<<v.fcori_s_inv<<','
             <<v.neutral.roughness_m<<','<<v.neutral.ustar_mps<<','
             <<v.neutral.el_m<<','<<v.mixing.zi_m<<','
             <<v.mixing.zimech_m<<','<<v.mixing.ziconv_m<<','
             <<v.mixing.persisted_zicold_m<<','
             <<v.neutral.qh_buoyancy_wm2<<','<<v.neutral.wstar_mps<<','
             <<v.neutral.wt_kelvin_mps<<','<<v.neutral.pgt<<'\n';
        }
        f.close();
        if(!f)throw std::runtime_error("G53 WATER numeric report flush failed");
        std::cerr<<"S4R1C8D_REAL_NOAA_G24_TO_WATER=PRODUCED_UNVERIFIED "
                    "WATER=63 ORIGINAL_WIND_INJECTION=FALSE "
                    "P5_RAW_UNCHANGED=TRUE G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C8D_NATIVE_WATER_FAIL_CLOSED "<<e.what()<<"\n";
        return 2;
    }
}
