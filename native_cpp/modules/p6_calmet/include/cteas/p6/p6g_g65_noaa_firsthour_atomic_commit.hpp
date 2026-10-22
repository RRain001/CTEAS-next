#pragma once
// S4-R1c8w: one authentic NOAA first-hour G14 atomic transaction.
// Research-only, selected WATER route. NOT hour-2 physics or P6 production.
// All 17 physics stages run on the SAME scheduler-owned frame; no G54/G59
// numbers are used as native forcing. Failed precommit cannot publish state.
#include "cteas/p6/p6g_g62_real_noaa_firsthour_memory_seed.hpp"
#include "cteas/p6/p6g_g45_six_hour_water_wind1.hpp"
#include <bit>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {

class G65RealNoaaFirstHourActor final : public MultiHourPhysics {
public:
    G65RealNoaaFirstHourActor(
        const UnifiedMultistationHourlyScheduler& scheduler,
        G18D2StationClockAuthority& clocks,
        const G19FileBackedCase& source,
        const G41SelectedNoowWaterFirstHourSource& original)
        :diagno_(scheduler,clocks,source,true),
         comp_(diagno_,source,true,&original) {}

    [[nodiscard]] p6::NativeHourStageResult run(
        p6::NativeHourStage stage,MultiHourFrame& frame) override {
        if(frame.hour_index!=0)
            throw std::logic_error(
                "G65 first-hour source actor refuses cross-hour replay");
        if(cursor_>=p6::kHefeiOriginalStageOrder.size()||
           stage!=p6::kHefeiOriginalStageOrder[cursor_])
            throw std::logic_error("G65 17-stage G14 order/phase drift");
        const auto result=(cursor_<12)
            ?diagno_.run(stage,frame):comp_.run(stage,frame);
        if(!result.completed||result.source!=p6::NativeHourSource::NativeCpp)
            throw std::logic_error("G65 missing native CALMET stage");
        ++cursor_;
        return result;
    }

    [[nodiscard]] const cteas::p6f::Calmet21File& precommit(
        const MultiHourFrame& frame) const {
        if(cursor_!=17||frame.hour_index!=0)
            throw std::logic_error("G65 precommit before full first hour");
        const auto& candidate=comp_.source_water_p6f_stage16(frame);
        if(!candidate.actual_g14_stage16_precommit_validated||
           candidate.serialized_prepared_only.empty()||
           candidate.candidate_dataset.hourly.size()!=45)
            throw std::logic_error("G65 P6F native precommit not verified");
        diagno_.require_station_clock_preflight(frame);
        return candidate.candidate_dataset;
    }

    [[nodiscard]] bool publish_after_commit_noexcept() noexcept {
        return cursor_==17&&
               diagno_.try_publish_after_selected_g14_commit_noexcept();
    }
private:
    G26SourceFileBackedG14DiagnoBridge diagno_;
    G26BSourceFileBackedCompBridge comp_;
    std::size_t cursor_=0;
};

struct G65NoaaFirstHourCommitReceipt {
    std::chrono::sys_seconds end{};
    p6::NativeGridMemory committed_memory;
    std::size_t committed_hours=0;
    std::size_t g59_bitwise_compared_words=0;
    std::size_t hidden_bitwise_compared_words=0;
    bool rejected_precommit_rolled_back=false;
    bool committed_with_published_station_clocks=false;
    bool hour2_preview_uses_committed_state=false;
    bool hour2_raw_source_admission_verified=false;
    bool hour2_firsthour_replay_rejected_atomically=false;
    bool hour2_prepdi_stage0_staged_preflight_only=false;
    std::size_t hour2_live_g26_wind1_bitwise_compared_words=0;
    bool hour2_live_g26_stage01_uncommitted=false;
    bool hour2_physics_accepted=false;
    bool general_p6_accepted=false;
};

inline bool g65_equal_real4_bits(
    const std::vector<float>& a,const std::vector<float>& b) {
    if(a.size()!=b.size())return false;
    for(std::size_t i=0;i<a.size();++i)
        if(std::bit_cast<std::uint32_t>(a[i])!=
           std::bit_cast<std::uint32_t>(b[i]))return false;
    return true;
}

