#pragma once
// P6G G11 selected original CALMET DIAGNO terrain subchain.
// Real numerical kernels: TERSET envelope -> FRADJ -> SLOPE addition.
// Per-hour lapse rate, 2D temperature and sensible heat MUST come from the
// caller, with explicit provenance. They are not inferred from SURF.DAT or
// fabricated by this module; G11 exercises synthetic test hours only until
// native P6E real flux/temperature fields have been independently accepted.
// Vendor order calmet.for: FRADJ at L5643; SLOPE at L5722 and add L5738-42;
// boundary snapshot L5748; INTER2 L6055/L6059 follows.
#include "cteas/p6/read_geo_dynamic.hpp"
#include "cteas/p6/terrain_envelope.hpp"
#include "cteas/p6/froude_adjust.hpp"
#include "cteas/p6/slope_flow.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
namespace cteas::calmet::p6g {
namespace p6=cteas::calmet::p6;

struct TerrainStaticG11 {
    int nx=0,ny=0;
    float spacing_m=0.f,terrad_km=0.f;
    int water_first=0,water_last=0;
    std::vector<int> landuse;
    std::vector<float> terrain_m,hmax_m,hmin_m,dist_hmax_m,dist_hmin_m;
};
inline TerrainStaticG11 prepare_g11_terrain(
    const GeoGrid& geo,float terrad_km) {
    if(geo.nx<2||geo.ny<2||geo.nx>400||geo.ny>400||
       !std::isfinite(geo.grid_km)||geo.grid_km<=0.f||
       !std::isfinite(terrad_km)||terrad_km<0.f)
        throw std::invalid_argument("G11 invalid dynamic GEO or TERRAD");
    const auto n=static_cast<std::size_t>(geo.nx)*static_cast<std::size_t>(geo.ny);
    if(geo.terrain_m.size()!=n||geo.landuse.size()!=n)
        throw std::invalid_argument("G11 incomplete original GEO terrain/landuse");
    const float spacing_m=geo.grid_km*1000.f;
    const auto envelope=p6::terset(geo.terrain_m,geo.nx,geo.ny,
                                  spacing_m,spacing_m,terrad_km);
    return {geo.nx,geo.ny,spacing_m,terrad_km,geo.iwat1,geo.iwat2,
            geo.landuse,geo.terrain_m,envelope.maximum_m,envelope.minimum_m,
            envelope.distance_to_maximum_m,envelope.distance_to_minimum_m};
}
enum class TerrainHourProvenance {
    Missing=0,
    SyntheticReferenceFixture=1,
    ValidatedP6EHourlyPhysics=2,
    // Observed source-selected SURFVAR TEMP2D + HEATFX QH, but solar,
    // coefficients and GAMMA are still controlled synthetic test inputs.
    ObservedSurfvarSyntheticSolarFixture=3
};
struct TerrainHourG11 {
    std::chrono::sys_seconds end{}; // G11 clock gate checks original UTC SURF/UP hour-end.
    TerrainHourProvenance provenance=TerrainHourProvenance::Missing;
    // Physical 2-D inputs, not hidden defaults. No temporal extrapolation.
    int isurft=-1;
    float domain_temperature_k=0.f,critfn=0.f;
    std::vector<float> lapse_k_per_m,temperature_k,sensible_heat_w_m2;
};
struct TerrainCorrectionG11 {
    p6::WindUV field;
    std::size_t froude_modified=0,slope_modified=0;
};
inline TerrainCorrectionG11 apply_g11_terrain_after_wind1(
    const TerrainStaticG11& static_input,const TerrainHourG11& hour,
    const std::vector<float>& zface,p6::WindUV input) {
    const int nx=static_input.nx,ny=static_input.ny;
    const auto n=static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny);
    if(nx<2||ny<2||nx>400||ny>400||
       !std::isfinite(static_input.spacing_m)||static_input.spacing_m<=0.f||
       static_input.terrain_m.size()!=n||static_input.landuse.size()!=n||
       static_input.hmax_m.size()!=n||static_input.hmin_m.size()!=n||
       static_input.dist_hmax_m.size()!=n||static_input.dist_hmin_m.size()!=n||
       static_input.water_first>static_input.water_last||
       (hour.provenance!=TerrainHourProvenance::SyntheticReferenceFixture&&
        hour.provenance!=TerrainHourProvenance::ObservedSurfvarSyntheticSolarFixture)||
       hour.isurft!=-1||
       hour.lapse_k_per_m.size()!=n||hour.temperature_k.size()!=n||
       hour.sensible_heat_w_m2.size()!=n||
       !std::isfinite(hour.domain_temperature_k)||
       hour.domain_temperature_k<=0.f||
       !std::isfinite(hour.critfn)||hour.critfn<0.f||
       zface.size()<2||zface.size()>13)
        throw std::invalid_argument("G11 invalid source-backed terrain and explicit per-hour thermal fields");
    const auto nz=static_cast<int>(zface.size())-1;
    if(input.u.size()!=n*static_cast<std::size_t>(nz)||
       input.v.size()!=n*static_cast<std::size_t>(nz))
        throw std::invalid_argument("G11 inconsistent 3D WIND1 geometry");
    for(std::size_t cell=0;cell<n;++cell){
        if(!std::isfinite(static_input.terrain_m[cell])||
           !std::isfinite(static_input.hmax_m[cell])||
           !std::isfinite(static_input.hmin_m[cell])||
           !std::isfinite(static_input.dist_hmax_m[cell])||
           !std::isfinite(static_input.dist_hmin_m[cell])||
           static_input.dist_hmax_m[cell]<0.f||
           static_input.dist_hmin_m[cell]<0.f||
           static_input.hmin_m[cell]>static_input.terrain_m[cell]||
           static_input.hmax_m[cell]<static_input.terrain_m[cell])
            throw std::invalid_argument("G11 invalid TERSET envelope");
    }
    const auto original_u=input.u,original_v=input.v;
    auto corrected=p6::froude_adjust(
        nx,ny,nz,static_input.spacing_m,static_input.spacing_m,
        static_input.terrain_m,static_input.hmax_m,
        hour.lapse_k_per_m,hour.temperature_k,
        hour.isurft,hour.domain_temperature_k,hour.critfn,
        zface,std::move(input));
    TerrainCorrectionG11 result;
    for(std::size_t idx=0;idx<corrected.u.size();++idx)
        if(corrected.u[idx]!=original_u[idx]||corrected.v[idx]!=original_v[idx])
            ++result.froude_modified;
    p6::SlopeInput slope;
    slope.nx=nx;slope.ny=ny;slope.nz=nz;
    slope.dx_m=static_input.spacing_m;
    slope.dy_m=static_input.spacing_m;
    slope.water_first=static_input.water_first;
    slope.water_last=static_input.water_last;
    slope.isurft=hour.isurft;
    slope.domain_temperature_k=hour.domain_temperature_k;
    slope.zface_m=zface;
    slope.terrain_m=static_input.terrain_m;
    slope.hmax_m=static_input.hmax_m;slope.hmin_m=static_input.hmin_m;
    slope.disthmax_m=static_input.dist_hmax_m;
    slope.disthmin_m=static_input.dist_hmin_m;
    slope.sensible_heat_w_m2=hour.sensible_heat_w_m2;
    slope.surface_temperature_k=hour.temperature_k;
    slope.landuse=static_input.landuse;
    const auto contribution=p6::compute_original_slope_scoped(slope);
    for(std::size_t idx=0;idx<corrected.u.size();++idx){
        if(contribution.u_mps[idx]!=0.f||contribution.v_mps[idx]!=0.f)
            ++result.slope_modified;
        corrected.u[idx]+=contribution.u_mps[idx];
        corrected.v[idx]+=contribution.v_mps[idx];
        if(!std::isfinite(corrected.u[idx])||!std::isfinite(corrected.v[idx]))
            throw std::invalid_argument("G11 terrain-corrected wind not finite");
    }
    result.field=std::move(corrected);
    return result;
}
} // namespace cteas::calmet::p6g
