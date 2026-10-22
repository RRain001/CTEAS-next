#pragma once
// S4-R1c8i: genuine first-hour mixed LAND/WATER source-native P6F
// 43 REAL4 physical fields only; two original INTEGER4 IPGT/IRH
// remain separately unaccepted and are deliberately absent.
// Strict source-only: original Fortran intermediates are never inputs.
#include "cteas/p6/p6g_g56_real_comp_temp3d.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
namespace cteas::calmet::p6g {
struct G57FirstHour43Real {
    std::chrono::sys_seconds end{};
    std::vector<std::pair<std::string,std::vector<float>>> fields;
    std::size_t source_land=0,source_water=0;
    bool source_firsthour_43real_only=false;
    bool original_ipgt_irh_verified=false;
    bool g26_45field_ready=false;
    bool six_hour_causal_ready=false;
};
inline G57FirstHour43Real g57_noaa_real_43_output_fields(
    const G19SourceFilePaths& paths,bool explicit_source_only) {
    if(!explicit_source_only)
        throw std::invalid_argument("G57 45-field production cannot be admitted");
    const auto source=g41_load_selected_noow_water_first_hour_source(
        paths,true);
    const auto wind=g48_real_sparse_stheor_first_hour(
        paths,true,true,true,true);
    const auto mixed=g54_real_noaa_firsthour_land_mixht(paths,true);
    const auto water_source=g41_load_selected_noow_water_first_hour_source(
        paths,true);
    const auto water_scheduler=water_source.source.make_scheduler();
    const auto water_frame=water_scheduler.preview_next_hour();
    if(!wind.firsthour_g24_tail_unverified)
        throw std::logic_error("G57 no true native G24 final wind");
    const auto& g24=*wind.firsthour_g24_tail_unverified;
    const auto water=g53_real_source_g24_neutral_water_reference(
        water_source,water_frame,g24,true);
    const auto wstar=g55_native_real_comp_wstarr(paths,true);
    const auto temp=g56_real_source_comp_temp3d(paths,true);
    const auto n=static_cast<std::size_t>(source.source.grid.nx)*
                 static_cast<std::size_t>(source.source.grid.ny);
    if(n!=82U*85U||source.source.grid.nx!=82||
       source.source.grid.ny!=85||g24.end!=mixed.end||
       wstar.end!=mixed.end||temp.end!=mixed.end||
       water.end!=mixed.end||wind.missing_wind_skipped!=1||
       wind.native_valid_station.size()!=1||
       source.source.stations.surface.size()!=2||
       source.source.stations.upper.size()!=1||
       mixed.actual_land_count!=6907||mixed.actual_water_count!=63||
       water.water.size()!=63||!wstar.firsthour_source_only||
       !temp.firsthour_temp3d_forensic_only||
       !mixed.sparse_first_hour_research_only||
       mixed.g26_45field_ready||mixed.causal_six_hour_ready||
       g24.wind.u_mps.size()!=9*n||
       g24.wind.v_mps.size()!=9*n||
       g24.wind.w_face_mps.size()!=10*n||
       temp.temperature_k.size()!=9*n||
       mixed.zi_after_avemix_m.size()!=n||
       mixed.comp_third_ustar_mps.size()!=n||
       mixed.comp_third_el_m.size()!=n||
       mixed.comp_third_heat_k.size()!=n||
       mixed.comp_third_density_kgm3.size()!=n||
       mixed.comp_third_shortwave_wm2.size()!=n||
       wstar.wstar_mps.size()!=n)
        throw std::invalid_argument("G57 authentic source outputs missing or G26 falsely promoted");
    std::vector<float> ustar=mixed.comp_third_ustar_mps;
    std::vector<float> el=mixed.comp_third_el_m;
    for(const auto& w:water.water) {
        if(w.source_index>=n ||
           ustar[w.source_index]!=mixed.comp_third_ustar_mps[w.source_index]||
           !std::isfinite(w.neutral.ustar_mps)||
           !std::isfinite(w.neutral.el_m))
            throw std::logic_error("G57 WATER ordinal/flux malformed");
        ustar[w.source_index]=w.neutral.ustar_mps;
        el[w.source_index]=w.neutral.el_m;
    }
    G57FirstHour43Real out;
    out.end=mixed.end;
    out.source_land=6907;out.source_water=63;
    auto emit=[&](std::string label,std::vector<float> data) {
        if(label.size()!=8||data.size()!=n)
            throw std::invalid_argument("G57 wrong source label/REAL4 grid extent");
        for(float x:data)
            if(!std::isfinite(x)||x==9999.f)
                throw std::invalid_argument("G57 missing/nonfinite real P6F quantity");
        out.fields.emplace_back(std::move(label),std::move(data));
    };
    auto plane=[&](const std::vector<float>& src,std::size_t level) {
        if((level+1)*n>src.size())throw std::out_of_range("G57 source plane");
        return std::vector<float>(src.begin()+level*n,src.begin()+(level+1)*n);
    };
    auto level_label=[](const char* prefix,int k) {
        return std::string(prefix)+"  "+std::to_string(k);
    };
    for(int k=1;k<=9;++k) {
        emit(level_label("U-LEV",k),plane(g24.wind.u_mps,k-1));
        emit(level_label("V-LEV",k),plane(g24.wind.v_mps,k-1));
        // Original WFACE(K) is G24 array's upper face K+1.
        emit(level_label("WFACE",k),plane(g24.wind.w_face_mps,k));
    }
    for(int k=1;k<=9;++k)
        emit(level_label("T-LEV",k),plane(temp.temperature_k,k-1));
    // The INTEGER fields IPGT and IRH are deliberately NOT faked.
    emit("USTAR   ",std::move(ustar));
    emit("ZI      ",mixed.zi_after_avemix_m);
    emit("EL      ",std::move(el));
    emit("WSTAR   ",wstar.wstar_mps);
    emit("TEMPK   ",mixed.comp_third_heat_k);
    emit("RHO     ",mixed.comp_third_density_kgm3);
    emit("QSW     ",mixed.comp_third_shortwave_wm2);
    if(out.fields.size()!=43)
        throw std::logic_error("G57 exactly 43 source-real P6F records required");
    out.source_firsthour_43real_only=true;
    return out;
}
} // namespace cteas::calmet::p6g
