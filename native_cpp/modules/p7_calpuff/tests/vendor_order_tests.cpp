#include "cteas/puff/vendor_order.hpp"
#include <iostream>
#include <stdexcept>

namespace {
template <typename F> void throws(F f, const char* reason) {
    try { f(); } catch (const std::logic_error&) { return; }
    throw std::runtime_error(reason);
}
}
int main() {
    try {
        using namespace cteas::puff;
        static_assert(kVendorSubstepOrder.size() == 11U);
        VendorSubstepOrder order;
        throws([&]{ order.completed(VendorSubstepPhase::EvaluateAdvect); },
               "advection accepted before cadence");
        throws([&]{ order.finish(); }, "incomplete puff falsely accepted");
        for (auto phase : kVendorSubstepOrder) order.completed(phase);
        order.finish();
        throws([&]{ order.completed(VendorSubstepPhase::CommitSetpuf); },
               "repeated SETPUF accepted");
        order.begin_next_substep();
        order.completed(VendorSubstepPhase::SamplingCadence);
        throws([&]{ order.completed(VendorSubstepPhase::SamplingCadence); },
               "duplicated cadence accepted");
        throws([&]{ order.completed(VendorSubstepPhase::CommitSetpuf); },
               "SETPUF jumped ahead of wind and position");
        for (std::size_t i=1; i<kVendorSubstepOrder.size(); ++i)
            order.completed(kVendorSubstepOrder[i]);
        order.finish();
        // Exercise real feature-dependent seams: a syntactically complete
        // 11-phase sequence must NOT bypass enabled QOLD, DRY, CALCPF.
        const auto before_history=[](VendorSubstepOrder& state){
            for(std::size_t i=0;i+1<kVendorSubstepOrder.size();++i)
                state.completed(kVendorSubstepOrder[i]);
        };
        {
            VendorSubstepOrder coupled(true,true);
            before_history(coupled);
            throws([&]{coupled.completed(VendorSubstepPhase::CommitNextStepHistory);},
                   "coupled history skipped pre-DRY mass snapshot");
            throws([&]{coupled.dry_removal_completed();},
                   "DRY accepted before QOLD");
            throws([&]{coupled.receptors_sampled();},
                   "CALCPF accepted before QOLD and DRY");
            coupled.captured_pre_removal_mass();
            throws([&]{coupled.receptors_sampled();},
                   "CALCPF accepted before required dry removal");
            coupled.dry_removal_completed();
            throws([&]{coupled.dry_removal_completed();},
                   "DRY accepted twice");
            throws([&]{coupled.completed(VendorSubstepPhase::CommitNextStepHistory);},
                   "history skipped enabled CALCPF");
            coupled.receptors_sampled();
            throws([&]{coupled.receptors_sampled();},
                   "CALCPF accepted twice");
            coupled.completed(VendorSubstepPhase::CommitNextStepHistory);
            coupled.finish();
            coupled.begin_next_substep();
            throws([&]{coupled.captured_pre_removal_mass();},
                   "QOLD accepted before next step SETPUF");
            before_history(coupled);
            coupled.captured_pre_removal_mass();
            coupled.dry_removal_completed();
            coupled.receptors_sampled();
            coupled.completed(VendorSubstepPhase::CommitNextStepHistory);
            coupled.finish();
        }
        {
            VendorSubstepOrder dry_only(true,false);
            before_history(dry_only);
            dry_only.captured_pre_removal_mass();
            dry_only.dry_removal_completed();
            throws([&]{dry_only.receptors_sampled();},
                   "CALCPF accepted when not configured");
            dry_only.completed(VendorSubstepPhase::CommitNextStepHistory);
            dry_only.finish();
            VendorSubstepOrder receptor_only(false,true);
            before_history(receptor_only);
            receptor_only.captured_pre_removal_mass();
            throws([&]{receptor_only.dry_removal_completed();},
                   "DRY accepted when not configured");
            receptor_only.receptors_sampled();
            receptor_only.completed(VendorSubstepPhase::CommitNextStepHistory);
            receptor_only.finish();
        }
        std::cout << "P7_VENDOR_COMP_COUPLED_SEQUENCE=PASS"
                  << " QOLD_BEFORE_DRY=ENFORCED"
                  << " DRY_BEFORE_CALCPF=ENFORCED"
                  << " CALCPF_BEFORE_HISTORY=ENFORCED"
                  << " DISABLED_PHASES=REJECTED"
                  << " NEXT_SUBSTEP_RESETS=YES\\n";
        std::cout << "P7_VENDOR_COMP_ORDER_CONTRACT=PASS"
                  << " PHASES=11 OUT_OF_ORDER=REJECTED"
                  << " PHYSICS_DRIVER_PARITY=NOT_YET_TESTED\n";
    } catch (const std::exception& e) {
        std::cerr << "P7_VENDOR_COMP_ORDER_CONTRACT=FAIL " << e.what() << '\n';
        return 1;
    }
}
