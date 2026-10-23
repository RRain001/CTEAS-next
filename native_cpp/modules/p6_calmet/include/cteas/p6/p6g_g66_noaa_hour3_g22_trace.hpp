#pragma once
// S4-R1c9n: strictly test-only third-hour NOAA G22 intermediate trace.
// Native current-hour WIND1/FRADJ + native prior-hour P6F WATER history ONLY.
// No original MET.DAT/trace is consumed; no G26 hour>1 guard is bypassed,
// no production stage is completed and no G14 state or clocks are published.
#include "cteas/p6/p6g_g22_file_backed_thermal_slope.hpp"
#include <bit>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6g {

// Narrow typed physical state: no P6F serialization dependency leaks
// into G26A or frozen C1/C2 test translation units.
struct G66NativeHour2WaterState {
    std::chrono::sys_seconds begin{},end{};
    std::vector<float> ustar_mps,el_m;
    bool explicitly_native_p6f_origin=false;
};

struct G66NoaaHour3G22Trace {
    // Strictly unpublished native result, eligible only for a separate
    // test-only G26A stage3 actor; NEVER a production stage admission.
    G22SelectedThermalSlope thermal;
    std::vector<std::uint8_t> bytes;
    std::size_t water_history_values=0;
    std::size_t traced_stages=0;
    bool production_admitted=false;
};

