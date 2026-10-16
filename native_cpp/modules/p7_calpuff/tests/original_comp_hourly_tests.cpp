#include "cteas/puff/original_comp_hourly.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
using namespace cteas::puff;
void check(bool v,const char* why) {
    if(!v)throw std::runtime_error(why);
}
template<class F> void reject(F&& f,const char* msg) {
    bool caught=false;try{f();}catch(const std::exception&){caught=true;}
    check(caught,msg);
}
HourlyPointAdmission source(int id,double x) {
    HourlyPointAdmission s;
    s.puff_id=id;
    s.point.source_x_km=x;
    s.point.source_y_km=5.0;
    s.point.sigma_y_source_m=1.0;
    s.point.sigma_z_source_m=1.0;
    s.point.effective_height_m=50.0;
    s.point.stability_class=4;
    s.mass.species_count=2;
    s.mass.emission_duration_s=3600.0;
    s.mass.effective_height_m=50.0;
    s.mass.max_layer_height_m=200.0;
    s.mass.mixing_height_m=100.0;
    s.mass.mass_fraction_mixed=1.0;
    s.mass.stability_class=4;
    s.mass.gaussian_distribution=1;
    s.mass.emission_rate={2.0,3.0};
    return s;
}
void test(int hours) {
    OriginalCompMultiPuffHours scheduler;
    OriginalMetHour met;
    met.nx=100;met.ny=100;met.nz=2;
    constexpr std::size_t grid=100*100;
    met.zi.assign(grid,100.0F);
    met.ipgt.assign(grid,4);
    met.u.assign(grid*2,0.002F);
    met.v.assign(grid*2,0.0F);
    Calmet21Static statics;
    statics.cell_face_m={0,100,200};
    NeutralCompControls ctl;
    ctl.max_sampling_steps=1;
    DispersionSetup pg;
    pg.mdisp=3;
    pg.averaging_factor=1.0;
    pg.sigma_y_heffter_m=550.0;
    pg.heffter_sigma_z=false;
    pg.roughness_adjustment=false;
    const auto total=[](const NativeVerticalPuffState& s,std::size_t species) {
        return s.mass_mixed.at(species)+s.mass_above.at(species);
    };
    for(int hour=0;hour<hours;++hour) {
        std::vector<HourlyPointAdmission> newp;
        if(hour==0)newp.push_back(source(1,5.0));
        if(hour==6)newp.push_back(source(2,6.0));
        if(hour==70)newp.push_back(source(3,7.0));
        const auto before_steps=hour==0?0U:scheduler.puff_steps(1);
        if(hour==2) {
            // The later, newly admitted puff is out-of-grid. The first
            // puff would have moved, but the whole 2-puff hour rolls back.
            auto invalid=source(2,100.5);
            const auto before=scheduler.motion(1);
            const auto prior_vertical=scheduler.vertical(1);
            reject([&]{
                (void)scheduler.advance_hour_pg(
                    met,statics,ctl,pg,false,{invalid});
            },"late second-puff failure incorrectly committed the hour");
            check(scheduler.completed_hours()==2 &&
                  scheduler.active_count()==1 &&
                  scheduler.motion(1).travel_time_s==before.travel_time_s &&
                  scheduler.motion(1).x_cells==before.x_cells &&
                  scheduler.vertical(1).completed_substeps==
                     prior_vertical.completed_substeps &&
                  scheduler.puff_steps(1)==before_steps,
                  "group rollback partially updated the first native puff");
            reject([&]{(void)scheduler.motion(2);},
                   "failed attempted admission left an orphan puff");
        }
        auto result=scheduler.advance_hour_pg(
            met,statics,ctl,pg,false,newp);
        const std::size_t n=hour<6?1U:hour<70?2U:3U;
        check(result.hour_index==static_cast<std::size_t>(hour) &&
              result.steps.size()==n &&
              result.active_after==n &&
              scheduler.active_count()==n &&
              scheduler.completed_hours()==static_cast<std::size_t>(hour+1),
              "native multi-puff hour accounting incorrect");
        int prev=0;
        for(const auto& rec:result.steps) {
            check(rec.puff_id>prev,"noncanonical original puff ordering");
            prev=rec.puff_id;
            const int admission=rec.puff_id==1?0:rec.puff_id==2?6:70;
            check(rec.state.after.travel_time_s==
                      float((hour-admission+1)*3600) &&
                  rec.state.vertical_after.completed_substeps==
                     std::size_t(hour-admission+1) &&
                  rec.state.vertical_after.committed_lid_steps==
                     rec.state.vertical_after.completed_substeps,
                  "multi-puff PG age/sigma/lid step continuity broken");
            const auto v=scheduler.vertical(rec.puff_id);
            for(std::size_t sp=0;sp<2;++sp) {
                const float expected=sp==0?7200.0F:10800.0F;
                check(std::abs(total(v,sp)-expected)<=0.00001F*expected,
                      "native multi-puff species mass drifted");
            }
        }
    }
    check(scheduler.canonical_ids().size()==
         scheduler.active_count(),"retirement list corrupt");
    if(hours>6) {
        scheduler.retire(2);
        check(scheduler.active_count()==(hours>70?2U:1U),
              "native puff retirement incorrectly deleted unrelated puffs");
        reject([&]{(void)scheduler.puff_steps(2);},
               "retired puff still in solver");
    }
    std::cout<<"P7_NATIVE_COMP_PG_MULTIPUFF=PASS HOURS="<<hours
             <<" DISTINCT_RELEASE_HOURS=0,6,70"
             <<" CANONICAL_ORDER=YES"
             <<" SOURCE_MASS=CONSERVED"
             <<" COMPLETE_HOUR_ROLLBACK=YES"
             <<" ORIGINAL_POINT1_ADMISSION_ORDER=NOT_YET_VALIDATED"
             <<" FROZEN_2022_CASE=NOT_YET_VALIDATED\n";
}
}
int main(int argc,char** argv) {
    try{
       if(argc!=2)throw std::invalid_argument("usage: multi-puff [1|6|143]");
       const int hours=std::stoi(argv[1]);
       if(hours!=1&&hours!=6&&hours!=143)
           throw std::invalid_argument("hours outside selected test matrix");
       test(hours);
       return 0;
    }catch(const std::exception& e) {
       std::cerr<<"P7_NATIVE_COMP_PG_MULTIPUFF=FAIL "<<e.what()<<"\n";
       return 1;
    }
}
