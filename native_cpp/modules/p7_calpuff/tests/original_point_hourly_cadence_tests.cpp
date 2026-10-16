#include "cteas/puff/original_comp_rise_hourly.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {
using namespace cteas::puff;
void need(bool v,const char* msg){if(!v)throw std::runtime_error(msg);}
template<class F> void fail(F&& fn,const char* msg){
    bool caught=false;try{fn();}catch(const std::exception&){caught=true;}
    need(caught,msg);
}
struct Inputs {
    OriginalCompRiseMultiPuffHours driver;
    OriginalMetHour met;
    Calmet21Static geo;
    NeutralCompControls ctl;
    DispersionSetup pg;
    OriginalPointHourSource source;
    Inputs() {
        met.nx=80;met.ny=80;met.nz=3;
        constexpr std::size_t n=80U*80U;
        met.zi.assign(n,250.0F);
        met.ipgt.assign(n,4);
        met.u.assign(3*n,0.002F);
        met.v.assign(3*n,0.0F);
        for(std::size_t i=n;i<2*n;++i)met.u[i]=0.006F;
        for(std::size_t i=2*n;i<3*n;++i)met.u[i]=0.010F;
        geo.cell_face_m={0,100,200,300};
        geo.roughness_m.assign(n,0.25F); // RLSMET/WINDSET requires original Z0
        ctl.seconds=3600.0F;
        ctl.source_period_s=3600.0F;
        ctl.max_sampling_steps=1;
        // This POINTS1 chronology fixture deliberately uses 0.002-0.010 m/s
        // winds and explicitly selects a TEST-ONLY noncalm WSCALM=0.001.
        // Real frozen Hefei puff.inp uses WSCALM=0.5, unchanged.
        ctl.calm_threshold_ms=0.001F;
        ctl.release_number=1;
        pg.mdisp=3;
        pg.averaging_factor=1;
        pg.sigma_y_heffter_m=550;
        pg.heffter_sigma_z=false;
        pg.roughness_adjustment=false;
        auto& p=source.point;
        p.source_x_km=5;
        p.source_y_km=5;
        p.stack_height_m=50;
        p.effective_height_m=160;
        p.x_final_m=230;
        p.buoyancy_flux=49;
        p.x_final_buoyancy_m=230;
        p.z_final_buoyancy_m=110;
        p.stack_wind_speed_ms=2;
        p.sigma_y_source_m=1;
        p.sigma_z_source_m=1;
        p.stability_class=4;
        auto& m=source.mass;
        m.species_count=2;
        m.emission_duration_s=3600;
        m.effective_height_m=160;
        m.mixing_height_m=250;
        m.max_layer_height_m=300;
        m.mass_fraction_mixed=1;
        m.stability_class=4;
        m.gaussian_distribution=1;
        m.emission_rate={2,3};
        source.cadence.wind_speed_ms=2.3;
        source.cadence.emission_interval=1.0;
        source.cadence.max_puffs=3;
        source.cadence.hour_seconds=3600;
    }
};
void native_release_wsnew() {
    Inputs fixture;
    auto& a=fixture;
    // The dummy input WSNEW is enormously above the permitted native
    // CALMET level-2 wind of 0.006 m/s. Native WINDSET must override it.
    a.source.cadence.wind_speed_ms=1000.0;
    a.source.cadence.emission_interval=100.0;
    a.source.cadence.max_puffs=3;
    const auto hour=a.driver.advance_hour_point_native_wsnew(
        a.met,a.geo,a.ctl,a.pg,false,a.source,0.5F);
    need(hour.cadence.puff_count==1 &&
         hour.cadence.emission_duration_s==3600.0F &&
         hour.new_puffs==1 && hour.active_after==1 &&
         hour.steps.size()==1 &&
         hour.steps[0].step.after.travel_time_s==3600.0F &&
         a.driver.completed_hours()==1 &&
         a.driver.active_count()==1,
         "native original RLSMET/WINDSET WSNEW was not used for POINTS1");
    const auto mixed=a.driver.vertical(1);
    need(mixed.mass_mixed.at(0)+mixed.mass_above.at(0)==7200.0F &&
         mixed.mass_mixed.at(1)+mixed.mass_above.at(1)==10800.0F,
         "native release wind integration caused mass drift");
    std::cout<<"P7_NATIVE_POINTS1_FROM_WINDSET=PASS"
             <<" EXTERNAL_WSNEW_IGNORED=YES"
             <<" METFM1_NATIVE_RELEASE_WIND=YES"
             <<" FROZEN_HEFEI_143H=NOT_YET_ACCEPTED\n";
}
void run(int hours){
    Inputs a;
    const auto n=a.source.cadence.max_puffs;
    const float dt=1200;
    double total0=0;
    double total1=0;
    for(int hour=0;hour<hours;++hour) {
        if(hour==1){
            const auto past=a.driver.motion(1);
            const auto v=a.driver.vertical(1);
            auto bad=a.source;
            bad.point.source_x_km=82;
            fail([&]{(void)a.driver.advance_hour_point_cadence(
                a.met,a.geo,a.ctl,a.pg,false,bad);},
                "off-grid release did not rollback whole hour");
            need(a.driver.completed_hours()==1 &&
                 a.driver.active_count()==static_cast<std::size_t>(n) &&
                 a.driver.motion(1).travel_time_s==past.travel_time_s &&
                 a.driver.vertical(1).completed_substeps==v.completed_substeps,
                 "POINTS1 late failure partially committed old puffs");
        }
        const auto result=a.driver.advance_hour_point_cadence(
            a.met,a.geo,a.ctl,a.pg,false,a.source);
        need(result.cadence.puff_count==n &&
             result.cadence.emission_duration_s==dt &&
             result.new_puffs==static_cast<std::size_t>(n) &&
             result.active_after==static_cast<std::size_t>((hour+1)*n) &&
             a.driver.completed_hours()==static_cast<std::size_t>(hour+1),
             "POINTS1 hourly admission count, dt or total states incorrect");
        const int base=hour*n;
        const std::size_t expected_steps=static_cast<std::size_t>(base)+
                             static_cast<std::size_t>(n*(n+1)/2);
        need(result.steps.size()==expected_steps,
             "POINTS1 j..NPUFFS substep count incorrect");
        int previous_id=0;
        for(const auto& rec:result.steps){
            need(rec.puff_id>=previous_id,
                 "POINTS1 deterministic release order changed");
            previous_id=rec.puff_id;
            need(rec.step.bookkeeping.mid_time_s==
                    (rec.original_release_number==0?1800.0:600.0),
                 "original SETPUF substep TMID not native REAL4 DT/2");
        }
        for(int j=1;j<=n;++j){
            const int id=base+j;
            const auto v=a.driver.vertical(id);
            const auto age=a.driver.motion(id).travel_time_s;
            need(age==dt*static_cast<float>(n-j+1) &&
                 v.completed_substeps==static_cast<std::size_t>(n-j+1) &&
                 v.committed_lid_steps==v.completed_substeps,
                 "new POINTS1 release J age does not honor NSSTR=IPNO");
            const float m1=v.mass_mixed.at(0)+v.mass_above.at(0);
            const float m2=v.mass_mixed.at(1)+v.mass_above.at(1);
            need(std::abs(m1-2400.0F)<0.05 &&
                 std::abs(m2-3600.0F)<0.05,
                 "INJECT per-puff Q*DT incorrect");
            total0+=m1;total1+=m2;
        }
    }
    need(total0==static_cast<double>(hours)*7200 &&
         total1==static_cast<double>(hours)*10800,
         "hourly POINTS1 release mass did not close at Q*DHR");
    need(a.driver.active_count()==static_cast<std::size_t>(hours*n),
         "POINTS1/COMP active puff count drift");
    std::cout<<"P7_NATIVE_POINT_HOURLY_CADENCE=PASS HOURS="<<hours
             <<" NPUFFS=3 DT=1200 NSSTR=J"
             <<" EMITTED_MASS=CONSERVATIVE"
             <<" GRISE=YES PG_SIGMA=YES VMASS=YES"
             <<" WHOLE_HOUR_ROLLBACK=YES"
             <<" EXTERNAL_WSNEW=REQUIRES_ORIGINAL_RLSMET"
             <<" ORIGINAL_143H_PUFF_CON=NOT_YET_VALIDATED\n";
}
}
int main(int argc,char** argv){
    try{
        if(argc!=2)throw std::invalid_argument("expected 1/6/143");
        if(std::string(argv[1])=="rlsmet"){native_release_wsnew();return 0;}
        const int hours=std::stoi(argv[1]);
        if(hours!=1 && hours!=6 && hours!=143)
            throw std::invalid_argument("invalid selected hour span");
        run(hours);return 0;
    }catch(const std::exception& e){
        std::cerr<<"P7_NATIVE_POINT_HOURLY_CADENCE=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
