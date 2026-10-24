#pragma once
// S4-R1c9j: authentic NOAA first/second-hour G14 transactions.
// Selected WATER route. Second-hour positive commit is explicitly opted in
// and research-only, with independent original-hour Fortran science performed
// outside this actor; general P6 production remains NOT_ACCEPTED.
// All 17 physics stages run on the SAME scheduler-owned frame; no G54/G59
// numbers are used as native forcing. Failed precommit cannot publish state.
#include "cteas/p6/p6g_g62_real_noaa_firsthour_memory_seed.hpp"
#include "cteas/p6/p6g_g45_six_hour_water_wind1.hpp"
#include "cteas/p6/p6g_g66_noaa_hour3_g22_trace.hpp"
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cmath>
#include <memory>
#include <optional>
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

// S4-R1c9j: a fresh second-hour 17-stage actor can serve either a forced
// rollback trial or an explicitly opted-in positive G14 transaction. No
// general P6 production is enabled, and independent original Fortran science
// is a separate required gate.
class G65RealNoaaSecondHourActor final : public MultiHourPhysics {
public:
    G65RealNoaaSecondHourActor(
        const UnifiedMultistationHourlyScheduler& scheduler,
        G18D2StationClockAuthority& clocks,
        const G19FileBackedCase& source,
        const G41SelectedNoowWaterFirstHourSource& original)
        :diagno_(scheduler,clocks,source,true),
         comp_(diagno_,source,true,&original) {}

    [[nodiscard]] p6::NativeHourStageResult run(
        p6::NativeHourStage stage,MultiHourFrame& frame) override {
        if(frame.hour_index!=1||cursor_>=p6::kHefeiOriginalStageOrder.size()||
           stage!=p6::kHefeiOriginalStageOrder[cursor_])
            throw std::logic_error(
                "G65 second-hour actor wrong hour/stage");
        const auto result=(cursor_<12)
            ?diagno_.run(stage,frame):comp_.run(stage,frame);
        if(!result.completed||result.source!=p6::NativeHourSource::NativeCpp)
            throw std::logic_error(
                "G65 second-hour actor missing native physics");
        ++cursor_;
        return result;
    }

    [[nodiscard]] const G64RealNoaaP6FPrecommit& precommit(
        const MultiHourFrame& frame) const {
        if(cursor_!=17||frame.hour_index!=1)
            throw std::logic_error(
                "G65 second-hour precommit before all 17 native stages");
        const auto& candidate=comp_.source_water_p6f_stage16(frame);
        if(!candidate.actual_g14_stage16_precommit_validated||
           candidate.g14_hour_committed||candidate.source_clocks_published||
           candidate.candidate_dataset.hourly.size()!=45||
           candidate.serialized_prepared_only.empty())
            throw std::logic_error(
                "G65 second-hour has invalid P6F candidate");
        diagno_.require_station_clock_preflight(frame);
        return candidate;
    }

