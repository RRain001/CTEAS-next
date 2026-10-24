#pragma once
// S4-C: one first-hour research-only native G14 WATER actor shared by
// the G65 forensic reference and the parameterized S4B2 entry point.
// No source/Fortran oracle feeds these 17 physical stages. G26 default
// production admission remains closed; the caller must prove authentic
// G41/G43 and source shape before constructing this actor.
#include "cteas/p6/p6g_g26b_file_backed_comp_bridge.hpp"
#include "cteas/p6/p6g_g41_real_water_first_hour_source.hpp"
#include "cteas/p6/p6g_g66_noaa_hour3_g22_trace.hpp"
#include <cstddef>
#include <stdexcept>

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


// Strictly scoped fourth-hour executor: genuine G26A stages0–11 and G26B
// stages12–16 run on the G14-owned live frame with committed hour3 history.
// Production defaults remain fail-closed; every retry creates a fresh actor.
class G65RealNoaaFourthHourTrialActor final : public MultiHourPhysics {
public:
    G65RealNoaaFourthHourTrialActor(
        const UnifiedMultistationHourlyScheduler& owner,
        G18D2StationClockAuthority& clocks,
        const G19FileBackedCase& source,
        const G41SelectedNoowWaterFirstHourSource& original,
        const G66NativeHour2WaterState& native_prior)
        :diagno_(owner,clocks,source,true,&native_prior,
                 false,false,true,true),
         source_(source),original_(original) {}

    [[nodiscard]] p6::NativeHourStageResult run(
        p6::NativeHourStage stage,MultiHourFrame& frame) override {
        if(frame.hour_index!=3||
           cursor_>=p6::kHefeiOriginalStageOrder.size()||
           stage!=p6::kHefeiOriginalStageOrder[cursor_])
            throw std::logic_error(
                "G65 fourth-hour trial actor wrong hour/stage");
        if(cursor_==12)
            comp_.emplace(diagno_,source_,true,&original_,
                          false,false,false,true,true,true);
        const auto result=(cursor_<12)?diagno_.run(stage,frame)
                                     :comp_->run(stage,frame);
        if(!result.completed||
           result.source!=p6::NativeHourSource::NativeCpp)
            throw std::logic_error(
                "G65 fourth-hour trial missing source-native stage");
        ++cursor_;
        return result;
    }

    [[nodiscard]] const G64RealNoaaP6FPrecommit& precommit(
        const MultiHourFrame& frame) const {
        if(cursor_!=17||frame.hour_index!=3||!comp_)
            throw std::logic_error(
                "G65 fourth-hour precommit before all 17 native stages");
        const auto& candidate=comp_->source_water_p6f_stage16(frame);
        if(!candidate.actual_g14_stage16_precommit_validated||
           candidate.g14_hour_committed||candidate.source_clocks_published||
           candidate.ready_for_next_hour||
           candidate.candidate_dataset.hourly.size()!=45||
           candidate.serialized_prepared_only.empty())
            throw std::logic_error(
                "G65 fourth-hour P6F published prematurely or incomplete");
        diagno_.require_station_clock_preflight(frame);
        return candidate;
    }

