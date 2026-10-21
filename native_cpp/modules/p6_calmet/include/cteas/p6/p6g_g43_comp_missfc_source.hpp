#pragma once
// S4-R1c2: source-exact original COMP MISSFC reference only.
// The original P5 sparse SURF.DAT / raw hourly arrays are IMMUTABLE.
// Source CALMET COMP L3986 calls MISSFC before DIAGNO L4511, and
// MISSFC L9762-10000 reconstructs only ceiling, cloud, temperature,
// humidity, and station pressure from nearest valid ORIGINAL site.
// Never fill wind (WS/WD) or precipitation code; no G14 production.
#include "cteas/p6/p6g_g41_real_water_first_hour_source.hpp"
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
enum class G43MissfcField : std::size_t {
    Ceiling=0,Cloud=1,Temperature=2,Humidity=3,Pressure=4
};
struct G43OriginalMissfcHour {
    SurfaceHour original_raw,original_comp_resolved;
    // Original source station ordinal (1-based), or itself for valid
    // observations. -1 never allowed after an accepted source MISSFC.
    std::array<std::vector<int>,5> donor_surface_ordinal;
    std::array<std::size_t,5> missing_repaired_count{};
    std::vector<float> original_otempk_before_replacement;
    bool source_comp_missfc_complete=false;
    bool G14_G26_production_accepted=false;
};
inline G43OriginalMissfcHour g43_original_comp_missfc_source_only(
    const G41SelectedNoowWaterFirstHourSource& source,
    const SurfaceHour& hour,bool explicitly_test_only) {
    if(!explicitly_test_only||source.g14_g26_production_ready||
       source.g24_native_final_wind_ready||
       source.source.stations.surface.empty()||
       (g18c1_source_integer(source.source.original_metinp,"ICLOUD")!=0 &&
        g18c1_source_integer(source.source.original_metinp,"ICLOUD")!=1)||
       source.surface_controls.source.itprog!=0||
       hour.end-hour.start!=std::chrono::hours{1})
        throw std::invalid_argument(
            "G43 original COMP MISSFC requires selected observed MCLOUD=1/ITPROG=0");
    const auto& sites=source.source.stations.surface;
    const auto count=sites.size();
    if(hour.by_station.size()!=count)
        throw std::invalid_argument("G43 mismatched original station count");
    bool source_hour=false;
    for(const auto& recorded:source.source.surface.hourly)
        if(&hour==&recorded){source_hour=true;break;}
    if(!source_hour)
        throw std::invalid_argument("G43 refuses foreign/forged source hour");
    G43OriginalMissfcHour result;
    result.original_raw=hour;
    result.original_comp_resolved=hour;
    for(std::size_t f=0;f<5;++f) {
        result.donor_surface_ordinal[f].reserve(count);
        for(std::size_t i=0;i<count;++i)
            result.donor_surface_ordinal[f].push_back(static_cast<int>(i+1));
    }
    for(const auto& obs:hour.by_station)
        result.original_otempk_before_replacement.push_back(obs.temperature_k);
    // CALMET CMPD2 L3427-3456 uses REAL*4 squared local distances,
    // followed by RREPLAC/IREPLAC strict '<' and original station-order ties.
    // All valid-source candidate arrays are captured BEFORE ANY repair:
    // original MISSFC stores OTEMPK, OPRES, etc. before its outer site loop.
    const auto nearest=[&](std::size_t dest,auto usable)->int {
        float distance=1.e38f;
        int donor=-1;
        for(std::size_t j=0;j<count;++j) {
            if(!usable(hour.by_station[j]))continue;
            const float dx=sites[j].local_x_m-sites[dest].local_x_m;
            const float dy=sites[j].local_y_m-sites[dest].local_y_m;
            const float d2=dx*dx+dy*dy;
            if(!std::isfinite(d2))throw std::invalid_argument(
                "G43 nonfinite source station CMPD2");
            if(d2<distance){distance=d2;donor=static_cast<int>(j);}
        }
        if(donor<0)
            throw std::invalid_argument(
                "G43 original MISSFC all surface stations missing field");
        return donor;
    };
    // Keep five fields source-typed, and all non-selected weather variables
    // untouched. This is NOT P5 data imputation; only a detached copy of
    // the physical CALMET COMP hour is reconstructed.
    for(std::size_t i=0;i<count;++i) {
        auto& dst=result.original_comp_resolved.by_station[i];
        const auto& raw=hour.by_station[i];
        const auto fill=[&](G43MissfcField f,auto validity,auto assign) {
            if(validity(raw))return;
            const int j=nearest(i,validity);
            assign(dst,hour.by_station[static_cast<std::size_t>(j)]);
            const auto k=static_cast<std::size_t>(f);
            result.donor_surface_ordinal[k][i]=j+1;
            ++result.missing_repaired_count[k];
        };
        fill(G43MissfcField::Ceiling,
            [](const auto& v){return v.ceiling_valid;},
            [](auto& a,const auto& b){
                a.ceiling_hundreds_ft=b.ceiling_hundreds_ft;
                a.ceiling_valid=b.ceiling_valid;});
        fill(G43MissfcField::Cloud,
            [](const auto& v){return v.cloud_valid;},
            [](auto& a,const auto& b){
                a.opaque_cloud_tenths=b.opaque_cloud_tenths;
                a.cloud_valid=b.cloud_valid;});
        fill(G43MissfcField::Temperature,
            [](const auto& v){return v.temperature_valid;},
            [](auto& a,const auto& b){
                a.temperature_k=b.temperature_k;
                a.temperature_valid=b.temperature_valid;});
        fill(G43MissfcField::Humidity,
            [](const auto& v){return v.humidity_valid;},
            [](auto& a,const auto& b){
                a.humidity_pct=b.humidity_pct;
                a.humidity_valid=b.humidity_valid;});
        fill(G43MissfcField::Pressure,
            [](const auto& v){return v.pressure_valid;},
            [](auto& a,const auto& b){
                a.pressure_mb=b.pressure_mb;
                a.pressure_valid=b.pressure_valid;});
        // Do not write any absent wind, wind direction, precip, or raw
        // original station and clock metadata during COMP's MISSFC.
        if(dst.wind_valid!=raw.wind_valid||
           dst.wind_speed_mps!=raw.wind_speed_mps||
           dst.wind_direction_deg!=raw.wind_direction_deg||
           dst.precipitation_code_valid!=raw.precipitation_code_valid||
           dst.precip_code!=raw.precip_code)
            throw std::logic_error("G43 illegally changed P5 wind/precip");
    }
    result.source_comp_missfc_complete=true;
    return result;
}
} // namespace cteas::calmet::p6g
