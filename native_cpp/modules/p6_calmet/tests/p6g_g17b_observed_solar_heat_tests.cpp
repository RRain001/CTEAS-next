// G17B1: source-computed 2SS TEMP2D and solar with native HEATFX,
// no externally manufactured sunshine; P6E ancillary values remain
// explicit TEST fixtures, not accepted CALMET physics/production.
#include "cteas/p6/p6g_g17b_observed_solar_heat.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <exception>
#include <fstream>
#include <iterator>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace p6=cteas::calmet::p6;
namespace p6g=cteas::calmet::p6g;
using namespace std::chrono;
static void check(bool condition,const char* why) {
    if(!condition)throw std::runtime_error(why);
}
template<class F> static void reject(F&& call,const char* why) {
    bool fails=false;
    try{call();}catch(const std::exception&){fails=true;}
    check(fails,why);
}
static p6::DeckStation station(int id,float x,float y) {
    p6::DeckStation s{};
    s.id=id;s.local_x_m=x;s.local_y_m=y;return s;
}
struct Fixture {
    p6g::GeoGrid geo;
    p6g::StationSet deck;
    p6g::SurfaceSeries surface;
    p6g::G17BExplicitAncillaryFixture anc;
    explicit Fixture(sys_seconds start) {
        geo.nx=12;geo.ny=12;geo.grid_km=10.f;
        geo.zone=50;geo.hemisphere='N';
        geo.xorigin_km=510.885f;geo.yorigin_km=3531.269f;
        geo.iwat1=50;geo.iwat2=55;
        geo.landuse.assign(144,20);geo.landuse[0]=50;
        for(int j=0;j<12;++j)for(int i=0;i<12;++i)
            geo.terrain_m.push_back(100.f+60.f*i+35.f*j);
        geo.albedo.assign(144,0.2f);
        geo.bowen.assign(144,0.5f);
        geo.hcg.assign(144,0.2f);
        geo.qf.assign(144,0.f);
        deck.surface={station(58321,10000.f,10000.f),
                      station(58322,100000.f,100000.f)};
        surface.station_ids={58321,58322};
        surface.begin=start;surface.end=start+hours{1};
        p6g::SurfaceHour h;
        h.start=start;h.end=surface.end;
        h.by_station.resize(2);
        h.by_station[0].wind_valid=true;
        h.by_station[0].wind_speed_mps=5.f;
        h.by_station[0].pressure_mb=1013.f;
        h.by_station[0].pressure_valid=true;
        h.by_station[0].temperature_k=281.f;
        h.by_station[0].temperature_valid=true;
        h.by_station[0].humidity_pct=60;
        h.by_station[0].humidity_valid=true;
        h.by_station[0].cloud_valid=true;
        h.by_station[0].opaque_cloud_tenths=2;
        h.by_station[1].wind_valid=true;
        h.by_station[1].wind_speed_mps=5.f;
        h.by_station[1].pressure_mb=997.f;
        h.by_station[1].pressure_valid=true;
        h.by_station[1].temperature_k=302.f;
        h.by_station[1].temperature_valid=true;
        h.by_station[1].humidity_pct=73;
        h.by_station[1].humidity_valid=true;
        h.by_station[1].cloud_valid=true;
        h.by_station[1].opaque_cloud_tenths=7;
        surface.hourly.push_back(h);
        anc.explicitly_test_only=true;
        anc.irad=1;anc.numts=2;anc.trad_grid=20.f;
        anc.isurft=-1;anc.domain_temperature_k=285.f;anc.critfn=10.f;
        anc.coefficients={990.f,-30.f,-0.75f,3.4f,0.f,0.f,1.f};
        // Only an independent comparison oracle: the source-calculated
        // SETCOM NEARS grid, NOT a physical input to G17B HEATFX/AIRDEN.
        anc.nearest_surface=p6g::source_setcom_nears(geo,deck);
        anc.initial_water_qh_wm2.assign(144,0.f);
        anc.initial_water_qh_wm2[0]=7.f;
        anc.lapse_k_per_m.assign(144,0.002f);
    }
    p6g::G17BObservedSolarResult calculate()const{
        return p6g::observed_solar_heat_selected(
            geo,deck,surface,surface.hourly.front(),anc);
    }
};
static void verify_real_solar(const Fixture& f) {
    const auto r=f.calculate();
    check(r.end==f.surface.end &&
          r.nearest_surface.size()==144&&
          r.density_kg_m3.size()==144&&
          r.nearest_surface==p6g::source_setcom_nears(f.geo,f.deck)&&
          r.sun_sine.size()==144&&r.observed.temp2d_k.size()==144&&
          r.sensible_heat_wm2.size()==144,"G17B source array geometry");
    check(r.fradj_fixture.temperature_k==r.slope_fixture.temperature_k &&
          r.fradj_fixture.temperature_k==r.observed.temp2d_k,
          "G17B actual SURFVAR TEMP2D differs between FRADJ and SLOPE");
    check(r.fradj_fixture.provenance==
              p6g::TerrainHourProvenance::SyntheticReferenceFixture &&
          r.slope_fixture.provenance==
              p6g::TerrainHourProvenance::SyntheticReferenceFixture,
          "G17B incorrectly promoted unaccepted ancillaries to production");

    // Independent direct SURFVAR invocation, same immutable source kernel.
    cteas::p6e::SurfvarMultistationInput si;
    si.nx=12;si.ny=12;si.dgrid_m=10000.f;
    si.irad=1;si.numts=2;si.trad_grid=20.f;
    si.stations={{10000.f,10000.f,281.f,60},
                 {100000.f,100000.f,302.f,73}};
    const auto observed=cteas::p6e::surfvar_multistation(si);
    check(observed.temp2d_k==r.observed.temp2d_k&&
          observed.rh2d_pct==r.observed.rh2d_pct,
          "G17B SURFVAR station source numerical mismatch");
    for(std::size_t cell=0;cell<144;++cell) {
        const auto k=static_cast<std::size_t>(r.nearest_surface[cell]-1);
        const float pressure=f.surface.hourly.front().by_station[k].pressure_mb;
        const float source_rho=0.3484321f*pressure/r.observed.temp2d_k[cell];
        check(r.density_kg_m3[cell]==source_rho,
              "G17B AIRDEN differs from original source pressure/TEMP2D");
    }
    check(r.observed.temp2d_k[13]<r.observed.temp2d_k[130],
          "G17B does not honor two distinct surface stations");

    // Source SOLAR computes the grid and the BEGIN-HOUR mid-interval slot;
    // external fabricated solar forcing is not an input to G17B.
    const auto coords=cteas::p6e::surface_solar_grid(
        12,12,50,f.geo.xorigin_km*1000.f,
        f.geo.yorigin_km*1000.f,10000.f);
    const auto day=floor<days>(f.surface.begin);
    const auto yr=sys_days{year_month_day{day}.year()/January/1};
    const int julian=static_cast<int>((day-yr).count())+1;
    const int hour=static_cast<int>(
        duration_cast<hours>(f.surface.begin-day).count());
    const auto solar=cteas::p6e::sinalpc_grid(coords,julian,hour,0);
    check(solar==r.sun_sine,"G17B original SOLAR midhour slot mismatch");
    for(float v:r.sun_sine)check(std::isfinite(v)&&v>=-1.f&&v<=1.f,
                               "G17B solar physical range");

    // HEATFX uses the REAL source-calculated solar and SURFVAR, explicit
    // unaccepted ancillary inputs, original MCLOUD=1 station-nearest branch.
    cteas::p6e::HeatFluxInput hi;
    hi.nx=12;hi.ny=12;
    hi.mcloud=1;hi.water_first=50;hi.water_last=55;
    hi.ha1=990.f;hi.ha2=-30.f;hi.hb1=-0.75f;hi.hb2=3.4f;
    hi.hc1=0.f;hi.hc2=0.f;hi.hc3p1=1.f;
    hi.station_cloud={2,7};hi.nearest=f.anc.nearest_surface;
    hi.landuse=f.geo.landuse;hi.sun=solar;
    hi.temp_k=observed.temp2d_k;
    hi.cloud_grid.assign(144,0.f);
    hi.albedo=f.geo.albedo;hi.bowen=f.geo.bowen;
    hi.soil_heat_fraction=f.geo.hcg;
    hi.anthropogenic_wm2=f.geo.qf;
    hi.initial_qh=f.anc.initial_water_qh_wm2;
    const auto direct=cteas::p6e::heatfx(hi);
    check(direct.shortwave_wm2==r.shortwave_wm2&&
          direct.sensible_wm2==r.sensible_heat_wm2,
          "G17B HEATFX differs from original selected kernel");
    check(r.sensible_heat_wm2[0]==7.f,
          "G17B source HEATFX did not preserve water QH");
    for(float v:r.sensible_heat_wm2)
        check(std::isfinite(v),"G17B nonfinite source HEATFX flux");
}
static void verify_selected_slope_bridge(
    const Fixture& f,const p6g::OriginalWindControls& controls) {
    const auto result=f.calculate();
    const auto terrain=p6g::prepare_g11_terrain(f.geo,35.f);
    p6g::G16ObservedProfiles profiles;
    profiles.end=f.surface.end;
    profiles.station_ids={58321,58322,58424,58425};
    for(int k=0;k<9;++k) {
        const std::vector<float> u{3.f,-3.f,8.f,9.f};
        const std::vector<float> v{4.f,4.f,-2.f,10.f};
        profiles.wind1_u_mps.insert(
            profiles.wind1_u_mps.end(),u.begin(),u.end());
        profiles.wind1_v_mps.insert(
            profiles.wind1_v_mps.end(),v.begin(),v.end());
    }
    profiles.wind1_present.assign(36,1);
    profiles.inter2_u_mps=profiles.wind1_u_mps;
    profiles.inter2_v_mps=profiles.wind1_v_mps;
    profiles.inter2_present=profiles.wind1_present;
    for(std::size_t k=4;k<9;++k){
        profiles.inter2_present[k*4]=0;
        profiles.inter2_u_mps[k*4]=999.f;
        profiles.inter2_v_mps[k*4]=999.f;
    }
    p6g::InputHour slot{};
    slot.end=result.end;slot.upper.resize(2);
    std::vector<p6g::UpperSeries> upper(2);
    upper[0].station_id=58424;upper[1].station_id=58425;
    p6g::StationSet all=f.deck;
    all.upper={station(58424,20000.f,20000.f),
               station(58425,50000.f,50000.f)};
    p6::NativeGridMemory previous;
    previous.zi_m.assign(144,0.f);
    previous.ziconv_m.assign(144,0.f);
    previous.dptt_k.assign(144,0.f);
    const auto& surface=f.surface.hourly.front();
    p6g::MultiHourFrame frame{0,f.geo,all,surface,slot,upper,
                             &controls,previous,previous,{}};
    p6g::G17SelectedTerrainFixturePhysics stages(
        profiles,terrain,result.fradj_fixture);
    const auto wind=stages.run(p6::NativeHourStage::DiagnoWind1,frame);
    check(wind.completed&&wind.source==p6::NativeHourSource::NativeCpp,
          "G17B computed source hour failed to reach WIND1");
    const auto& first=stages.wind_stages().first_guess;
    p6::WindUV original{first.u_mps,first.v_mps};
    const auto fradj=stages.run(p6::NativeHourStage::DiagnoFradj,frame);
    check(fradj.completed,"G17B observed SURFVAR TEMP2D failed FRADJ");
    check(!stages.run(p6::NativeHourStage::DiagnoHeatfx,frame).completed,
          "G17B falsely approved complete native P6E HEATFX controls");
    check(!stages.run(p6::NativeHourStage::DiagnoAirden,frame).completed,
          "G17B accepted AIRDEN before original observed-temperature handoff");
    auto incorrect_temp=result.observed.temp2d_k;
    incorrect_temp[0]+=1.f;
    reject([&]{
        stages.prepare_selected_airden(frame,incorrect_temp);
    },"G17B accepted AIRDEN temperature differing from source SURFVAR/FRADJ");
    stages.prepare_selected_airden(frame,result.observed.temp2d_k);
    const auto air=stages.run(p6::NativeHourStage::DiagnoAirden,frame);
    check(air.completed&&air.source==p6::NativeHourSource::NativeCpp&&
          stages.selected_air_density()==result.density_kg_m3,
          "G17B source SETCOM/RDSN AIRDEN did not reach native stage");
    reject([&]{
        stages.prepare_selected_airden(frame,result.observed.temp2d_k);
    },"G17B accepted duplicate AIRDEN source handoff");
    stages.provide_slope_heat(result.slope_fixture);
    const auto slope=stages.run(p6::NativeHourStage::DiagnoSlope,frame);
    check(slope.completed,"G17B computed solar HEATFX QH did not enter SLOPE");

    // The same source-observed TEMP2D and source-computed solar QH must give
    // EXACTLY the G11 combined physical kernel field, not only finite values.
    p6g::TerrainHourG11 model_hour;
    model_hour.end=result.end;
    model_hour.provenance=p6g::TerrainHourProvenance::SyntheticReferenceFixture;
    model_hour.isurft=-1;
    model_hour.domain_temperature_k=result.fradj_fixture.domain_temperature_k;
    model_hour.critfn=result.fradj_fixture.critfn;
    model_hour.lapse_k_per_m=result.fradj_fixture.lapse_k_per_m;
    model_hour.temperature_k=result.observed.temp2d_k;
    model_hour.sensible_heat_w_m2=result.sensible_heat_wm2;
    const auto zface=std::vector<float>(
        controls.zface_m.begin(),controls.zface_m.end());
    const auto direct=p6g::apply_g11_terrain_after_wind1(
        terrain,model_hour,zface,original);
    check(stages.after_slope().u==direct.field.u&&
          stages.after_slope().v==direct.field.v,
          "G17B source-observed-SOLAR-HEATFX corrected U/V differ from native G11");
    check(stages.run(p6::NativeHourStage::DiagnoWindbcFirstGuess,frame).completed,
          "G17B did not snapshot first source WINDBC before INTER2");
    reject([&]{stages.run(p6::NativeHourStage::DiagnoInter2,frame);},
           "G17B skipped STHEOR DIAGI profile handoff before INTER2");
    stages.provide_selected_diagi_before_inter2(profiles);
    check(stages.run(p6::NativeHourStage::DiagnoInter2,frame).completed,
          "G17B source heat chain did not reach INTER2");
    check(!stages.run(p6::NativeHourStage::CompGridMixht,frame).completed,
          "G17B incorrectly certified full multi-station COMP");
    check(frame.next.ziconv_m==previous.ziconv_m,
          "G17B mutated accepted prior-hour P6E state");
}