    void require_station_clock_preflight(
        const MultiHourFrame& frame) const {
        if(cursor_!=17||frame.hour_index!=3)
            throw std::logic_error(
                "G65 fourth-hour clock preflight before native P6F");
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

// Strictly scoped fifth-hour executor: genuine G26A stages0–11 and G26B
// stages12–16 run on the G14-owned live frame with committed hour3 history.
// Production defaults remain fail-closed; every retry creates a fresh actor.
class G65RealNoaaFifthHourTrialActor final : public MultiHourPhysics {
public:
    G65RealNoaaFifthHourTrialActor(
        const UnifiedMultistationHourlyScheduler& owner,
        G18D2StationClockAuthority& clocks,
        const G19FileBackedCase& source,
        const G41SelectedNoowWaterFirstHourSource& original,
        const G66NativeHour2WaterState& native_prior)
        :diagno_(owner,clocks,source,true,&native_prior,
                 false,false,false,false,true,true),
         source_(source),original_(original) {}

    [[nodiscard]] p6::NativeHourStageResult run(
        p6::NativeHourStage stage,MultiHourFrame& frame) override {
        if(frame.hour_index!=4||
           cursor_>=p6::kHefeiOriginalStageOrder.size()||
           stage!=p6::kHefeiOriginalStageOrder[cursor_])
            throw std::logic_error(
                "G65 fifth-hour trial actor wrong hour/stage");
        if(cursor_==12)
            comp_.emplace(diagno_,source_,true,&original_,
                          false,false,false,false,false,false,
                          true,true,true);
        const auto result=(cursor_<12)?diagno_.run(stage,frame)
                                     :comp_->run(stage,frame);
        if(!result.completed||
           result.source!=p6::NativeHourSource::NativeCpp)
            throw std::logic_error(
                "G65 fifth-hour trial missing source-native stage");
        ++cursor_;
        return result;
    }

    [[nodiscard]] const G64RealNoaaP6FPrecommit& precommit(
        const MultiHourFrame& frame) const {
        if(cursor_!=17||frame.hour_index!=4||!comp_)
            throw std::logic_error(
                "G65 fifth-hour precommit before all 17 native stages");
        const auto& candidate=comp_->source_water_p6f_stage16(frame);
        if(!candidate.actual_g14_stage16_precommit_validated||
           candidate.g14_hour_committed||candidate.source_clocks_published||
           candidate.ready_for_next_hour||
           candidate.candidate_dataset.hourly.size()!=45||
           candidate.serialized_prepared_only.empty())
            throw std::logic_error(
                "G65 fifth-hour P6F published prematurely or incomplete");
        diagno_.require_station_clock_preflight(frame);
        return candidate;
    }

    void require_station_clock_preflight(
        const MultiHourFrame& frame) const {
        if(cursor_!=17||frame.hour_index!=4)
            throw std::logic_error(
                "G65 fifth-hour clock preflight before native P6F");
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

class G65RealNoaaSixthHourTrialActor final : public MultiHourPhysics {
public:
    G65RealNoaaSixthHourTrialActor(
        const UnifiedMultistationHourlyScheduler& owner,
        G18D2StationClockAuthority& clocks,
        const G19FileBackedCase& source,
        const G41SelectedNoowWaterFirstHourSource& original,
        const G66NativeHour2WaterState& native_prior)
        :diagno_(owner,clocks,source,true,&native_prior,
                 false,false,false,false,false,false,true,true),
         source_(source),original_(original) {}

    [[nodiscard]] p6::NativeHourStageResult run(
        p6::NativeHourStage stage,MultiHourFrame& frame) override {
        if(frame.hour_index!=5||
           cursor_>=p6::kHefeiOriginalStageOrder.size()||
           stage!=p6::kHefeiOriginalStageOrder[cursor_])
            throw std::logic_error(
                "G65 sixth-hour trial actor wrong hour/stage");
        if(cursor_==12)
            comp_.emplace(diagno_,source_,true,&original_,
                          false,false,false,false,false,false,
                          false,false,false,true,true,true);
        const auto result=(cursor_<12)?diagno_.run(stage,frame)
                                     :comp_->run(stage,frame);
        if(!result.completed||
           result.source!=p6::NativeHourSource::NativeCpp)
            throw std::logic_error(
                "G65 sixth-hour trial missing source-native stage");
        ++cursor_;
        return result;
    }

    [[nodiscard]] const G64RealNoaaP6FPrecommit& precommit(
        const MultiHourFrame& frame) const {
        if(cursor_!=17||frame.hour_index!=5||!comp_)
            throw std::logic_error(
                "G65 sixth-hour precommit before all 17 native stages");
        const auto& candidate=comp_->source_water_p6f_stage16(frame);
        if(!candidate.actual_g14_stage16_precommit_validated||
           candidate.g14_hour_committed||candidate.source_clocks_published||
           candidate.ready_for_next_hour||
           candidate.candidate_dataset.hourly.size()!=45||
           candidate.serialized_prepared_only.empty())
            throw std::logic_error(
                "G65 sixth-hour P6F published prematurely or incomplete");
        diagno_.require_station_clock_preflight(frame);
        return candidate;
    }

    void require_station_clock_preflight(
        const MultiHourFrame& frame) const {
        if(cursor_!=17||frame.hour_index!=5)
            throw std::logic_error(
                "G65 sixth-hour clock preflight before native P6F");
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

} // namespace cteas::calmet::p6g
