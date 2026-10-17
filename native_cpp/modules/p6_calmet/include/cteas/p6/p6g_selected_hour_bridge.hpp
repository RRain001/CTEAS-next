#pragma once
// P6G G10 selected-source DIAGNO tail audit after G9 multi-station WIND1.
// Source-backed SIMILT (surface neutral profile), VERTAV/PREPDI (upper
// profiles) and INTER2 (all stations) operate for a single UTC hour.
// G9 WIND1 selected route has direct extracted-original Fortran field parity.
// G10 adds an explicitly marked synthetic-identity DIAGNO tail audit.
// No real FRADJ/SLOPE, P6E or P6F acceptance claim.
#include "cteas/p6/observation_input_contract.hpp"
#include "cteas/p6/p6g_original_wind_controls.hpp"
#include "cteas/p6/inter2_selected.hpp"
#include "cteas/p6/diagno_segment.hpp"
#include "cteas/p6/p6g_terrain_hour.hpp"
#include "cteas/p6/p6g_multi_wind1_firstguess.hpp"
#include "cteas/p6/similt_profile.hpp"
#include "cteas/p6/upper_hourly_wind.hpp"
#include "cteas/p6/vertical_wind_average.hpp"
#include "cteas/p6e/coordlib_pj09z0.hpp"
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
namespace p6 = cteas::calmet::p6;

struct PreparedUpper {
    std::vector<p6::Upper2022> profiles;
    std::vector<std::vector<std::vector<p6::LayerWind>>> layers;
};
inline PreparedUpper prepare_upper_original_selected(
    const std::vector<UpperSeries>& upper,
    const std::vector<float>& zface) {
    if(upper.empty()||zface.size()!=10)
        throw std::invalid_argument("G8 selected bridge supports 9 source-proven layers");
    PreparedUpper result;
    for(const auto& station:upper) {
        p6::Upper2022 u;
        u.station_id=station.station_id;
        u.pstop_hpa=station.pstop_hpa;
        u.soundings=station.soundings;
        std::vector<std::vector<p6::LayerWind>> stations_layers;
        stations_layers.reserve(u.soundings.size());
        for(const auto& sounding:u.soundings)
            stations_layers.push_back(p6::calmet_vertav(sounding,zface));
        result.profiles.push_back(std::move(u));
        result.layers.push_back(std::move(stations_layers));
    }
    return result;
}

