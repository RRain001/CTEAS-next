#pragma once
// G18A: source-ordered selected COMP MIXHT and WSTARR using the frozen
// #53 kernels. Existing C2 selected 2SS+2US remains frozen. A source-backed,
// explicit 1SS+1US experiment is admitted for original numerical auditing only.
// Meteorological controls, PREPDI AA/BB and NEARU are fixture-scoped here;
// this is NOT a production COMP stage or complete multi-hour acceptance.
// The scheduler alone owns committing NativeGridMemory after ALL 17 stages.
#include "cteas/p6/p6g_g17c3_station_diagi.hpp"
#include "cteas/p6/p6g_g18b_upper_buffer_clock.hpp"
#include "cteas/p6e/mixht_observed_mc.hpp"
#include "cteas/p6e/wstarr.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G18ASelectedCompControls {
    // Fully explicit source-selected AA/BB soundings, JUSTA, NEARU and
    // original P6E constants. No hidden nearest-site or physics defaults.
    p6e::MixhtObservedMcInput grid_mixht;
    std::vector<float> initial_wstar_mps;
    bool explicitly_test_only=false;
    // Default false: do not broaden any existing selected fixture/admission.
    bool allow_one_one_source_audit=false;
    bool allow_asymmetric_source_audit=false;
};
struct G18ASelectedCompResult {
    std::chrono::sys_seconds end{};
    p6::NativeGridMemory candidate_next;
    std::vector<float> wstar_mps;
    // G29 audit-only: actual pre-call AA/BB, NEARU, source scalars and
    // prior-COMP/STHEOR inputs; NEVER the numerical Fortran reference.
    p6e::MixhtObservedMcInput source_mixht_input;
    // No completed NativeHourStageResult or scheduler commit is implied.
};
inline G18ASelectedCompResult selected_comp_mixht_wstarr_from_previous(
    const MultiHourFrame& frame,
    const G17CSelectedHeatResult& source_heat,
    const G17C2SelectedElustrResult& source_elustr,
    const std::vector<G17C3StationDiagi>& source_station,
    const G18ASelectedCompControls& ctrl) {
    const auto& g=frame.grid;
    if(g.nx<2||g.ny<2||g.nx>400||g.ny>400||
       !ctrl.explicitly_test_only||!frame.source_controls||
       frame.input.end!=frame.surface.end||
       frame.surface.end-frame.surface.start!=std::chrono::hours{1}||
       source_heat.end!=frame.input.end||
       source_elustr.end!=frame.input.end||
       source_station.size()!=frame.stations.surface.size()||
       ((frame.stations.surface.size()<2||frame.stations.upper.size()<2)&&
        !((ctrl.allow_one_one_source_audit&&
           frame.stations.surface.size()==1&&frame.stations.upper.size()==1)||
          (ctrl.allow_asymmetric_source_audit&&
           ((frame.stations.surface.size()==1&&frame.stations.upper.size()==2)||
            (frame.stations.surface.size()==2&&frame.stations.upper.size()==1))))))
        throw std::invalid_argument("G18A input provenance or selected COMP scope");
    const auto nx=static_cast<std::size_t>(g.nx);
    const auto ny=static_cast<std::size_t>(g.ny);
    const auto n=nx*ny;
    if(g.landuse.size()!=n||source_heat.temperature_k.size()!=n||
       source_heat.density_kg_m3.size()!=n||
       source_elustr.qh_wm2.size()!=n||
       source_elustr.ustar_mps.size()!=n||
       source_elustr.el_m.size()!=n||
       frame.previous.zi_m.size()!=n||
       frame.previous.ziconv_m.size()!=n||
       frame.previous.dptt_k.size()!=n||
       frame.fields.u_mps.size()!=9*n||
       frame.fields.v_mps.size()!=9*n||
       frame.fields.w_face_mps.size()!=10*n||
       ctrl.initial_wstar_mps.size()!=n)
        throw std::invalid_argument("G18A missing genuine DIAGNO or prior COMP fields");
    const auto& cfg=ctrl.grid_mixht;
    if(cfg.nx!=nx||cfg.ny!=ny||
       cfg.landuse!=g.landuse||
       cfg.sounding[0].size()!=frame.stations.upper.size()||
       cfg.sounding[1].size()!=frame.stations.upper.size()||
       cfg.justa.size()!=frame.stations.upper.size()||
       cfg.nearu.size()!=n||
       cfg.dptt_refresh!=0||
       (cfg.iupt!=-1 && (cfg.iupt<1||
        static_cast<std::size_t>(cfg.iupt)>frame.stations.upper.size()))||
       cfg.izicrlx<0)
        throw std::invalid_argument("G18A grid MIXHT source upper-air control invalid");
    for(float q:frame.fields.u_mps)
        if(!std::isfinite(q))throw std::invalid_argument("G18A nonfinite native DIAGNO U");
    for(float q:frame.fields.v_mps)
        if(!std::isfinite(q))throw std::invalid_argument("G18A nonfinite native DIAGNO V");
    for(float q:frame.fields.w_face_mps)
        if(!std::isfinite(q))throw std::invalid_argument("G18A nonfinite native DIAGNO W");
    // Carry previous committed state, not the mutable frame.next. Original
    // STHEOR/MIXHTST mutates /TJMP/ DPTT for the CURRENT COMP grid pass.
    auto in=cfg;
    in.initial_zi=frame.previous.zi_m;
    in.initial_ziconv=frame.previous.ziconv_m;
    in.initial_dptt=frame.previous.dptt_k;
    in.qh=source_elustr.qh_wm2;
    in.ustar=source_elustr.ustar_mps;
    in.el=source_elustr.el_m;
    in.rho=source_heat.density_kg_m3;
    std::vector<unsigned char> used(n,0);
    for(std::size_t i=0;i<source_station.size();++i) {
        const auto& site=source_station[i];
        if(site.end!=frame.input.end||
           site.surface_id!=frame.stations.surface[i].id||
           site.cell>=n||used[site.cell]++||
           !std::isfinite(site.station_mixing.dptt_for_comp_k))
            throw std::invalid_argument("G18A mismatched/duplicate source MIXHTST station cell");
        bool known_upper=false;
        for(std::size_t u=0;u<frame.stations.upper.size();++u)
            if(frame.stations.upper[u].id==site.upper_id) {
                const auto selected=cfg.iupt>0?cfg.iupt:cfg.nearu[site.cell];
                if(selected!=static_cast<int>(u+1))
                    throw std::invalid_argument("G18A MIXHT upper/site ordinal differs");
                known_upper=true;break;
            }
        if(!known_upper)
            throw std::invalid_argument("G18A station MIXHTST unknown upper site");
        // Crucial PREPDI/COMP state transition: the previous DPTT stays
        // immutable; station MIXHTST's current-hour result enters grid MIXHT.
        in.initial_dptt[site.cell]=site.station_mixing.dptt_for_comp_k;
    }
    const auto mixed=p6e::mixht_observed_mc(in);
    p6e::WstarrInput conv;
    conv.nx=nx;conv.ny=ny;
    conv.water_first=g.iwat1;conv.water_last=g.iwat2;
    conv.landuse=g.landuse;
    conv.zi_conv_m=mixed.ziconv;
    conv.heat_flux_wm2=in.qh;
    conv.temp_k=source_heat.temperature_k;
    conv.rho_kgm3=source_heat.density_kg_m3;
    conv.initial_wstar_ms=ctrl.initial_wstar_mps;
    const auto velocity=p6e::wstarr(conv);
    return {frame.input.end,{mixed.zi,mixed.ziconv,mixed.dptt},velocity,in};
}
// In G18B, physical AA/BB/JUSTA are now derived from the actual model-hour
// original UP station brackets, not copied from a stale fixture. NEARU,
// IUPT, CGAMMA and the other P6E parameters still need source attribution.
inline G18ASelectedCompResult selected_comp_mixht_with_observed_upper(
    const MultiHourFrame& frame,
    const G17CSelectedHeatResult& source_heat,
    const G17C2SelectedElustrResult& source_elustr,
    const std::vector<G17C3StationDiagi>& source_station,
    const G18BUpperHour& observed_upper,
    G18ASelectedCompControls ctrl) {
    g18b_bind_physical_upper(ctrl.grid_mixht,frame,observed_upper);
    return selected_comp_mixht_wstarr_from_previous(
        frame,source_heat,source_elustr,source_station,ctrl);
}
} // namespace cteas::calmet::p6g
