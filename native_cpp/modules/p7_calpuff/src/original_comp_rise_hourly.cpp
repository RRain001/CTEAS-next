#include "cteas/puff/original_comp_rise_hourly.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>

namespace cteas::puff {
namespace {
float native_point_wsnew(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const OriginalPointHourSource& source,float calm_threshold_ms) {
    OriginalReleaseWindRequest position{
        .x_cells=static_cast<float>(source.point.source_x_km),
        .y_cells=static_cast<float>(source.point.source_y_km),
        .release_height_m=static_cast<float>(source.point.effective_height_m),
        .calm_threshold_ms=calm_threshold_ms
    };
    const auto final=original_release_wind_metfm1(met,statics,position);
    position.release_height_m=static_cast<float>(source.point.stack_height_m);
    const auto stack=original_release_wind_metfm1(met,statics,position);
    // POINTS1 original: WSNEW = AMAX1(WS at HTSTAK, WS at HEFF).
    // Both WINDSET samples use original CALMET REAL*4, not caller WSNEW.
    return std::max(stack.wind_speed_ms,final.wind_speed_ms);
}
} // namespace

OriginalPointHourSource original_point_hour_from_prfin(
    const OriginalPointPrfinRequest& in,
    const OriginalPointPrfinResult& rise,
    const OriginalPointNativeSourceParameters& src) {
    if(!std::isfinite(src.base_elevation_m)||
       !std::isfinite(src.met_spacing_m)||src.met_spacing_m<=0.0F||
       !std::isfinite(src.initial_sigma_y_m)||src.initial_sigma_y_m<=0.0F||
       !std::isfinite(src.initial_sigma_z_m)||src.initial_sigma_z_m<=0.0F||
       src.emission_rates.empty()||
       !std::all_of(src.emission_rates.begin(),src.emission_rates.end(),
            [](double q){return std::isfinite(q)&&q>=0.0;})||
       !(rise.stability_class>=1 && rise.stability_class<=6)||
       (rise.stability_class>=5 &&
        (!in.use_calmet_profile_lapse ||
         !std::isfinite(rise.sqrt_stability_s) ||
         rise.sqrt_stability_s<=0.0F))||
       // Original POINTS1 L15603 permits HEFF below HTSTAK from
       // tip downwash; the PRFIN result already rejects <=0 and NaN.
       !(std::isfinite(rise.effective_height_m) && rise.effective_height_m>0.0F)||
       // Original CALPUFF PRFIN explicitly sets XFINAL=0 at
       // WSSTK < WSSTK0=1.0 m/s while still producing a nonzero
       // vertical rise and genuine POINTS1 releases. Accept ONLY that
       // source-verified zero-distance branch, not arbitrary invalid
       // negative/non-finite rise data.
       !(rise.x_final_m>0.0F ||
         (rise.x_final_m==0.0F && rise.stack_wind_ms<1.0F &&
          rise.brigg.x_final_buoyancy_m==0.0 &&
          rise.brigg.x_final_momentum_m==0.0))||
       !(rise.buoyancy_variance_m2>=0.0F)||
       !(rise.release_wind_ms>=0.0F))
        throw std::invalid_argument("POINTS1 native admission lacks supported source physical data");
    const float sampling=in.hour_seconds/
        (src.met_spacing_m*in.max_sample_distance_cells);
    if(!std::isfinite(sampling)||sampling<=0.0F)
        throw std::invalid_argument("POINTS1 XTMP1 must be finite and positive");
    OriginalPointHourSource out;
    auto& point=out.point;
    point.source_type=1;
    point.source_x_km=in.x_cells; // original XPT1GRD: relative grid cells
    point.source_y_km=in.y_cells;
    point.base_elevation_m=src.base_elevation_m;
    point.sigma_y_source_m=src.initial_sigma_y_m; // original SYSRC
    point.sigma_z_source_m=src.initial_sigma_z_m; // original SZSRC
    point.initial_sigma_y_m=src.initial_sigma_y_m;
    point.initial_sigma_z_m=src.initial_sigma_z_m;
    point.effective_height_m=rise.effective_height_m;
    point.x_final_m=rise.x_final_m;
    point.final_rise_variance_m2=rise.buoyancy_variance_m2;
    point.buoyancy_flux=rise.buoyancy_flux;
    point.momentum_flux=rise.momentum_flux;
    point.x_final_buoyancy_m=rise.brigg.x_final_buoyancy_m;
    point.x_final_momentum_m=rise.brigg.x_final_momentum_m;
    point.z_final_buoyancy_m=rise.brigg.z_final_buoyancy_m;
    point.z_final_momentum_m=rise.brigg.z_final_momentum_m;
    point.stack_tip_downwash_m=rise.stack_tip_downwash_m;
    point.stack_height_m=in.stack_height_m;
    point.exit_velocity_ms=in.exit_velocity_ms;
    point.diameter_m=in.diameter_m;
    point.stack_wind_speed_ms=rise.stack_wind_ms;
    point.stability_class=rise.stability_class;
    point.sqrt_stability_s=rise.sqrt_stability_s; // RLSMET real source SQRTS
    point.downwash_code=0; // this source factory accepts no building
    // The receiver terrain and deposition controls remain separately
    // mandatory for a real full-case comparison.
    auto& mass=out.mass;
    mass.species_count=static_cast<int>(src.emission_rates.size());
    mass.emission_duration_s=rise.release.emission_duration_s;
    mass.effective_height_m=rise.effective_height_m;
    mass.mixing_height_m=rise.mixing_height_m;
    mass.max_layer_height_m=rise.max_layer_height_m;
    mass.mass_fraction_mixed=rise.mixed_fraction;
    mass.stability_class=rise.stability_class;
    mass.gaussian_distribution=1;
    mass.emission_rate=src.emission_rates;
    out.cadence.wind_speed_ms=rise.release_wind_ms;
    out.cadence.emission_interval=sampling;
    out.cadence.max_puffs=in.max_new_puffs;
    out.cadence.hour_seconds=in.hour_seconds;
    if(release_cadence(out.cadence).puff_count!=rise.release.puff_count||
       static_cast<float>(release_cadence(out.cadence).emission_duration_s)!=
           static_cast<float>(rise.release.emission_duration_s))
        throw std::logic_error("POINTS1 PRFIN source and release cadence disagree");
    return out;
}

RiseCompHour OriginalCompRiseMultiPuffHours::advance_hour(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const std::vector<RisePointAdmission>& admissions) {
    int last=last_id_;
    for(const auto& admission:admissions){
        if(admission.puff_id<=last)
            throw std::invalid_argument("noncanonical rising point release IDs");
        last=admission.puff_id;
    }
    // Copy *all* native rise, motion and mass state at the hour boundary.
    // No puff (old or newly admitted) is committed if ANY puff fails.
    auto trial=puffs_;
    auto ids=active_ids_;
    for(const auto& a:admissions){
        trial.admit(a.puff_id,a.point,a.mass);
        ids.push_back(a.puff_id);
    }
    RiseCompHour result;
    result.hour_index=hours_;
    result.puffs.reserve(ids.size());
    for(const int id:ids){
        result.puffs.push_back({id,
            trial.step_pg_rise(id,met,statics,controls,pg,urban)});
    }
    result.active_after=ids.size();
    puffs_=std::move(trial);
    active_ids_=std::move(ids);
    last_id_=last;
    ++hours_;
    return result;
}

RiseCadencedHour OriginalCompRiseMultiPuffHours::advance_hour_point_native_wsnew(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource& source,
    float calm_threshold_ms) {
    // Exact original POINTS1 L15448 and L15965-15970: first RLSMET at
    // HTSTAK, then RLSMET at PRFIN effective height HEFF. WSNEW must use
    // AMAX1(stack WS, final-rise WS), never only the final-rise wind.
    auto native=source;
    native.cadence.wind_speed_ms=native_point_wsnew(
        met,statics,source,calm_threshold_ms);
    return advance_hour_point_cadence(
        met,statics,controls,pg,urban,native);
}

RiseCadencedHour OriginalCompRiseMultiPuffHours::advance_hour_point_cadence(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource& source) {
    if(!std::isfinite(controls.seconds) || controls.seconds<=0.0F ||
       controls.max_sampling_steps!=1 || controls.release_number!=1 ||
       !std::isfinite(source.cadence.hour_seconds) ||
       static_cast<float>(source.cadence.hour_seconds)!=controls.seconds ||
       source.point.source_type!=1 ||
       source.mass.step_index!=0 || source.mass.species_count<1 ||
       last_id_>std::numeric_limits<int>::max()-source.cadence.max_puffs)
       throw std::invalid_argument("POINTS1 cadence requires one finite full hour / point-puff path");

    // POINTS1 L15975-16002, itself independently compared to ORIGINAL.
    const ReleaseCadence cadence=release_cadence(source.cadence);
    const float dt=static_cast<float>(cadence.emission_duration_s);
    if(!std::isfinite(dt) || dt<=0.0F ||
       cadence.puff_count<1 || cadence.new_puffs!=cadence.puff_count)
       throw std::invalid_argument("invalid native REAL4 POINTS1 emission duration");

    // Copy all active puffs; the entire hour is one atomic transaction.
    auto trial=puffs_;
    auto ids=active_ids_;
    int next_id=last_id_;
    RiseCadencedHour result;
    result.hour_index=hours_;
    result.cadence=cadence;
    result.new_puffs=static_cast<std::size_t>(cadence.puff_count);
    const std::size_t old_count=ids.size();
    result.steps.reserve(old_count+
                         static_cast<std::size_t>(cadence.puff_count)*
                         static_cast<std::size_t>(cadence.puff_count+1)/2U);

    // Existing puffs get their full hour. The original may divide old
    // puff trajectories further for MXSAM>1; explicitly refuse that here.
    for(const int id:ids){
        const auto sub=trial.step_pg_rise(
            id,met,statics,controls,pg,urban);
        result.steps.push_back({id,0,1,sub});
    }

    for(int j=1;j<=cadence.puff_count;++j) {
        const int id=++next_id;
        auto point=source.point;
        auto mass=source.mass;
        point.release_index=j;
        point.emission_duration_s=dt;   // TEMIT0 / DT, original REAL*4
        mass.emission_duration_s=dt;    // INJECT: QM+QU = Q*DT
        trial.admit(id,point,mass);
        ids.push_back(id);
        auto partial=controls;
        partial.seconds=dt;
        partial.source_period_s=dt;
        // CALPUFF new puff releases start on slot IPNO (not the beginning
        // of the hour). The initial remaining age after this hour is
        // (NPUFFS-J+1)*DT; every substep is native GRISE+PG+VMASS.
        for(int k=j;k<=cadence.puff_count;++k) {
            const auto sub=trial.step_pg_rise(
                id,met,statics,partial,pg,urban);
            result.steps.push_back({id,j,k,sub});
        }
    }
    result.active_after=ids.size();
    puffs_=std::move(trial);
    active_ids_=std::move(ids);
    last_id_=next_id;
    ++hours_;
    return result;
}

OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_point_mxsam99_native_wsnew_unsplit(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource& source,
    float calm_threshold_ms) {
    // Join the source-faithful release wind to the real MXSAM=99 scheduler.
    // Only the unsplit physical subcase is accepted: the downstream COMP
    // rejects any required FSTEP resplit, calm old-puff path or off-grid exit.
    auto native=source;
    native.cadence.wind_speed_ms=native_point_wsnew(
        met,statics,source,calm_threshold_ms);
    return advance_hour_point_mxsam99_unsplit(
        met,statics,controls,pg,urban,native);
}

OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_point_mxsam99_native_wsnew_unsplit_rolldn(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource& source,
    float calm_threshold_ms,const std::vector<int>& inactive_old_ids) {
    // Fortran POINTS1/ROLLDN/SWAP packs the old puff slots, then new
    // admissions are appended. Keep the original COPY (not std::swap)
    // slot permutation in the transient driver, and atomically commit
    // compaction AND the complete hour only after every substep succeeds.
    // Existing active episode IDs are stable while their array slots move.
    auto trial=*this;
    (void)trial.compact_original_inactive(inactive_old_ids);
    auto result=trial.advance_hour_point_mxsam99_native_wsnew_unsplit(
        met,statics,controls,pg,urban,source,calm_threshold_ms);
    *this=std::move(trial);
    return result;
}

OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_point_mxsam99_native_wsnew_adaptive(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource& source,
    float calm_threshold_ms) {
    auto native=source;
    native.cadence.wind_speed_ms=native_point_wsnew(
        met,statics,source,calm_threshold_ms);
    return advance_hour_point_mxsam99_adaptive(
        met,statics,controls,pg,urban,native);
}

OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_point_mxsam99_adaptive(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource& source) {
    return advance_hour_mxsam99_source_order(
        met,statics,controls,pg,urban,source,true);
}

OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_point_mxsam99_unsplit(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource& source) {
    return advance_hour_mxsam99_source_order(
        met,statics,controls,pg,urban,source,false);
}

OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_existing_mxsam99_adaptive(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,bool urban) {
    return advance_hour_mxsam99_core(
        met,statics,controls,pg,urban,nullptr,true);
}

OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_existing_mxsam99_adaptive_bounded(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalCompPuffBounds& bounds) {
    return advance_hour_mxsam99_core(
        met,statics,controls,pg,urban,nullptr,true,&bounds);
}

OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_point_mxsam99_adaptive_bounded(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource& source,
    const OriginalCompPuffBounds& bounds) {
    return advance_hour_mxsam99_core(
        met,statics,controls,pg,urban,&source,true,&bounds);
}

OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_mxsam99_source_order(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource& source,bool adaptive) {
    return advance_hour_mxsam99_core(
        met,statics,controls,pg,urban,&source,adaptive);
}

OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_mxsam99_core(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource* source,bool adaptive,
    const OriginalCompPuffBounds* bounds,bool deferred_original_rolldn,
    const RiseCompSamplingKernel* sampling_kernel,
    std::size_t receptor_values) {
    if(capacity_slots_ && !deferred_original_rolldn)
        throw std::logic_error("capacity-controlled COMP cannot mix legacy schedulers");
    if(deferred_original_rolldn && !capacity_slots_)
        throw std::logic_error("capacity-controlled COMP requires admission inventory");
    if(controls.max_sampling_steps!=99 || controls.release_number!=1 ||
       !std::isfinite(controls.met_spacing_m) ||
       controls.met_spacing_m<=0.0F ||
       !std::isfinite(controls.max_sample_distance_cells) ||
       controls.max_sample_distance_cells<=0.0F ||
       controls.seconds!=3600.0F ||
       (source!=nullptr &&
        (source->cadence.hour_seconds!=3600.0 ||
         source->point.source_type!=1 ||
         source->mass.step_index!=0 ||
         source->cadence.max_puffs>99 ||
         last_id_>std::numeric_limits<int>::max()-99)))
        throw std::invalid_argument(
            "original COMP MXSAM99 point-puff scope invalid");
    // No releases is a valid history-continuation hour (no POINTS1).
    const ReleaseCadence release=source
        ?release_cadence(source->cadence):ReleaseCadence{};
    const float dt=static_cast<float>(release.emission_duration_s);
    if(source && (!std::isfinite(dt)||dt<=0 || release.puff_count<1))
        throw std::invalid_argument("invalid source-ported NPUFFS/DT");

    // Fail closed on absent/invalid ORIGINAL CALPUFF XB/XE/YB/YE; do not
    // infer bounds from CALMET NX/NY (distinct coordinate authorities).
    if(bounds)
        (void)original_comp_after_step_exit(bounds->xb,bounds->yb,*bounds);
    // Entire hour is a single transaction, including all old puff states,
    // newly admitted POINTS1 puffs, every re-entry and vertical mass/lid.
    auto trial=puffs_;
    auto ids=active_ids_;
    int next_id=last_id_;
    OriginalCompMxsamHour result;
    result.hour_index=hours_;
    result.release=release;
    if(sampling_kernel){
        if(!*sampling_kernel || receptor_values==0)
            throw std::invalid_argument("CALCPF sampler needs nonempty kernel and receptors");
        result.receptor_concentrations.assign(receptor_values,0.0F);
    }
    const auto mark_retired=[&](int id,OriginalCompExitReason why){
        if(why==OriginalCompExitReason::Active)
            throw std::logic_error("COMP invalid active retirement request");
        for(const auto& item:result.retired)
            if(item.puff_id==id)
                throw std::logic_error("COMP retired the same puff twice");
        const auto v=trial.vertical(id);
        result.retired.push_back({
            id,why,trial.motion(id),v.mass_mixed,v.mass_above
        });
    };
    const auto execute=[&](int id,int rel,const SamplingCadence& plan){
        const float reference=static_cast<float>(plan.reference_step_s);
        if(!std::isfinite(reference) || reference<=0.0F ||
           plan.start_substep<1 || plan.sampling_steps<plan.start_substep ||
           plan.sampling_steps>99)
            throw std::invalid_argument("COMP invalid source sampling plan");
        float tleft=0.0F; // source L10348
        for(int k=plan.start_substep;k<=plan.sampling_steps;++k){
            // Original COMP L10450-10457: zero total QM+QU kills this
            // puff BEFORE fetching the next wind or advancing position.
            if(bounds){
                const auto vertical=trial.vertical(id);
                const auto reason=original_comp_before_step_exit(
                    vertical.mass_mixed,vertical.mass_above);
                if(reason!=OriginalCompExitReason::Active){
                    mark_retired(id,reason);
                    return;
                }
            }
            // Original L10430-10433: excess time carries to next KSAM.
            float tsamp=static_cast<float>(reference+tleft);
            tleft=tsamp;
            unsigned reentries=0;
            for(;;){ // original L10445 label 500
                if(!std::isfinite(tsamp)||tsamp<=0.0F ||
                   ++reentries>8192U)
                    throw std::invalid_argument(
                        "COMP FSTEP nonprogress or unbounded re-entry");
                auto ctrl=controls;
                ctrl.seconds=tsamp;
                ctrl.source_period_s=tsamp;
                ctrl.release_number=1;
                ctrl.max_sampling_steps=1;
                const auto physics=[&](){
                    try {
                        return trial.step_pg_rise(
                            id,met,statics,ctrl,pg,urban,
                            {.ksam=k,.nsam=plan.sampling_steps,
                             .lsubsam=adaptive && plan.subsampling},
                            sampling_kernel?*sampling_kernel:RiseCompSamplingKernel{});
                    } catch(const std::exception& failure) {
                        // No change to the COMP transaction or REAL4 math.
                        // Identify the earliest failing old/new episode,
                        // KSAM and exact pre-step puff centre for domain audit.
                        const auto centre=trial.motion(id);
                        const std::string message=
                            "P7 COMP phase=physical_substep HOUR="+
                            std::to_string(hours_+1U)+" PUFF="+
                            std::to_string(id)+" KSAM="+
                            std::to_string(k)+" X_CELLS="+
                            std::to_string(centre.x_cells)+" Y_CELLS="+
                            std::to_string(centre.y_cells)+" : "+failure.what();
                        // Preserve original exception categories: the
                        // unsupported CALM and other fail-closed callers
                        // explicitly require std::invalid_argument.
                        if(dynamic_cast<const std::invalid_argument*>(&failure))
                            throw std::invalid_argument(message);
                        if(dynamic_cast<const std::out_of_range*>(&failure))
                            throw std::out_of_range(message);
                        throw std::runtime_error(message);
                    }
                }();
                const float used=static_cast<float>(physics.substep.step_s);
                if(!(used>0.0F && used<=tsamp && std::isfinite(used)))
                    throw std::logic_error("invalid native COMP effective TSAMP");
                if(!adaptive){
                    // Keep the historical restricted unsplit contract and
                    // fail atomically if the real source would shorten it.
                    const auto would_split=substep_length({
                        .sampling_step_s=tsamp,
                        .wind_speed_ms=physics.rise.adjusted.wind_speed_ms,
                        .puff=true,.free_slug=false,
                        .subsampling=plan.subsampling,
                        .grid_spacing_m=controls.met_spacing_m,
                        .x_sam_len=controls.max_sample_distance_cells,
                        .substep_index=k,.sampling_steps=plan.sampling_steps
                    });
                    if(would_split.split ||
                       static_cast<float>(would_split.step_s)!=tsamp)
                        throw std::invalid_argument(
                            "COMP requires FSTEP split: use adaptive scheduler");
                }
                if(physics.substep.split)++result.fstep_shortened_steps;
                if(sampling_kernel){
                    if(physics.receptor_increments.size()!=receptor_values)
                        throw std::invalid_argument("CALCPF receptor field size drift");
                    for(std::size_t j=0;j<receptor_values;++j){
                        const float next=result.receptor_concentrations[j]+
                                         physics.receptor_increments[j];
                        if(!std::isfinite(next))
                            throw std::overflow_error("CALCPF hourly REAL4 accumulation overflow");
                        result.receptor_concentrations[j]=next;
                    }
                }
                result.steps.push_back({id,rel,k,plan,physics});
                // Original COMP L11400-L11413: only after the actual
                // native substep, test PUFF CENTER (not sigma footprint).
                // An exited puff must never be sampled in another KSAM.
                if(bounds){
                    const auto reason=original_comp_after_step_exit(
                        physics.after.x_cells,physics.after.y_cells,*bounds);
                    if(reason!=OriginalCompExitReason::Active){
                        mark_retired(id,reason);
                        return;
                    }
                }
                // Original L10581 and L11475-11492, in REAL*4 order.
                tleft=static_cast<float>(tleft-used);
                const bool repeat=adaptive && plan.subsampling &&
                    ((tleft>=1.0F && k==plan.sampling_steps) ||
                     (tleft>used));
                if(!repeat)break;
                tsamp=tleft;
                ++result.fstep_reentries;
            }
        }
    };
    for(const int id:ids){
        const auto native=[&]() {
            try {
                return trial.pre_cadence_wind(id,met,statics);
            } catch(const std::exception& failure) {
                const auto centre=trial.motion(id);
                const std::string message=
                    "P7 COMP phase=old_puff_pre_cadence HOUR="+
                    std::to_string(hours_+1U)+" PUFF="+
                    std::to_string(id)+" X_CELLS="+
                    std::to_string(centre.x_cells)+" Y_CELLS="+
                    std::to_string(centre.y_cells)+" : "+failure.what();
                if(dynamic_cast<const std::invalid_argument*>(&failure))
                    throw std::invalid_argument(message);
                if(dynamic_cast<const std::out_of_range*>(&failure))
                    throw std::out_of_range(message);
                throw std::runtime_error(message);
            }
        }();
        const float u=static_cast<float>(native.wind.u_ms);
        const float v=static_cast<float>(native.wind.v_ms);
        const float ws=std::sqrt(u*u+v*v);
        // Pre-cadence wind is NOT the final post-RISEWIND puff wind.
        // Reject non-finite inputs, but do not impose WSCALM here:
        // COMP determines LCALM for each actual physical KSAM/FSTEP.
        // Premature rejection incorrectly conflated CALMET-source low
        // wind with CALPUFF's puff-specific post-RISEWIND treatment.
        if(!std::isfinite(ws)||ws<0.0F)
            throw std::invalid_argument("original COMP pre-cadence wind invalid");
        const auto plan=sampling_cadence({
            .new_puff=false,.step_seconds=controls.seconds,
            .wind_speed_ms=ws,
            .x_sam_len=controls.max_sample_distance_cells,
            .grid_spacing_m=controls.met_spacing_m,
            .max_sampling_steps=99
        });
        execute(id,0,plan);
    }
    for(int j=1;j<=release.puff_count;++j){
        auto point=source->point;
        auto mass=source->mass;
        point.release_index=j;
        point.emission_duration_s=dt;
        mass.emission_duration_s=dt;
        const int id=++next_id;
        trial.admit(id,point,mass);
        ids.push_back(id);
        const auto plan=sampling_cadence({
            .new_puff=true,.source_type=1,
            .emission_period_s=dt,.step_seconds=controls.seconds,
            .release_number=j,
            .wind_speed_ms=source->cadence.wind_speed_ms,
            .x_sam_len=controls.max_sample_distance_cells,
            .grid_spacing_m=controls.met_spacing_m,
            .max_sampling_steps=99
        });
        if(plan.sampling_steps!=release.puff_count)
            throw std::invalid_argument("native POINTS1/COMP NEW NSAM drift");
        execute(id,j,plan);
    }
    if(bounds && deferred_original_rolldn && !result.retired.empty()){
        // Vendor COMP writes ICODE=99 and SKIPS it until a later POINTS1
        // MXPUFF capacity trigger. Release physical states, but retain
        // those inactive historical ARRAY SLOTS in capacity_slots_.
        for(const auto& item:result.retired)trial.retire(item.puff_id);
        ids.erase(std::remove_if(ids.begin(),ids.end(),
            [&](int id){return std::any_of(result.retired.begin(),result.retired.end(),
                [id](const auto& item){return item.puff_id==id;});}),ids.end());
    } else if(bounds && !result.retired.empty()){
        // Source-ported ROLLDN slot COPY, not std::swap, with immutable
        // physical episode IDs. The original invokes ROLLDN conditionally
        // on MXPUFF pressure; this opt-in eager compact is NOT that full
        // original call timing and must be gated separately.
        std::vector<OriginalPuffSlot> slots;
        slots.reserve(ids.size());
        for(int id:ids){
            bool expired=false;
            for(const auto& entry:result.retired)
                if(entry.puff_id==id){expired=true;break;}
            slots.push_back({id,expired?99:trial.vertical(id).puff_code});
        }
        const auto packed=original_rolldn_slots(slots,ids.size());
        for(const auto& item:result.retired)trial.retire(item.puff_id);
        ids.clear();
        for(const auto& slot:packed.slots)ids.push_back(slot.state_id);
        if(packed.retired_old!=result.retired.size())
            throw std::logic_error("COMP ROLLDN lost a native retirement");
    }
    result.active_puffs=ids.size();
    puffs_=std::move(trial);
    active_ids_=std::move(ids);
    last_id_=next_id;
    ++hours_;
    return result;
}

std::size_t OriginalCompRiseMultiPuffHours::compact_original_inactive(
    const std::vector<int>& dead_ids){
    if(dead_ids.empty())return 0;
    std::vector<OriginalPuffSlot> slots;
    slots.reserve(active_ids_.size());
    for(const int id:active_ids_){
        const auto state=puffs_.vertical(id);
        const bool dead=std::find(dead_ids.begin(),dead_ids.end(),id)!=dead_ids.end();
        slots.push_back({id,dead?99:state.puff_code});
    }
    // Reject phantom/duplicate dead IDs before changing physical state.
    for(const int id:dead_ids){
        const auto it=std::find(active_ids_.begin(),active_ids_.end(),id);
        if(it==active_ids_.end() ||
           std::count(dead_ids.begin(),dead_ids.end(),id)!=1)
            throw std::invalid_argument("ROLDN inactive puff ID invalid");
    }
    const auto plan=original_rolldn_slots(slots,slots.size());
    std::vector<int> reordered;
    reordered.reserve(plan.slots.size());
    for(const auto& slot:plan.slots)
        reordered.push_back(slot.state_id);
    auto trial=puffs_;
    for(const int id:active_ids_)
        if(std::find(reordered.begin(),reordered.end(),id)==reordered.end())
            trial.retire(id);
    // Full atomic update across all motion and vertical stores.
    puffs_=std::move(trial);
    active_ids_=std::move(reordered);
    return plan.retired_old;
}
OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource& source,
    const OriginalCompPuffBounds& bounds,std::size_t mxpuff,
    std::size_t receptor_values,const RiseCompSamplingKernel& kernel) {
    return advance_hour_capacity(
        met,statics,controls,pg,urban,&source,bounds,mxpuff,&kernel,receptor_values);
}
OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_point_mxsam99_adaptive_bounded_capacity(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource& source,
    const OriginalCompPuffBounds& bounds,std::size_t mxpuff) {
    return advance_hour_capacity(
        met,statics,controls,pg,urban,&source,bounds,mxpuff);
}
OriginalCompMxsamHour
OriginalCompRiseMultiPuffHours::advance_hour_existing_mxsam99_adaptive_bounded_capacity(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalCompPuffBounds& bounds,std::size_t mxpuff) {
    return advance_hour_capacity(
        met,statics,controls,pg,urban,nullptr,bounds,mxpuff);
}
const OriginalPuffCapacityInventory&
OriginalCompRiseMultiPuffHours::capacity_inventory()const {
    if(!capacity_slots_)throw std::logic_error("capacity mode not initialized");
    return *capacity_slots_;
}
OriginalCompMxsamHour OriginalCompRiseMultiPuffHours::advance_hour_capacity(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,const DispersionSetup& pg,
    bool urban,const OriginalPointHourSource* source,
    const OriginalCompPuffBounds& bounds,std::size_t mxpuff,
    const RiseCompSamplingKernel* sampling_kernel,
    std::size_t receptor_values) {
    // The inventory, source, physical puffs, ages and hour counter all
    // roll back if capacity, meteorology or substep physics fail.
    auto trial=*this;
    if(!trial.capacity_slots_) {
        if(trial.hours_!=0||!trial.active_ids_.empty())
            throw std::logic_error("capacity mode must start from first COMP hour");
        trial.capacity_slots_.emplace(mxpuff);
    }
    if(trial.capacity_slots_->limit()!=mxpuff)
        throw std::invalid_argument("MXPUFF cannot change during a run");
    const auto new_release=source?release_cadence(source->cadence):
                           ReleaseCadence{};
    const std::size_t incoming=static_cast<std::size_t>(new_release.puff_count);
    const auto decision=trial.capacity_slots_->prepare_release(incoming);
    const auto live=trial.capacity_slots_->active_ids();
    if(live.size()!=trial.active_ids_.size())
        throw std::logic_error("COMP puff state / capacity slots disagree");
    // Original ROLLDN changes mutable Fortran slots before POINTS1 emits,
    // preserving the physical episode state keyed by its stable ID.
    trial.active_ids_=live;
    const int old_last=trial.last_id_;
    auto result=trial.advance_hour_mxsam99_core(
        met,statics,controls,pg,urban,source,true,&bounds,true,
        sampling_kernel,receptor_values);
    if(source && static_cast<std::size_t>(trial.last_id_-old_last)!=incoming)
        throw std::logic_error("POINTS1 new releases differ from capacity admission");
    for(int id=old_last+1;id<=trial.last_id_;++id) {
        const auto retired=std::any_of(result.retired.begin(),result.retired.end(),
            [id](const auto& r){return r.puff_id==id;});
        trial.capacity_slots_->append(id,retired?1:trial.puffs_.vertical(id).puff_code);
    }
    for(const auto& r:result.retired)trial.capacity_slots_->retire(r.puff_id);
    // Persist latest active ICODE values for a later vendor ROLLDN.
    for(const int id:trial.active_ids_)
        trial.capacity_slots_->update_code(id,trial.puffs_.vertical(id).puff_code);
    if(trial.capacity_slots_->active_ids()!=trial.active_ids_)
        throw std::logic_error("original active slot order and native puff state drift");
    result.capacity_rolldn_triggered=decision.rolled_down;
    result.capacity_rolldn_removed=decision.removed_inactive;
    result.occupied_slots_after=trial.capacity_slots_->occupied();
    result.inactive_slots_after=trial.capacity_slots_->inactive();
    *this=std::move(trial);
    return result;
}
OriginalPuffMotionState OriginalCompRiseMultiPuffHours::motion(int id)const {
    return puffs_.motion(id);
}
NativeVerticalPuffState OriginalCompRiseMultiPuffHours::vertical(int id)const{
    return puffs_.vertical(id);
}
std::size_t OriginalCompRiseMultiPuffHours::puff_steps(int id)const{
    return puffs_.steps(id);
}
std::size_t OriginalCompRiseMultiPuffHours::completed_hours()const noexcept{
    return hours_;
}
std::size_t OriginalCompRiseMultiPuffHours::active_count()const noexcept{
    return active_ids_.size();
}
const std::vector<int>& OriginalCompRiseMultiPuffHours::canonical_ids()const noexcept{
    return active_ids_;
}
void OriginalCompRiseMultiPuffHours::retire(int id){
    if(std::find(active_ids_.begin(),active_ids_.end(),id)==active_ids_.end())
        throw std::out_of_range("retire unknown rising puff");
    auto next=puffs_;
    next.retire(id);
    puffs_=std::move(next);
    active_ids_.erase(
        std::remove(active_ids_.begin(),active_ids_.end(),id),
        active_ids_.end());
}
} // namespace cteas::puff