struct SelectedBridgeGrid {
    int nx=0,ny=0;
    float spacing_km=0.0f;
    int utm_zone=0;
    char hemisphere='N';
    std::array<float,10> zface_m{};
    std::vector<int> landuse; // Read from P6G READGE GEO.DAT, not hardcoded.
    // Intentionally audit-only: the real post-WIND1 FRADJ/SLOPE/terrain
    // processing has NOT been run, so the initial WIND1 field is passed
    // as an explicit identity substitute to DIAGNO's selected tail.
    bool synthetic_identity_diagno_tail=false;
    std::vector<int> smoothing_passes{}; // 9 source SMOOTH passes, 0..1000
    // Mutually exclusive with synthetic_identity_diagno_tail. Requires
    // explicitly passed, time-stamped test thermodynamics per input hour.
    bool source_terrain_diagno_tail=false;
    std::optional<TerrainStaticG11> terrain{};
    // Mandatory for any selected-source wind computation: read from the
    // same original CALMET met.inp that declares SS/US and numerical grid.
    std::optional<OriginalWindControls> source_controls{};
};
struct SelectedBridgeHour {
    std::chrono::sys_seconds end{};
    float center_u_mps{},center_v_mps{};
    float upper_u_mps{},upper_v_mps{};
    float firstguess_center_u_mps{},firstguess_center_v_mps{};
    std::size_t observed_contributions{};
    float final_center_u_mps{},final_center_v_mps{},top_center_w_mps{};
    std::size_t nonzero_w_faces{};
    bool selected_tail_exercised=false;
    bool original_terrain_kernels_exercised=false;
    std::size_t fradj_changed_cells{},slope_changed_cells{};
};
inline SelectedBridgeHour selected_multisite_hour(
    const StationSet& deck,const SurfaceHour& surface,
    const InputHour& input,const PreparedUpper& prepared,
    const SelectedBridgeGrid& grid,
    const TerrainHourG11* thermal_hour=nullptr) {
    if(grid.nx<2||grid.ny<2||grid.nx>400||grid.ny>400||
       grid.spacing_km<=0.f||!std::isfinite(grid.spacing_km)||
       grid.utm_zone<1||grid.utm_zone>60||grid.hemisphere!='N'||
       surface.end!=input.end||surface.by_station.size()!=deck.surface.size()||
       prepared.profiles.size()!=deck.upper.size()||
       prepared.layers.size()!=deck.upper.size()||
       input.upper.size()!=deck.upper.size()||
       grid.landuse.size()!=static_cast<std::size_t>(grid.nx)*
                            static_cast<std::size_t>(grid.ny))
        throw std::invalid_argument("G8 bridge source-hour/grid/array mismatch");
    if(!grid.source_controls)
        throw std::invalid_argument("G15 wind bridge refuses missing met.inp numerical controls");
    const auto& controls=*grid.source_controls;
    if(grid.zface_m!=controls.zface_m)
        throw std::invalid_argument(
            "G15 stage ZFACE not equal to original met.inp vertical grid");
    if(grid.synthetic_identity_diagno_tail&&grid.source_terrain_diagno_tail)
        throw std::invalid_argument("G11 identity and terrain DIAGNO audit modes conflict");
    if((thermal_hour!=nullptr)!=grid.source_terrain_diagno_tail ||
       (grid.source_terrain_diagno_tail&&!grid.terrain) ||
       (thermal_hour!=nullptr&&thermal_hour->end!=input.end))
        throw std::invalid_argument("G11 original terrain needs explicit GEO and hourly thermal input");
    for(std::size_t i=1;i<grid.zface_m.size();++i)
        if(!(grid.zface_m[i]>grid.zface_m[i-1]))
            throw std::invalid_argument("G8 invalid ZFACE");
    const std::size_t stations=deck.surface.size()+deck.upper.size();
    if(stations<2||stations>479)
        throw std::invalid_argument("G8 original INTER2 station count unsupported");
    p6::Inter2SelectedInput inter;
    inter.nx=grid.nx;inter.ny=grid.ny;inter.nz=9;
    inter.nstations=static_cast<int>(stations);
    inter.dx_m=grid.spacing_km*1000.f;
    inter.dy_m=inter.dx_m;
    // Numeric influence weights and station-selection limits from the
    // SAME original source met.inp, never G8/G10 experimental constants.
    inter.rmin_km=controls.rmin_km;
    inter.rmax1_km=controls.rmax1_km;
    inter.rmax2_km=controls.rmax2_km;
    inter.rmax3_km=controls.rmax3_km;
    inter.r1_km=controls.r1_km;inter.r2_km=controls.r2_km;
    inter.lvary=controls.lvary;
    inter.nintrp_per_layer.resize(9);
    for(std::size_t k=0;k<9;++k)
        inter.nintrp_per_layer[k]=std::min(
            controls.nintr2[k],inter.nstations);
    const std::size_t cells=static_cast<std::size_t>(grid.nx)*
                            static_cast<std::size_t>(grid.ny);
    inter.landuse=grid.landuse;
    inter.station_x_km.reserve(stations);
    inter.station_y_km.reserve(stations);
    for(const auto& s:deck.surface){
        inter.station_x_km.push_back(s.local_x_m*0.001f);
        inter.station_y_km.push_back(s.local_y_m*0.001f);
    }
    for(const auto& s:deck.upper){
        inter.station_x_km.push_back(s.local_x_m*0.001f);
        inter.station_y_km.push_back(s.local_y_m*0.001f);
    }
    const std::size_t levels=9;
    std::vector<float> su(levels*stations,0.f),sv(levels*stations,0.f);
    std::vector<float> surface_speeds;
    surface_speeds.reserve(deck.surface.size());
    const auto projection=cteas::p6e::utm_north_projection(grid.utm_zone);
    for(std::size_t s=0;s<deck.surface.size();++s){
        const auto& o=surface.by_station[s];
        if(!o.wind_valid)
            throw std::invalid_argument("G8 selected test needs real SURF wind, not invented");
        surface_speeds.push_back(o.wind_speed_mps);
        const float rad=0.0174533f*o.wind_direction_deg;
        const float u=-o.wind_speed_mps*std::sin(rad);
        const float v=-o.wind_speed_mps*std::cos(rad);
        p6::SimiltProfileInput profile;
        // Original READCF/GLOBE uses the deck's absolute REAL*4 UTM km,
        // not case centre latitude or independently rounded CSV metadata.
        double lat=0.,lon=0.;
        cteas::p6e::utm_north_to_latlon_deg(
            projection,
            static_cast<double>(deck.surface[s].utm_x_km)*1000.0,
            static_cast<double>(deck.surface[s].utm_y_km)*1000.0,
            lat,lon);
        if(!std::isfinite(lat)||!std::isfinite(lon)||std::abs(lat)>90.)
            throw std::invalid_argument("G8 station GLOBE projection invalid");
        profile.station_lat_deg=static_cast<float>(lat);
        profile.anemometer_height_m=deck.surface[s].anemometer_height_m;
        profile.roughness_m=0.1f;
        profile.anemometer_u_mps=u;profile.anemometer_v_mps=v;
        profile.obukhov_length_m=10000.f;
        profile.mixing_height_m=10000.f;
        profile.minimum_mixing_height_m=0.f;
        profile.zface_m=grid.zface_m;
        const auto winds=p6::original_similt_profile(profile);
        if(winds.levels_filled!=levels)
            throw std::invalid_argument("G8 surface source profile not complete");
        for(std::size_t k=0;k<levels;++k){
            su[k*stations+s]=winds.u_mps[k];
            sv[k*stations+s]=winds.v_mps[k];
        }
    }
    for(std::size_t s=0;s<deck.upper.size();++s){
        const auto& station=prepared.profiles[s];
        const auto hr=p6::calmet_prepdi_hour(
            station,input.end,prepared.layers[s]);
        const auto& bracket=input.upper[s];
        if(hr.prior_sounding!=bracket.earlier||
           hr.following_sounding!=bracket.later||
           hr.past_seconds!=bracket.past_seconds||
           hr.to_go_seconds!=bracket.future_seconds)
            throw std::invalid_argument("G8 COMP/PREPDI station bracket disagreement");
        const std::size_t index=deck.surface.size()+s;
        for(std::size_t k=0;k<levels;++k){
            su[k*stations+index]=hr.winds.at(k).u_mps;
            sv[k*stations+index]=hr.winds.at(k).v_mps;
        }
    }
    // G9 joins the candidate multi-SS/US WIND1 to the already selected
    // objective analysis. BIAS=0, ICALM=0 remain explicitly controlled.
    // Actual CALMET BIAS/radius/terrain data still require parity acceptance.
    Wind1MultiInput wind;
    wind.nx=grid.nx;wind.ny=grid.ny;wind.nz=static_cast<int>(levels);
    wind.spacing_m=grid.spacing_km*1000.f;
    wind.surface_count=static_cast<int>(deck.surface.size());
    wind.upper_count=static_cast<int>(deck.upper.size());
    wind.surface_speeds_mps=std::move(surface_speeds);
    wind.station_u_mps=su;
    wind.station_v_mps=sv;
    wind.present.assign(levels*stations,1);
    wind.icalm=controls.icalm;
    wind.vertical_bias.assign(controls.bias.begin(),controls.bias.end());
    wind.station_x_m.reserve(stations);
    wind.station_y_m.reserve(stations);
    for(const auto& st:deck.surface){
        wind.station_x_m.push_back(st.local_x_m);
        wind.station_y_m.push_back(st.local_y_m);
    }
    for(const auto& st:deck.upper){
        wind.station_x_m.push_back(st.local_x_m);
        wind.station_y_m.push_back(st.local_y_m);
    }
    const auto guess=multi_station_wind1_firstguess(wind);
    // Original DIAGNO post-WIND1 stage order, *before* INTER2, and
    // L5748 WINDBC records these corrected winds, never blended U/V.
    std::vector<float> prepared_u=guess.u_mps,prepared_v=guess.v_mps;
    TerrainCorrectionG11 terrain_result;
    if(grid.source_terrain_diagno_tail) {
        const std::vector<float> zface(grid.zface_m.begin(),grid.zface_m.end());
        terrain_result=apply_g11_terrain_after_wind1(
            *grid.terrain,*thermal_hour,zface,
            p6::WindUV{std::move(prepared_u),std::move(prepared_v)});
        prepared_u=std::move(terrain_result.field.u);
        prepared_v=std::move(terrain_result.field.v);
    }
    inter.observation_weight.assign(cells*levels,1.f);
    inter.step1_mps=prepared_u;
    inter.station_component_mps=std::move(su);
    const auto u=p6::original_inter2_selected(inter);
    inter.step1_mps=prepared_v;
    inter.station_component_mps=std::move(sv);
    const auto v=p6::original_inter2_selected(inter);
    // Save the original WIND1 step-one boundary snapshot before INTER2.
    // In real CALMET this snapshot must instead come from post-FRADJ/SLOPE
    // UG/VG. Explicit synthetic-identity audit only; no hidden fallback.
    p6::FinalWindSegment tail;
    if(grid.synthetic_identity_diagno_tail||grid.source_terrain_diagno_tail) {
        if(grid.smoothing_passes.size()!=levels||
           !std::equal(grid.smoothing_passes.begin(),grid.smoothing_passes.end(),
                       controls.nsmth.begin()))
            throw std::invalid_argument(
                "G15 SMOOTH passes must agree with original met.inp NSMTH");
        p6::SmoothInput sm;
        sm.nx=grid.nx;sm.ny=grid.ny;sm.nz=static_cast<int>(levels);
        sm.lake_breeze=false;
        sm.passes_per_layer=grid.smoothing_passes;
        sm.u_mps=u.component_mps;sm.v_mps=v.component_mps;
        sm.ub_west_east_mps.resize(levels*2*
                                   static_cast<std::size_t>(grid.ny));
        sm.vb_south_north_mps.resize(levels*2*
                                     static_cast<std::size_t>(grid.nx));
        for(std::size_t k=0;k<levels;++k){
            for(int j=0;j<grid.ny;++j){
                const auto first=k*cells+static_cast<std::size_t>(j)*
                                 static_cast<std::size_t>(grid.nx);
                const auto edge=k*2*static_cast<std::size_t>(grid.ny)+
                                static_cast<std::size_t>(j);
                sm.ub_west_east_mps[edge]=prepared_u[first];
                sm.ub_west_east_mps[edge+static_cast<std::size_t>(grid.ny)]=
                    prepared_u[first+static_cast<std::size_t>(grid.nx-1)];
            }
            for(int i=0;i<grid.nx;++i){
                const auto start=k*cells+static_cast<std::size_t>(i);
                const auto edge=k*2*static_cast<std::size_t>(grid.nx)+
                                static_cast<std::size_t>(i);
                sm.vb_south_north_mps[edge]=prepared_v[start];
                sm.vb_south_north_mps[edge+static_cast<std::size_t>(grid.nx)]=
                    prepared_v[start+(static_cast<std::size_t>(grid.ny-1)*
                                        static_cast<std::size_t>(grid.nx))];
            }
        }
        std::vector<float> dz;
        dz.reserve(levels);
        for(std::size_t k=0;k<levels;++k)
            dz.push_back(grid.zface_m[k+1]-grid.zface_m[k]);
        tail=p6::original_smooth_divcel_w(
            std::move(sm),grid.spacing_km*1000.f,
            grid.spacing_km*1000.f,dz,false);
    }
    const auto center=static_cast<std::size_t>(grid.ny/2)*
                      static_cast<std::size_t>(grid.nx)+
                      static_cast<std::size_t>(grid.nx/2);
    SelectedBridgeHour out;
    out.end=input.end;
    out.original_terrain_kernels_exercised=grid.source_terrain_diagno_tail;
    out.fradj_changed_cells=terrain_result.froude_modified;
    out.slope_changed_cells=terrain_result.slope_modified;
    out.firstguess_center_u_mps=guess.u_mps[center];
    out.firstguess_center_v_mps=guess.v_mps[center];
    out.center_u_mps=u.component_mps[center];
    out.center_v_mps=v.component_mps[center];
    out.upper_u_mps=u.component_mps[8*cells+center];
    out.upper_v_mps=v.component_mps[8*cells+center];
    if(grid.synthetic_identity_diagno_tail||grid.source_terrain_diagno_tail){
        out.selected_tail_exercised=true;
        out.final_center_u_mps=tail.u_mps[center];
        out.final_center_v_mps=tail.v_mps[center];
        out.top_center_w_mps=tail.w_face_mps[levels*cells+center];
        for(float w:tail.w_face_mps)
            if(std::abs(w)>1.e-10f)++out.nonzero_w_faces;
        // A physically calm or horizontally non-divergent flow can have
        // identically zero W; this is valid, not a DIAGNO failure.
        if(!std::isfinite(out.final_center_u_mps)||
           !std::isfinite(out.final_center_v_mps)||
           !std::isfinite(out.top_center_w_mps))
            throw std::invalid_argument("G10 no valid selected DIAGNO W after INTER2");
    }
    for(const auto n:u.contributing_station_count)
        out.observed_contributions+=static_cast<std::size_t>(n);
    if(out.observed_contributions==0||
       !std::isfinite(out.firstguess_center_u_mps)||
       !std::isfinite(out.firstguess_center_v_mps)||
       !std::isfinite(out.center_u_mps)||!std::isfinite(out.center_v_mps)||
       !std::isfinite(out.upper_u_mps)||!std::isfinite(out.upper_v_mps))
        throw std::invalid_argument("G8 source INTER2 nonfinite/empty selected field");
    return out;
}
} // namespace cteas::calmet::p6g
