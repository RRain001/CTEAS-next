#pragma once
// S4-C: one first-hour research-only native G14 WATER actor shared by
// the G65 forensic reference and the parameterized S4B2 entry point.
// No source/Fortran oracle feeds these 17 physical stages. G26 default
// production admission remains closed; the caller must prove authentic
// G41/G43 and source shape before constructing this actor.
#include "cteas/p6/p6g_g26b_file_backed_comp_bridge.hpp"
#include "cteas/p6/p6g_g41_real_water_first_hour_source.hpp"
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

} // namespace cteas::calmet::p6g