inline G65NoaaFirstHourCommitReceipt
g65_real_noaa_firsthour_atomic_commit(
    const G19SourceFilePaths& paths,bool explicitly_forensic_only) {
    if(!explicitly_forensic_only)
        throw std::invalid_argument("G65 cannot enter P6 production");

    const auto actual=g41_load_selected_noow_water_first_hour_source(paths,true);
    const auto repaired=g43_original_comp_missfc_source_only(
        actual,actual.source.surface.hourly.front(),true);
    if(!repaired.source_comp_missfc_complete||
       repaired.original_raw.by_station.size()!=2||
       repaired.original_comp_resolved.by_station.size()!=2)
        throw std::logic_error("G65 authentic NOAA G43 source absent");
    for(std::size_t i=0;i<2;++i) {
        const auto& raw=repaired.original_raw.by_station[i];
        const auto& next=repaired.original_comp_resolved.by_station[i];
        if(raw.wind_valid!=next.wind_valid||
           raw.wind_speed_mps!=next.wind_speed_mps||
           raw.wind_direction_deg!=next.wind_direction_deg||
           raw.precip_code!=next.precip_code||
           raw.precipitation_code_valid!=next.precipitation_code_valid)
            throw std::logic_error("G65 forbids P5 raw missing-wind imputation");
    }

    auto source=g19_load_original_source_case(paths,true);
    source.surface.hourly.front()=repaired.original_comp_resolved;
    if(!source.research_noow_water_source_only||
       source.surface.hourly.size()!=6||
       source.grid.nx!=82||source.grid.ny!=85||
       source.stations.surface.size()!=2||source.stations.upper.size()!=1||
       source.source_water_cells.size()!=63)
        throw std::invalid_argument("G65 requires frozen actual NOAA 2SS/1US six-hour case");
    // These two independent paths are exclusively post-physics comparators.
    const auto independent=g59_source_noaa_firsthour_dataset(paths,true);
    const auto hidden=g54_real_noaa_firsthour_land_mixht(paths,true);
    auto scheduler=source.make_scheduler();
    G18D2StationClockAuthority clocks;
    const auto first=scheduler.preview_next_hour();
    if(first.hour_index!=0||scheduler.completed_hours()!=0||
       clocks.has_published_hour())
        throw std::logic_error("G65 source G14 not at a cold first hour");
    const auto first_end=first.input.end;

    auto attempt=[&](bool inject_precommit_failure) {
        G65RealNoaaFirstHourActor* live=nullptr;
        bool published=false;
        bool injection_reached=false;
        std::size_t compared=0;
        try {
            scheduler.advance_with_fresh_physics(
                [&](const MultiHourFrame& next)
                    ->std::unique_ptr<MultiHourPhysics> {
                    if(next.hour_index!=0||next.input.end!=first_end)
                        throw std::logic_error("G65 factory not on NOAA first-hour clock");
                    auto actor=std::make_unique<G65RealNoaaFirstHourActor>(
                        scheduler,clocks,source,actual);
                    live=actor.get();
                    return actor;
                },
                [&](const MultiHourFrame& frame) {
                    if(!live||frame.hour_index!=0||
                       frame.input.end!=first_end)
                        throw std::logic_error("G65 detached G14 precommit gate");
                    const auto& candidate=live->precommit(frame);
                    if(candidate.hourly.size()!=45||
                       independent.dataset.hourly.size()!=45)
                        throw std::logic_error("G65 incorrect original P6F cardinality");
                    const auto n=static_cast<std::size_t>(82)*85;
                    for(std::size_t k=0;k<45;++k) {
                        const auto& a=candidate.hourly.at(k);
                        const auto& b=independent.dataset.hourly.at(k);
                        if(a.label!=b.label||a.integer!=b.integer||
                           cteas::p6f::instant_seconds(a.begin)!=
                               cteas::p6f::instant_seconds(b.begin)||
                           cteas::p6f::instant_seconds(a.end)!=
                               cteas::p6f::instant_seconds(b.end))
                            throw std::logic_error("G65 original P6F label/UTC drift");
                        if(a.integer) {
                            if(a.integer_values.size()!=n||
                               a.integer_values!=b.integer_values)
                                throw std::logic_error("G65 G59 INTEGER4 parity failed");
                        } else if(a.real_values.size()!=n||
                                  !g65_equal_real4_bits(a.real_values,b.real_values))
                            throw std::logic_error("G65 G59 REAL4 bit parity failed");
                        compared+=n;
                    }
                    if(compared!=313650)
                        throw std::logic_error("G65 full 45-field comparison incomplete");
                    if(!g65_equal_real4_bits(frame.next.zi_m,
                                             hidden.zi_after_avemix_m)||
                       !g65_equal_real4_bits(frame.next.ziconv_m,
                                             hidden.ziconv_after_avemix_m)||
                       !g65_equal_real4_bits(frame.next.dptt_k,
                                             hidden.dptt_before_avemix_k))
                        throw std::logic_error("G65 hidden COMP memory parity failed");
                    // Throw only after all 17 live stages and independent
                    // comparisons, so this actually proves G14 rollback.
                    if(inject_precommit_failure) {
                        injection_reached=true;
                        throw std::runtime_error("G65_EXPECTED_PRECOMMIT_INJECTION");
                    }
                },
                [&](MultiHourPhysics& physics,
                    const UnifiedMultistationHourlyScheduler& owner) noexcept {
                    auto* actor=dynamic_cast<G65RealNoaaFirstHourActor*>(&physics);
                    published=(actor!=nullptr&&
                               actor->publish_after_commit_noexcept()&&
                               clocks.has_published_hour()&&
                               owner.completed_hours()==1);
                });
            if(inject_precommit_failure)
                throw std::logic_error("G65 forged precommit unexpectedly committed");
        } catch(const std::runtime_error& e) {
            if(!inject_precommit_failure||!injection_reached||
               std::string(e.what())!="G65_EXPECTED_PRECOMMIT_INJECTION")
                throw;
            if(scheduler.completed_hours()!=0||clocks.has_published_hour()||
               !g65_equal_real4_bits(scheduler.committed_memory().zi_m,
                                     first.previous.zi_m)||
               !g65_equal_real4_bits(scheduler.committed_memory().ziconv_m,
                                     first.previous.ziconv_m)||
               !g65_equal_real4_bits(scheduler.committed_memory().dptt_k,
                                     first.previous.dptt_k))
                throw std::logic_error("G65 failed G14 physical/station rollback");
            return std::pair<bool,std::size_t>{false,compared};
        }
        if(!published||scheduler.completed_hours()!=1||
           !clocks.has_published_hour()||
           clocks.latest_upper_hour()!=first_end||
           clocks.latest_gamma_hour()!=first_end)
            throw std::logic_error("G65 firsthour G14/clock commit not synchronized");
        return std::pair<bool,std::size_t>{true,compared};
    };

    const auto rejected=attempt(true);
    if(rejected.first||rejected.second!=313650)
        throw std::logic_error("G65 negative exact-head precommit gate failed");
    const auto accepted=attempt(false);
    if(!accepted.first||accepted.second!=313650)
        throw std::logic_error("G65 successful exact-head P6F gate failed");
    const auto& committed=scheduler.committed_memory();
    if(!g65_equal_real4_bits(committed.zi_m,hidden.zi_after_avemix_m)||
       !g65_equal_real4_bits(committed.ziconv_m,hidden.ziconv_after_avemix_m)||
       !g65_equal_real4_bits(committed.dptt_k,hidden.dptt_before_avemix_k))
        throw std::logic_error("G65 committed REAL4 hidden COMMON parity failed");
    const auto hour2=scheduler.preview_next_hour();
    if(hour2.hour_index!=1||hour2.surface.start!=first_end||
       &hour2.previous!=&scheduler.committed_memory()||
       !g65_equal_real4_bits(hour2.previous.zi_m,committed.zi_m)||
       !g65_equal_real4_bits(hour2.previous.ziconv_m,committed.ziconv_m)||
       !g65_equal_real4_bits(hour2.previous.dptt_k,committed.dptt_k))
        throw std::logic_error("G65 hour2 preview does not inherit G14 committed memory");

    // Real second-hour source admission is separate from the UNSUPPORTED
    // second-hour physics. G43 may repair only COMP's five non-wind
    // meteorological fields, preserving the raw archive and all wind/precip.
    const auto& hour2_raw=actual.source.surface.hourly.at(1);
    if(hour2_raw.start!=first_end||
       hour2_raw.end!=hour2.input.end||
       hour2.input.end-first_end!=std::chrono::hours{1}||
       hour2.surface.start!=hour2_raw.start||
       hour2.surface.end!=hour2_raw.end||
       hour2.surface.by_station.size()!=hour2_raw.by_station.size())
        throw std::logic_error(
            "G65 next-hour preview does not use actual NOAA hour-two source");
    const auto repaired_hour2=g43_original_comp_missfc_source_only(
        actual,hour2_raw,true);
    if(!repaired_hour2.source_comp_missfc_complete||
       repaired_hour2.original_raw.end!=hour2.input.end||
       repaired_hour2.original_comp_resolved.end!=hour2.input.end)
        throw std::logic_error("G65 genuine NOAA hour-two MISSFC unavailable");
    for(std::size_t i=0;i<hour2_raw.by_station.size();++i) {
        const auto& a=hour2_raw.by_station[i];
        const auto& live=hour2.surface.by_station[i];
        const auto& repaired_obs=
            repaired_hour2.original_comp_resolved.by_station[i];
        if(live.wind_valid!=a.wind_valid||
           live.wind_speed_mps!=a.wind_speed_mps||
           live.wind_direction_deg!=a.wind_direction_deg||
           live.precipitation_code_valid!=a.precipitation_code_valid||
           live.precip_code!=a.precip_code||
           repaired_obs.wind_valid!=a.wind_valid||
           repaired_obs.wind_speed_mps!=a.wind_speed_mps||
           repaired_obs.wind_direction_deg!=a.wind_direction_deg||
           repaired_obs.precipitation_code_valid!=a.precipitation_code_valid||
           repaired_obs.precip_code!=a.precip_code)
            throw std::logic_error(
                "G65 authentic NOAA hour-two source wind/precip was imputed");
    }
    // Explicitly deny running the hour-zero-only G26/G63/G64 formulas
    // against the hour-two frame, even with a valid committed hidden state.
    // This is a negative safety test, NOT a stand-in for hour-two physics.
    bool refused_replay=false;
    try {
        scheduler.advance_with_fresh_physics(
            [&](const MultiHourFrame& next)
                ->std::unique_ptr<MultiHourPhysics> {
                if(next.hour_index!=1||next.input.end!=hour2.input.end)
                    throw std::logic_error("G65 hour-two replay clock drift");
                return std::make_unique<G65RealNoaaFirstHourActor>(
                    scheduler,clocks,source,actual);
            },
            [](const MultiHourFrame&) {
                throw std::logic_error(
                    "G65 hour-two actor unexpectedly reached P6F precommit");
            },
            [](MultiHourPhysics&,
               const UnifiedMultistationHourlyScheduler&) noexcept {});
    }catch(const std::logic_error& e) {
        if(std::string(e.what())!=
           "G65 first-hour source actor refuses cross-hour replay")throw;
        refused_replay=true;
    }
    if(!refused_replay||scheduler.completed_hours()!=1||
       clocks.latest_upper_hour()!=first_end||
       clocks.latest_gamma_hour()!=first_end||
       !g65_equal_real4_bits(scheduler.committed_memory().zi_m,committed.zi_m)||
       !g65_equal_real4_bits(scheduler.committed_memory().ziconv_m,committed.ziconv_m)||
       !g65_equal_real4_bits(scheduler.committed_memory().dptt_k,committed.dptt_k))
        throw std::logic_error(
            "G65 hour-two unsupported physics failed closed/altered hour-one state");

    // G18E4 genuine hour-two PREPDI stage zero is already reusable:
    // evaluate authentic AA/BB upper buffers and per-US CGAMMA against
    // scheduler-owned hour-one ZI/ZICONV/DPTT and committed clocks.
    // Do not call any remaining second-hour physics stage, and NEVER
    // publish this stage-zero-only station-clock candidate.
    auto hour2_live=scheduler.preview_next_hour();
    G18E4SelectedPrepdiStageAdapter second_prepdi(
        scheduler,clocks,source.original_metinp);
    second_prepdi.run_selected(
        p6::kHefeiOriginalStageOrder[0],hour2_live,true);
    const auto& second_upper=second_prepdi.selected_upper_for(hour2_live);
    const auto& second_gamma=second_prepdi.selected_gamma_for(hour2_live);
    if(!second_prepdi.staged()||second_prepdi.published()||
       second_upper.end!=hour2.input.end||
       second_gamma.end!=hour2.input.end||
       second_gamma.hour_index!=1||
       second_upper.station_ids.size()!=source.stations.upper.size()||
       second_gamma.station_ids!=second_upper.station_ids||
       second_upper.physical_aa_index.size()!=source.stations.upper.size()||
       second_upper.physical_bb_index.size()!=source.stations.upper.size()||
       second_gamma.candidate.size()!=source.stations.upper.size()||
       second_gamma.lapse.size()!=source.stations.upper.size())
        throw std::logic_error(
            "G65 authentic hour-two AA/BB/CGAMMA PREPDI stage-zero invalid");
    // Preflight is allowed while G14 is at committed hour 1; publishing
    // is NOT allowed because the remaining 16 stages and P6F are absent.
    second_prepdi.require_publishable_before_g14_commit(hour2_live);
    if(scheduler.completed_hours()!=1||
       second_prepdi.published()||
       clocks.latest_upper_hour()!=first_end||
       clocks.latest_gamma_hour()!=first_end||
       !g65_equal_real4_bits(scheduler.committed_memory().zi_m,committed.zi_m)||
       !g65_equal_real4_bits(scheduler.committed_memory().ziconv_m,committed.ziconv_m)||
       !g65_equal_real4_bits(scheduler.committed_memory().dptt_k,committed.dptt_k))
        throw std::logic_error(
            "G65 PREPDI-only hour-two stage prematurely published G14/clocks");

    // G26A executes *real* second-hour PREPDI [0] and WIND1 [1]
    // against the live G14 next-hour frame, with the prior G14 memory
    // and AA/BB/CGAMMA clocks committed at hour one. The separate G45
    // six-hour source-only WIND1 path is comparison-only; the G26
    // physical stage never receives G45 arrays as meteorological input.
    auto live_wind_frame=scheduler.preview_next_hour();
    G26SourceFileBackedG14DiagnoBridge hour2_diagno(
        scheduler,clocks,source,true);
    for(std::size_t stage=0;stage<2;++stage) {
        const auto result=hour2_diagno.run(
            p6::kHefeiOriginalStageOrder[stage],live_wind_frame);
        if(!result.completed||
           result.source!=p6::NativeHourSource::NativeCpp)
            throw std::logic_error(
                "G65 second-hour live G26A PREPDI/WIND1 stage absent");
    }
    if(hour2_diagno.selected_checkpoints()!=2||
       live_wind_frame.hour_index!=1||
       live_wind_frame.input.end!=hour2.input.end)
        throw std::logic_error("G65 second-hour G26A stage identity drift");
    const auto& live_wind=hour2_diagno.selected_source_wind1_after_stage(
        live_wind_frame);
    const auto comparison=g45_selected_source_six_hour_wind1(paths,true);
    if(comparison.hours.size()!=6||
       comparison.source_end_utc.size()!=6||
       comparison.source_end_utc[1]!=hour2.input.end||
       comparison.g21_g39_g24_g26_accepted||
       comparison.original_p5_surf_mutated||
       comparison.original_previous_ziconv_accepted)
        throw std::logic_error(
            "G65 independent original-source G45 hour-two WIND1 unavailable");
    const auto& ref_wind=comparison.hours[1].native_firstguess;
    const std::size_t size=9U*82U*85U;
    if(live_wind.nx!=82||live_wind.ny!=85||live_wind.nz!=9||
       ref_wind.nx!=82||ref_wind.ny!=85||ref_wind.nz!=9||
       live_wind.u_mps.size()!=size||live_wind.v_mps.size()!=size||
       !g65_equal_real4_bits(live_wind.u_mps,ref_wind.u_mps)||
       !g65_equal_real4_bits(live_wind.v_mps,ref_wind.v_mps))
        throw std::logic_error(
            "G65 real hour-two live G26 WIND1 U/V differs from G45 source path");
    // No precommit output or clock publication is possible at stage 1;
    // WIND1 must not create or replace next-hour hidden COMP memory.
    if(scheduler.completed_hours()!=1||
       clocks.latest_upper_hour()!=first_end||
       clocks.latest_gamma_hour()!=first_end||
       !g65_equal_real4_bits(scheduler.committed_memory().zi_m,committed.zi_m)||
       !g65_equal_real4_bits(scheduler.committed_memory().ziconv_m,committed.ziconv_m)||
       !g65_equal_real4_bits(scheduler.committed_memory().dptt_k,committed.dptt_k)||
       !g65_equal_real4_bits(live_wind_frame.next.zi_m,committed.zi_m)||
       !g65_equal_real4_bits(live_wind_frame.next.ziconv_m,committed.ziconv_m)||
       !g65_equal_real4_bits(live_wind_frame.next.dptt_k,committed.dptt_k))
        throw std::logic_error(
            "G65 second-hour physical WIND1 changed committed COMP memory/clocks");

    G65NoaaFirstHourCommitReceipt receipt;
    receipt.end=first_end;
    receipt.committed_memory=committed;
    receipt.committed_hours=scheduler.completed_hours();
    receipt.g59_bitwise_compared_words=accepted.second;
    receipt.hidden_bitwise_compared_words=3U*82U*85U;
    receipt.rejected_precommit_rolled_back=true;
    receipt.committed_with_published_station_clocks=true;
    receipt.hour2_preview_uses_committed_state=true;
    receipt.hour2_raw_source_admission_verified=true;
    receipt.hour2_firsthour_replay_rejected_atomically=true;
    receipt.hour2_prepdi_stage0_staged_preflight_only=true;
    receipt.hour2_live_g26_wind1_bitwise_compared_words=2U*9U*82U*85U;
    receipt.hour2_live_g26_stage01_uncommitted=true;
    return receipt;
}
} // namespace cteas::calmet::p6g
