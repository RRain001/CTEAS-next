#pragma once
// P6D9A selected original CALMET 6.5.0 DIAGNO bridging contract.
//
// Source call order: WIND1 [L5590], WINDBC [L5599], then optional kinetic,
// Froude [L5643-5644], radiative/heat, slope corrections, first WINDBC
// [L5748]; INTER2 U/V [L6055-6061]; if HTFAC>0 a second WINDBC(U,V)
// [L6100] overwrites the first, then SMOOTH+DIVCEL+W [L6119-6148]; optional
// IOBR=1 O'Brien W adjustment [L6153-6159] and MINIM [L6180].
//
// D9A deliberately DOES NOT simulate the intervening heat/terrain physics.
// It requires the caller to explicitly designate a synthetic-identity
// audit route or supply an externally calculated, audited post-correction
// step-one field. No silent fallback and no claim of actual DIAGNO parity.
#include "cteas/p6/wind1_selected_firstguess.hpp"
#include "cteas/p6/inter2_selected.hpp"
#include "cteas/p6/diagno_segment.hpp"
#include "cteas/p6/diagno_obrien_minim.hpp"
#include "cteas/p6/froude_adjust.hpp"
#include "cteas/p6/slope_flow.hpp"
#include "cteas/p6/topof2.hpp"
#include "cteas/p6/terrain_envelope.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6 {

enum class DiagnoD9UpstreamMode {
    Missing=0,
    SyntheticIdentityForSourceAudit=1,
    ExternallyCompletedUpstreamPhysics=2
};
struct DiagnoD9TerrainBoundary {
    // Original FRADJ/SLOPE inputs beyond the step-one winds: gridded terrain,
    // terrain envelope HMAX, lapse rate GAMMA, 2-D surface temperature and
    // the ISURFT selector. All 2500-element fields are k-less 50x50 planes.
    // CRITFN is consumed by FRADJ only.
    int isurft=-1;
    float tinf_k=0.f;
    float critfn=0.f;
    std::vector<float> terrain_m,maximum_terrain_m;
    std::vector<float> lapse_rate_k_per_m,surface_temperature_k;
};
struct DiagnoD9SlopeBoundary {
    // Original SLOPE inputs beyond HTOPO/HMAX/TEMP2D/TINF/ISURFT: valley
    // bottoms, birdwise distances to the envelope extremes, gridded sensible
    // heat flux and the GEO water landuse range. 2500-element planes.
    int water_first=0,water_last=0;
    std::vector<float> minimum_terrain_m,distance_to_max_terrain_m;
    std::vector<float> distance_to_min_terrain_m,sensible_heat_w_m2;
    std::vector<int> landuse;
};
struct DiagnoD9SelectedInput {
    Wind1SelectedStationHour stations;
    Wind1FirstGuessSelectedControls first_guess;
    Inter2SelectedInput inter2_u, inter2_v;
    std::vector<int> smoothing_passes;
    std::vector<float> layer_thickness_m;
    DiagnoD9UpstreamMode upstream_mode=DiagnoD9UpstreamMode::Missing;
    // If externally completed, replace WIND1 original step-one winds with
    // the caller's terrain/heat/slope-corrected UG/VG. Size 50*50*9.
    std::vector<float> corrected_first_guess_u_mps,corrected_first_guess_v_mps;
    // Original L6092 gate: HTFAC>0 performs a SECOND WINDBC(U,V) after
    // INTER2, overwriting the earlier L5748 UG/VG snapshot.
    // The frozen 2022 GEO.DAT has HTFAC=1. The isolated D9A Fortran
    // synthetic fixture enters at SMOOTH with caller-supplied pre-INTER2
    // boundaries and DOES NOT include L6092-L6101. Default=0 preserves
    // the deliberately segmented oracle. Production must explicitly
    // pass the real GEO HTFAC=1; never infer that from the D9A default.
    float htfac=0.f;
    bool lake_breeze=false;
    // Original IKINE=1 pre-blend kinematic route: W zeroed [L5615-5616],
    // TOPOF2 [L5621-5622], then MINIM(UG,VG,W,UB,VB,DIV,NITER,DIVLIM)
    // [L5628-5629] using the L5598-5600 boundary snapshot. ALPHA is the
    // original empirical topographic coefficient. Non-case path: the frozen
    // real deck has IKINE=0.
    bool kinematic_route=false;
    float alpha=0.f;
    // Original namelist NITER/DIVLIM of the L5628 pre-blend MINIM call.
    int kinematic_iterations=0;
    float kinematic_divergence_limit_per_s=0.f;
    // Original pre-DIAGNO TERSET envelope call (DIAGI L5228, gated by
    // I3DCTW=IWFCOD, which the real deck sets to 1): builds HMAX, HMIN,
    // DISTHMAX and DISTHMIN from the GEO terrain inside the bridge. When set,
    // the caller must NOT also supply those four planes.
    bool terset_envelope=false;
    float terrad_km=0.f;
    // Original IFRADJ=1 stage L5643-L5644, applied to the step-one UG/VG
    // before the L5748 WINDBC snapshot and the L6055/L6059 INTER2 calls.
    bool froude_adjustment=false;
    DiagnoD9TerrainBoundary terrain;
    // Original ISLOPE=1 stage L5722 plus the L5738-L5742 additive loop,
    // applied after FRADJ and before the L5748 WINDBC snapshot.
    bool slope_flow=false;
    DiagnoD9SlopeBoundary slope;
    // Original IOBR=1 tail: O'Brien W adjustment L6153-L6159 then MINIM
    // L6180. CELLZB(1) is the original lowest face height, NITER and DIVLIM
    // are the original namelist MINIM controls.
    bool obrien_adjustment=false;
    float cellzb_origin_m=0.f;
    int minim_iterations=0;
    float minim_divergence_limit_per_s=0.f;
};
struct DiagnoD9SelectedOutput {
    Wind1FirstGuessSelectedFields raw_first_guess;
    std::vector<float> prepared_ug,prepared_vg;
    std::vector<float> blended_u,blended_v;
    // Original TOPOF2 terrain-following vertical velocity face field; empty
    // unless the IKINE=1 pre-blend route is enabled. MINIM holds it fixed.
    std::vector<float> kinematic_w_face_mps;
    FinalWindSegment final_fields;
};

