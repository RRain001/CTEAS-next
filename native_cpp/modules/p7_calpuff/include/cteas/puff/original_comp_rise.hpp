#pragma once

#include "cteas/puff/original_comp_neutral.hpp"
#include "cteas/puff/original_rise_met.hpp"
#include "cteas/puff/original_puffct2.hpp"
#include "cteas/puff/original_calm_sigma.hpp"
#include <cstddef>
#include <functional>
#include <optional>
#include <unordered_map>
#include <vector>

namespace cteas::puff {

// Restricted REAL*4 point-puff COMP integration WITH native Briggs GRISE and
// RISEWIND coupled to actual METFM1 winds and native PG SIGTY/SIGTZ, SETPUF
// position, VMASS and historical lids. No original DGM driving inputs.
// This covers one complete noncalm / one-sample / no-building puff substep,
// not original POINTS1/SWAP/MXSAM multi-substep scheduling or frozen Hefei
// numerical parity. PRFIN/PRFPP release parameters must be native inputs.
// Immutable state delivered precisely between original COMP SETPUF and
// its post-CALCPF historical ZIOLD/ZIMAX commit. A sampling callback must
// be pure: it returns per-receptor increments rather than mutating output.
// Chemistry, wet/dry mass removal, and receptor-specific PUFRECS/VCBAR
// remain independent full-case integration gates.
struct RiseCompSamplingState {
    int puff_id=0;
    OriginalPuffMotionState before;
    OriginalPuffMotionState after;
    NativeVerticalPuffState after_setpuf_before_lid;
    SigmaUpdateResult sigmas;
    VmassResult vmass;
    float step_seconds=0.0F;
    // Authoritative original SETCSIG/GRISE context for receptor-specific
    // PUFRECS: supplied by native COMP, never frozen DGM/puff.con.
    DispersionEnvironment receptor_dispersion;
    PlumeRiseState receptor_rise;
    float receptor_final_rise_distance_m=0.0F;
    float receptor_buoyancy_variance_m2=0.0F;
    float receptor_initial_sigma_y_squared_m2=0.0F;
    float receptor_minimum_sigma_y_m=0.0F;
    float receptor_minimum_sigma_z_m=0.0F;
    // Native SETPUF's *end* CTADJ2 call, never defaulted. This is
    // the state read by original PUFFCT2 at each receptor fraction.
    std::optional<OriginalPuffct2Step> original_ctadj2_step;
    // Authoritative COMP/SETPUF instantaneous environment needed by
    // receptor-specific terrain PUFRECS, NOT derived from receptor motion.
    float receptor_brunt_vaisala_s=0.0F;
    float receptor_effective_wind_ms=0.0F;
    // CALPUFF COMP L10963-10966: QOLD is recorded after VMASS,
    // before DRY/CHEM/WET mass removal; QNEW is post removal.
    // This is solver-owned state, never sampled from original puff.con.
    std::vector<float> receptor_qold_mixed;
    // Original COMP LCALM=1 selects SIGTY/SIGTZ IDOPT=1, including inside
    // receptor-specific PUFRECS. Do not silently fall back to PG IDOPT=3.
    // Derived from live SETCSIG/TURBSET meteorology, never from DGM.
    std::optional<OriginalCalmSigmaInput> receptor_calm_sigma;
    // Vendor CALCPF L4304 reads VDPVD(IPOL): DRY L26227-26261
    // sets a non-unity boundary ratio for uniform ICODE 2/6.
    // Gaussian codes retain 1.0. Native VDCOMP/DRY owns this state.
    float receptor_deposition_ratio=1.0F;
};
using RiseCompSamplingKernel=std::function<std::vector<float>(
    const RiseCompSamplingState&)>;
struct RiseCompStep {
    OriginalPuffMotionState before;
    OriginalPuffMotionState after;
    NativeVerticalPuffState vertical_after;
    NativeVerticalWind initial_met;
    OriginalRiseMetResult rise;
    SamplingCadence cadence;
    Substep substep;
    StepBookkeeping bookkeeping;
    SigmaUpdateResult sigma;
    VmassResult vmass;
    float final_height_m=0.0F;
    std::vector<float> receptor_increments;
    // Native QM after original DRY, before CALCPF, for scientific
    // audit/retirement. Empty if MDRY=0 or not enabled.
    std::optional<OriginalGaussianDryResult> dry;
    // Exact copied REAL4 COMP QOLD before DRY; read-only per-step provenance.
    // Never inferred by dividing QNEW by FRACDRY (would round differently).
    std::vector<float> pre_dry_qold_mixed;
    // Read-only original VDCOMP-produced VD/VDPVD for numerical audit.
    std::optional<DryDepositionStep> dry_input_resistance;
};

// COMP KSAM/NSAM context (vendor L10417, 10553-10581). Defaults reproduce
// the preexisting restricted single-sample solver. For FSTEP the calling
// scheduler must still account for TLEFT and resume the actual physics.
struct RiseCompSourceSampling {
    int ksam=1;
    int nsam=1;
    bool lsubsam=false;
};

class OriginalCompRisePointDriver {
public:
    void admit(int id,const NewPuffInputs& source,
               const InjectionInputs& release_mass);
    [[nodiscard]] RiseCompStep step_pg_rise(
        int id,const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,
        const DispersionSetup& pg,bool urban,
        RiseCompSourceSampling source_sampling={},
        const RiseCompSamplingKernel& sampling_kernel={});
    // Native COMP old-puff sampling wind BEFORE RISEWIND, from current
    // persistent PUFFDZ/ADVECT state (vendor L10119-10143).
    [[nodiscard]] NativeVerticalWind pre_cadence_wind(
        int id,const OriginalMetHour& met,
        const Calmet21Static& statics)const;
    [[nodiscard]] OriginalPuffMotionState motion(int id)const;
    [[nodiscard]] NativeVerticalPuffState vertical(int id)const;
    [[nodiscard]] std::size_t steps(int id)const;
    [[nodiscard]] std::size_t active_count()const noexcept;
    void retire(int id);
private:
    struct RiseSource {
        PlumeRiseState physics;
        float x_final_m=0.0F;
        float previous_wind_ms=0.0F;
        std::size_t completed=0U;
        float buoyancy_variance_m2=0.0F;
        float initial_sigma_y_squared_m2=0.0F;
        float minimum_sigma_y_m=0.0F;
        float minimum_sigma_z_m=0.0F;
    };
    OriginalPuffMotionLifecycle motion_;
    OriginalVerticalLifecycle vertical_;
    std::unordered_map<int,RiseSource> rise_;
};

} // namespace cteas::puff
