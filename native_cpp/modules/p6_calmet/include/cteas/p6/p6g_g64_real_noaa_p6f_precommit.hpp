#pragma once
// S4-R1c8v: build a complete source-native G14 stage16 P6F PRECOMMIT
// candidate from the ACTUAL SAME G14 frame and G26B stages12..15.
// Neither G54/G56/G57/G58/G59 nor an original Fortran value supplies
// any meteorological input. Native G59 is used ONLY after this function
// returns for independent parity comparison. Output is not published.
// Scheduler memory and AA/BB/CGAMMA are not advanced in this function.
#include "cteas/p6/p6g_g63_real_noaa_g14_comp_mixht.hpp"
#include "cteas/p6/p6g_g18c6_selected_p6f_dataset.hpp"
#include "cteas/p6/p6g_g18d1_p6f_precommit.hpp"
#include "cteas/p6/p6g_original_surfvar_controls.hpp"
#include "cteas/p6e/pgtstb.hpp"
#include "cteas/p6e/surfvar_multistation.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <initializer_list>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G64RealNoaaP6FPrecommit {
    std::chrono::sys_seconds end{};
    p6::NativeGridMemory candidate_next;
    p6::NativeHourFields candidate_fields;
    cteas::p6f::Calmet21File candidate_dataset;
    std::vector<std::uint8_t> serialized_prepared_only;
    bool actual_g14_stage16_precommit_validated=false;
    bool g14_hour_committed=false;
    bool source_clocks_published=false;
    bool ready_for_next_hour=false;
};

