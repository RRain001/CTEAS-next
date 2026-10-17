// Integration-boundary test: real native COMP kernels run in the shared
// single-pass clock; DIAGNO stages below are explicitly a TEST FIXTURE.
// No original-CALMET scientific parity or independent MET.DAT is claimed.
#include "cteas/p6e/native_hourly_comp_steps.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace cteas::calmet::p6;

static void need(bool cond,const char* why){
    if(!cond)throw std::runtime_error(why);
}

struct SelectedCompOnlyFixture final : NativeHourPhysics {
    NativeCompHourControls c;
    float last_committed_ziconv=0.f;
    std::size_t observed_hours=0;
    SelectedCompOnlyFixture(){
        constexpr std::size_t n=2500;
        c.station_cell=0;
        auto& m=c.mixing;
        m.nx=50;m.ny=50;m.imixh=1;
        m.sounding[0]={cteas::p6e::MixdtSounding{
            {0.f,100.f,500.f,1500.f,3000.f},
            {295.f,294.f,290.f,282.f,270.f}}};
        m.sounding[1]=m.sounding[0];
        m.justa={1};
        m.nearu.assign(n,1);
        m.landuse.assign(n,10);
        m.rho.assign(n,1.2f);
        m.cmech.assign(n,150.f);
        m.fcori.assign(n,1.e-4f);
        c.averaging.nx=50;c.averaging.ny=50;
        c.averaging.mnmdav=0;c.averaging.dgrid_m=100.f;
        c.averaging.hafang_deg=30.f;
        c.convective_scale.nx=50;c.convective_scale.ny=50;
        c.convective_scale.landuse=m.landuse;
        c.convective_scale.temp_k.assign(n,285.f);
        c.convective_scale.rho_kgm3.assign(n,1.2f);
        c.convective_scale.initial_wstar_ms.assign(n,0.f);
        auto& t=c.temperature;
        t.nx=50;t.ny=50;t.nz=9;
        t.dgrid_m=100.f;
        t.face_z_m={0.f,20.f,40.f,80.f,160.f,320.f,640.f,
                    1200.f,2000.f,3000.f};
        t.station_x_m={2500.f};t.station_y_m={2500.f};
        t.justa={1};
        t.aa_face_temp_k={285.f,285.f,284.5f,284.f,283.f,282.f,280.f,
                          277.f,273.f,269.f};
        t.bb_face_temp_k=t.aa_face_temp_k;
        t.surface_temp_k.assign(n,285.f);
        t.past_seconds={3600};t.to_go_seconds={39600};
    }
    NativeHourStageResult run(NativeHourStage stage,NativeHourFrame& frame) override{
        const std::size_t hour=frame.input.hour_index;
        if(stage==NativeHourStage::PrepdiPreviousZiconv){
            need(frame.previous.ziconv_m[0]==last_committed_ziconv,
                 "PREPDI used future-hour ZICONV");
            ++observed_hours;
        }
        if(stage==NativeHourStage::DiagnoWind1) {
            frame.fields.u_mps.assign(22500,0.f);
            frame.fields.v_mps.assign(22500,0.f);
            frame.fields.w_face_mps.assign(25000,0.f);
            frame.fields.qh_wm2.assign(2500,100.f);
            frame.fields.ustar_mps.assign(2500,0.3f);
            frame.fields.el_m.assign(2500,-100.f);
        }
        if(stage==NativeHourStage::DiagnoStheorElustr2Mixhtst){
            // Test-only upstream state mutation; in the actual adapter this
            // must be the REAL STHEOR→ELUSTR2→MIXHTST native result.
            frame.next.dptt_k[c.station_cell]=0.125f+static_cast<float>(hour);
        }
        if(stage==NativeHourStage::CompGridMixht){
            const auto previous_other=frame.previous.dptt_k[1];
            const auto current_station=frame.next.dptt_k[c.station_cell];
            const auto result=native_comp_dispatch(stage,frame,c);
            need(result.completed &&
                 result.source==NativeHourSource::NativeCpp,
                 "native MIXHT dispatch missing");
            need(c.mixing.initial_dptt[c.station_cell]==current_station,
                 "COMP ignored DIAGNO same-hour /TJMP/ DPTT");
            need(c.mixing.initial_dptt[1]==previous_other,
                 "COMP replaced nonstation DPTT with same-hour values");
            need(c.mixing.initial_ziconv[c.station_cell]==last_committed_ziconv,
                 "COMP MIXHT consumed current-hour ZICONV");
            return result;
        }
        if(stage==NativeHourStage::CompAvemix||
           stage==NativeHourStage::CompWstarr||
           stage==NativeHourStage::CompTemp3d){
            auto result=native_comp_dispatch(stage,frame,c);
            if(stage==NativeHourStage::CompTemp3d){
                need(frame.fields.temperature_k.size()==22500,
                     "TEMP3D did not produce 9 full native levels");
                need(frame.fields.wstar_mps.size()==2500,
                     "WSTARR did not produce one grid");
                need(frame.next.ziconv_m.size()==2500,
                     "MIXHT→AVEMIX did not preserve ZICONV");
                last_committed_ziconv=frame.next.ziconv_m[c.station_cell];
            }
            return result;
        }
        // ALL other stages are FIXTURE STUBS; the scientific solver must
        // replace these with actual DIAGNO/PREPDI kernels before G2 PASS.
        return {NativeHourSource::NativeCpp,true};
    }
};
int main(){
    try{
        SelectedCompOnlyFixture f;
        P6SinglePassHourlyScheduler clock(50,50,9);
        for(std::size_t h=0;h<6;++h){
            clock.advance({h,1,"synthetic-case-hour"},f);
            need(clock.committed_memory().ziconv_m[0]==f.last_committed_ziconv,
                 "COMP output was not committed before the next DIAGNO");
        }
        need(clock.completed_hours()==6 && f.observed_hours==6,
             "six-hour single-pass COMP contract incomplete");
        std::cout<<"PASS_P6E_NATIVE_COMP_IN_SINGLE_PASS_CLOCK: "
                 <<"6 ordered hours actual MIXHT→AVEMIX→WSTARR→TEMP3D; "
                 <<"DIAGNO=TEST_FIXTURE; FULL_G2_G3_G4=NOT_PASS\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"FAIL_P6E_NATIVE_COMP_INTEGRATION: "<<e.what()<<'\n';
        return 1;
    }
}
