#include "cteas/puff/original_comp_calm.hpp"
#include "cteas/puff/original_comp_rise_hourly.hpp"
#include <bit>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
void check(bool value,const char* msg){
    if(!value)throw std::runtime_error(msg);
}
void transport_contract(){
    using cteas::puff::original_comp_calm_transport;
    const auto moving=original_comp_calm_transport(0.8F,0.3F,0.8544F,0.5F);
    check(!moving.calm&&moving.u_ms==0.8F&&moving.v_ms==0.3F&&
          moving.wind_speed_ms==0.8544F,
          "noncalm transport changed an original REAL4 value");
    const auto slow=original_comp_calm_transport(0.2F,0.0F,0.2F,0.5F);
    check(slow.calm&&slow.u_ms==0.2F&&slow.v_ms==0.001F&&
          slow.wind_speed_ms==0.2F,
          "COMP WSCALM incorrectly replaces WS by 0.5 or zeroes UADV");
    const auto zero=original_comp_calm_transport(0.0F,0.0F,0.0F,0.5F);
    check(zero.calm&&zero.u_ms==0.0F&&zero.v_ms==0.001F&&
          zero.wind_speed_ms==0.001F,
          "COMP UCALM=0.001 fallback is not source faithful");
    const auto negative_v=original_comp_calm_transport(0.2F,-0.01F,0.201F,0.5F);
    check(negative_v.calm&&negative_v.v_ms==-0.01F,
          "COMP incorrectly rewrote a nonzero negative VADV");
    const auto threshold=original_comp_calm_transport(0.5F,0.0F,0.5F,0.5F);
    check(!threshold.calm&&threshold.v_ms==0.0F,
          "COMP WSCALM boundary must use strictly less-than");
    bool rejected=false;
    try {(void)original_comp_calm_transport(0.0F,0.0F,-1.0F,0.5F);}
    catch(const std::invalid_argument&){rejected=true;}
    check(rejected,"invalid COMP negative transport speed was accepted");
}
void atomic_calm_production_gate(){
    using namespace cteas::puff;
    OriginalMetHour met;
    met.nx=120;met.ny=120;met.nz=3;
    constexpr std::size_t cells=120U*120U;
    met.u.assign(cells*3U,1.2F);
    met.v.assign(cells*3U,0.0F);
    met.zi.assign(cells,250.0F);
    met.ipgt.assign(cells,4);
    Calmet21Static statics;
    statics.cell_face_m={0.0F,100.0F,200.0F,300.0F};
    statics.roughness_m.assign(cells,0.25F);
    NeutralCompControls ctrl;
    ctrl.max_sampling_steps=99;
    ctrl.met_spacing_m=100.0F;
    ctrl.max_sample_distance_cells=1.0F;
    ctrl.calm_threshold_ms=0.5F;
    ctrl.seconds=3600.0F;
    ctrl.source_period_s=3600.0F;
    DispersionSetup pg;
    pg.mdisp=3;pg.averaging_factor=1.0;
    pg.sigma_y_heffter_m=550.0;pg.heffter_sigma_z=false;
    pg.roughness_adjustment=false;
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
    source.mass.emission_rate={2,0};
    source.cadence.wind_speed_ms=1.2;
    source.cadence.emission_interval=0.5;
    source.cadence.max_puffs=99;
    source.cadence.hour_seconds=3600;
    OriginalCompRiseMultiPuffHours driver;
    const auto first=driver.advance_hour_point_mxsam99_adaptive(
        met,statics,ctrl,pg,false,source);
    check(driver.completed_hours()==1&&first.active_puffs==1&&
          first.steps.size()>0,"first noncalm rising COMP hour did not commit");
    const auto before=driver.motion(1);
    const auto vertical=driver.vertical(1);
    auto low=met;
    low.u.assign(cells*3U,0.2F);
    bool rejected=false;
    std::string message;
    try {(void)driver.advance_hour_point_mxsam99_adaptive(
        low,statics,ctrl,pg,false,source);}
    catch(const std::invalid_argument& e){
        rejected=true;message=e.what();
    }
    check(rejected&&message.find("WSCALM")!=std::string::npos,
          "low-wind original COMP did not fail at explicit calm dispersion boundary");
    check(driver.completed_hours()==1&&driver.active_count()==1&&
          driver.motion(1).travel_time_s==before.travel_time_s&&
          driver.motion(1).x_cells==before.x_cells&&
          driver.vertical(1).completed_substeps==vertical.completed_substeps,
          "rejected CALPUFF calm dispersion partially committed puff state");
    // A rejected hour is not silently skipped; a later noncalm hour
    // can continue from precisely the previously committed history.
    const auto second=driver.advance_hour_point_mxsam99_adaptive(
        met,statics,ctrl,pg,false,source);
    check(second.hour_index==1&&driver.completed_hours()==2&&
          driver.active_count()==2,
          "calm-hour refusal corrupted future native COMP chronology");
}
} // namespace
int main(){
    try {
        transport_contract();
        atomic_calm_production_gate();
        std::cout<<"P7_NATIVE_COMP_CALM_BRANCH_GATE=PASS"
                 <<" COMP_WSCALM_0P5=SOURCE_ORDERED"
                 <<" UCALM_0P001=SOURCE_ORDERED"
                 <<" CALM_SIGTY_IDOPT1=FAIL_CLOSED"
                 <<" LOW_WIND_HOUR=ATOMIC_ROLLBACK"
                 <<" FULL_989_VENDOR_SUBSTEP_PARITY=NOT_YET_ACCEPTED\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"P7_NATIVE_COMP_CALM_BRANCH_GATE=FAIL "<<e.what()<<'\n';
        return 1;
    }
}
