#pragma once
// S4-P: source-restricted, reference-only native original WATER mixing HEIGHT.
// Accepts ONLY actual unmodified original source FCORI + CONSTW + bounds;
// source WS10 is fed to already independently verified G35 neutral friction.
// Does NOT compute native winds, original FCORI grid or admit G14/G26.
#include "cteas/p6/p6g_g35_original_noow_water_neutral.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cteas::calmet::p6g {
struct G36OriginalWaterZiInputs {
    G35SelectedWaterNeutralControls original_neutral{};
    float original_fcori_s_inv=0.f;
    float original_constw=0.f;
    float original_ziminw_m=0.f;
    float original_zimaxw_m=0.f;
    bool explicit_source_reference_only=false;
};
struct G36OriginalWaterZiResult {
    float zi_m{};
    float zimech_m{};
    float ziconv_m{};
    float persisted_zicold_m{};
    bool full_original_water_state_ready=false;
    bool g14_g26_production_ready=false;
};
inline G36OriginalWaterZiResult
g36_selected_original_nowsta0_zi_source_reference(
    const G36OriginalWaterZiInputs& in) {
    if(!in.explicit_source_reference_only)
        throw std::invalid_argument("G36 original water ZI is reference-only, not G14/G26");
    const auto flux=g35_selected_original_nowsta0_water_reference(
        in.original_neutral);
    if(!std::isfinite(in.original_fcori_s_inv)||
       in.original_fcori_s_inv<2.5e-5f||
       !std::isfinite(in.original_constw)||
       in.original_constw<=0.f||
       !std::isfinite(in.original_ziminw_m)||
       in.original_ziminw_m<=0.f||
       !std::isfinite(in.original_zimaxw_m)||
       in.original_zimaxw_m<in.original_ziminw_m)
        throw std::invalid_argument("G36 original FCORI/CONSTW/ZIMINW/ZIMAXW source invalid");
    if(flux.wt_kelvin_mps!=0.f||flux.qh_buoyancy_wm2!=0.f)
        throw std::logic_error("G36 neutral WT must be identically zero");
    // Unmodified original MIXHMC, WT=0, source 11681..11701:
    // regardless IZICRLX branch, original returns immediately ZICONV=0.
    const float ziconv=0.f;
    // Exact original selected WATER L32964, L33019, L33027..33029.
    const float zimech=in.original_constw*flux.ustar_mps/
                         in.original_fcori_s_inv;
    const float zi=std::min(in.original_zimaxw_m,
        std::max(in.original_ziminw_m,std::max(zimech,ziconv)));
    return {zi,zimech,ziconv,ziconv,false,false};
}
} // namespace cteas::calmet::p6g