inline G66NoaaHour3G22Trace g66_native_hour3_g22_trace_only(
    const MultiHourFrame& frame,const G19FileBackedCase& source,
    const Wind1MultiField& native_wind1,
    const G21SelectedFradjFields& native_fradj,
    const G66NativeHour2WaterState& native_hour2_water,
    bool explicitly_test_only) {
    constexpr std::size_t nx=82,ny=85,nz=9,n=nx*ny;
    if(!explicitly_test_only||frame.hour_index!=2||
       !frame.source_controls||frame.grid.nx!=82||frame.grid.ny!=85||
       frame.stations.surface.size()!=2||frame.stations.upper.size()!=1||
       source.surface.hourly.size()!=6||
       source.source_water_cells.size()!=63||
       frame.input.end!=source.surface.hourly[2].end||
       frame.surface.start!=source.surface.hourly[1].end||
       frame.surface.end!=source.surface.hourly[2].end||
       frame.grid.landuse!=source.grid.landuse||
       frame.grid.terrain_m!=source.grid.terrain_m||
       native_wind1.nx!=82||native_wind1.ny!=85||native_wind1.nz!=9||
       native_wind1.u_mps.size()!=nz*n||
       native_wind1.v_mps.size()!=nz*n||
       native_fradj.end!=frame.input.end||
       native_fradj.corrected_wind.u.size()!=nz*n||
       native_fradj.corrected_wind.v.size()!=nz*n||
       !native_hour2_water.explicitly_native_p6f_origin||
       native_hour2_water.end!=frame.surface.start||
       native_hour2_water.begin!=frame.surface.start-std::chrono::hours{1}||
       native_hour2_water.ustar_mps.size()!=n||
       native_hour2_water.el_m.size()!=n)
        throw std::invalid_argument(
            "G66 requires committed native hour2 and authentic hour3 G26 stage02");
    if(frame.surface.end-frame.surface.start!=std::chrono::hours{1})
        throw std::invalid_argument("G66 NOAA hour3 UTC window drift");

    const auto& previous_ustar=native_hour2_water.ustar_mps;
    const auto& previous_el=native_hour2_water.el_m;

    G17B4TwoPassSurfvar surfvar(
        frame.grid,frame.stations,source.surface,frame.surface,
        source.surface_controls,true);
    surfvar.after_wind1_before_fradj(
        frame.input.end,native_wind1.u_mps,native_wind1.v_mps);
    surfvar.after_fradj_before_heatfx(
        frame.input.end,native_fradj.corrected_wind.u,
        native_fradj.corrected_wind.v);
    if(surfvar.first_temperature()!=native_fradj.temperature_before_k||
       surfvar.final_temperature()!=native_fradj.temperature_after_k)
        throw std::logic_error("G66 native third-hour SURFVAR/FRADJ mismatch");
    const float zm=0.5f*(frame.source_controls->zface_m[0]+
                          frame.source_controls->zface_m[1]);
    const auto thermal=g39_original_noow_water_postfradj_thermal_reference(
        frame.grid,frame.stations,frame.surface,surfvar,
        native_fradj.corrected_wind,source.original_metinp,zm,true);
    if(thermal.selected_original_water_cells!=63||
       !thermal.elustr.water_state_pending_original_WATER||
       thermal.heat.end!=frame.input.end||
       thermal.elustr.end!=frame.input.end)
        throw std::logic_error("G66 current-hour native thermal provenance lost");
    // Original SLOPE uses QH/TEMP2D only. Calculate it while native G39
    // still represents the pre-WATER zero-water intermediate. Then restore
    // the native hour2 post-WATER USTAR/EL in the *trace only*.
    const auto original_slope=g22_original_slope_after_elustr(
        frame.grid,*frame.source_controls,source.original_metinp,
        native_fradj.corrected_wind,thermal.heat,thermal.elustr,true);
    const auto terrain=prepare_g11_terrain(
        frame.grid,static_cast<float>(
            g19_read_real_control(source.original_metinp,"TERRAD")));
    p6::SlopeInput slope_input;
    slope_input.nx=82;slope_input.ny=85;slope_input.nz=9;
    slope_input.dx_m=terrain.spacing_m;
    slope_input.dy_m=terrain.spacing_m;
    slope_input.water_first=frame.grid.iwat1;
    slope_input.water_last=frame.grid.iwat2;
    slope_input.isurft=-1;
    slope_input.domain_temperature_k=thermal.heat.temperature_k.front();
    slope_input.zface_m.assign(frame.source_controls->zface_m.begin(),
                               frame.source_controls->zface_m.end());
    slope_input.terrain_m=terrain.terrain_m;
    slope_input.hmax_m=terrain.hmax_m;
    slope_input.hmin_m=terrain.hmin_m;
    slope_input.disthmax_m=terrain.dist_hmax_m;
    slope_input.disthmin_m=terrain.dist_hmin_m;
    slope_input.sensible_heat_w_m2=thermal.elustr.qh_wm2;
    slope_input.surface_temperature_k=thermal.heat.temperature_k;
    slope_input.landuse=terrain.landuse;
    const auto addition=p6::compute_original_slope_scoped(slope_input);
    if(addition.u_mps.size()!=nz*n||addition.v_mps.size()!=nz*n)
        throw std::logic_error("G66 SLOPE correction extent invalid");
    for(std::size_t k=0;k<nz*n;++k)
        if(std::bit_cast<std::uint32_t>(
               native_fradj.corrected_wind.u[k]+addition.u_mps[k])!=
               std::bit_cast<std::uint32_t>(
                   original_slope.post_slope_wind.u[k])||
           std::bit_cast<std::uint32_t>(
               native_fradj.corrected_wind.v[k]+addition.v_mps[k])!=
               std::bit_cast<std::uint32_t>(
                   original_slope.post_slope_wind.v[k]))
            throw std::logic_error("G66 SLOPE duplicate kernel mismatch");

    std::vector<float> current_ustar=thermal.elustr.ustar_mps;
    std::vector<float> current_el=thermal.elustr.el_m;
    std::size_t water=0;
    for(std::size_t i=0;i<n;++i) {
        const bool is_water=frame.grid.landuse[i]>=frame.grid.iwat1&&
                            frame.grid.landuse[i]<=frame.grid.iwat2;
        if(is_water) {
            if(thermal.elustr.qh_wm2[i]!=0.f||
               current_ustar[i]!=0.f||current_el[i]!=0.f||
               !std::isfinite(previous_ustar[i])||
               !std::isfinite(previous_el[i])||
               previous_ustar[i]<=0.f||previous_el[i]==0.f)
                throw std::logic_error(
                    "G66 invalid native prior WATER history or current QH");
            current_ustar[i]=previous_ustar[i];
            current_el[i]=previous_el[i];
            ++water;
        }
    }
    if(water!=63)
        throw std::logic_error("G66 GEO water mask not 63");

    G66NoaaHour3G22Trace result;
    result.water_history_values=2*water;
    const auto put_int=[&](std::int32_t value) {
        const auto word=std::bit_cast<std::uint32_t>(value);
        for(unsigned k=0;k<4;++k)
            result.bytes.push_back(static_cast<std::uint8_t>(
                (word>>(8U*k))&0xffU));
    };
    const auto put_float=[&](float value) {
        if(!std::isfinite(value))
            throw std::logic_error("G66 nonfinite source-native G22 field");
        const auto word=std::bit_cast<std::uint32_t>(value);
        for(unsigned k=0;k<4;++k)
            result.bytes.push_back(static_cast<std::uint8_t>(
                (word>>(8U*k))&0xffU));
    };
    const auto stage=[&](int code,const std::vector<float>& a,
                         const std::vector<float>* b=nullptr,
                         const std::vector<float>* c=nullptr) {
        const std::size_t count=(code==50)?n*nz:n;
        if(a.size()!=count||(b&&b->size()!=count)||
           (c&&c->size()!=count))
            throw std::logic_error("G66 trace field extent drift");
        put_int(4);put_int(82);put_int(85);put_int(9);put_int(code);
        for(std::size_t i=0;i<count;++i) {
            put_float(a[i]);
            if(b)put_float((*b)[i]);
            if(c)put_float((*c)[i]);
        }
        ++result.traced_stages;
    };
    stage(10,surfvar.first_temperature());
    stage(20,thermal.heat.temperature_k,
          &thermal.heat.sensible_heat_wm2,&thermal.heat.shortwave_wm2);
    stage(30,thermal.heat.density_kg_m3);
    stage(40,thermal.elustr.qh_wm2,&current_ustar,&current_el);
    stage(50,addition.u_mps,&addition.v_mps);
    constexpr std::size_t expected_bytes=5*20+
        4*n*(1+3+1+3+2*nz);
    if(result.traced_stages!=5||result.bytes.size()!=expected_bytes)
        throw std::logic_error("G66 trace byte schema drift");
    result.thermal.end=frame.input.end;
    result.thermal.heat=thermal.heat;
    result.thermal.elustr=thermal.elustr;
    result.thermal.elustr.ustar_mps=std::move(current_ustar);
    result.thermal.elustr.el_m=std::move(current_el);
    result.thermal.post_slope_wind=original_slope.post_slope_wind;
    result.thermal.changed_slope_components=
        original_slope.changed_slope_components;
    return result;
}
} // namespace cteas::calmet::p6g
