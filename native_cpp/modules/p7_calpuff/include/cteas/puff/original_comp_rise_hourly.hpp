#pragma once

#include "cteas/puff/original_comp_rise.hpp"
#include "cteas/puff/original_comp_exit.hpp"
#include "cteas/puff/original_release_wind.hpp"
#include "cteas/puff/original_point_prfin.hpp"
#include "cteas/puff/original_rolldn.hpp"
#include "cteas/puff/original_capacity_inventory.hpp"
#include <cstddef>
#include <optional>
#include <vector>

namespace cteas::puff {

// Deterministic 1/6/143h native MULTI-POINT COMP transaction with the
// genuine source-ported GRISE/RISEWIND + METFM1 + SIGTY/SIGTZ + VMASS chain.
// Input point admissions are EXPLICIT; native POINTS1/SWAP/ROLLDN original
// source release cadence is still independent pending integration.
struct RisePointAdmission {
    int puff_id=0;
    NewPuffInputs point;
    InjectionInputs mass;
};
struct RiseCompHourRecord {
    int puff_id=0;
    RiseCompStep step;
};
struct RiseCompHour {
    std::size_t hour_index=0;
    std::vector<RiseCompHourRecord> puffs;
    std::size_t active_after=0;
};

// One original POINTS1 *constant* point source with externally resolved
// WSNEW. Native RLSMET/PRFIN wind-at-final-rise selection must supply WSNEW
// upstream; this API NEVER infers WSNEW from a synthetic stack wind.
struct OriginalPointHourSource {
    NewPuffInputs point;
    InjectionInputs mass;
    ReleaseCadenceInputs cadence;
};
// Genuine POINTS1 release-state factory. Physical PRFIN/RLSMET is native,
// not read from the DGM; source-specific initial sigmas, elevation and
// emission rates are supplied explicitly from original puff.inp. Works
// with any MET grid-relative XY, not a hard-coded Hefei source location.
struct OriginalPointNativeSourceParameters {
    float base_elevation_m=0.0F;
    float met_spacing_m=0.0F; // original CALMET DELSAM, not release coords
    float initial_sigma_y_m=0.0F;  // original MAX(SYMIN,SYIPT1)
    float initial_sigma_z_m=0.0F;  // original MAX(SZMIN,SZIPT1)
    std::vector<double> emission_rates;
};
[[nodiscard]] OriginalPointHourSource original_point_hour_from_prfin(
    const OriginalPointPrfinRequest& request,
    const OriginalPointPrfinResult& rise,
    const OriginalPointNativeSourceParameters& source);

struct RiseCadencedSubstep {
    int puff_id=0;
    int original_release_number=0; // J=1..NPUFFS, 0 for old puff
    int sampling_slot=0;            // KSAM 1..NPUFFS
    RiseCompStep step;
};
struct RiseCadencedHour {
    std::size_t hour_index=0;
    ReleaseCadence cadence;
    std::vector<RiseCadencedSubstep> steps;
    std::size_t active_after=0;
    std::size_t new_puffs=0;
};
// Original 99-slot (old/new) sampling plan + actual rising COMP physics.
struct OriginalCompMxsamSubstep {
    int puff_id=0;
    int release_number=0;
    int ksam=0;
    SamplingCadence original_plan;
    RiseCompStep step;
};
struct OriginalCompPuffRetirement {
    int puff_id=0;
    OriginalCompExitReason reason=OriginalCompExitReason::Active;
    OriginalPuffMotionState motion_at_exit;
    // Preserve QM/QU for later MBALSUM(OUT/OBC) rather than losing it
    // when the inactive puff leaves the physical state stores.
    std::vector<float> mass_mixed;
    std::vector<float> mass_above;
};
// Opt-in source-pinned life-cycle subset: COMP QALL<=0 before each step
// and inclusive XB/XE/YB/YE center bounds after every executed puff step.
// Case caller must supply actual original CALPUFF bounds, NOT MET NX/NY.
struct OriginalCompMxsamHour {
    std::size_t hour_index=0;
    ReleaseCadence release;
    std::vector<OriginalCompMxsamSubstep> steps;
    std::size_t active_puffs=0;
    std::size_t fstep_shortened_steps=0; // physical FSTEP > 1
    std::size_t fstep_reentries=0; // original L11475-11486 goto 500
    std::vector<OriginalCompPuffRetirement> retired;
    // Populated by opt-in original POINTS1 capacity-controlled mode only.
    bool capacity_rolldn_triggered=false;
    std::size_t capacity_rolldn_removed=0;
    std::size_t occupied_slots_after=0;
    std::size_t inactive_slots_after=0;
    // Staged source/receptor contributions in original substep order.
    // Only returned on a successful hour-atomic commit.
    std::vector<float> receptor_concentrations;
};
class OriginalCompRiseMultiPuffHours {
public:
    [[nodiscard]] RiseCompHour advance_hour(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,
        const DispersionSetup& pg,bool urban,
        const std::vector<RisePointAdmission>& admissions);

