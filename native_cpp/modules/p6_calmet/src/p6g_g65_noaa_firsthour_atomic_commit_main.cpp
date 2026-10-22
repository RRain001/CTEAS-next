// S4-R1c8w genuine NOAA scoped G14 first-hour atomic commit trial.
// No production CALMET.DAT is emitted and no second-hour physics is claimed.
#include "cteas/p6/p6g_g65_noaa_firsthour_atomic_commit.hpp"
#include <bit>
#include <cstdint>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc,char** argv) {
    try {
        if(argc!=6||
           std::string(argv[1])!="--real-noaa-firsthour-g14-atomic"||
           sizeof(float)!=4||sizeof(std::int32_t)!=4||
           std::endian::native!=std::endian::little)
            throw std::invalid_argument(
                "G65 requires: --real-noaa-firsthour-g14-atomic met.inp GEO.DAT SURF.DAT UP.DAT");
        const cteas::calmet::p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto result=
            cteas::calmet::p6g::g65_real_noaa_firsthour_atomic_commit(
                paths,true);
        if(result.committed_hours!=1||
           result.g59_bitwise_compared_words!=313650||
           result.hidden_bitwise_compared_words!=20910||
           !result.rejected_precommit_rolled_back||
           !result.committed_with_published_station_clocks||
           !result.hour2_preview_uses_committed_state||
           !result.hour2_raw_source_admission_verified||
           !result.hour2_firsthour_replay_rejected_atomically||
           result.hour2_physics_accepted||result.general_p6_accepted)
            throw std::logic_error("G65 scope or committed-hour claim drift");
        std::cout
            <<"S4R1C8W_G14_FIRSTHOUR_17STAGE_ATOMIC_COMMIT=PASS_SCOPED\n"
            <<"S4R1C8W_G14_P6F_G59_BITWISE=PASS_313650_WORDS\n"
            <<"S4R1C8W_G14_HIDDEN_MEMORY_BITWISE=PASS_20910_REAL4\n"
            <<"S4R1C8W_G14_FAILED_PRECOMMIT_ROLLBACK=PASS\n"
            <<"S4R1C8W_G14_AABB_CGAMMA_AFTER_COMMIT=PASS\n"
            <<"S4R1C8W_G14_HOUR2_PREVIEW_INHERITS_MEMORY=PASS_SOURCE_ONLY\n"
            <<"S4R1C8W_G14_HOUR2_RAW_MISSFC_WIND_PRESERVED=PASS_SOURCE_ONLY\n"
            <<"S4R1C8W_G14_HOUR2_FIRSTHOUR_REPLAY_REJECTED=PASS_ATOMIC\n"
            <<"S4R1C8W_G14_HOUR2_REAL_PHYSICS=NOT_ACCEPTED\n"
            <<"S4R1C8W_G14_SIXHOUR_45FIELD_AND_P6_P7=NOT_ACCEPTED\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr<<"S4R1C8W_FAIL_CLOSED "<<error.what()<<'\n';
        return 2;
    }
}
