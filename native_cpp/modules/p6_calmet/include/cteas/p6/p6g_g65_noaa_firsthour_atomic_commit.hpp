#pragma once
// S4-R1c8w: one authentic NOAA first-hour G14 atomic transaction.
// Selected WATER route; hour2 stages 0..16 are research-only and
// uncommitted. Hour2 P6F is a candidate only: no original-hour
// Fortran science, state/clock publication, or P6 production.
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
    std::size_t hour2_p6f_compared_words=0;
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
    receipt.hour2_p6f_compared_words=45U*82U*85U;
    return receipt;
}
} // namespace cteas::calmet::p6g
