// S4-R1c9j genuine NOAA scoped G14 first/second-hour transaction trials.
// Default mode retains the rollback-only second-hour gate; explicit opt-in
// commits hour two and publishes clocks, but never writes production MET.DAT.
// Original Fortran parity is audited by a separate independent comparator.
#include "cteas/p6/p6g_g65_noaa_firsthour_atomic_commit.hpp"
#include <bit>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc,char** argv) {
    try {
        const bool live_third_comp12=(argc==8&&
            std::string(argv[6])=="--third-hour-g26b-comp12-trial-only");
        const bool live_third_windtail=live_third_comp12||(argc==8&&
            std::string(argv[6])=="--third-hour-g26a-windtail-trial-only");
        const bool live_third_g22=live_third_windtail||(argc==8&&
            std::string(argv[6])=="--third-hour-g26a-g22-trial-only");
        const bool third_trace=live_third_g22||(argc==8&&
            std::string(argv[6])=="--third-hour-g22-trace-only");
        if((argc!=6&&argc!=7&&argc!=8&&argc!=10&&argc!=12&&argc!=14)||
           (argc==7&&std::string(argv[6])!="--positive-hour2-g14-transaction"&&
            std::string(argv[6])!="--third-hour-g26a-preflight-only")||
           (argc>=8&&!third_trace&&
            std::string(argv[6])!="--forensic-hour2-precommit")||
           (argc>=10&&std::string(argv[8])!="--forensic-stage14-inputs")||
           (argc>=12&&std::string(argv[10])!="--forensic-stage12-13-mixht")||
           (argc==14&&std::string(argv[12])!="--forensic-hour1-committed")||
           std::string(argv[1])!="--real-noaa-firsthour-g14-atomic"||
           sizeof(float)!=4||sizeof(std::int32_t)!=4||
           std::endian::native!=std::endian::little)
            throw std::invalid_argument(
                "G65 requires: --real-noaa-firsthour-g14-atomic met.inp GEO.DAT SURF.DAT UP.DAT");
        const cteas::calmet::p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const bool positive_hour2=(argc==7||third_trace);
        const bool third_hour_diagno=third_trace||
            (argc==7&&
             std::string(argv[6])=="--third-hour-g26a-preflight-only");
        const auto result=
            cteas::calmet::p6g::g65_real_noaa_firsthour_atomic_commit(
                paths,true,positive_hour2,third_hour_diagno,third_trace,
                live_third_g22,live_third_windtail,live_third_comp12);
        if(result.committed_hours!=(positive_hour2?2U:1U)||
           result.hour2_positive_g14_commit_verified!=positive_hour2||
           result.hour2_positive_station_clocks_published!=positive_hour2||
           result.hour3_preview_inherits_hour2_memory!=positive_hour2||
           result.hour3_real_g26a_stage02_preflight_only!=third_hour_diagno||
           result.hour3_g22_thermal_guard_remains_rejected!=third_hour_diagno||
           result.hour3_test_only_native_g22_trace_ready!=third_trace||
           result.hour3_live_g26a_stage3_trial_only!=live_third_g22||
           result.hour3_native_g23_g24_stage11_trial_only!=live_third_windtail||
           result.hour3_native_g26b_stage12_trial_only!=live_third_comp12||
           (positive_hour2&&
            (result.hour2_committed_memory.zi_m.size()!=6970||
             result.hour2_committed_memory.ziconv_m.size()!=6970||
             result.hour2_committed_memory.dptt_k.size()!=6970))||
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
           !result.hour2_stage16_prepared_unpublished||
           !result.hour2_real_g14_full17_rollback_verified||
           result.hour2_p6f_compared_words!=313650||
           result.hour2_physics_accepted||result.general_p6_accepted)
            throw std::logic_error("G65 scope or committed-hour claim drift");
        // Only opt-in forensic output; never write an accepted hourly
        // CALMET.DAT or overwrite a prior audit input/receipt.
        if(third_trace) {
            const std::filesystem::path trace_path(argv[7]);
            if(trace_path.empty()||std::filesystem::exists(trace_path)||
               result.hour3_test_only_native_g22_trace_bytes.empty()||
               (live_third_g22&&
                result.hour3_live_g26a_stage3_trace_bytes.empty())||
               (live_third_windtail&&
                result.hour3_native_g23_g24_trace_bytes.empty())||
               (live_third_comp12&&
                result.hour3_native_g26b_stage12_trace_bytes.empty()))
                throw std::invalid_argument(
                    "G66 test-only third-hour trace path absent/already exists");
            std::ofstream out(trace_path,std::ios::binary);
            if(!out)throw std::runtime_error("G66 cannot open trace output");
            const auto& bytes=live_third_comp12
                ?result.hour3_native_g26b_stage12_trace_bytes
                :(live_third_windtail
                  ?result.hour3_native_g23_g24_trace_bytes
                  :(live_third_g22
                  ?result.hour3_live_g26a_stage3_trace_bytes
                  :result.hour3_test_only_native_g22_trace_bytes));
            out.write(reinterpret_cast<const char*>(bytes.data()),
                      static_cast<std::streamsize>(bytes.size()));
            out.close();
            if(!out)throw std::runtime_error("G66 incomplete trace write");
        }
        if(argc>=8&&!third_trace) {
            const std::filesystem::path candidate_path(argv[7]);
            if(candidate_path.empty()||
               std::filesystem::exists(candidate_path)||
               result.hour2_unpublished_p6f_bytes.empty())
                throw std::invalid_argument(
                    "G65 forensic hour2 candidate path absent/already exists");
            std::ofstream output(candidate_path,std::ios::binary);
            if(!output)throw std::runtime_error(
                "G65 cannot open exclusive forensic output path");
            const auto& bytes=result.hour2_unpublished_p6f_bytes;
            output.write(reinterpret_cast<const char*>(bytes.data()),
                         static_cast<std::streamsize>(bytes.size()));
            output.close();
            if(!output)throw std::runtime_error(
                "G65 incomplete forensic secondhour candidate write");
        }
        if(argc>=10) {
            const std::filesystem::path stage_path(argv[9]);
            const auto& values=result.hour2_unpublished_wstarr_input_rows;
            if(stage_path.empty()||stage_path==std::filesystem::path(argv[7])||
               std::filesystem::exists(stage_path)||values.size()!=5U*82U*85U)
                throw std::invalid_argument(
                    "G65 stage14 forensic path/shape invalid or already exists");
            std::ofstream out(stage_path,std::ios::binary);
            if(!out)throw std::runtime_error("G65 stage14 forensic open failed");
            // Same [year, Julian-day, UTC-hour, NX, NY] framing as the
            // scratch-only original Fortran stage probe, never production MET.
            const std::int32_t header[5]={2022,152,3,82,85};
            out.write(reinterpret_cast<const char*>(header),sizeof(header));
            out.write(reinterpret_cast<const char*>(values.data()),
                      static_cast<std::streamsize>(values.size()*sizeof(float)));
            out.close();
            if(!out)throw std::runtime_error("G65 stage14 forensic write incomplete");
        }
        if(argc>=12) {
            const std::filesystem::path mixht_path(argv[11]);
            const auto& values=result.hour2_unpublished_mixht_avemix_rows;
            if(mixht_path.empty()||
               mixht_path==std::filesystem::path(argv[7])||
               mixht_path==std::filesystem::path(argv[9])||
               std::filesystem::exists(mixht_path)||
               values.size()!=4U*82U*85U)
                throw std::invalid_argument(
                    "G65 stage12/13 forensic path/shape invalid or already exists");
            std::ofstream out(mixht_path,std::ios::binary);
            if(!out)throw std::runtime_error("G65 stage12/13 forensic open failed");
            const std::int32_t header[5]={2022,152,3,82,85};
            out.write(reinterpret_cast<const char*>(header),sizeof(header));
            out.write(reinterpret_cast<const char*>(values.data()),
                      static_cast<std::streamsize>(values.size()*sizeof(float)));
            out.close();
            if(!out)throw std::runtime_error(
                "G65 stage12/13 forensic write incomplete");
        }
        if(argc==14) {
            const std::filesystem::path state_path(argv[13]);
            const auto& memory=result.committed_memory;
            const auto n=82U*85U;
            if(state_path.empty()||state_path==std::filesystem::path(argv[7])||
               state_path==std::filesystem::path(argv[9])||
               state_path==std::filesystem::path(argv[11])||
               std::filesystem::exists(state_path)||
               memory.zi_m.size()!=n||memory.ziconv_m.size()!=n||
               memory.dptt_k.size()!=n)
                throw std::invalid_argument(
                    "G65 hour1 committed memory trace path/extent invalid");
            std::ofstream out(state_path,std::ios::binary);
            if(!out)throw std::runtime_error("G65 hour1 memory trace open failed");
            const std::int32_t header[5]={2022,152,2,82,85};
            out.write(reinterpret_cast<const char*>(header),sizeof(header));
            for(std::size_t i=0;i<n;++i) {
                const float row[3]={memory.zi_m[i],memory.ziconv_m[i],
                                    memory.dptt_k[i]};
                out.write(reinterpret_cast<const char*>(row),sizeof(row));
            }
            out.close();
            if(!out)throw std::runtime_error("G65 hour1 memory trace incomplete");
        }
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
            <<"S4R1C9F_HOUR2_STAGE16_P6F=PASS_PRECOMMIT_UNPUBLISHED\n"
            <<"S4R1C9F_HOUR2_P6F_45FIELDS_SOURCE_BITWISE=PASS_313650_WORDS\n"
            <<"S4R1C9F_HOUR2_G14_MEMORY_CLOCKS=UNCHANGED_AFTER_P6F_PRECOMMIT\n"
            <<"S4R1C9I_HOUR2_REAL_G14_17STAGE_FAILED_PRECOMMIT=PASS_ROLLBACK_ONLY\n"
            <<(positive_hour2
               ?"S4R1C9J_HOUR2_G14_POSITIVE_COMMIT=PASS_SCOPED_TRANSACTION_ONLY\n"
               :"S4R1C9J_HOUR2_G14_POSITIVE_COMMIT=NOT_RUN\n")
            <<(positive_hour2
               ?"S4R1C9J_HOUR2_AABB_CGAMMA_AFTER_COMMIT=PASS_SCOPED\n"
               :"S4R1C9J_HOUR2_AABB_CGAMMA_AFTER_COMMIT=NOT_RUN\n")
            <<(positive_hour2
               ?"S4R1C9J_HOUR3_PREVIEW_INHERITS_HOUR2=PASS_SCOPED\n"
               :"S4R1C9J_HOUR3_PREVIEW_INHERITS_HOUR2=NOT_RUN\n")
            <<(third_hour_diagno
               ?"S4R1C9K_HOUR3_G26A_STAGE0_2=PASS_PRECOMMIT_ONLY\n"
               :"S4R1C9K_HOUR3_G26A_STAGE0_2=NOT_RUN\n")
            <<(third_hour_diagno
               ?"S4R1C9K_HOUR3_G22_GUARD=PASS_REJECTED\n"
               :"S4R1C9K_HOUR3_G22_GUARD=NOT_RUN\n")
            <<(third_trace
               ?"S4R1C9N_HOUR3_NATIVE_G22_TRACE=PASS_TEST_ONLY_NOT_SCIENCE\n"
               :"S4R1C9N_HOUR3_NATIVE_G22_TRACE=NOT_RUN\n")
            <<(live_third_g22
               ?"S4R1C9O_HOUR3_REAL_G26A_STAGE3_6=PASS_TEST_ONLY_PRECOMMIT\n"
               :"S4R1C9O_HOUR3_REAL_G26A_STAGE3_6=NOT_RUN\n")
            <<"S4R1C8W_G14_HOUR2_REAL_PHYSICS=NOT_ACCEPTED\n"
            <<"S4R1C8W_G14_SIXHOUR_45FIELD_AND_P6_P7=NOT_ACCEPTED\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr<<"S4R1C8W_FAIL_CLOSED "<<error.what()<<'\n';
        return 2;
    }
}
