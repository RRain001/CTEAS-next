#include "cteas/p6/p6g_observed_thermal_hour.hpp"
#include <chrono>
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <utility>

using namespace std::chrono;
using namespace cteas::calmet::p6g;

static void check(bool yes,const char* reason) {
    if(!yes)throw std::runtime_error(reason);
}
template<typename Fn>static void rejected(Fn f,const char* reason) {
    bool caught=false;
    try{(void)f();}catch(const std::invalid_argument&){caught=true;}
    check(caught,reason);
}
struct Fixture {
    StationSet deck;
    SurfaceSeries series;
    GeoGrid grid;
    G12ExplicitSolarHeat forcing;
    Fixture(){
        auto a=cteas::calmet::p6::DeckStation{};
        a.id=101;a.local_x_m=10000.f;a.local_y_m=10000.f;
        auto b=cteas::calmet::p6::DeckStation{};
        b.id=102;b.local_x_m=100000.f;b.local_y_m=100000.f;
        deck.surface={a,b};
        const auto start=sys_days{year{2023}/December/31}+hours{23};
        series.begin=start;series.end=start+hours{1};
        series.station_ids={101,102};
        SurfaceHour hour;
        hour.start=start;hour.end=series.end;
        hour.by_station.resize(2);
        hour.by_station[0].temperature_k=283.f;
        hour.by_station[0].temperature_valid=true;
        hour.by_station[0].humidity_pct=60;
        hour.by_station[0].humidity_valid=true;
        hour.by_station[0].cloud_valid=true;
        hour.by_station[0].opaque_cloud_tenths=3;
        hour.by_station[1].temperature_k=295.f;
        hour.by_station[1].temperature_valid=true;
        hour.by_station[1].humidity_pct=70;
        hour.by_station[1].humidity_valid=true;
        hour.by_station[1].cloud_valid=true;
        hour.by_station[1].opaque_cloud_tenths=7;
        series.hourly.push_back(hour);
        grid.nx=12;grid.ny=12;grid.grid_km=10.f;
        grid.iwat1=50;grid.iwat2=55;
        grid.terrain_m.assign(144,100.f);
        grid.landuse.assign(144,20);
        grid.landuse[0]=50;
        grid.albedo.assign(144,0.2f);
        grid.bowen.assign(144,0.5f);
        grid.hcg.assign(144,0.2f);
        grid.qf.assign(144,0.f);
        forcing.end=hour.end;
        forcing.synthetic_radiation_fixture=true;
        forcing.irad=1;forcing.numts=2;forcing.trad_grid=20.f;
        forcing.domain_temperature_k=285.f;
        forcing.critfn=10.f;
        forcing.coefficients=G12HeatCoefficients{
            950.f,0.f,-0.2f,1.f,0.f,0.f,1.f};
        forcing.sun_sine.assign(144,0.9f);
        forcing.nearest_surface.assign(144,1);
        for(int j=0;j<12;++j)for(int i=0;i<12;++i)
            forcing.nearest_surface[static_cast<std::size_t>(j*12+i)]=
                i<6?1:2;
        forcing.lapse_k_per_m.assign(144,0.002f);
        forcing.initial_water_qh_wm2.assign(144,0.f);
        forcing.initial_water_qh_wm2[0]=7.f;
    }
    G12ThermalResult compute()const {
        return source_selected_g12_thermal_hour(
            deck,series,series.hourly.front(),grid,forcing);
    }
};
int main(){
    try {
        Fixture f;
        const auto result=f.compute();
        check(result.thermal.end==f.series.end&&
              result.thermal.provenance==
                TerrainHourProvenance::ObservedSurfvarSyntheticSolarFixture,
              "G12 source-selected provenance or UTC hour mismatch");
        check(result.thermal.temperature_k.size()==144&&
              result.thermal.sensible_heat_w_m2.size()==144&&
              result.shortwave_wm2.size()==144,
              "G12 10km P6E gridded thermal field shapes incorrect");
        check(result.thermal.temperature_k[13]<
              result.thermal.temperature_k[130],
              "G12 SURFVAR does not respond to 2 different stations");
        check(result.thermal.sensible_heat_w_m2[0]==7.f,
              "G12 HEATFX must preserve preexisting water QH");
        check(result.thermal.sensible_heat_w_m2[1]>0.f,
              "G12 daylight HEATFX did not generate positive land QH");
        for(float q:result.thermal.sensible_heat_w_m2)
            check(std::isfinite(q),"G12 nonfinite source-computed QH");
        auto changed=f;
        changed.series.hourly[0].by_station[0].temperature_k=303.f;
        const auto warmer=changed.compute();
        check(warmer.thermal.temperature_k[13]>
              result.thermal.temperature_k[13],
              "G12 changed observed surface temperature did not propagate");
        changed=f;
        changed.forcing.sun_sine.assign(144,-0.2f);
        const auto night=changed.compute();
        check(night.thermal.sensible_heat_w_m2[1]==-0.1f,
              "G12 original HEATFX night branch not exercised");
        changed=f;changed.forcing.synthetic_radiation_fixture=false;
        rejected([&]{return changed.compute();},
                 "G12 missing test-solar provenance accepted");
        changed=f;changed.forcing.coefficients.reset();
        rejected([&]{return changed.compute();},
                 "G12 missing radiation coefficients accepted");
        changed=f;changed.forcing.sun_sine.pop_back();
        rejected([&]{return changed.compute();},
                 "G12 truncated gridded solar accepted");
        changed=f;changed.forcing.end+=hours{1};
        rejected([&]{return changed.compute();},
                 "G12 shifted UTC hour accepted");
        changed=f;std::swap(changed.series.station_ids[0],
                             changed.series.station_ids[1]);
        rejected([&]{return changed.compute();},
                 "G12 mismatched SURF station order accepted");
        changed=f;changed.series.hourly[0].by_station[1].cloud_valid=false;
        rejected([&]{return changed.compute();},
                 "G12 missing HEATFX cloud accepted");
        changed=f;changed.series.hourly[0].by_station[0].temperature_valid=false;
        changed.series.hourly[0].by_station[1].temperature_valid=false;
        rejected([&]{return changed.compute();},
                 "G12 fabricated all-missing observed temperatures");
        changed=f;changed.forcing.nearest_surface[0]=3;
        rejected([&]{return changed.compute();},
                 "G12 invented nearest surface station 3 of 2");
        changed=f;changed.forcing.lapse_k_per_m.pop_back();
        rejected([&]{return changed.compute();},
                 "G12 incomplete external GAMMA silently accepted");
        changed=f;changed.forcing.coefficients->hc3p1=0.f;
        rejected([&]{return changed.compute();},
                 "G12 zero HEATFX denominator accepted");
        std::cout<<"PASS_G12_MULTI_SURFVAR_OBSERVED_TEMP_HEATFX_EXPLICIT_SOLAR_10KM "
                 <<"temp_near_1="<<result.thermal.temperature_k[13]
                 <<" temp_near_2="<<result.thermal.temperature_k[130]
                 <<" land_day_QH="<<result.thermal.sensible_heat_w_m2[1]
                 <<" water_QH="<<result.thermal.sensible_heat_w_m2[0]<<"\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"FAIL_G12_P6E_SURFVAR_HEATFX "<<e.what()<<"\n";return 1;
    }
}
