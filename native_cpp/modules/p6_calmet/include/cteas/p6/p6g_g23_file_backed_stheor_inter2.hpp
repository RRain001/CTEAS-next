#pragma once
// G23: file-backed G14 hour, G22 HEATFX/ELUSTR -> original STHEOR,
// station MIXHTST/DIAGI -> first original WINDBC -> INTER2 selected kernel.
// Reuse frozen #53 numeric physics, source G19/G20/G21/G22, and the SINGLE
// G14 previous-hour authority. TEST-ONLY: not complete native CALMET/P6F
// and not yet original multi-station end-to-end 45-field equivalence.
#include "cteas/p6/p6g_g22_file_backed_thermal_slope.hpp"
#include "cteas/p6/p6g_g18d5_source_mixht_controls.hpp"
#include "cteas/p6/p6g_g17c3_station_diagi.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {

struct G23SelectedSourceStheorInter2 {
    std::chrono::sys_seconds end{};
    std::size_t hour_index=0;
    std::vector<G17C3StationDiagi> station_diagi;
    G16ObservedProfiles observed_after_diagi;
    p6::Inter2SelectedOutput inter2_u,inter2_v;
    std::vector<float> original_ub_west_east_mps;
    std::vector<float> original_vb_south_north_mps;
    float source_fcori_s=0.f,source_cmech=0.f;
    std::size_t replaced_surface_profile_values=0;
};

// Original SETCOM L: FCORI(I,J)=max(abs(FCORIOL),0.25e-4) when the
// user supplies a non-missing FCORIOL; CMECH(I,J)=CONSTB/sqrt(FCORI).
// The default G17C3 controls wrongly used a fixture CMECH=100. Current
// source case explicitly supplies FCORIOL=1e-4, so a scalar is valid.
// FCORIOL>998 produces site-dependent latitude FCORI; FAIL until that
// grid-varying branch is tied to a distinct source Fortran acceptance.
inline G17C3StationControls g23_source_stheor_station_controls(
    const std::string& met,
    const std::vector<std::size_t>& ordinal_for_surface,
    const G12HeatCoefficients& source_heat,
    std::size_t source_surface_count,
    bool explicitly_test_only) {
    if(!explicitly_test_only)
        throw std::invalid_argument("G23 source STHEOR remains selected test-only");
    if(g18d5_source_integer(met,"ICOARE")<=0)
        throw std::invalid_argument("G23 original ICOARE=0 changes ISFCMET/IPSIFCN");
    const float fcoriol=g18d5_source_scalar(met,"FCORIOL");
    const float constb=g18d5_source_scalar(met,"CONSTB");
    const float conste=g18d5_source_scalar(met,"CONSTE");
    if(fcoriol>=998.f||constb<=0.f||conste<0.f||conste>=1.f)
        throw std::invalid_argument("G23 source latitude-varying FCORI or bad mechanical mixing controls");
    G17C3StationControls c;
    c.explicitly_test_only=true;
    c.upper_ordinal_for_surface=ordinal_for_surface;
    c.heat_coefficients=source_heat;
    c.ipsifcn=0; // READCF ICOARE>0 selection
    c.imixh=g18d5_source_integer(met,"IMIXH");
    c.izicrlx=g18d5_source_integer(met,"IZICRLX");
    c.zimin_m=g18d5_source_scalar(met,"ZIMIN");
    c.zimax_m=g18d5_source_scalar(met,"ZIMAX");
    c.constn=g18d5_source_scalar(met,"CONSTN");
    c.dptmin_kperm=g18d5_source_scalar(met,"DPTMIN");
    c.dzzi_m=g18d5_source_scalar(met,"DZZI");
    c.threshl=g18d5_source_scalar(met,"THRESHL");
    c.tzicrlx_s=g18d5_source_scalar(met,"TZICRLX");
    // Literal SETCOM reads hour NSECDT=3600 and uses REAL*4 arithmetic.
    c.twodte_s=2.f*3600.f*conste;
    c.onedte_s=3600.f*(1.f+conste);
    c.fcori_s=std::max(std::abs(fcoriol),0.25e-4f);
    c.cmech=constb/std::sqrt(c.fcori_s);
    if(c.upper_ordinal_for_surface.size()!=source_surface_count||
       !std::isfinite(c.cmech)||c.cmech<=0.f||
       c.zimin_m<=0.f||c.zimax_m<c.zimin_m||c.dptmin_kperm<=0.f||
       c.dzzi_m<=0.f||c.constn<=0.f||c.tzicrlx_s<=0.f||
       c.imixh!=1||c.izicrlx!=1)
        throw std::invalid_argument("G23 original selected STHEOR/MIXHTST source controls outside scope");
    return c;
}

