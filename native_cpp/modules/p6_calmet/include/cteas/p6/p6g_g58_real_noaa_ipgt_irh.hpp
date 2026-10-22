#pragma once
// S4-R1c8j: source-native two INTEGER4 P6F fields for authentic
// mixed LAND/WATER NOAA 2SS/1US. Uses frozen P6E PGTSTB and
// SURFVAR observed RH interpolation. Original Fortran outputs are
// never input; no six-hour G14 nor 45-field writer authority.
#include "cteas/p6/p6g_g57_real_firsthour_p6f_43.hpp"
#include "cteas/p6/p6g_original_surfvar_controls.hpp"
#include "cteas/p6e/pgtstb.hpp"
#include "cteas/p6e/surfvar_multistation.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <vector>
namespace cteas::calmet::p6g {
struct G58RealNoaaIntegerOutput {
    std::chrono::sys_seconds end{};
    std::vector<std::int32_t> ipgt,irh;
    std::size_t original_land=0,original_water=0;
    bool source_only_two_integer_fields=false;
    bool p6f_45field_file_ready=false;
    bool g14_six_hour_causal_ready=false;
};
inline G58RealNoaaIntegerOutput g58_source_noaa_p6f_ipgt_irh(
    const G19SourceFilePaths& paths,bool explicitly_test_only) {
    if(!explicitly_test_only)
        throw std::invalid_argument("G58 full P6F production denied");
    // G57 is source-owned and has passed an external, independent
    // 43-REAL output comparison; do not fake missing integer values.
    const auto physical=g57_noaa_real_43_output_fields(paths,true);
    const auto mixed=g54_real_noaa_firsthour_land_mixht(paths,true);
    auto src=g41_load_selected_noow_water_first_hour_source(paths,true);
    const auto raw=src.source.surface.hourly.front();
    const auto resolved=g43_original_comp_missfc_source_only(src,raw,true);
    if(!resolved.source_comp_missfc_complete||
       resolved.G14_G26_production_accepted||
       raw.by_station.size()!=2)
        throw std::invalid_argument("G58 genuine sparse original COMP observations missing");
    for(std::size_t st=0;st<raw.by_station.size();++st)
        if(raw.by_station[st].wind_valid!=
           resolved.original_comp_resolved.by_station[st].wind_valid||
           raw.by_station[st].wind_speed_mps!=
           resolved.original_comp_resolved.by_station[st].wind_speed_mps)
            throw std::invalid_argument("G58 must not invent missing station wind");
    src.source.surface.hourly.front()=resolved.original_comp_resolved;
    auto schedule=src.source.make_scheduler();
    const auto frame=schedule.preview_next_hour();
    const auto& grid=src.source.grid;
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    const auto n=nx*ny;
    if(!physical.source_firsthour_43real_only||
       physical.g26_45field_ready||
       physical.original_ipgt_irh_verified||
       physical.fields.size()!=43||
       physical.fields[0].first!="U-LEV  1"||
       physical.fields[1].first!="V-LEV  1"||
       physical.fields[0].second.size()!=n||
       physical.fields[1].second.size()!=n||
       physical.end!=frame.input.end||
       mixed.end!=frame.input.end||
       mixed.comp_third_nearest_surface.size()!=n||
       mixed.comp_third_sun_sine.size()!=n||
       mixed.actual_water_count!=63||mixed.actual_land_count!=6907||
       frame.stations.surface.size()!=2||
       frame.stations.upper.size()!=1||
       frame.surface.by_station.size()!=2||
       schedule.completed_hours()!=0||frame.hour_index!=0)
        throw std::invalid_argument("G58 original source COMP provenance incomplete");
    const auto controls=parse_original_surfvar_controls(
        src.source.original_metinp);
    const int icloud=g18c1_source_integer(
        src.source.original_metinp,"ICLOUD");
    if(controls.iavet!=1||controls.itprog!=0||
       controls.irhprog!=0||controls.npsta!=0||
       controls.irad!=1||(icloud!=0&&icloud!=1))
        throw std::invalid_argument("G58 unsupported original source PGT/RH mode");
    p6e::PgtInput pgt;
    pgt.nx=nx;pgt.ny=ny;
    pgt.mcloud=1; // Original READCF ICLOUD 0/1 => MCLOUD=1
    pgt.water_first=grid.iwat1;pgt.water_last=grid.iwat2;
    pgt.landuse=grid.landuse;
    pgt.nearest=mixed.comp_third_nearest_surface;
    pgt.sinalp=mixed.comp_third_sun_sine;
    pgt.ccgrid.assign(n,0.f);
    pgt.ceilgrid.assign(n,0);
    pgt.u10=physical.fields[0].second;
    pgt.v10=physical.fields[1].second;
    p6e::SurfvarMultistationInput rh;
    rh.nx=nx;rh.ny=ny;
    rh.dgrid_m=grid.grid_km*1000.f;
    rh.irad=controls.irad;
    rh.numts=controls.numts;
    rh.trad_grid=controls.trad_km/grid.grid_km;
    for(std::size_t idx=0;idx<2;++idx) {
        const auto& st=frame.stations.surface[idx];
        const auto& obs=frame.surface.by_station[idx];
        if(st.id<=0||!std::isfinite(st.local_x_m)||
           !std::isfinite(st.local_y_m)||
           !obs.cloud_valid||!obs.ceiling_valid||
           obs.opaque_cloud_tenths<0||obs.opaque_cloud_tenths>10||
           obs.ceiling_hundreds_ft<0||
           (obs.humidity_valid&&(obs.humidity_pct<0||obs.humidity_pct>100)))
            throw std::invalid_argument("G58 original SS cloud/RH not source-valid");
        rh.stations.push_back({
            st.local_x_m,st.local_y_m,
            obs.temperature_valid?obs.temperature_k:9999.f,
            obs.humidity_valid?obs.humidity_pct:9999
        });
        pgt.station_cloud.push_back(obs.opaque_cloud_tenths);
        pgt.station_ceil.push_back(obs.ceiling_hundreds_ft);
    }
    auto stability=p6e::pgtstb(pgt);
    auto humidity=p6e::surfvar_multistation(rh);
    if(stability.size()!=n||humidity.rh2d_pct.size()!=n)
        throw std::logic_error("G58 incomplete original integer fields");
    // Original source-selected NOWSTA=0 WATER neutral branch assigns
    // PGT D (4) during WATER; PGTSTB intentionally skips WATER.
    // G53 already independently verifies these 63 genuine WATER states.
    std::size_t nw=0,nl=0;
    for(std::size_t k=0;k<n;++k) {
        if(grid.landuse[k]>=grid.iwat1&&grid.landuse[k]<=grid.iwat2) {
            if(stability[k]!=p6e::missing_pgt)
                throw std::logic_error("G58 WATER spuriously classified as LAND");
            stability[k]=4;
            // Original SURFVAR L12926-L13005 LDWAT=1 uses only
            // overwater RH stations at WATER cells; NOWSTA=0 means
            // zero eligible stations, assigning WATER RH=100 exactly.
            humidity.rh2d_pct[k]=100;
            ++nw;
        }else{
            if(stability[k]<1||stability[k]>6)
                throw std::logic_error("G58 invalid original LAND PGT");
            ++nl;
        }
        if(humidity.rh2d_pct[k]<0||humidity.rh2d_pct[k]>100)
            throw std::logic_error("G58 invalid original interpolated humidity");
    }
    if(nw!=63||nl!=6907)
        throw std::logic_error("G58 changed source original GEO partition");
    G58RealNoaaIntegerOutput out;
    out.end=frame.input.end;
    out.ipgt.assign(stability.begin(),stability.end());
    out.irh.assign(humidity.rh2d_pct.begin(),humidity.rh2d_pct.end());
    out.original_land=nl;out.original_water=nw;
    out.source_only_two_integer_fields=true;
    return out;
}
} // namespace cteas::calmet::p6g
