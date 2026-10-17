#include "cteas/p6/hourly_comp_scheduler.hpp"
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace cteas::calmet::p6;

static void need(bool ok, const char* why) {
    if (!ok) throw std::runtime_error(why);
}

struct DeterministicNativeAdapter final : NativeHourPhysics {
    std::vector<NativeHourStage> calls;
    float expected_prior = 0.0f;
    NativeHourStage fail_at = NativeHourStage::CommitOutput;
    bool inject_reference = false, fail_stage = false, omit_w = false;

    NativeHourStageResult run(NativeHourStage stage, NativeHourFrame& frame) override {
        calls.push_back(stage);
        if (stage == NativeHourStage::PrepdiPreviousZiconv) {
            need(frame.previous.ziconv_m.size() == 2500, "missing prior ZICONV");
            need(frame.previous.ziconv_m[0] == expected_prior,
                 "PREPDI was not handed previous-hour ZICONV");
        }
        if (stage == NativeHourStage::DiagnoStheorElustr2Mixhtst)
            frame.next.dptt_k[0] = 10.0f + static_cast<float>(frame.input.hour_index);
        if (stage == NativeHourStage::CompGridMixht) {
            need(frame.next.dptt_k[0] ==
                     10.0f + static_cast<float>(frame.input.hour_index),
                 "DIAGNO station /TJMP/ mutation did not precede COMP MIXHT");
            std::fill(frame.next.ziconv_m.begin(), frame.next.ziconv_m.end(),
                      static_cast<float>(frame.input.hour_index + 1));
            std::fill(frame.next.zi_m.begin(), frame.next.zi_m.end(),
                      static_cast<float>(frame.input.hour_index + 2));
        }
        if (stage == NativeHourStage::CommitOutput) {
            frame.fields.u_mps.assign(22500, 1.0f);
            frame.fields.v_mps.assign(22500, 1.0f);
            if (!omit_w) frame.fields.w_face_mps.assign(25000, 0.0f);
            frame.fields.temperature_k.assign(22500, 280.0f);
            frame.fields.qh_wm2.assign(2500, 25.0f);
            frame.fields.ustar_mps.assign(2500, 0.3f);
            frame.fields.el_m.assign(2500, -100.0f);
            frame.fields.wstar_mps.assign(2500, 0.5f);
        }
        if (fail_stage && stage == fail_at)
            throw std::runtime_error("intentional stage failure");
        if (inject_reference && stage == NativeHourStage::CommitOutput)
            return {NativeHourSource::OriginalFortranOracle, true};
        return {NativeHourSource::NativeCpp, true};
    }
};

int main() {
    try {
        P6SinglePassHourlyScheduler scheduler(50, 50, 9);
        DeterministicNativeAdapter native;
        bool caught = false;
        try { scheduler.require_frozen_case_complete(); }
        catch (const std::runtime_error&) { caught = true; }
        need(caught, "partial 143h claim was accepted");

        for (std::size_t hour = 0; hour < 143; ++hour) {
            native.expected_prior = static_cast<float>(hour);
            native.calls.clear();
            scheduler.advance({hour, 1, "source-original-hour-label"}, native);
            need(native.calls.size() == kHefeiOriginalStageOrder.size(),
                 "missing or repeated original stage");
            need(std::equal(native.calls.begin(), native.calls.end(),
                            kHefeiOriginalStageOrder.begin()),
                 "wrong original COMP/DIAGNO call order");
            need(scheduler.committed_memory().ziconv_m[0] ==
                     static_cast<float>(hour+1),
                 "new ZICONV not committed after hourly COMP");
        }
        scheduler.require_frozen_case_complete();
        need(scheduler.completed_hours() == 143, "hour count mismatch");
        caught = false;
        try { scheduler.advance({143, 1, "overflow"}, native); }
        catch (const std::invalid_argument&) { caught = true; }
        need(caught, "144th hour should be rejected");

        P6SinglePassHourlyScheduler rollback(50, 50, 9);
        native.fail_at = NativeHourStage::CompGridMixht;
        native.fail_stage = true;
        native.expected_prior = 0.0f;
        caught = false;
        try { rollback.advance({0, 1, "hour-0"}, native); }
        catch (const std::runtime_error&) { caught = true; }
        need(caught && rollback.completed_hours() == 0 &&
                     rollback.committed_memory().dptt_k[0] == 0.0f,
             "failed hour leaked current-hour state");

        native.fail_stage = false;
        native.inject_reference = true;
        caught = false;
        try { rollback.advance({0, 1, "hour-0"}, native); }
        catch (const std::runtime_error&) { caught = true; }
        need(caught && rollback.completed_hours() == 0,
             "oracle injection was incorrectly accepted");

        native.inject_reference = false;
        native.omit_w = true;
        caught = false;
        try { rollback.advance({0, 1, "hour-0"}, native); }
        catch (const std::runtime_error&) { caught = true; }
        need(caught && rollback.completed_hours() == 0,
             "missing native WFACE silently accepted");

        // A nine-layer W array is incorrect: the native DIAGNO state
        // carries 10 vertical faces; the output writer omits only the bottom.
        native.omit_w = false;
        rollback.advance({0, 1, "hour-0"}, native);
        need(rollback.completed_hours() == 1, "valid retry did not commit");
        caught = false;
        try { rollback.advance({2, 1, "skipped-hour"}, native); }
        catch (const std::invalid_argument&) { caught = true; }
        need(caught, "skipped hour was accepted");
        caught = false;
        try { rollback.advance({1, 0, "unsupported-htfac"}, native); }
        catch (const std::invalid_argument&) { caught = true; }
        need(caught, "unsupported HTFAC route accepted");

        std::cout << "PASS_P6_SINGLE_PASS_HOURLY_SCHEDULER_CONTRACT "
                  << "143 consecutive hours, 17 source-ordered stages/hour, "
                  << "n-1 ZICONV, station DPTT, rollback, oracle rejection, "
                  << "missing W fail closed; PHYSICS_INTEGRATION=NOT_PASS\n";
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
    return 0;
}
