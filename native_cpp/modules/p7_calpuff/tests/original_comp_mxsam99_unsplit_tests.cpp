#include "cteas/puff/original_comp_rise_hourly.hpp"
#include "cteas/puff/receptors.hpp"
#include "cteas/puff/original_flat_calcpf.hpp"
#include "cteas/puff/original_pufrecs_geometry.hpp"
#include "cteas/puff/original_native_terrain.hpp"
#include "cteas/puff/hourly_conc.hpp"
#include <algorithm>
#include <bit>
#include <chrono>
#include <filesystem>
#include <cstdint>
#include <cmath>
#include <iostream>
#include <optional>
#include <stdexcept>
using namespace cteas::puff;
namespace {
void need(bool v,const char* s){if(!v)throw std::runtime_error(s);}
void test(){
    OriginalCompRiseMultiPuffHours driver;
    OriginalMetHour met;
    met.nx=120;met.ny=120;met.nz=3;
    const auto n=120U*120U;
    met.zi.assign(n,250.0F);
    met.ipgt.assign(n,4);
    met.u.assign(n*3,1.2F);
    met.v.assign(n*3,0.0F);
    Calmet21Static geo;
    geo.cell_face_m={0,100,200,300};
    geo.roughness_m.assign(n,0.25F);
    NeutralCompControls ctl;
    ctl.max_sampling_steps=99;
    ctl.met_spacing_m=100.0F;
    ctl.max_sample_distance_cells=1.0F;
    ctl.seconds=3600.0F;
    ctl.source_period_s=3600.0F;
    DispersionSetup pg;
    pg.mdisp=3;pg.averaging_factor=1;
    pg.sigma_y_heffter_m=550;
    pg.heffter_sigma_z=false;pg.roughness_adjustment=false;
    OriginalPointHourSource source;
    source.point.source_x_km=5;
    source.point.source_y_km=5;
    source.point.stack_height_m=50;
    source.point.effective_height_m=160;
    source.point.x_final_m=230;
    source.point.buoyancy_flux=49;
    source.point.x_final_buoyancy_m=230;
    source.point.z_final_buoyancy_m=110;
    source.point.stack_wind_speed_ms=1.2;
    source.point.sigma_y_source_m=1;
    source.point.sigma_z_source_m=1;
    source.point.stability_class=4;
    source.mass.species_count=2;
    source.mass.emission_duration_s=3600;
    source.mass.effective_height_m=160;
    source.mass.mixing_height_m=250;
    source.mass.max_layer_height_m=300;
    source.mass.mass_fraction_mixed=1;
    source.mass.stability_class=4;
    source.mass.gaussian_distribution=1;
    source.mass.emission_rate={2,3};
    source.cadence.wind_speed_ms=1.2;
    source.cadence.emission_interval=36.0;
    source.cadence.max_puffs=99;
    source.cadence.hour_seconds=3600;
    const auto a=driver.advance_hour_point_mxsam99_unsplit(
        met,geo,ctl,pg,false,source);
    need(a.release.puff_count==44 &&
         a.active_puffs==44 &&
         a.steps.size()==44U*45U/2U &&
         driver.completed_hours()==1,
         "MXSAM99 new release slots absent");
    for(const auto& s:a.steps){
        need(s.release_number>0 &&
             s.original_plan.sampling_steps==44 &&
             s.original_plan.start_substep==s.release_number &&
             s.ksam>=s.release_number &&
             s.step.after.x_cells>s.step.before.x_cells,
             "native original new MXSAM99 rise/PG step drift");
    }
    const auto b=driver.advance_hour_point_mxsam99_unsplit(
        met,geo,ctl,pg,false,source);
    need(b.active_puffs==88 &&
         driver.completed_hours()==2,
         "second rising MXSAM99 hour not committed");
    std::size_t old_steps=0;
    for(const auto& s:b.steps){
        if(s.release_number==0){
            ++old_steps;
            need(s.original_plan.sampling_steps==44 &&
                 s.original_plan.start_substep==1 &&
                 s.original_plan.old_flag==1,
                 "old puff NSAM99 selected wrong vendor cadence");
        }
        need(s.step.vertical_after.committed_lid_steps>0 &&
             s.step.after.x_cells>s.step.before.x_cells,
             "native PG/VMASS substep did not move puff");
    }
    need(old_steps==44U*44U,
         "old puff multi-step COMP execution omitted slots");
    // Integrated POINTS1 -> original RLSMET WINDSET at stack AND HEFF ->
    // MXSAM=99 COMP. The caller's deliberately incorrect WSNEW must not be
    // used. Stack level 1.5 m/s dominates final-rise level 1.2 m/s;
    // original POINTS1 uses INT(1.5*36)+1 = 55 releases, not 44 or 1.
    OriginalCompRiseMultiPuffHours native_wind_driver;
    auto native_wind_met=met;
    for(std::size_t cell=0;cell<n;++cell)
        native_wind_met.u[cell]=1.5F;  // HTSTAK=50 m, layer 1
    auto native_wind_source=source;
    native_wind_source.cadence.wind_speed_ms=0.001;
    const auto native_wind_hour=
        native_wind_driver.advance_hour_point_mxsam99_native_wsnew_unsplit(
            native_wind_met,geo,ctl,pg,false,native_wind_source,0.5F);
    need(native_wind_hour.release.puff_count==55 &&
         native_wind_hour.active_puffs==55 &&
         native_wind_hour.steps.size()==55U*56U/2U &&
         native_wind_driver.completed_hours()==1,
         "native RLSMET stack/HEFF max not connected to MXSAM99 release");
    for(const auto& step:native_wind_hour.steps)
        need(step.original_plan.sampling_steps==55 &&
             step.release_number>=1 &&
             step.ksam>=step.release_number,
             "MXSAM99 native WSNEW did not reach original NSAM selection");
    // The second hour selects a fresh release speed from its OWN MET
    // profile (stack 1.0 m/s, HEFF 1.2 m/s), while independently
    // advancing the 55 persisted old native puffs from hour one.
    auto second_native_met=native_wind_met;
    for(std::size_t cell=0;cell<n;++cell)
        second_native_met.u[cell]=1.0F;
    const auto second_native_hour=
        native_wind_driver.advance_hour_point_mxsam99_native_wsnew_unsplit(
            second_native_met,geo,ctl,pg,false,native_wind_source,0.5F);
    need(second_native_hour.release.puff_count==44 &&
         second_native_hour.active_puffs==99 &&
         native_wind_driver.completed_hours()==2,
         "hour-two fresh native WSNEW or cross-hour puff state diverged");
    std::size_t carried_old_steps=0;
    for(const auto& s:second_native_hour.steps)
        if(s.release_number==0)++carried_old_steps;
    need(carried_old_steps>=55U,
         "hour-two native WSNEW path dropped persisted old puff substeps");

    // Missing original meteorology must fail before any hour is committed.
    auto invalid_met=native_wind_met;
    invalid_met.u.clear();
    bool rejected=false;
    try {
        (void)native_wind_driver.advance_hour_point_mxsam99_native_wsnew_unsplit(
            invalid_met,geo,ctl,pg,false,native_wind_source,0.5F);
    } catch(const std::exception&) { rejected=true; }
    need(rejected && native_wind_driver.completed_hours()==2 &&
         native_wind_driver.active_count()==99,
         "native WSNEW failure partially committed a COMP hour");

    // One original-style POINTS1 transaction: compact two inactive old
    // slot episodes by vendor ROLLDN COPY order, then source-derived WSNEW
    // and MXSAM99 execute. Previously separated compaction would commit
    // retirement even if the subsequent hour later aborted.
    OriginalCompRiseMultiPuffHours packed_driver;
    const auto initial_packed=
        packed_driver.advance_hour_point_mxsam99_native_wsnew_unsplit(
            native_wind_met,geo,ctl,pg,false,native_wind_source,0.5F);
    need(initial_packed.active_puffs==55,
         "atomic ROLLDN setup lacks 55 old puff slots");
    const auto packed=
        packed_driver.advance_hour_point_mxsam99_native_wsnew_unsplit_rolldn(
            second_native_met,geo,ctl,pg,false,native_wind_source,
            0.5F,{2,4});
    const auto& order=packed_driver.canonical_ids();
    need(packed.release.puff_count==44 && packed.active_puffs==97 &&
         packed_driver.completed_hours()==2 && order.size()==97 &&
         order.at(0)==1 && order.at(1)==55 && order.at(2)==3 &&
         order.at(3)==54 && order.at(52)==53 && order.at(53)==56 &&
         order.back()==99,
         "vendor ROLLDN COPY slot order was not preserved into native COMP");
    bool retired2=false,retired4=false;
    try{(void)packed_driver.motion(2);}catch(const std::out_of_range&){retired2=true;}
    try{(void)packed_driver.vertical(4);}catch(const std::out_of_range&){retired4=true;}
    need(retired2 && retired4 && packed_driver.puff_steps(55)>0,
         "retired slots remain alive or ROLLDN copied state lost history");
    const auto prior=packed_driver.motion(1);
    const auto active_before=packed_driver.canonical_ids();
    auto broken_met=second_native_met;
    broken_met.u.clear();
    bool rollback=false;
    try {
        (void)packed_driver.advance_hour_point_mxsam99_native_wsnew_unsplit_rolldn(
            broken_met,geo,ctl,pg,false,native_wind_source,0.5F,{1});
    }catch(const std::exception&){rollback=true;}
    need(rollback && packed_driver.completed_hours()==2 &&
         packed_driver.active_count()==97 &&
         packed_driver.canonical_ids()==active_before &&
         packed_driver.motion(1).travel_time_s==prior.travel_time_s,
         "failing COMP hour retained a partial ROLLDN retirement");
    std::cout<<"P7_ROLLDN_NATIVE_MXSAM99_ATOMIC=PASS"
             <<" OLD_COPIES=2 NATIVE_NEW=44 ACTIVE=97"
             <<" VENDOR_SLOT_ORDER=YES ABORT_ROLLBACK=YES"
             <<" AUTONOMOUS_OFFDOMAIN=NOT_YET_ACCEPTED\\n";

    // Force a physically meaningful FSTEP > 1: only one newly released
    // puff (externally controlled release speed 0.001 m/s), but its actual
    // 3-D METFM1 wind is 1.2 m/s. Unlike the existing unsplit branch, the
    // new scheduler must shorten TSAMP, re-evaluate rising RISEWIND, and
    // use the original TLEFT/goto-500 loop without discarding puff state.
    auto fast=source;
    fast.cadence.wind_speed_ms=0.001;
    fast.cadence.emission_interval=36.0;
    OriginalCompRiseMultiPuffHours refused_split;
    bool fstep_refusal=false;
    try{(void)refused_split.advance_hour_point_mxsam99_unsplit(
        met,geo,ctl,pg,false,fast);}catch(const std::invalid_argument&){
        fstep_refusal=true;
    }
    need(fstep_refusal && refused_split.completed_hours()==0 &&
         refused_split.active_count()==0,
         "legacy unsplit COMP silently accepted forced FSTEP");
    OriginalCompRiseMultiPuffHours adaptive;
    const auto split_hour=adaptive.advance_hour_point_mxsam99_adaptive(
        met,geo,ctl,pg,false,fast);
    need(split_hour.release.puff_count==1 &&
         split_hour.active_puffs==1 &&
         split_hour.fstep_shortened_steps>0 &&
         split_hour.fstep_reentries>0 &&
         split_hour.steps.size()>1 &&
         adaptive.completed_hours()==1,
         "native FSTEP did not execute source TLEFT/substep reentries");
    double used_time=0.0;
    bool rising_resample=false;
    for(const auto& rec:split_hour.steps){
        need(rec.puff_id==1 && rec.ksam==1 &&
             rec.step.after.travel_time_s>rec.step.before.travel_time_s &&
             rec.step.vertical_after.committed_lid_steps>0 &&
             rec.step.substep.step_s>0.0,
             "native FSTEP resampling corrupted puff clock or lid");
        used_time+=rec.step.substep.step_s;
        if(rec.step.before.total_distance_m<230.0F &&
           rec.step.substep.split && rec.step.rise.adjusted.passes==2)
            rising_resample=true;
    }
    need(rising_resample &&
         std::abs(adaptive.motion(1).travel_time_s-3600.0F)<1.0F &&
         std::abs(used_time-3600.0)<1.0 &&
         adaptive.puff_steps(1)==split_hour.steps.size(),
         "native FSTEP lost full-hour time or rising puff state");
    const auto mass_state=adaptive.vertical(1);
    need(std::abs(mass_state.mass_mixed.at(0)+
                  mass_state.mass_above.at(0)-7200.0F)<0.1F &&
         std::abs(mass_state.mass_mixed.at(1)+
                  mass_state.mass_above.at(1)-10800.0F)<0.1F,
         "native FSTEP introduced source-mass drift");
    const auto saved=adaptive.motion(1);
    auto invalid_admission=fast;
    invalid_admission.point.source_x_km=130;
    bool adaptive_rollback=false;
    try{(void)adaptive.advance_hour_point_mxsam99_adaptive(
        met,geo,ctl,pg,false,invalid_admission);
    }catch(const std::exception&){adaptive_rollback=true;}
    need(adaptive_rollback && adaptive.completed_hours()==1 &&
         adaptive.active_count()==1 &&
         adaptive.motion(1).travel_time_s==saved.travel_time_s &&
         adaptive.motion(1).x_cells==saved.x_cells,
         "late FSTEP+POINTS1 error corrupted an earlier physical hour");
    std::cout<<"P7_NATIVE_FSTEP_TLEFT_REENTRY=PASS"
             <<" SOURCE_KSAM=1 RESAMPLE_RISEWIND=YES"
             <<" FULL_HOUR_MOTION=YES MASS_CONSERVED=YES"
             <<" ATOMIC_ROLLBACK=YES"
             <<" ORIGINAL_FROZEN_143H_NOT_YET_ACCEPTED=YES\\n";

    // Across-hour native state authority. Release ends after hour 1,
    // yet the same puff MUST keep moving, broadening and preserving
    // source mass over the remaining hours. This is not a 143x replay
    // of independent POINTS1 emissions: every old puff inherits its full
    // preceding hour's native motion, sigma, lid and QM/QU.
    const auto born=adaptive.motion(1);
    const auto old_vert=adaptive.vertical(1);
    const auto birth_steps=adaptive.puff_steps(1);
    need(adaptive.canonical_ids().size()==1 && adaptive.canonical_ids()[0]==1,
         "first-hour source puff ID missing from persistent inventory");
    // An in-memory copy captures the entire authoritative hour-boundary
    // checkpoint. A 143h job may be partitioned ONLY if this complete
    // multi-puff state follows it, never by replaying independent hours.
    std::optional<OriginalCompRiseMultiPuffHours> checkpoint;
    std::size_t old_advance_steps=0;
    for(int h=1;h<143;++h){
        auto nextmet=met;
        const float wind=h%2 ? -1.2F : 1.2F;
        std::fill(nextmet.u.begin(),nextmet.u.end(),wind);
        const auto before=adaptive.motion(1);
        const auto vb=adaptive.vertical(1);
        const auto steps_before=adaptive.puff_steps(1);
        const auto no_release=adaptive.advance_hour_existing_mxsam99_adaptive(
            nextmet,geo,ctl,pg,false);
        need(no_release.hour_index==static_cast<std::size_t>(h) &&
             no_release.release.puff_count==0 &&
             no_release.release.new_puffs==0 &&
             no_release.active_puffs==1 &&
             no_release.steps.size()>0 &&
             adaptive.active_count()==1 &&
             adaptive.canonical_ids().at(0)==1,
             "non-emitting COMP hour reset or duplicated the puff");
        const auto after=adaptive.motion(1);
        const auto va=adaptive.vertical(1);
        need(no_release.steps.front().puff_id==1 &&
             no_release.steps.front().release_number==0 &&
             no_release.steps.front().step.before.x_cells==before.x_cells &&
             no_release.steps.front().step.before.y_cells==before.y_cells &&
             no_release.steps.front().step.before.travel_time_s==before.travel_time_s,
             "old puff did not start exactly from previous native hour end");
        const auto check_state=[&](bool ok,const char* label){
            if(!ok){
                std::cerr<<"P7_HISTORY_DIAG HOUR="<<h+1
                         <<" FIELD="<<label
                         <<" DT="<<after.travel_time_s-before.travel_time_s
                         <<" STEPS="<<adaptive.puff_steps(1)
                         <<" EXPECT_STEPS="<<steps_before+no_release.steps.size()
                         <<" SIGY_BEFORE="<<vb.sigma_y_m
                         <<" SIGY_AFTER="<<va.sigma_y_m
                         <<" SIGZ_BEFORE="<<vb.sigma_z_m
                         <<" SIGZ_AFTER="<<va.sigma_z_m
                         <<" ZIOLD="<<va.ziold_m
                         <<" ZIMAX="<<va.zimax_m
                         <<" LID_STEPS="<<va.committed_lid_steps
                         <<" SIGMA_STEPS="<<va.completed_substeps
                         <<" X="<<after.x_cells<<"\\n";
            }
            need(ok,label);
        };
        check_state(after.travel_time_s>before.travel_time_s,
                    "old puff travel time did not advance");
        check_state(std::abs((after.travel_time_s-before.travel_time_s)-3600.0F)<1.0F,
                    "old puff lost one hour of physical sampling time");
        check_state(adaptive.puff_steps(1)==steps_before+no_release.steps.size(),
                    "old puff native step count reset");
        check_state(va.committed_lid_steps==va.completed_substeps,
                    "old puff VMASS/lid and sigma steps diverged");
        check_state(va.committed_lid_steps==adaptive.puff_steps(1),
                    "old puff vertical and horizontal clock diverged");
        check_state(va.completed_substeps>vb.completed_substeps,
                    "old puff sigma history was reset");
        check_state(va.sigma_y_m>=vb.sigma_y_m,
                    "old puff sigma-y shrank");
        // Source SIGADJ: even/non-Gaussian ICODE deliberately stores
        // SIGZB=0.0 after uniform/upper-layer conversion. Requiring
        // monotonic sigma-z is incorrect and first fails at hour 18.
        // The historical puff code/ZIOLD/ZIMAX and conserved mass must
        // still persist and remain self-consistent across that transition.
        check_state(std::isfinite(va.sigma_z_m) && va.sigma_z_m>=0.0F,
                    "old puff stored invalid sigma-z");
        check_state(va.ziold_m>=0.0F && va.zimax_m>=va.ziold_m,
                    "old puff historical mixing lid invalid");
        need(va.mass_mixed.size()==2 && va.mass_above.size()==2 &&
             std::abs(va.mass_mixed[0]+va.mass_above[0]-7200.0F)<0.25F &&
             std::abs(va.mass_mixed[1]+va.mass_above[1]-10800.0F)<0.25F,
             "native old puff mass changed without removal or new emissions");
        // Changing meteorology MUST change the inherited puff motion.
        need(wind>0.0F ? after.x_cells>before.x_cells
                       : after.x_cells<before.x_cells,
             "old puff ignored the next hour's native wind");
        old_advance_steps+=no_release.steps.size();
        if(h==71)checkpoint=adaptive; // 72h state retained through resume
    }
    need(checkpoint.has_value() && checkpoint->completed_hours()==72,
         "72h checkpoint did not retain old puff states");
    for(int h=72;h<143;++h){
        auto nextmet=met;
        const float wind=h%2 ? -1.2F : 1.2F;
        std::fill(nextmet.u.begin(),nextmet.u.end(),wind);
        (void)checkpoint->advance_hour_existing_mxsam99_adaptive(
            nextmet,geo,ctl,pg,false);
    }
    const auto resumed_motion=checkpoint->motion(1);
    const auto resumed_vertical=checkpoint->vertical(1);
    const auto live_motion=adaptive.motion(1);
    const auto live_vertical=adaptive.vertical(1);
    need(checkpoint->completed_hours()==143 &&
         checkpoint->canonical_ids()==adaptive.canonical_ids() &&
         checkpoint->puff_steps(1)==adaptive.puff_steps(1) &&
         resumed_motion.x_cells==live_motion.x_cells &&
         resumed_motion.y_cells==live_motion.y_cells &&
         resumed_motion.z_m==live_motion.z_m &&
         resumed_motion.total_distance_m==live_motion.total_distance_m &&
         resumed_motion.travel_time_s==live_motion.travel_time_s &&
         resumed_vertical.puff_code==live_vertical.puff_code &&
         resumed_vertical.sigma_y_m==live_vertical.sigma_y_m &&
         resumed_vertical.sigma_z_m==live_vertical.sigma_z_m &&
         resumed_vertical.ziold_m==live_vertical.ziold_m &&
         resumed_vertical.zimax_m==live_vertical.zimax_m &&
         resumed_vertical.mass_mixed==live_vertical.mass_mixed &&
         resumed_vertical.mass_above==live_vertical.mass_above &&
         resumed_vertical.completed_substeps==live_vertical.completed_substeps &&
         resumed_vertical.committed_lid_steps==live_vertical.committed_lid_steps,
         "72h full-state checkpoint -> 143h resume differs from continuous execution");
    std::cout<<"P7_NATIVE_72H_CHECKPOINT_RESUME_143H=PASS"
             <<" XY_Z=BITWISE_EQUAL SIGMA=BITWISE_EQUAL"
             <<" QM_QU=BITWISE_EQUAL ZIOLD_ZIMAX=BITWISE_EQUAL"
             <<" RESTART_FILE_IO=NOT_YET_IMPLEMENTED\\n";
    need(adaptive.completed_hours()==143 && adaptive.active_count()==1 &&
         adaptive.canonical_ids().size()==1 &&
         adaptive.puff_steps(1)==birth_steps+old_advance_steps &&
         adaptive.motion(1).travel_time_s>born.travel_time_s &&
         adaptive.vertical(1).completed_substeps>old_vert.completed_substeps,
         "143h stateful old-puff continuation was accidentally split into independent hours");
    const auto final_motion=adaptive.motion(1);
    const auto final_vertical=adaptive.vertical(1);
    const auto final_steps=adaptive.puff_steps(1);
    auto broken_old_met=met;
    broken_old_met.u.clear();
    bool history_rollback=false;
    try{(void)adaptive.advance_hour_existing_mxsam99_adaptive(
        broken_old_met,geo,ctl,pg,false);}
    catch(const std::exception&){history_rollback=true;}
    need(history_rollback && adaptive.completed_hours()==143 &&
         adaptive.puff_steps(1)==final_steps &&
         adaptive.motion(1).x_cells==final_motion.x_cells &&
         adaptive.motion(1).travel_time_s==final_motion.travel_time_s &&
         adaptive.vertical(1).sigma_y_m==final_vertical.sigma_y_m &&
         adaptive.vertical(1).ziold_m==final_vertical.ziold_m &&
         adaptive.vertical(1).mass_mixed==final_vertical.mass_mixed &&
         adaptive.vertical(1).mass_above==final_vertical.mass_above,
         "failed hour committed partial old-puff physical history");
    std::cout<<"P7_NATIVE_143H_CONTINUOUS_PUFF_HISTORY=PASS"
             <<" RELEASE_HOURS=1 NO_RELEASE_HOURS=142"
             <<" EPISODE_ID=1 OLD_STEPS="<<old_advance_steps
             <<" POSITION=RETAINED SIGMA=RETAINED"
             <<" QM_QU=CONSERVED ZIOLD_ZIMAX=RETAINED"
             <<" HOURLY_WIND=CHANGED FAILURE_ATOMIC=YES"
             <<" REAL_HEFEI_143H_CONC=NOT_YET_ACCEPTED\\n";

    // Original COMP L11400: detect exiting PUFF CENTERS after their native
    // physical step, not on the next hourly GETCELL and not from Gaussian
    // sigma extents. Use CALPUFF XB/XE/YB/YE explicitly, independent of
    // CALMET array dimensions. A puff with zero remaining live time must
    // not be spuriously sampled on another KSAM or in the next hour.
    OriginalCompRiseMultiPuffHours crossing;
    const OriginalCompPuffBounds narrow_domain{
        .xb=0.0F,.xe=6.0F,.yb=0.0F,.ye=119.0F};
    const auto outside=crossing.advance_hour_point_mxsam99_adaptive_bounded(
        met,geo,ctl,pg,false,fast,narrow_domain);
    need(outside.release.puff_count==1 && outside.retired.size()==1 &&
         outside.retired[0].puff_id==1 &&
         outside.retired[0].reason==
             OriginalCompExitReason::OutsideComputationalDomain &&
         outside.retired[0].motion_at_exit.x_cells>narrow_domain.xe &&
         outside.steps.size()>=1 &&
         outside.steps.size()<split_hour.steps.size() &&
         crossing.active_count()==0 &&
         crossing.canonical_ids().empty() &&
         crossing.completed_hours()==1,
         "source COMP off-domain failed to retire puff after its exit step");
    need(outside.retired[0].mass_mixed.size()==2 &&
         outside.retired[0].mass_above.size()==2 &&
         std::abs(outside.retired[0].mass_mixed[0]+
                  outside.retired[0].mass_above[0]-7200.0F)<0.25F &&
         std::abs(outside.retired[0].mass_mixed[1]+
                  outside.retired[0].mass_above[1]-10800.0F)<0.25F,
         "COMP retired puff mass disappeared instead of entering OUT ledger");
    const auto after_empty=crossing.advance_hour_existing_mxsam99_adaptive_bounded(
        met,geo,ctl,pg,false,narrow_domain);
    need(after_empty.steps.empty() && after_empty.retired.empty() &&
         crossing.completed_hours()==2 && crossing.active_count()==0,
         "zero-active next hour re-sampled an already retired puff");

    // Original COMP L10450: mass fully removed before a step is taken.
    // No wind, travel, PG or VMASS step should execute on zero-QALL puffs.
    OriginalCompRiseMultiPuffHours zero_driver;
    auto source_zero=fast;
    source_zero.mass.emission_rate={0.0,0.0};
    const auto zero=zero_driver.advance_hour_point_mxsam99_adaptive_bounded(
        met,geo,ctl,pg,false,source_zero,narrow_domain);
    need(zero.release.puff_count==1 &&
         zero.steps.empty() &&
         zero.retired.size()==1 && zero.retired[0].puff_id==1 &&
         zero.retired[0].reason==OriginalCompExitReason::ExhaustedMass &&
         zero_driver.completed_hours()==1 &&
         zero_driver.active_count()==0,
         "COMP QALL=0 puff advanced physically instead of being retired");

    const auto invalid_bounds=OriginalCompPuffBounds{
        .xb=7.0F,.xe=6.0F,.yb=0.0F,.ye=9.0F};
    bool domain_rollback=false;
    try {
        (void)crossing.advance_hour_existing_mxsam99_adaptive_bounded(
            met,geo,ctl,pg,false,invalid_bounds);
    } catch(const std::invalid_argument&){domain_rollback=true;}
    need(domain_rollback && crossing.completed_hours()==2 &&
         crossing.active_count()==0,
         "invalid CALPUFF bounds advanced a committed episode");
    std::cout<<"P7_NATIVE_COMP_AUTONOMOUS_EXIT=PASS"
             <<" POST_STEP_CENTER=YES PRE_STEP_ZERO_QALL=YES"
             <<" RETIRED_QM_QU_PRESERVED=YES"
             <<" NEXT_HOUR_NO_PHANTOM_PUFF=YES"
             <<" BOUNDARY_FROM_CALPUFF=YES"
             <<" SOURCE_ROLLDN_CALL_TIMING=NOT_YET_ACCEPTED\\n";

    // Source-authentic POINTS1 L15990 capacity pressure, not a cleanup at
    // every bounded hour. Every new puff leaves the narrow domain, leaving
    // ICODE=99 holes retained across two distinct emission hours.
    OriginalCompRiseMultiPuffHours slots_driver;
    const OriginalCompPuffBounds slot_domain{
        .xb=0.0F,.xe=5.0F,.yb=0.0F,.ye=119.0F};
    const auto capacity1=slots_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity(
        met,geo,ctl,pg,false,fast,slot_domain,2);
    need(capacity1.release.puff_count==1 &&
         capacity1.retired.size()==1 &&
         capacity1.active_puffs==0 &&
         capacity1.occupied_slots_after==1 &&
         capacity1.inactive_slots_after==1 &&
         !capacity1.capacity_rolldn_triggered &&
         slots_driver.capacity_inventory().slots().front().puff_code==99,
         "COMP eagerly compacted an unpressured ICODE=99 slot");
    const auto capacity2=slots_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity(
        met,geo,ctl,pg,false,fast,slot_domain,2);
    need(capacity2.release.puff_count==1 &&
         capacity2.retired.size()==1 &&
         capacity2.occupied_slots_after==2 &&
         capacity2.inactive_slots_after==2 &&
         !capacity2.capacity_rolldn_triggered &&
         slots_driver.active_count()==0,
         "POINTS1 compacted before MXPUFF capacity pressure");
    const auto capacity3=slots_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity(
        met,geo,ctl,pg,false,fast,slot_domain,2);
    need(capacity3.capacity_rolldn_triggered &&
         capacity3.capacity_rolldn_removed==2 &&
         capacity3.occupied_slots_after==1 &&
         capacity3.inactive_slots_after==1 &&
         slots_driver.completed_hours()==3 &&
         slots_driver.canonical_ids().empty(),
         "POINTS1 did not compact original old ICODE=99 slots on overflow");
    const auto cap_idle=slots_driver.advance_hour_existing_mxsam99_adaptive_bounded_capacity(
        met,geo,ctl,pg,false,slot_domain,2);
    need(cap_idle.steps.empty() && cap_idle.occupied_slots_after==1 &&
         cap_idle.inactive_slots_after==1 && !cap_idle.capacity_rolldn_triggered &&
         slots_driver.completed_hours()==4,
         "zero-source hour erroneously compacted historical puff slots");
    // Capacity exhausted with ACTIVE puffs: ROLLDN cannot reclaim them,
    // so rejection must not advance the hour or drop any historical state.
    OriginalCompRiseMultiPuffHours full_driver;
    const OriginalCompPuffBounds wide_domain{
        .xb=0.0F,.xe=119.0F,.yb=0.0F,.ye=119.0F};
    const auto full1=full_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity(
        met,geo,ctl,pg,false,fast,wide_domain,1);
    need(full1.active_puffs==1 && full1.occupied_slots_after==1,
         "capacity setup should admit exactly one live puff");
    const auto full_state=full_driver.motion(1);
    bool capacity_refused=false;
    try{(void)full_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity(
        met,geo,ctl,pg,false,fast,wide_domain,1);}
    catch(const std::overflow_error&){capacity_refused=true;}
    need(capacity_refused && full_driver.completed_hours()==1 &&
         full_driver.active_count()==1 &&
         full_driver.capacity_inventory().occupied()==1 &&
         full_driver.motion(1).travel_time_s==full_state.travel_time_s,
         "insufficient MXPUFF capacity corrupted hour-atomic puff state");
    std::cout<<"P7_SOURCE_CAPACITY_ROLLDN=PASS"
             <<" FIRST_99_HOLE_RETAINED=YES"
             <<" CAPACITY_PRESSURE_ROLLDN=YES"
             <<" FAILED_ADMISSION=ATOMIC"
             <<" WET_CALCPF_OUTPUT=NOT_YET_INTEGRATED\\n";

    // Full source-ordered DRY for a TRUE native Gaussian point puff:
    // native METFM1+VDCOMP→SETPUF VCBAR→DRY QM→CALCPF→late lid.
    // Synthetic MET fields below are explicit test forcing; this DOES
    // NOT establish frozen 2022 per-puff dry-removal numerical parity.
    auto dry_met=met;
    dry_met.ustar.assign(n,0.3F);
    dry_met.el.assign(n,-80.0F);
    dry_met.tempk.assign(n,288.0F);
    dry_met.qsw.assign(n,300.0F);
    dry_met.wstar.assign(n,0.5F);
    auto dry_geo=geo;
    dry_geo.land_use.assign(n,10);
    dry_geo.leaf_area_index.assign(n,2.0F);
    const std::string dry_control_text=R"DRY(
! MDRY = 1 !
! NZ = 3 !
! ZFACE = 0,100,200,300 !
! CSPEC = H-3 !
! CSPEC = HE-3 !
! RCUTR = 30 !
! RGR = 10 !
! REACTR = 8 !
! NINT = 9 !
! IVEG = 1 !
INPUT GROUP: 3a, 3b -- Species list
Subgroup (3a)
! H-3 = 1,1,1,0 !
! HE-3 = 1,0,0,0 !
!END!
INPUT GROUP: 7 -- Chemical parameters for dry deposition of gases
! H-3 = .1509,1.0,8.0,.0,.04 !
!END!
)DRY";
    auto dry_controls=ctl;
    dry_controls.gaussian_dry=NativeGaussianDryControls{
        dry_deposition_setup_from_control(dry_control_text),1.0F};
    std::size_t physically_dried_steps=0;
    std::size_t gaussian_depleted_steps=0;
    const RiseCompSamplingKernel dry_sample=[&](
        const RiseCompSamplingState& state){
        need(state.after_setpuf_before_lid.mass_mixed==
                 state.vmass.mass_mixed &&
             state.vmass.mass_mixed.size()==2,
             "native CALCPF received stale pre-DRY QM or wrong species");
        ++physically_dried_steps;
        return std::vector<float>{0.0F};
    };
    OriginalCompRiseMultiPuffHours dry_native;
    const auto dry_hour=
        dry_native.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
            dry_met,dry_geo,dry_controls,pg,false,fast,wide_domain,1,1,
            dry_sample);
    for(const auto& part:dry_hour.steps){
        need(part.step.dry.has_value() &&
             part.step.dry->mixed_mass_after.size()==2 &&
             part.step.dry->removed_mass.size()==2 &&
             part.step.dry->removed_mass[1]==0.0F &&
             part.step.vmass.mass_mixed==
                 part.step.dry->mixed_mass_after,
             "native DRY did not apply H3-only removal before CALCPF");
        if(part.step.dry->removed_mass[0]>0.0F)
            ++gaussian_depleted_steps;
    }
    need(dry_hour.steps.size()>1 &&
         dry_hour.steps.size()==physically_dried_steps &&
         gaussian_depleted_steps>0 &&
         dry_native.completed_hours()==1,
         "native Gaussian DRY failed source ordered one-hour mass depletion");
    OriginalCompRiseMultiPuffHours no_dry_native;
    const auto no_dry_hour=
        no_dry_native.advance_hour_point_mxsam99_adaptive_bounded_capacity(
            dry_met,dry_geo,ctl,pg,false,fast,wide_domain,1);
    need(no_dry_hour.steps.size()==dry_hour.steps.size() &&
         dry_native.vertical(1).mass_mixed.at(0)<
             no_dry_native.vertical(1).mass_mixed.at(0) &&
         dry_native.vertical(1).mass_mixed.at(1)==
             no_dry_native.vertical(1).mass_mixed.at(1) &&
         dry_native.vertical(1).mass_above==
             no_dry_native.vertical(1).mass_above,
         "DRY deposition corrupted H3/HE3 QM/QU conservation semantics");
    std::cout<<"P7_NATIVE_DRY_GAUSSIAN_SETPUF_TO_CALCPF_1H=PASS"
             <<" SUBSTEPS="<<physically_dried_steps
             <<" H3_DEPLETED_STEPS="<<gaussian_depleted_steps
             <<" HE3_QM_UNCHANGED=YES QU_UNCHANGED=YES"
             <<" REAL_H3_VDCOMP=YES REAL4_VCBAR=YES"
             <<" SYNTHETIC_MET_ONLY=YES"
             <<" FROZEN_HEFEI_DRY=NOT_YET_ACCEPTED\\n";

    // Preserve EXACT native H-3 depletion across a delayed ICODE
    // transition. The 143-hour no-removal test identifies the first
    // Gaussian->uniform code transition at about hour 18 under
    // alternating winds. Real DRY uses Gaussian VCBAR for odd codes
    // and uniform VDPVD*TSAMP/HLID for even 2/6, without resetting QM.
    std::size_t uniform_dry_steps=0;
    std::size_t dry_longitudinal_steps=0;
    for(int hour=1;hour<=22;++hour) {
        auto met_next=dry_met;
        const float wind=(hour%2 ? -1.2F : 1.2F);
        std::fill(met_next.u.begin(),met_next.u.end(),wind);
        const auto old_hour=
            dry_native.advance_hour_existing_mxsam99_adaptive_bounded_capacity(
                met_next,dry_geo,dry_controls,pg,false,wide_domain,1);
        ++dry_longitudinal_steps;
        for(const auto& state:old_hour.steps) {
            need(state.step.dry.has_value() &&
                 state.step.dry->mixed_mass_after==
                   state.step.vmass.mass_mixed,
                 "native DRY old puff lost state while crossing hour");
            const int type=state.step.vmass.puff_code%10;
            if(type==2||type==6) {
                ++uniform_dry_steps;
                need(state.step.dry->vcbar_m_inverse==0.0F &&
                     state.step.dry->fraction_remaining.at(1)==1.0F,
                     "native uniform DRY used forbidden Gaussian VCBAR");
            }
        }
    }
    need(uniform_dry_steps>0 &&
         dry_native.completed_hours()==1+dry_longitudinal_steps &&
         dry_native.vertical(1).mass_mixed.at(1)>=0.0F &&
         dry_native.vertical(1).mass_above.size()==2,
         "native dry old puff never exercised original uniform ICODE2/6");
    std::cout<<"P7_NATIVE_DRY_GAUSSIAN_TO_UNIFORM_23H=PASS"
             <<" HOUR_TRANSITIONS="<<dry_longitudinal_steps
             <<" UNIFORM_STEPS="<<uniform_dry_steps
             <<" VDPVD_ONLY_FOR_UNIFORM=YES"
             <<" NO_DGM_DRIVING_INPUT=YES"
             <<" SYNTHETIC_MET_ONLY=YES"
             <<" FROZEN_HEFEI_DRY=NOT_YET_ACCEPTED\\n";

    // Source-ordered CALCPF seam: use source-ported PFSAMP + source-ported
    // gridded CALCPF horizontal mass weighting at a receptor positioned on
    // each substep trajectory. PFSAMP expects sigma in SAMPLING GRID UNITS
    // (metres / sampling-grid spacing), whereas CALCPF's denominator needs
    // the same receptor sigma in METRES. Full PUFRECS/VCBAR is NOT here.
    OriginalCompRiseMultiPuffHours sampled_driver;
    const RiseCompSamplingKernel kernel=[&](const RiseCompSamplingState& step) {
        need(step.after_setpuf_before_lid.vmass_pending &&
             step.after_setpuf_before_lid.completed_substeps==
               step.after_setpuf_before_lid.committed_lid_steps+1 &&
             step.vmass.mass_mixed.size()==2,
             "CALCPF callback did not run between SETPUF and late lid");
        const double sy_m=step.sigmas.step.sigma_y_mid_m;
        need(sy_m>0,"sampled CALCPF sigma-y is invalid");
        const double sy_sample_units=sy_m/ctl.met_spacing_m;
        const double xrec=0.5*(step.before.x_cells+step.after.x_cells);
        const double yrec=0.5*(step.before.y_cells+step.after.y_cells);
        const auto ints=puff_sampling_integrals(
            step.before.x_cells,step.before.y_cells,
            step.after.x_cells,step.after.y_cells,
            xrec,yrec,sy_sample_units,0.0);
        const auto inc=receptor_concentration_increment(ints,{
            .mass_old=step.vmass.mass_mixed.at(0),
            .mass_new=step.vmass.mass_mixed.at(0),
            .sigma_y_at_receptor_m=sy_m,
            .closest_approach_squared_km2=0,
            .vertical_factor=1.0,  // explicitly supplied test VCOUP factor
            .time_fraction=step.step_seconds/3600.0,
            .deposition_ratio=1.0,.area_source_factor=1.0
        });
        const float v=static_cast<float>(inc);
        need(std::isfinite(v) && v>0.0F,"native CALCPF contributed no finite receptor value");
        return std::vector<float>{v};
    };
    const auto sampled=sampled_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
        met,geo,ctl,pg,false,fast,wide_domain,1,1,kernel);
    float recomputed=0;
    for(const auto& part:sampled.steps){
        need(part.step.receptor_increments.size()==1,
             "native CALCPF substep increment not retained");
        recomputed+=part.step.receptor_increments.at(0);
    }
    need(sampled.receptor_concentrations.size()==1 &&
         sampled.receptor_concentrations[0]==recomputed &&
         sampled.steps.size()>1 &&
         sampled_driver.completed_hours()==1,
         "CALCPF sampling did not accumulate each actual FSTEP substep");
    auto no_sample=[](const RiseCompSamplingState&)->std::vector<float>{
        throw std::runtime_error("intentional CALCPF failure");
    };
    OriginalCompRiseMultiPuffHours failed_sample_driver;
    bool sample_refused=false;
    try{(void)failed_sample_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
        met,geo,ctl,pg,false,fast,wide_domain,1,1,no_sample);}
    catch(const std::runtime_error&){sample_refused=true;}
    need(sample_refused && failed_sample_driver.completed_hours()==0 &&
         failed_sample_driver.active_count()==0 &&
         failed_sample_driver.canonical_ids().empty(),
         "CALCPF callback failure partially committed puff/source hour");
    std::cout<<"P7_CALCPF_NATIVE_SUBSTEP_HOOK=PASS"
             <<" AFTER_SETPUF_BEFORE_LID=YES"
             <<" FSTEP_SAMPLES="<<sampled.steps.size()
             <<" PFSAMP_GRID_UNITS=YES"
             <<" HOUR_ATOMIC=YES"
             <<" FULL_PUFRECS_VCBAR=NOT_YET_ACCEPTED\\n";

    // Actual 2500-cell native substep field: PFSCRN -> PFSAMP -> VCOUP,
    // no caller-invented vertical coupling coefficient, and 1-hour
    // output retained as 2500-element REAL4 receptor accumulator.
    ReceptorSet flat_grid;
    flat_grid.gridded=true;
    flat_grid.mesh_down=1;
    flat_grid.ibsamp=1;flat_grid.jbsamp=1;
    flat_grid.iesamp=50;flat_grid.jesamp=50;
    flat_grid.sampling_nx=50;flat_grid.sampling_ny=50;
    flat_grid.spacing_km=0.1;
    flat_grid.grid.assign(2500,Receptor{});
    auto planar_kernel=make_original_flat_calcpf_sampler(
        flat_grid,100.0F,3600.0F);
    OriginalCompRiseMultiPuffHours native_receptors;
    auto single_mass=fast;
    single_mass.mass.species_count=1;
    single_mass.mass.emission_rate={2.0};
    const auto flat1=native_receptors.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
        met,geo,ctl,pg,false,single_mass,wide_domain,2,2500,planar_kernel);
    need(flat1.receptor_concentrations.size()==2500 &&
         flat1.steps.size()>1 && native_receptors.completed_hours()==1,
         "flat 2500-grid CALCPF not called through real FSTEP COMP");
    std::vector<float> rebuilt(2500,0.0F);
    for(const auto& sub:flat1.steps){
        need(sub.step.receptor_increments.size()==2500,
             "flat CALCPF did not return a complete 2500-cell substep");
        for(std::size_t i=0;i<2500;++i){
            const auto delta=sub.step.receptor_increments[i];
            need(std::isfinite(delta),"flat CALCPF nonfinite species field");
            rebuilt[i]+=delta;
        }
    }
    need(rebuilt==flat1.receptor_concentrations,
         "flat CALCPF FSTEP sum changed REAL4 operation order");
    bool bad_flat=false;
    try{(void)make_original_flat_calcpf_sampler(flat_grid,0.0F,3600.0F);}
    catch(const std::invalid_argument&){bad_flat=true;}
    need(bad_flat,"flat CALCPF silently accepted invalid MET grid spacing");
    std::cout<<"P7_NATIVE_2500_FLAT_CALCPF_HOOK=PASS"
             <<" RECEPTORS=2500"
             <<" PFSCRN=ORIGINAL_REAL4 PFSAMP=ORIGINAL_REAL4"
             <<" VCOUP=SOURCE_PORTED"
             <<" FSTEP_ACCUMULATOR=REAL4"
             <<" PUFRECS=NOT_YET_INTEGRATED"
             <<" FROZEN_2022_PARITY=NOT_YET_ACCEPTED\\n";

    // A strictly limited 1h -> 6h output continuation: same native
    // puff lifetime and flat CALCPF 2500-cell hook, source-typed OUTPUT
    // period/descriptor/H-3 records, and bitwise REAL4 read-back. The
    // vendor WROUT1 full header and real Hefei 2022 values remain OPEN.
    // First validate a physically nonzero near-ground synthetic puff.
    RiseCompSamplingState known;
    known.puff_id=99;
    known.before.x_cells=5.0F; known.before.y_cells=5.5F;
    known.before.z_m=10.0F;
    known.after.x_cells=6.0F; known.after.y_cells=5.5F;
    known.after.z_m=10.0F;
    known.after_setpuf_before_lid.puff_code=1;
    known.after_setpuf_before_lid.vmass_pending=true;
    known.vmass.puff_code=1;
    known.vmass.reflecting_lid_m=100.0F;
    known.vmass.mass_mixed={2.0F};
    known.vmass.mass_above={0.0F};
    known.sigmas.step.sigma_y_mid_m=50.0;
    known.sigmas.step.sigma_y_end_m=50.0;
    // SETPUF supplies the adjusted end-of-step SIGTY read by PUFRECS.
    // Keep this synthetic known-puff fixture consistent with that contract.
    known.sigmas.adjust.sigma_y_end_m=50.0;
    known.sigmas.step.sigma_z_mid_m=30.0;
    known.step_seconds=60.0F;
    const auto known_cells=planar_kernel(known);
    need(known_cells.size()==2500 && known_cells[5+5*50]>0.0F &&
         known_cells[2499]==0.0F,
         "flat source-ported VCOUP/PFSAMP receptor result was not localized/positive");

    // Original CALCPF L4295/L4304 samples QOLD*T1 + QNEW*T2.
    // When DRY removes the last remaining mixed H-3 mass, QNEW=0 must
    // not suppress an otherwise valid positive pre-removal QOLD term.
    auto endpoint=known;
    endpoint.vmass.mass_mixed={0.0F,0.0F};
    endpoint.vmass.mass_above={0.0F,0.0F};
    endpoint.receptor_qold_mixed={2.0F,0.0F};
    const auto endpoint_kernel=make_original_flat_calcpf_sampler(
        flat_grid,100.0F,3600.0F,3.0F,
        OriginalFlatVerticalMethod::midpoint_vcoup,{},true);
    const auto qold_only=endpoint_kernel(endpoint);
    const std::size_t endpoint_receptor=5U+5U*50U;
    need(qold_only.size()==2500U && qold_only[endpoint_receptor]>0.0F,
         "CALCPF discarded nonzero QOLD when QNEW was removed by DRY");
    endpoint.receptor_qold_mixed[0]=0.0F;
    const auto empty_endpoints=endpoint_kernel(endpoint);
    need(std::all_of(empty_endpoints.begin(),empty_endpoints.end(),
                     [](float x){return x==0.0F;}),
         "CALCPF did not reject truly zero old and new species mass");
    endpoint.vmass.mass_mixed[0]=2.0F;
    const auto qnew_only=endpoint_kernel(endpoint);
    endpoint.receptor_qold_mixed[0]=2.0F;
    const auto both_endpoints=endpoint_kernel(endpoint);
    need(qnew_only[endpoint_receptor]>0.0F &&
         std::abs((qold_only[endpoint_receptor]+
                   qnew_only[endpoint_receptor])-
                  both_endpoints[endpoint_receptor])<=
             2.0e-6F*both_endpoints[endpoint_receptor],
         "CALCPF failed independent linear QOLD/QNEW endpoint weight test");
    std::cout<<"P7_CALCPF_QOLD_QNEW_ZERO_ENDPOINT=PASS"
             <<" PRE_DRY_QOLD_PRESERVED=YES"
             <<" BOTH_MASS_ZERO=ZERO"
             <<" VENDOR_QOLD_T1_QNEW_T2=ENFORCED\\n";


    // New opt-in, source-ported VCBAR stage: independently verify the
    // begin/mid/end SIGTZ/GRISE height coupling against P7H VCBAR, while
    // retaining the existing nonzero 6h VCOUP output regression untouched.
    known.sigmas.adjust.sigma_z_begin_m=25.0;
    known.sigmas.adjust.sigma_z_mid_m=30.0;
    known.sigmas.adjust.sigma_z_end_m=35.0;
    const auto vbar_kernel=make_original_flat_calcpf_sampler(
        flat_grid,100.0F,3600.0F,3.0F,
        OriginalFlatVerticalMethod::substep_vcbar);
    const auto bar_cells=vbar_kernel(known);
    constexpr std::size_t receptor=5+5*50;
    VcbarInputs expected;
    expected.state.puff_code=1;
    expected.state.z_begin1=10.0;
    expected.state.z_end1=10.0;
    expected.state.sigma_z_begin1=25.0;
    expected.state.sigma_z_mid=30.0;
    expected.state.sigma_z_end1=35.0;
    expected.lid_height_m=100.0;
    const float fbar=static_cast<float>(vertical_coupling_bar(expected));
    const float fmid=static_cast<float>(vertical_coupling({
        1,0.0,10.0,30.0,100.0,100.0}));
    need(bar_cells.size()==2500 && bar_cells[receptor]>0.0F &&
         fmid>0.0F && fbar>0.0F &&
         std::abs(static_cast<double>(bar_cells[receptor])/known_cells[receptor] -
                  static_cast<double>(fbar)/fmid)<5.0e-5,
         "native VCBAR field disagrees with independently evaluated P7H VCBAR");
    const auto bar_unchanged=bar_cells;
    known.sigmas.adjust.sigma_z_end_m=-1.0;
    bool refused_bad_sigma=false;
    try{(void)vbar_kernel(known);}
    catch(const std::invalid_argument&){refused_bad_sigma=true;}
    need(refused_bad_sigma,
         "native VCBAR silently accepted an invalid adjusted end SIGTZ");
    known.sigmas.adjust.sigma_z_end_m=35.0;
    need(vbar_kernel(known)==bar_unchanged,
         "native VCBAR was non-deterministic after failure/refusal");
    std::cout<<"P7_NATIVE_FLAT_VCBAR_INTEGRATION=PASS"
             <<" SETPUF_SIGTZ_BEGIN_MID_END=YES"
             <<" GRISE_BEGIN_END_HEIGHT=YES"
             <<" TERRAIN_PUFRECS_SIGMA_RECEPTOR_SPECIFIC=OPEN"
             <<" FROZEN_2022_PARITY=NOT_YET_ACCEPTED\\n";

    const auto binary_path=std::filesystem::temp_directory_path() /
        ("cteas-p7-flat6h-"+std::to_string(
            std::chrono::steady_clock::now().time_since_epoch().count())+".con");
    // The native point's authoritatively stored coordinates start at
    // MET cells (5,5), NOT (50,50): source_x_km=5 is already converted
    // by the POINTS1 release grid convention. A window starting at
    // (40,40) misses y=5 and yields a fully zero false-positive output.
    // Keep the original 1..50 grid to intercept the actual plume path.
    auto plume_grid=flat_grid;
    plume_grid.ibsamp=1;
    plume_grid.jbsamp=1;
    // Make original P7H VCBAR (native begin/mid/end SIGTZ and GRISE heights)
    // the *live* sampling kernel for every actual COMP FSTEP, rather than
    // stopping at a one-puff constructed fixture. The midpoint VCOUP path
    // remains an independent, deliberately restricted control.
    // MCTADJ2 is opt-in and fail-closed. The original CTADJ2/SETPUF
    // values MUST be generated by the physical puff step before using
    // the receptor-specific MCTADJ2 PUFRECS/VCOUP code.
    bool missing_receiver_terrain_rejected=false;
    try {
        (void)make_original_flat_calcpf_sampler(
            plume_grid,100.0F,3600.0F,3.0F,
            OriginalFlatVerticalMethod::receptor_pg_vcoup_mctadj2);
    } catch(const std::invalid_argument&) {
        missing_receiver_terrain_rejected=true;
    }
    need(missing_receiver_terrain_rejected,
         "MCTADJ2 CALCPF fabricated missing receptor TRELIEF/GETELEV");
    // Build physical ELEV, GETELEV, TRELIEF, and VWIDTH from the same
    // Calmet21Static contract that the frozen real MET.DAT reader supplies.
    // The elevations here remain a SYNTHETIC 50x50 fixture, matching
    // the spatial extent of the locked Hefei receptor grid. Use a
    // consistently cropped meteorological array for this test's first
    // hour, rather than invoking global 120x120 TRELIEF/VWIDTH.
    auto met_for_terrain=met;
    constexpr std::size_t terrain_n=50U*50U;
    met_for_terrain.nx=50;met_for_terrain.ny=50;
    met_for_terrain.zi.assign(terrain_n,250.0F);
    met_for_terrain.ipgt.assign(terrain_n,4);
    met_for_terrain.u.assign(terrain_n*3U,1.2F);
    met_for_terrain.v.assign(terrain_n*3U,0.0F);
    auto geo_for_terrain=geo;
    geo_for_terrain.present=true;
    geo_for_terrain.elevation_m.assign(terrain_n,10.0F);
    const auto native_terrain_grid=OriginalNativeTerrain::from_calmet(
        geo_for_terrain,50,50,100.0F);
    const auto source_terrain_sampler=make_original_flat_calcpf_sampler(
        plume_grid,100.0F,3600.0F,3.0F,
        OriginalFlatVerticalMethod::receptor_pg_vcoup_mctadj2,
        [&native_terrain_grid](const RiseCompSamplingState& state,
                 std::size_t receiver,const OriginalPuffct2Result& position){
            const float wind=(state.after.total_distance_m-
                state.before.total_distance_m)/state.step_seconds;
            return native_terrain_grid.receptor(
                receiver,1,1,50,50,position,0.0F,wind);
        });
    bool missing_step_rejected=false;
    try {(void)source_terrain_sampler(known);}
    catch(const std::invalid_argument&){missing_step_rejected=true;}
    need(missing_step_rejected,
         "MCTADJ2 CALCPF manufactured missing native CTADJ2 /CURRENT/");
    // Construct a genuine native SETPUF/CTADJ2 terrain transaction
    // from reproducible SYNTHETIC elevations/RELIEF; it uses the real
    // C++ SETPUF, CTADJ2, PUFFCT2, PUFRECS and VCOUP call chain.
    // This is NOT an original Hefei 2022 terrain case verification.
    auto terrain_ctl=ctl;
    NativeMctadj2Controls terrain_control;
    terrain_control.brunt_vaisala_s=0.0F;
    terrain_control.terrain=native_terrain_grid.constraint_lookup();
    terrain_ctl.mctadj2=terrain_control;
    std::size_t native_ctadj2_substeps=0;
    std::size_t native_ctadj2_receptor_nonzero=0;
    const RiseCompSamplingKernel integrated_terrain=[&](
        const RiseCompSamplingState& ss){
        need(ss.original_ctadj2_step.has_value(),
             "native CTADJ2 was not published to CALCPF");
        const auto& p=*ss.original_ctadj2_step;
        need(p.z_end_m==ss.after.z_m &&
             p.upslope==false &&
             std::isfinite(p.terrain_fraction),
             "SETPUF CTADJ2 height/FRACZ1/LUP1 was not native and persistent");
        const auto values=source_terrain_sampler(ss);
        ++native_ctadj2_substeps;
        native_ctadj2_receptor_nonzero+=std::count_if(
            values.begin(),values.end(),[](float value){return value>0.0F;});
        return values;
    };
    OriginalCompRiseMultiPuffHours integrated_terrain_driver;
    const auto terrain_hour=
        integrated_terrain_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
            met_for_terrain,geo_for_terrain,terrain_ctl,pg,false,
            single_mass,wide_domain,99,2500,integrated_terrain);
    need(terrain_hour.steps.size()>1 &&
         terrain_hour.receptor_concentrations.size()==2500 &&
         native_ctadj2_substeps==terrain_hour.steps.size() &&
         native_ctadj2_receptor_nonzero>0 &&
         integrated_terrain_driver.completed_hours()==1,
         "native CTADJ2/PUFFCT2/PUFRECS CALCPF one-hour chain not operational");
    std::cout<<"P7_NATIVE_SETPUF_CTADJ2_PUFFCT2_PUFRECS_CALCPF_1H=PASS"
             <<" FSTEP="<<native_ctadj2_substeps
             <<" NONZERO_SUBSTEP_RECEPTORS="<<native_ctadj2_receptor_nonzero
             <<" PERSISTENT_HEIGHT=YES"
             <<" TERRAIN_STATIC_CALMET_INPUT=YES"
             <<" TRELIEF_GETELEV_VWIDTH_SOURCE_PORTED=YES"
             <<" TERRAIN_SYNTHETIC_ONLY=YES"
             <<" ORIGINAL_HEFEI_MCTADJ2=NOT_YET_ACCEPTED\\n";

    // Exercise NONZERO native terrain strain: flat ELEV tests prove wiring,
    // not that active CTADJ2 changes the physical puff height or CALCPF.
    // Gradient is deliberately synthetic, NEVER a frozen-case oracle.
    auto grade_geo=geo_for_terrain;
    for(int j=0;j<50;++j)for(int i=0;i<50;++i)
        grade_geo.elevation_m[static_cast<std::size_t>(j*50+i)]=
            10.0F+static_cast<float>(i);
    const auto grade_grid=OriginalNativeTerrain::from_calmet(
        grade_geo,50,50,100.0F);
    auto grade_ctl=terrain_ctl;
    grade_ctl.mctadj2->brunt_vaisala_s=0.10F;
    grade_ctl.mctadj2->terrain=grade_grid.constraint_lookup();
    const auto grade_sampler=make_original_flat_calcpf_sampler(
        plume_grid,100.0F,3600.0F,3.0F,
        OriginalFlatVerticalMethod::receptor_pg_vcoup_mctadj2,
        [&grade_grid](const RiseCompSamplingState& state,
                      std::size_t receiver,const OriginalPuffct2Result& position){
            const float ws=(state.after.total_distance_m-
                state.before.total_distance_m)/state.step_seconds;
            return grade_grid.receptor(
                receiver,1,1,50,50,position,0.10F,ws);
        });
    std::size_t terrain_height_changed=0;
    std::size_t terrain_gaussian_substeps=0;
    const RiseCompSamplingKernel grade_checked=[&](
        const RiseCompSamplingState& state){
        need(state.original_ctadj2_step.has_value() &&
             std::isfinite(state.original_ctadj2_step->terrain_fraction),
             "sloped original SETPUF lost authoritative CTADJ2 data");
        if(state.original_ctadj2_step->upslope &&
           state.after.z_m<state.before.z_m)
            ++terrain_height_changed;
        ++terrain_gaussian_substeps;
        return grade_sampler(state);
    };
    OriginalCompRiseMultiPuffHours grade_driver;
    const auto grade_hour=
        grade_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
            met_for_terrain,grade_geo,grade_ctl,pg,false,single_mass,
            wide_domain,99,2500,grade_checked);
    need(terrain_gaussian_substeps==grade_hour.steps.size() &&
         terrain_gaussian_substeps>1 &&
         terrain_height_changed>0 &&
         grade_hour.receptor_concentrations.size()==2500 &&
         grade_driver.completed_hours()==1,
         "nonflat native CTADJ2 never modified actual end-step puff height");
    std::cout<<"P7_NATIVE_MCTADJ2_NONFLAT_1H=PASS"
             <<" PHYSICAL_SUBSTEPS="<<terrain_gaussian_substeps
             <<" UPSLOPE_Z_CHANGED="<<terrain_height_changed
             <<" CTADJ2_SETPUF_PUFRECS_VCOUP=SOURCE_ORDERED"
             <<" TERRAIN_SYNTHETIC_ONLY=YES"
             <<" FROZEN_HEFEI_PARITY=NOT_ACCEPTED\\n";

    // Combined source-ordered P7 gate: actual native SETPUF CTADJ2,
    // gas-phase DRY, then receptor-specific PUFRECS/CALCPF on the same
    // physical substeps. Both existing independent gates must also pass.
    // These meteorological values are SYNTHETIC; no vendor DGM is input.
    auto coupled_met=met_for_terrain;
    coupled_met.ustar.assign(terrain_n,0.3F);
    coupled_met.el.assign(terrain_n,-80.0F);
    coupled_met.tempk.assign(terrain_n,288.0F);
    coupled_met.qsw.assign(terrain_n,300.0F);
    coupled_met.wstar.assign(terrain_n,0.5F);
    auto coupled_geo=grade_geo;
    coupled_geo.roughness_m.assign(terrain_n,0.25F);
    coupled_geo.land_use.assign(terrain_n,10);
    coupled_geo.leaf_area_index.assign(terrain_n,2.0F);
    auto coupled_ctl=grade_ctl;
    auto h3_dry_setup=dry_controls.gaussian_dry->setup;
    need(!h3_dry_setup.species.empty(),
         "selected H-3 gas dry controls missing");
    // DRYI caches *all* per-species vectors, not just group 3a rows.
    // Keep the immutable H-3 species-0 coefficients while narrowing the
    // synthetic one-species receptor fixture; never mismatch vector sizes.
    h3_dry_setup.species.resize(1);
    h3_dry_setup.diffusivity_m2_s.resize(1);
    h3_dry_setup.mesophyll_resistance_s_m.resize(1);
    h3_dry_setup.cuticle_resistance_s_m.resize(1);
    h3_dry_setup.ground_resistance_s_m.resize(1);
    h3_dry_setup.water_ground_term_s_m.resize(1);
    h3_dry_setup.deposition_layer_term.resize(1);
    coupled_ctl.gaussian_dry=NativeGaussianDryControls{
        h3_dry_setup,1.0F};
    std::size_t coupled_samples=0;
    const RiseCompSamplingKernel coupled_sampler=[&](
        const RiseCompSamplingState& state){
        need(state.original_ctadj2_step.has_value() &&
             state.vmass.mass_mixed.size()==1 &&
             state.after_setpuf_before_lid.mass_mixed==
                 state.vmass.mass_mixed,
             "combined DRY/CTADJ2 sampler received stale native puff state");
        ++coupled_samples;
        return grade_sampler(state);
    };
    OriginalCompRiseMultiPuffHours coupled_dry_driver;
    const auto coupled_dry_hour=
        coupled_dry_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
            coupled_met,coupled_geo,coupled_ctl,pg,false,single_mass,
            wide_domain,99,2500,coupled_sampler);
    OriginalCompRiseMultiPuffHours coupled_nodry_driver;
    const auto coupled_nodry_hour=
        coupled_nodry_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
            coupled_met,coupled_geo,grade_ctl,pg,false,single_mass,
            wide_domain,99,2500,grade_sampler);
    need(coupled_samples==coupled_dry_hour.steps.size() &&
         coupled_samples>1 &&
         coupled_dry_hour.steps.size()==coupled_nodry_hour.steps.size() &&
         coupled_dry_hour.receptor_concentrations.size()==2500 &&
         coupled_nodry_hour.receptor_concentrations.size()==2500 &&
         coupled_dry_driver.completed_hours()==1 &&
         coupled_nodry_driver.completed_hours()==1,
         "MCTADJ2 plus MDRY failed joint native substep/receiver transaction");
    std::size_t positive_dry_removal=0;
    for(std::size_t i=0;i<coupled_dry_hour.steps.size();++i){
        const auto& a=coupled_dry_hour.steps[i].step;
        const auto& b=coupled_nodry_hour.steps[i].step;
        need(a.dry.has_value() &&
             a.dry->removed_mass.size()==1 &&
             a.after.x_cells==b.after.x_cells &&
             a.after.y_cells==b.after.y_cells &&
             a.after.z_m==b.after.z_m &&
             a.vmass.mass_above==b.vmass.mass_above &&
             a.vmass.mass_mixed[0]<=b.vmass.mass_mixed[0],
             "combined gas DRY changed native trajectory, QU, or raised QM");
        if(a.dry->removed_mass[0]>0.0F)++positive_dry_removal;
    }
    std::size_t nonzero_cells=0,decreased_cells=0;
    for(std::size_t i=0;i<2500;++i){
        const float dry=coupled_dry_hour.receptor_concentrations[i];
        const float baseline=coupled_nodry_hour.receptor_concentrations[i];
        need(std::isfinite(dry)&&std::isfinite(baseline) &&
             dry>=0.0F && baseline>=0.0F && dry<=baseline,
             "combined DRY+MCTADJ2 invalid H-3 receptor concentration");
        if(baseline>0.0F)++nonzero_cells;
        if(dry<baseline)++decreased_cells;
    }
    need(positive_dry_removal>0 && nonzero_cells>0 && decreased_cells>0 &&
         coupled_dry_driver.vertical(1).mass_mixed[0]<
             coupled_nodry_driver.vertical(1).mass_mixed[0],
         "combined native DRY+MCTADJ2 produced no physical receptor effect");
    std::cout<<"P7_NATIVE_MCTADJ2_MDRY1_PUFRECS_CALCPF_1H=PASS"
             <<" PHYSICAL_SUBSTEPS="<<coupled_samples
             <<" H3_REMOVAL_SUBSTEPS="<<positive_dry_removal
             <<" NONZERO_NO_DRY_CELLS="<<nonzero_cells
             <<" DECREASED_H3_RECEPTORS="<<decreased_cells
             <<" TERRAIN_AND_DRY_COMBINED=YES"
             <<" REAL_HEFEI_EQUIVALENCE=NOT_YET_ACCEPTED\\n";

    const auto plume_sampler=make_original_flat_calcpf_sampler(
        plume_grid,100.0F,3600.0F,3.0F,
        OriginalFlatVerticalMethod::receptor_pg_vcoup);
    // First real native IDOPT1 -> PUFRECS -> CALCPF integration, isolated
    // to source-valid XFINAL=0 and a synthetic flat, no-dry/no-terrain grid.
    // Original Hefei hour9 additionally needs MCTADJ2+MDRY=1, which MUST
    // remain fail-closed until its independent original-source stage gate.
    {
        auto calm_met=met;
        calm_met.u.assign(n*3U,0.2F);
        calm_met.v.assign(n*3U,0.0F);
        calm_met.el.assign(n,-100.0F);
        auto calm_geo=geo;
        calm_geo.present=true;
        calm_geo.land_use.assign(n,1);
        auto calm_control=ctl;
        calm_control.calm_mdisp3=NativeCalmMdisp3Controls{};
        calm_control.calm_mdisp3->iwat1=50;
        calm_control.calm_mdisp3->iwat2=55;
        calm_control.calm_mdisp3->original_turbulence.svmin.fill(0.5F);
        calm_control.calm_mdisp3->original_turbulence.swmin.fill(0.06F);
        auto calm_point=single_mass;
        calm_point.point.x_final_m=0.0F;
        // Enforce the actual original PRFIN WSSTK<WSSTK0 branch rather
        // than forging zero XFINAL while retaining a high stack wind.
        calm_point.point.stack_wind_speed_ms=0.2F;
        calm_point.point.x_final_buoyancy_m=0.0F;
        calm_point.point.x_final_momentum_m=0.0F;
        calm_point.cadence.wind_speed_ms=0.2F;
        const auto original_calm_receptor=make_original_flat_calcpf_sampler(
            plume_grid,100.0F,3600.0F,3.0F,
            OriginalFlatVerticalMethod::receptor_pg_vcoup);
        std::size_t native_calm_sample_calls=0;
        const RiseCompSamplingKernel calm_kernel=[&](
                const RiseCompSamplingState& state){
            need(state.receptor_calm_sigma.has_value() &&
                 state.receptor_final_rise_distance_m==0.0F,
                 "LCALM sampler lost live IDOPT1 or original XFINAL=0");
            const auto values=original_calm_receptor(state);
            need(values.size()==2500U &&
                 std::all_of(values.begin(),values.end(),
                     [](float x){return std::isfinite(x)&&x>=0.0F;}),
                 "native calm PUFRECS CALCPF returned invalid receptor field");
            ++native_calm_sample_calls;
            return values;
        };
        OriginalCompRiseMultiPuffHours calm_driver;
        const OriginalCompPuffBounds calm_bounds{0.0F,119.0F,0.0F,119.0F};
        const auto calm_hour=
            calm_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
                calm_met,calm_geo,calm_control,pg,false,calm_point,
                calm_bounds,4096,2500,calm_kernel);
        need(calm_driver.completed_hours()==1U &&
             native_calm_sample_calls>0U &&
             native_calm_sample_calls==calm_hour.steps.size() &&
             calm_hour.receptor_concentrations.size()==2500U,
             "synthetic native LCALM IDOPT1 CALCPF did not finish one hour");
        std::cout<<"P7_NATIVE_CALM_IDOPT1_PUFRECS_CALCPF_1H=PASS"
                 <<" SUBSTEPS="<<native_calm_sample_calls
                 <<" SOURCE_XFINAL=0"
                 <<" TURBSET=LIVE_MET"
                 <<" CTADJ2_DRY=FAIL_CLOSED"
                 <<" HEFEI_H9_PARITY=NOT_YET_ACCEPTED\\n";

        // Reuse the identical low-wind synthetic puff/MET with a genuine
        // native CALMET-derived terrain lookup. This tests IDOPT1 with
        // CTADJ2 and receptor PUFFCT2, but does NOT permit real MDRY=1.
        calm_geo.elevation_m.assign(n,10.0F);
        const auto native_calm_terrain=OriginalNativeTerrain::from_calmet(
            calm_geo,120,120,100.0F);
        auto terrain_calm_control=calm_control;
        NativeMctadj2Controls calm_ctadj2;
        calm_ctadj2.terrain=native_calm_terrain.constraint_lookup();
        calm_ctadj2.brunt_vaisala_s=0.0F;
        terrain_calm_control.mctadj2=calm_ctadj2;
        const auto calm_terrain_receptors=make_original_flat_calcpf_sampler(
            plume_grid,100.0F,3600.0F,3.0F,
            OriginalFlatVerticalMethod::receptor_pg_vcoup_mctadj2,
            [&native_calm_terrain](const RiseCompSamplingState& state,
                std::size_t receiver,const OriginalPuffct2Result& pos){
                return native_calm_terrain.receptor(
                    receiver,1,1,50,50,pos,0.0F,
                    state.receptor_effective_wind_ms);
            });
        std::size_t calm_terrain_calls=0;
        const RiseCompSamplingKernel terrain_calm_kernel=[&](
                const RiseCompSamplingState& state){
            need(state.receptor_calm_sigma.has_value() &&
                 state.original_ctadj2_step.has_value(),
                 "native LCALM CTADJ2 did not reach receptor sampling");
            const auto values=calm_terrain_receptors(state);
            need(values.size()==2500U &&
                 std::all_of(values.begin(),values.end(),
                     [](float x){return std::isfinite(x)&&x>=0.0F;}),
                 "calm CTADJ2 PUFFCT2 returned invalid concentrations");
            ++calm_terrain_calls;
            return values;
        };
        OriginalCompRiseMultiPuffHours calm_terrain_driver;
        const auto calm_terrain_hour=
            calm_terrain_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
                calm_met,calm_geo,terrain_calm_control,pg,false,calm_point,
                calm_bounds,4096,2500,terrain_calm_kernel);
        need(calm_terrain_driver.completed_hours()==1U &&
             calm_terrain_calls>0U &&
             calm_terrain_calls==calm_terrain_hour.steps.size(),
             "synthetic LCALM CTADJ2 PUFRECS CALCPF hour did not commit");
        std::cout<<"P7_NATIVE_CALM_IDOPT1_CTADJ2_PUFRECS_CALCPF_1H=PASS"
                 <<" SUBSTEPS="<<calm_terrain_calls
                 <<" TERRAIN=SYNTHETIC_NATIVE"
                 <<" DRY_VCBAR=SEPARATE_GATE"
                 <<" HEFEI_H9_PARITY=NOT_YET_ACCEPTED\\n";

        // Original DRY explicitly sets LCALMF=.FALSE. and calls VCBAR
        // with that LOCAL flag even when COMP uses LCALM=1 IDOPT1 sigmas.
        // Exercise the entire native calm+CTADJ2+DRY+receptor chain; this
        // remains a synthetic regression, not a substitute for original H9.
        calm_met.ustar.assign(n,0.3F);
        calm_met.tempk.assign(n,288.0F);
        calm_met.qsw.assign(n,300.0F);
        calm_met.wstar.assign(n,0.5F);
        calm_geo.leaf_area_index.assign(n,2.0F);
        auto dry_calm_control=terrain_calm_control;
        dry_calm_control.gaussian_dry=NativeGaussianDryControls{
            h3_dry_setup,1.0F};
        std::size_t calm_dry_samples=0;
        const RiseCompSamplingKernel calm_dry_kernel=[&](
                const RiseCompSamplingState& state){
            need(state.receptor_calm_sigma.has_value() &&
                 state.original_ctadj2_step.has_value() &&
                 state.receptor_qold_mixed.size()==1,
                 "calm DRY receiver lost native IDOPT1 or pre-DRY QOLD");
            ++calm_dry_samples;
            return calm_terrain_receptors(state);
        };
        OriginalCompRiseMultiPuffHours calm_dry_driver;
        const auto calm_dry_hour=
            calm_dry_driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
                calm_met,calm_geo,dry_calm_control,pg,false,calm_point,
                calm_bounds,4096,2500,calm_dry_kernel);
        need(calm_dry_driver.completed_hours()==1U &&
             calm_dry_samples==calm_dry_hour.steps.size() &&
             calm_dry_samples==calm_terrain_hour.steps.size() &&
             calm_dry_hour.receptor_concentrations.size()==2500U,
             "native calm DRY failed full hour or CALCPF stage counts");
        std::size_t removed_calm=0;
        for(std::size_t i=0;i<calm_dry_hour.steps.size();++i){
            const auto& with_dry=calm_dry_hour.steps[i].step;
            const auto& no_dry=calm_terrain_hour.steps[i].step;
            need(with_dry.bookkeeping.calm &&
                 with_dry.dry.has_value() &&
                 with_dry.dry->removed_mass.size()==1 &&
                 with_dry.after.x_cells==no_dry.after.x_cells &&
                 with_dry.after.y_cells==no_dry.after.y_cells &&
                 with_dry.vmass.mass_mixed[0]<=no_dry.vmass.mass_mixed[0] &&
                 with_dry.pre_dry_qold_mixed.size()==1 &&
                 with_dry.pre_dry_qold_mixed[0]>=with_dry.vmass.mass_mixed[0],
                 "calm DRY changed puff trajectory or mass chronology");
            if(with_dry.dry->removed_mass[0]>0.0F)++removed_calm;
        }
        need(removed_calm>0U &&
             calm_dry_driver.vertical(1).mass_mixed[0] <=
                  calm_terrain_driver.vertical(1).mass_mixed[0],
             "original LCALMF false VCBAR produced no calm H3 removal");
        std::cout<<"P7_NATIVE_CALM_IDOPT1_CTADJ2_DRY_CALCPF_1H=PASS"
                 <<" SUBSTEPS="<<calm_dry_samples
                 <<" DRY_REMOVAL_SUBSTEPS="<<removed_calm
                 <<" DRY_VCBAR_LCALMF=FALSE"
                 <<" HEFEI_H9_PARITY=NOT_YET_ACCEPTED\\n";
    }
    const auto midpoint_control=make_original_flat_calcpf_sampler(
        plume_grid,100.0F,3600.0F,3.0F,
        OriginalFlatVerticalMethod::substep_vcbar);
    std::size_t pufrecs_native_substeps=0;
    std::size_t receptor_changed_increments=0;
    std::size_t sample_diagnostic_count=0;
    bool zero_xfinal_receptor_verified=false;
    std::size_t nonzero_lower_mass_steps=0;
    std::size_t positive_concentration_steps=0;
    std::size_t geometry_bridge_substeps=0;
    const RiseCompSamplingKernel sampled_plume=[&](const RiseCompSamplingState& state) {
        // Probe the *actual* native substep's MET-cell -> original PUFRECS
        // REAL4 receptor center mapping, without treating this projection as
        // the still-unimplemented receptor-specific SIGTY/SIGTZ or GRISE.
        const float travel=state.after.total_distance_m -
                           state.before.total_distance_m;
        need(travel>0.0F && state.step_seconds>0.0F,
             "PUFRECS native FSTEP probe requires noncalm travel");
        OriginalPufrecsGridStepInputs g;
        g.x_begin_cells=state.before.x_cells;
        g.y_begin_cells=state.before.y_cells;
        g.x_end_cells=state.after.x_cells;
        g.y_end_cells=state.after.y_cells;
        g.sigma_y_begin_m=static_cast<float>(
            state.sigmas.adjust.sigma_y_begin_m);
        g.sigma_y_end_m=static_cast<float>(
            state.sigmas.adjust.sigma_y_end_m);
        g.distance_begin_m=state.before.total_distance_m;
        g.mean_wind_ms=travel/state.step_seconds;
        g.met_spacing_m=100.0F;
        g.ibsamp=1;g.jbsamp=1;g.sampling_nx=50;g.sampling_ny=50;
        g.fclip=3.0F;g.clip=true;
        const auto geom=original_pufrecs_grid_receptor_geometry(g,5+5*50);
        need(std::isfinite(geom.fraction) &&
             std::isfinite(geom.distance_to_receptor_m) &&
             std::isfinite(geom.time_to_receptor_s) &&
             geom.distance_to_receptor_m>=0.0F &&
             geom.time_to_receptor_s>=0.0F,
             "PUFRECS native receptor frame returned invalid geometry");
        ++geometry_bridge_substeps;
        auto concentrations=plume_sampler(state);
        if(!zero_xfinal_receptor_verified) {
            // Original PRFIN legitimately sets XFINAL=0 when WSSTK<1m/s.
            // Test the REAL4 PUFRECS receptor branch through the actual
            // native COMP sampling state without altering its puff history.
            auto zero_final=state;
            zero_final.receptor_final_rise_distance_m=0.0F;
            const auto zero_values=plume_sampler(zero_final);
            need(zero_values.size()==2500U &&
                 std::all_of(zero_values.begin(),zero_values.end(),
                    [](float value){return std::isfinite(value)&&value>=0.0F;}),
                 "PUFRECS refused source-valid XFINAL=0 receptor sampling");
            // PFSCRN may reject every receptor before PUFRECS is called:
            // its early return cannot be used as a negative-XFINAL oracle.
            // Source-negative input validation remains inside PUFRECS itself.
            zero_xfinal_receptor_verified=true;
            std::cout<<"P7_PUFRECS_ORIGINAL_ZERO_XFINAL=PASS"
                     <<" CALCPF=ACTUAL_NATIVE_COMP_SAMPLER"
                     <<" CALM_TERRAIN_DRY=NOT_YET_ACCEPTED\\n";
        }
        const auto midpoint=midpoint_control(state);
        need(midpoint.size()==concentrations.size() &&
             concentrations.size()==2500U,
             "native VCBAR live field diverged in receptor dimensions");
        ++pufrecs_native_substeps;
        for(std::size_t i=0;i<concentrations.size();++i) {
            need(std::isfinite(concentrations[i]) && concentrations[i]>=0.0F,
                 "native VCBAR live returned nonfinite/negative concentration");
            if(std::bit_cast<std::uint32_t>(concentrations[i])!=
               std::bit_cast<std::uint32_t>(midpoint[i]))
                ++receptor_changed_increments;
        }
        const auto present=std::count_if(concentrations.begin(),concentrations.end(),
                                        [](float v){return v>0.0F;});
        if(state.vmass.mass_mixed[0]>0.0F)++nonzero_lower_mass_steps;
        if(present>0)++positive_concentration_steps;
        if(sample_diagnostic_count<5 || present>0){
            if(sample_diagnostic_count<5 || positive_concentration_steps<3)
                std::cerr<<"P7_6H_CALCPF_DIAG"
                         <<" substep="<<sample_diagnostic_count
                         <<" old=("<<state.before.x_cells<<","<<state.before.y_cells<<","
                                      <<state.before.z_m<<")"
                         <<" new=("<<state.after.x_cells<<","<<state.after.y_cells<<","
                                      <<state.after.z_m<<")"
                         <<" qm="<<state.vmass.mass_mixed[0]
                         <<" qu="<<state.vmass.mass_above[0]
                         <<" sz_mid="<<state.sigmas.step.sigma_z_mid_m
                         <<" sy_mid="<<state.sigmas.step.sigma_y_mid_m
                         <<" h_lid="<<state.vmass.reflecting_lid_m
                         <<" affected="<<present<<"\\n";
        }
        ++sample_diagnostic_count;
        return concentrations;
    };
    std::vector<std::vector<float>> six_fields;
    std::size_t meaningful_cells=0;
    {
        ConcFileWriter binary(binary_path.string(),"2.2",
            "P7 restricted native six-hour test",{});
        HourlyConcSeriesWriter series(binary,
            original_total_source_descriptor(510885.0F,3531269.0F),50,50);
        OriginalCompRiseMultiPuffHours six_native;
        for(int h=0;h<6;++h){
            const auto six=six_native.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
                met,geo,ctl,pg,false,single_mass,wide_domain,99,
                2500,sampled_plume);
            need(six.hour_index==static_cast<std::size_t>(h) &&
                 six.receptor_concentrations.size()==2500 &&
                 six_native.completed_hours()==static_cast<std::size_t>(h+1),
                 "flat CALCPF failed original across-hour stateful source continuation");
            ConcPeriod hour{};
            hour.begin_year=2022;hour.begin_julian=1;hour.begin_hour=h;
            hour.end_year=2022;hour.end_julian=1;hour.end_hour=h+1;
            for(const float conc:six.receptor_concentrations)
                if(conc>0.0F)++meaningful_cells;
            series.write_hour(hour,six.receptor_concentrations);
            six_fields.push_back(six.receptor_concentrations);
        }
        need(series.hours_written()==6 && binary.records_written()==18,
             "six-hour OUTPUT lacked period/source/species field records");
        binary.close();
    }
    if(meaningful_cells==0)
        std::cerr<<"P7_NATIVE_6H_ZERO_FIELD_DIAGNOSTIC"
                 <<" sampling_substeps="<<sample_diagnostic_count
                 <<" mass_present_steps="<<nonzero_lower_mass_steps
                 <<" positive_receptor_steps="<<positive_concentration_steps
                 <<" grid_origin_cells=("<<plume_grid.ibsamp<<","<<plume_grid.jbsamp<<")\\n";
    need(meaningful_cells>0,
         "flat CALCPF six-hour output passed on an entirely zero concentration field");
    need(geometry_bridge_substeps==sample_diagnostic_count &&
         geometry_bridge_substeps>0,
         "PUFRECS native geometry was not checked at every CALCPF substep");
    need(pufrecs_native_substeps==sample_diagnostic_count &&
         pufrecs_native_substeps>0,
         "PUFRECS receiver PG+VCOUP was not executed on every COMP substep");
    std::cout<<"P7_NATIVE_COMP_PUFRECS_RECEIVER_FRAME=PASS"
             <<" SUBSTEPS="<<geometry_bridge_substeps
             <<" REAL4_CENTER_MAPPING=YES"
             <<" REAL_2022_PUFRECS_SIGMA=NOT_YET_ACCEPTED\\n";
    const auto observed=read_conc_species_fields(binary_path.string(),50,50);
    const auto periods=read_conc_periods(binary_path.string());
    need(observed.size()==6 && periods.size()==6,
         "six-hour source-typed OUTPUT period/species count mismatched");
    for(std::size_t hour=0;hour<6;++hour){
        need(observed[hour].species_index==1 &&
             periods[hour].begin_hour==static_cast<int>(hour) &&
             periods[hour].end_hour==static_cast<int>(hour+1) &&
             observed[hour].values.size()==2500,
             "six-hour native field timestamp or H-3 source descriptor mismatch");
        for(std::size_t i=0;i<2500;++i)
            need(std::bit_cast<std::uint32_t>(observed[hour].values[i])==
                 std::bit_cast<std::uint32_t>(six_fields[hour][i]),
                 "six-hour native CALCPF field bytes changed during OUTPUT");
    }
    std::filesystem::remove(binary_path);
    std::cout<<"P7_NATIVE_PUFRECS_PG_VCOUP_CALCPF_OUTPUT_6H=PASS"
             <<" HOURS=6 RECORDS=18 RECEIVERS=2500"
             <<" PUFRECS_PG_VCOUP_NATIVE_SUBSTEPS="<<pufrecs_native_substeps
             <<" PUFRECS_PG_VCOUP_CHANGED_INCREMENTS="<<receptor_changed_increments
             <<" PERSISTENT_NATIVE_PUFFS=YES"
             <<" NONZERO_RECEPTOR_VALUES="<<meaningful_cells
             <<" CONCENTRATION_REAL4=BITWISE_READBACK"
             <<" SOURCE_DESCRIPTOR=ORIGINAL_OUTPUT_LAYOUT"
             <<" FULL_WROUT1_HEADER=ACCEPTED_SEPARATELY"
             <<" ORIGINAL_RECEPTOR_SPECIFIC_PUFRECS=NOT_YET_ACCEPTED"
             <<" REAL_2022_PARITY=NOT_YET_ACCEPTED\\n";

    const auto state=driver.motion(1);
    const auto count=driver.completed_hours();
    auto bad=source;bad.point.source_x_km=130;
    bool fail=false;try{(void)driver.advance_hour_point_mxsam99_unsplit(
        met,geo,ctl,pg,false,bad);}catch(const std::exception&){fail=true;}
    need(fail && driver.completed_hours()==count &&
         driver.motion(1).travel_time_s==state.travel_time_s &&
         driver.active_count()==88,
         "late source failure partially committed the MXSAM99 hour");
    std::cout<<"P7_NATIVE_COMP_MXSAM99_UNSPLIT=PASS"
             <<" NEW_FIRST_HOUR_STEPS="<<a.steps.size()
             <<" OLD_SECOND_HOUR_STEPS="<<old_steps
             <<" SOURCE_VMASS=YES"
             <<" NATIVE_RLSMET_WSNEW_MXSAM99=YES"
             <<" FSTEP_SPLIT=NOT_YET_IMPLEMENTED"
             <<" ORIGINAL_HEFEI_143H=NOT_YET_ACCEPTED\n";
}
}
int main(){try{test();return 0;}catch(const std::exception& e){
    std::cerr<<"P7_NATIVE_COMP_MXSAM99_UNSPLIT=FAIL "<<e.what()<<"\n";return 1;}}
