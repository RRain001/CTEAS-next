// S4-R1a bounded water thermal bridge tests: controlled original-format
// source controls, no vendor output injection, no G14/G26 production route.
#include "cteas/p6/p6g_g39_selected_water_thermal_reference.hpp"
#include <chrono>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace p6g=cteas::calmet::p6g;
using namespace std::chrono;
static void check(bool ok,const char* msg) {
    if(!ok)throw std::runtime_error(msg);
}
template<class F> static void rejects(F&& f,const char* msg) {
    bool denied=false;
    try {f();} catch(const std::exception&) {denied=true;}
    check(denied,msg);
}
static p6g::G17B4SurfaceControls selected_control() {
    p6g::G17B4SurfaceControls x;
    x.source.irad=1;x.source.numts=2;x.source.iavet=1;
    x.source.itprog=0;x.source.irhprog=0;x.source.npsta=0;
    x.source.trad_km=80.f;
    x.mnmdav=3;x.hafang_deg=20.f;
    return x;
}
static p6g::GeoGrid grid() {
    p6g::GeoGrid x;
    x.nx=12;x.ny=12;x.zone=50;x.hemisphere='N';
    x.grid_km=10.f;x.xorigin_km=510.885f;x.yorigin_km=3531.269f;
    x.nlu=2;x.valid_categories={20,52};x.iwat1=50;x.iwat2=55;
    x.landuse.assign(144,20);
    x.landuse[0]=52;x.landuse[90]=52;
    x.terrain_m.assign(144,100.f);
    x.z0_m.assign(144,0.5f);
    x.albedo.assign(144,0.2f);
    x.bowen.assign(144,0.5f);
    x.hcg.assign(144,0.2f);
    x.qf.assign(144,0.f);
    x.lai.assign(144,1.5f);
    return x;
}
static p6g::StationSet stations() {
    p6g::StationSet set;
    cteas::calmet::p6::DeckStation a{};
    a.id=583140;a.local_x_m=15000.f;a.local_y_m=15000.f;
    cteas::calmet::p6::DeckStation b{};
    b.id=583210;b.local_x_m=95000.f;b.local_y_m=95000.f;
    set.surface={a,b};
    return set;
}
static p6g::SurfaceSeries surface() {
    p6g::SurfaceSeries series;
    series.begin=sys_days{year{2022}/June/1}+hours{1};
    series.end=series.begin+hours{1};
    series.station_ids={583140,583210};
    p6g::SurfaceHour hour;
    hour.start=series.begin;hour.end=series.end;
    hour.by_station.resize(2);
    auto& a=hour.by_station[0];
    a.wind_valid=true;a.wind_speed_mps=4.f;a.wind_direction_deg=90.f;
    a.pressure_valid=true;a.pressure_mb=1013.f;
    a.cloud_valid=true;a.opaque_cloud_tenths=2;
    a.temperature_valid=true;a.temperature_k=281.f;
    a.humidity_valid=true;a.humidity_pct=65;
    auto& b=hour.by_station[1];
    b.wind_valid=true;b.wind_speed_mps=7.f;b.wind_direction_deg=175.f;
    b.pressure_valid=true;b.pressure_mb=992.f;
    b.cloud_valid=true;b.opaque_cloud_tenths=7;
    b.temperature_valid=true;b.temperature_k=299.f;
    b.humidity_valid=true;b.humidity_pct=73;
    series.hourly.push_back(hour);
    return series;
}
static const std::string& selected_deck(){
    static const std::string value=
        "! NOWSTA = 0 !\n! ITWPROG = 0 !\n"
        "! ICOARE = 10 !\n! IMIXH = 1 !\n! NOOBS = 0 !\n"
        "! IAVET = 1 !\n! ISURFT = -1 !\n";
    return value;
}
int main(int argc,char** argv) {
    try {
        if(argc!=2||std::string(argv[1])!="--self-test")
            throw std::invalid_argument("S4-R1a test-only --self-test required");
        auto geo=grid();
        auto st=stations();
        auto obs=surface();
        auto orig=selected_control();
        const auto& hour=obs.hourly.front();
        rejects([&]{p6g::G17B4TwoPassSurfvar denied(
            geo,st,obs,hour,orig);(void)denied;},
            "G17B4 default accepted unverified water physics");
        p6g::G17B4TwoPassSurfvar twice(
            geo,st,obs,hour,orig,true);
        const auto n=static_cast<std::size_t>(geo.nx*geo.ny);
        std::vector<float> original_u(n*9,4.f),original_v(n*9,1.f);
        std::vector<float> post_u(n*9,6.f),post_v(n*9,2.f);
        twice.after_wind1_before_fradj(hour.end,original_u,original_v);
        twice.after_fradj_before_heatfx(hour.end,post_u,post_v);
        check(twice.first_ready()&&twice.second_ready(),
              "original source SURFVAR two passes not completed");
        const auto hflux=p6g::g38_selected_noow_water_hflux_source_only(
            geo,selected_deck(),true);
        rejects([&]{(void)p6g::selected_iavet1_heat_after_fradj(
            geo,st,hour,twice,hflux.reference_heat);},
            "G17C1 all-land default was bypassed");
        rejects([&]{(void)p6g::g39_original_noow_water_postfradj_thermal_reference(
            geo,st,hour,twice,{post_u,post_v},selected_deck(),20.f,false);},
            "G39 accepted implicit production");
        const auto out=p6g::g39_original_noow_water_postfradj_thermal_reference(
            geo,st,hour,twice,{post_u,post_v},selected_deck(),20.f,true);
        check(out.selected_original_water_cells==2 &&
              out.elustr.water_state_pending_original_WATER,
              "selected water categories not preserved through ELUSTR");
        check(!out.water_ustar_el_zi_ready&&!out.g22_g24_wind_ready&&
              !out.g14_g26_production_ready,
              "source-only water path incorrectly reports native readiness");
        check(out.heat.temperature_k==twice.final_temperature(),
              "G39 source temperature was not after second SURFVAR");
        check(out.heat.shortwave_wm2.size()==n&&out.elustr.qh_wm2.size()==n,
              "G39 thermal output field size");
        for(std::size_t i=0;i<n;++i) {
            check(std::isfinite(out.heat.shortwave_wm2[i])&&
                  std::isfinite(out.elustr.qh_wm2[i]),
                  "thermal field is nonfinite");
            if(geo.landuse[i]==52)
                check(out.heat.sensible_heat_wm2[i]==0.f&&
                      out.elustr.qh_wm2[i]==0.f&&
                      out.elustr.ustar_mps[i]==0.f&&
                      out.elustr.el_m[i]==0.f,
                      "original WATER must remain responsible for USTAR/EL");
            else
                check(std::isfinite(out.elustr.ustar_mps[i])&&
                      out.elustr.ustar_mps[i]>=0.05f&&
                      std::isfinite(out.elustr.el_m[i]),
                      "original land ELUSTR was not computed");
        }
        // No permissive fallback to stale or original-oracle wind fields.
        auto forged=post_u;forged[0]+=1.f;
        rejects([&]{(void)p6g::g39_original_noow_water_postfradj_thermal_reference(
            geo,st,hour,twice,{forged,post_v},selected_deck(),20.f,true);},
            "G39 accepted detached original first-plane wind");
        auto invalid=selected_deck()+"! HC1 = 0 !\n";
        rejects([&]{(void)p6g::g39_original_noow_water_postfradj_thermal_reference(
            geo,st,hour,twice,{post_u,post_v},invalid,20.f,true);},
            "G39 accepted HFLUX override");
        rejects([&]{(void)p6g::selected_iavet1_elustr_after_heatfx(
            geo,st,hour,twice,out.heat,{post_u,post_v},
            {0,20.f,true});},
            "G17C2 default ELUSTR failed to reject water");
        auto land=geo;land.landuse[0]=20;land.landuse[90]=20;
        rejects([&]{(void)p6g::g39_original_noow_water_postfradj_thermal_reference(
            land,st,hour,twice,{post_u,post_v},selected_deck(),20.f,true);},
            "G39 accepted all-land source as water");
        std::cout<<"S4R1A_SELECTED_WATER_SURFVAR_HEATFX_ELUSTR_GUARDS=PASS\n"
                 <<"S4R1A_VENDOR_63X6_THERMAL_NUMERIC=NOT_RUN\n"
                 <<"S4R1A_NATIVE_G24_WATER_WIND=NOT_RUN\n"
                 <<"S4R1A_G26_PRODUCTION=NOT_ACCEPTED\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"S4R1A_FAIL_CLOSED "<<e.what()<<"\n";
        return 2;
    }
}