int main(int argc,char** argv) {
    try {
        check(argc==2,"G17B source met.inp argument missing");
        std::ifstream deck(argv[1]);
        check(static_cast<bool>(deck),"G17B pinned original met.inp not found");
        const std::string text((std::istreambuf_iterator<char>(deck)),
                               std::istreambuf_iterator<char>());
        const auto control=p6g::parse_original_wind_controls(text);
        const auto real_surfvar=p6g::parse_original_surfvar_controls(text);
        check(real_surfvar.irad==1&&real_surfvar.trad_km==500.f&&
              real_surfvar.numts==5&&real_surfvar.iavet==1&&
              real_surfvar.itprog==0&&real_surfvar.irhprog==0&&
              real_surfvar.npsta==0,
              "G17B pinned Hefei real SURFVAR controls not parsed correctly");
        const auto noon=sys_days{year{2024}/January/1}+hours{4};
        Fixture winter_day(noon);
        verify_real_solar(winter_day);
        verify_selected_slope_bridge(winter_day,control);
        // Pinned real Hefei requests IAVET=1. The current multi-station
        // SURFVAR source kernel only implements IAVET=0, and MUST reject
        // attempts to call that path complete/physically original.
        auto original_case=winter_day;
        original_case.anc.original_surfvar_controls=real_surfvar;
        reject([&]{(void)original_case.calculate();},
               "G17B silently accepted real Hefei IAVET=1 as selected IAVET=0");
        // An explicitly transformed *test-only* IAVET=0 configuration
        // can execute exactly if ALL original influence controls match.
        auto selected_case=winter_day;
        auto selected_controls=real_surfvar;
        selected_controls.iavet=0;
        selected_case.anc.original_surfvar_controls=selected_controls;
        selected_case.anc.numts=5;
        selected_case.anc.trad_grid=50.f;
        check(selected_case.calculate().observed.temp2d_k.size()==144,
              "G17B rejected correctly source-bounded IAVET=0 test path");
        selected_case.anc.trad_grid=20.f;
        reject([&]{(void)selected_case.calculate();},
               "G17B accepted incorrect original TRADKM/Grid resolution");
        Fixture winter_night(noon+hours{12});
        verify_real_solar(winter_night);
        const auto daylight=winter_day.calculate();
        const auto nighttime=winter_night.calculate();
        check(daylight.sun_sine[20]>nighttime.sun_sine[20]&&
              daylight.shortwave_wm2[20]>nighttime.shortwave_wm2[20],
              "G17B real solar model has no diurnal forcing");
        check(nighttime.sun_sine[20]<0.f&&
              nighttime.sensible_heat_wm2[20]==-0.1f,
              "G17B original HEATFX night branch not followed");
        auto altered=winter_day;
        altered.surface.hourly.front().by_station[0].temperature_k=291.f;
        check(altered.calculate().observed.temp2d_k[13]>
              daylight.observed.temp2d_k[13],
              "G17B updated real station temperature did not propagate");
        altered=winter_day;
        altered.surface.hourly.front().by_station[0].opaque_cloud_tenths=9;
        // Cell 13 is controlled by NEARS=1 (SS1); cell 20 is NEARS=2.
        check(altered.calculate().shortwave_wm2[13]<
              daylight.shortwave_wm2[13],
              "G17B source station cloud did not enter HEATFX");
        altered=winter_day;altered.anc.explicitly_test_only=false;
        reject([&]{(void)altered.calculate();},
               "G17B allowed externally controlled P6E ancillaries as production");
        altered=winter_day;altered.geo.hemisphere='S';
        reject([&]{(void)altered.calculate();},
               "G17B used unsupported UTM south source geometry");
        altered=winter_day;altered.surface.station_ids={58322,58321};
        reject([&]{(void)altered.calculate();},
               "G17B accepted reversed original SSn identity");
        altered=winter_day;altered.surface.hourly.front().by_station[0].cloud_valid=false;
        reject([&]{(void)altered.calculate();},
               "G17B fabricated missing station cloud");
        altered=winter_day;altered.anc.nearest_surface[30]=3;
        reject([&]{(void)altered.calculate();},
               "G17B accepted spoofed external NEARS site");
        altered=winter_day;altered.anc.nearest_surface.clear();
        check(altered.calculate().nearest_surface==daylight.nearest_surface,
              "G17B source SETCOM depends on an external NEARS fixture");
        altered=winter_day;
        altered.surface.hourly.front().by_station[0].pressure_valid=false;
        reject([&]{(void)altered.calculate();},
               "G17B AIRDEN fabricated missing nearest RDSN station pressure");
        altered=winter_day;altered.anc.coefficients.hc3p1=0.f;
        reject([&]{(void)altered.calculate();},
               "G17B silently supplied missing source heat coefficients");
        altered=winter_day;altered.anc.initial_water_qh_wm2.pop_back();
        reject([&]{(void)altered.calculate();},
               "G17B substituted original water QH");
        altered=winter_day;altered.anc.lapse_k_per_m.pop_back();
        reject([&]{(void)altered.calculate();},
               "G17B accepted incomplete original lapse input");
        std::cout<<"PASS_P6G_G17B_OBS_SURFVAR_COMPUTED_SOLAR_HEATFX "
                    "2SS_10KM_REAL_UTM UTC_DAY_NIGHT "
                    "SOURCE_KERNEL_ELEMENTWISE_EQUAL "
                    "EXPLICIT_ANCILLARIES=FIXTURE_ONLY "
                    "FULL_P6E_AND_45_FIELD_PARITY=NOT_YET_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"FAIL_P6G_G17B "<<e.what()<<"\n";return 1;
    }
}
