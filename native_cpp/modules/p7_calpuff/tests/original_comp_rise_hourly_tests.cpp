#include "cteas/puff/original_comp_rise_hourly.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
using namespace cteas::puff;
void check(bool v,const char* msg){
    if(!v)throw std::runtime_error(msg);
}
template<class F> void rejects(F&& f,const char* msg){
    bool caught=false;try{f();}catch(const std::exception&){caught=true;}
    check(caught,msg);
}
RisePointAdmission puff(int id,double x){
    RisePointAdmission a;
    a.puff_id=id;
    a.point.source_x_km=x;
    a.point.source_y_km=5;
    a.point.stack_height_m=50;
    a.point.effective_height_m=160;
    a.point.x_final_m=230;
    a.point.buoyancy_flux=49;
    a.point.x_final_buoyancy_m=230;
    a.point.z_final_buoyancy_m=110;
    a.point.stack_wind_speed_ms=2;
    a.point.sigma_y_source_m=1;
    a.point.sigma_z_source_m=1;
    a.point.stability_class=4;
    a.mass.species_count=2;
    a.mass.emission_duration_s=3600;
    a.mass.effective_height_m=160;
    a.mass.mixing_height_m=250;
    a.mass.max_layer_height_m=300;
    a.mass.mass_fraction_mixed=1;
    a.mass.stability_class=4;
    a.mass.gaussian_distribution=1;
    a.mass.emission_rate={2,3};
    return a;
}
void test_original_zero_xfinal_point_release() {
    // Source-scoped PRFIN: WSSTK < original WSSTK0=1.0 gives
    // XFINB=XFINM=XFINAL=0, yet the plume rises vertically and
    // POINTS1 still emits positive mass. This is not an arbitrary
    // zero-XFINAL acceptance for noncalm or corrupted input.
    OriginalPointPrfinRequest in;
    in.stack_height_m=70.8F;
    in.max_sample_distance_cells=1.0F;
    OriginalPointNativeSourceParameters src;
    src.met_spacing_m=100.0F;
    src.initial_sigma_y_m=1.0F;
    src.initial_sigma_z_m=1.0F;
    src.emission_rates={834000.0,0.0};
    OriginalPointPrfinResult rise;
    rise.stability_class=3;
    rise.stack_wind_ms=0.189907F;
    rise.release_wind_ms=0.276511F;
    rise.effective_height_m=153.648F;
    rise.x_final_m=0.0F;
    rise.final_rise_m=82.848F;
    rise.mixing_height_m=1009.945F;
    rise.max_layer_height_m=1009.945F;
    rise.mixed_fraction=1.0F;
    rise.buoyancy_flux=5.014F;
    rise.momentum_flux=181.836F;
    rise.buoyancy_variance_m2=560.31F;
    rise.brigg.z_final_buoyancy_m=82.848;
    rise.release=release_cadence({
        rise.release_wind_ms,
        in.hour_seconds/(src.met_spacing_m*in.max_sample_distance_cells),
        in.max_new_puffs,in.hour_seconds});
    const auto source=original_point_hour_from_prfin(in,rise,src);
    check(source.point.x_final_m==0.0 &&
          source.point.effective_height_m>source.point.stack_height_m &&
          source.mass.species_count==2 &&
          source.mass.emission_rate[0]>0.0,
          "original PRFIN calm XFINAL=0 must preserve physical puff release");
    rise.stack_wind_ms=1.1F;
    rejects([&]{(void)original_point_hour_from_prfin(in,rise,src);},
            "noncalm XFINAL=0 cannot pass original-source guard");
    rise.stack_wind_ms=0.189907F;
    rise.x_final_m=-1.0F;
    rejects([&]{(void)original_point_hour_from_prfin(in,rise,src);},
            "negative XFINAL cannot pass original-source guard");
    rise.x_final_m=0.0F;
    rise.brigg.x_final_buoyancy_m=1.0;
    rejects([&]{(void)original_point_hour_from_prfin(in,rise,src);},
            "inconsistent PRFIN buoyancy XFINAL cannot pass source guard");
    std::cout<<"P7_ORIGINAL_POINT_ZERO_XFINAL_WIND_LT_1=PASS"
             <<" INVALID_NONCALM_AND_NEGATIVE_REJECTED=YES\n";
}
void run(int total_hours){
    OriginalCompRiseMultiPuffHours scheduler;
    OriginalMetHour met;
    met.nx=50;met.ny=50;met.nz=3;
    constexpr std::size_t cells=2500;
    met.zi.assign(cells,250.0F);
    met.ipgt.assign(cells,4);
    met.u.assign(3*cells,0.002F);
    met.v.assign(3*cells,0.0F);
    for(std::size_t n=cells;n<2*cells;++n)met.u[n]=0.006F;
    for(std::size_t n=2*cells;n<3*cells;++n)met.u[n]=0.010F;
    Calmet21Static statics;
    statics.cell_face_m={0,100,200,300};
    NeutralCompControls ctl;
    ctl.max_sampling_steps=1;
    // Synthetic tiny-wind PG lifecycle fixture only: explicitly keep these
    // 0.002-0.010 m/s winds NONCALM by choosing WSCALM=0.001.
    // The frozen Hefei puff.inp independently uses WSCALM=0.5.
    ctl.calm_threshold_ms=0.001F;
    DispersionSetup pg;
    pg.mdisp=3;
    pg.averaging_factor=1;
    pg.sigma_y_heffter_m=550;
    pg.heffter_sigma_z=false;
    pg.roughness_adjustment=false;
    bool final_rise=false;
    for(int h=0;h<total_hours;++h){
        std::vector<RisePointAdmission> added;
        if(h==0)added.push_back(puff(1,5));
        if(h==6)added.push_back(puff(2,6));
        if(h==70)added.push_back(puff(3,7));
        if(h==2){
            // The old puff can complete its pending step, but a NEW point
            // would leave the CALMET grid. The ENTIRE hour must roll back.
            const auto old=scheduler.motion(1);
            const auto vertical=scheduler.vertical(1);
            const auto steps=scheduler.puff_steps(1);
            auto bad=puff(2,50.5);
            rejects([&]{
                (void)scheduler.advance_hour(
                    met,statics,ctl,pg,false,{bad});
            },"late rise puff error did not abort the whole hour");
            check(scheduler.completed_hours()==2 &&
                  scheduler.active_count()==1 &&
                  scheduler.motion(1).travel_time_s==old.travel_time_s &&
                  scheduler.motion(1).x_cells==old.x_cells &&
                  scheduler.vertical(1).completed_substeps==
                    vertical.completed_substeps &&
                  scheduler.puff_steps(1)==steps,
                  "late rising puff failure partially committed old puff");
            rejects([&]{(void)scheduler.puff_steps(2);},
                    "failed release was retained");
        }
        const auto period=scheduler.advance_hour(
            met,statics,ctl,pg,false,added);
        const auto expected=h<6?1U:h<70?2U:3U;
        check(period.hour_index==static_cast<std::size_t>(h) &&
              period.active_after==expected &&
              period.puffs.size()==expected &&
              scheduler.active_count()==expected &&
              scheduler.completed_hours()==static_cast<std::size_t>(h+1),
              "rising multi-puff hour count or release order inconsistent");
        int previous=0;
        for(const auto& rec:period.puffs){
            check(rec.puff_id>previous,
                  "nondeterministic multi-puff native order");
            previous=rec.puff_id;
            const int released=rec.puff_id==1?0:rec.puff_id==2?6:70;
            const auto clock=static_cast<std::size_t>(h-released+1);
            const auto v=scheduler.vertical(rec.puff_id);
            // Source COMP L10503-L10519 only runs RISEWIND while
            // the odd-ICODE puff still travels toward XFINAL. Earlier
            // synthetic tests incorrectly required two rise iterations
            // even after the plume reached its final-rise distance.
            const bool rising=
                rec.step.before.total_distance_m<230.0F;
            check(rec.step.rise.adjusted.passes==(rising?2:0),
                  "source COMP post-XFINAL RISEWIND gating drifted");
            check(rec.step.after.travel_time_s==
                    static_cast<float>(clock*3600) &&
                  v.completed_substeps==clock &&
                  v.committed_lid_steps==clock &&
                  rec.step.bookkeeping.mid_time_s==1800 &&
                  rec.step.after.z_m==rec.step.final_height_m,
                  "native multi-puff rise/PG/VMASS state was not persistent");
            for(std::size_t species=0;species<2;++species){
                const float expect=species?10800.0F:7200.0F;
                const float mass=v.mass_mixed.at(species)+
                                 v.mass_above.at(species);
                check(std::isfinite(mass) &&
                      std::abs(mass-expect)<=0.00001F*expect,
                      "native multi-puff rising tracer mass drifted");
            }
            if(rec.step.before.total_distance_m>=230.0F)
                final_rise=true;
        }
    }
    check(total_hours<143 || final_rise,
          "full rise profile never reached final plume height");
    if(total_hours>6){
        const auto lost=scheduler.compact_original_inactive({2});
        check(lost==1U &&
              scheduler.active_count()==(total_hours>70?2U:1U),
              "original ROLLDN old-puff compaction disturbed neighbors");
        rejects([&]{(void)scheduler.motion(2);},
                "ROLDN retired rising puff remains active");
    }
    std::cout<<"P7_NATIVE_RISING_COMP_MULTIPUFF=PASS HOURS="<<total_hours
             <<" ACTIVE_RELEASES=0,6,70"
             <<" NATIVE_GRISE_RISEWIND=YES NATIVE_PG_SIGMA=YES"
             <<" NATIVE_VMASS=YES WHOLE_HOUR_ROLLBACK=YES"
             <<" SOURCE_MASS_CONSERVED=YES"
             <<" FROZEN_HEFEI_EQUIVALENCE=NOT_YET_VALIDATED\n";
}
}
int main(int argc,char** argv){
    try{
        if(argc!=2)throw std::invalid_argument("expected hours 1|6|143");
        const int h=std::stoi(argv[1]);
        if(h!=1&&h!=6&&h!=143)
            throw std::invalid_argument("hours must be 1, 6 or 143");
        test_original_zero_xfinal_point_release();
        run(h);
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P7_NATIVE_RISING_COMP_MULTIPUFF=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
