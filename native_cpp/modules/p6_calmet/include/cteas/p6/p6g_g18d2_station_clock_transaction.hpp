#pragma once
// G18D2: transactional original upper PREPDI AA/BB and per-US CGAMMA
// clocks for the SAME existing G14 scheduler. Prepare on the G14 next-hour
// snapshot, preflight both clock commits on detached copies, and publish
// them ONLY after G14::advance_with_precommit has returned successfully.
// Selected/test-only while native multi-station full 17-stage physics is
// not yet independently original-CALMET 45-field accepted.
#include "cteas/p6/p6g_g18b9_original_gamma_controls.hpp"
#include "cteas/p6/p6g_g18b_upper_buffer_clock.hpp"
#include <chrono>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>

namespace cteas::calmet::p6g {
struct G18D2StagedStationClocks {
    const UnifiedMultistationHourlyScheduler* owner=nullptr;
    std::size_t hour_index=0;
    std::chrono::sys_seconds source_end{};
    G18BUpperHour observed;
    G18B4CGammaPrepared cgamma;
    G18BUpperBufferClock new_upper;
    G18B4CGammaClock new_gamma;
    bool published=false;
};
class G18D2StationClockAuthority {
public:
    [[nodiscard]] G18D2StagedStationClocks prepare_selected(
        const UnifiedMultistationHourlyScheduler& scheduler,
        const std::string& original_metinp,bool explicitly_test_only) const {
        if(!explicitly_test_only||!scheduler.has_original_controls())
            throw std::invalid_argument("G18D2 full native production upper history not yet accepted");
        const auto f=scheduler.preview_next_hour();
        const auto source=g18b9_parse_original_gamma_controls(
            original_metinp,f.stations.upper.size());
        G18D2StagedStationClocks prepared;
        prepared.owner=&scheduler;
        prepared.hour_index=f.hour_index;
        prepared.source_end=f.input.end;
        prepared.observed=upper_.select(f);
        prepared.cgamma=g18b7_prepare_source_grid_cgamma(
            gamma_,f,prepared.observed,source.zupt_m,true);
        prepared.new_upper=upper_;
        prepared.new_gamma=gamma_;
        // PRE-FLIGHT exact source AA/BB thermal and convective clock
        // transition on *copies* before starting any G14 physics.
        // A malformed second US cannot partially commit the first.
        prepared.new_upper.commit_after_completed_g14_hour(
            f,prepared.observed,f.hour_index+1);
        prepared.new_gamma.commit_after_completed_g14_hour(
            prepared.cgamma,f.hour_index+1);
        return prepared;
    }

    // G18F2: preflight source-clock admission while the authoritative
    // G14 physical state is STILL n-1. This must run before the P6F
    // precommit barrier returns. It proves that both independently
    // precommitted station candidates can publish at exactly n+1,
    // without touching clocks or creating a second hour authority.
    [[nodiscard]] bool can_publish_after_next_g14_commit(
        const UnifiedMultistationHourlyScheduler& scheduler,
        const G18D2StagedStationClocks& prepared) const noexcept {
        return !prepared.published&&prepared.owner==&scheduler&&
               prepared.new_upper.has_hour()&&
               prepared.new_gamma.has_committed_hour()&&
               prepared.new_upper.last_hour()==prepared.source_end&&
               prepared.new_gamma.committed_end()==prepared.source_end&&
               scheduler.completed_hours()==prepared.hour_index&&
               ((!has_published_&&prepared.hour_index==0)||
                (has_published_&&prepared.hour_index==last_hour_+1));
    }

    // G18F1: G14's fresh-owned per-hour executor must publish both
    // PREPDI/CGAMMA clocks AFTER accepted P6F and native physical memory,
    // but BEFORE the owning hourly executor is destroyed. This operation
    // must not throw after the physical commit; it returns false without
    // mutating either clock for any invalid/stale/duplicate candidate.
    [[nodiscard]] bool try_publish_only_after_completed_g14_noexcept(
        const UnifiedMultistationHourlyScheduler& scheduler,
        G18D2StagedStationClocks& prepared) noexcept {
        if(prepared.published||prepared.owner!=&scheduler||
           !prepared.new_upper.has_hour()||
           !prepared.new_gamma.has_committed_hour()||
           prepared.new_upper.last_hour()!=prepared.source_end||
           prepared.new_gamma.committed_end()!=prepared.source_end||
           scheduler.completed_hours()!=prepared.hour_index+1||
           (has_published_&&prepared.hour_index!=last_hour_+1)||
           (!has_published_&&prepared.hour_index!=0))
            return false;
        // The source clock candidates were independently committed and
        // validated on detached copies by prepare_selected BEFORE G14.
        // Both moves are compile-time noexcept; never partially update.
        static_assert(std::is_nothrow_move_assignable_v<G18BUpperBufferClock>);
        static_assert(std::is_nothrow_move_assignable_v<G18B4CGammaClock>);
        upper_=std::move(prepared.new_upper);
        gamma_=std::move(prepared.new_gamma);
        last_hour_=prepared.hour_index;
        has_published_=true;
        prepared.published=true;
        return true;
    }

    void publish_only_after_completed_g14(
        const UnifiedMultistationHourlyScheduler& scheduler,
        G18D2StagedStationClocks& prepared) {
        if(!try_publish_only_after_completed_g14_noexcept(scheduler,prepared))
            throw std::invalid_argument(
                "G18D2 G14 hour not accepted; refuse PREPDI/CGAMMA publish");
    }

    [[nodiscard]] bool has_published_hour() const noexcept {return has_published_;}
    [[nodiscard]] std::chrono::sys_seconds latest_upper_hour() const noexcept {
        return upper_.last_hour();
    }
    [[nodiscard]] std::chrono::sys_seconds latest_gamma_hour() const noexcept {
        return gamma_.committed_end();
    }
private:
    G18BUpperBufferClock upper_;
    G18B4CGammaClock gamma_;
    std::size_t last_hour_=0;
    bool has_published_=false;
};
} // namespace cteas::calmet::p6g
