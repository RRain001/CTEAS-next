// G62 research-only REAL4 physical hidden memory seed (no G14 commit).
#include "cteas/p6/p6g_g62_real_noaa_firsthour_memory_seed.hpp"
#include <bit>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace p6g=cteas::calmet::p6g;
namespace {
void write_real(std::ofstream& output,const std::vector<float>& field){
    if(field.size()!=82U*85U)
        throw std::logic_error("G62 native hidden COMMON plane incorrect");
    output.write(reinterpret_cast<const char*>(field.data()),
                 static_cast<std::streamsize>(field.size()*sizeof(float)));
    if(!output)throw std::runtime_error("G62 native state write truncated");
}
}
int main(int argc,char** argv) {
    try {
        if(argc!=7||
           std::string(argv[1])!="--real-noaa-firsthour-memory-only"||
           sizeof(float)!=4||sizeof(std::int32_t)!=4||
           sizeof(std::int64_t)!=8||
           std::endian::native!=std::endian::little)
            throw std::invalid_argument(
                "G62 requires met.inp GEO.DAT SURF.DAT UP.DAT state.bin");
        if(std::filesystem::exists(argv[6]))
            throw std::invalid_argument(
                "G62 refuses to overwrite prior native hidden memory evidence");
        const p6g::G19SourceFilePaths paths{argv[2],argv[3],argv[4],{argv[5]}};
        const auto state=p6g::g62_real_noaa_firsthour_memory_seed(paths,true);
        if(!state.source_native_hidden_memory_candidate||
           !state.firsthour_g59_45_fields_crosschecked||
           !state.g14_source_preflight_only||
           !state.g14_prepdi_clocks_staged_unpublished||
           !state.g14_wind1_source_native_bitwise_verified||
           !state.g14_fradj_source_native_bitwise_verified||
           !state.g14_source_missfc_original_wind_untouched||
           !state.g14_water_thermal_slope_bitwise_verified||
           !state.g14_real_sparse_stheor_g24_bitwise_verified||
           state.g14_17_stage_transaction_committed||
           state.station_clocks_published||
           state.second_hour_prior_state_consumed||
           state.g26_p7_production)
            throw std::logic_error(
                "G62 silently promoted uncommitted native state to G14/P7");
        std::ofstream f(argv[6],std::ios::binary|std::ios::trunc);
        if(!f)throw std::runtime_error("G62 state candidate file unavailable");
        constexpr char magic[16]={
            'C','T','E','A','S','_','G','6','2','_','S','E','E','D','_','1'};
        constexpr std::int32_t nx=82,ny=85,nz=9,hours=1;
        const std::int64_t end=state.source_end.time_since_epoch().count();
        f.write(magic,sizeof(magic));
        for(const auto value:{nx,ny,nz,hours})
            f.write(reinterpret_cast<const char*>(&value),sizeof(value));
        f.write(reinterpret_cast<const char*>(&end),sizeof(end));
        write_real(f,state.post_comp.zi_m);
        write_real(f,state.post_comp.ziconv_m);
        write_real(f,state.post_comp.dptt_k);
        f.flush();
        if(!f)throw std::runtime_error("G62 state candidate not flushed");
        f.close();
        if(std::filesystem::file_size(argv[6])!=
            sizeof(magic)+4U*sizeof(std::int32_t)+sizeof(std::int64_t)+
            3U*82U*85U*sizeof(float))
            throw std::runtime_error("G62 native candidate wrong physical extent");
        std::cerr
            <<"S4R1C8N_NATIVE_HIDDEN_COMP_MEMORY=PRODUCED_UNVERIFIED "
              "FIRSTHOUR=TRUE CELLS=6970 PLANES=3 "
              "G59_SERIALIZED_ZI_BITWISE_IDENTICAL=TRUE "
              "G14_SOURCE_PREPDI=STAGED_UNPUBLISHED "
              "G14_STAGE1_WIND1=G26_NATIVE_BITWISE_G42 "
              "G14_STAGE2_FRADJ=G26_NATIVE_BITWISE_G41 "
              "G14_G43_NONWIND_MISSFC=P5_RAW_WIND_UNCHANGED "
              "G14_STAGE3_TO_6_WATER_THERMAL_SLOPE=G26_NATIVE_BITWISE_G47 "
              "G14_STAGE7_TO_11_SPARSE_INTER2_G24=G26_NATIVE_BITWISE_G48 "
              "G14_COMMIT_SECONDHOUR_G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& error){
        std::cerr<<"S4R1C8N_FAIL_CLOSED "<<error.what()<<'\n';
        return 2;
    }
}
