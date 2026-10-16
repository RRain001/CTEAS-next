#include "cteas/puff/original_rise_met.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {
using namespace cteas::puff;
void require(bool v,const char* msg) {
    if(!v)throw std::runtime_error(msg);
}
template<class F> void rejects(F&& f,const char* msg) {
    bool t=false;try{f();}catch(const std::exception&){t=true;}
    require(t,msg);
}
struct Case {
    OriginalMetHour hour;
    Calmet21Static statics;
    OriginalRiseMetInputs data;
    Case() {
        hour.nx=4;hour.ny=4;hour.nz=3;
        const auto n=16U;
        hour.u.assign(n*3,2.0F);
        hour.v.assign(n*3,1.0F);
        hour.zi.assign(n,150.0F);
        hour.ipgt.assign(n,4);
        statics.cell_face_m={0.0F,100.0F,200.0F,300.0F};
        data.x_cells=1.5F;data.y_cells=1.5F;
        data.start_distance_m=100.0F;
        data.final_distance_m=500.0F;
        data.step_seconds=15.0F;
        data.rise_half_depth_m=10.0F;
        data.plume.source_type=1;
        data.plume.downwash_code=0;
        data.plume.met_period=1;
        data.plume.rise_method=1;
        data.plume.shear_flag=0;
        data.plume.stack_height_m=100.0;
        data.plume.final_rise_m=220.0;
        data.plume.full_final_rise_m=120.0;
        data.plume.stability_class=4;
        data.plume.buoyancy_flux=30.0;
        data.plume.stack_wind_speed_ms=2.0;
        data.plume.x_final_buoyancy_m=500.0;
        data.plume.z_final_buoyancy_m=120.0;
    }
};
void check_constant() {
    Case t;
    const auto a=original_rise_wind_met(t.hour,t.statics,t.data);
    require(a.cell.ix_1based==2 && a.cell.iy_1based==2,
            "native RISEWIND selected incorrect CALMET original grid");
    require(a.adjusted.passes==2,"native RISEWIND pass count differs");
    require(a.adjusted.u_ms==2.0 && a.adjusted.v_ms==1.0 &&
            a.final_rise_wind.u_ms==2.0 && a.final_rise_wind.v_ms==1.0,
            "native RISEWIND changed an exactly constant vertical wind");
    require(a.initial_rise.height_m>100.0 &&
            a.initial_rise.height_m<220.0,
            "native GRISE did not evaluate true transitional plume height");
    // Past XFINAL the original interpolated transition is entirely final.
    t.data.start_distance_m=650.0F;
    const auto final=original_rise_wind_met(t.hour,t.statics,t.data);
    require(final.adjusted.u_ms==2.0 && final.adjusted.v_ms==1.0,
            "post-final rise wind drifted from the original MET profile");
}
void check_shear() {
    Case t;
    for(std::size_t i=16;i<32;++i) {t.hour.u[i]=4.0F;t.hour.v[i]=2.0F;}
    for(std::size_t i=32;i<48;++i) {t.hour.u[i]=6.0F;t.hour.v[i]=3.0F;}
    const auto a=original_rise_wind_met(t.hour,t.statics,t.data);
    require(std::isfinite(a.adjusted.u_ms) &&
            a.adjusted.wind_speed_ms>0.0 &&
            a.adjusted.passes==2,
            "native GRiSE/RISEWIND with original layer shear not finite");
    require(a.adjusted.u_ms<a.final_rise_wind.u_ms,
            "gradual rise failed to select lower-layer U profile");
    auto bad=t.data;
    bad.plume.shear_flag=1;
    rejects([&]{(void)original_rise_wind_met(t.hour,t.statics,bad);},
            "MSHEAR=1 was silently approximated");
    bad=t.data;bad.plume.downwash_code=3;
    rejects([&]{(void)original_rise_wind_met(t.hour,t.statics,bad);},
            "PRIME unsupported source silently accepted");
    bad=t.data;bad.x_cells=4.0F;
    rejects([&]{(void)original_rise_wind_met(t.hour,t.statics,bad);},
            "off-grid puff silently sampled");
    bad=t.data;bad.step_seconds=0.0F;
    rejects([&]{(void)original_rise_wind_met(t.hour,t.statics,bad);},
            "invalid plume wind iteration step accepted");
    t.hour.u.clear();
    rejects([&]{(void)original_rise_wind_met(t.hour,t.statics,t.data);},
            "incomplete original CALMET profile silently accepted");
}
}
int main() {
    try {
        check_constant();
        check_shear();
        std::cout<<"P7_NATIVE_METFM1_GRISE_RISEWIND=PASS"
                 <<" VENDOR_KERNELS=REUSED"
                 <<" REAL4_MET_PROFILE=YES"
                 <<" SHEAR_PROFILE=TESTED"
                 <<" WHOLE_COMP_143H=NOT_YET_VALIDATED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"P7_NATIVE_METFM1_GRISE_RISEWIND=FAIL "
                 <<e.what()<<"\n";
        return 1;
    }
}
