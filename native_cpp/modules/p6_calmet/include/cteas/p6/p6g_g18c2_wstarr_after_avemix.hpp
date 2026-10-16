#pragma once
// G18C2: source COMP order MIXHT -> (IAVEZI=1) AVEMIX -> WSTARR.
// Reuse unchanged PR #53 WSTARR. G18A's earlier WSTARR is only
// a standalone precursor test and is NOT the production WSTAR result.
#include "cteas/p6/p6g_g18c1_avemix.hpp"
#include "cteas/p6e/wstarr.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G18C2SourceCompAfterAverage {
    std::chrono::sys_seconds end{};
    p6::NativeGridMemory candidate_next;
    std::vector<float> wstar_mps;
};
inline G18C2SourceCompAfterAverage g18c2_wstarr_after_avemix(
    const MultiHourFrame& frame,
    const G18ASelectedCompResult& pre_average,
    const G18C1AvemixOutput& averaged,
    const G17CSelectedHeatResult& heat,
    const G17C2SelectedElustrResult& flux,
    bool explicitly_test_only) {
    const auto n=static_cast<std::size_t>(frame.grid.nx)*
                 static_cast<std::size_t>(frame.grid.ny);
    if(!explicitly_test_only||frame.input.end!=pre_average.end||
       frame.input.end!=heat.end||frame.input.end!=flux.end||
       frame.grid.landuse.size()!=n||averaged.zi_m.size()!=n||
       averaged.ziconv_m.size()!=n||heat.temperature_k.size()!=n||
       heat.density_kg_m3.size()!=n||flux.qh_wm2.size()!=n||
       pre_average.candidate_next.dptt_k.size()!=n||
       pre_average.candidate_next.zi_m.size()!=n||
       pre_average.candidate_next.ziconv_m.size()!=n||
       pre_average.wstar_mps.size()!=n||
       frame.fields.u_mps.size()!=9*n||
       frame.fields.v_mps.size()!=9*n||
       frame.fields.w_face_mps.size()!=10*n)
        throw std::invalid_argument("G18C2 requires source-selected complete MIXHT/AVEMIX/DIAGNO");
    // Source's MIXHT modifies DPTT, but AVEMIX modifies only the two
    // mixing-height grids (never the previous committed DPTT buffer).
    p6e::WstarrInput cfg;
    cfg.nx=static_cast<std::size_t>(frame.grid.nx);
    cfg.ny=static_cast<std::size_t>(frame.grid.ny);
    cfg.water_first=frame.grid.iwat1;cfg.water_last=frame.grid.iwat2;
    cfg.landuse=frame.grid.landuse;
    cfg.zi_conv_m=averaged.ziconv_m;
    cfg.heat_flux_wm2=flux.qh_wm2;
    cfg.temp_k=heat.temperature_k;
    cfg.rho_kgm3=heat.density_kg_m3;
    cfg.initial_wstar_ms.assign(n,0.f);
    auto wstar=p6e::wstarr(cfg);
    return {frame.input.end,
            {averaged.zi_m,averaged.ziconv_m,
             pre_average.candidate_next.dptt_k},std::move(wstar)};
}
} // namespace cteas::calmet::p6g
