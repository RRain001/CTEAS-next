#include "cteas/puff/original_comp_rise.hpp"
#include "cteas/puff/original_comp_calm.hpp"
#include "cteas/puff/original_calm_sigma.hpp"
#include "cteas/puff/original_ptlaps.hpp"
#include "cteas/puff/coupling.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace cteas::puff {
namespace {
void require(bool v,const char* message) {
    if(!v)throw std::invalid_argument(message);
}
float r4(double x,const char* what) {
    require(std::isfinite(x),what);
    const float y=static_cast<float>(x);
    require(std::isfinite(y),what);
    return y;
}
}
void OriginalCompRisePointDriver::admit(
    int id,const NewPuffInputs& source,const InjectionInputs& injection) {
    require(id>0 && !rise_.contains(id),"duplicate/invalid rising puff");
    require(source.source_type==1 && source.downwash_code==0 &&
            source.stack_height_m>0.0 &&
            // Original POINTS1 HEFF=HTSTAK-TIPDW+RISE_B can be
            // below stack-top under downwash; positive finite required.
            std::isfinite(source.effective_height_m) &&
            source.effective_height_m>0.0 &&
            // Vendor PRFIN WSSTK<1 gives XFINAL=0 and completed
            // vertical rise. Native GRISE/RISEWIND already implements
            // the source condition XTOTB<XFINAL, which is false here.
            // Reject zero XFINAL outside the exact non-windy PRFIN branch.
            (source.x_final_m>0.0 ||
             (source.x_final_m==0.0 && source.stack_wind_speed_ms<1.0 &&
              source.x_final_buoyancy_m==0.0 &&
              source.x_final_momentum_m==0.0)) &&
            source.exit_velocity_ms>=0.0 &&
            source.diameter_m>=0.0 &&
            (source.buoyancy_flux>0.0 || source.momentum_flux>0.0) &&
            source.wake_radius_m==0.0 &&
            source.building_height_m==0.0 &&
            source.wake_xshift_m==0.0,
            "original rise point requires native PRFIN, no PRIME/building");
    require(injection.gaussian_distribution==1 &&
            r4(injection.effective_height_m,"injection height")==
              r4(source.effective_height_m,"rise final height"),
            "rise POINTS1 and INJECT source height or Gaussian flag differs");
    RiseSource state;
    state.x_final_m=r4(source.x_final_m,"XFINAL");
    state.buoyancy_variance_m2=r4(source.final_rise_variance_m2,"BIDSQ");
    // Original SETPUF calpuff.for L48408-48413: SY0SQ is the
    // initial AREA-source size ONLY (ISTYPE=3 or 4). POINTS1
    // ISTYPE=1 sets SY0SQ=0. The native point SYSRC already enters
    // the persisted SIGYB/virtual SIGTY state; adding SYSRC**2 again
    // double counts source width in every /CURRENT/ receptor sigma.
    require(std::isfinite(source.sigma_y_source_m) &&
            source.sigma_y_source_m>=0.0,
            "original point SYSRC must be finite and non-negative");
    state.initial_sigma_y_squared_m2=0.0F;
    state.minimum_sigma_y_m=r4(source.initial_sigma_y_m,"SY0");
    state.minimum_sigma_z_m=r4(source.initial_sigma_z_m,"SZ0");
    auto& p=state.physics;
    p.source_type=1;
    p.downwash_code=0;
    p.met_period=1;
    p.rise_method=1;
    p.shear_flag=0;
    p.final_rise_m=r4(source.effective_height_m,"ZFINAL");
    p.stack_height_m=r4(source.stack_height_m,"HT0");
    p.full_final_rise_m=r4(
       source.effective_height_m-source.stack_height_m+
       source.stack_tip_downwash_m,"ZFRISE");
    p.diameter_m=r4(source.diameter_m,"DIAM");
    p.exit_velocity_ms=r4(source.exit_velocity_ms,"EXITW");
    p.stack_wind_speed_ms=r4(source.stack_wind_speed_ms,"WS0");
    p.stability_class=source.stability_class;
    p.sqrt_stability_s=r4(source.sqrt_stability_s,"SQRTS");
    p.momentum_flux=r4(source.momentum_flux,"FM");
    p.buoyancy_flux=r4(source.buoyancy_flux,"FB");
    p.x_final_momentum_m=r4(source.x_final_momentum_m,"XMFIN");
    p.z_final_momentum_m=r4(source.z_final_momentum_m,"ZMFIN");
    p.x_final_buoyancy_m=r4(source.x_final_buoyancy_m,"XBFIN");
    p.z_final_buoyancy_m=r4(source.z_final_buoyancy_m,"ZBFIN");
    p.stack_tip_downwash_m=r4(source.stack_tip_downwash_m,"STIPDW");
    // Catch invalid rise data and unsupported source branches before adding
    // to either physical store.
    auto probe=p;
    probe.x_m=0.0;
    (void)gradual_plume_height(probe);
    auto m=motion_;
    auto v=vertical_;
    m.introduce_point_source(id,source);
    v.admit_point(id,source,injection);
    motion_=std::move(m);
    vertical_=std::move(v);
    rise_.emplace(id,state);
}
RiseCompStep OriginalCompRisePointDriver::step_pg_rise(
    int id,const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& control,const DispersionSetup& pg,bool urban,
    RiseCompSourceSampling source_sampling,
    const RiseCompSamplingKernel& sampling_kernel) {
    const auto found=rise_.find(id);
    if(found==rise_.end())throw std::out_of_range("unknown rise puff");
    require(pg.mdisp==3 && !pg.heffter_sigma_z &&
            !pg.roughness_adjustment &&
            !control.dispersion.calm &&
            std::isfinite(control.seconds) && control.seconds>0.0F &&
            std::isfinite(control.met_spacing_m) && control.met_spacing_m>0.0F &&
            std::isfinite(control.source_period_s) && control.source_period_s>0.0F &&
            std::isfinite(control.max_sample_distance_cells) &&
            control.max_sample_distance_cells>0.0F &&
            control.max_sampling_steps==1 && control.release_number==1,
            "native rising COMP only supports MDISP3 single noncalm point step");

    require(source_sampling.ksam>=1 &&
            source_sampling.nsam>=source_sampling.ksam &&
            source_sampling.nsam<=99,
            "invalid original COMP KSAM/NSAM source sampling context");
    // Full state copy: failed wind, GRISE, PG, SETPUF or VMASS must not
    // leave a partial trajectory, mass partition or sampling clock.
    auto m=motion_;
    auto v=vertical_;
    auto state=found->second;
    const auto before=m.state(id);
    auto vs=v.state(id);
    require(vs.completed_substeps==state.completed &&
            vs.committed_lid_steps==state.completed,
            "native rising puff sigma/mass clock drift");
    VendorSubstepOrder order(control.gaussian_dry.has_value(),
                            static_cast<bool>(sampling_kernel));
    const SamplingCadence cadence=sampling_cadence({
        .new_puff=state.completed==0,
        .source_type=1,
        .emission_period_s=control.source_period_s,
        .step_seconds=control.seconds,
        .release_number=control.release_number,
        .wind_speed_ms=state.previous_wind_ms,
        .x_sam_len=control.max_sample_distance_cells,
        .grid_spacing_m=control.met_spacing_m,
        .max_sampling_steps=control.max_sampling_steps
    });
    require(cadence.sampling_steps==1 && cadence.start_substep==1,
            "multi-sample COMP not yet integrated");
    order.completed(VendorSubstepPhase::SamplingCadence);
    order.completed(VendorSubstepPhase::LoadPreviousPuffState);
    const auto cell=original_met_cell(
        before.x_cells,before.y_cells,met.nx,met.ny);
    order.completed(VendorSubstepPhase::ResolveMetCell);
    const auto sampled=v.sample(
        id,met,statics,before.x_cells,before.y_cells,before.z_m);
    order.completed(VendorSubstepPhase::EvaluatePuffDz);
    require(sampled.cell.offset_0based==cell.offset_0based,
            "rise METFM1 GETCELL drift");
    order.completed(VendorSubstepPhase::EvaluateAdvect);

    // Original COMP passes DZB (begin vertical top minus centre) and the
    // current puff travel distance to RISEWIND, and the latter itself
    // invokes GRISE at XBEG and XEND in its NCOUNT=2 REAL4 iteration.
    OriginalRiseMetInputs inputs;
    inputs.x_cells=before.x_cells;
    inputs.y_cells=before.y_cells;
    inputs.start_distance_m=before.total_distance_m;
    inputs.final_distance_m=state.x_final_m;
    inputs.step_seconds=r4(cadence.sampling_step_s,"rise step time");
    inputs.rise_half_depth_m=r4(
        std::max(0.0,sampled.extent.z_top_m-before.z_m),"DZB");
    inputs.rise_iterations=2;
    inputs.plume=state.physics;
    // Directly verified original COMP calpuff.for L10503-L10519:
    // RISEWIND executes ONLY when (MOD(ICODE,2)==1) and XTOTB<XFINAL.
    // This covers both naturally completed plume rise and calm SETPUF
    // cancellation (XFINAL=0), without inventing another velocity profile.
    // Gaussian POINTS1/INJECT and VMASS are separately enforced here.
    OriginalRiseMetResult rise;
    if((vs.puff_code%2)==1 && before.total_distance_m<state.x_final_m){
        rise=original_rise_wind_met(met,statics,inputs);
    }else{
        const float raw_u=r4(sampled.wind.u_ms,"post-calm ADVECT U");
        const float raw_v=r4(sampled.wind.v_ms,"post-calm ADVECT V");
        const float raw_ws=std::sqrt(r4(raw_u*raw_u+raw_v*raw_v,
                                          "post-calm ADVECT WS2"));
        rise.cell=sampled.cell;
        rise.final_rise_wind=sampled.wind;
        rise.adjusted={raw_u,raw_v,raw_ws,0};
        auto p=state.physics;
        p.x_m=before.total_distance_m;
        rise.initial_rise=gradual_plume_height(p);
    }
    float u=r4(rise.adjusted.u_ms,"RISEWIND U");
    float w=r4(rise.adjusted.v_ms,"RISEWIND V");
    float ws=r4(rise.adjusted.wind_speed_ms,"RISEWIND WS");
    // Source-ordered COMP applies its own WSCALM only AFTER RISEWIND.
    // Never conflate this with the CALMET station/diagnostic calm policy.
    // The source-verified transport guard is available, but P7D currently
    // only ports SIGTY/SIGTZ for IDOPT=3. Original calm SETPUF changes both
    // IDOPTY and IDOPTZ to 1. Refuse those cases rather than silently using
    // ordinary PG dispersion coefficients and claiming false parity.
    const auto wind_calm=original_comp_calm_transport(
        u,w,ws,control.calm_threshold_ms);
    if(wind_calm.calm && !control.calm_mdisp3)
        throw std::invalid_argument(
            "native COMP detected original WSCALM branch: "
            "IDOPTY=1/IDOPTZ=1 requires source-derived TURBSET inputs");
    u=wind_calm.u_ms;
    w=wind_calm.v_ms;
    ws=wind_calm.wind_speed_ms;
    order.completed(VendorSubstepPhase::ApplyRiseWindAndCalm);

    const Substep substep=substep_length({
        .sampling_step_s=cadence.sampling_step_s,
        .wind_speed_ms=ws,.puff=true,.free_slug=false,
        .subsampling=source_sampling.lsubsam,
        .grid_spacing_m=control.met_spacing_m,
        .x_sam_len=control.max_sample_distance_cells,
        .substep_index=source_sampling.ksam,
        .sampling_steps=source_sampling.nsam
    });
    if(substep.split){
        // Unmodified CALPUFF COMP L10571-10578: a shortened TSAMP must
        // resample RISEWIND while the puff is still rising. DO NOT reuse
        // the provisional pre-FSTEP wind in the transport or SETPUF state.
        if(before.total_distance_m<state.x_final_m){
            inputs.step_seconds=r4(substep.step_s,"shortened rise TSAMP");
            rise=original_rise_wind_met(met,statics,inputs);
            u=r4(rise.adjusted.u_ms,"resampled RISEWIND U");
            w=r4(rise.adjusted.v_ms,"resampled RISEWIND V");
            ws=r4(rise.adjusted.wind_speed_ms,"resampled RISEWIND WS");
            // FSTEP may resample RISEWIND at a different effective TSAMP.
            // Classify THAT wind too; the provisional branch may differ.
            const auto resampled_calm=original_comp_calm_transport(
                u,w,ws,control.calm_threshold_ms);
            if(resampled_calm.calm && !control.calm_mdisp3)
                throw std::invalid_argument(
                    "resampled native COMP detected original WSCALM branch: "
                    "IDOPTY=1/IDOPTZ=1 requires source-derived TURBSET inputs");
            u=resampled_calm.u_ms;
            w=resampled_calm.v_ms;
            ws=resampled_calm.wind_speed_ms;
        }
    } else if(r4(substep.step_s,"native rise TSAMP")!=control.seconds){
        throw std::logic_error("COMP unexpectedly shortened unsplit step");
    }
    order.completed(VendorSubstepPhase::ChooseSubstepLength);

    // Final post-FSTEP RISEWIND determines LCALM. Only the post-rise,
    // no-receptor subset has been source-validated for native IDOPT=1.
    const bool lcalm=ws<control.calm_threshold_ms;
    if(lcalm){
        require(control.calm_mdisp3.has_value(),
                "LCALM requires original MDISP3 turbulence inputs");
        // Vendor DRY source L26155-26159 sets LCALMF=.FALSE. and
        // L26266-26268 calls VCBAR(...,LCALMF) irrespective of COMP's
        // dispersion LCALM. Allow DRY to use its actual source policy
        // without changing SETPUF/PUFRECS IDOPT=1 calm sigma physics.
        // Source COMP executes rising (odd ICODE, XTOTB<XFINAL)
        // through RISEWIND/GRISE *before* applying the WSCALM policy.
        // SETPUF may then cancel outstanding horizontal rise for LCALM;
        // do not reject the legitimate H8->H9 rising-to-calm transition.
        // Verify it against original DGM before accepting real H9.
    }

    const float distance=r4(ws*r4(substep.step_s,"time"),"rise distance");
    auto end_state=state.physics;
    end_state.x_m=r4(before.total_distance_m+distance,"RISE x end");
    const float end_height=r4(
        gradual_plume_height(end_state).height_m,"native GRISE ZE");
    auto moved=m.advance(id,{
        .uadv_ms=u,.vadv_ms=w,.ws_ms=ws,
        .tsamp_s=r4(substep.step_s,"rise TSAMP"),
        .met_spacing_m=control.met_spacing_m,
        .end_height_m=end_height,
        .settling_velocity_ms=0.0F,.plume_tilt=0
    });
    order.completed(VendorSubstepPhase::AdvancePosition);

    const StepBookkeeping bookkeeping=step_bookkeeping({
        .total_distance_m=before.total_distance_m,
        .total_time_s=before.travel_time_s,
        .step_distance_m=moved.distance_m,
        .step_seconds=substep.step_s,
        .km_per_m=0.001,.wind_speed_ms=ws,
        .calm_wind_threshold=control.calm_threshold_ms,.downwash_code=0,
        .x_final_m=state.x_final_m,
        .dispersion_y_option=3,.dispersion_z_option=3
    });
    require(bookkeeping.calm==lcalm &&
            bookkeeping.dispersion_y_option==(lcalm?1:3) &&
            bookkeeping.dispersion_z_option==(lcalm?1:3),
            "SETPUF LCALM and IDOPT classification drift");
    // Vendor COMP L10683-10691 and L10820-10883 selects the
    // POST-ADVECT midpoint meteorological class for SETCSIG, then
    // substitutes JSUP when an A-D puff lies above the bounded DPBL.
    // This applies to normal MDISP=3 PG SIGTY/SIGTZ too, not only to
    // the special calm IDOPT=1 turbulence path. H24 old puff 1603
    // enters the above-inversion class from a prior stable hour.
    int sigma_stability=sampled.stability_class;
    if(control.calm_mdisp3 && control.calm_mdisp3->jsup>0) {
        const auto mid=original_met_cell_clamped(
            0.5F*(before.x_cells+moved.state.x_cells),
            0.5F*(before.y_cells+moved.state.y_cells),met.nx,met.ny);
        const auto& config=*control.calm_mdisp3;
        require(mid.offset_0based<met.ipgt.size() &&
                mid.offset_0based<met.zi.size() &&
                config.minimum_mixing_height_m>0.0F &&
                config.maximum_mixing_height_m>=
                    config.minimum_mixing_height_m,
                "SETPUF JSUP requires original midpoint PGT and bounded PBL");
        const int midpoint_class=std::min(
            met.ipgt[mid.offset_0based],6);
        const float midpoint_dpbl=std::clamp(
            met.zi[mid.offset_0based],
            config.minimum_mixing_height_m,
            config.maximum_mixing_height_m);
        sigma_stability=original_comp_turbset_jdstab(
            midpoint_class,config.jsup,before.z_m,midpoint_dpbl);
    }
    const SigmaCurves curves(dispersion_environment(
        pg,sigma_stability,urban,ws));
    SigmaYCurve sigma_y=[&curves](double first,double delta,double time) {
        const auto s=curves.sigma_y(first,{delta,time});
        return SigmaCurvePoint{s.sigma_y_m,s.virtual_time_y_s,
                               s.virtual_distance_y_km};
    };
    SigmaZCurve sigma_z=[&curves](double first,double delta,
                                        double time,double height) {
        const auto s=curves.sigma_z(first,height,{delta,time});
        return SigmaCurvePoint{s.sigma_z_m,s.virtual_time_z_s,
                               s.virtual_distance_z_km};
    };
    std::optional<OriginalCalmSigmaInput> native_receptor_calm;
    if(lcalm){
        // Source COMP L10695-10703 resolves midpoint IXMET/IYMET;
        // L10839-10842 selects ILW from THAT cell, not release/origin.
        // Vendor GETCELL allows the crossing substep's midpoint to map
        // to the nearest valid outer MET cell until COMP retires the puff.
        const auto mid_cell=original_met_cell_clamped(
            0.5F*(before.x_cells+moved.state.x_cells),
            0.5F*(before.y_cells+moved.state.y_cells),met.nx,met.ny);
        require(mid_cell.offset_0based<met.el.size() &&
                mid_cell.offset_0based<met.ipgt.size(),
                "native calm SETCSIG requires real midpoint EL and JDSTAB");
        const int mid_stability=met.ipgt[mid_cell.offset_0based];
        // Full VMASS and TIBL changes across differing stability zones
        // have not yet passed source parity; never use the old PG class
        // while reading new-cell turbulence without saying so.
        require(mid_stability==sampled.stability_class,
                "calm COMP cross-cell stability transition not yet accepted");
        const auto& cfg=*control.calm_mdisp3;
        // Original COMP calpuff.for L10863-10883:
        // JDSTAB = ISTAB; when above the bounded mixed layer, an unstable
        // PGT class 1-4 is replaced by the original deck's JSUP (5 in the
        // frozen Hefei case). MDISP=3 then selects
        // TSIGW=SWMIN(JDSTAB,ILW), NOT SWMIN(ISTAB,ILW).
        // This is the original H9 #16426 source cause: 0.03 vs 0.08 m/s.
        // HTMET=ZOLD=ZPB(II) for a Gaussian puff (COMP L10465-10489);
        // use actual native pre-ADVECT state and the original mid MET cell.
        require(mid_cell.offset_0based<met.zi.size() &&
                cfg.jsup>=0&&cfg.jsup<=6 &&
                (cfg.jsup==0 ||
                 (cfg.minimum_mixing_height_m>0.0F &&
                  cfg.maximum_mixing_height_m>=cfg.minimum_mixing_height_m)),
                "original JSUP/PBL source selection requires deck-derived bounds");
        // Synthetic JDSTAB tests may explicitly disable JSUP with zero.
        // Real puff.inp uses JSUP>0 and must apply the source PBL clamps.
        const float dpbl=cfg.jsup>0 ?
            std::clamp(met.zi[mid_cell.offset_0based],
                cfg.minimum_mixing_height_m,cfg.maximum_mixing_height_m):
            met.zi[mid_cell.offset_0based];
        const int jdstab=original_comp_turbset_jdstab(
            mid_stability,cfg.jsup,before.z_m,dpbl);
        const auto turb=original_turbset_mdisp3_from_cell(
            cfg.original_turbulence,statics,
            static_cast<std::size_t>(met.nx),
            static_cast<std::size_t>(met.ny),
            mid_cell.offset_0based,jdstab,
            cfg.iwat1,cfg.iwat2);
        OriginalCalmSigmaInput parameters;
        parameters.uavg=ws;
        parameters.sigv=turb.sigv_ms;
        parameters.sigw=turb.sigw_ms;
        parameters.el=met.el[mid_cell.offset_0based];
        parameters.tyidr=cfg.original_turbulence.tyidr;
        parameters.tzidr=cfg.original_turbulence.tzidr;
        parameters.tzisdr=cfg.original_turbulence.tzisdr;
        parameters.syh=r4(pg.sigma_y_heffter_m,"original SYH");
        parameters.ayt=cfg.original_turbulence.ayt;
        parameters.sy0=parameters.syh;
        // SETCSIG initializes THFTY with SIGTY(SYH,0,0).
        parameters.thfty=original_calm_sigma(parameters).virty;
        // PUFRECS reads the same live SETCSIG /CSIGMA/ parameters as
        // SETPUF when LCALM=1. No PG re-classification at receptors.
        native_receptor_calm=parameters;
        sigma_y=[parameters](double initial,double distance,double time){
            auto p=parameters;
            p.sy0=static_cast<float>(initial);p.sz0=0.0F;
            p.dx_km=static_cast<float>(distance);
            p.dt_s=static_cast<float>(time);
            const auto r=original_calm_sigma(p);
            return SigmaCurvePoint{r.sy,r.virty,r.virdy};
        };
        sigma_z=[parameters](double initial,double distance,double time,
                             double /*height*/){
            auto p=parameters;
            p.sy0=0.0F;p.sz0=static_cast<float>(initial);
            p.dx_km=static_cast<float>(distance);
            p.dt_s=static_cast<float>(time);
            const auto r=original_calm_sigma(p);
            return SigmaCurvePoint{r.sz,r.virtz,r.virdz};
        };
    }
    // Original COMP L10629-10649: LDIV && Gaussian puff, *after* the
    // old-sigma PUFFDZ/ADVECT wind and movement, *before* VMASS/SETPUF.
    // The WDIV field is reconstructed from ORIGINAL hourly CALMET W and
    // ZFACE, never fetched from DGM; CDIV is frozen puff.inp input.
    if(control.original_wdiv){
        // Source GETCELL/GRIDIJ L82559-82720 CLAMPS the meteorological
        // end-cell lookup at an outer domain edge. A puff center can
        // cross the original computational bounds ON THIS SUBSTEP and is
        // retired only after WDIV/SETPUF. The stricter interior-only
        // original_met_cell wrapper is correct for the start cell but
        // not for this end-cell profile lookup.
        const auto edge=grid_cell({
            .x_cells=moved.state.x_cells,
            .y_cells=moved.state.y_cells,
            .nx=met.nx,.ny=met.ny,
            .domains=1,.domain=1,.nest_factor=1.0
        });
        const OriginalMetCell end_cell{
            edge.i,edge.j,
            static_cast<std::size_t>(edge.j-1)*static_cast<std::size_t>(met.nx)+
            static_cast<std::size_t>(edge.i-1)
        };
        const auto dz=original_vertical_divergence(
            met,statics,sampled.cell,end_cell,
            r4(sampled.extent.z_bottom_m,"WDIV original ZBOT"),
            r4(sampled.extent.z_top_m,"WDIV original ZTOP"),
            r4(substep.step_s,"WDIV original TSAMP"),
            vs.sigma_z_m,vs.puff_code,*control.original_wdiv);
        v.commit_wdiv_sigma_z(id,vs.sigma_z_m,dz.sigma_z_m);
        vs.sigma_z_m=dz.sigma_z_m;
    }
    auto dispersion=control.dispersion;
    dispersion.calm=lcalm;
    // Vendor COMP L10859: VMASS uses OLD sigma and may alter ICODE.
    // Original COMP calpuff.for L10683-10691 reloads ISTAB/DPBL from
    // the POST-ADVECT midpoint (IXMID/IYMID).  VMASS L10859 consumes
    // that live DPBL, not the pre-ADVECT start-cell value used by
    // PUFFDZ and ADVECT L10482-10499.
    //
    // The production original-deck path carries explicit XMINZI/XMAXZI
    // in calm_mdisp3. Other synthetic test paths keep their separate
    // previously supported metadata contract until that clamp is
    // represented in general NeutralCompControls.
    float vmass_dpbl=sampled.mixing_height_m;
    int vmass_stability=sampled.stability_class;
    // Vendor COMP L10683-L10691 refreshes ISTAB/DPBL from IXMID/IYMID
    // on EVERY substep before VMASS, irrespective of JSUP. JSUP only
    // selects above-PBL dispersion stability later (L10863-L10867).
    // The former jsup>0 guard reused pre-ADVECT DPBL in C2 JSUP=0,
    // notably the last H1 puff crossing into a new start cell.
    // Only authentic source-deck paths provide the positive XMINZI/XMAXZI
    // admission contract. Isolated synthetic CALM tests intentionally use
    // a default-initialized calm_mdisp3 without those deck bounds; keep
    // their pre-existing sampled-PBL contract rather than rejecting them.
    // A SOURCE deck with positive XMINZI remains strict on every field.
    if(control.gaussian_dry && control.calm_mdisp3 &&
       control.calm_mdisp3->minimum_mixing_height_m>0.0F){
        const auto mid=original_met_cell_clamped(
            0.5F*(before.x_cells+moved.state.x_cells),
            0.5F*(before.y_cells+moved.state.y_cells),
            met.nx,met.ny);
        const auto& config=*control.calm_mdisp3;
        require(mid.offset_0based<met.zi.size() &&
                mid.offset_0based<met.ipgt.size() &&
                config.minimum_mixing_height_m>0.0F &&
                config.maximum_mixing_height_m>=
                    config.minimum_mixing_height_m,
                "source COMP midpoint VMASS requires valid PBL bounds");
        vmass_dpbl=std::clamp(met.zi[mid.offset_0based],
            config.minimum_mixing_height_m,
            config.maximum_mixing_height_m);
        vmass_stability=std::min(met.ipgt[mid.offset_0based],6);
        require(vmass_stability>=1 && vmass_stability<=6 &&
                std::isfinite(vmass_dpbl) && vmass_dpbl>0.0F,
                "source COMP midpoint VMASS PBL/stability invalid");
    }
    auto mass=v.commit_vmass(
        id,vmass_dpbl,before.z_m,moved.state.z_m,
        vs.sigma_z_m,vmass_stability,0);
    order.completed(VendorSubstepPhase::ApplyVmass);
    dispersion.step.puff_code=mass.puff_code;
    dispersion.step.sigma_y_start_m=vs.sigma_y_m;
    dispersion.step.sigma_z_start_m=vs.sigma_z_m;
    // Original SETPUF L48641-L48666: source POINTS1 BIDFNL and SY0
    // affect the begin/mid/end sampling sigmas in /CURRENT/ only.
    // They MUST come from the persisted physical puff (not test control
    // defaults) and MUST NOT be mistaken for stored SIGYB/SIGZB.
    dispersion.final_rise_variance_m2=state.buoyancy_variance_m2;
    dispersion.initial_sigma_y_squared_m2=state.initial_sigma_y_squared_m2;
    dispersion.step.puff_height_m=before.z_m;
    dispersion.step.mid_time_s=bookkeeping.mid_time_s;
    dispersion.step.mid_distance_km=bookkeeping.mid_distance_km;
    float current_receptor_bvf=0.0F;
    OriginalTerrainSigmaInputs terrain_inputs;
    const OriginalTerrainSigmaInputs* selected_terrain=nullptr;
    // Vendor COMP computes BVF for PUFRECS regardless of vertical ICODE.
    // SETPUF L48362-L48365 initializes FRACZ1=0 and LUP1=.FALSE.
    // for EVERY step. Odd Gaussian code's CTADJ2 may then overwrite these
    // initial values at L48613-L48632; even code preserves the initialized
    // pair for PUFRECS PUFFCT2 L5321.
    if(control.mctadj2){
        // SETPUF L48616-48631 owns the authoritative CTADJ2 state.
        // This must use the same *native* x/y/height and RISEWIND WS
        // as the step being committed; no historical DGM inputs.
        terrain_inputs.lookup=&control.mctadj2->terrain;
        terrain_inputs.x_begin_cells=before.x_cells;
        terrain_inputs.y_begin_cells=before.y_cells;
        terrain_inputs.x_end_cells=moved.state.x_cells;
        terrain_inputs.y_end_cells=moved.state.y_cells;
        terrain_inputs.z_begin_m=before.z_m;
        terrain_inputs.wind_speed_ms=ws;
        float bvf=control.mctadj2->brunt_vaisala_s;
        if(control.mctadj2->derive_bvf_from_metfm1){
            // Vendor COMP L10893-10896: PTLAPS is evaluated for the
            // current *midpoint* meteorological cell and full puff
            // extent. Do not reuse PRFIN source-cell lapse or a frozen
            // hour-constant Brunt-Vaisala frequency.
            // Source COMP PTLAPS reads a clamped post-advection GETCELL
            // midpoint BEFORE the final out-of-domain retirement check.
            const auto mid=original_met_cell_clamped(
                0.5F*(before.x_cells+moved.state.x_cells),
                0.5F*(before.y_cells+moved.state.y_cells),met.nx,met.ny);
            const auto nz=static_cast<std::size_t>(met.nz);
            const auto xy=static_cast<std::size_t>(met.nx)*
                          static_cast<std::size_t>(met.ny);
            require(nz>=2 && statics.cell_face_m.size()==nz+1U &&
                    met.t.size()==nz*xy,
                    "native PTLAPS requires actual complete CALMET ZFACE/TMET");
            std::vector<float> zgpt,tprofile;
            zgpt.reserve(nz);tprofile.reserve(nz);
            for(std::size_t k=0;k<nz;++k){
                zgpt.push_back(0.5F*(statics.cell_face_m[k]+
                                     statics.cell_face_m[k+1U]));
                tprofile.push_back(met.t[k*xy+mid.offset_0based]);
            }
            bvf=original_comp_bvf_metfm1(
                zgpt,tprofile,
                r4(sampled.extent.z_bottom_m,"COMP PTLAPS ZBOT"),
                r4(sampled.extent.z_top_m,"COMP PTLAPS ZTOP"),
                control.mctadj2->minimum_pt_gradient_k_per_m);
        }
        current_receptor_bvf=bvf;
        terrain_inputs.brunt_vaisala_s=bvf;
        terrain_inputs.met_spacing_m=control.met_spacing_m;
        if((mass.puff_code % 2)==1)
            selected_terrain=&terrain_inputs;
    }
    const auto sigma=v.commit_sigma(
        id,dispersion,sigma_y,sigma_z,selected_terrain);
    std::optional<OriginalPuffct2Step> ctadj2_step;
    if(sigma.terrain){
        // SETPUF L487xx persists CTADJ2's corrected ZPE for the
        // *next* native puff step, then CALCPF consumes FRACZ1/LUP1.
        const auto terrain_height=sigma.terrain->z_end_m;
        ctadj2_step=OriginalPuffct2Step{
            .x_begin_m=before.x_cells*control.met_spacing_m,
            .y_begin_m=before.y_cells*control.met_spacing_m,
            .z_begin_m=before.z_m,
            .x_end_m=moved.state.x_cells*control.met_spacing_m,
            .y_end_m=moved.state.y_cells*control.met_spacing_m,
            .z_end_m=terrain_height,
            .terrain_fraction=sigma.terrain->fracz_end,
            .upslope=sigma.terrain->upslope_end
        };
        m.commit_setpuf_terrain_height(
            id,moved.state.z_m,terrain_height);
        moved.state=m.state(id);
    } else if(control.mctadj2) {
        // Original SETPUF L48363-48365 explicitly resets both COMMON
        // flags before every SIGTZ branch, and even ICODE skips CTADJ2.
        // This is a source-initialized (not fitted) PUFFCT2 input.
        require((mass.puff_code % 2)==0,
                "native even ICODE PUFFCT2 requires non-Gaussian SETPUF");
        ctadj2_step=OriginalPuffct2Step{
            .x_begin_m=before.x_cells*control.met_spacing_m,
            .y_begin_m=before.y_cells*control.met_spacing_m,
            .z_begin_m=before.z_m,
            .x_end_m=moved.state.x_cells*control.met_spacing_m,
            .y_end_m=moved.state.y_cells*control.met_spacing_m,
            .z_end_m=moved.state.z_m,
            .terrain_fraction=0.0F,  // SETPUF L48364
            .upslope=false           // SETPUF L48365
        };
    }
    order.completed(VendorSubstepPhase::CommitSetpuf);
    // Original COMP calpuff.for L11076–11097 invokes DRY after SETPUF,
    // before CALCPF, and applies the exponential fraction to QM.
    // This selected Gaussian branch uses independently native
    // VDCOMP meteorology and full SETPUF VCBAR. It refuses the
    // original uniform codes 2/6 until their distinct ratio branch
    // is integrated, rather than applying the wrong Gaussian fraction.
    // Original COMP L10963-10966 takes QOLD after VMASS and before
    // dry removal; never substitute the final post-DRY QM for both
    // CALCPF integration endpoints.
    const auto original_qold_mixed=mass.mass_mixed;
    if(control.gaussian_dry || sampling_kernel)
        order.captured_pre_removal_mass();
    std::optional<OriginalGaussianDryResult> dry_result;
    std::optional<DryDepositionStep> dry_input_resistance;
    if(control.gaussian_dry){
        const auto& setup=control.gaussian_dry->setup;
        // Original COMP L11084 invokes
        // DRY(ICODE,IXS,IYS,MDOMS,...,DPBL,HLID,TEMPK,QSW,...).
        // DRY L26219-26222 and L26229-26230 read U/V, land use, Z0,
        // USTAR, XMONIN, XLAI and WSTAR from the START cell (IXS/IYS).
        // Only the explicitly passed DPBL, TEMPK and QSW are sourced
        // from the refreshed post-ADVECT COMP state. Combining a
        // midpoint WSTAR with start-cell USTAR caused the C2 H1
        // uniform ICODE=2 VDPVD difference even with identical MET.
        // Keep this original call-boundary rule independent of station count.
        const auto dry_cell=original_met_cell_clamped(
            0.5F*(before.x_cells+moved.state.x_cells),
            0.5F*(before.y_cells+moved.state.y_cells),met.nx,met.ny);
        const auto index=dry_cell.offset_0based;
        const auto wind_index=sampled.cell.offset_0based;
        const auto at_midpoint=[index](const auto& field){
            return index<field.size();
        };
        const auto at_start=[wind_index](const auto& field){
            return wind_index<field.size();
        };
        require(setup.species.size()==mass.mass_mixed.size() &&
                at_midpoint(met.tempk)&&at_midpoint(met.qsw)&&
                at_start(met.u)&&at_start(met.v)&&
                at_start(met.ustar)&&at_start(met.el)&&
                at_start(met.wstar)&&
                at_start(statics.land_use)&&
                at_start(statics.roughness_m)&&
                at_start(statics.leaf_area_index),
                "native DRY requires original COMP start-cell VDCOMP fields and midpoint scalar inputs");
        DryDepositionEnvironment e;
        e.u10_ms=met.u[wind_index];
        e.v10_ms=met.v[wind_index];
        e.land_use=statics.land_use[wind_index];
        e.roughness_m=statics.roughness_m[wind_index];
        e.temperature_k=met.tempk[index];
        e.friction_velocity_ms=met.ustar[wind_index];
        e.monin_obukhov_m=met.el[wind_index];
        e.leaf_area_index=statics.leaf_area_index[wind_index];
        e.shortwave_w_m2=met.qsw[index];
        e.vegetation_state=setup.vegetation_state;
        // COMP L10686 supplies post-ADVECT midpoint DPBL explicitly
        // to DRY; DRY L26237/26241 uses START-cell WSTAR/USTAR
        // with that same midpoint DPBL for DIFFK and DZ.
        const auto resistance=dry_deposition_step(
            setup,e,mass.reflecting_lid_m,substep.step_s,
            vmass_dpbl,met.wstar[wind_index]);
        // Expose exact native VDCOMP values to the read-only mass oracle.
        // Never use these preserved copies as a new solver authority.
        dry_input_resistance=resistance;
        int original_type=mass.puff_code;
        if(original_type>=11 && original_type<=16)
            original_type-=10;
        OriginalDryMassResult updated;
        if(mass.puff_code==99 || original_type==4 ||
           original_type==2 || original_type==6) {
            // Original DRY L26227–26261: uniform ICODE 2/6
            // computes VDPVD and TSAMP/HLID; ICODE4/99 skips.
            updated=original_uniform_dry_mass(
                resistance,mass.puff_code,mass.mass_mixed);
        } else {
            // Original DRY L26266–26276: Gaussian ICODE 1/3/5
            // uses source-ported VCBAR instead of 1/HLID and
            // leaves VDPVD exactly 1.
            VcbarInputs vc;
            vc.state.puff_code=mass.puff_code;
            vc.state.x_begin1=before.x_cells;
            vc.state.y_begin1=before.y_cells;
            vc.state.x_end1=moved.state.x_cells;
            vc.state.y_end1=moved.state.y_cells;
            vc.state.z_begin1=before.z_m;
            vc.state.z_end1=moved.state.z_m;
            vc.state.sigma_z_begin1=sigma.adjust.sigma_z_begin_m;
            vc.state.sigma_z_mid=sigma.adjust.sigma_z_mid_m;
            vc.state.sigma_z_end1=sigma.adjust.sigma_z_end_m;
            vc.lid_height_m=mass.reflecting_lid_m;
            vc.terrain_adjustment=control.mctadj2?2:0;
            vc.plume_path_coefficient=
                control.gaussian_dry->plume_path_coefficient;
            // Original DRY's VCBAR argument is LCALMF=.FALSE. even
            // for a puff whose COMP dispersion flag is LCALM=.TRUE.
            vc.calm=false;
            const float vbar=r4(
                vertical_coupling_bar(vc),"native DRY original VCBAR");
            updated=original_gaussian_dry_mass(
                resistance,mass.puff_code,
                r4(substep.step_s,"native DRY TSAMP"),
                vbar,mass.mass_mixed);
        }
        // State and returned VMASS must agree at CALCPF and next hour.
        v.commit_dry(id,mass.mass_mixed,updated.mixed_mass_after);
        mass.mass_mixed=updated.mixed_mass_after;
        dry_result=std::move(updated);
        order.dry_removal_completed();
    }
    // Native receptor accumulation belongs AFTER SETPUF but BEFORE COMP
    // L11391-11398. A pure sampling callback returns staged increments;
    // it must not directly write puff.con or mutate external accumulators.
    // Full CALCPF PUFRECS/VCBAR and CHEM/WET/DRY remain outside scope.
    std::vector<float> receptor_increments;
    if(sampling_kernel){
        // Original SETPUF calpuff.for L48600-48604 and L48664-48668:
        // LCALM writes SY0/SZ0 from the CURRENT midpoint (with BID)
        // before COMP calls CALCPF L11169-11178. Previous-step floors
        // are persisted only when the entire native transaction commits,
        // but PUFRECS must read these current-step values immediately.
        // This is read-only staging; do not mutate the committed puff
        // until receptor sampling and all substeps have succeeded.
        const float receptor_sy0=lcalm?
            r4(sigma.adjust.minimum_sigma_y_m,"LCALM current SY0") :
            state.minimum_sigma_y_m;
        const float receptor_sz0=lcalm?
            r4(sigma.adjust.minimum_sigma_z_m,"LCALM current SZ0") :
            state.minimum_sigma_z_m;
        float receptor_vdpvd=1.0F;
        int receptor_icode=mass.puff_code;
        if(receptor_icode>=11 && receptor_icode<=16)
            receptor_icode-=10;
        if(dry_input_resistance &&
           (receptor_icode==2 || receptor_icode==6)) {
            const auto& ratio=dry_input_resistance->boundary_ratio;
            require(ratio.size()==mass.mass_mixed.size() && !ratio.empty(),
                    "uniform ICODE CALCPF requires native H-3 DRY VDPVD");
            receptor_vdpvd=r4(ratio.front(),"native DRY VDPVD H-3");
            require(receptor_vdpvd>=0.0F && receptor_vdpvd<=1.0F,
                    "CALCPF uniform VDPVD must be a native physical ratio");
        }
        const RiseCompSamplingState at_receptor{
            id,before,moved.state,v.state(id),sigma,mass,
            r4(substep.step_s,"native sample step seconds"),
            curves.environment(),state.physics,state.x_final_m,
            state.buoyancy_variance_m2,
            state.initial_sigma_y_squared_m2,
            receptor_sy0,receptor_sz0,
            ctadj2_step,current_receptor_bvf,ws,original_qold_mixed,
            native_receptor_calm,receptor_vdpvd
        };
        receptor_increments=sampling_kernel(at_receptor);
        for(float increment:receptor_increments){
            if(!std::isfinite(increment))
                throw std::invalid_argument("CALCPF sampler returned nonfinite increment");
        }
        order.receptors_sampled();
    }
    v.commit_lid(id,mass.reflecting_lid_m,mass.puff_code);
    order.completed(VendorSubstepPhase::CommitNextStepHistory);
    order.finish();
    const auto post=v.state(id);
    require(post.completed_substeps==state.completed+1 &&
            post.committed_lid_steps==state.completed+1,
            "native rising COMP partial vertical commit");
    // SETPUF cancels remaining plume rise and persists calm midpoint
    // minima only after every component of this substep has succeeded.
    if(lcalm){
        state.x_final_m=0.0F;
        state.minimum_sigma_y_m=r4(sigma.adjust.minimum_sigma_y_m,"LCALM SY0");
        state.minimum_sigma_z_m=r4(sigma.adjust.minimum_sigma_z_m,"LCALM SZ0");
    }
    state.previous_wind_ms=ws;
    ++state.completed;
    RiseCompStep outcome{
        before,moved.state,post,sampled,rise,
        cadence,substep,bookkeeping,sigma,mass,end_height,
        std::move(receptor_increments),std::move(dry_result),
        original_qold_mixed,std::move(dry_input_resistance)
    };
    motion_=std::move(m);
    vertical_=std::move(v);
    found->second=std::move(state);
    return outcome;
}
NativeVerticalWind OriginalCompRisePointDriver::pre_cadence_wind(
    int id,const OriginalMetHour& met,const Calmet21Static& statics)const{
    const auto before=motion_.state(id);
    return vertical_.sample(id,met,statics,
        before.x_cells,before.y_cells,before.z_m);
}
OriginalPuffMotionState OriginalCompRisePointDriver::motion(int id)const{
    return motion_.state(id);
}
NativeVerticalPuffState OriginalCompRisePointDriver::vertical(int id)const{
    return vertical_.state(id);
}
std::size_t OriginalCompRisePointDriver::steps(int id)const{
    const auto it=rise_.find(id);
    if(it==rise_.end())throw std::out_of_range("unknown rising puff");
    return it->second.completed;
}
std::size_t OriginalCompRisePointDriver::active_count()const noexcept{
    return rise_.size();
}
void OriginalCompRisePointDriver::retire(int id) {
    require(rise_.contains(id),"unknown native rise puff retire");
    auto m=motion_;
    auto v=vertical_;
    m.retire(id);
    v.retire(id);
    motion_=std::move(m);
    vertical_=std::move(v);
    rise_.erase(id);
}
} // namespace cteas::puff