inline DiagnoD9SelectedOutput integrate_diagno_d9_selected(
    const DiagnoD9SelectedInput& request) {
    if(request.upstream_mode==DiagnoD9UpstreamMode::Missing)
        throw std::invalid_argument("D9 upstream terrain/radiative/slope stage not provided");
    if(request.lake_breeze)
        throw std::invalid_argument("D9 lake breeze branch not verified");
    if(request.first_guess.nx!=50||request.first_guess.ny!=50||
       request.first_guess.nz!=9)
        throw std::invalid_argument("D9 only supports frozen 50x50x9 case");
    if(request.smoothing_passes.size()!=9||request.layer_thickness_m.size()!=9)
        throw std::invalid_argument("D9 missing nine-level SMOOTH/DZ controls");
    for(float dz:request.layer_thickness_m)
        if(!(std::isfinite(dz)&&dz>0.f))
            throw std::invalid_argument("D9 invalid DZ");
    const auto first=wind1_firstguess_selected(request.stations,request.first_guess);
    auto u=first.ug_mps,v=first.vg_mps;
    if(request.upstream_mode==DiagnoD9UpstreamMode::ExternallyCompletedUpstreamPhysics){
        if(request.corrected_first_guess_u_mps.size()!=22500||
           request.corrected_first_guess_v_mps.size()!=22500)
            throw std::invalid_argument("D9 missing upstream corrected UG/VG");
        u=request.corrected_first_guess_u_mps;
        v=request.corrected_first_guess_v_mps;
        for(float x:u)if(!std::isfinite(x))
            throw std::invalid_argument("D9 corrected U contains missing values");
        for(float x:v)if(!std::isfinite(x))
            throw std::invalid_argument("D9 corrected V contains missing values");
    }else if(!request.corrected_first_guess_u_mps.empty()||
             !request.corrected_first_guess_v_mps.empty()) {
        throw std::invalid_argument("D9 synthetic identity cannot silently apply corrections");
    }
    if(request.froude_adjustment||request.slope_flow||request.kinematic_route) {
        if(request.upstream_mode!=DiagnoD9UpstreamMode::SyntheticIdentityForSourceAudit)
            throw std::invalid_argument("D9 terrain stages cannot re-adjust an external corrected field");
    }
    // Original CELLZB(K)=ZFACE(K); shared by the FRADJ height test and the
    // SLOPE vertical decay of the slope-flow layer.
    std::vector<float> zface(10);
    zface[0]=request.cellzb_origin_m;
    for(std::size_t k=0;k<9;++k)zface[k+1]=zface[k]+
        request.layer_thickness_m[k];
    const auto nx=std::size_t(50),ny=std::size_t(50),plane=nx*ny;
    // Original TERSET envelope resolution: exactly one provider may supply
    // HMAX/HMIN/DISTHMAX/DISTHMIN, either the caller or the in-chain kernel.
    std::vector<float> envelope_max,envelope_min,envelope_dist_max,
        envelope_dist_min;
    if(request.terset_envelope) {
        if(!request.terrain.maximum_terrain_m.empty()||
           !request.slope.minimum_terrain_m.empty()||
           !request.slope.distance_to_max_terrain_m.empty()||
           !request.slope.distance_to_min_terrain_m.empty())
            throw std::invalid_argument(
                "D9 TERSET envelope cannot replace supplied envelope planes");
        if(request.terrain.terrain_m.size()!=2500)
            throw std::invalid_argument("D9 TERSET envelope missing terrain");
        const auto envelope=terset(request.terrain.terrain_m,50,50,100.f,100.f,
                                   request.terrad_km);
        envelope_max=envelope.maximum_m;
        envelope_min=envelope.minimum_m;
        envelope_dist_max=envelope.distance_to_maximum_m;
        envelope_dist_min=envelope.distance_to_minimum_m;
    }
    std::vector<float> kinematic_w;
    if(request.kinematic_route) {
        const auto& t=request.terrain;
        if(!std::isfinite(request.alpha))
            throw std::invalid_argument("D9 invalid original ALPHA coefficient");
        if(t.terrain_m.size()!=2500||t.lapse_rate_k_per_m.size()!=2500||
           t.surface_temperature_k.size()!=2500)
            throw std::invalid_argument("D9 missing original TOPOF2 50x50 fields");
        Topof2Input topof2;
        topof2.nx=50;topof2.ny=50;topof2.nz=9;
        topof2.dx_m=100.f;topof2.dy_m=100.f;
        topof2.isurft=t.isurft;topof2.tinf_k=t.tinf_k;
        topof2.alpha=request.alpha;
        topof2.dz_m=request.layer_thickness_m;
        topof2.cellzb_m=zface;
        topof2.terrain_m=t.terrain_m;
        topof2.lapse_rate_k_per_m=t.lapse_rate_k_per_m;
        topof2.surface_temperature_k=t.surface_temperature_k;
        kinematic_w=original_topof2_w(topof2,u,v);
        // Original L5598-5600 WINDBC snapshot, taken before this route.
        std::vector<float> pre_ub(9*2*ny),pre_vb(9*2*nx);
        for(std::size_t k=0;k<9;++k)for(std::size_t j=0;j<ny;++j){
            pre_ub[k*2*ny+j]=u[k*plane+j*nx];
            pre_ub[k*2*ny+ny+j]=u[k*plane+j*nx+nx-1];
        }
        for(std::size_t k=0;k<9;++k)for(std::size_t i=0;i<nx;++i){
            pre_vb[k*2*nx+i]=v[k*plane+i];
            pre_vb[k*2*nx+nx+i]=v[k*plane+(ny-1)*nx+i];
        }
        DivcelInput minim_in;
        minim_in.nx=50;minim_in.ny=50;minim_in.nz=9;
        minim_in.dx_m=100.f;minim_in.dy_m=100.f;
        minim_in.dz_m=request.layer_thickness_m;
        minim_in.u_mps=u;minim_in.v_mps=v;minim_in.w_mps=kinematic_w;
        minim_in.ub_west_east_mps=std::move(pre_ub);
        minim_in.vb_south_north_mps=std::move(pre_vb);
        auto relaxed=original_minim_scoped(
            std::move(minim_in),request.kinematic_iterations,
            request.kinematic_divergence_limit_per_s);
        u=std::move(relaxed.wind.u_mps);v=std::move(relaxed.wind.v_mps);
    }
    if(request.froude_adjustment) {
        const auto& f=request.terrain;
        const std::vector<float>& hmax=request.terset_envelope
            ? envelope_max:f.maximum_terrain_m;
        if(f.terrain_m.size()!=2500||hmax.size()!=2500||
           f.lapse_rate_k_per_m.size()!=2500||
           f.surface_temperature_k.size()!=2500)
            throw std::invalid_argument("D9 missing original FRADJ 50x50 fields");
        WindUV step_one{std::move(u),std::move(v)};
        auto adjusted=froude_adjust(
            50,50,9,100.f,100.f,f.terrain_m,hmax,
            f.lapse_rate_k_per_m,f.surface_temperature_k,
            f.isurft,f.tinf_k,f.critfn,zface,std::move(step_one));
        u=std::move(adjusted.u);v=std::move(adjusted.v);
    }
    if(request.slope_flow) {
        const auto& t=request.terrain;
        const auto& s=request.slope;
        const std::vector<float>& hmax=request.terset_envelope
            ? envelope_max:t.maximum_terrain_m;
        const std::vector<float>& hmin=request.terset_envelope
            ? envelope_min:s.minimum_terrain_m;
        const std::vector<float>& dist_max=request.terset_envelope
            ? envelope_dist_max:s.distance_to_max_terrain_m;
        const std::vector<float>& dist_min=request.terset_envelope
            ? envelope_dist_min:s.distance_to_min_terrain_m;
        if(t.terrain_m.size()!=2500||hmax.size()!=2500||
           t.surface_temperature_k.size()!=2500||hmin.size()!=2500||
           dist_max.size()!=2500||dist_min.size()!=2500||
           s.sensible_heat_w_m2.size()!=2500||s.landuse.size()!=2500)
            throw std::invalid_argument("D9 missing original SLOPE 50x50 fields");
        SlopeInput slope;
        slope.nx=50;slope.ny=50;slope.nz=9;
        slope.dx_m=100.f;slope.dy_m=100.f;
        slope.water_first=s.water_first;slope.water_last=s.water_last;
        slope.isurft=t.isurft;
        slope.domain_temperature_k=t.tinf_k;
        slope.zface_m=zface;
        slope.terrain_m=t.terrain_m;slope.hmax_m=hmax;
        slope.hmin_m=hmin;
        slope.disthmax_m=dist_max;
        slope.disthmin_m=dist_min;
        slope.sensible_heat_w_m2=s.sensible_heat_w_m2;
        slope.surface_temperature_k=t.surface_temperature_k;
        slope.landuse=s.landuse;
        const auto contribution=compute_original_slope_scoped(slope);
        // Original L5738-L5742 adds the slope flow to the step-one winds at
        // every level; every magnitude guard is performed inside SLOPE.
        for(std::size_t n=0;n<22500;++n){
            u[n]+=contribution.u_mps[n];
            v[n]+=contribution.v_mps[n];
        }
    }

    // Original DIAGNO refreshes step-one WINDBC after terrain and slope
    // modifications at L5748, BEFORE the L6055/L6059 INTER2 calls.
    std::vector<float> ub(9*2*ny),vb(9*2*nx);
    for(std::size_t k=0;k<9;++k)for(std::size_t j=0;j<ny;++j){
        ub[k*2*ny+j]=u[k*plane+j*nx];
        ub[k*2*ny+ny+j]=u[k*plane+j*nx+nx-1];
    }
    for(std::size_t k=0;k<9;++k)for(std::size_t i=0;i<nx;++i){
        vb[k*2*nx+i]=v[k*plane+i];
        vb[k*2*nx+nx+i]=v[k*plane+(ny-1)*nx+i];
    }

    auto au=request.inter2_u,av=request.inter2_v;
    // Original INTER2 has independent observed station values, one
    // component at a time; never copy U into the V observation slot.
    auto check_inter2=[&](const Inter2SelectedInput& field){
        if(field.nx!=50||field.ny!=50||field.nz!=9||
           field.nstations!=2||field.iprog!=0||field.nbar!=0||
           field.noobs!=0||field.dx_m!=100.f||field.dy_m!=100.f)
            throw std::invalid_argument("D9 original selected INTER2 control mismatch");
        if(field.station_x_km.size()!=2||field.station_y_km.size()!=2)
            throw std::invalid_argument("D9 missing station locations");
        const float sx=request.first_guess.surface_x_relative_m*0.001f;
        const float sy=request.first_guess.surface_y_relative_m*0.001f;
        const float ux=request.first_guess.upper_x_relative_m*0.001f;
        const float uy=request.first_guess.upper_y_relative_m*0.001f;
        constexpr float eps=0.000001f;
        if(std::abs(field.station_x_km[0]-sx)>eps||
           std::abs(field.station_y_km[0]-sy)>eps||
           std::abs(field.station_x_km[1]-ux)>eps||
           std::abs(field.station_y_km[1]-uy)>eps)
            throw std::invalid_argument("D9 WIND1/INTER2 station position mismatch");
    };
    check_inter2(au);check_inter2(av);
    // WO weights may legitimately differ between U and V in original
    // CALMET configurations. Preserve independently supplied arrays.
    au.step1_mps=u;av.step1_mps=v;
    const auto ou=original_inter2_selected(au);
    const auto ov=original_inter2_selected(av);
    if(!std::isfinite(request.htfac))
        throw std::invalid_argument("DIAGNO HTFAC nonfinite");
    if(request.htfac>0.f){
        // CALMET 6.5.0 DIAGNO L6092-L6101: second, post-INTER2
        // WINDBC(U,V) overrides the L5748 UG/VG boundary before SMOOTH.
        const auto& iu=ou.component_mps;
        const auto& iv=ov.component_mps;
        for(std::size_t k=0;k<9;++k){
            for(std::size_t j=0;j<ny;++j){
                ub[k*2*ny+j]=iu[k*plane+j*nx];
                ub[k*2*ny+ny+j]=iu[k*plane+j*nx+nx-1];
            }
            for(std::size_t i=0;i<nx;++i){
                vb[k*2*nx+i]=iv[k*plane+i];
                vb[k*2*nx+nx+i]=iv[k*plane+(ny-1)*nx+i];
            }
        }
    }
    SmoothInput smooth;
    smooth.nx=50;smooth.ny=50;smooth.nz=9;
    smooth.lake_breeze=false;
    smooth.passes_per_layer=request.smoothing_passes;
    smooth.u_mps=ou.component_mps;
    smooth.v_mps=ov.component_mps;
    smooth.ub_west_east_mps=std::move(ub);
    smooth.vb_south_north_mps=std::move(vb);
    auto final=original_smooth_divcel_w(
        std::move(smooth),100.f,100.f,request.layer_thickness_m,false);
    if(request.obrien_adjustment) {
        DiagnoObrienControls controls;
        controls.cellzb_origin_m=request.cellzb_origin_m;
        controls.minim_iterations=request.minim_iterations;
        controls.minim_divergence_limit_per_s=request.minim_divergence_limit_per_s;
        final=original_diagno_obrien_minim(
            std::move(final),request.layer_thickness_m,100.f,100.f,controls);
    }
    DiagnoD9SelectedOutput output;
    output.raw_first_guess=first;
    output.prepared_ug=std::move(u);
    output.prepared_vg=std::move(v);
    output.blended_u=ou.component_mps;
    output.blended_v=ov.component_mps;
    output.kinematic_w_face_mps=std::move(kinematic_w);
    output.final_fields=std::move(final);
    return output;
}

} // namespace cteas::calmet::p6