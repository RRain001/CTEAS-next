#pragma once
// G18E4: PREPDI AA/BB upper-air and per-US CGAMMA candidate at original
// frozen #53 G14 stage index 0, on G14's actual live hour frame.
// Delegates to G18D2 transactional station clocks; no copied physics,
// independent hour scheduler, premature clock commit, or production claim.
#include "cteas/p6/p6g_g18d2_station_clock_transaction.hpp"
#include <chrono>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>

namespace cteas::calmet::p6g {
class G18E4SelectedPrepdiStageAdapter final : public MultiHourPhysics {
public:
    G18E4SelectedPrepdiStageAdapter(
        const UnifiedMultistationHourlyScheduler& scheduler,
        G18D2StationClockAuthority& clocks,std::string source_metinp)
        : scheduler_(scheduler),clocks_(clocks),
          metinp_(std::move(source_metinp)) {}

    // Selected multi-station data is not yet a source-accepted full
    // PREPDI/G14 physics stage. No NativeCpp promotion via production run.
    p6::NativeHourStageResult run(
        p6::NativeHourStage,MultiHourFrame&) override {
        return {p6::NativeHourSource::Unknown,false};
    }

    void run_selected(p6::NativeHourStage stage,MultiHourFrame& frame,
                      bool explicitly_test_only) {
        static_assert(p6::kHefeiOriginalStageOrder[0] ==
                      p6::NativeHourStage::PrepdiPreviousZiconv);
        if(!explicitly_test_only||staged_||published_||
           stage!=p6::kHefeiOriginalStageOrder[0]||
           !frame.source_controls||!scheduler_.has_original_controls()||
           frame.hour_index!=scheduler_.completed_hours())
            throw std::invalid_argument(
                "G18E4 PREPDI must execute once at original G14 stage zero");
        const auto preview=scheduler_.preview_next_hour();
        // G14 owns previous committed COMMON state, not a caller-created
        // duplicate with the same UTC label or independently reset ZICONV.
        if(&frame.previous!=&preview.previous||
           &frame.grid!=&preview.grid||
           &frame.stations!=&preview.stations||
           &frame.surface!=&preview.surface||
           &frame.input!=&preview.input||
           &frame.upper!=&preview.upper||
           frame.source_controls!=preview.source_controls||
           frame.input.end!=preview.input.end||
           frame.next.zi_m!=frame.previous.zi_m||
           frame.next.ziconv_m!=frame.previous.ziconv_m||
           frame.next.dptt_k!=frame.previous.dptt_k||
           !frame.fields.u_mps.empty()||!frame.fields.v_mps.empty()||
           !frame.fields.w_face_mps.empty())
            throw std::invalid_argument(
                "G18E4 PREPDI does not own a clean live G14 next-hour frame");
        // This prepares source-bracket AA/BB/CGAMMA and preflights BOTH
        // station clocks on detached copies. It does not publish them.
        auto candidate=clocks_.prepare_selected(scheduler_,metinp_,true);
        if(candidate.owner!=&scheduler_||
           candidate.hour_index!=frame.hour_index||
           candidate.source_end!=frame.input.end||
           candidate.observed.station_ids.size()!=frame.stations.upper.size()||
           candidate.cgamma.station_ids!=candidate.observed.station_ids||
           candidate.cgamma.hour_index!=frame.hour_index)
            throw std::runtime_error(
                "G18E4 PREPDI source AA/BB/CGAMMA hour mismatch");
        prepared_.emplace(std::move(candidate));
        live_frame_=&frame;
        prior_ = frame.previous;
        source_end_=frame.input.end;
        hour_index_=frame.hour_index;
        staged_=true;
    }

    [[nodiscard]] const G18BUpperHour& selected_upper_for(
        const MultiHourFrame& frame) const {
        verify_live(frame);
        return prepared_->observed;
    }
    [[nodiscard]] const G18B4CGammaPrepared& selected_gamma_for(
        const MultiHourFrame& frame) const {
        verify_live(frame);
        return prepared_->cgamma;
    }

    // G18F2: explicit precommit admission barrier. The PREPDI source
    // clock candidates must already be prepared by the live G14 stage
    // zero and independently committed on detached clock copies.
    // Reject any foreign/stale candidate BEFORE G14 accepts P6F and
    // changes its previous-hour memory. No clock is mutated here.
    void require_publishable_before_g14_commit(
        const MultiHourFrame& live) const {
        verify_live(live);
        if(scheduler_.completed_hours()!=live.hour_index||
           !clocks_.can_publish_after_next_g14_commit(
               scheduler_,*prepared_))
            throw std::logic_error(
                "G18F2 source PREPDI station clocks not preflighted for G14 commit");
    }

    // Only the accepted G14 scheduler counter may publish both clocks.
    // No PREPDI state is committed during stages 0-16 or P6F precommit.
    // This is the strict throwing API retained for validation callers.
    void publish_after_completed_g14_hour() {
        if(!staged_||published_||!prepared_)
            throw std::logic_error("G18E4 cannot publish incomplete PREPDI");
        clocks_.publish_only_after_completed_g14(scheduler_,*prepared_);
        published_=true;
    }

    // G18F1: safe postcommit observer for owned G14 executors. Exactly
    // the source-preflighted AA/BB and per-US CGAMMA clocks are published
    // as one noexcept operation. Returns false (without partial mutation)
    // if called before G14 commits, twice, or with a stale source hour.
    [[nodiscard]] bool try_publish_after_completed_g14_hour_noexcept() noexcept {
        if(!staged_||published_||!prepared_)
            return false;
        if(!clocks_.try_publish_only_after_completed_g14_noexcept(
               scheduler_,*prepared_))
            return false;
        published_=true;
        return true;
    }
    [[nodiscard]] bool staged() const noexcept {return staged_;}
    [[nodiscard]] bool published() const noexcept {return published_;}
private:
    void verify_live(const MultiHourFrame& frame) const {
        if(!staged_||!prepared_||published_||&frame!=live_frame_||
           frame.hour_index!=hour_index_||frame.input.end!=source_end_||
           frame.previous.zi_m!=prior_.zi_m||
           frame.previous.ziconv_m!=prior_.ziconv_m||
           frame.previous.dptt_k!=prior_.dptt_k)
            throw std::logic_error(
                "G18E4 PREPDI candidate cannot cross G14 hour or state");
    }
    const UnifiedMultistationHourlyScheduler& scheduler_;
    G18D2StationClockAuthority& clocks_;
    std::string metinp_;
    std::optional<G18D2StagedStationClocks> prepared_;
    const MultiHourFrame* live_frame_=nullptr;
    p6::NativeGridMemory prior_;
    std::chrono::sys_seconds source_end_{};
    std::size_t hour_index_=0;
    bool staged_=false,published_=false;
};
} // namespace cteas::calmet::p6g
