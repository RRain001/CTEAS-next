#pragma once
// S4-B2: EXACT previously accepted C2 G34B selected G14 17-stage actor,
// extracted without changing any stage equation, history or output field.
// Shared by the unchanged C2 G34B CLI and the new experimental generic CLI.
// G26::run() is still fail-closed; scientific approval is separate.
#include "cteas/p6/p6g_g19_file_backed_case.hpp"
#include "cteas/p6/p6g_g26b_file_backed_comp_bridge.hpp"
#include "cteas/p6/p6g_g18d1_p6f_precommit.hpp"
#include <cstddef>
#include <memory>
#include <optional>
#include <stdexcept>
namespace p6g=cteas::calmet::p6g;
namespace p6=cteas::calmet::p6;

class G34BSelectedOnlyHour final : public p6g::MultiHourPhysics {
public:
    G34BSelectedOnlyHour(const p6g::UnifiedMultistationHourlyScheduler& owner,
                         p6g::G18D2StationClockAuthority& clocks,
                         const p6g::G19FileBackedCase& source)
        :source_(source),diagno_(owner,clocks,source),comp_(diagno_,source) {}

    p6::NativeHourStageResult run(p6::NativeHourStage stage,
                                  p6g::MultiHourFrame& frame) override {
        if(cursor_>=17||stage!=p6::kHefeiOriginalStageOrder[cursor_])
            throw std::logic_error("G34B native stage skipped/reordered");
        if(cursor_<12) diagno_.run_selected(stage,frame,true);
        else if(cursor_<16) comp_.run_selected(stage,frame,true);
        else {
            const auto& candidate=comp_.selected_p6f_candidate(frame);
            const auto& heat=comp_.source_comp_heat_for_p6f(frame);
            const auto records=p6g::g18c5_selected_p6f_fields(
                frame,heat,candidate,source_.original_metinp,true);
            const auto dataset=p6g::g18c6_selected_one_hour_dataset(
                frame,records,p6g::source_setcom_nears(frame.grid,frame.stations),
                source_.original_metinp,true);
            const auto bytes=p6g::g18d1_validate_p6f_precommit(frame,dataset);
            if(bytes.empty()||dataset.hourly.size()!=45)
                throw std::logic_error("G34B native P6F candidate incomplete");
            output_.emplace(dataset);
        }
        ++cursor_;
        // Only this opt-in executable converts independently computed
        // selected kernels to a G14 transaction attempt, not production.
        return {p6::NativeHourSource::NativeCpp,true};
    }

    const cteas::p6f::Calmet21File& precommit(
        const p6g::MultiHourFrame& frame) const {
        if(cursor_!=17||!output_)
            throw std::logic_error("G34B missing native 17th stage or output");
        diagno_.require_station_clock_preflight(frame);
        return *output_;
    }

    bool publish_after_commit_noexcept() noexcept {
        return cursor_==17&&diagno_.try_publish_after_selected_g14_commit_noexcept();
    }
private:
    const p6g::G19FileBackedCase& source_;
    p6g::G26SourceFileBackedG14DiagnoBridge diagno_;
    p6g::G26BSourceFileBackedCompBridge comp_;
    std::size_t cursor_=0;
    std::optional<cteas::p6f::Calmet21File> output_;
};

