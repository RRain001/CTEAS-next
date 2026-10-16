#pragma once
// G18E1: execute G17C3 STHEOR/ELUSTR2/MIXHTST/DIAGI in the immutable
// #53 G14 DIAGNO stage slot and deliver the result directly to G17 INTER2.
// This is a selected original-input TEST bridge, not a complete 17-stage
// native scheduler or evidence of original multi-site numerical equivalence.
#include "cteas/p6/p6g_g17c3_station_diagi.hpp"
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <utility>

namespace cteas::calmet::p6g {
class G18E1SelectedStheorStageAdapter final : public MultiHourPhysics {
public:
    G18E1SelectedStheorStageAdapter(
        G17SelectedTerrainFixturePhysics& terrain,
        G16ObservedProfiles original_wind1_and_prepdi,
        const G17B4TwoPassSurfvar& surface,
        const G17CSelectedHeatResult& heat,
        G17C3StationControls controls)
        : terrain_(terrain), profiles_(std::move(original_wind1_and_prepdi)),
          surface_(surface), heat_(heat), controls_(std::move(controls)) {}

    // Never convert selected/fixture station physics into NativeCpp=true
    // for the full 17-stage production scheduler.
    p6::NativeHourStageResult run(
        p6::NativeHourStage, MultiHourFrame&) override {
        return {p6::NativeHourSource::Unknown,false};
    }

    void run_selected(p6::NativeHourStage stage, MultiHourFrame& frame,
                      bool explicitly_test_only) {
        static_assert(p6::kHefeiOriginalStageOrder[8] ==
                      p6::NativeHourStage::DiagnoStheorElustr2Mixhtst);
        if(!explicitly_test_only||!controls_.explicitly_test_only||
           completed_||stage!=p6::kHefeiOriginalStageOrder[8]||
           !frame.source_controls||frame.input.end!=frame.surface.end||
           frame.surface.end!=profiles_.end||surface_.end()!=frame.input.end||
           heat_.end!=frame.input.end)
            throw std::invalid_argument(
                "G18E1 original G14 STHEOR/DIAGI stage or source-hour mismatch");
        // Compute actual selected STHEOR flux and station MIXHTST from the
        // immutable previous COMP state. No independent time controller.
        const auto candidate=selected_station_diagi_from_previous_comp(
            frame,surface_,heat_,controls_);
        const auto merged=merge_g17c3_surface_diagi(
            profiles_,frame.stations,candidate);
        // This checks original G17 FIRST WINDBC, current WIND1 identity and
        // upper PREPDI preservation before any INTER2 can consume the data.
        // Exceptions leave this adapter uncompleted and cannot advance G14.
        terrain_.provide_selected_diagi_before_inter2(merged);
        selected_=candidate;
        profiles_after_diagi_=merged;
        completed_=true;
        source_hour_=frame.hour_index;
        source_end_=frame.input.end;
        source_frame_=&frame;
        previous_snapshot_=frame.previous;
    }

    [[nodiscard]] bool selected_complete() const noexcept {
        return completed_&&selected_.has_value()&&
               profiles_after_diagi_.has_value();
    }
    [[nodiscard]] const std::vector<G17C3StationDiagi>& stations() const {
        if(!selected_complete())
            throw std::logic_error("G18E1 STHEOR stage not completed");
        return *selected_;
    }
    // Downstream COMP MUST consume this exact G14-stage result from the
    // same live hour frame and the identical immutable previous-hour
    // CALMET memory.  A same-timestamp preview clone is not authoritative.
    [[nodiscard]] const std::vector<G17C3StationDiagi>&
    stations_for_comp(const MultiHourFrame& frame) const {
        if(!selected_complete()||&frame!=source_frame_||
           frame.hour_index!=source_hour_||frame.input.end!=source_end_||
           frame.previous.zi_m!=previous_snapshot_.zi_m||
           frame.previous.ziconv_m!=previous_snapshot_.ziconv_m||
           frame.previous.dptt_k!=previous_snapshot_.dptt_k)
            throw std::logic_error(
                "G18E1 COMP requires same G14 STHEOR hour frame and previous state");
        return *selected_;
    }
    [[nodiscard]] const G16ObservedProfiles& observed_after_diagi() const {
        if(!selected_complete())
            throw std::logic_error("G18E1 source DIAGI observations unavailable");
        return *profiles_after_diagi_;
    }
    [[nodiscard]] std::size_t selected_hour_index() const {
        if(!selected_complete())
            throw std::logic_error("G18E1 source hour not completed");
        return source_hour_;
    }
private:
    G17SelectedTerrainFixturePhysics& terrain_;
    G16ObservedProfiles profiles_;
    const G17B4TwoPassSurfvar& surface_;
    const G17CSelectedHeatResult& heat_;
    G17C3StationControls controls_;
    std::optional<std::vector<G17C3StationDiagi>> selected_;
    std::optional<G16ObservedProfiles> profiles_after_diagi_;
    std::size_t source_hour_=0;
    std::chrono::sys_seconds source_end_{};
    const MultiHourFrame* source_frame_=nullptr;
    p6::NativeGridMemory previous_snapshot_;
    bool completed_=false;
};
} // namespace cteas::calmet::p6g
