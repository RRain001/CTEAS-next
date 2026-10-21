#pragma once
// S4-O: a strictly TEST-ONLY numerical implementation of the ORIGINAL
// CALMET 6.5.0 WATER no-overwater-station neutral subset.
//
// Source: pinned original CALMET git blob 437f43bb... WATER:
//   L32721-32727 Hosker roughness, L32731 NOWSTA=0 skip,
//   L32808-32815 neutral USTAR/EL/WT,
//   L33059-33065 WSTAR=0 and buoyancy QH=WT*RHOCP,
//   L33068-33077 PGT category. NEVER the generic WATER/COARE/WATERP path.
// Does NOT produce ZI, ZICONV, DPTT or selected G14/G26 physical authority.
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cteas::calmet::p6g {
struct G35SelectedWaterNeutralControls {
    int nowsta=0,itwprog=0,icoare=10,imixh=1;
    int water_first=50,water_last=55;
    int original_land_category=52;
    float source_ws10_mps=0.f;
    bool explicit_reference_only=false;
};
struct G35SelectedWaterNeutralResult {
    float roughness_m{},ustar_mps{},el_m{},qh_buoyancy_wm2{},
          wt_kelvin_mps{},wstar_mps{};
    int pgt{};
    bool zi_ziconv_physics_ready=false;
    bool g14_g26_physics_ready=false;
};
inline G35SelectedWaterNeutralResult
g35_selected_original_nowsta0_water_reference(
    const G35SelectedWaterNeutralControls& c) {
    if(!c.explicit_reference_only)
        throw std::invalid_argument(
            "G35 original-water neutral numerical comparison is test-only; "
            "no G14/G26 authorization");
    if(c.nowsta!=0||c.itwprog!=0||c.icoare!=10||c.imixh!=1)
        throw std::invalid_argument(
            "G35 selected original no-overwater-observations tuple changed");
    if(c.water_first!=50||c.water_last!=55||
       c.original_land_category<c.water_first||
       c.original_land_category>c.water_last)
        throw std::invalid_argument("G35 original water category out of scope");
    if(!std::isfinite(c.source_ws10_mps)||c.source_ws10_mps<0.f)
        throw std::invalid_argument("G35 requires a valid original water WS10");
    // Literal original REAL*4 step sequence for neutral selected WATER.
    constexpr float z0min=2.e-6f,vk=.4f;
    const float z02=std::max(z0min,
                         2.e-6f*std::pow(c.source_ws10_mps,2.5f));
    const float ustar2=vk*c.source_ws10_mps/std::log(10.f/z02);
    G35SelectedWaterNeutralResult out;
    out.roughness_m=z02;
    out.ustar_mps=std::max(ustar2,1.e-9f);
    out.el_m=9.9e9f;
    // This is the original WATER buoyancy-flux common-array semantics,
    // not the atmospheric sensible heat-flux calculation of HEATFX land.
    const float wt=0.f;
    constexpr float rhocp=1195.2f;
    out.wt_kmps=wt;
    out.qh_buoyancy_wm2=wt*rhocp;
    out.wstar_mps=0.f;
    out.pgt=4;  // EL > 25, original WATER classified PGT D.
    // ZI depends on original IMIXH and previous-hour ZICOLD/DPTT;
    // intentionally absent. Construction never bypasses G18D3 guard.
    return out;
}
} // namespace cteas::calmet::p6g
