#pragma once

#include "cteas/puff/original_comp_rise.hpp"
#include "cteas/puff/receptors.hpp"
#include "cteas/puff/original_puffct2.hpp"
#include <functional>

namespace cteas::puff {

// The legacy midpoint VCOUP path is kept as a control. The new, explicitly
// selected VCBAR path uses native SETPUF begin/mid/end sigma-z and heights.
// Neither choice by itself supplies receptor-dependent PUFRECS sigma/rise.
enum class OriginalFlatVerticalMethod {
    midpoint_vcoup,
    substep_vcbar,
    // Original CALCPF L4234-4275 uses PUFRECS's receptor-specific
    // SIGTY/SIGTZ, no-building GRISE and VCOUP, NOT a global VCBAR.
    // Still restricted to MCTADJ=0/MTILT=0/LPDF=F/MDRY=0.
    receptor_pg_vcoup,
    // No defaults for authentic CTADJ2 step, TRELIEF and GETELEV.
    receptor_pg_vcoup_mctadj2
};
// Diagnostic-only stage values for exact same-puff/same-KSAM receptor comparison.
// Values are captured from the live native CALCPF calculation, never used
// as inputs; the optional hook is disabled in every production path.
struct OriginalCalcpfReceiverIntermediate {
    std::size_t receptor_index=0;
    float receptor_fraction=0.0F;
    float sigma_y_m=0.0F;
    float sigma_z_m=0.0F;
    float puff_height_m=0.0F;
    float receptor_pole_m=0.0F;
    float vertical_factor=0.0F;
    float xi1=0.0F,xi2=0.0F,t1=0.0F,t2=0.0F;
    float qold=0.0F,qnew=0.0F,xtemp=0.0F,concentration=0.0F;
};
using OriginalCalcpfIntermediateHook=std::function<void(
    const RiseCompSamplingState&,
    const OriginalCalcpfReceiverIntermediate&)>;

using OriginalMctadj2TerrainLookup=std::function<
    OriginalMctadj2ReceptorTerrain(
        const RiseCompSamplingState&,std::size_t,
        const OriginalPuffct2Result&)>;

// Restricted, deliberately non-oracle flat-grid CALCPF integration.
// This connects native COMP's per-substep hook to the independently
// source-ported PFSCRN -> PFSAMP -> VCOUP -> CALCPF horizontal kernel.
// It is valid ONLY for gridded ground-level receptors, MESHDN=1,
// MCTADJ=0, no plume PDF, no receptor-specific PUFRECS adjustment,
// no settling/PRIME and M(CHEM,WET,DRY)=0 in legacy flat modes. Unsupported modes must
// not be labeled full 2022 CALPUFF parity. The receptor_pg_vcoup
// mode source-ports per-receptor SIGTY/SIGTZ, GRISE and VCOUP but does
// not complete MCTADJ=2 terrain, dry-removal or full case parity.
//
// The vendor uses sampling-grid XY indices for PFSAMP, but METRES for
// 1/(2*pi*sigma_y^2). The returned callback is pure: results are
// staged by COMP and committed only at the successful hour boundary.
[[nodiscard]] RiseCompSamplingKernel make_original_flat_calcpf_sampler(
    const ReceptorSet& receptors, float met_spacing_m,
    float averaging_period_s, float impact_sigma_multiple = 3.0F,
    OriginalFlatVerticalMethod vertical_method =
        OriginalFlatVerticalMethod::midpoint_vcoup,
    OriginalMctadj2TerrainLookup terrain_lookup={},
    bool selected_h3_from_multispecies=false,
    OriginalCalcpfIntermediateHook trace_hook={},
    // FCLIP is the PUFRECS trajectory-extension control, *not* CALCPF's
    // RCONST/NSIGMA influence radius. The legacy fixture default is kept;
    // original-case callers MUST pass the source-derived FCLIP explicitly.
    float receptor_clip_extension_sigma=3.0F);

} // namespace cteas::puff
