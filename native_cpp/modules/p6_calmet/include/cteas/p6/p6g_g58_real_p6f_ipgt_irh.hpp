#pragma once
// S4-R1c8j: genuine NOAA two INTEGER4 P6F outputs; original physical
// P6E pgtstb/surfvar_multistation untouched. Source is raw NOAA + G43
// internal nonwind MISSFC, not original calculated weather fields.
// Mixed WATER: original PGTSTB skips WATER; original SURFVAR LDWAT=1
// and NOWSTA=0 yields RH=100 on WATER (vendor L12926-13005).
// The original output WATER IPGT representation remains a numeric gate:
// use zero-initialized source model state, never infer from an oracle.
#include "cteas/p6/p6g_g57_real_firsthour_p6f_43.hpp"
#include "cteas/p6/p6g_original_surfvar_controls.hpp"
#include "cteas/p6e/pgtstb.hpp"
#include "cteas/p6e/surfvar_multistation.hpp"
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace cteas::calmet::p6g {
struct G58RealP6FIntegers {
    std::chrono::sys_seconds end{};
    std::vector<std::int32_t> ipgt,irh;
    std::size_t source_water=0,source_land=0;
    bool actual_source_firsthour_only=false;
    bool integer_values_original_verified=false;
    bool full45_p6f_accepted=false;
    bool causal_sixhour_accepted=false;
};
inline G58RealP6FIntegers g58_noaa_real_ipgt_irh(
    const G19SourceFilePaths& paths,bool explicitly_test_only) {
    if(!explicitly_test_only)
        throw std::invalid_argument("G58 source IPGT/IRH production unaccepted");
    auto source=g41_load_selected_noow_water_first_hour_source(paths,true);
    const auto g43=g43_original_comp_missfc_source_only(
        source,source.source.surface.hourly.front(),true);
    if(!g43.source_comp_missfc_complete||
       g43.G14_G26_production_accepted)
        throw std::logic_error("G58 true source COMP MISSFC not accepted");
    source.source.surface.hourly.front()=g43.original_comp_resolved;
    auto scheduler=source.source.make_scheduler();
    const auto frame=scheduler.preview_next_hour();
    const auto mixed=g54_real_noaa_firsthour_land_mixht(paths,true);
    const auto wind=g48_real_sparse_stheor_first_hour(
        paths,true,true,true,true);
    if(!wind.firsthour_g24_tail_unverified)
        throw std::logic_error("G58 genuine G24 wind missing");
    const auto& final=*wind.firsthour_g24_tail_unverified;
    const auto& geo=source.source.grid;
    const auto n=static_cast<std::size_t>(geo.nx)*
                 static_cast<std::size_t>(geo.ny);
    if(n!=82U*85U||frame.hour_index!=0||
       frame.input.end!=final.end||
       frame.input.end!=mixed.end||
       source.source.stations.surface.size()!=2||
       source.source.stations.upper.size()!=1||
       mixed.actual_water_count!=63||mixed.actual_land_count!=6907||
       mixed.comp_third_nearest_surface.size()!=n||
       mixed.comp_third_sun_sine.size()!=n||
       final.wind.u_mps.size()!=9*n||
       final.wind.v_mps.size()!=9*n||
       frame.surface.by_station.size()!=2||
       geo.landuse.size()!=n)
        throw std::invalid_argument("G58 physical NOAA PGT/IRH prerequisites absent");
    const auto controls=parse_original_surfvar_controls(
        source.source.original_metinp);
    const int cloud=g18c1_source_integer(
        source.source.original_metinp,"ICLOUD");
    if(controls.iavet!=1||controls.itprog!=0||
       controls.irhprog!=0||controls.npsta!=0||
       controls.irad!=1||(cloud!=0&&cloud!=1)||
       source.source.original_metinp.find("NOWSTA")==
           std::string::npos)
        throw std::invalid_argument("G58 unsupported original observed RH/PGT options");
    p6e::SurfvarMultistationInput humidity;
    humidity.nx=geo.nx;humidity.ny=geo.ny;
    humidity.dgrid_m=geo.grid_km*1000.f;
    humidity.irad=controls.irad;
    humidity.numts=controls.numts;
    humidity.trad_grid=controls.trad_km/geo.grid_km;
    p6e::PgtInput stability;
    stability.nx=geo.nx;stability.ny=geo.ny;
    stability.mcloud=1;
    stability.water_first=geo.iwat1;
    stability.water_last=geo.iwat2;
    stability.landuse=geo.landuse;
    stability.nearest=mixed.comp_third_nearest_surface;
    stability.sinalp=mixed.comp_third_sun_sine;
    stability.ccgrid.assign(n,0.f);
    stability.ceilgrid.assign(n,0);
    stability.u10.assign(final.wind.u_mps.begin(),
                        final.wind.u_mps.begin()+n);
    stability.v10.assign(final.wind.v_mps.begin(),
                        final.wind.v_mps.begin()+n);
    for(std::size_t i=0;i<2;++i) {
        const auto& st=frame.stations.surface[i];
        const auto& obs=frame.surface.by_station[i];
        if(!obs.cloud_valid||!obs.ceiling_valid||
           !obs.temperature_valid||!obs.humidity_valid||
           obs.opaque_cloud_tenths<0||obs.opaque_cloud_tenths>10||
           obs.ceiling_hundreds_ft<0||
           obs.humidity_pct<0||obs.humidity_pct>100)
            throw std::invalid_argument("G58 selected MISSFC source observation incomplete");
        humidity.stations.push_back({
            st.local_x_m,st.local_y_m,
            obs.temperature_k,obs.humidity_pct});
        stability.station_cloud.push_back(obs.opaque_cloud_tenths);
        stability.station_ceil.push_back(obs.ceiling_hundreds_ft);
    }
    const auto land_ipgt=p6e::pgtstb(stability);
    const auto rh=p6e::surfvar_multistation(humidity);
    if(land_ipgt.size()!=n||rh.rh2d_pct.size()!=n)
        throw std::logic_error("G58 shared P6E physics produced wrong extent");
    G58RealP6FIntegers out;
    out.end=frame.input.end;
    out.ipgt.resize(n);out.irh.resize(n);
    for(std::size_t i=0;i<n;++i) {
        const bool water=geo.landuse[i]>=geo.iwat1&&
                         geo.landuse[i]<=geo.iwat2;
        if(water) {
            ++out.source_water;
            if(land_ipgt[i]!=p6e::missing_pgt)
                throw std::logic_error("G58 PGTSTB computed forbidden WATER IPGT");
            // Original common-block beginning source state is zero before
            // PGTSTB skips water. This will be independently checked.
            out.ipgt[i]=0;
            out.irh[i]=100;
        } else {
            ++out.source_land;
            if(land_ipgt[i]<1||land_ipgt[i]>6)
                throw std::logic_error("G58 source LAND PGT invalid");
            out.ipgt[i]=land_ipgt[i];
            out.irh[i]=rh.rh2d_pct[i];
        }
        if(out.irh[i]<0||out.irh[i]>100)
            throw std::logic_error("G58 source IRH outside 0..100");
    }
    if(out.source_water!=63||out.source_land!=6907)
        throw std::logic_error("G58 real original WATER landuse partition drift");
    out.actual_source_firsthour_only=true;
    return out;
}
} // namespace cteas::calmet::p6g
