#pragma once

#include "cteas/puff/original_motion_lifecycle.hpp"
#include "cteas/puff/original_vertical_lifecycle.hpp"
#include "cteas/puff/step_integration.hpp"
#include "cteas/puff/step.hpp"
#include "cteas/puff/dispersion.hpp"
#include "cteas/puff/vendor_order.hpp"
#include "cteas/puff/dry_deposition.hpp"
#include "cteas/puff/original_turbset_mdisp3.hpp"
#include "cteas/puff/original_vertical_divergence.hpp"
#include <optional>
#include <stdexcept>
#include <algorithm>
#include <cmath>
#include <limits>

namespace cteas::puff {

// A physically restricted but genuinely autonomous, original-ordered COMP
// *point-puff* integration path. It reads actual CALMET hourly U/V and native
// vertical state, performs PUFFDZ/ADVECT -> position -> SETPUF sigma -> VMASS
// -> COMP lid history and commits both state stores atomically.
// IMPORTANT: Rise-neutral, non-calm, one sampling substep only; no split,
// settling, buildings, terrain/PRIME, deposition or receptors. The frozen
// Hefei source is NOT rise-neutral; this is an integration stepping stone,
// never the original 143h case acceptance.
// Production MCTADJ2 requires the genuine TRELIEF/GETELEV native grid
// functions and a source-computed BVF. Synthetic callbacks are permitted
// only in labelled regression cases, never silently substituted on Hefei.
struct NativeMctadj2Controls {
    TerrainLookup terrain;
    float brunt_vaisala_s=0.0F;  // scoped synthetic fixed-BVF regressions only
    // Original COMP L10893-10896 recomputes PTLAPS/BVF for EACH puff
    // substep from its live METFM1 cell, ZBOT/ZTOP and TMET. Selecting
    // this mode prevents an hour-constant synthetic BVF in a real case.
    bool derive_bvf_from_metfm1=false;
    float minimum_pt_gradient_k_per_m=0.005F;
};
// Selected original CALPUFF MDRY=1 gas deposition at COMP
// L11076-11097. Explicitly opt-in until frozen 2022 setup/cell
// selection and uniform-code transition reach final case parity.
struct NativeGaussianDryControls {
    DryDepositionSetup setup;          // validated from original puff.inp
    float plume_path_coefficient=1.0F; // PPCOEF of selected source
};
// Opt-in original MDISP3 turbulence, with water category boundaries from
// authoritative MAKEGEO control rather than guessed land-use categories.
struct NativeCalmMdisp3Controls {
    OriginalTurbsetMdisp3 original_turbulence;
    int iwat1=0, iwat2=0;
    // Original COMP L10863-10883: JDSTAB=JSUP for a puff above the
    // mixing layer when ISTAB<5 and JSUP>0, BEFORE SVMIN/SWMIN selection.
    // Zero disables the synthetic fixture override; real cases MUST read
    // JSUP and the clipped mixing-layer bounds from original puff.inp.
    int jsup=0;
    float minimum_mixing_height_m=0.0F;
    float maximum_mixing_height_m=std::numeric_limits<float>::max();
};
// Use the *same* immutable puff.inp and makegeo.inp accepted by the
// original case, not user supplied/fitted turbulence defaults.
[[nodiscard]] inline NativeCalmMdisp3Controls original_calm_mdisp3_from_decks(
    const ControlFile& puff_control,const ControlFile& makegeo_control) {
    NativeCalmMdisp3Controls out;
    out.original_turbulence=original_turbset_mdisp3_from_control(puff_control);
    out.iwat1=makegeo_control.required_int("IWAT1");
    out.iwat2=makegeo_control.required_int("IWAT2");
    out.jsup=puff_control.required_int("JSUP");
    const auto xmin=puff_control.required_float_list("XMINZI");
    const auto xmax=puff_control.required_float_list("XMAXZI");
    if(xmin.size()!=1U||xmax.size()!=1U ||
       !std::isfinite(xmin[0])||!std::isfinite(xmax[0]) ||
       xmin[0]<=0.0||xmin[0]>xmax[0] ||
       xmax[0]>static_cast<double>(std::numeric_limits<float>::max()) ||
       out.jsup<0||out.jsup>6 ||
       out.iwat1<0||out.iwat1>out.iwat2)
        throw std::invalid_argument(
            "invalid source COMP JSUP/XMINZI/XMAXZI or MAKEGEO IWAT1/IWAT2");
    out.minimum_mixing_height_m=static_cast<float>(xmin[0]);
    out.maximum_mixing_height_m=static_cast<float>(xmax[0]);
    return out;
}
struct NeutralCompControls {
    float seconds=3600.0F;
    float source_period_s=3600.0F;
    float met_spacing_m=100.0F;
    float max_sample_distance_cells=1.0F;
    // Original CALPUFF COMP WSCALM, distinct from CALMET's ICALM.
    // Frozen Hefei puff.inp explicitly selects 0.5 m/s.
    float calm_threshold_ms=0.5F;
    int max_sampling_steps=1;
    int release_number=1;
    SigmaUpdateInputs dispersion;
    std::optional<NativeMctadj2Controls> mctadj2;
    std::optional<NativeGaussianDryControls> gaussian_dry;
    // COMP L10629 pre-VMASS WDIV -> SIGZB, opt-in for CALMET METFM1.
    std::optional<NativeOriginalWdivControls> original_wdiv;
    // Only post-rise unsampled calm point steps until receptor/DRY/MCTADJ2
    // source parity is established. Missing data is a hard error.
    std::optional<NativeCalmMdisp3Controls> calm_mdisp3;
};
struct NeutralCompResult {
    OriginalPuffMotionState before;
    OriginalPuffMotionState after;
    NativeVerticalPuffState vertical_after;
    OriginalMetCell cell;
    PuffExtent vertical_extent;
    AdvectiveWind wind;
    SamplingCadence cadence;
    Substep substep;
    StepBookkeeping bookkeeping;
    SigmaUpdateResult sigmas;
    VmassResult mass;
    float native_wind_speed_ms=0.0F;
};
class OriginalCompNeutralPointDriver {
public:
    void admit(int id,const NewPuffInputs& point,const InjectionInputs& injection);
    [[nodiscard]] NeutralCompResult step(
        int id,const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,
        const SigmaYCurve& curve_y,const SigmaZCurve& curve_z);
    // Same native ordered COMP transaction, now sourcing the SIGTY/SIGTZ
    // callbacks from the REAL4 source-ported MDISP=3 PG/MP curves using
    // the puff's current native METFM=1 wind/PG class, NOT test doubles.
    // The urban flag and MDISP options remain explicit until native
    // SETCSIG cell classification is integrated. Rise/calm limitations
    // of the single-substep controller remain in force.
    [[nodiscard]] NeutralCompResult step_pg(
        int id,const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,
        const DispersionSetup& setup,bool urban);
    [[nodiscard]] OriginalPuffMotionState motion(int id)const;
    [[nodiscard]] NativeVerticalPuffState vertical(int id)const;
    [[nodiscard]] std::size_t steps(int id)const;
    void retire(int id);
    [[nodiscard]] std::size_t active_count() const noexcept;
private:
    struct RunningPuff {
        std::size_t steps=0;
        float previous_ws_ms=0.0F;
    };
    OriginalPuffMotionLifecycle motion_;
    OriginalVerticalLifecycle vertical_;
    std::unordered_map<int,RunningPuff> running_;
};
} // namespace cteas::puff
