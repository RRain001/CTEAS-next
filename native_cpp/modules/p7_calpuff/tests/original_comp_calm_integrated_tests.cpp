// Scoped production COMP opt-in: real source-ordered RISEWIND -> SETPUF calm
// IDOPT1 + TURBSET minima on an actual native puff state, not a math stub.
#include "cteas/puff/original_comp_rise_hourly.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>

using namespace cteas::puff;
namespace {
void check(bool ok,const char* message){
 if(!ok)throw std::runtime_error(message);
}
OriginalPointHourSource source(){
 OriginalPointHourSource s;
 s.point.source_x_km=5;s.point.source_y_km=5;
 s.point.stack_height_m=50;s.point.effective_height_m=160;
 s.point.x_final_m=230;s.point.buoyancy_flux=49;
 s.point.x_final_buoyancy_m=230;s.point.z_final_buoyancy_m=110;
 s.point.stack_wind_speed_ms=1.2;s.point.sigma_y_source_m=1;
 s.point.sigma_z_source_m=1;s.point.stability_class=4;
 s.mass.species_count=2;s.mass.emission_duration_s=3600;
 s.mass.effective_height_m=160;s.mass.mixing_height_m=250;
 s.mass.max_layer_height_m=300;s.mass.mass_fraction_mixed=1;
 s.mass.stability_class=4;s.mass.gaussian_distribution=1;
 s.mass.emission_rate={2,0};
 s.cadence.wind_speed_ms=1.2;s.cadence.emission_interval=0.5;
 s.cadence.max_puffs=99;s.cadence.hour_seconds=3600;
 return s;
}
}
int main(){
 try{
  OriginalMetHour met;
  met.nx=120;met.ny=120;met.nz=3;
  constexpr std::size_t n=120U*120U;
  met.u.assign(n*3U,1.2F);met.v.assign(n*3U,0.0F);
  met.zi.assign(n,250.0F);met.ipgt.assign(n,4);
  met.el.assign(n,-100.0F);
  Calmet21Static st;
  st.present=true;st.cell_face_m={0.0F,100.0F,200.0F,300.0F};
  st.roughness_m.assign(n,0.25F);st.land_use.assign(n,1);
  NeutralCompControls ctrl;
  ctrl.max_sampling_steps=99;ctrl.met_spacing_m=100;
  ctrl.max_sample_distance_cells=1;ctrl.calm_threshold_ms=.5F;
  ctrl.seconds=3600;ctrl.source_period_s=3600;
  DispersionSetup pg;
  pg.mdisp=3;pg.averaging_factor=1;pg.sigma_y_heffter_m=550;
  pg.heffter_sigma_z=false;pg.roughness_adjustment=false;
  OriginalCompRiseMultiPuffHours driver;
  const auto hour0=driver.advance_hour_point_mxsam99_adaptive(
      met,st,ctrl,pg,false,source());
  check(hour0.active_puffs==1&&driver.completed_hours()==1,
        "first noncalm hour missing");
  const auto old=driver.motion(1);
  check(old.total_distance_m>230,"test needs a post-rise puff");
  const auto old_vertical=driver.vertical(1);
  auto low=met;
  low.u.assign(n*3U,0.2F);
  ctrl.calm_mdisp3=NativeCalmMdisp3Controls{};
  ctrl.calm_mdisp3->iwat1=50;ctrl.calm_mdisp3->iwat2=55;
  ctrl.calm_mdisp3->original_turbulence.svmin.fill(.5F);
  ctrl.calm_mdisp3->original_turbulence.swmin.fill(.06F);

  // Source COMP L10863-10883: JSUP is applied BEFORE SWMIN lookup,
  // only above the bounded mixed layer and only when PGT ISTAB<5.
  // The frozen original H9 /CSIGMA/ audit found 0.03 m/s (JSUP=5)
  // rather than the unadjusted PGT C value 0.08 m/s.
  check(original_comp_turbset_jdstab(3,5,160.0F,50.0F)==5 &&
        original_comp_turbset_jdstab(3,5,50.0F,50.0F)==3 &&
        original_comp_turbset_jdstab(3,0,160.0F,50.0F)==3 &&
        original_comp_turbset_jdstab(5,6,160.0F,50.0F)==5 &&
        original_comp_turbset_jdstab(6,5,160.0F,50.0F)==6,
        "source COMP above-lid JSUP conditional was not ported");
  auto source_swmin=ctrl.calm_mdisp3->original_turbulence;
  source_swmin.swmin[2]=.08F; // Original land C, SWMIN(3,1)
  source_swmin.swmin[4]=.03F; // Original land E, SWMIN(5,1)
  const auto source_upper=original_turbset_mdisp3_minimum(
      source_swmin,original_comp_turbset_jdstab(3,5,160.0F,50.0F),1);
  const auto source_lower=original_turbset_mdisp3_minimum(
      source_swmin,original_comp_turbset_jdstab(3,5,49.0F,50.0F),1);
  check(source_upper.sigw_ms==.03F && source_lower.sigw_ms==.08F,
        "original H9 MDISP3 above-PBL SWMIN .03/.08 selector drift");
  std::cout<<"P7_ORIGINAL_COMP_JSUP_TURBSET_ABOVE_PBL=PASS"
           <<" ABOVE_SIGW="<<source_upper.sigw_ms
           <<" BELOW_SIGW="<<source_lower.sigw_ms
           <<" JSUP5_FROM_SOURCE_DECK=REQUIRED"
           <<" HEFEI_H9_REAL4=NOT_YET_ACCEPTED\\n";

  // Use identical native puff history and wind to exercise the
  // original stable ELS>0 logarithmic SIGTZ inversion in production,
  // independently of the ELS<=0 physical substeps below.
  auto stable_driver=driver;
  auto stable_met=low;
  stable_met.el.assign(n,100.0F);
  const auto stable_hour=stable_driver.advance_hour_existing_mxsam99_adaptive(
      stable_met,st,ctrl,pg,false);
  check(stable_driver.completed_hours()==2&&!stable_hour.steps.empty(),
        "stable native CALPUFF calm hour did not commit");
  std::size_t stable_calm=0;
  for(const auto& sub:stable_hour.steps){
    if(!sub.step.bookkeeping.calm)continue;
    ++stable_calm;
    check(sub.step.sigma.adjust.stored_sigma_z_m>0.0,
          "stable log-secant SIGTZ left the native physical domain");
  }
  check(stable_calm>0,"stable native COMP has no actual calm substeps");

  // An actual post-rise old-puff hour, with no new emissions.
  const auto hour1=driver.advance_hour_existing_mxsam99_adaptive(
      low,st,ctrl,pg,false);
  check(driver.completed_hours()==2&&hour1.active_puffs==1,
        "native calm hour did not commit");
  check(!hour1.steps.empty(),"calm hour had no physical substeps");
  std::size_t calm=0;
  for(const auto& step:hour1.steps) {
    if(!step.step.bookkeeping.calm)continue;
    ++calm;
    check(step.step.bookkeeping.dispersion_y_option==1&&
          step.step.bookkeeping.dispersion_z_option==1&&
          step.step.bookkeeping.x_final_m==0.0,
          "CALPUFF SETPUF LCALM state/options not selected");
    check(step.step.sigma.adjust.minimum_sigma_y_m>0&&
          step.step.sigma.adjust.minimum_sigma_z_m>0&&
          step.step.sigma.adjust.stored_sigma_y_m>0,
          "calm midpoint sigma minimum not generated");
  }
  check(calm>0,"low wind did not drive actual calm COMP SETPUF");
  check(stable_hour.steps.front().step.sigma.step.sigma_z_end_m!=
        hour1.steps.front().step.sigma.step.sigma_z_end_m,
        "EL>0 SIGTZ branch was silently replaced with ELS<=0 math");
  const auto post=driver.vertical(1);
  check(post.completed_substeps>old_vertical.completed_substeps &&
        post.committed_lid_steps==post.completed_substeps &&
        !post.vmass_pending,
        "native VMASS/SETPUF/CALCPF history was not atomic");

  // Cross-hour source-ordered rising -> calm: the latest short-lived
  // POINTS1 episodes begin H2 with XTOTB<XFINAL, unlike older fully risen
  // puffs. COMP must run their RISEWIND/GRISE before LCALM SETPUF cancels
  // further horizontal rise, and preserve every hourly state atomically.
  {
    auto late_source=source();
    late_source.cadence.emission_interval=36.0;
    OriginalCompRiseMultiPuffHours rising_driver;
    const auto previous=rising_driver.advance_hour_point_mxsam99_adaptive(
        met,st,ctrl,pg,false,late_source);
    std::size_t still_rising=0;
    for(const int puff_id:rising_driver.canonical_ids()){
      if(rising_driver.motion(puff_id).total_distance_m<
         late_source.point.x_final_m)++still_rising;
    }
    check(previous.active_puffs>1 && still_rising>0,
          "cross-hour fixture has no unfinished rising puffs");
    const auto calm_rising_hour=rising_driver.advance_hour_existing_mxsam99_adaptive(
        low,st,ctrl,pg,false);
    std::size_t calm_rising_substeps=0;
    for(const auto& sub:calm_rising_hour.steps){
      const auto& p=sub.step;
      if(!(p.bookkeeping.calm &&
           p.before.total_distance_m<late_source.point.x_final_m))
        continue;
      ++calm_rising_substeps;
      check(p.bookkeeping.dispersion_y_option==1 &&
            p.bookkeeping.dispersion_z_option==1 &&
            p.bookkeeping.x_final_m==0.0F &&
            p.after.total_distance_m>=p.before.total_distance_m &&
            p.sigma.adjust.minimum_sigma_y_m>0 &&
            p.sigma.adjust.minimum_sigma_z_m>0,
            "rising-to-calm RISEWIND GRISE SETPUF state invalid");
    }
    check(rising_driver.completed_hours()==2U &&
          calm_rising_substeps>0 &&
          calm_rising_hour.active_puffs==previous.active_puffs,
          "rising-to-calm original COMP transition did not commit");
    std::cout<<"P7_ORIGINAL_COMP_RISING_TO_CALM_2H=PASS"
             <<" UNFINISHED_BEFORE="<<still_rising
             <<" ACTUAL_CALM_RISING_SUBSTEPS="<<calm_rising_substeps
             <<" GRISE_BEFORE_SETPUF=YES"
             <<" HEFEI_H9_REAL4=NOT_YET_ACCEPTED\\n";
  }

  // Unsupported downstream modes MUST continue to fail closed and roll
  // back the whole hour, even with a valid original turbulence adapter.
  auto unsupported=ctrl;
  unsupported.mctadj2=NativeMctadj2Controls{};
  const auto snapshot=driver.motion(1);
  bool rejected=false;
  try{(void)driver.advance_hour_existing_mxsam99_adaptive(
      low,st,unsupported,pg,false);}
  catch(const std::invalid_argument&){rejected=true;}
  check(rejected&&driver.completed_hours()==2&&
        driver.motion(1).travel_time_s==snapshot.travel_time_s,
        "unsupported calm terrain was accepted or partially committed");
  std::cout<<"P7_ORIGINAL_COMP_CALM_NATIVE_INTEGRATION=PASS"
           <<" COMP_IDOPT1_REAL_SUBSTEPS="<<calm
           <<" COMP_STABLE_CALM_SUBSTEPS="<<stable_calm
           <<" VMASS_SETPUF_COMMIT=ATOMIC"
           <<" RECEPTOR_MCTADJ2_DRY=FAIL_CLOSED"
           <<" HEFEI_989_CALM_PARITY=NOT_YET_ACCEPTED\n";
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P7_ORIGINAL_COMP_CALM_NATIVE_INTEGRATION=FAIL "
           <<e.what()<<'\n';
  return 1;
 }
}
