// S4-R1c8w genuine NOAA scoped G14 first-hour atomic commit trial.
// Hour2 stages through TEMP3D are source-only/uncommitted. No production
// CALMET.DAT or accepted hour2 original Fortran science comparison.
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
           !result.hour2_prepdi_stage0_staged_preflight_only||
           !result.hour2_live_g26_stage01_uncommitted||
           result.hour2_live_g26_wind1_bitwise_compared_words!=125460||
           !result.hour2_live_g26_stage02_uncommitted||
           result.hour2_live_g26_fradj_compared_words!=146370||
           !result.hour2_live_g26_stage06_uncommitted||
           result.hour2_live_g26_thermal_compared_words!=160310||
           !result.hour2_live_g26_stage11_uncommitted||
           result.hour2_live_g26_g24_compared_words!=320620||
           !result.hour2_live_g26_stage12_uncommitted||
           result.hour2_live_g26_mixht_compared_words!=55760||
           !result.hour2_live_g26_stage13_uncommitted||
           result.hour2_live_g26_avemix_compared_words!=13940||
           !result.hour2_live_g26_stage14_uncommitted||
           result.hour2_live_g26_wstarr_compared_words!=6970||
           !result.hour2_live_g26_stage15_uncommitted||
           result.hour2_live_g26_temp3d_compared_words!=62730||
           !result.hour2_stage16_rejected||
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
            <<"S4R1C8W_G14_HOUR2_REAL_PREPDI_STAGE0=PASS_PRECOMMIT_ONLY\n"
            <<"S4R1C8X_HOUR2_REAL_G26A_STAGE01=PASS_UNCOMMITTED\n"
            <<"S4R1C8X_HOUR2_G26_WIND1_G45_BITWISE=PASS_125460_UV_WORDS\n"
            <<"S4R1C8X_HOUR2_G14_MEMORY_CLOCKS=UNCHANGED_AFTER_WIND1\n"
            <<"S4R1C8Y_HOUR2_REAL_G26A_STAGE02=PASS_UNCOMMITTED\n"
            <<"S4R1C8Y_HOUR2_G26_FRADJ_G21_BITWISE=PASS_146370_REAL4\n"
            <<"S4R1C8Y_HOUR2_G14_MEMORY_CLOCKS=UNCHANGED_AFTER_FRADJ\n"
            <<"S4R1C8Z_HOUR2_REAL_G26A_STAGE03_06=PASS_UNCOMMITTED\n"
            <<"S4R1C8Z_HOUR2_THERMAL_SLOPE_G39_G22_BITWISE=PASS_160310_REAL4\n"
            <<"S4R1C8Z_HOUR2_G14_MEMORY_CLOCKS=UNCHANGED_AFTER_SLOPE\n"
            <<"S4R1C9A_HOUR2_REAL_G26A_STAGE07_11=PASS_UNCOMMITTED\n"
            <<"S4R1C9A_HOUR2_INTER2_G24_SOURCE_BITWISE=PASS_320620_REAL4\n"
            <<"S4R1C9A_HOUR2_G14_MEMORY_CLOCKS=UNCHANGED_AFTER_G24\n"
            <<"S4R1C9B_HOUR2_REAL_G26B_STAGE12=PASS_UNCOMMITTED\n"
            <<"S4R1C9B_HOUR2_MIXHT_CAUSAL_REPLAY_BITWISE=PASS_55760_REAL4\n"
            <<"S4R1C9C_HOUR2_REAL_G26B_STAGE13=PASS_UNCOMMITTED\n"
            <<"S4R1C9C_HOUR2_AVEMIX_SOURCE_BITWISE=PASS_13940_REAL4\n"
            <<"S4R1C9D_HOUR2_REAL_G26B_STAGE14=PASS_UNCOMMITTED\n"
            <<"S4R1C9D_HOUR2_WSTARR_SOURCE_BITWISE=PASS_6970_REAL4\n"
            <<"S4R1C9E_HOUR2_REAL_G26B_STAGE15=PASS_UNCOMMITTED\n"
            <<"S4R1C9E_HOUR2_TEMP3D_SOURCE_BITWISE=PASS_62730_REAL4\n"
            <<"S4R1C9E_HOUR2_STAGE16=REJECTED_UNVERIFIED\n"
            <<"S4R1C9E_HOUR2_G14_MEMORY_CLOCKS=UNCHANGED_AFTER_TEMP3D\n"
            <<"S4R1C8W_G14_HOUR2_REAL_PHYSICS=NOT_ACCEPTED\n"
            <<"S4R1C8W_G14_SIXHOUR_45FIELD_AND_P6_P7=NOT_ACCEPTED\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr<<"S4R1C8W_FAIL_CLOSED "<<error.what()<<'\n';
        return 2;
    }
}