    void require_station_clock_preflight(const MultiHourFrame& frame) const {
        if(cursor_!=17||frame.hour_index!=1)
            throw std::logic_error("G65 second-hour clock preflight before P6F");
        diagno_.require_station_clock_preflight(frame);
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


// S4-R1c9v: fresh, strictly scoped real NOAA hour-three G14 executor.
// Stages0..11 are G26A, stages12..16 are the same G26B source-native
// physics used by the independently compared unpublished G64 candidate.
// This actor is created afresh on EVERY rollback/retry. It does not remove
// the default G22/G26B/G64 hour_index>1 production guards.
class G65RealNoaaThirdHourTrialActor final : public MultiHourPhysics {
public:
    G65RealNoaaThirdHourTrialActor(
        const UnifiedMultistationHourlyScheduler& owner,
        G18D2StationClockAuthority& clocks,
        const G19FileBackedCase& source,
        const G41SelectedNoowWaterFirstHourSource& original,
        const G66NativeHour2WaterState& native_prior)
        :diagno_(owner,clocks,source,true,&native_prior,true,true),
         source_(source),original_(original) {}

    [[nodiscard]] p6::NativeHourStageResult run(
        p6::NativeHourStage stage,MultiHourFrame& frame) override {
        if(frame.hour_index!=2||cursor_>=p6::kHefeiOriginalStageOrder.size()||
           stage!=p6::kHefeiOriginalStageOrder[cursor_])
            throw std::logic_error(
                "G65 third-hour trial actor wrong hour/stage");
        if(cursor_==12)
            comp_.emplace(diagno_,source_,true,&original_,true,true,true);
        const auto result=(cursor_<12)?diagno_.run(stage,frame)
                                     :comp_->run(stage,frame);
        if(!result.completed||result.source!=p6::NativeHourSource::NativeCpp)
            throw std::logic_error(
                "G65 third-hour trial actor missing source-native stage");
        ++cursor_;
        return result;
    }

    [[nodiscard]] const G64RealNoaaP6FPrecommit& precommit(
        const MultiHourFrame& frame) const {
        if(cursor_!=17||frame.hour_index!=2||!comp_)
            throw std::logic_error(
                "G65 third-hour trial P6F before all 17 native stages");
        const auto& candidate=comp_->source_water_p6f_stage16(frame);
        if(!candidate.actual_g14_stage16_precommit_validated||
           candidate.g14_hour_committed||candidate.source_clocks_published||
           candidate.ready_for_next_hour||
           candidate.candidate_dataset.hourly.size()!=45||
           candidate.serialized_prepared_only.empty())
            throw std::logic_error(
                "G65 third-hour trial P6F already published or incomplete");
        diagno_.require_station_clock_preflight(frame);
        return candidate;
    }

    void require_station_clock_preflight(
        const MultiHourFrame& frame) const {
        if(cursor_!=17||frame.hour_index!=2)
            throw std::logic_error(
                "G65 third-hour trial clock preflight before G64 P6F");
        diagno_.require_station_clock_preflight(frame);
    }

    [[nodiscard]] bool publish_after_commit_noexcept() noexcept {
        return cursor_==17&&comp_.has_value()&&
            diagno_.try_publish_after_selected_g14_commit_noexcept();
    }
private:
    G26SourceFileBackedG14DiagnoBridge diagno_;
    const G19FileBackedCase& source_;
    const G41SelectedNoowWaterFirstHourSource& original_;
    std::optional<G26BSourceFileBackedCompBridge> comp_;
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
    std::size_t hour2_live_g26_fradj_compared_words=0;
    bool hour2_live_g26_stage02_uncommitted=false;
    std::size_t hour2_live_g26_thermal_compared_words=0;
    bool hour2_live_g26_stage06_uncommitted=false;
    std::size_t hour2_live_g26_g24_compared_words=0;
    bool hour2_live_g26_stage11_uncommitted=false;
    std::size_t hour2_live_g26_mixht_compared_words=0;
    bool hour2_live_g26_stage12_uncommitted=false;
    std::size_t hour2_live_g26_avemix_compared_words=0;
    bool hour2_live_g26_stage13_uncommitted=false;
    std::size_t hour2_live_g26_wstarr_compared_words=0;
    bool hour2_live_g26_stage14_uncommitted=false;
    std::size_t hour2_live_g26_temp3d_compared_words=0;
    bool hour2_live_g26_stage15_uncommitted=false;
    bool hour2_stage16_prepared_unpublished=false;
    bool hour2_real_g14_full17_rollback_verified=false;
    bool hour2_positive_g14_commit_verified=false;
    bool hour2_positive_station_clocks_published=false;
    bool hour3_preview_inherits_hour2_memory=false;
    bool hour3_real_g26a_stage02_preflight_only=false;
    bool hour3_g22_thermal_guard_remains_rejected=false;
    bool hour3_test_only_native_g22_trace_ready=false;
    std::vector<std::uint8_t> hour3_test_only_native_g22_trace_bytes;
    bool hour3_live_g26a_stage3_trial_only=false;
    std::vector<std::uint8_t> hour3_live_g26a_stage3_trace_bytes;
    bool hour3_native_g23_g24_stage11_trial_only=false;
    std::vector<std::uint8_t> hour3_native_g23_g24_trace_bytes;
    bool hour3_native_g26b_stage12_trial_only=false;
    std::vector<std::uint8_t> hour3_native_g26b_stage12_trace_bytes;
    bool hour3_native_g26b_stage15_trial_only=false;
    std::vector<std::uint8_t> hour3_native_g26b_stage15_trace_bytes;
    bool hour3_native_g26b_p6f45_trial_only=false;
    std::vector<std::uint8_t> hour3_native_g26b_p6f45_bytes;
    bool hour3_g14_rollback_verified=false;
    bool hour3_g14_positive_commit_verified=false;
    bool hour3_station_clocks_published=false;
    bool hour4_preview_inherits_hour3_memory=false;
    bool hour4_g26a_stage0_2_source_preflight_only=false;
    bool hour4_g22_production_guard_rejected=false;
    bool hour4_g22_forensic_trace_only=false;
    std::vector<std::uint8_t> hour4_g22_forensic_trace_bytes;
    bool hour4_live_g26a_stage3_6_uncommitted=false;
    bool hour4_live_g22_matches_detached=false;
    p6::NativeGridMemory hour2_committed_memory;
    std::size_t hour2_p6f_compared_words=0;
    // Explicit forensic handoff only: NOT a committed model output.
    std::vector<std::uint8_t> hour2_unpublished_p6f_bytes;
    // Read-only source-native stage14 AoS [ZICONV,QH,TEMP2D,RHO,WSTAR]
    // 6970 cells x 5 REAL4, independent of the reference Fortran model.
    std::vector<float> hour2_unpublished_wstarr_input_rows;
    // [ZI,ZICONV] before and after AVEMIX (4 REAL4 per cell) for independent source comparison.
    std::vector<float> hour2_unpublished_mixht_avemix_rows;
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

// Decode serialization ONLY at the G65/P6F boundary. G26A and G66 see
// typed native prior physical state, never depend on P6F writer linkage.
inline G66NativeHour2WaterState g65_native_hour2_water_from_p6f(
    const cteas::p6f::Calmet21File& native,
    std::chrono::sys_seconds expected_end) {
    if(native.hourly.size()!=45)
        throw std::invalid_argument("G65 native hour2 P6F field count");
    const auto field=[&](const std::string& label)
        ->const std::vector<float>& {
        const cteas::p6f::Calmet21Field* found=nullptr;
        for(const auto& f:native.hourly)
            if(f.label==label) {
                if(found)throw std::invalid_argument(
                    "G65 duplicate native P6F water field");
                found=&f;
            }
        if(!found||found->integer||found->real_values.size()!=6970||
           cteas::p6f::instant_seconds(found->end)!=
               expected_end.time_since_epoch().count()||
           cteas::p6f::instant_seconds(found->begin)!=
               (expected_end-std::chrono::hours{1})
                   .time_since_epoch().count())
            throw std::invalid_argument(
                "G65 native P6F water field clock/shape invalid");
        return found->real_values;
    };
    G66NativeHour2WaterState prior;
    prior.begin=expected_end-std::chrono::hours{1};
    prior.end=expected_end;
    prior.ustar_mps=field("USTAR   ");
    prior.el_m=field("EL      ");
    prior.explicitly_native_p6f_origin=true;
    return prior;
}

inline G65NoaaFirstHourCommitReceipt
g65_real_noaa_firsthour_atomic_commit(
    const G19SourceFilePaths& paths,bool explicitly_forensic_only,
    bool opt_in_positive_hour2_transaction=false,
    bool opt_in_third_hour_diagno_preflight=false,
    bool opt_in_hour3_g22_trace_only=false,
    bool opt_in_hour3_live_g22_trial=false,
    bool opt_in_hour3_windtail_trial=false,
    bool opt_in_hour3_comp_stage12_trial=false,
    bool opt_in_hour3_comp_stage15_trial=false,
    bool opt_in_hour3_p6f_trial=false,
    bool opt_in_hour3_g14_transaction=false,
    bool opt_in_hour4_g26a_preflight=false,
    bool opt_in_hour4_g22_trace_only=false) {
    if(opt_in_hour4_g22_trace_only&&!opt_in_hour4_g26a_preflight)
        throw std::invalid_argument(
            "G65 hour4 G22 forensic trace requires hour4 source preflight");
    if(opt_in_hour4_g26a_preflight&&!opt_in_hour3_g14_transaction)
        throw std::invalid_argument(
            "G65 hour4 PREPDI requires committed hour3 trial");
    if(opt_in_hour3_g14_transaction&&!opt_in_hour3_p6f_trial)
        throw std::invalid_argument(
            "G65 hour3 G14 transaction requires native P6F trial");
    if(opt_in_hour3_p6f_trial&&!opt_in_hour3_comp_stage15_trial)
        throw std::invalid_argument(
            "G65 hour3 P6F requires stage15 trial");
    if(opt_in_hour3_comp_stage15_trial&&!opt_in_hour3_comp_stage12_trial)
        throw std::invalid_argument(
            "G65 hour3 stage15 requires stage12 opt-in");
    if(opt_in_hour3_comp_stage12_trial&&!opt_in_hour3_windtail_trial)
        throw std::invalid_argument(
            "G65 hour3 COMP stage12 requires live wind-tail trial");
    if(opt_in_hour3_windtail_trial&&!opt_in_hour3_live_g22_trial)
        throw std::invalid_argument(
            "G65 hour3 wind-tail requires live G22 trial");
    if(opt_in_hour3_live_g22_trial&&!opt_in_hour3_g22_trace_only)
        throw std::invalid_argument(
            "G65 hour3 live G22 trial requires independent detached trace");
    if((opt_in_third_hour_diagno_preflight||opt_in_hour3_g22_trace_only)&&
       !opt_in_positive_hour2_transaction)
        throw std::invalid_argument(
            "G65 third-hour PREPDI requires committed hour-two trial");
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
    if(opt_in_hour3_g22_trace_only) {
        // CALMET COMP calls MISSFC before every DIAGNO. In the real NOAA
        // third hour SS #1 has missing pressure/T/RH/cloud; raw P5 is
        // immutable, while the model-internal five nonwind fields must
        // be repaired from the current-hour valid station #2.
        // This isolated G66 forensic route is the ONLY additional caller;
        // existing G26 production/hour>1 guards remain untouched.
        const auto& raw=actual.source.surface.hourly.at(2);
        const auto third_missfc=g43_original_comp_missfc_source_only(
            actual,raw,true);
        if(!third_missfc.source_comp_missfc_complete||
           third_missfc.original_raw.end!=raw.end||
           third_missfc.original_comp_resolved.end!=raw.end||
           third_missfc.original_comp_resolved.by_station.size()!=2)
            throw std::logic_error("G66 third-hour source MISSFC invalid");
        for(std::size_t site=0;site<2;++site) {
            const auto& a=raw.by_station[site];
            const auto& b=third_missfc.original_comp_resolved.by_station[site];
            if(!b.pressure_valid||!b.temperature_valid||
               !b.humidity_valid||!b.cloud_valid||!b.ceiling_valid||
               a.wind_valid!=b.wind_valid||
               a.wind_speed_mps!=b.wind_speed_mps||
               a.wind_direction_deg!=b.wind_direction_deg||
               a.precip_code!=b.precip_code||
               a.precipitation_code_valid!=b.precipitation_code_valid)
                throw std::logic_error(
                    "G66 MISSFC cannot repair P5 wind or precip");
        }
        source.surface.hourly[2]=third_missfc.original_comp_resolved;
    }
    if(opt_in_hour4_g22_trace_only) {
        // Original CALMET COMP calls source MISSFC EACH hour before
        // DIAGNO (calmet.for COMP ~L3986, MISSFC ~L9762). Raw station #1
        // in the fourth NOAA hour has missing T/P/RH, not a zero-value
        // measurement. Preserve the raw immutable P5 series; only the
        // detached internal G14 source-hour copy receives the source's
        // five nonwind replacements. Wind/precip cannot be invented.
        const auto& raw=actual.source.surface.hourly.at(3);
        const auto fourth_missfc=g43_original_comp_missfc_source_only(
            actual,raw,true);
        if(!fourth_missfc.source_comp_missfc_complete||
           fourth_missfc.original_raw.end!=raw.end||
           fourth_missfc.original_comp_resolved.end!=raw.end||
           fourth_missfc.original_comp_resolved.by_station.size()!=2)
            throw std::logic_error("G65 native hour4 MISSFC source incomplete");
        for(std::size_t site=0;site<2;++site) {
            const auto& before=raw.by_station[site];
            const auto& after=
                fourth_missfc.original_comp_resolved.by_station[site];
            if(!after.pressure_valid||!after.temperature_valid||
               !after.humidity_valid||!after.cloud_valid||
               !after.ceiling_valid||
               before.wind_valid!=after.wind_valid||
               before.wind_speed_mps!=after.wind_speed_mps||
               before.wind_direction_deg!=after.wind_direction_deg||
               before.precip_code!=after.precip_code||
               before.precipitation_code_valid!=
                   after.precipitation_code_valid)
                throw std::logic_error(
                    "G65 native hour4 MISSFC altered raw wind or precipitation");
        }
        source.surface.hourly[3]=fourth_missfc.original_comp_resolved;
    }
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
    // S4-R1c8y: execute original stage 2 FRADJ on this SAME actual G14
    // second-hour G26A actor, using its live stage-0 CGAMMA and stage-1
    // source-native WIND1. Recompute an independent source-only current
    // gamma/FRADJ candidate; no independent values feed the live actor.
    const auto fradj_result=hour2_diagno.run(
        p6::kHefeiOriginalStageOrder[2],live_wind_frame);
    if(!fradj_result.completed||
       fradj_result.source!=p6::NativeHourSource::NativeCpp||
       hour2_diagno.selected_checkpoints()!=3)
        throw std::logic_error(
            "G65 authentic NOAA hour-two live G26A FRADJ stage2 absent");
    const auto& live_fradj=
        hour2_diagno.selected_source_fradj_after_stage(live_wind_frame);
    const auto external_clocks=clocks.prepare_selected(
        scheduler,source.original_metinp,true);
    if(external_clocks.hour_index!=1||
       external_clocks.source_end!=live_wind_frame.input.end||
       !clocks.can_publish_after_next_g14_commit(scheduler,external_clocks))
        throw std::logic_error(
            "G65 detached NOAA second-hour source CGAMMA was not preflighted");
    // Independently source real G45 hourly WIND1 and reconstruct original
    // G21 gamma, SURFVAR(IAVET=1), TERSET/FRADJ and final SURFVAR; the
    // G26A actor neither reads the oracle nor receives G45 input.
    const auto independent_fradj=g21_original_source_clock_fradj_kernel(
        live_wind_frame,source,source.surface_controls,
        external_clocks.cgamma,ref_wind,true,true);
    const std::size_t n=82U*85U;
    if(live_fradj.end!=live_wind_frame.input.end||
       independent_fradj.end!=live_wind_frame.input.end||
       live_fradj.gamma_k_per_m.size()!=n||
       live_fradj.temperature_before_k.size()!=n||
       live_fradj.temperature_after_k.size()!=n||
       live_fradj.corrected_wind.u.size()!=size||
       live_fradj.corrected_wind.v.size()!=size||
       !g65_equal_real4_bits(live_fradj.gamma_k_per_m,
                             independent_fradj.gamma_k_per_m)||
       !g65_equal_real4_bits(live_fradj.temperature_before_k,
                             independent_fradj.temperature_before_k)||
       !g65_equal_real4_bits(live_fradj.temperature_after_k,
                             independent_fradj.temperature_after_k)||
       !g65_equal_real4_bits(live_fradj.corrected_wind.u,
                             independent_fradj.corrected_wind.u)||
       !g65_equal_real4_bits(live_fradj.corrected_wind.v,
                             independent_fradj.corrected_wind.v))
        throw std::logic_error(
            "G65 actual second-hour G26A FRADJ differs from standalone"
            " original-source G21 after committed CGAMMA handoff");
    // S4-R1c8z: execute the genuine second-hour WATER/LAND thermal
    // checkpoints 3..6 (HEATFX, AIRDEN, ELUSTR, SLOPE) on the SAME live
    // G14 frame/actor, without calling MIXHTST, COMP or P6F.
    for(std::size_t stage=3;stage<=6;++stage) {
        const auto completed=hour2_diagno.run(
            p6::kHefeiOriginalStageOrder[stage],live_wind_frame);
        if(!completed.completed||
           completed.source!=p6::NativeHourSource::NativeCpp)
            throw std::logic_error(
                "G65 genuine second-hour G26A thermal/SLOPE stage absent");
    }
    if(hour2_diagno.selected_checkpoints()!=7)
        throw std::logic_error(
            "G65 second-hour G26A thermal checkpoint cursor drift");
    const auto& live_thermal=
        hour2_diagno.selected_source_water_thermal_after_stage(live_wind_frame);

    // Comparator reconstructs current-hour SURFVAR two-pass, G39 thermal,
    // and source G22 SLOPE solely from raw/source-repaired NOAA plus the
    // independently staged G21 FRADJ. It never feeds G26's live physics.
    G17B4TwoPassSurfvar independent_two_pass(
        live_wind_frame.grid,live_wind_frame.stations,source.surface,
        live_wind_frame.surface,source.surface_controls,true);
    independent_two_pass.after_wind1_before_fradj(
        live_wind_frame.input.end,ref_wind.u_mps,ref_wind.v_mps);
    independent_two_pass.after_fradj_before_heatfx(
        live_wind_frame.input.end,independent_fradj.corrected_wind.u,
        independent_fradj.corrected_wind.v);
    const float source_zm=
        0.5f*(live_wind_frame.source_controls->zface_m[0]+
              live_wind_frame.source_controls->zface_m[1]);
    const auto standalone_water=
        g39_original_noow_water_postfradj_thermal_reference(
            live_wind_frame.grid,live_wind_frame.stations,
            live_wind_frame.surface,independent_two_pass,
            independent_fradj.corrected_wind,source.original_metinp,
            source_zm,true);
    const auto standalone_slope=g22_original_slope_after_elustr(
        live_wind_frame.grid,*live_wind_frame.source_controls,
        source.original_metinp,independent_fradj.corrected_wind,
        standalone_water.heat,standalone_water.elustr,true);
    if(live_thermal.end!=live_wind_frame.input.end||
       live_thermal.heat.temperature_k.size()!=n||
       live_thermal.heat.density_kg_m3.size()!=n||
       live_thermal.elustr.qh_wm2.size()!=n||
       live_thermal.elustr.ustar_mps.size()!=n||
       live_thermal.elustr.el_m.size()!=n||
       live_thermal.post_slope_wind.u.size()!=size||
       live_thermal.post_slope_wind.v.size()!=size||
       standalone_water.selected_original_water_cells!=63||
       standalone_water.water_ustar_el_zi_ready||
       standalone_water.g14_g26_production_ready||
       !g65_equal_real4_bits(live_thermal.heat.temperature_k,
                             standalone_water.heat.temperature_k)||
       !g65_equal_real4_bits(live_thermal.heat.density_kg_m3,
                             standalone_water.heat.density_kg_m3)||
       !g65_equal_real4_bits(live_thermal.elustr.qh_wm2,
                             standalone_water.elustr.qh_wm2)||
       !g65_equal_real4_bits(live_thermal.elustr.ustar_mps,
                             standalone_water.elustr.ustar_mps)||
       !g65_equal_real4_bits(live_thermal.elustr.el_m,
                             standalone_water.elustr.el_m)||
       !g65_equal_real4_bits(live_thermal.post_slope_wind.u,
                             standalone_slope.post_slope_wind.u)||
       !g65_equal_real4_bits(live_thermal.post_slope_wind.v,
                             standalone_slope.post_slope_wind.v))
        throw std::logic_error(
            "G65 NOAA second-hour G26A WATER thermal/SLOPE diverged"
            " from detached source-only G39/G22 REAL4 comparator");

    // S4-R1c9a: second-hour source-controlled original stage7..11.
    // Run native STHEOR/MIXHTST/DIAGI, INTER2 and final WINDBC/SMOOTH/
    // DIVCEL/W on the SAME live G14 frame and current post-SLOPE wind.
    // The STHEOR station reads the actual prior-hour COMP memory.
    for(std::size_t stage=7;stage<=11;++stage) {
        const auto complete=hour2_diagno.run(
            p6::kHefeiOriginalStageOrder[stage],live_wind_frame);
        if(!complete.completed||
           complete.source!=p6::NativeHourSource::NativeCpp)
            throw std::logic_error(
                "G65 true NOAA hour-two G26A STHEOR/INTER2/G24 failed");
    }
    if(hour2_diagno.selected_checkpoints()!=12)
        throw std::logic_error(
            "G65 NOAA hour-two G26A DIAGNO checkpoint 12 not reached");
    const auto& g14_g23=hour2_diagno.selected_station_for_comp(
        live_wind_frame);
    const auto& g14_g24=hour2_diagno.selected_wind_for_comp(
        live_wind_frame);

    // Reconstruct a separate hour-two source-native physics chain from
    // raw observed G45 WIND1 and independently calculated G21 FRADJ.
    // This copy inherits exactly the same committed G14 prior state;
    // NO result is injected into the live actor or G14 frame.
    auto reference_frame=scheduler.preview_next_hour();
    if(reference_frame.hour_index!=1||
       reference_frame.input.end!=live_wind_frame.input.end||
       !g65_equal_real4_bits(reference_frame.previous.zi_m,committed.zi_m)||
       !g65_equal_real4_bits(reference_frame.previous.ziconv_m,committed.ziconv_m)||
       !g65_equal_real4_bits(reference_frame.previous.dptt_k,committed.dptt_k))
        throw std::logic_error(
            "G65 detached hour-two source path lost committed COMP prior");
    auto independent_profiles=g20_source_wind1_profiles_kernel(
        reference_frame,true,true);
    const auto independently_thermal=g22_selected_source_thermal_slope(
        reference_frame,source,
        {ref_wind.u_mps,ref_wind.v_mps},
        independent_fradj,true);
    const auto separately_stheor=g23_source_stheor_diagi_inter2(
        reference_frame,source,std::move(independent_profiles),
        independent_fradj,independently_thermal,true);
    const auto separately_g24=g24_selected_original_wind_tail(
        reference_frame,source,separately_stheor,true);
    // G23 site count is determined from the *second* P5 hour, which
    // can differ from the first hour's source-valid SS selection.
    std::vector<int> hour2_valid_station_ids;
    for(std::size_t i=0;i<live_wind_frame.surface.by_station.size();++i)
        if(live_wind_frame.surface.by_station[i].wind_valid)
            hour2_valid_station_ids.push_back(
                live_wind_frame.stations.surface[i].id);
    const std::size_t g24_words=2U*2U*9U*82U*85U+
        10U*82U*85U;
    if(g14_g23.end!=live_wind_frame.input.end||
       g14_g23.hour_index!=1||
       hour2_valid_station_ids.empty()||
       g14_g23.station_diagi.size()!=hour2_valid_station_ids.size()||
       separately_stheor.station_diagi.size()!=hour2_valid_station_ids.size()||
       g14_g23.inter2_u.component_mps.size()!=size||
       g14_g23.inter2_v.component_mps.size()!=size||
       g14_g24.wind.u_mps.size()!=size||
       g14_g24.wind.v_mps.size()!=size||
       g14_g24.wind.w_face_mps.size()!=10U*n||
       !g65_equal_real4_bits(g14_g23.inter2_u.component_mps,
                             separately_stheor.inter2_u.component_mps)||
       !g65_equal_real4_bits(g14_g23.inter2_v.component_mps,
                             separately_stheor.inter2_v.component_mps)||
       !g65_equal_real4_bits(g14_g24.wind.u_mps,
                             separately_g24.wind.u_mps)||
       !g65_equal_real4_bits(g14_g24.wind.v_mps,
                             separately_g24.wind.v_mps)||
       !g65_equal_real4_bits(g14_g24.wind.w_face_mps,
                             separately_g24.wind.w_face_mps)||
       !g65_equal_real4_bits(live_wind_frame.fields.u_mps,
                             separately_g24.wind.u_mps)||
       !g65_equal_real4_bits(live_wind_frame.fields.v_mps,
                             separately_g24.wind.v_mps)||
       !g65_equal_real4_bits(live_wind_frame.fields.w_face_mps,
                             separately_g24.wind.w_face_mps))
        throw std::logic_error(
            "G65 NOAA second-hour original-source STHEOR/INTER2/G24 "
            "does not match live scheduler-bound G26A at bit level");
    for(std::size_t i=0;i<hour2_valid_station_ids.size();++i)
        if(g14_g23.station_diagi[i].surface_id!=hour2_valid_station_ids[i]||
           separately_stheor.station_diagi[i].surface_id!=
             hour2_valid_station_ids[i]||
           g14_g23.station_diagi[i].end!=live_wind_frame.input.end||
           separately_stheor.station_diagi[i].end!=live_wind_frame.input.end)
            throw std::logic_error(
                "G65 NOAA hour-two STHEOR changed source-valid SS ordinal");
    (void)g24_words;
    // S4-R1c9b: enter genuine second-hour G26B MIXHT stage12 on the
    // SAME G14 frame after authentic original-source stage11 U/V/W.
    // This candidate consumes previous-hour committed COMP arrays;
    // its station count must follow this hour's actual P5 wind-valid mask.
    G26BSourceFileBackedCompBridge hour2_comp(
        hour2_diagno,source,true,&actual);
    const auto live_mixht_result=hour2_comp.run(
        p6::kHefeiOriginalStageOrder[12],live_wind_frame);
    if(!live_mixht_result.completed||
       live_mixht_result.source!=p6::NativeHourSource::NativeCpp)
        throw std::logic_error(
            "G65 real NOAA secondhour G26B stage12 did not run");
    const auto& live_mixht=hour2_comp.source_water_mixht_stage12(
        live_wind_frame);
    // Detached comparator independently replays current observed G26A
    // 12-stage DIAGNO from the published previous-hour source clock and
    // committed scheduler memory, then runs G26B MIXHT on the detached
    // authentic source frame. No numeric candidate is fed to live G14.
    auto detached_frame=scheduler.preview_next_hour();
    G26SourceFileBackedG14DiagnoBridge detached_diagno(
        scheduler,clocks,source,true);
    for(std::size_t stage=0;stage<12;++stage) {
        const auto result=detached_diagno.run(
            p6::kHefeiOriginalStageOrder[stage],detached_frame);
        if(!result.completed||
           result.source!=p6::NativeHourSource::NativeCpp)
            throw std::logic_error(
                "G65 detached secondhour G26A source physics not complete");
    }
    G26BSourceFileBackedCompBridge detached_comp(
        detached_diagno,source,true,&actual);
    const auto detached_mixht_result=detached_comp.run(
        p6::kHefeiOriginalStageOrder[12],detached_frame);
    if(!detached_mixht_result.completed||
       detached_mixht_result.source!=p6::NativeHourSource::NativeCpp)
        throw std::logic_error(
            "G65 detached secondhour G26B MIXHT not complete");
    const auto& separate_mixht=detached_comp.source_water_mixht_stage12(
        detached_frame);
    const auto cell_count=82U*85U;
    if(live_mixht.end!=live_wind_frame.input.end||
       separate_mixht.end!=live_wind_frame.input.end||
       live_mixht.valid_ss!=hour2_valid_station_ids.size()||
       separate_mixht.valid_ss!=hour2_valid_station_ids.size()||
       live_mixht.water_cells!=63||
       live_mixht.land_cells!=6907||
       separate_mixht.water_cells!=63||
       separate_mixht.land_cells!=6907||
       !live_mixht.source_native_comp_mixht_uncommitted||
       !separate_mixht.source_native_comp_mixht_uncommitted||
       live_mixht.zi_before_avemix_m.size()!=cell_count||
       live_mixht.ziconv_before_avemix_m.size()!=cell_count||
       live_mixht.dptt_before_avemix_k.size()!=cell_count||
       live_mixht.comp_third_temperature_k.size()!=cell_count||
       live_mixht.comp_third_qh_wm2.size()!=cell_count||
       live_mixht.comp_third_density_kgm3.size()!=cell_count||
       live_mixht.comp_third_ustar_mps.size()!=cell_count||
       live_mixht.comp_third_el_m.size()!=cell_count||
       !g65_equal_real4_bits(live_mixht.zi_before_avemix_m,
                             separate_mixht.zi_before_avemix_m)||
       !g65_equal_real4_bits(live_mixht.ziconv_before_avemix_m,
                             separate_mixht.ziconv_before_avemix_m)||
       !g65_equal_real4_bits(live_mixht.dptt_before_avemix_k,
                             separate_mixht.dptt_before_avemix_k)||
       !g65_equal_real4_bits(live_mixht.comp_third_temperature_k,
                             separate_mixht.comp_third_temperature_k)||
       !g65_equal_real4_bits(live_mixht.comp_third_qh_wm2,
                             separate_mixht.comp_third_qh_wm2)||
       !g65_equal_real4_bits(live_mixht.comp_third_density_kgm3,
                             separate_mixht.comp_third_density_kgm3)||
       !g65_equal_real4_bits(live_mixht.comp_third_ustar_mps,
                             separate_mixht.comp_third_ustar_mps)||
       !g65_equal_real4_bits(live_mixht.comp_third_el_m,
                             separate_mixht.comp_third_el_m))
        throw std::logic_error(
            "G65 secondhour real G26B MIXHT differs from detached"
            " causal source-native re-execution of 55760 REAL4 words");
    // S4-R1c9c: source-owned AVEMIX stage13 on the same scheduler
    // hour-two frame, strictly AFTER accepted G26B MIXHT. The separate
    // replay actor runs AVEMIX from its independently computed MIXHT.
    const auto live_avemix_result=hour2_comp.run(
        p6::kHefeiOriginalStageOrder[13],live_wind_frame);
    const auto detached_avemix_result=detached_comp.run(
        p6::kHefeiOriginalStageOrder[13],detached_frame);
    if(!live_avemix_result.completed||
       live_avemix_result.source!=p6::NativeHourSource::NativeCpp||
       !detached_avemix_result.completed||
       detached_avemix_result.source!=p6::NativeHourSource::NativeCpp)
        throw std::logic_error(
            "G65 real NOAA G14 hour-two native AVEMIX stage13 absent");
    const auto& live_avemix=
        hour2_comp.source_water_avemix_stage13(live_wind_frame);
    const auto& detached_avemix=
        detached_comp.source_water_avemix_stage13(detached_frame);
    // Third comparison: direct original-source AVEMIX from a wholly
    // independent G23/G24 wind reconstruction and separately replayed
    // G63 pre-AVEMIX MIXHT. No vendor or detached numeric value enters
    // the live actor; this is NOT an independent Fortran hour2 audit.
    const auto controls=g18c1_parse_original_avemix(
        source.original_metinp);
    const auto offset=
        static_cast<std::size_t>(controls.ilevzi-1)*cell_count;
    if(controls.ilevzi<1||
       offset+cell_count>separately_g24.wind.u_mps.size()||
       offset+cell_count>separately_g24.wind.v_mps.size())
        throw std::invalid_argument(
            "G65 NOAA hour2 original AVEMIX ILEVZI out of source G24");
    const std::vector<float> source_u(
        separately_g24.wind.u_mps.begin()+offset,
        separately_g24.wind.u_mps.begin()+offset+cell_count);
    const std::vector<float> source_v(
        separately_g24.wind.v_mps.begin()+offset,
        separately_g24.wind.v_mps.begin()+offset+cell_count);
    const auto source_avemix=g18c1_original_avemix_rebuild(
        live_wind_frame.grid.nx,live_wind_frame.grid.ny,
        controls.mnmdav,controls.hafang_deg,
        live_wind_frame.grid.grid_km*1000.f,
        source_u,source_v,separate_mixht.zi_before_avemix_m,
        separate_mixht.ziconv_before_avemix_m);
    if(live_avemix.zi_m.size()!=cell_count||
       live_avemix.ziconv_m.size()!=cell_count||
       !g65_equal_real4_bits(live_avemix.zi_m,detached_avemix.zi_m)||
       !g65_equal_real4_bits(live_avemix.ziconv_m,
                             detached_avemix.ziconv_m)||
       !g65_equal_real4_bits(live_avemix.zi_m,source_avemix.zi_m)||
       !g65_equal_real4_bits(live_avemix.ziconv_m,
                             source_avemix.ziconv_m))
        throw std::logic_error(
            "G65 real NOAA hour-two AVEMIX source 13940 REAL4 bit mismatch");
    // S4-R1c9d: authentic hour2 WSTARR stage14, after MIXHT stage12
    // and AVEMIX stage13 on one scheduler-owned G14 frame. A separate
    // G26B replay and direct original P6E WSTARR calculation are
    // read-only oracles; neither one feeds the live G26B actor.
    const auto wstarr_native_result=hour2_comp.run(
        p6::kHefeiOriginalStageOrder[14],live_wind_frame);
    const auto wstarr_replay_result=detached_comp.run(
        p6::kHefeiOriginalStageOrder[14],detached_frame);
    if(!wstarr_native_result.completed||
       wstarr_native_result.source!=p6::NativeHourSource::NativeCpp||
       !wstarr_replay_result.completed||
       wstarr_replay_result.source!=p6::NativeHourSource::NativeCpp)
        throw std::logic_error(
            "G65 NOAA actual hour2 native G26B WSTARR stage14 absent");
    const auto& live_wstarr=
        hour2_comp.source_water_wstarr_stage14(live_wind_frame);
    const auto& detached_wstarr=
        detached_comp.source_water_wstarr_stage14(detached_frame);
    p6e::WstarrInput original_wstarr;
    original_wstarr.nx=static_cast<std::size_t>(live_wind_frame.grid.nx);
    original_wstarr.ny=static_cast<std::size_t>(live_wind_frame.grid.ny);
    original_wstarr.water_first=live_wind_frame.grid.iwat1;
    original_wstarr.water_last=live_wind_frame.grid.iwat2;
    original_wstarr.landuse=live_wind_frame.grid.landuse;
    original_wstarr.zi_conv_m=source_avemix.ziconv_m;
    original_wstarr.heat_flux_wm2=separate_mixht.comp_third_qh_wm2;
    original_wstarr.temp_k=separate_mixht.comp_third_temperature_k;
    original_wstarr.rho_kgm3=separate_mixht.comp_third_density_kgm3;
    original_wstarr.initial_wstar_ms.assign(cell_count,0.f);
    const auto source_wstarr=p6e::wstarr(original_wstarr);
    if(live_wstarr.size()!=cell_count||
       detached_wstarr.size()!=cell_count||
       source_wstarr.size()!=cell_count||
       !g65_equal_real4_bits(live_wstarr,detached_wstarr)||
       !g65_equal_real4_bits(live_wstarr,source_wstarr))
        throw std::logic_error(
            "G65 NOAA true hour2 WSTARR mismatches 6970 original-source REAL4");
    for(std::size_t i=0;i<cell_count;++i) {
        const auto u=live_wstarr[i];
        if(!std::isfinite(u)||u<0.f||
           (live_wind_frame.grid.landuse[i]>=
               live_wind_frame.grid.iwat1&&
            live_wind_frame.grid.landuse[i]<=
               live_wind_frame.grid.iwat2&&u!=0.f))
            throw std::logic_error(
                "G65 real NOAA hour2 WATER WSTAR nonzero or invalid");
    }
    // S4-R1c9e: authentic hour-two COMP TEMP3D stage15 reuses native
    // P6E observed upper-air vertical temperature physics on the same
    // uncommitted G14 frame, after MIXHT/AVEMIX/WSTARR. Independently
    // rebuild its original-source AA/BB/FACET and surface inputs from
    // the detached NOAA hour-two G26A/G26B replay. No original Fortran
    // temperature or previous diagnostic output enters the live actor.
    const auto temp3d_native_result=hour2_comp.run(
        p6::kHefeiOriginalStageOrder[15],live_wind_frame);
    const auto temp3d_replay_result=detached_comp.run(
        p6::kHefeiOriginalStageOrder[15],detached_frame);
    if(!temp3d_native_result.completed||
       temp3d_native_result.source!=p6::NativeHourSource::NativeCpp||
       !temp3d_replay_result.completed||
       temp3d_replay_result.source!=p6::NativeHourSource::NativeCpp)
        throw std::logic_error(
            "G65 authentic hour2 G26B TEMP3D stage15 missing");
    const auto& live_temp3d=
        hour2_comp.source_water_temp3d_stage15(live_wind_frame);
    const auto& replay_temp3d=
        detached_comp.source_water_temp3d_stage15(detached_frame);
    const auto& source_upper=
        detached_diagno.selected_upper_for_comp(detached_frame);
    const auto source_faces=g18b5_selected_native_temperature_faces(
        detached_frame,source_upper);
    const auto temp_ctrl=g18c3_parse_original_temp3d_controls(
        source.original_metinp);
    if(!temp_ctrl.lcalgrd||temp_ctrl.itprog!=0||
       source_faces.end!=detached_frame.input.end||
       source_faces.station_ids.size()!=1||
       source_faces.face_height_m.size()!=10||
       source_faces.aa_face_k.size()!=10||
       source_faces.bb_face_k.size()!=10)
        throw std::logic_error(
            "G65 NOAA hour2 original-source upper FACET invalid");
    p6e::Temp3dObservedInput source_temp;
    source_temp.nx=static_cast<std::size_t>(detached_frame.grid.nx);
    source_temp.ny=static_cast<std::size_t>(detached_frame.grid.ny);
    source_temp.nz=9;
    source_temp.dgrid_m=detached_frame.grid.grid_km*1000.f;
    source_temp.irad=temp_ctrl.irad;
    using namespace std::chrono;
    const auto utc_h=duration_cast<hours>(
        detached_frame.input.end-floor<days>(detached_frame.input.end)).count();
    source_temp.current_hour_utc=static_cast<int>(utc_h%12);
    source_temp.face_z_m=source_faces.face_height_m;
    source_temp.justa=source_faces.justa;
    source_temp.past_seconds=source_faces.past_seconds;
    source_temp.to_go_seconds=source_faces.to_go_seconds;
    source_temp.aa_face_temp_k=source_faces.aa_face_k;
    source_temp.bb_face_temp_k=source_faces.bb_face_k;
    source_temp.surface_temp_k=separate_mixht.comp_third_temperature_k;
    source_temp.convective_zi_m=source_avemix.ziconv_m;
    for(const auto& station:detached_frame.stations.upper) {
        source_temp.station_x_m.push_back(station.local_x_m);
        source_temp.station_y_m.push_back(station.local_y_m);
    }
    const auto source_temp3d=p6e::temp3d_observed_land(source_temp);
    const auto temp_words=9U*cell_count;
    if(live_temp3d.size()!=temp_words||
       replay_temp3d.size()!=temp_words||
       source_temp3d.size()!=temp_words||
       !g65_equal_real4_bits(live_temp3d,replay_temp3d)||
       !g65_equal_real4_bits(live_temp3d,source_temp3d))
        throw std::logic_error(
            "G65 authentic hour2 TEMP3D 62730 source REAL4 bit mismatch");
    for(std::size_t i=0;i<cell_count;++i)
        if(live_temp3d[i]!=source_temp.surface_temp_k[i])
            throw std::logic_error(
                "G65 real NOAA hour2 TEMP3D k1 COMP surface T drift");
    for(const auto value:live_temp3d)
        if(!std::isfinite(value)||value<180.f||value>350.f)
            throw std::logic_error(
                "G65 authentic NOAA hour2 TEMP3D nonphysical");
    // Stage16: preserve a third source-native candidate BEFORE advancing
    // either actor. This is same-kernel causal replay, NOT an independent
    // original Fortran science comparator or permission to commit.
    const auto source_p6f=g64_real_noaa_p6f_from_live_g14(
        detached_frame,source,separate_mixht,detached_avemix,
        detached_wstarr,replay_temp3d,true);
    const auto live_p6f_result=hour2_comp.run(
        p6::kHefeiOriginalStageOrder[16],live_wind_frame);
    const auto detached_p6f_result=detached_comp.run(
        p6::kHefeiOriginalStageOrder[16],detached_frame);
    if(!live_p6f_result.completed||
       live_p6f_result.source!=p6::NativeHourSource::NativeCpp||
       !detached_p6f_result.completed||
       detached_p6f_result.source!=p6::NativeHourSource::NativeCpp)
        throw std::logic_error("G65 genuine NOAA hour2 P6F stage16 absent");
    const auto& live_p6f=hour2_comp.source_water_p6f_stage16(
        live_wind_frame);
    const auto& replay_p6f=detached_comp.source_water_p6f_stage16(
        detached_frame);
    const auto same_dataset=[&](const cteas::p6f::Calmet21File& lhs,
                                const cteas::p6f::Calmet21File& rhs) {
        if(lhs.hourly.size()!=45||rhs.hourly.size()!=45)
            return false;
        for(std::size_t k=0;k<45;++k) {
            const auto& a=lhs.hourly[k];
            const auto& b=rhs.hourly[k];
            if(a.label!=b.label||a.integer!=b.integer||
               cteas::p6f::instant_seconds(a.begin)!=
                   cteas::p6f::instant_seconds(b.begin)||
               cteas::p6f::instant_seconds(a.end)!=
                   cteas::p6f::instant_seconds(b.end))
                return false;
            if(a.integer) {
                if(a.integer_values.size()!=cell_count||
                   a.integer_values!=b.integer_values)
                    return false;
            } else if(a.real_values.size()!=cell_count||
                      !g65_equal_real4_bits(a.real_values,b.real_values))
                return false;
        }
        return true;
    };
    if(!live_p6f.actual_g14_stage16_precommit_validated||
       !replay_p6f.actual_g14_stage16_precommit_validated||
       !source_p6f.actual_g14_stage16_precommit_validated||
       live_p6f.g14_hour_committed||replay_p6f.g14_hour_committed||
       source_p6f.g14_hour_committed||
       live_p6f.source_clocks_published||
       replay_p6f.source_clocks_published||
       source_p6f.source_clocks_published||
       live_p6f.ready_for_next_hour||replay_p6f.ready_for_next_hour||
       source_p6f.ready_for_next_hour||
       live_p6f.end!=hour2.input.end||
       replay_p6f.end!=hour2.input.end||
       source_p6f.end!=hour2.input.end||
       live_p6f.serialized_prepared_only.empty()||
       live_p6f.serialized_prepared_only!=
           replay_p6f.serialized_prepared_only||
       live_p6f.serialized_prepared_only!=
           source_p6f.serialized_prepared_only||
       !same_dataset(live_p6f.candidate_dataset,
                     replay_p6f.candidate_dataset)||
       !same_dataset(live_p6f.candidate_dataset,
                     source_p6f.candidate_dataset)||
       !g65_equal_real4_bits(live_p6f.candidate_next.zi_m,
                             replay_p6f.candidate_next.zi_m)||
       !g65_equal_real4_bits(live_p6f.candidate_next.ziconv_m,
                             replay_p6f.candidate_next.ziconv_m)||
       !g65_equal_real4_bits(live_p6f.candidate_next.dptt_k,
                             replay_p6f.candidate_next.dptt_k)||
       !g65_equal_real4_bits(live_p6f.candidate_next.zi_m,
                             source_p6f.candidate_next.zi_m)||
       !g65_equal_real4_bits(live_p6f.candidate_next.ziconv_m,
                             source_p6f.candidate_next.ziconv_m)||
       !g65_equal_real4_bits(live_p6f.candidate_next.dptt_k,
                             source_p6f.candidate_next.dptt_k))
        throw std::logic_error(
            "G65 real NOAA hour2 45-field source P6F precommit mismatch");
    // The frame carries only an in-flight candidate, while scheduler
    // memory and public AA/BB/CGAMMA clocks remain at hour one.
    if(scheduler.completed_hours()!=1||
       clocks.latest_upper_hour()!=first_end||
       clocks.latest_gamma_hour()!=first_end||
       !g65_equal_real4_bits(scheduler.committed_memory().zi_m,committed.zi_m)||
       !g65_equal_real4_bits(scheduler.committed_memory().ziconv_m,committed.ziconv_m)||
       !g65_equal_real4_bits(scheduler.committed_memory().dptt_k,committed.dptt_k)||
       !g65_equal_real4_bits(live_wind_frame.next.zi_m,
                             live_p6f.candidate_next.zi_m)||
       !g65_equal_real4_bits(live_wind_frame.next.ziconv_m,
                             live_p6f.candidate_next.ziconv_m)||
       !g65_equal_real4_bits(live_wind_frame.next.dptt_k,
                             live_p6f.candidate_next.dptt_k))
        throw std::logic_error(
            "G65 second-hour P6F precommit changed committed memory/clocks");

    // S4-R1c9i: unlike detached manual stage calls above, exercise the
    // actual G14 scheduler's full second-hour execute_and_commit_hour path.
    // Force a P6F precommit failure only AFTER all 17 native stages,
    // candidate field checks and staged AA/BB/CGAMMA clock preflight.
    // This must roll back BOTH physical memory and public clock authority.
    // A successful negative test does not authorize committing hour2.
    const auto second_before=scheduler.committed_memory();
    bool second_injection_reached=false;
    bool second_postcommit_called=false;
    G65RealNoaaSecondHourActor* second_actor=nullptr;
    try {
        scheduler.advance_with_fresh_physics(
            [&](const MultiHourFrame& next)
                ->std::unique_ptr<MultiHourPhysics> {
                if(next.hour_index!=1||next.input.end!=hour2.input.end||
                   &next.previous!=&scheduler.committed_memory())
                    throw std::logic_error(
                        "G65 second-hour rollback detached G14 scheduler");
                auto actor=std::make_unique<
                    G65RealNoaaSecondHourActor>(
                        scheduler,clocks,source,actual);
                second_actor=actor.get();
                return actor;
            },
            [&](const MultiHourFrame& candidate_frame) {
                if(!second_actor||candidate_frame.hour_index!=1||
                   candidate_frame.input.end!=hour2.input.end)
                    throw std::logic_error(
                        "G65 second-hour rollback precommit clock drift");
                const auto& candidate=second_actor->precommit(
                    candidate_frame);
                if(candidate.serialized_prepared_only!=
                       live_p6f.serialized_prepared_only||
                   !g65_equal_real4_bits(
                       candidate_frame.next.zi_m,
                       live_p6f.candidate_next.zi_m)||
                   !g65_equal_real4_bits(
                       candidate_frame.next.ziconv_m,
                       live_p6f.candidate_next.ziconv_m)||
                   !g65_equal_real4_bits(
                       candidate_frame.next.dptt_k,
                       live_p6f.candidate_next.dptt_k))
                    throw std::logic_error(
                        "G65 second-hour transaction P6F differs from source");
                second_injection_reached=true;
                throw std::runtime_error(
                    "G65_EXPECTED_SECOND_HOUR_PRECOMMIT_ROLLBACK");
            },
            [&](MultiHourPhysics&,
                const UnifiedMultistationHourlyScheduler&) noexcept {
                second_postcommit_called=true;
            });
        throw std::logic_error(
            "G65 second-hour rollback injection unexpectedly committed");
    } catch(const std::runtime_error& e) {
        if(!second_injection_reached||
           std::string(e.what())!=
               "G65_EXPECTED_SECOND_HOUR_PRECOMMIT_ROLLBACK")
            throw;
    }
    if(second_postcommit_called||scheduler.completed_hours()!=1||
       clocks.latest_upper_hour()!=first_end||
       clocks.latest_gamma_hour()!=first_end||
       !g65_equal_real4_bits(
           scheduler.committed_memory().zi_m,second_before.zi_m)||
       !g65_equal_real4_bits(
           scheduler.committed_memory().ziconv_m,second_before.ziconv_m)||
       !g65_equal_real4_bits(
           scheduler.committed_memory().dptt_k,second_before.dptt_k))
        throw std::logic_error(
            "G65 second-hour failed precommit changed physical/clock state");

    // S4-R1c9j: opt-in POSITIVE transaction test only. The immediately
    // preceding forced failure proved rollback with unchanged hour-one
    // memory and clocks. This second attempt must allocate a NEW actor and
    // publish hour-two clocks only after G14 commits the physical memory.
    // Source-native 45-field equality is a precommit invariant; it is NOT
    // a substitute for the separate original Fortran 45-field science audit.
    bool second_positive_published=false;
    bool third_inherits_second=false;
    bool third_g26a_staged=false;
    bool third_thermal_refused=false;
    G66NoaaHour3G22Trace third_g22_forensic;
    G66NativeHour2WaterState third_native_prior;
    std::vector<std::uint8_t> third_live_g22_bytes;
    std::vector<std::uint8_t> third_windtail_bytes;
    std::vector<std::uint8_t> third_comp_stage12_bytes;
    std::vector<std::uint8_t> third_comp_stage15_bytes;
    std::vector<std::uint8_t> third_p6f45_bytes;
    p6::NativeGridMemory third_trial_next;
    bool third_g14_rollback=false;
    bool third_g14_positive=false;
    bool third_station_published=false;
    bool fourth_inherits_third=false;
    bool fourth_g26a_staged=false;
    bool fourth_g22_guarded=false;
    G66NativeHour2WaterState fourth_native_prior;
    std::vector<std::uint8_t> fourth_g22_bytes;
    bool fourth_live_g22=false;
    bool fourth_live_exact=false;
    p6::NativeGridMemory second_committed;
    if(opt_in_positive_hour2_transaction) {
        G65RealNoaaSecondHourActor* positive_actor=nullptr;
        bool positive_precommit_reached=false;
        scheduler.advance_with_fresh_physics(
            [&](const MultiHourFrame& next)
                ->std::unique_ptr<MultiHourPhysics> {
                if(next.hour_index!=1||next.input.end!=hour2.input.end||
                   &next.previous!=&scheduler.committed_memory()||
                   !g65_equal_real4_bits(next.previous.zi_m,second_before.zi_m)||
                   !g65_equal_real4_bits(next.previous.ziconv_m,
                                         second_before.ziconv_m)||
                   !g65_equal_real4_bits(next.previous.dptt_k,
                                         second_before.dptt_k))
                    throw std::logic_error(
                        "G65 positive hour-two factory prior memory/clock drift");
                auto actor=std::make_unique<G65RealNoaaSecondHourActor>(
                    scheduler,clocks,source,actual);
                positive_actor=actor.get();
                return actor;
            },
            [&](const MultiHourFrame& candidate_frame) {
                if(!positive_actor||candidate_frame.hour_index!=1||
                   candidate_frame.input.end!=hour2.input.end||
                   scheduler.completed_hours()!=1||
                   clocks.latest_upper_hour()!=first_end||
                   clocks.latest_gamma_hour()!=first_end)
                    throw std::logic_error(
                        "G65 positive hour-two precommit not isolated");
                const auto& candidate=positive_actor->precommit(candidate_frame);
                if(candidate.serialized_prepared_only!=
                       live_p6f.serialized_prepared_only||
                   !g65_equal_real4_bits(
                       candidate_frame.next.zi_m,
                       live_p6f.candidate_next.zi_m)||
                   !g65_equal_real4_bits(
                       candidate_frame.next.ziconv_m,
                       live_p6f.candidate_next.ziconv_m)||
                   !g65_equal_real4_bits(
                       candidate_frame.next.dptt_k,
                       live_p6f.candidate_next.dptt_k))
                    throw std::logic_error(
                        "G65 positive hour-two source-native P6F drift");
                positive_precommit_reached=true;
            },
            [&](MultiHourPhysics& physics,const MultiHourFrame& frame,
                const UnifiedMultistationHourlyScheduler& owner) {
                auto* actor=dynamic_cast<G65RealNoaaSecondHourActor*>(&physics);
                if(!positive_precommit_reached||!actor||
                   actor!=positive_actor||owner.completed_hours()!=1||
                   frame.hour_index!=1)
                    throw std::logic_error(
                        "G65 positive hour-two clock preflight order drift");
                actor->require_station_clock_preflight(frame);
            },
            [&](MultiHourPhysics& physics,
                const UnifiedMultistationHourlyScheduler& owner) noexcept {
                auto* actor=dynamic_cast<G65RealNoaaSecondHourActor*>(&physics);
                second_positive_published=(actor!=nullptr&&
                    actor==positive_actor&&
                    actor->publish_after_commit_noexcept()&&
                    owner.completed_hours()==2&&clocks.has_published_hour());
            });
        if(!positive_precommit_reached||!second_positive_published||
           scheduler.completed_hours()!=2||
           clocks.latest_upper_hour()!=hour2.input.end||
           clocks.latest_gamma_hour()!=hour2.input.end)
            throw std::logic_error(
                "G65 hour-two G14 commit and AA/BB/CGAMMA not synchronized");
        second_committed=scheduler.committed_memory();
        if(!g65_equal_real4_bits(second_committed.zi_m,
                                 live_p6f.candidate_next.zi_m)||
           !g65_equal_real4_bits(second_committed.ziconv_m,
                                 live_p6f.candidate_next.ziconv_m)||
           !g65_equal_real4_bits(second_committed.dptt_k,
                                 live_p6f.candidate_next.dptt_k))
            throw std::logic_error(
                "G65 positive hour-two committed hidden memory mismatch");
        const auto third=scheduler.preview_next_hour();
        third_inherits_second=(third.hour_index==2&&
            third.surface.start==hour2.input.end&&
            &third.previous==&scheduler.committed_memory()&&
            g65_equal_real4_bits(third.previous.zi_m,second_committed.zi_m)&&
            g65_equal_real4_bits(third.previous.ziconv_m,
                                 second_committed.ziconv_m)&&
            g65_equal_real4_bits(third.previous.dptt_k,
                                 second_committed.dptt_k));
        if(!third_inherits_second)
            throw std::logic_error(
                "G65 hour-three preview lost committed hour-two history");

        // S4-R1c9k: third-hour PREPDI/WIND1/FRADJ source stages0..2
        // on the scheduler's real committed hour-two history. G22 thermal
        // is still protected by hour_index>1 and MUST reject stage3.
        // This is a bounded source/clock admission test, not third-hour
        // physics or an authorization to bypass the G22/G63/G64 guards.
        if(opt_in_third_hour_diagno_preflight) {
            auto third_frame=scheduler.preview_next_hour();
            G26SourceFileBackedG14DiagnoBridge third_diagno(
                scheduler,clocks,source,true);
            for(std::size_t stage=0;stage<3;++stage) {
                const auto result=third_diagno.run(
                    p6::kHefeiOriginalStageOrder[stage],third_frame);
                if(!result.completed||
                   result.source!=p6::NativeHourSource::NativeCpp)
                    throw std::logic_error(
                        "G65 third-hour source PREPDI/WIND1/FRADJ missing");
            }
            if(third_diagno.selected_checkpoints()!=3||
               third_frame.input.end!=source.surface.hourly[2].end||
               scheduler.completed_hours()!=2||
               clocks.latest_upper_hour()!=hour2.input.end||
               clocks.latest_gamma_hour()!=hour2.input.end||
               !g65_equal_real4_bits(scheduler.committed_memory().zi_m,
                                     second_committed.zi_m)||
               !g65_equal_real4_bits(scheduler.committed_memory().ziconv_m,
                                     second_committed.ziconv_m)||
               !g65_equal_real4_bits(scheduler.committed_memory().dptt_k,
                                     second_committed.dptt_k)||
               !g65_equal_real4_bits(third_frame.next.zi_m,
                                     second_committed.zi_m)||
               !g65_equal_real4_bits(third_frame.next.ziconv_m,
                                     second_committed.ziconv_m)||
               !g65_equal_real4_bits(third_frame.next.dptt_k,
                                     second_committed.dptt_k))
                throw std::logic_error(
                    "G65 third-hour PREPDI/FRADJ mutated committed memory/clocks");
            third_g26a_staged=true;
            try {
                (void)third_diagno.run(
                    p6::kHefeiOriginalStageOrder[3],third_frame);
            }catch(const std::invalid_argument& e) {
                third_thermal_refused=(
                    std::string(e.what())==
                    "G22 unvalidated mixed-WATER hour/station/GEO source path");
            }
            if(!third_thermal_refused||scheduler.completed_hours()!=2||
               clocks.latest_upper_hour()!=hour2.input.end||
               clocks.latest_gamma_hour()!=hour2.input.end)
                throw std::logic_error(
                    "G65 third-hour unverified G22 thermal was not fail-closed");
            if(opt_in_hour3_g22_trace_only) {
                third_native_prior=g65_native_hour2_water_from_p6f(
                    live_p6f.candidate_dataset,hour2.input.end);
                // This standalone G66 tracer never invokes G26 stage3,
                // consumes only the NATIVE hour2 P6F result, and cannot
                // publish an hour3 stage, memory, clocks or MET output.
                const auto& native_wind1=
                    third_diagno.selected_source_wind1_after_stage(third_frame);
                const auto& native_fradj=
                    third_diagno.selected_source_fradj_after_stage(third_frame);
                third_g22_forensic=g66_native_hour3_g22_trace_only(
                    third_frame,source,native_wind1,native_fradj,
                    third_native_prior,true);
                if(third_g22_forensic.traced_stages!=5||
                   third_g22_forensic.water_history_values!=126||
                   third_g22_forensic.production_admitted||
                   scheduler.completed_hours()!=2||
                   clocks.latest_upper_hour()!=hour2.input.end||
                   clocks.latest_gamma_hour()!=hour2.input.end)
                    throw std::logic_error(
                        "G65 standalone third-hour trace modified G14 authority");
            }
            if(opt_in_hour3_live_g22_trial) {
                // Fresh *actual* G26A actor: the same scheduler-owned
                // third-hour frame, explicit native P6F prior-water
                // history, real G26A stages0..6. It cannot run COMP,
                // publish clocks, or admit the default G22 branch.
                auto live_third=scheduler.preview_next_hour();
                G26SourceFileBackedG14DiagnoBridge live_actor(
                    scheduler,clocks,source,true,
                    &third_native_prior,true,opt_in_hour3_windtail_trial);
                for(std::size_t stage=0;
                    stage<(opt_in_hour3_windtail_trial?12U:7U);++stage) {
                    const auto step=live_actor.run(
                        p6::kHefeiOriginalStageOrder[stage],live_third);
                    if(!step.completed||
                       step.source!=p6::NativeHourSource::NativeCpp)
                        throw std::logic_error(
                            "G65 real hour3 G26A G22 trial stage missing");
                }
                third_live_g22_bytes=
                    live_actor.selected_hour3_g22_trace_after_stage(live_third);
                if(live_actor.selected_checkpoints()!=
                       (opt_in_hour3_windtail_trial?12U:7U)||
                   third_live_g22_bytes!=third_g22_forensic.bytes||
                   scheduler.completed_hours()!=2||
                   clocks.latest_upper_hour()!=hour2.input.end||
                   clocks.latest_gamma_hour()!=hour2.input.end||
                   !g65_equal_real4_bits(
                       scheduler.committed_memory().zi_m,second_committed.zi_m)||
                   !g65_equal_real4_bits(
                       scheduler.committed_memory().ziconv_m,
                       second_committed.ziconv_m)||
                   !g65_equal_real4_bits(
                       scheduler.committed_memory().dptt_k,
                       second_committed.dptt_k))
                    throw std::logic_error(
                        "G65 real G26A stage3 differs from detached G66"
                        " or mutated prior G14 state/clocks");
                if(opt_in_hour3_windtail_trial) {
                    third_windtail_bytes=
                        live_actor.selected_hour3_windtail_trace_after_stage(
                            live_third);
                    if(third_windtail_bytes.empty()||
                       scheduler.completed_hours()!=2||
                       clocks.latest_upper_hour()!=hour2.input.end||
                       clocks.latest_gamma_hour()!=hour2.input.end)
                        throw std::logic_error(
                            "G65 third-hour G23/G24 trace modified G14 authority");
                    if(opt_in_hour3_comp_stage12_trial) {
                        // A separate, strictly test-only G26B actor consumes
                        // the SAME live third-hour G26A wind, committed
                        // hour-two memory and source-owned current COMP WATER.
                        // No stage13–16, third-hour G14 commit or clock publish.
                        G26BSourceFileBackedCompBridge comp(
                            live_actor,source,true,&actual,true,
                            opt_in_hour3_comp_stage15_trial,
                            opt_in_hour3_p6f_trial);
                        const auto step=comp.run(
                            p6::kHefeiOriginalStageOrder[12],live_third);
                        if(!step.completed||
                           step.source!=p6::NativeHourSource::NativeCpp)
                            throw std::logic_error(
                                "G65 hour3 native G26B stage12 not completed");
                        const auto& mixed=
                            comp.source_water_mixht_stage12(live_third);
                        constexpr std::size_t n=82U*85U;
                        const std::array<const std::vector<float>*,7> fields{
                            &mixed.zi_before_avemix_m,
                            &mixed.ziconv_before_avemix_m,
                            &mixed.comp_third_qh_wm2,
                            &mixed.comp_third_temperature_k,
                            &mixed.comp_third_density_kgm3,
                            &mixed.p6f_water_reconciled_ustar_mps,
                            &mixed.p6f_water_reconciled_el_m};
                        const auto put=[&](std::uint32_t value) {
                            for(unsigned k=0;k<4;++k)
                                third_comp_stage12_bytes.push_back(
                                    static_cast<std::uint8_t>(value>>(8*k)));
                        };
                        for(int value:{4,12,82,85,9})
                            put(static_cast<std::uint32_t>(value));
                        for(const auto* field:fields) {
                            if(!field||field->size()!=n)
                                throw std::logic_error(
                                    "G65 hour3 COMP stage12 array shape invalid");
                            for(float value:*field) {
                                if(!std::isfinite(value))
                                    throw std::logic_error(
                                        "G65 hour3 COMP stage12 nonfinite");
                                put(std::bit_cast<std::uint32_t>(value));
                            }
                        }
                        if(opt_in_hour3_comp_stage15_trial) {
                            // Unpublished COMP stages13–15, same G26B
                            // actor and same G14 frame. Stage16 P6F
                            // remains rejected by the trial guard.
                            third_comp_stage15_bytes=third_comp_stage12_bytes;
                            const auto put15=[&](std::uint32_t value) {
                                for(unsigned k=0;k<4;++k)
                                    third_comp_stage15_bytes.push_back(
                                        static_cast<std::uint8_t>(value>>(8*k)));
                            };
                            const auto emit_stage=[&](
                                int stage,
                                const std::vector<const std::vector<float>*>& arrays) {
                                for(int value:{4,stage,82,85,9})
                                    put15(static_cast<std::uint32_t>(value));
                                for(const auto* field:arrays) {
                                    if(!field||field->size()!=(stage==15?9*n:n))
                                        throw std::logic_error(
                                            "G65 hour3 COMP stage array shape invalid");
                                    for(float value:*field) {
                                        if(!std::isfinite(value))
                                            throw std::logic_error(
                                                "G65 hour3 COMP stage nonfinite");
                                        put15(std::bit_cast<std::uint32_t>(value));
                                    }
                                }
                            };
                            for(int stage=13;stage<=15;++stage) {
                                const auto step=comp.run(
                                    p6::kHefeiOriginalStageOrder[stage],live_third);
                                if(!step.completed||
                                   step.source!=p6::NativeHourSource::NativeCpp)
                                    throw std::logic_error(
                                        "G65 hour3 COMP stage13-15 incomplete");
                                if(stage==13) {
                                    const auto& averaged=
                                        comp.source_water_avemix_stage13(live_third);
                                    emit_stage(13,{&averaged.zi_m,
                                                   &averaged.ziconv_m});
                                } else if(stage==14) {
                                    const auto& velocity=
                                        comp.source_water_wstarr_stage14(live_third);
                                    emit_stage(14,{&velocity});
                                } else {
                                    const auto& temp=
                                        comp.source_water_temp3d_stage15(live_third);
                                    emit_stage(15,{&temp});
                                }
                            }
                            if(third_comp_stage15_bytes.size()!=
                               4U*20U+(7U+2U+1U+9U)*n*4U)
                                throw std::logic_error(
                                    "G65 hour3 COMP stage12-15 trace incomplete");
                            if(opt_in_hour3_p6f_trial) {
                                const auto step=comp.run(
                                    p6::kHefeiOriginalStageOrder[16],live_third);
                                if(!step.completed||
                                   step.source!=p6::NativeHourSource::NativeCpp)
                                    throw std::logic_error(
                                        "G65 hour3 G64 P6F stage16 incomplete");
                                const auto& prepared=
                                    comp.source_water_p6f_stage16(live_third);
                                if(!prepared.actual_g14_stage16_precommit_validated||
                                   prepared.g14_hour_committed||
                                   prepared.source_clocks_published||
                                   prepared.ready_for_next_hour||
                                   prepared.candidate_dataset.hourly.size()!=45||
                                   prepared.serialized_prepared_only.empty())
                                    throw std::logic_error(
                                        "G65 hour3 P6F was incorrectly published");
                                third_p6f45_bytes=prepared.serialized_prepared_only;
                                third_trial_next=prepared.candidate_next;
                            }
                        }
                        if(third_comp_stage12_bytes.size()!=20U+7U*n*4U||
                           scheduler.completed_hours()!=2||
                           clocks.latest_upper_hour()!=hour2.input.end||
                           clocks.latest_gamma_hour()!=hour2.input.end||
                           !g65_equal_real4_bits(
                               scheduler.committed_memory().zi_m,
                               second_committed.zi_m)||
                           !g65_equal_real4_bits(
                               scheduler.committed_memory().ziconv_m,
                               second_committed.ziconv_m)||
                           !g65_equal_real4_bits(
                               scheduler.committed_memory().dptt_k,
                               second_committed.dptt_k))
                            throw std::logic_error(
                                "G65 hour3 stage12 mutated committed G14 authority");
                    }
                }
            }
        }
    }


    // S4-R1c9v: separately opted-in third-hour, real-source G14 retry
    // against the preceding unpublished P6F candidate. No source Fortran
    // MET is an input. This remains research-only, not production admission.
    if(opt_in_hour3_g14_transaction) {
        if(third_p6f45_bytes.empty()||
           third_trial_next.zi_m.size()!=6970||
           third_native_prior.ustar_mps.size()!=6970||
           scheduler.completed_hours()!=2)
            throw std::logic_error(
                "G65 third-hour G14 cannot use incomplete native P6F");
        const auto before=scheduler.committed_memory();
        const auto second_end=source.surface.hourly[1].end;
        const auto third_end=source.surface.hourly[2].end;
        auto assert_candidate=[&](
            const G65RealNoaaThirdHourTrialActor& actor,
            const MultiHourFrame& frame) {
            if(frame.hour_index!=2||frame.input.end!=third_end||
               frame.surface.start!=second_end||
               &frame.previous!=&scheduler.committed_memory()||
               scheduler.completed_hours()!=2||
               clocks.latest_upper_hour()!=second_end||
               clocks.latest_gamma_hour()!=second_end)
                throw std::logic_error(
                    "G65 hour3 transaction detached from genuine hour2 clocks");
            const auto& prepared=actor.precommit(frame);
            if(prepared.serialized_prepared_only!=third_p6f45_bytes||
               !g65_equal_real4_bits(frame.next.zi_m,
                                     third_trial_next.zi_m)||
               !g65_equal_real4_bits(frame.next.ziconv_m,
                                     third_trial_next.ziconv_m)||
               !g65_equal_real4_bits(frame.next.dptt_k,
                                     third_trial_next.dptt_k))
                throw std::logic_error(
                    "G65 hour3 committed candidate differs from unpublished G64");
            if(opt_in_hour4_g22_trace_only)
                fourth_native_prior=g65_native_hour2_water_from_p6f(
                    prepared.candidate_dataset,third_end);
        };
        G65RealNoaaThirdHourTrialActor* failed_actor=nullptr;
        bool failed_gate_reached=false;
        bool failed_published=false;
        try {
            scheduler.advance_with_fresh_physics(
                [&](const MultiHourFrame& next)
                    ->std::unique_ptr<MultiHourPhysics> {
                    if(next.hour_index!=2||
                       !g65_equal_real4_bits(next.previous.zi_m,
                                             before.zi_m)||
                       !g65_equal_real4_bits(next.previous.ziconv_m,
                                             before.ziconv_m)||
                       !g65_equal_real4_bits(next.previous.dptt_k,
                                             before.dptt_k))
                        throw std::logic_error(
                            "G65 hour3 rollback factory missing hour2 state");
                    auto actor=std::make_unique<
                        G65RealNoaaThirdHourTrialActor>(
                            scheduler,clocks,source,actual,third_native_prior);
                    failed_actor=actor.get();
                    return actor;
                },
                [&](const MultiHourFrame& candidate_frame) {
                    if(!failed_actor)throw std::logic_error(
                        "G65 missing fresh hour3 rollback actor");
                    assert_candidate(*failed_actor,candidate_frame);
                    failed_gate_reached=true;
                    throw std::runtime_error(
                        "G65_EXPECTED_HOUR3_P6F_ROLLBACK");
                },
                [&](MultiHourPhysics&,const MultiHourFrame&,
                    const UnifiedMultistationHourlyScheduler&) {
                    throw std::logic_error(
                        "G65 hour3 rollback must not reach clock preflight");
                },
                [&](MultiHourPhysics&,
                    const UnifiedMultistationHourlyScheduler&) noexcept {
                    failed_published=true;
                });
            throw std::logic_error(
                "G65 third-hour rollback unexpectedly committed");
        }catch(const std::runtime_error& e) {
            if(!failed_gate_reached||
               std::string(e.what())!="G65_EXPECTED_HOUR3_P6F_ROLLBACK")
                throw;
        }
        if(failed_published||scheduler.completed_hours()!=2||
           clocks.latest_upper_hour()!=second_end||
           clocks.latest_gamma_hour()!=second_end||
           !g65_equal_real4_bits(scheduler.committed_memory().zi_m,
                                 before.zi_m)||
           !g65_equal_real4_bits(scheduler.committed_memory().ziconv_m,
                                 before.ziconv_m)||
           !g65_equal_real4_bits(scheduler.committed_memory().dptt_k,
                                 before.dptt_k))
            throw std::logic_error(
                "G65 hour3 P6F rollback published memory or clocks");
        third_g14_rollback=true;

        G65RealNoaaThirdHourTrialActor* actor=nullptr;
        bool validated=false, clock_preflight=false;
        scheduler.advance_with_fresh_physics(
            [&](const MultiHourFrame& next)
                ->std::unique_ptr<MultiHourPhysics> {
                if(next.hour_index!=2||next.input.end!=third_end||
                   &next.previous!=&scheduler.committed_memory())
                    throw std::logic_error(
                        "G65 hour3 retry did not use live G14 frame");
                auto fresh=std::make_unique<
                    G65RealNoaaThirdHourTrialActor>(
                        scheduler,clocks,source,actual,third_native_prior);
                actor=fresh.get();
                return fresh;
            },
            [&](const MultiHourFrame& candidate_frame) {
                if(!actor)throw std::logic_error(
                    "G65 hour3 retry actor absent before P6F");
                assert_candidate(*actor,candidate_frame);
                validated=true;
            },
            [&](MultiHourPhysics& physics,
                const MultiHourFrame& candidate_frame,
                const UnifiedMultistationHourlyScheduler& owner) {
                auto* current=dynamic_cast<
                    G65RealNoaaThirdHourTrialActor*>(&physics);
                if(!validated||current!=actor||
                   owner.completed_hours()!=2)
                    throw std::logic_error(
                        "G65 third-hour G14 station preflight order wrong");
                actor->require_station_clock_preflight(candidate_frame);
                clock_preflight=true;
            },
            [&](MultiHourPhysics& physics,
                const UnifiedMultistationHourlyScheduler& owner) noexcept {
                auto* current=dynamic_cast<
                    G65RealNoaaThirdHourTrialActor*>(&physics);
                third_station_published=(validated&&clock_preflight&&
                    current!=nullptr&&current==actor&&
                    current->publish_after_commit_noexcept()&&
                    owner.completed_hours()==3&&clocks.has_published_hour());
            });
        if(!third_station_published||scheduler.completed_hours()!=3||
           clocks.latest_upper_hour()!=third_end||
           clocks.latest_gamma_hour()!=third_end||
           !g65_equal_real4_bits(scheduler.committed_memory().zi_m,
                                 third_trial_next.zi_m)||
           !g65_equal_real4_bits(scheduler.committed_memory().ziconv_m,
                                 third_trial_next.ziconv_m)||
           !g65_equal_real4_bits(scheduler.committed_memory().dptt_k,
                                 third_trial_next.dptt_k))
            throw std::logic_error(
                "G65 positive hour3 G14 memory/clock commit mismatch");
        third_g14_positive=true;
        const auto fourth=scheduler.preview_next_hour();
        fourth_inherits_third=(
            fourth.hour_index==3&&fourth.surface.start==third_end&&
            &fourth.previous==&scheduler.committed_memory()&&
            g65_equal_real4_bits(fourth.previous.zi_m,
                                 third_trial_next.zi_m)&&
            g65_equal_real4_bits(fourth.previous.ziconv_m,
                                 third_trial_next.ziconv_m)&&
            g65_equal_real4_bits(fourth.previous.dptt_k,
                                 third_trial_next.dptt_k));
        if(!fourth_inherits_third)
            throw std::logic_error(
                "G65 fourth-hour preview lost native committed hour3 history");
        if(opt_in_hour4_g26a_preflight) {
            // Genuine NOAA fourth-hour PREPDI/WIND1/FRADJ inputs from the
            // same G14 scheduler after hour3 commit. Fail closed at G22.
            // No hour4 native physics acceptance or external data output.
            auto frame=scheduler.preview_next_hour();
            G26SourceFileBackedG14DiagnoBridge fourth_actor(
                scheduler,clocks,source,true);
            for(std::size_t stage=0;stage<3;++stage) {
                const auto result=fourth_actor.run(
                    p6::kHefeiOriginalStageOrder[stage],frame);
                if(!result.completed||
                   result.source!=p6::NativeHourSource::NativeCpp)
                    throw std::logic_error(
                        "G65 hour4 PREPDI/WIND1/FRADJ stage incomplete");
            }
            if(fourth_actor.selected_checkpoints()!=3||
               frame.hour_index!=3||
               frame.input.end!=source.surface.hourly[3].end||
               clocks.latest_upper_hour()!=third_end||
               clocks.latest_gamma_hour()!=third_end||
               scheduler.completed_hours()!=3||
               !g65_equal_real4_bits(frame.previous.zi_m,
                                     third_trial_next.zi_m)||
               !g65_equal_real4_bits(frame.previous.ziconv_m,
                                     third_trial_next.ziconv_m)||
               !g65_equal_real4_bits(frame.previous.dptt_k,
                                     third_trial_next.dptt_k)||
               !g65_equal_real4_bits(frame.next.zi_m,
                                     third_trial_next.zi_m)||
               !g65_equal_real4_bits(frame.next.ziconv_m,
                                     third_trial_next.ziconv_m)||
               !g65_equal_real4_bits(frame.next.dptt_k,
                                     third_trial_next.dptt_k))
                throw std::logic_error(
                    "G65 hour4 G26A preflight changed hour3 committed state");
            fourth_g26a_staged=true;
            if(opt_in_hour4_g22_trace_only) {
                if(!fourth_native_prior.explicitly_native_p6f_origin||
                   fourth_native_prior.end!=third_end||
                   fourth_native_prior.begin!=second_end)
                    throw std::logic_error(
                        "G65 hour4 WATER history not sourced from committed G64");
                const auto forensic=g66_native_hour4_g22_trace_only(
                    frame,source,
                    fourth_actor.selected_source_wind1_after_stage(frame),
                    fourth_actor.selected_source_fradj_after_stage(frame),
                    fourth_native_prior,true);
                if(forensic.production_admitted||
                   forensic.water_history_values!=126||
                   forensic.traced_stages!=5||forensic.bytes.empty()||
                   scheduler.completed_hours()!=3)
                    throw std::logic_error(
                        "G65 hour4 G22 trace lacked native history or published state");
                fourth_g22_bytes=forensic.bytes;
            }
            try {
                (void)fourth_actor.run(
                    p6::kHefeiOriginalStageOrder[3],frame);
            }catch(const std::invalid_argument& e) {
                fourth_g22_guarded=(
                    std::string(e.what())==
                    "G22 unvalidated mixed-WATER hour/station/GEO source path");
            }
            if(!fourth_g22_guarded||scheduler.completed_hours()!=3||
               clocks.latest_upper_hour()!=third_end||
               clocks.latest_gamma_hour()!=third_end||
               !g65_equal_real4_bits(scheduler.committed_memory().zi_m,
                                     third_trial_next.zi_m)||
               !g65_equal_real4_bits(scheduler.committed_memory().ziconv_m,
                                     third_trial_next.ziconv_m)||
               !g65_equal_real4_bits(scheduler.committed_memory().dptt_k,
                                     third_trial_next.dptt_k))
                throw std::logic_error(
                    "G65 hour4 production G22 guard or history violated");
            if(opt_in_hour4_g22_trace_only) {
                // Explicitly opt-in the REAL G26A stage3–6 actor only after
                // the default production path rejected hour4 stage3.
                // The independent detached G66 path is retained as a strict
                // byte-for-byte cross-check and never supplies model values.
                auto live=scheduler.preview_next_hour();
                G26SourceFileBackedG14DiagnoBridge live_actor(
                    scheduler,clocks,source,true,&fourth_native_prior,
                    false,false,true);
                for(std::size_t stage=0;stage<7;++stage) {
                    const auto result=live_actor.run(
                        p6::kHefeiOriginalStageOrder[stage],live);
                    if(!result.completed||
                       result.source!=p6::NativeHourSource::NativeCpp)
                        throw std::logic_error(
                            "G65 native hour4 live G26A stage0-6 missing");
                }
                fourth_live_exact=(
                    live_actor.selected_hour4_g22_trace_after_stage(live)==
                    fourth_g22_bytes);
                fourth_live_g22=live_actor.selected_checkpoints()==7&&
                    scheduler.completed_hours()==3&&
                    clocks.latest_upper_hour()==third_end&&
                    clocks.latest_gamma_hour()==third_end&&
                    g65_equal_real4_bits(scheduler.committed_memory().zi_m,
                                         third_trial_next.zi_m)&&
                    g65_equal_real4_bits(
                        scheduler.committed_memory().ziconv_m,
                        third_trial_next.ziconv_m)&&
                    g65_equal_real4_bits(scheduler.committed_memory().dptt_k,
                                         third_trial_next.dptt_k);
                if(!fourth_live_exact||!fourth_live_g22)
                    throw std::logic_error(
                        "G65 hour4 live G26A differed from G66 or advanced G14");
            }
        }
    }

    G65NoaaFirstHourCommitReceipt receipt;
    receipt.end=first_end;
    receipt.committed_memory=second_before;
    receipt.committed_hours=scheduler.completed_hours();
    receipt.hour2_positive_g14_commit_verified=second_positive_published;
    receipt.hour2_positive_station_clocks_published=second_positive_published;
    receipt.hour3_preview_inherits_hour2_memory=third_inherits_second;
    receipt.hour3_real_g26a_stage02_preflight_only=third_g26a_staged;
    receipt.hour3_g22_thermal_guard_remains_rejected=third_thermal_refused;
    receipt.hour3_test_only_native_g22_trace_ready=
        opt_in_hour3_g22_trace_only&&third_g22_forensic.traced_stages==5;
    if(receipt.hour3_test_only_native_g22_trace_ready)
        receipt.hour3_test_only_native_g22_trace_bytes=
            std::move(third_g22_forensic.bytes);
    receipt.hour3_live_g26a_stage3_trial_only=
        opt_in_hour3_live_g22_trial&&!third_live_g22_bytes.empty();
    if(receipt.hour3_live_g26a_stage3_trial_only)
        receipt.hour3_live_g26a_stage3_trace_bytes=
            std::move(third_live_g22_bytes);
    receipt.hour3_native_g23_g24_stage11_trial_only=
        opt_in_hour3_windtail_trial&&!third_windtail_bytes.empty();
    if(receipt.hour3_native_g23_g24_stage11_trial_only)
        receipt.hour3_native_g23_g24_trace_bytes=
            std::move(third_windtail_bytes);
    receipt.hour3_native_g26b_stage12_trial_only=
        opt_in_hour3_comp_stage12_trial&&!third_comp_stage12_bytes.empty();
    if(receipt.hour3_native_g26b_stage12_trial_only)
        receipt.hour3_native_g26b_stage12_trace_bytes=
            std::move(third_comp_stage12_bytes);
    receipt.hour3_native_g26b_stage15_trial_only=
        opt_in_hour3_comp_stage15_trial&&!third_comp_stage15_bytes.empty();
    if(receipt.hour3_native_g26b_stage15_trial_only)
        receipt.hour3_native_g26b_stage15_trace_bytes=
            std::move(third_comp_stage15_bytes);
    receipt.hour3_g14_rollback_verified=third_g14_rollback;
    receipt.hour3_g14_positive_commit_verified=third_g14_positive;
    receipt.hour3_station_clocks_published=third_station_published;
    receipt.hour4_preview_inherits_hour3_memory=fourth_inherits_third;
    receipt.hour4_g26a_stage0_2_source_preflight_only=fourth_g26a_staged;
    receipt.hour4_g22_production_guard_rejected=fourth_g22_guarded;
    receipt.hour4_live_g26a_stage3_6_uncommitted=fourth_live_g22;
    receipt.hour4_live_g22_matches_detached=fourth_live_exact;
    receipt.hour4_g22_forensic_trace_only=
        opt_in_hour4_g22_trace_only&&!fourth_g22_bytes.empty();
    if(receipt.hour4_g22_forensic_trace_only)
        receipt.hour4_g22_forensic_trace_bytes=
            std::move(fourth_g22_bytes);
    receipt.hour3_native_g26b_p6f45_trial_only=
        opt_in_hour3_p6f_trial&&!third_p6f45_bytes.empty();
    if(receipt.hour3_native_g26b_p6f45_trial_only)
        receipt.hour3_native_g26b_p6f45_bytes=
            std::move(third_p6f45_bytes);
    if(second_positive_published)
        receipt.hour2_committed_memory=std::move(second_committed);
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
    receipt.hour2_live_g26_fradj_compared_words=3U*82U*85U+
        2U*9U*82U*85U;
    receipt.hour2_live_g26_stage02_uncommitted=true;
    receipt.hour2_live_g26_thermal_compared_words=5U*82U*85U+
        2U*9U*82U*85U;
    receipt.hour2_live_g26_stage06_uncommitted=true;
    receipt.hour2_live_g26_g24_compared_words=
        4U*9U*82U*85U+10U*82U*85U;
    receipt.hour2_live_g26_stage11_uncommitted=true;
    receipt.hour2_live_g26_mixht_compared_words=8U*82U*85U;
    receipt.hour2_live_g26_stage12_uncommitted=true;
    receipt.hour2_live_g26_avemix_compared_words=2U*82U*85U;
    receipt.hour2_live_g26_stage13_uncommitted=true;
    receipt.hour2_live_g26_wstarr_compared_words=82U*85U;
    receipt.hour2_live_g26_stage14_uncommitted=true;
    receipt.hour2_live_g26_temp3d_compared_words=9U*82U*85U;
    receipt.hour2_live_g26_stage15_uncommitted=true;
    receipt.hour2_stage16_prepared_unpublished=true;
    receipt.hour2_real_g14_full17_rollback_verified=true;
    receipt.hour2_p6f_compared_words=45U*82U*85U;
    receipt.hour2_unpublished_p6f_bytes=live_p6f.serialized_prepared_only;
    receipt.hour2_unpublished_mixht_avemix_rows.reserve(4U*82U*85U);
    for(std::size_t i=0;i<82U*85U;++i) {
        receipt.hour2_unpublished_mixht_avemix_rows.push_back(
            live_mixht.zi_before_avemix_m[i]);
        receipt.hour2_unpublished_mixht_avemix_rows.push_back(
            live_mixht.ziconv_before_avemix_m[i]);
        receipt.hour2_unpublished_mixht_avemix_rows.push_back(
            live_avemix.zi_m[i]);
        receipt.hour2_unpublished_mixht_avemix_rows.push_back(
            live_avemix.ziconv_m[i]);
    }
    receipt.hour2_unpublished_wstarr_input_rows.reserve(5U*82U*85U);
    for(std::size_t i=0;i<82U*85U;++i) {
        receipt.hour2_unpublished_wstarr_input_rows.push_back(
            live_avemix.ziconv_m[i]);
        receipt.hour2_unpublished_wstarr_input_rows.push_back(
            live_mixht.comp_third_qh_wm2[i]);
        receipt.hour2_unpublished_wstarr_input_rows.push_back(
            live_mixht.comp_third_temperature_k[i]);
        receipt.hour2_unpublished_wstarr_input_rows.push_back(
            live_mixht.comp_third_density_kgm3[i]);
        receipt.hour2_unpublished_wstarr_input_rows.push_back(
            live_wstarr[i]);
    }
    return receipt;
}
} // namespace cteas::calmet::p6g
