#include "cteas/puff/original_flat_calcpf.hpp"
#include "cteas/puff/original_pufrecs_geometry.hpp"
#include "cteas/puff/original_precision.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <optional>
#include <stdexcept>
#include <utility>

namespace cteas::puff {
namespace {
// PUFRECS original L5152–5272 for the selected no-building,
// no-calm, Gaussian-vertical MDISP=3 PG point-puff branch.
// All intermediates deliberately return to original REAL*4.
struct ReceptorPgSigma {
    float y=0.0F,z=0.0F,grise_height_m=0.0F;
};
ReceptorPgSigma receptor_pg_sigma(
    const RiseCompSamplingState& s,
    const OriginalPufrecsGeometry& geom,
    const SigmaCurves& curves) {
    // Original PUFRECS L4998-5004: a real LCALM step discards the
    // trajectory-based FRAC and pending horizontal-rise distance.
    // Keep the original SLGFRAC distance (XTT1 is computed *before*
    // this override), but sample time-based sigma at FRAC=0.5.
    const bool calm=s.receptor_calm_sigma.has_value();
    const float frac=calm?0.5F:geom.fraction;
    const float xtt=geom.distance_to_receptor_m;
    const float xfinal=calm?0.0F:s.receptor_final_rise_distance_m;
    const float bidsq=s.receptor_buoyancy_variance_m2;
    const float sy0sq=s.receptor_initial_sigma_y_squared_m2;
    if(!std::isfinite(frac)||!std::isfinite(xtt)||xtt<0.0F ||
       // Original PRFIN may set XFINAL=0 below WSSTK0 while retaining
       // genuine vertical final rise. PUFRECS then uses the final-rise
       // branch for XT>0; reject negative/infinite XFINAL, not zero.
       !std::isfinite(xfinal)||xfinal<0.0F ||
       !std::isfinite(bidsq)||bidsq<0.0F ||
       !std::isfinite(sy0sq)||sy0sq<0.0F)
        throw std::invalid_argument("PUFRECS receptor PG requires valid native rise/virtuals");
    // Original L5152-5195: source-specific gradual/final rise.
    float hgr=0.0F,rfacsq=1.0F;
    if(xtt<xfinal && xtt>0.0F) {
        auto plume=s.receptor_rise;
        plume.x_m=xtt;
        const auto rise=gradual_plume_height(plume);
        hgr=static_cast<float>(rise.height_m);
        const float rf=static_cast<float>(rise.rise_fraction);
        rfacsq=rf*rf;
    } else if(xtt<=0.0F && xfinal>0.0F) {
        // PUFRECS L5180-5184 enters this branch only if XFRISE>0.
        hgr=static_cast<float>(s.receptor_rise.stack_height_m);
        rfacsq=0.0F;
    } else {
        hgr=static_cast<float>(s.receptor_rise.final_rise_m);
    }
    const float addbid=bidsq*rfacsq;
    const float subbid=bidsq*(1.0F-rfacsq);
    const auto& a=s.sigmas.adjust;
    const auto& v=s.sigmas.step;
    // PUFRECS evaluates SIGTY/SIGTZ at interpolated virtual time and
    // distance using the CURRENT COMP IDOPT (not always PG IDOPT=3).
    // Live calm SETCSIG/TURBSET is carried by the puff's native step.
    const auto calm_forward=[&](float t,float d,bool vertical) {
        auto p=*s.receptor_calm_sigma;
        p.sy0=0.0F;
        p.sz0=0.0F;
        p.dt_s=t;
        p.dx_km=d;
        const auto result=original_calm_sigma(p);
        return vertical?result.sz:result.sy;
    };
    float syr=0.0F,szr=0.0F;
    if(frac==0.0F || frac==1.0F) {
        // Original L5201-5223: endpoints use stored begin/end sigma,
        // removing the missing part of the final buoyancy enhancement.
        syr=static_cast<float>(frac==0.0F?a.sigma_y_begin_m:a.sigma_y_end_m);
        szr=static_cast<float>(frac==0.0F?a.sigma_z_begin_m:a.sigma_z_end_m);
        if(subbid>=0.0F) {
            const float argy=syr*syr-subbid;
            syr=s.receptor_minimum_sigma_y_m;
            if(argy>0.0F)syr=std::sqrt(argy);
            if(v.gaussian_vertical) {
                const float argz=szr*szr-subbid;
                szr=s.receptor_minimum_sigma_z_m;
                if(argz>0.0F)szr=std::sqrt(argz);
            }
        }
    } else {
        // Original L5233-5265: interpolated PUFRECS virtual distances
        // and times feed *forward* SIGTY/SIGTZ from zero initial sigma.
        const float vty=std::max(0.0F,static_cast<float>(
            v.virtual_time_y_begin_s)+frac*(static_cast<float>(
            v.virtual_time_y_end_s)-static_cast<float>(
            v.virtual_time_y_begin_s)));
        const float vdy=std::max(0.0F,static_cast<float>(
            v.virtual_distance_y_begin_km)+frac*(static_cast<float>(
            v.virtual_distance_y_end_km)-static_cast<float>(
            v.virtual_distance_y_begin_km)));
        const float syar=s.receptor_calm_sigma ?
            calm_forward(vty,vdy,false) :
            static_cast<float>(curves.sigma_y(0.0F,{vdy,vty}).sigma_y_m);
        syr=syar;
        if(addbid>0.0F || sy0sq>0.0F)
            syr=std::sqrt(syar*syar+addbid+sy0sq);
        if(v.gaussian_vertical) {
            const float vtz=std::max(0.0F,static_cast<float>(
                v.virtual_time_z_begin_s)+frac*(static_cast<float>(
                v.virtual_time_z_end_s)-static_cast<float>(
                v.virtual_time_z_begin_s)));
            const float vdz=std::max(0.0F,static_cast<float>(
                v.virtual_distance_z_begin_km)+frac*(static_cast<float>(
                v.virtual_distance_z_end_km)-static_cast<float>(
                v.virtual_distance_z_begin_km)));
            // Original SIGTZ(...,ZB1,...): use native puff's begin height.
            const float szar=s.receptor_calm_sigma ?
                calm_forward(vtz,vdz,true) :
                static_cast<float>(curves.sigma_z(
                    0.0F,s.before.z_m,{vdz,vtz}).sigma_z_m);
            szr=szar;
            if(addbid>0.0F)szr=std::sqrt(szar*szar+addbid);
        } else {
            szr=static_cast<float>(a.sigma_z_begin_m);
        }
    }
    syr=std::max(syr,s.receptor_minimum_sigma_y_m);
    szr=std::max(szr,s.receptor_minimum_sigma_z_m);
    if(!std::isfinite(syr)||syr<=0.0F ||
       !std::isfinite(szr)||szr<0.0F || !std::isfinite(hgr))
       throw std::invalid_argument("PUFRECS receptor-specific PG sigma failed");
    return {syr,szr,hgr};
}
} // namespace
RiseCompSamplingKernel make_original_flat_calcpf_sampler(
    const ReceptorSet& receptors,float met_spacing_m,
    float averaging_period_s,float impact_sigma_multiple,
    OriginalFlatVerticalMethod vertical_method,
    OriginalMctadj2TerrainLookup terrain_lookup,
    bool selected_h3_from_multispecies,
    OriginalCalcpfIntermediateHook trace_hook,
    float receptor_clip_extension_sigma) {
    if(!receptors.gridded || !receptors.discrete.empty() ||
       receptors.mesh_down!=1 || receptors.sampling_nx<=0 ||
       receptors.sampling_ny<=0 || receptors.ibsamp<1 ||
       receptors.jbsamp<1 || !std::isfinite(met_spacing_m) ||
       met_spacing_m<=0.0F || !std::isfinite(averaging_period_s) ||
       averaging_period_s<=0.0F || !std::isfinite(impact_sigma_multiple) ||
       impact_sigma_multiple<=0.0F ||
       !std::isfinite(receptors.spacing_km) ||
       std::abs(static_cast<float>(receptors.spacing_km)*1000.0F -
                met_spacing_m)>1.0e-3F ||
       receptors.grid.size()!=static_cast<std::size_t>(receptors.sampling_nx) *
                              static_cast<std::size_t>(receptors.sampling_ny)) {
        throw std::invalid_argument(
            "flat CALCPF supports only validated MESHDN=1 gridded ground receptors");
    }
    if(!std::isfinite(receptor_clip_extension_sigma) ||
       receptor_clip_extension_sigma<0.0F)
        throw std::invalid_argument("PUFRECS FCLIP must be finite and nonnegative");
    const bool terrain_mode=
        vertical_method==OriginalFlatVerticalMethod::receptor_pg_vcoup_mctadj2;
    if(trace_hook && vertical_method!=OriginalFlatVerticalMethod::receptor_pg_vcoup &&
       !terrain_mode)
        throw std::invalid_argument("CALCPF intermediate trace requires receptor PUFRECS");
    if(terrain_mode && !terrain_lookup)
        throw std::invalid_argument(
            "CALCPF MCTADJ2 needs authentic TRELIEF/GETELEV receptor lookup");
    const auto nrecs=receptors.grid.size();
    const auto nx=static_cast<std::size_t>(receptors.sampling_nx);
    const float grid_x=static_cast<float>(receptors.ibsamp)-0.5F;
    const float grid_y=static_cast<float>(receptors.jbsamp)-0.5F;
    return [nrecs,nx,grid_x,grid_y,met_spacing_m,averaging_period_s,
            impact_sigma_multiple,vertical_method,terrain_lookup,
            selected_h3_from_multispecies,trace_hook,
             receptor_clip_extension_sigma](
            const RiseCompSamplingState& s) {
        const bool terrain_mode=
            vertical_method==OriginalFlatVerticalMethod::receptor_pg_vcoup_mctadj2;
        if(terrain_mode && !s.original_ctadj2_step)
            throw std::invalid_argument(
                "CALCPF MCTADJ2 requires native SETPUF FRACZ1/LUP1");
        if(s.after_setpuf_before_lid.puff_code!=s.vmass.puff_code ||
           !s.after_setpuf_before_lid.vmass_pending ||
           s.vmass.mass_mixed.empty() ||
           (selected_h3_from_multispecies ?
                s.vmass.mass_mixed.size()!=2 :
                s.vmass.mass_mixed.size()!=1) ||
           s.vmass.mass_above.size()!=s.vmass.mass_mixed.size() ||
           (selected_h3_from_multispecies &&
            s.receptor_qold_mixed.size()!=s.vmass.mass_mixed.size()) ||
           !std::isfinite(s.step_seconds) || s.step_seconds<=0.0F ||
           s.step_seconds>averaging_period_s) {
            throw std::invalid_argument(
                "flat CALCPF expects one-species post-VMASS, pre-history state");
        }
        const float sy=static_cast<float>(s.sigmas.step.sigma_y_mid_m);
        const float sz=static_cast<float>(s.sigmas.step.sigma_z_mid_m);
        // Original COMP L11169-11174 forms PUFFR=RCONST*SYE1 from
        // /CURRENT/ AFTER SETPUF has added BIDFNL. PUFRECS L4969-4970
        // likewise clips using the adjusted SYB1/SYE1, not the stored
        // pre-BID dispersion sigma. Screening with step.sigma_y_end_m
        // erroneously discards real edge receptors.
        const float end_sy=static_cast<float>(s.sigmas.adjust.sigma_y_end_m);
        const float lid=s.vmass.reflecting_lid_m;
        if(!std::isfinite(sy)||sy<=0.0F || !std::isfinite(sz) ||
           sz<0.0F || !std::isfinite(end_sy)||end_sy<=0.0F ||
           !std::isfinite(lid)||lid<=0.0F) {
            throw std::invalid_argument("flat CALCPF invalid sigma or VMASS HLID");
        }
        // CALCPF L4191-4197 original sampling-grid coordinates, not UTM.
        const float xo=(s.before.x_cells-grid_x)+1.0F;
        const float yo=(s.before.y_cells-grid_y)+1.0F;
        const float xn=(s.after.x_cells-grid_x)+1.0F;
        const float yn=(s.after.y_cells-grid_y)+1.0F;
        const float midz=0.5F*(s.before.z_m+s.after.z_m);
        const float max_lid=std::max(lid,s.after_setpuf_before_lid.zimax_m);
        float vfactor=0.0F;
        if(vertical_method==OriginalFlatVerticalMethod::midpoint_vcoup) {
            // Legacy restricted kernel, retained to preserve its accepted
            // six-hour nonzero/bitwise-readback regression as a control.
            vfactor=static_cast<float>(vertical_coupling({
                s.vmass.puff_code,0.0,midz,sz,lid,max_lid}));
        } else if(vertical_method==OriginalFlatVerticalMethod::substep_vcbar) {
            // Source-ported CALPUFF VCBAR: use the *native* post-SETPUF
            // begin/mid/end vertical distribution, not a fabricated sigma
            // sampled at the midpoint. Strictly flat, MTILT=0, non-slug,
            // MCTADJ=0; terrain-specific PUFRECS is a separate gate.
            const auto& a=s.sigmas.adjust;
            for(double v:{a.sigma_z_begin_m,a.sigma_z_mid_m,
                          a.sigma_z_end_m}) {
                if(!std::isfinite(v) || v<0.0)
                    throw std::invalid_argument(
                        "flat VCBAR requires native adjusted begin/mid/end SIGTZ");
            }
            VcbarInputs c;
            c.state.puff_code=s.vmass.puff_code;
            c.state.x_begin1=s.before.x_cells;
            c.state.y_begin1=s.before.y_cells;
            c.state.z_begin1=s.before.z_m;
            c.state.sigma_z_begin1=a.sigma_z_begin_m;
            c.state.sigma_z_mid=a.sigma_z_mid_m;
            c.state.x_end1=s.after.x_cells;
            c.state.y_end1=s.after.y_cells;
            c.state.z_end1=s.after.z_m;
            c.state.sigma_z_end1=a.sigma_z_end_m;
            c.lid_height_m=lid;
            c.calm=false;
            c.slug=false;
            c.terrain_adjustment=0;
            c.plume_tilt=0;
            vfactor=static_cast<float>(vertical_coupling_bar(c));
        } else if(vertical_method==OriginalFlatVerticalMethod::receptor_pg_vcoup ||
                  terrain_mode) {
            // CALCPF L4234–4275: the Gaussian receptor vertical factor
            // is determined *inside* the receptor loop after PUFRECS,
            // not from the substep-averaged VCBAR.
            vfactor=1.0F;
        } else {
            throw std::invalid_argument("unsupported CALCPF vertical mode");
        }
        if(!std::isfinite(vfactor) || vfactor<0.0F)
            throw std::invalid_argument("flat CALCPF invalid original VCOUP factor");
        std::vector<float> values(nrecs,0.0F);
        const bool per_receptor_vertical=
            (vertical_method==OriginalFlatVerticalMethod::receptor_pg_vcoup ||
             terrain_mode);
        // Original CALCPF Gaussian path evaluates VCOUP using the result
        // of each receptor-specific PUFRECS. Global VCBAR=0 cannot be
        // used to discard that receptor's possible concentration.
        // Original CALCPF L4295/L4304 integrates QOLD*T1+QNEW*T2.
        // A dry-removal substep may leave QNEW=0 while pre-removal
        // QOLD remains positive; do not discard that valid contribution.
        const float qnew=s.vmass.mass_mixed[0];
        const float qold=selected_h3_from_multispecies ?
            s.receptor_qold_mixed[0] : qnew;
        if((vfactor==0.0F && !per_receptor_vertical) ||
           (qnew<=0.0F && qold<=0.0F))
            return values;
        const float radius=impact_sigma_multiple*end_sy/met_spacing_m;
        const float at_rec=sy/met_spacing_m;
        if(!std::isfinite(radius)||radius<=0.0F ||
           !std::isfinite(at_rec)||at_rec<=0.0F)
            throw std::invalid_argument("flat CALCPF sampling radius overflow");
        // Original COMP calpuff.for L10342, L10447 and L10563/10569:
        //   TAVGI=1.0/TAVG  (REAL*4, computed once)
        //   TFRACT=TSAMP*TAVGI
        // Do not replace the two single-precision operations with
        // TSAMP/TAVG: the first real hour-2 receptor difference at DGM
        // seq1607 is 1 ULP in XTEMP=F1*TFRACT (upstream 11 fields exact).
        const float frac=original_calcpf_time_fraction(
            s.step_seconds,averaging_period_s);
        const bool pg_receiver=
            (vertical_method==OriginalFlatVerticalMethod::receptor_pg_vcoup ||
             terrain_mode);
        // Source-ported SETCSIG uses the meteorology already selected by
        // native COMP for this substep; never use a frozen DGM class/wind.
        const auto curves=pg_receiver ?
            std::make_optional<SigmaCurves>(s.receptor_dispersion) :
            std::nullopt;
        OriginalPufrecsGridStepInputs grid_step;
        if(pg_receiver) {
            grid_step.x_begin_cells=s.before.x_cells;
            grid_step.y_begin_cells=s.before.y_cells;
            grid_step.x_end_cells=s.after.x_cells;
            grid_step.y_end_cells=s.after.y_cells;
            grid_step.sigma_y_begin_m=static_cast<float>(
                s.sigmas.adjust.sigma_y_begin_m);
            grid_step.sigma_y_end_m=end_sy;
            grid_step.distance_begin_m=s.before.total_distance_m;
            grid_step.mean_wind_ms=static_cast<float>(
                (s.after.total_distance_m-s.before.total_distance_m)/
                s.step_seconds);
            grid_step.met_spacing_m=met_spacing_m;
            grid_step.ibsamp=static_cast<int>(grid_x+0.5F);
            grid_step.jbsamp=static_cast<int>(grid_y+0.5F);
            grid_step.sampling_nx=static_cast<int>(nx);
            grid_step.sampling_ny=static_cast<int>(nrecs/nx);
            // Original PUFRECS /COMPARM/ FCLIP is independent of
            // CALCPF's RCONST screening radius.
            grid_step.fclip=receptor_clip_extension_sigma;
            grid_step.clip=true;
        }
        for(std::size_t i=0;i<nrecs;++i) {
            const float xr=static_cast<float>(i%nx)+1.0F;
            const float yr=static_cast<float>(i/nx)+1.0F;
            const auto screen=original_puff_screen(xo,yo,xn,yn,xr,yr,radius*radius);
            // Original CALCPF L4221-4224: PFSCRN first screens only
            // against the END-of-substep puff radius. The second impact
            // test L4241-4247 MUST follow PUFRECS SIGTY at this receptor.
            if(!screen.has_impact)
                continue;
            float receptor_fraction=0.0F;
            float receptor_sigma_y=sy;
            float receptor_sigma_z=sz;
            float receptor_height_m=midz;
            float receptor_pole_m=0.0F;
            float receptor_vertical=vfactor;
            if(pg_receiver) {
                const auto geometry=original_pufrecs_grid_receptor_geometry(
                    grid_step,i);
                const auto pufrecs=receptor_pg_sigma(s,geometry,*curves);
                // Original PUFRECS LCALM overrides FRAC=0.5 AFTER
                // SLGFRAC and BEFORE SIGTY/SIGTZ and PUFFCT2.
                receptor_fraction=s.receptor_calm_sigma?0.5F:
                                  geometry.fraction;
                receptor_sigma_y=pufrecs.y;
                receptor_sigma_z=pufrecs.z;
                // Vendor CALCPF L4234–4275: PUFRECS computes per-receptor
                // ZPR/ZRPOLE, with PUFFCT2 MCTADJ2 at L5321–5369.
                float zpr=pufrecs.grise_height_m;
                float zrpole=0.0F;
                if(terrain_mode) {
                    const auto position=original_puffct2(
                        *s.original_ctadj2_step,receptor_fraction);
                    const auto met_terrain=terrain_lookup(s,i,position);
                    const auto adjusted=original_mctadj2_receptor_height(
                        position,pufrecs.grise_height_m,
                        static_cast<float>(s.receptor_rise.final_rise_m),
                        met_terrain);
                    zpr=adjusted.puff_height_above_ground_m;
                    zrpole=adjusted.pole_height_m;
                }
                receptor_height_m=zpr;
                receptor_pole_m=zrpole;
                receptor_vertical=static_cast<float>(vertical_coupling({
                    s.vmass.puff_code,zrpole,zpr,pufrecs.z,lid,max_lid
                }));
                if(!std::isfinite(receptor_vertical) ||
                   receptor_vertical<0.0F)
                    throw std::invalid_argument(
                        "CALCPF receptor-specific VCOUP invalid");
                if(receptor_vertical==0.0F)continue;
            }
            // Vendor L4244-4247: PR2 = (NSIGMA*SYREC/DELSAM)**2.
            // Using the step-midpoint SYM1 here would reject receptors
            // that the source-ordered receptor-specific PUFRECS admits.
            const float receptor_radius=
                impact_sigma_multiple*(receptor_sigma_y/met_spacing_m);
            if(!std::isfinite(receptor_radius) || receptor_radius<=0.0F)
                throw std::invalid_argument(
                    "original CALCPF receptor-specific sampling radius invalid");
            if(static_cast<float>(screen.closest_distance_squared)>
               receptor_radius*receptor_radius)
                continue;
            const auto ints=puff_sampling_integrals(
                xo,yo,xn,yn,xr,yr,receptor_sigma_y/met_spacing_m,
                screen.closest_distance_squared);
            const double inc=receptor_concentration_increment(ints,{
                // CALPUFF COMP L10965 QOLD is the post-VMASS snapshot;
                // L11108 QNEW is post-DRY. Keep the historical restricted
                // one-species/synthetic kernel unchanged by default.
                .mass_old=selected_h3_from_multispecies ?
                    s.receptor_qold_mixed[0] : s.vmass.mass_mixed[0],
                .mass_new=s.vmass.mass_mixed[0],
                .sigma_y_at_receptor_m=receptor_sigma_y,
                .closest_approach_squared_km2=screen.closest_distance_squared,
                .vertical_factor=receptor_vertical,
                .time_fraction=frac,
                .deposition_ratio=s.receptor_deposition_ratio,
                .area_source_factor=1.0
            });
            if(!std::isfinite(inc) ||
               std::abs(inc)>std::numeric_limits<float>::max())
                throw std::overflow_error("flat CALCPF receptor REAL4 overflow");
            if(trace_hook) {
                // Read-only: the trace is not fed back into PFSAMP/CALCPF.
                // Read-only mirror of CALCPF L4293: 6.2831853*SYREC**2.
                const float denom=6.2831853F*(receptor_sigma_y*receptor_sigma_y);
                const float dinv=1.0F/denom;
                const float t2=static_cast<float>(ints.i2)*dinv;
                const float t1=static_cast<float>(ints.i1)*dinv-t2;
                trace_hook(s,OriginalCalcpfReceiverIntermediate{
                    i,receptor_fraction,receptor_sigma_y,receptor_sigma_z,
                    receptor_height_m,receptor_pole_m,receptor_vertical,
                    static_cast<float>(ints.i1),static_cast<float>(ints.i2),
                    t1,t2,qold,qnew,static_cast<float>(receptor_vertical*frac),
                    static_cast<float>(inc)
                });
            }
            values[i]=static_cast<float>(inc);
        }
        return values;
    };
}
} // namespace cteas::puff
