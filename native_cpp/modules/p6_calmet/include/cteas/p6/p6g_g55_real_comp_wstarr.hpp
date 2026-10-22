#pragma once
// S4-R1c8g authentic NOAA first-hour source-only CALMET COMP WSTARR.
// Formula is exclusively the existing P6E original-validated kernel.
// Strict ordering: native G54 post-AVEMIX ZICONV + COMP-third
// SURFVAR HEATFX QH/TEMP2D/RHO; never earlier DIAGNO heat or Fortran oracle.
#include "cteas/p6/p6g_g54_real_land_mixht.hpp"
#include "cteas/p6e/wstarr.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace cteas::calmet::p6g {
struct G55NativeRealCompWstarr {
    std::chrono::sys_seconds end{};
    std::vector<float> wstar_mps;
    bool firsthour_source_only=false;
    bool native_temp3d_ready=false;
    bool g26_45field_ready=false;
    bool six_hour_causal_ready=false;
};
inline G55NativeRealCompWstarr g55_native_real_comp_wstarr(
    const G19SourceFilePaths& paths,bool explicitly_test_only){
    if(!explicitly_test_only)
        throw std::invalid_argument("G55 source COMP WSTARR production unavailable");
    const auto source=g41_load_selected_noow_water_first_hour_source(
        paths,true);
    const auto native=g54_real_noaa_firsthour_land_mixht(paths,true);
    const auto& grid=source.source.grid;
    const auto n=static_cast<std::size_t>(grid.nx)*
                 static_cast<std::size_t>(grid.ny);
    if(!native.sparse_first_hour_research_only||
       !native.native_avemix_candidate_unverified||
       native.native_avemix_ready||native.causal_six_hour_ready||
       native.g26_45field_ready||
       native.actual_land_count!=6907||
       native.actual_water_count!=63||
       native.zi_after_avemix_m.size()!=n||
       native.ziconv_after_avemix_m.size()!=n||
       native.comp_third_heat_k.size()!=n||
       native.comp_third_qh_wm2.size()!=n||
       native.comp_third_density_kgm3.size()!=n||
       grid.landuse.size()!=n||
       native.end!=source.source.surface.hourly.front().end)
        throw std::invalid_argument("G55 actual NOAA post-AVEMIX COMP source missing");
    p6e::WstarrInput state;
    state.nx=static_cast<std::size_t>(grid.nx);
    state.ny=static_cast<std::size_t>(grid.ny);
    state.water_first=grid.iwat1;state.water_last=grid.iwat2;
    state.landuse=grid.landuse;
    state.zi_conv_m=native.ziconv_after_avemix_m;
    state.heat_flux_wm2=native.comp_third_qh_wm2;
    state.temp_k=native.comp_third_heat_k;
    state.rho_kgm3=native.comp_third_density_kgm3;
    state.initial_wstar_ms.assign(n,0.f);
    auto field=p6e::wstarr(state);
    if(field.size()!=n)
        throw std::logic_error("G55 full source WSTARR state incomplete");
    for(std::size_t i=0;i<n;++i) {
        if(!std::isfinite(field[i])||field[i]<0.f)
            throw std::logic_error("G55 native WSTARR nonfinite or negative");
        if(grid.landuse[i]>=grid.iwat1&&grid.landuse[i]<=grid.iwat2 &&
           field[i]!=0.f)
            throw std::logic_error("G55 source-neutral WATER nonzero WSTAR");
    }
    return {native.end,std::move(field),true,false,false,false};
}
} // namespace cteas::calmet::p6g
