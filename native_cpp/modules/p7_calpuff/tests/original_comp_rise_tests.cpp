#include "cteas/puff/original_comp_rise.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {
using namespace cteas::puff;
void require(bool b,const char* msg) {
    if(!b)throw std::runtime_error(msg);
}
template<class F> void rejects(F&& f,const char* msg){
    bool threw=false;try{f();}catch(const std::exception&){threw=true;}
    require(threw,msg);
}
struct Fixture {
    OriginalCompRisePointDriver driver;
    OriginalMetHour hour;
    Calmet21Static statics;
    NeutralCompControls control;
    DispersionSetup pg;
    Fixture() {
        hour.nx=50;hour.ny=50;hour.nz=3;
        const auto n=50U*50U;
        hour.zi.assign(n,250.0F);
        hour.ipgt.assign(n,4);
        hour.u.assign(n*3,0.002F);
        hour.v.assign(n*3,0.0F);
        // Source-ordered RISEWIND samples the rise profile only while
        // XTOTB<XFINAL; after final rise, COMP uses ADVECT's puff layer.
        for(std::size_t k=n;k<2*n;++k)hour.u[k]=0.006F;
        for(std::size_t k=2*n;k<3*n;++k)hour.u[k]=0.010F;
        statics.cell_face_m={0,100,200,300};
        control.max_sampling_steps=1;
        // Synthetic tiny-wind PG lifecycle fixture only: explicitly keep these
        // 0.002-0.010 m/s winds NONCALM by choosing WSCALM=0.001.
        // The frozen Hefei puff.inp independently uses WSCALM=0.5.
        control.calm_threshold_ms=0.001F;
        pg.mdisp=3;
        pg.averaging_factor=1.0;
        pg.sigma_y_heffter_m=550;
        pg.heffter_sigma_z=false;
        pg.roughness_adjustment=false;
        NewPuffInputs source;
        source.source_x_km=5;
        source.source_y_km=5;
        source.stack_height_m=50;
        source.effective_height_m=160;
        source.x_final_m=230;
        source.buoyancy_flux=49;
        source.x_final_buoyancy_m=230;
        source.z_final_buoyancy_m=110;
        source.stack_wind_speed_ms=2;
        source.sigma_y_source_m=1;
        source.sigma_z_source_m=1;
        source.stability_class=4;
        InjectionInputs release;
        release.species_count=2;
        release.emission_duration_s=3600;
        release.effective_height_m=160;
        release.max_layer_height_m=300;
        release.mixing_height_m=250;
        release.mass_fraction_mixed=1;
        release.stability_class=4;
        release.gaussian_distribution=1;
        release.emission_rate={2,3};
        driver.admit(1,source,release);
        source.downwash_code=3;
        rejects([&]{driver.admit(2,source,release);},
                "unsupported PRIME source got admitted");
        require(driver.active_count()==1,
                "invalid source partially admitted");
    }
};
void scenario(int hours) {
    Fixture f;
    const auto initial=f.driver.vertical(1);
    const auto sum=[](const NativeVerticalPuffState& s,std::size_t i){
        return s.mass_mixed.at(i)+s.mass_above.at(i);
    };
    bool saw_final=false;
    bool saw_gradual=false;
    for(int i=0;i<hours;++i) {
        const auto old=f.driver.motion(1);
        const auto result=f.driver.step_pg_rise(
            1,f.hour,f.statics,f.control,f.pg,false);
        const auto state=f.driver.vertical(1);
        require(result.bookkeeping.mid_time_s==1800 &&
                result.after.travel_time_s==static_cast<float>((i+1)*3600) &&
                state.completed_substeps==static_cast<std::size_t>(i+1) &&
                state.committed_lid_steps==static_cast<std::size_t>(i+1) &&
                // Vendor COMP L10505–10519 calls RISEWIND only while rising.
                // Once XTOTB>=XFINAL the original uses ADVECT directly.
                result.rise.adjusted.passes==
                    (old.total_distance_m<230.0F ? 2 : 0) &&
                result.after.x_cells>old.x_cells &&
                result.after.y_cells==old.y_cells &&
                result.after.total_distance_m>old.total_distance_m &&
                result.after.z_m==result.final_height_m,
                "rising native COMP failed ordered real-state step");
        require(result.bookkeeping.distance_begin_m==old.total_distance_m &&
                result.bookkeeping.mid_distance_km>0,
                "rising SETPUF used accumulated distance as midpoint");
        for(std::size_t k=0;k<2;++k) {
            const float mass=sum(state,k);
            require(std::isfinite(mass) &&
                    std::abs(mass-sum(initial,k)) <= 1.0e-5F*sum(initial,k),
                    "native RISEWIND changed tracer mass");
        }
        if(result.before.total_distance_m<230.0F){
            saw_gradual=true;
            require(result.rise.initial_rise.height_m>=50 &&
                    result.rise.initial_rise.height_m<=160,
                    "GRISE initial transitional height not plausible");
        }
        if(result.before.total_distance_m>=230.0F){
            saw_final=true;
            require(result.final_height_m==160.0F,
                    "GRISE did not preserve final effective height");
        }
        if(i==1){
            const auto prev_m=f.driver.motion(1);
            const auto prev_v=f.driver.vertical(1);
            auto bad=f.pg;
            bad.mdisp=17;
            rejects([&]{(void)f.driver.step_pg_rise(
                 1,f.hour,f.statics,f.control,bad,false);},
                 "bad PG option accepted");
            require(f.driver.motion(1).travel_time_s==prev_m.travel_time_s &&
                    f.driver.vertical(1).completed_substeps==prev_v.completed_substeps &&
                    f.driver.steps(1)==2,
                    "failed rising COMP step partially mutated state");
        }
    }
    require(saw_gradual && (hours<143 || saw_final),
            "no gradual-to-final plume-rise lifecycle witnessed");
    require(f.driver.steps(1)==static_cast<std::size_t>(hours),
            "missing rising COMP steps");
    f.driver.retire(1);
    require(f.driver.active_count()==0,
            "rising native puff retirement leaked state");
    std::cout<<"P7_NATIVE_COMP_GRISE_RISEWIND_PG=PASS HOURS="<<hours
             <<" METFM1=YES SIGTY_SIGTZ=YES VMASS_COMP=YES"
             <<" GRADUAL_RISE=YES"
             <<" FINAL_RISE_SEEN="<<(saw_final?"YES":"NO")
             <<" DGM_AS_NATIVE_INPUT=NO"
             <<" ORIGINAL_HEFEI_NUMERICAL_EQUIVALENCE=NOT_YET_VALIDATED\n";
}
}
int main(int argc,char** argv){
    try{
        if(argc!=2)throw std::invalid_argument("expected [1|6|143]");
        const int hours=std::stoi(argv[1]);
        if(hours!=1 && hours!=6 && hours!=143)
            throw std::invalid_argument("test hours outside matrix");
        scenario(hours);
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P7_NATIVE_COMP_GRISE_RISEWIND_PG=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
