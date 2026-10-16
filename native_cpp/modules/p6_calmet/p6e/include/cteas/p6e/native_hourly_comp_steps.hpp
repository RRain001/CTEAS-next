#pragma once
// First production-physics boundary for the original single-pass COMP loop.
// Reuses the ALREADY validated native P6E kernels (no new formula tests).
// The caller must provide native, same-hour P6D wind and surface meteorology.
// This is not an all-P6D/P6E runtime: DIAGNO/PREPDI adapter and native
// input/writer ownership remain G2/G4 blockers.
#include "cteas/p6/hourly_comp_scheduler.hpp"
#include "cteas/p6e/avetmp.hpp"
#include "cteas/p6e/mixht_observed_mc.hpp"
#include "cteas/p6e/wstarr.hpp"
#include "cteas/p6e/temp3d_observed_land.hpp"
#include <cstddef>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6 {

struct NativeCompHourControls {
    cteas::p6e::MixhtObservedMcInput mixing;  // hourly AA/BB soundings, landuse etc.
    cteas::p6e::AvetmpInput averaging;        // IAVEZI=1 original wind-level 1
    cteas::p6e::WstarrInput convective_scale;
    cteas::p6e::Temp3dObservedInput temperature;
    std::size_t station_cell = 0;            // zero-based /TJMP/ station
};

// COMP L4692: source-ordered handoff from DIAGNO's MIXHTST. The thermal
// history lives in frame.previous; only the station-cell DPTT comes from
// frame.next because STHEOR/ELUSTR2/MIXHTST already mutated it this hour.
// Do NOT read previous ZI in place of previous ZICONV.
inline void native_comp_grid_mixht(NativeHourFrame& frame,
                                   NativeCompHourControls& controls) {
    auto& a=controls.mixing;
    const std::size_t n=a.nx*a.ny;
    if(a.nx!=50 || a.ny!=50 || controls.station_cell>=n ||
       frame.previous.zi_m.size()!=n ||
       frame.previous.ziconv_m.size()!=n ||
       frame.previous.dptt_k.size()!=n ||
       frame.next.dptt_k.size()!=n ||
       frame.fields.qh_wm2.size()!=n ||
       frame.fields.ustar_mps.size()!=n ||
       frame.fields.el_m.size()!=n)
        throw std::invalid_argument("COMP MIXHT requires native same-hour P6D and previous-hour state");

    a.initial_zi.assign(n, -7777.f);  // Original selected MIXHT grid initializes ZI independently.
    a.initial_ziconv=frame.previous.ziconv_m;
    a.initial_dptt=frame.previous.dptt_k;
    // Only the station that DIAGNO revisited via MIXHTST has current-hour
    // /TJMP/ DPTT. Every other cell still sees the original previous hour.
    a.initial_dptt[controls.station_cell]=frame.next.dptt_k[controls.station_cell];
    a.dptt_refresh=0;  // never recompute a surrogate station jump inside grid MIXHT
    a.qh=frame.fields.qh_wm2;
    a.ustar=frame.fields.ustar_mps;
    a.el=frame.fields.el_m;
    const auto result=cteas::p6e::mixht_observed_mc(a);
    frame.next.zi_m=result.zi;
    frame.next.ziconv_m=result.ziconv;
    frame.next.dptt_k=result.dptt;
}

// COMP L4715: upwind IAVEZI/ILEVZI=1 using same-hour *post-DIAGNO*
// U/V. Native grid ZICONV is preserved separately from output ZI.
inline void native_comp_avemix(NativeHourFrame& frame,
                               NativeCompHourControls& controls) {
    auto& a=controls.averaging;
    const std::size_t n=a.nx*a.ny;
    if(a.nx!=50||a.ny!=50||frame.fields.u_mps.size()<n||
       frame.fields.v_mps.size()<n||frame.next.zi_m.size()!=n||
       frame.next.ziconv_m.size()!=n)
        throw std::invalid_argument("COMP AVEMIX requires DIAGNO U/V and MIXHT state");
    a.u_ms.assign(frame.fields.u_mps.begin(),frame.fields.u_mps.begin()+n);
    a.v_ms.assign(frame.fields.v_mps.begin(),frame.fields.v_mps.begin()+n);
    const auto next=cteas::p6e::avemix(a,frame.next.zi_m,frame.next.ziconv_m);
    frame.next.zi_m=next.zi_m;
    frame.next.ziconv_m=next.ziconv_m;
}

// COMP L4744: WSTARR uses this same hour's QH and updated ZICONV,
// never frozen original MET.DAT ZI.
inline void native_comp_wstarr(NativeHourFrame& frame,
                               NativeCompHourControls& controls) {
    auto& a=controls.convective_scale;
    if(a.nx!=50||a.ny!=50||
       a.temp_k.size()!=a.nx*a.ny||a.rho_kgm3.size()!=a.nx*a.ny)
        throw std::invalid_argument("COMP WSTARR requires native TEMP2D/RHO");
    a.zi_conv_m=frame.next.ziconv_m;
    a.heat_flux_wm2=frame.fields.qh_wm2;
    frame.fields.wstar_mps=cteas::p6e::wstarr(a);
}

// COMP L4766: TEMP3D supplied from the native same-hour AA/BB temporal
// window, not interpolated from the frozen original CALMET.DAT.
inline void native_comp_temp3d(NativeHourFrame& frame,
                               NativeCompHourControls& controls) {
    auto& a=controls.temperature;
    if(a.nx!=50||a.ny!=50||a.nz!=9||a.surface_temp_k.size()!=2500)
        throw std::invalid_argument("COMP TEMP3D requires native 50x50x9 hourly observations");
    a.convective_zi_m=frame.next.ziconv_m;
    frame.fields.temperature_k=cteas::p6e::temp3d_observed_land(a);
}

inline NativeHourStageResult native_comp_dispatch(
    NativeHourStage stage, NativeHourFrame& frame,
    NativeCompHourControls& controls) {
    switch(stage) {
        case NativeHourStage::CompGridMixht: native_comp_grid_mixht(frame,controls); break;
        case NativeHourStage::CompAvemix: native_comp_avemix(frame,controls); break;
        case NativeHourStage::CompWstarr: native_comp_wstarr(frame,controls); break;
        case NativeHourStage::CompTemp3d: native_comp_temp3d(frame,controls); break;
        default: return {NativeHourSource::Unknown,false};
    }
    return {NativeHourSource::NativeCpp,true};
}
} // namespace cteas::calmet::p6
