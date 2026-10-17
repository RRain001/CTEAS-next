#pragma once
// G18E3: route selected AIRDEN and ELUSTR through original G14 slots 4/5.
// Existing G17/G17C2/PR#53 kernels supply all physics; never duplicate it.
// Strictly fixture-scoped: production MultiHourPhysics::run remains false.
#include "cteas/p6/p6g_g18e2_heatfx_stage_adapter.hpp"
#include "cteas/p6/p6g_g17c2_elustr_handoff.hpp"
#include <chrono>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <utility>

namespace cteas::calmet::p6g {
class G18E3SelectedAirdenElustrStageAdapter final : public MultiHourPhysics {
public:
    G18E3SelectedAirdenElustrStageAdapter(
        G17SelectedTerrainFixturePhysics& terrain,
        const G18E2SelectedHeatfxStageAdapter& heat,
        const G17B4TwoPassSurfvar& surface,
        G17C2SelectedElustrControls controls)
        : terrain_(terrain), heat_(heat), surface_(surface),
          controls_(std::move(controls)) {}

    p6::NativeHourStageResult run(
        p6::NativeHourStage, MultiHourFrame&) override {
        return {p6::NativeHourSource::Unknown,false};
    }

    void run_selected(p6::NativeHourStage stage, MultiHourFrame& frame,
                      bool explicitly_test_only) {
        static_assert(p6::kHefeiOriginalStageOrder[4]==
                      p6::NativeHourStage::DiagnoAirden);
        static_assert(p6::kHefeiOriginalStageOrder[5]==
                      p6::NativeHourStage::DiagnoElustr);
        if(!explicitly_test_only||!controls_.explicitly_test_only||
           !frame.source_controls||frame.input.end!=frame.surface.end||
           (phase_==0 && stage!=p6::kHefeiOriginalStageOrder[4])||
           (phase_==1 && stage!=p6::kHefeiOriginalStageOrder[5])||
           phase_>=2)
            throw std::invalid_argument("G18E3 wrong source G14 AIRDEN/ELUSTR stage");
        const auto& heat=heat_.selected_heat_for(frame);
        if(phase_==0) {
            if(heat.end!=frame.input.end)
                throw std::invalid_argument("G18E3 AIRDEN wrong source-hour HEATFX");
            terrain_.prepare_selected_airden(frame,heat.temperature_k);
            const auto result=terrain_.run(p6::NativeHourStage::DiagnoAirden,frame);
            if(!result.completed||result.source!=p6::NativeHourSource::NativeCpp||
               terrain_.selected_air_density()!=heat.density_kg_m3)
                throw std::runtime_error("G18E3 AIRDEN differs from source-nearest station density");
            frame_=&frame;
            source_end_=frame.input.end;
            hour_index_=frame.hour_index;
            previous_=frame.previous;
            phase_=1;
        } else {
            verify_frame(frame);
            if(terrain_.selected_air_density()!=heat.density_kg_m3)
                throw std::runtime_error("G18E3 AIRDEN mutated before ELUSTR");
            auto result=selected_iavet1_elustr_after_heatfx(
                frame.grid,frame.stations,frame.surface,surface_,heat,
                terrain_.after_fradj(),controls_);
            elustr_.emplace(std::move(result));
            phase_=2;
        }
    }

    [[nodiscard]] const G17C2SelectedElustrResult& selected_elustr_for(
        const MultiHourFrame& frame) const {
        if(phase_!=2||!elustr_)throw std::logic_error(
            "G18E3 ELUSTR not executed at original G14 slot");
        verify_frame(frame);
        return *elustr_;
    }

    [[nodiscard]] bool selected_complete() const noexcept {return phase_==2;}
private:
    void verify_frame(const MultiHourFrame& frame) const {
        if(&frame!=frame_||frame.hour_index!=hour_index_||
           frame.input.end!=source_end_||
           frame.previous.zi_m!=previous_.zi_m||
           frame.previous.ziconv_m!=previous_.ziconv_m||
           frame.previous.dptt_k!=previous_.dptt_k)
            throw std::logic_error("G18E3 AIRDEN/ELUSTR crossed G14 frame/state boundary");
    }
    G17SelectedTerrainFixturePhysics& terrain_;
    const G18E2SelectedHeatfxStageAdapter& heat_;
    const G17B4TwoPassSurfvar& surface_;
    G17C2SelectedElustrControls controls_;
    std::optional<G17C2SelectedElustrResult> elustr_;
    const MultiHourFrame* frame_=nullptr;
    p6::NativeGridMemory previous_;
    std::chrono::sys_seconds source_end_{};
    std::size_t hour_index_=0;
    unsigned phase_=0;
};
} // namespace cteas::calmet::p6g
