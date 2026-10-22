#pragma once
// S4-R1c8n G62: genuine source-native first-hour hidden COMP state bundle.
// The 45 original-format CALMET.DAT fields CANNOT reconstruct ZICONV/DPTT.
// G54, G59 are independently computed from actual source files; do not
// import reference/original Fortran intermediate states as native inputs.
// This is a physical candidate, NOT a G14 transaction, station-clock commit,
// second-hour forcing admission, general G26, or P7 output.
#include "cteas/p6/p6g_g59_real_noaa_firsthour_dataset.hpp"
#include <bit>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G62RealNoaaFirstHourMemorySeed {
    std::chrono::sys_seconds source_end{};
    p6::NativeGridMemory post_comp;
    bool source_native_hidden_memory_candidate=false;
    bool firsthour_g59_45_fields_crosschecked=false;
    bool g14_17_stage_transaction_committed=false;
    bool station_clocks_published=false;
    bool second_hour_prior_state_consumed=false;
    bool g26_p7_production=false;
};

inline G62RealNoaaFirstHourMemorySeed g62_real_noaa_firsthour_memory_seed(
    const G19SourceFilePaths& paths, bool explicitly_forensic_only) {
    if(!explicitly_forensic_only)
        throw std::invalid_argument("G62 hidden memory cannot enter production");
    // G54's post-LAND MIXHT DPTT and post-AVEMIX ZI/ZICONV are separate
    // *physical* arrays and must remain three distinct native REAL4 planes.
    const auto physical=g54_real_noaa_firsthour_land_mixht(paths,true);
    const auto file=g59_source_noaa_firsthour_dataset(paths,true);
    const auto source=g41_load_selected_noow_water_first_hour_source(paths,true);
    const auto scheduler=source.source.make_scheduler();
    const auto frame=scheduler.preview_next_hour();
    constexpr std::size_t n=82U*85U;
    if(frame.grid.nx!=82||frame.grid.ny!=85||
       frame.stations.surface.size()!=2||frame.stations.upper.size()!=1||
       source.source.surface.hourly.size()!=6||
       frame.hour_index!=0||scheduler.completed_hours()!=0||
       physical.end!=frame.input.end||
       !physical.sparse_first_hour_research_only||
       !physical.native_avemix_candidate_unverified||
       physical.native_avemix_ready||
       physical.g26_45field_ready||physical.causal_six_hour_ready||
       physical.actual_land_count!=6907||physical.actual_water_count!=63||
       !file.firsthour_source_native_45_record_dataset||
       file.g14_six_hour_causal||file.g26_production||file.p7_accepted||
       file.dataset.hourly.size()!=45||file.dataset.header.irlg!=1||
       physical.zi_after_avemix_m.size()!=n||
       physical.ziconv_after_avemix_m.size()!=n||
       physical.dptt_before_avemix_k.size()!=n||
       frame.previous.zi_m.size()!=n||
       frame.previous.ziconv_m.size()!=n||
       frame.previous.dptt_k.size()!=n)
        throw std::invalid_argument(
            "G62 actual firsthour original-source physics/clock incomplete");

    // The signed-zero distinction matters for REAL4 COMMON state. Do not
    // compare rounded strings or copy the CALMET.DAT ZI into COMP memory.
    const cteas::p6f::Calmet21Field* serialized_zi=nullptr;
    for(const auto& field:file.dataset.hourly)
        if(field.label=="ZI      ") {
            if(serialized_zi)
                throw std::logic_error("G62 duplicate P6F ZI source record");
            serialized_zi=&field;
        }
    if(!serialized_zi||serialized_zi->integer||
       serialized_zi->real_values.size()!=n||
       cteas::p6f::instant_seconds(serialized_zi->end)!=
           frame.input.end.time_since_epoch().count())
        throw std::logic_error(
            "G62 firsthour P6F and native COMP hour identity changed");
    for(std::size_t k=0;k<n;++k) {
        const float z=physical.zi_after_avemix_m[k];
        const float zc=physical.ziconv_after_avemix_m[k];
        const float dptt=physical.dptt_before_avemix_k[k];
        if(!std::isfinite(z)||!std::isfinite(zc)||!std::isfinite(dptt)||
           z<0.f||zc<0.f||z==9999.f||zc==9999.f||dptt==9999.f||
           std::bit_cast<std::uint32_t>(z)!=
               std::bit_cast<std::uint32_t>(serialized_zi->real_values[k]))
            throw std::logic_error(
                "G62 hidden COMP source-memory / serialized firsthour ZI drift");
        // The first-hour source contract begins with original COMMON zero;
        // it must not silently inherit an unrelated warm-start state.
        if(frame.previous.zi_m[k]!=0.f||
           frame.previous.ziconv_m[k]!=0.f||
           frame.previous.dptt_k[k]!=0.f)
            throw std::logic_error(
                "G62 source firsthour initial COMMON memory not cold");
    }
    G62RealNoaaFirstHourMemorySeed result;
    result.source_end=physical.end;
    result.post_comp.zi_m=physical.zi_after_avemix_m;
    result.post_comp.ziconv_m=physical.ziconv_after_avemix_m;
    result.post_comp.dptt_k=physical.dptt_before_avemix_k;
    result.source_native_hidden_memory_candidate=true;
    result.firsthour_g59_45_fields_crosschecked=true;
    return result;
}
} // namespace cteas::calmet::p6g
