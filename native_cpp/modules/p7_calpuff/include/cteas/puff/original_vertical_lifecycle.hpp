#pragma once

#include "cteas/puff/original_met_cell.hpp"
#include "cteas/puff/release.hpp"
#include "cteas/puff/original_vmass.hpp"
#include "cteas/puff/sigma_update.hpp"

#include <cstddef>
#include <unordered_map>
#include <vector>

namespace cteas::puff {

// One authoritative native copy of the CALPUFF point-puff vertical COMMON
// variables at the boundary between successive COMP substeps. All values
// are REAL*4, including those returned by source-verified P7O/P7Q routines.
// Original DGM data is never accepted by any production method.
struct NativeVerticalPuffState {
    float sigma_y_m = 0.0F;
    float sigma_z_m = 0.0F;
    float ziold_m = 0.0F;
    float zimax_m = 0.0F;
    int puff_code = 0;
    std::vector<float> mass_mixed;
    std::vector<float> mass_above;
    std::size_t completed_substeps = 0;
    std::size_t committed_lid_steps = 0;
    // VMASS precedes SETPUF. Preserve the intermediate lid for COMP's
    // post-CALCPF history update at L11391-11398.
    bool vmass_pending = false;
    float pending_reflecting_lid_m = 0.0F;
};

struct NativeVerticalWind {
    OriginalMetCell cell;
    PuffExtent extent;
    AdvectiveWind wind;
    int stability_class = 0;
    float mixing_height_m = 0.0F;
};

// This advances the native physical *state connection*, not the complete
// COMP or SETPUF scheduler. After point-source admission, PUFFDZ reads
// persistent native SIGZB/ZIOLD/ZIMAX and ADVECT reads original METFM=1
// input via the already validated CALMET hourly reader. The caller must
// supply independently calculated HTMET (not a DGM/oracle value).
// All VMASS, SETPUF and late history commits are separately ordered.
class OriginalVerticalLifecycle {
public:
    void admit_point(int puff_id, const NewPuffInputs& source,
                     const InjectionInputs& injection);
    [[nodiscard]] NativeVerticalPuffState state(int puff_id) const;
    [[nodiscard]] NativeVerticalWind sample(
        int puff_id, const OriginalMetHour& met,
        const Calmet21Static& statics, float x_cells, float y_cells,
        float height_m) const;
    // COMP L10629-10649: CALMET WDIV inflates stored SIGZB AFTER
    // PUFFDZ/ADVECT, BEFORE VMASS/SETPUF. Never re-run PUFFDZ for this
    // step with the updated sigma; original uses old ZBOT/ZTOP.
    void commit_wdiv_sigma_z(int puff_id,float expected_before,
                             float updated_sigma_z);
    // COMP L10859 VMASS: consumes PRE-SETPUF SIGZB and updates QM/QU,
    // ICODE and intermediate ZIOLD/ZIMAX without committing next-step HLID.
    [[nodiscard]] VmassResult commit_vmass(
        int puff_id, float native_pbl_m,
        float native_height_begin_m, float native_height_end_m,
        float native_sigma_z_end_m, int native_stability_class,
        int native_plume_tilt);
    // Source-ported full P7Q sigma-step plus adjustment; commits only if
    // the step's initial sigma matches the persisted native state exactly.
    // Requires completed VMASS; failures leave old sigma unchanged.
    [[nodiscard]] SigmaUpdateResult commit_sigma(
        int puff_id, const SigmaUpdateInputs& inputs,
        const SigmaYCurve& sigma_y, const SigmaZCurve& sigma_z,
        const OriginalTerrainSigmaInputs* terrain=nullptr);
    // COMP calpuff.for 11391-11398, AFTER SETPUF and any VMASS operation:
    //   IPUFCD(II)=ICODE; ZIMAX=AMAX1(ZIMAX,HLID); ZIOLD=HLID.
    // HLID / adjusted puff code MUST be calculated by the native upstream
    // VMASS/COMP branch; this method cannot invent the 2-layer mass transfer.
    // Must be called AFTER SETPUF and, once connected, CHEM/WET/DRY/CALCPF.
    // One late lid commit for each completed native sigma substep.
    void commit_lid(int puff_id, float native_hlid_m, int native_puff_code);
    // DRY L11084–11090 acts after SETPUF and before CALCPF, updates
    // QM only. Preserve QU and the pending historical lid exactly.
    void commit_dry(int puff_id,const std::vector<float>& expected_mixed_before,
                    const std::vector<float>& mixed_after);
    void retire(int puff_id);
    [[nodiscard]] std::size_t active_count() const noexcept;
private:
    std::unordered_map<int, NativeVerticalPuffState> puffs_;
};

} // namespace cteas::puff