// One original READCF numerical control path, whether all-land source G19
// or genuine real-WATER source G41; neither licenses G23 production.
inline G17C3StationControls g23_stheor_original_readcf_controls(
    const G19FileBackedCase& source,bool explicitly_test_only) {
    return g23_source_stheor_station_controls(
        source.original_metinp,
        source.stheor_upper_ordinal_for_surface,
        source.heat_inputs.coefficients,
        source.stations.surface.size(),
        explicitly_test_only);
}

// Frame is passed by reference because G16 selected WIND1 and INTER2 use the
// authoritative G14 frame. This function MUST NOT commit or change physical
// prior-hour state; the production G14 17-stage owner still fails closed.
inline G23SelectedSourceStheorInter2 g23_source_stheor_diagi_inter2(
    MultiHourFrame& frame,
    const G19FileBackedCase& source,
    G16ObservedProfiles original_g20_profiles,
    const G21SelectedFradjFields& g21,
    const G22SelectedThermalSlope& g22,
    bool explicitly_test_only) {
    const auto& grid=frame.grid;
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    const auto n=nx*ny;
    const auto prior=frame.previous;
    if(!explicitly_test_only||!frame.source_controls||
       frame.input.end!=frame.surface.end||frame.input.end!=g21.end||
       frame.input.end!=g22.end||frame.input.end!=original_g20_profiles.end||
       source.grid.nx!=grid.nx||source.grid.ny!=grid.ny||
       source.grid.landuse!=grid.landuse||
       source.grid.terrain_m!=grid.terrain_m||
       source.stations.surface.size()!=frame.stations.surface.size()||
       source.stations.upper.size()!=frame.stations.upper.size()||
       source.surface.station_ids.size()!=frame.stations.surface.size()||
       source.surface.begin>frame.surface.start||
       source.surface.end<frame.surface.end||
       g22.post_slope_wind.u.size()!=9*n||
       g22.post_slope_wind.v.size()!=9*n||
       g22.heat.temperature_k.size()!=n||
       g22.elustr.qh_wm2.size()!=n)
        throw std::invalid_argument("G23 source G22/DIAGI not the same live G14 input");
    for(std::size_t i=0;i<frame.stations.surface.size();++i)
        if(source.stations.surface[i].id!=frame.stations.surface[i].id||
           source.surface.station_ids[i]!=frame.stations.surface[i].id)
            throw std::invalid_argument("G23 original SS source ordinal mismatch");
    for(std::size_t i=0;i<frame.stations.upper.size();++i)
        if(source.stations.upper[i].id!=frame.stations.upper[i].id)
            throw std::invalid_argument("G23 original US source ordinal mismatch");

    G17B4TwoPassSurfvar surfvar(
        grid,frame.stations,source.surface,frame.surface,source.surface_controls);
    // Keep the original station profile immutable for subsequent DIAGI merge.
    G16SelectedWindPhysics original_wind(original_g20_profiles);
    const auto first=original_wind.run(
        p6::NativeHourStage::DiagnoWind1,frame);
    if(!first.completed||first.source!=p6::NativeHourSource::NativeCpp)
        throw std::logic_error("G23 original G20 WIND1 stage missing");
    const auto& initial=original_wind.selected_result().first_guess;
    surfvar.after_wind1_before_fradj(
        frame.input.end,initial.u_mps,initial.v_mps);
    surfvar.after_fradj_before_heatfx(
        frame.input.end,g21.corrected_wind.u,g21.corrected_wind.v);
    if(surfvar.first_temperature()!=g21.temperature_before_k||
       surfvar.final_temperature()!=g21.temperature_after_k||
       g22.heat.temperature_k!=surfvar.final_temperature()||
       g22.heat.sensible_heat_wm2.size()!=n)
        throw std::invalid_argument("G23 source STHEOR cannot consume forged prior SURFVAR");

    const auto controls=g23_stheor_original_readcf_controls(source,true);
    // The original IF(ISURFT=-1) STHEOR stage occurs AFTER SLOPE and
    // FIRST WINDBC, yet it consumes observed SURF/UP, previous n-1
    // grid ZI/ZICONV/DPTT, actual HEATFX, and source SETCOM station US.
    const auto candidate=selected_station_diagi_from_previous_comp(
        frame,surfvar,g22.heat,controls);
    const auto merged=merge_g17c3_surface_diagi(
        original_g20_profiles,frame.stations,candidate);

    G16PostSlopeFields corrected;
    corrected.end=frame.input.end;
    corrected.u_mps=g22.post_slope_wind.u;
    corrected.v_mps=g22.post_slope_wind.v;
    if(frame.source_controls->iprog!=0)
        throw std::invalid_argument("G23 source WO differs from selected RDWT=1 branch");
    corrected.observation_weight.assign(9*n,1.f);
    corrected.ub_west_east_mps.resize(18*ny);
    corrected.vb_south_north_mps.resize(18*nx);
    // Original CALMET source WINDBC snapshot BEFORE INTER2, not
    // post-INTER2 blended values. Keep it immutable for final W segment.
    for(std::size_t k=0;k<9;++k) {
        for(std::size_t j=0;j<ny;++j) {
            const auto row=k*n+j*nx,face=k*2*ny+j;
            corrected.ub_west_east_mps[face]=corrected.u_mps[row];
            corrected.ub_west_east_mps[face+ny]=corrected.u_mps[row+nx-1];
        }
        for(std::size_t i=0;i<nx;++i) {
            const auto row=k*n+i,face=k*2*nx+i;
            corrected.vb_south_north_mps[face]=corrected.v_mps[row];
            corrected.vb_south_north_mps[face+nx]=
                corrected.v_mps[row+(ny-1)*nx];
        }
    }
    original_wind.provide_post_slope(std::move(corrected));
    original_wind.provide_selected_diagi_after_wind1(merged);
    const auto inter2=original_wind.run(
        p6::NativeHourStage::DiagnoInter2,frame);
    if(!inter2.completed||inter2.source!=p6::NativeHourSource::NativeCpp)
        throw std::logic_error("G23 original INTER2 not computed");

    const auto& wind=original_wind.selected_result();
    if(frame.previous.zi_m!=prior.zi_m||
       frame.previous.ziconv_m!=prior.ziconv_m||
       frame.previous.dptt_k!=prior.dptt_k)
        throw std::logic_error("G23 STHEOR mutated authoritative G14 previous state");
    G23SelectedSourceStheorInter2 out;
    out.end=frame.input.end;out.hour_index=frame.hour_index;
    out.station_diagi=candidate;
    out.observed_after_diagi=merged;
    out.inter2_u=wind.blended_u;out.inter2_v=wind.blended_v;
    out.original_ub_west_east_mps=wind.original_ub_west_east_mps;
    out.original_vb_south_north_mps=wind.original_vb_south_north_mps;
    out.source_fcori_s=controls.fcori_s;out.source_cmech=controls.cmech;
    const auto nss=frame.stations.surface.size();
    const auto all=nss+frame.stations.upper.size();
    for(std::size_t k=0;k<9;++k)
        for(std::size_t i=0;i<nss;++i) {
            const auto p=k*all+i;
            out.replaced_surface_profile_values+=
                (merged.inter2_u_mps[p]!=merged.wind1_u_mps[p])+
                (merged.inter2_v_mps[p]!=merged.wind1_v_mps[p]);
        }
    return out;
}
} // namespace cteas::calmet::p6g