inline G64RealNoaaP6FPrecommit g64_real_noaa_p6f_from_live_g14(
    const MultiHourFrame& frame,
    const G19FileBackedCase& source,
    const G63RealNoaaG14MixhtStage12& mix,
    const G18C1AvemixOutput& ave,
    const std::vector<float>& wstar,
    const std::vector<float>& temp3d,
    bool forensic_only) {
    const auto n=static_cast<std::size_t>(frame.grid.nx)*
                 static_cast<std::size_t>(frame.grid.ny);
    if(!forensic_only||!source.research_noow_water_source_only||
       frame.hour_index!=0||n!=6970||
       frame.grid.nx!=82||frame.grid.ny!=85||
       frame.stations.surface.size()!=2||
       frame.stations.upper.size()!=1||
       source.source_water_cells.size()!=63||
       source.original_metinp.empty()||
       frame.input.end!=mix.end||frame.surface.end!=mix.end||
       frame.next.zi_m!=frame.previous.zi_m||
       frame.next.ziconv_m!=frame.previous.ziconv_m||
       frame.next.dptt_k!=frame.previous.dptt_k||
       frame.fields.u_mps.size()!=9*n||
       frame.fields.v_mps.size()!=9*n||
       frame.fields.w_face_mps.size()!=10*n||
       temp3d.size()!=9*n||
       wstar.size()!=n||
       ave.zi_m.size()!=n||ave.ziconv_m.size()!=n||
       mix.dptt_before_avemix_k.size()!=n||
       mix.comp_third_temperature_k.size()!=n||
       mix.comp_third_density_kgm3.size()!=n||
       mix.comp_third_qh_wm2.size()!=n||
       mix.comp_third_ustar_mps.size()!=n||
       mix.p6f_water_reconciled_ustar_mps.size()!=n||
       mix.p6f_water_reconciled_el_m.size()!=n||
       mix.comp_third_el_m.size()!=n||
       mix.comp_third_shortwave_wm2.size()!=n||
       mix.comp_third_sun_sine.size()!=n||
       mix.comp_third_nearest_surface.size()!=n)
        throw std::invalid_argument(
            "G64 true current-hour P6F requires all 16 authentic G14 native stages");

    auto current_memory=frame.previous;
    current_memory.zi_m=ave.zi_m;
    current_memory.ziconv_m=ave.ziconv_m;
    current_memory.dptt_k=mix.dptt_before_avemix_k;

    p6::NativeHourFields fields;
    fields.u_mps=frame.fields.u_mps;
    fields.v_mps=frame.fields.v_mps;
    fields.w_face_mps=frame.fields.w_face_mps;
    fields.temperature_k=temp3d;
    // Preserve physical COMP MIXHT candidate separately; original P6F
    // publishes source-native neutral-water USTAR and EL at the 63 WATER
    // cells, as does independent G57. Never overwrite the G54 audit arrays.
    fields.ustar_mps=mix.p6f_water_reconciled_ustar_mps;
    fields.el_m=mix.p6f_water_reconciled_el_m;
    fields.qh_wm2=mix.comp_third_qh_wm2;
    fields.wstar_mps=wstar;
    for(const auto* values:
        std::initializer_list<const std::vector<float>*>{
            &current_memory.zi_m,&current_memory.ziconv_m,
            &current_memory.dptt_k,&fields.u_mps,&fields.v_mps,
            &fields.w_face_mps,&fields.temperature_k,&fields.ustar_mps,
            &fields.el_m,&fields.qh_wm2,&fields.wstar_mps,
            &mix.comp_third_temperature_k,&mix.comp_third_density_kgm3,
            &mix.comp_third_shortwave_wm2})
        for(const float v:*values)
            if(!std::isfinite(v)||v==9999.f)
                throw std::invalid_argument(
                    "G64 cannot publish missing/nonfinite native CALMET field");

    const auto surfvar=parse_original_surfvar_controls(source.original_metinp);
    const auto icloud=g18c1_source_integer(source.original_metinp,"ICLOUD");
    if(surfvar.iavet!=1||surfvar.itprog!=0||
       surfvar.irhprog!=0||surfvar.npsta!=0||
       surfvar.irad!=1||(icloud!=0&&icloud!=1))
        throw std::invalid_argument("G64 unsupported genuine NOAA IPGT/IRH controls");
    p6e::PgtInput pgt;
    pgt.nx=static_cast<std::size_t>(frame.grid.nx);
    pgt.ny=static_cast<std::size_t>(frame.grid.ny);
    pgt.mcloud=1;  // original READCF ICLOUD=0/1 maps to MCLOUD=1
    pgt.water_first=frame.grid.iwat1;
    pgt.water_last=frame.grid.iwat2;
    pgt.landuse=frame.grid.landuse;
    pgt.nearest=mix.comp_third_nearest_surface;
    pgt.sinalp=mix.comp_third_sun_sine;
    pgt.ccgrid.assign(n,0.f);
    pgt.ceilgrid.assign(n,0);
    pgt.u10.assign(fields.u_mps.begin(),fields.u_mps.begin()+n);
    pgt.v10.assign(fields.v_mps.begin(),fields.v_mps.begin()+n);
    p6e::SurfvarMultistationInput rh;
    rh.nx=pgt.nx;rh.ny=pgt.ny;
    rh.dgrid_m=frame.grid.grid_km*1000.f;
    rh.irad=surfvar.irad;
    rh.numts=surfvar.numts;
    rh.trad_grid=surfvar.trad_km/frame.grid.grid_km;
    G18C5SelectedHourFields selected;
    selected.end=frame.input.end;
    for(std::size_t i=0;i<frame.stations.surface.size();++i){
        const auto& st=frame.stations.surface[i];
        const auto& obs=frame.surface.by_station.at(i);
        if(st.id<=0||
           !std::isfinite(st.local_x_m)||!std::isfinite(st.local_y_m)||
           !obs.cloud_valid||!obs.ceiling_valid||
           obs.opaque_cloud_tenths<0||obs.opaque_cloud_tenths>10||
           obs.ceiling_hundreds_ft<0||
           (obs.humidity_valid&&(obs.humidity_pct<0||obs.humidity_pct>100)))
            throw std::invalid_argument(
                "G64 source P5 repaired nonwind cloud/ceiling/RH invalid");
        selected.station_ids.push_back(st.id);
        pgt.station_cloud.push_back(obs.opaque_cloud_tenths);
        pgt.station_ceil.push_back(obs.ceiling_hundreds_ft);
        rh.stations.push_back({st.local_x_m,st.local_y_m,
            obs.temperature_valid?obs.temperature_k:9999.f,
            obs.humidity_valid?obs.humidity_pct:9999});
    }
    auto stability=p6e::pgtstb(pgt);
    const auto humidity=p6e::surfvar_multistation(rh);
    if(stability.size()!=n||humidity.rh2d_pct.size()!=n)
        throw std::logic_error("G64 source-native PGT/RH incomplete");
    std::size_t nl=0,nw=0;
    for(std::size_t i=0;i<n;++i){
        const auto water=frame.grid.landuse[i]>=frame.grid.iwat1&&
                         frame.grid.landuse[i]<=frame.grid.iwat2;
        if(water){
            if(stability[i]!=p6e::missing_pgt)
                throw std::logic_error("G64 original WATER PGT should be missing before neutral write");
            stability[i]=4;
            ++nw;
        }else{
            if(stability[i]<1||stability[i]>6)
                throw std::logic_error("G64 original LAND PGT invalid");
            ++nl;
        }
        if(humidity.rh2d_pct[i]<0||humidity.rh2d_pct[i]>100)
            throw std::logic_error("G64 original P6F RH out of range");
    }
    if(nl!=6907||nw!=63)
        throw std::logic_error("G64 original NOAA WATER ordinals drifted");
    selected.integer.emplace("IPGT    ",
        std::vector<std::int32_t>(stability.begin(),stability.end()));
    selected.integer.emplace("IRH     ",
        std::vector<std::int32_t>(
            humidity.rh2d_pct.begin(),humidity.rh2d_pct.end()));
    const auto plane=[n](const std::vector<float>& v,std::size_t k) {
        if((k+1)*n>v.size())throw std::out_of_range("G64 hourly plane");
        return std::vector<float>(v.begin()+k*n,v.begin()+(k+1)*n);
    };
    for(int k=1;k<=9;++k){
        selected.real.emplace(g18c5_level_label("U-LEV",k),
                              plane(fields.u_mps,k-1));
        selected.real.emplace(g18c5_level_label("V-LEV",k),
                              plane(fields.v_mps,k-1));
        selected.real.emplace(g18c5_level_label("WFACE",k),
                              plane(fields.w_face_mps,k));
        selected.real.emplace(g18c5_level_label("T-LEV",k),
                              plane(fields.temperature_k,k-1));
    }
    selected.real.emplace("USTAR   ",fields.ustar_mps);
    selected.real.emplace("ZI      ",current_memory.zi_m);
    selected.real.emplace("EL      ",fields.el_m);
    selected.real.emplace("WSTAR   ",fields.wstar_mps);
    selected.real.emplace("TEMPK   ",mix.comp_third_temperature_k);
    selected.real.emplace("RHO     ",mix.comp_third_density_kgm3);
    selected.real.emplace("QSW     ",mix.comp_third_shortwave_wm2);
    if(selected.real.size()!=43||selected.integer.size()!=2)
        throw std::logic_error("G64 native full P6F must have exact 45 fields");
    for(const auto& item:selected.real)
        if(item.first.size()!=8||item.second.size()!=n)
            throw std::logic_error("G64 incorrect P6F REAL4 field extent");
    const auto nears=source_setcom_nears(frame.grid,frame.stations);
    auto dataset=g18c6_selected_one_hour_dataset(
        frame,selected,nears,source.original_metinp,true,false,true);
    // G18D1 checks legal 45 records against the in-flight G14 frame,
    // including all source wind/temperature/previous COMP arrays.
    // Local copied frame is never published and never alters scheduler.
    auto local=frame;
    local.next=current_memory;
    local.fields=fields;
    const auto prepared=g18d1_validate_p6f_precommit(local,dataset);
    if(prepared.empty()||frame.next.zi_m!=frame.previous.zi_m||
       frame.next.ziconv_m!=frame.previous.ziconv_m||
       frame.next.dptt_k!=frame.previous.dptt_k)
        throw std::logic_error("G64 precommit mutated G14 or emitted empty bytes");
    G64RealNoaaP6FPrecommit result;
    result.end=frame.input.end;
    result.candidate_next=std::move(current_memory);
    result.candidate_fields=std::move(fields);
    result.candidate_dataset=std::move(dataset);
    result.serialized_prepared_only=prepared;
    result.actual_g14_stage16_precommit_validated=true;
    return result;
}
} // namespace cteas::calmet::p6g