    // Adds the original POINTS1 cadence NPUFFS and emits NPUFFS equal-mass
    // puffs per hour. Fresh release J executes KSAM=J..NPUFFS with TSAMP=DT,
    // old puffs advance one full hour in this explicitly restricted branch.
    // Until true COMP MXSAM/XSAMLEN and POINTS1/SWAP order are accepted,
    // this method REQUIRES max_sampling_steps=1, no split, and constant
    // point source (no building, variable emissions or MTAULY).
    [[nodiscard]] RiseCadencedHour advance_hour_point_cadence(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource& source);
    // First native original POINTS1/WSNEW path. Source must contain
    // independently computed native PRFIN HEFF; only selected original
    // METFM1 ZFIND/WINDSET/RLSMET speed is re-evaluated here.
    // Source.cadence.wind_speed_ms is never used as the physical input.
    [[nodiscard]] RiseCadencedHour advance_hour_point_native_wsnew(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource& source,
        float calm_threshold_ms);
    // Bounded source-ordered MXSAM=99 branch for constant POINTS1 puff:
    // real old pre-rise ADVECT WS -> NSAM, all old/new KSAM slots and
    // native physical PG/GRISE/VMASS, full-hour atomic commit. FSTEP>1,
    // CALM and off-grid stop FAIL CLOSED until original resplit/ROLLDN.
    // Original POINTS1 HTSTAK/HEFF WINDSET -> WSNEW -> MXSAM=99 COMP.
    // Unlike the lower-level unsplit API, ignores externally prefilled
    // source.cadence.wind_speed_ms. Native PRFIN HEFF remains caller-provided.
    // Still fails closed on vendor FSTEP split, calm old-puff, off-grid cases.
    [[nodiscard]] OriginalCompMxsamHour advance_hour_point_mxsam99_native_wsnew_unsplit(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource& source,
        float calm_threshold_ms);
    // Atomic vendor slot compaction + native release wind + restricted COMP.
    // inactive_old_ids is an EXPLICIT, previously diagnosed list; this
    // overload does not claim autonomous off-domain/zero-mass detection.
    // If the subsequent COMP hour fails (including unsupported FSTEP),
    // ROLLDN retirement, physical states and the hour counter ALL roll back.
    [[nodiscard]] OriginalCompMxsamHour
    advance_hour_point_mxsam99_native_wsnew_unsplit_rolldn(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource& source,
        float calm_threshold_ms,const std::vector<int>& inactive_old_ids);
    // Native RLSMET + original KSAM/TLEFT substep re-entry. This executes
    // the original source-ordered single-domain, noncalm PG/GRISE branch;
    // source PRFIN remains caller-provided. Every COMP hour commits atomically.
    [[nodiscard]] OriginalCompMxsamHour
    advance_hour_point_mxsam99_native_wsnew_adaptive(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource& source,
        float calm_threshold_ms);
    [[nodiscard]] OriginalCompMxsamHour advance_hour_point_mxsam99_adaptive(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource& source);
    [[nodiscard]] OriginalCompMxsamHour advance_hour_point_mxsam99_unsplit(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource& source);
    // Continue already-released puffs through a non-emitting hour. The
    // preceding hour's native XY/Z, SIGY/SIGZ, QM/QU, ZIOLD/ZIMAX and
    // accumulated travel time remain authoritative. This intentionally does
    // NOT call POINTS1/INJECT or create a new source episode.
    // All old-puff adaptive MXSAM=99 substeps commit as one hour or roll back.
    [[nodiscard]] OriginalCompMxsamHour advance_hour_existing_mxsam99_adaptive(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban);
    // Optional bounded active-inventory transitions. The old, unbounded
    // methods remain fail-closed on off-grid sampling. This path performs
    // automatic zero-mass and domain-exit diagnosis, stores removed mass
    // for accounting, and uses original ROLLDN slot COPY to compact.
    // Original timing of conditional ROLLDN at MXPUFF capacity remains a
    // separate full-case acceptance gate.
    [[nodiscard]] OriginalCompMxsamHour
    advance_hour_existing_mxsam99_adaptive_bounded(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalCompPuffBounds& bounds);
    [[nodiscard]] OriginalCompMxsamHour
    advance_hour_point_mxsam99_adaptive_bounded(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource& source,
        const OriginalCompPuffBounds& bounds);
    // Source POINTS1 capacity semantics: retain inactive ICODE=99 slots
    // across hours and call ROLLDN only if NP+NEWPUF > supplied MXPUFF.
    // Cannot be interleaved with legacy eager-compaction or unbounded APIs.
    [[nodiscard]] OriginalCompMxsamHour advance_hour_point_mxsam99_adaptive_bounded_capacity(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource& source,
        const OriginalCompPuffBounds& bounds,std::size_t mxpuff);
    [[nodiscard]] OriginalCompMxsamHour advance_hour_existing_mxsam99_adaptive_bounded_capacity(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalCompPuffBounds& bounds,std::size_t mxpuff);
    // Scoped PFSAMP/CALCPF sampling callback, executed at the actual
    // SETPUF -> [CALCPF] -> late-history boundary for EACH native substep.
    // Callback must not modify external state; the float32 total is
    // published only after successful complete-hour advancement.
    [[nodiscard]] OriginalCompMxsamHour advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource& source,
        const OriginalCompPuffBounds& bounds,std::size_t mxpuff,
        std::size_t receptor_values,const RiseCompSamplingKernel& kernel);
    [[nodiscard]] const OriginalPuffCapacityInventory& capacity_inventory()const;
    [[nodiscard]] OriginalPuffMotionState motion(int id)const;
    [[nodiscard]] NativeVerticalPuffState vertical(int id)const;
    [[nodiscard]] std::size_t puff_steps(int id)const;
    [[nodiscard]] std::size_t completed_hours()const noexcept;
    [[nodiscard]] std::size_t active_count()const noexcept;
    [[nodiscard]] const std::vector<int>& canonical_ids()const noexcept;
    void retire(int id);
    // Fortran ROLLDN/SWAP slot compaction with native puff state retained
    // under stable episode IDs. Caller supplies codes marked inactive by
    // native off-grid, zero-mass or retirement checks; this does NOT yet
    // perform original autonomous 143h exit detection.
    [[nodiscard]] std::size_t compact_original_inactive(
        const std::vector<int>& inactive_state_ids);
private:
    [[nodiscard]] OriginalCompMxsamHour advance_hour_mxsam99_source_order(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource& source,bool adaptive);
    [[nodiscard]] OriginalCompMxsamHour advance_hour_mxsam99_core(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource* source,bool adaptive,
        const OriginalCompPuffBounds* bounds=nullptr,
        bool deferred_original_rolldn=false,
        const RiseCompSamplingKernel* sampling_kernel=nullptr,
        std::size_t receptor_values=0);
    [[nodiscard]] OriginalCompMxsamHour advance_hour_capacity(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,const DispersionSetup& pg,
        bool urban,const OriginalPointHourSource* source,
        const OriginalCompPuffBounds& bounds,std::size_t mxpuff,
        const RiseCompSamplingKernel* sampling_kernel=nullptr,
        std::size_t receptor_values=0);
    OriginalCompRisePointDriver puffs_;
    std::vector<int> active_ids_;
    std::size_t hours_=0;
    int last_id_=0;
    std::optional<OriginalPuffCapacityInventory> capacity_slots_;
};
} // namespace cteas::puff
