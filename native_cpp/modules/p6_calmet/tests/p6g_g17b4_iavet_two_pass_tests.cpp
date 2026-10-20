// G17B4 source IAVET=1: two distinct SURFVAR calls across FRADJ using
// original selected SURFVAR+AVETMP kernels. Actual 45-field multi-site
// physics is NOT accepted; WIND1/FRADJ arrays are controlled stage fixtures.
#include "cteas/p6/p6g_g17b4_iavet_two_pass.hpp"
#include "cteas/p6/p6g_g17_staged_terrain.hpp"
#include "cteas/p6/p6g_g17c_iavet1_heat_handoff.hpp"
#include "cteas/p6/p6g_g17c2_elustr_handoff.hpp"
#include "cteas/p6/p6g_g17c3_station_diagi.hpp"
#include "cteas/p6/p6g_g18a_selected_comp_mixht.hpp"
#include "cteas/p6/p6g_g18b3_upper_choice.hpp"
#include "cteas/p6/p6g_g18b4_cgamma_clock.hpp"
#include "cteas/p6/p6g_g18b5_upper_temp_faces.hpp"
#include "cteas/p6/p6g_g18b7_previous_ziconv.hpp"
#include "cteas/p6/p6g_g18b8_gamma_grid.hpp"
#include "cteas/p6/p6g_g18b9_original_gamma_controls.hpp"
#include "cteas/p6/p6g_g18c1_avemix.hpp"
#include "cteas/p6/p6g_g18c2_wstarr_after_avemix.hpp"
#include "cteas/p6/p6g_g18c3_temp3d_after_comp.hpp"
#include "cteas/p6/p6g_g18c4_selected_hour_candidate.hpp"
#include "cteas/p6/p6g_g18c5_selected_p6f_fields.hpp"
#include "cteas/p6/p6g_g18c6_selected_p6f_dataset.hpp"
#include "cteas/p6/p6g_g18d1_p6f_precommit.hpp"
#include "cteas/p6/p6g_g18d3_heat_source_defaults.hpp"
#include "cteas/p6/p6g_g18d4_comp_stage_adapter.hpp"
#include "cteas/p6/p6g_g18d5_source_mixht_controls.hpp"
#include "cteas/p6/p6g_g18d6_station_upper_assignment.hpp"
#include "cteas/p6/p6g_g18e1_stheor_stage_adapter.hpp"
#include "cteas/p6/p6g_g18e2_heatfx_stage_adapter.hpp"
#include "cteas/p6/p6g_g18e3_airden_elustr_stage_adapter.hpp"
#include "cteas/p6/p6g_g18e5_slope_stage_adapter.hpp"
#include "cteas/p6/p6g_g18e6_wind_tail_stage_adapter.hpp"
#include "cteas/p6/p6g_g18e7_live_comp_stage_adapter.hpp"
#include "cteas/p6/p6g_g18e8_p6f_commit_stage_adapter.hpp"
#include "cteas/p6/p6g_g18e4_prepdi_stage_adapter.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <exception>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <memory>
#include <optional>
#include <regex>
#include <stdexcept>
#include <string>
#include <vector>
namespace p6=cteas::calmet::p6;
namespace p6e=cteas::p6e;
namespace p6g=cteas::calmet::p6g;
using namespace std::chrono;
static void check(bool yes,const char* msg) {
    if(!yes)throw std::runtime_error(msg);
}
template<class F>static void rejects(F&& f,const char* why) {
    bool denied=false;
    try{f();}catch(const std::exception&){denied=true;}
    check(denied,why);
}
static p6::DeckStation station(int id,float x,float y){
    p6::DeckStation s{};s.id=id;s.local_x_m=x;s.local_y_m=y;return s;
}
struct Input {
    p6g::GeoGrid grid;
    p6g::StationSet station_set;
    p6g::SurfaceSeries series;
    p6g::G17B4SurfaceControls controls;
    explicit Input(const p6g::G17B4SurfaceControls& source,
                   sys_seconds begin) : controls(source){
        grid.nx=12;grid.ny=12;grid.grid_km=10.f;
        grid.zone=50;grid.hemisphere='N';
        grid.xorigin_km=510.885f;grid.yorigin_km=3531.269f;
        grid.nlu=1;grid.valid_categories={20};
        grid.lai.assign(144,1.5f);
        grid.z0_m.assign(144,0.5f);
        grid.albedo.assign(144,0.2f);
        grid.bowen.assign(144,0.5f);
        grid.hcg.assign(144,0.2f);grid.qf.assign(144,0.f);
        grid.iwat1=50;grid.iwat2=55;grid.landuse.assign(144,20);
        for(int j=0;j<12;++j)for(int i=0;i<12;++i)
            grid.terrain_m.push_back(100.f+150.f*i+100.f*j);
        station_set.surface={station(58321,10000.f,10000.f),
                             station(58322,100000.f,100000.f)};
        series.begin=begin;series.end=begin+hours{1};
        series.station_ids={58321,58322};
        p6g::SurfaceHour hour;
        hour.start=begin;hour.end=series.end;
        hour.by_station.resize(2);
        hour.by_station[0].wind_valid=true;
        hour.by_station[0].wind_speed_mps=5.f;
        hour.by_station[0].wind_direction_deg=90.f;
        hour.by_station[0].pressure_valid=true;
        hour.by_station[0].pressure_mb=1013.f;
        hour.by_station[0].cloud_valid=true;
        hour.by_station[0].opaque_cloud_tenths=2;
        hour.by_station[0].ceiling_valid=true;
        hour.by_station[0].ceiling_hundreds_ft=150;
        hour.by_station[0].temperature_valid=true;
        hour.by_station[0].temperature_k=281.f;
        hour.by_station[0].humidity_valid=true;
        hour.by_station[0].humidity_pct=60;
        hour.by_station[1].wind_valid=true;
        hour.by_station[1].wind_speed_mps=6.f;
        hour.by_station[1].wind_direction_deg=180.f;
        hour.by_station[1].pressure_valid=true;
        hour.by_station[1].pressure_mb=997.f;
        hour.by_station[1].cloud_valid=true;
        hour.by_station[1].opaque_cloud_tenths=7;
        hour.by_station[1].ceiling_valid=true;
        hour.by_station[1].ceiling_hundreds_ft=75;
        hour.by_station[1].temperature_valid=true;
        hour.by_station[1].temperature_k=302.f;
        hour.by_station[1].humidity_valid=true;
        hour.by_station[1].humidity_pct=73;
        series.hourly.push_back(hour);
    }
    p6g::G17B4TwoPassSurfvar make() const{
        return {grid,station_set,series,series.hourly.front(),controls};
    }
};
static std::vector<float> winds(int component,bool corrected) {
    std::vector<float> out(144*9);
    for(int k=0;k<9;++k)
        for(int j=0;j<12;++j)
            for(int i=0;i<12;++i) {
                const auto p=static_cast<std::size_t>(k*144+j*12+i);
                // The post-FRADJ field has a different horizontal direction.
                const float base=corrected ? (component==0?-8.f:2.f)
                                           : (component==0?8.f:-2.f);
                out[p]=base+static_cast<float>((i+2*j)%5)*0.03f;
            }
    return out;
}
static void verify(const p6g::G17B4SurfaceControls& controls,
                   sys_seconds begin){
    Input f(controls,begin);
    auto two=f.make();
    auto pre_u=winds(0,false),pre_v=winds(1,false);
    auto post_u=winds(0,true),post_v=winds(1,true);
    check(two.end()==f.series.end&&!two.first_ready()&&!two.second_ready(),
          "G17B4 IAVET source state not initially empty");
    rejects([&]{(void)two.result();},"G17B4 returned final field without stages");
    rejects([&]{two.after_fradj_before_heatfx(
        f.series.end,post_u,post_v);},
        "G17B4 accepted second IAVET before first wind");
    rejects([&]{two.after_wind1_before_fradj(
        f.series.end+hours{1},pre_u,pre_v);},
        "G17B4 accepted stale first model hour");
    auto short_wind=pre_u;short_wind.pop_back();
    rejects([&]{two.after_wind1_before_fradj(
        f.series.end,short_wind,pre_v);},
        "G17B4 accepted incomplete source 3D WIND1");
    two.after_wind1_before_fradj(f.series.end,pre_u,pre_v);
    check(two.first_ready()&&!two.second_ready(),
          "G17B4 source first SURFVAR did not commit");
    rejects([&]{(void)two.final_temperature();},
            "G17B4 invented post-FRADJ temperature before second call");
    rejects([&]{two.after_wind1_before_fradj(
        f.series.end,pre_u,pre_v);},
        "G17B4 silently duplicated source first SURFVAR");
    rejects([&]{two.after_fradj_before_heatfx(
        f.series.end+hours{1},post_u,post_v);},
        "G17B4 accepted next-hour post-FRADJ winds");
    // Independent numerical check against immutable #53 P6E AVETMP kernel.
    p6e::SurfvarMultistationInput base;
    base.nx=12;base.ny=12;base.dgrid_m=10000.f;
    base.irad=controls.source.irad;base.numts=controls.source.numts;
    base.trad_grid=controls.source.trad_km/10.f;
    base.stations={{10000.f,10000.f,281.f,60},
                   {100000.f,100000.f,302.f,73}};
    const auto raw=p6e::surfvar_multistation(base);
    check(two.raw_observed_temperature()==raw.temp2d_k,
          "G17B4 observation weighting differs from original SURFVAR");
    auto direct=[&](const std::vector<float>& u,
                    const std::vector<float>& v) {
        p6e::AvetmpInput a;
        a.nx=12;a.ny=12;
        a.mnmdav=controls.mnmdav;
        a.hafang_deg=controls.hafang_deg;
        a.dgrid_m=10000.f;
        a.temperature_k=raw.temp2d_k;
        a.u_ms.assign(u.begin(),u.begin()+144);
        a.v_ms.assign(v.begin(),v.begin()+144);
        return p6e::avetmp(a);
    };
    const auto expected_first=direct(pre_u,pre_v);
    check(two.first_temperature()==expected_first,
          "G17B4 pre-FRADJ source AVETMP field differs elementwise");
    two.after_fradj_before_heatfx(f.series.end,post_u,post_v);
    const auto out=two.result();
    const auto expected_final=direct(post_u,post_v);
    check(out.complete&&out.end==f.series.end&&
          out.temperature_before_fradj_k==expected_first&&
          out.temperature_after_fradj_k==expected_final,
          "G17B4 post-FRADJ source AVETMP field differs elementwise");
    std::size_t different=0;
    for(std::size_t p=0;p<144;++p)
        different+=out.temperature_before_fradj_k[p]!=
                   out.temperature_after_fradj_k[p];
    check(different>0,"G17B4 two source wind snapshots produce identical TEMP2D");
    rejects([&]{two.after_fradj_before_heatfx(f.series.end,post_u,post_v);},
            "G17B4 allowed duplicate second SURFVAR");
    auto invalid=f;
    std::swap(invalid.series.station_ids[0],invalid.series.station_ids[1]);
    rejects([&]{(void)invalid.make();},"G17B4 accepted shuffled station IDs");
    invalid=f;invalid.grid.landuse[0]=50;
    rejects([&]{(void)invalid.make();},
            "G17B4 falsely accepted untested water SURFVAR branch");
    invalid=f;invalid.controls.source.iavet=0;
    rejects([&]{(void)invalid.make();},
            "G17B4 accepted IAVET=0 in original two-pass route");
    invalid=f;invalid.series.hourly.front().by_station[0].temperature_valid=false;
    invalid.series.hourly.front().by_station[1].temperature_valid=false;
    rejects([&]{(void)invalid.make();},
            "G17B4 invented missing multi-site TEMP2D observations");
}
// P6-B2 scoped single real-station SURFVAR admission: no fake second
// source, and no weakening of observed temperature or water rejection.
static void verify_single_surface_source(
    const p6g::G17B4SurfaceControls& controls,sys_seconds begin) {
    Input f(controls,begin);
    f.station_set.surface.resize(1);
    f.series.station_ids.resize(1);
    f.series.hourly.front().by_station.resize(1);
    auto selected=f.make();
    const auto raw=selected.raw_observed_temperature();
    check(raw.size()==144&&
          std::all_of(raw.begin(),raw.end(),[](float t){return t==281.f;}),
          "G17B4 true one-observed-SS SURFVAR not exactly station temperature");
    auto first_u=winds(0,false),first_v=winds(1,false);
    auto second_u=winds(0,true),second_v=winds(1,true);
    selected.after_wind1_before_fradj(f.series.end,first_u,first_v);
    selected.after_fradj_before_heatfx(f.series.end,second_u,second_v);
    check(selected.result().complete&&
          selected.first_temperature().size()==144&&
          selected.final_temperature().size()==144,
          "G17B4 single-observed-SS selected IAVET twice could not complete");
    auto invalid=f;
    invalid.station_set.surface.clear();
    rejects([&]{(void)invalid.make();},
            "G17B4 admitted zero original surface stations");
    invalid=f;
    invalid.series.hourly.front().by_station[0].temperature_valid=false;
    rejects([&]{(void)invalid.make();},
            "G17B4 invented missing one-SS observed temperature");
    invalid=f;
    invalid.grid.landuse[0]=50;
    rejects([&]{(void)invalid.make();},
            "G17B4 one-SS improperly admitted unsupported land/water physics");
}
static void verify_source_staged_iavet(
    const p6g::G17B4SurfaceControls& controls,
    const p6g::OriginalWindControls& wind,
    sys_seconds begin,const std::string& source_metinp,
    const std::string& selected_output_file){
    Input f(controls,begin);
    auto surface=f.make();
    p6g::G16ObservedProfiles profiles;
    profiles.end=f.series.end;
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
    for(std::size_t k=4;k<9;++k) {
        profiles.inter2_present[k*4]=0;
        profiles.inter2_u_mps[k*4]=999.f;
        profiles.inter2_v_mps[k*4]=999.f;
    }
    const auto terrain=p6g::prepare_g11_terrain(f.grid,35.f);
    p6g::G17FradjSource forcing;
    forcing.end=f.series.end;
    forcing.provenance=p6g::TerrainHourProvenance::SyntheticReferenceFixture;
    forcing.isurft=-1;
    forcing.domain_temperature_k=285.f;
    forcing.critfn=10.f;
    forcing.lapse_k_per_m.assign(144,0.002f);
    const auto fresh_g14_fradj_source=forcing;
    // No externally invented TEMP2D. The first G17B4 SURFVAR fills it
    // using precisely G17's native WIND1 output.
    const auto initial_profiles=profiles;
    p6g::G17SelectedTerrainFixturePhysics stages(
        std::move(profiles),terrain,std::move(forcing));
    rejects([&]{stages.provide_selected_readge_htfac_fixture(1.f,false);},
            "G17D silently accepted source HTFAC from unproven GEO provenance");
    rejects([&]{stages.provide_selected_readge_htfac_fixture(0.f,true);},
            "G17D allowed HTFAC<=0 second boundary mode to masquerade as HTFAC=1");
    stages.provide_selected_readge_htfac_fixture(1.f,true);
    rejects([&]{stages.provide_selected_readge_htfac_fixture(1.f,true);},
            "G17D allowed duplicate GEO HTFAC source selection");
    p6g::StationSet all=f.station_set;
    all.upper={station(58424,20000.f,20000.f),
               station(58425,50000.f,50000.f)};
    // Supply source-ordered absolute READCF UTM positions for the two SSs.
    for(auto& ss:all.surface) {
        ss.utm_x_km=f.grid.xorigin_km+ss.local_x_m/1000.f;
        ss.utm_y_km=f.grid.yorigin_km+ss.local_y_m/1000.f;
        ss.anemometer_height_m=10.f;
    }
    p6g::InputHour slot{};
    slot.end=f.series.end;
    slot.upper.assign(2,p6g::UpperBracket{0,1,8*3600,3*3600,5*3600});
    std::vector<p6g::UpperSeries> upper(2);
    upper[0].station_id=58424;upper[1].station_id=58425;
    for(std::size_t idx=0;idx<upper.size();++idx) {
        p6::UpperSounding older;
        older.station_id=upper[idx].station_id;
        older.start=f.series.begin-hours{2};
        older.end=older.start;
        p6::UpperSounding following;
        following.station_id=upper[idx].station_id;
        following.start=f.series.end+hours{5};
        following.end=following.start;
        for(std::size_t k=0;k<4;++k) {
            p6::UpperLevel level;
            level.height_valid=true;level.temperature_valid=true;
            level.height_lgl_m=static_cast<float>(k*k*500);
            level.temperature_k=285.f+static_cast<float>(3*k+idx);
            older.data.push_back(level);
            following.data.push_back(level);
        }
        upper[idx].soundings={older,following};
    }
    p6::NativeGridMemory prior;
    prior.zi_m.assign(144,0.f);
    prior.ziconv_m.assign(144,0.f);
    prior.dptt_k.assign(144,0.f);
    p6g::MultiHourFrame frame{
        0,f.grid,all,f.series.hourly.front(),slot,upper,
        &wind,prior,prior,{}};
    rejects([&]{stages.prepare_original_iavet1_before_fradj(surface);},
            "G17B4 allowed first SURFVAR before source WIND1");
    check(stages.run(p6::NativeHourStage::DiagnoWind1,frame).completed,
          "G17B4 staged native WIND1 failed");
    stages.prepare_original_iavet1_before_fradj(surface);
    check(surface.first_stage_wind_matches(
              stages.wind_stages().first_guess.u_mps,
              stages.wind_stages().first_guess.v_mps),
          "G17B4 first SURFVAR did not use actual source WIND1");
    rejects([&]{stages.finish_original_iavet1_after_fradj(surface);},
            "G17B4 allowed second SURFVAR before native FRADJ");
    check(stages.run(p6::NativeHourStage::DiagnoFradj,frame).completed,
          "G17B4 source FRADJ rejected original first TEMP2D");
    stages.finish_original_iavet1_after_fradj(surface);
    check(surface.second_ready(),
          "G17B4 second original SURFVAR not computed after FRADJ");
    const auto second=surface.final_temperature();
    // Independent raw temperature + immutable AVETMP comparison based on
    // this G17 instance's actual FRADJ-adjusted lower-layer winds.
    p6e::AvetmpInput av;
    av.nx=12;av.ny=12;av.dgrid_m=10000.f;
    av.hafang_deg=controls.hafang_deg;av.mnmdav=controls.mnmdav;
    av.temperature_k=surface.raw_observed_temperature();
    const auto& fr=stages.after_fradj();
    av.u_ms.assign(fr.u.begin(),fr.u.begin()+144);
    av.v_ms.assign(fr.v.begin(),fr.v.begin()+144);
    check(second==p6e::avetmp(av),
          "G17B4 second source TEMP2D not based on native FRADJ wind");
    bool changed=false;
    for(std::size_t i=0;i<144;++i)
        changed|=(second[i]!=surface.first_temperature()[i]);
    check(changed,"G17B4 physical G17 FRADJ did not alter source TEMP2D");
    auto ancillary=p6g::g18d3_source_hflux_inputs(
        f.grid,source_metinp,false);
    check(ancillary.coefficients.hc1==5.31e-13f&&
          ancillary.coefficients.hc2==60.f&&
          ancillary.coefficients.hc3p1==0.12f+1.f,
          "G18D3 default vendor HC1/HC2/HC3 source values mismatched");
    rejects([&]{
        (void)p6g::g18d3_source_hflux_inputs(
            f.grid,source_metinp+"\n! HC1 = 0. !",true);
    },"G18D3 ignored met.inp HFLUX override before source READCF parity");
    rejects([&]{
        (void)p6g::selected_iavet1_heat_after_fradj(
            f.grid,all,f.series.hourly.front(),surface,ancillary);
    },"G17C accepted unmarked heat coefficients as production state");
    ancillary.explicitly_test_only=true;
    // Independent direct-call comparison only. The downstream P6E/DIAGNO
    // calculation must consume the stage-executed G14 HEATFX result.
    const auto direct_selected=p6g::selected_iavet1_heat_after_fradj(
        f.grid,all,f.series.hourly.front(),surface,ancillary);
    p6g::G18E2SelectedHeatfxStageAdapter heat_stage(
        stages,surface,ancillary);
    check(!heat_stage.run(
              p6::NativeHourStage::DiagnoHeatfx,frame).completed,
          "G18E2 test-only HEATFX was wrongly accepted as production");
    rejects([&]{
        heat_stage.run_selected(
            p6::NativeHourStage::DiagnoAirden,frame,true);
    },"G18E2 HEATFX ran at wrong original DIAGNO stage");
    rejects([&]{
        heat_stage.run_selected(
            p6::NativeHourStage::DiagnoHeatfx,frame,false);
    },"G18E2 unaccepted coefficients were promoted into production");
    heat_stage.run_selected(
        p6::NativeHourStage::DiagnoHeatfx,frame,true);
    auto counterfeit_heat_frame=frame;
    rejects([&]{
        (void)heat_stage.selected_heat_for(counterfeit_heat_frame);
    },"G18E2 HEATFX result reused from a clone of the original G14 frame");
    rejects([&]{
        heat_stage.run_selected(
            p6::NativeHourStage::DiagnoHeatfx,frame,true);
    },"G18E2 performed HEATFX twice in the same original source hour");
    const auto& selected=heat_stage.selected_heat_for(frame);
    check(selected.temperature_k==direct_selected.temperature_k&&
          selected.sensible_heat_wm2==direct_selected.sensible_heat_wm2&&
          selected.shortwave_wm2==direct_selected.shortwave_wm2&&
          selected.density_kg_m3==direct_selected.density_kg_m3&&
          selected.sun_sine==direct_selected.sun_sine,
          "G18E2 stage HEATFX differs from frozen original-source G17C kernel");
    check(selected.end==f.series.end &&
          selected.temperature_k==second &&
          selected.sun_sine.size()==144 &&
          selected.sensible_heat_wm2.size()==144 &&
          selected.nearest_surface==p6g::source_setcom_nears(f.grid,all),
          "G17C failed to bind the exact post-FRADJ observed temperature");
    auto reordered=all;
    std::swap(reordered.surface[0],reordered.surface[1]);
    rejects([&]{
        (void)p6g::selected_iavet1_heat_after_fradj(
            f.grid,reordered,f.series.hourly.front(),surface,ancillary);
    },"G17C silently accepted a different original surface station order");
    auto translated=f.grid;
    translated.xorigin_km+=1.f;
    rejects([&]{
        (void)p6g::selected_iavet1_heat_after_fradj(
            translated,all,f.series.hourly.front(),surface,ancillary);
    },"G17C accepted HEATFX geometry shifted from source SURFVAR");
    // Independent direct invocation of the immutable PR #53 HEATFX kernel:
    // second-pass TEMP2D, actual solar and cloud from 2SS, never the first.
    p6e::HeatFluxInput hi;
    hi.nx=12;hi.ny=12;hi.mcloud=1;hi.water_first=50;hi.water_last=55;
    const auto& coeff=ancillary.coefficients;
    hi.ha1=coeff.ha1;hi.ha2=coeff.ha2;
    hi.hb1=coeff.hb1;hi.hb2=coeff.hb2;
    hi.hc1=coeff.hc1;hi.hc2=coeff.hc2;hi.hc3p1=coeff.hc3p1;
    hi.station_cloud={2,7};hi.nearest=selected.nearest_surface;
    hi.landuse=f.grid.landuse;hi.sun=selected.sun_sine;
    hi.temp_k=second;hi.cloud_grid.assign(144,0.f);
    hi.albedo=f.grid.albedo;hi.bowen=f.grid.bowen;hi.soil_heat_fraction=f.grid.hcg;
    hi.anthropogenic_wm2=f.grid.qf;hi.initial_qh=ancillary.initial_water_qh_wm2;
    const auto direct_flux=p6e::heatfx(hi);
    check(selected.shortwave_wm2==direct_flux.shortwave_wm2 &&
          selected.sensible_heat_wm2==direct_flux.sensible_wm2,
          "G17C source HEATFX differs from identical PR #53 immutable kernel");
    hi.temp_k=surface.first_temperature();
    const auto wrong_flux=p6e::heatfx(hi);
    // Original HEATFX uses the fixed -0.1 W/m2 nocturnal land branch:
    // at night QH is independent of both SURFVAR temperatures. It is
    // incorrect to demand temperature sensitivity in that source branch.
    // Retain the first-vs-second temperature discrimination in daylight.
    const bool any_sun=std::any_of(selected.sun_sine.begin(),
                                  selected.sun_sine.end(),
                                  [](float x){return x>0.f;});
    if(any_sun)
        check(wrong_flux.sensible_wm2!=selected.sensible_heat_wm2,
              "G17C daytime HEATFX did not distinguish pre/post-FRADJ TEMP2D");
    else
        check(wrong_flux.sensible_wm2==selected.sensible_heat_wm2,
              "G17C nocturnal HEATFX not independent of TEMP2D as original");
    check(selected.density_kg_m3==
          p6g::source_airden_nears(selected.nearest_surface,second,
                                  f.series.hourly.front()),
          "G17C AIRDEN not sourced from the same final temperature");
    auto stale=f.series.hourly.front();
    stale.end+=hours{1};
    rejects([&]{
        (void)p6g::selected_iavet1_heat_after_fradj(
            f.grid,all,stale,surface,ancillary);
    },"G17C accepted mismatched source hour");
    stale=f.series.hourly.front();stale.by_station[0].cloud_valid=false;
    rejects([&]{
        (void)p6g::selected_iavet1_heat_after_fradj(
            f.grid,all,stale,surface,ancillary);
    },"G17C invented unavailable station cloud");
    rejects([&]{
        stages.prepare_selected_airden(frame,surface.first_temperature());
    },"G17C AIRDEN incorrectly reuses pre-FRADJ TEMP2D");
    p6g::G17C2SelectedElustrControls ec;
    ec.ipsifcn=0;
    ec.zm_m=0.5f*(wind.zface_m[0]+wind.zface_m[1]);
    ec.explicitly_test_only=true;
    p6g::G18E3SelectedAirdenElustrStageAdapter thermal_stage(
        stages,heat_stage,surface,ec);
    check(!thermal_stage.run(
              p6::NativeHourStage::DiagnoAirden,frame).completed,
          "G18E3 fixture AIRDEN falsely promoted to production");
    rejects([&]{
        thermal_stage.run_selected(p6::NativeHourStage::DiagnoElustr,frame,true);
    },"G18E3 permitted ELUSTR before original AIRDEN");
    rejects([&]{
        thermal_stage.run_selected(p6::NativeHourStage::DiagnoAirden,frame,false);
    },"G18E3 AIRDEN unverified fixture promoted to production");
    thermal_stage.run_selected(p6::NativeHourStage::DiagnoAirden,frame,true);
    check(stages.run(p6::NativeHourStage::DiagnoAirden,frame).completed &&
          stages.selected_air_density()==selected.density_kg_m3,
          "G18E3 source AIRDEN did not consume G18E2 stage HEATFX density");
    rejects([&]{
        thermal_stage.run_selected(p6::NativeHourStage::DiagnoAirden,frame,true);
    },"G18E3 duplicated original G14 AIRDEN");
    // ELUSTR's true input winds are the G17 source FRADJ output, before
    // SLOPE. Keep all thermodynamic input values from G17C1 source fields.
    auto unverified_ec=ec;
    unverified_ec.explicitly_test_only=false;
    rejects([&]{
        (void)p6g::selected_iavet1_elustr_after_heatfx(
            f.grid,all,f.series.hourly.front(),surface,selected,fr,unverified_ec);
    },"G17C2 certified fixture coefficient heat as production ELUSTR");
    rejects([&]{
        (void)thermal_stage.selected_elustr_for(frame);
    },"G18E3 returned ELUSTR before its original stage");
    auto fake_elustr_frame=frame;
    rejects([&]{
        thermal_stage.run_selected(
            p6::NativeHourStage::DiagnoElustr,fake_elustr_frame,true);
    },"G18E3 allowed same-hour cloned G14 frame in ELUSTR");
    const float previous_dptt=prior.dptt_k[0];
    prior.dptt_k[0]=previous_dptt+1.f;
    rejects([&]{
        thermal_stage.run_selected(
            p6::NativeHourStage::DiagnoElustr,frame,true);
    },"G18E3 accepted mutated prior-hour thermal memory");
    prior.dptt_k[0]=previous_dptt;
    thermal_stage.run_selected(p6::NativeHourStage::DiagnoElustr,frame,true);
    const auto direct_elustr=p6g::selected_iavet1_elustr_after_heatfx(
        f.grid,all,f.series.hourly.front(),surface,selected,fr,ec);
    const auto& elustr=thermal_stage.selected_elustr_for(frame);
    check(thermal_stage.selected_complete()&&
          elustr.qh_wm2==direct_elustr.qh_wm2&&
          elustr.ustar_mps==direct_elustr.ustar_mps&&
          elustr.el_m==direct_elustr.el_m&&
          elustr.stable_cells==direct_elustr.stable_cells&&
          elustr.daytime_cells==direct_elustr.daytime_cells,
          "G18E3 selected-stage ELUSTR differs from independent original kernel");
    rejects([&]{
        thermal_stage.run_selected(
            p6::NativeHourStage::DiagnoElustr,frame,true);
    },"G18E3 duplicated original G14 ELUSTR");
    check(elustr.end==f.series.end &&
          elustr.qh_wm2.size()==144 &&
          elustr.ustar_mps.size()==144 &&
          elustr.el_m.size()==144 &&
          elustr.stable_cells+elustr.daytime_cells==144,
          "G17C2 original ELUSTR branch contract failed");
    const auto utc_h=duration_cast<hours>(
        f.series.begin-floor<days>(f.series.begin)).count();
    if(utc_h==14)
        check(elustr.stable_cells>0,
              "G17C2 night fixture failed to exercise frozen stable ELUSTR");
    if(utc_h==2)
        check(elustr.daytime_cells>0,
              "G17C2 daylight fixture failed to exercise frozen daytime ELUSTR");
    // Independently call the exact two immutable PR #53 physics headers.
    // One branch is masked out as water at each cell, as the production
    // single-site numerical driver already does before merging the result.
    std::vector<int> stable_mask=f.grid.landuse;
    std::vector<int> day_mask=f.grid.landuse;
    for(std::size_t k=0;k<144;++k) {
        if(selected.sensible_heat_wm2[k]<0.f)day_mask[k]=f.grid.iwat1;
        else stable_mask[k]=f.grid.iwat1;
    }
    p6e::StableElustr st;
    st.nx=12;st.ny=12;st.mcloud=1;
    st.water_first=50;st.water_last=55;st.zm=ec.zm_m;
    st.landuse=stable_mask;st.nearest=selected.nearest_surface;
    st.station_cloud={2,7};st.z0=f.grid.z0_m;
    st.u1.assign(fr.u.begin(),fr.u.begin()+144);
    st.v1.assign(fr.v.begin(),fr.v.begin()+144);
    st.rho=selected.density_kg_m3;st.temp_k=second;
    st.cloud_grid.assign(144,0.f);
    st.heat_flux_initial=selected.sensible_heat_wm2;
    const auto stable_direct=p6e::stable_elustr(st);
    p6e::DaytimeElustrInput dy;
    dy.nx=12;dy.ny=12;dy.water_first=50;dy.water_last=55;
    dy.ipsifcn=0;dy.zm=ec.zm_m;dy.landuse=day_mask;
    dy.z0=f.grid.z0_m;dy.u1=st.u1;dy.v1=st.v1;
    dy.rho=st.rho;dy.temp_k=second;
    dy.heat_flux_initial=selected.sensible_heat_wm2;
    dy.initial_ustar.assign(144,0.05f);dy.initial_el.assign(144,-9.9e9f);
    const auto day_direct=p6e::elustr_daytime(dy);
    for(std::size_t k=0;k<144;++k) {
        const auto stable_here=selected.sensible_heat_wm2[k]<0.f;
        check(elustr.qh_wm2[k]==(stable_here?stable_direct.qh_wm2[k]:day_direct.qh_wm2[k]) &&
              elustr.ustar_mps[k]==(stable_here?stable_direct.ustar_ms[k]:day_direct.ustar_ms[k]) &&
              elustr.el_m[k]==(stable_here?stable_direct.monin_obukhov_m[k]:day_direct.monin_obukhov_m[k]),
              "G17C2 independent frozen P6E stable/daytime ELUSTR numerical mismatch");
    }
    auto wrong_wind=fr;
    wrong_wind.u[0]+=1.f;
    rejects([&]{
        (void)p6g::selected_iavet1_elustr_after_heatfx(
            f.grid,all,f.series.hourly.front(),surface,selected,wrong_wind,ec);
    },"G17C2 accepted wind other than actual G17 FRADJ source stage");
    auto wrong_grid=f.grid;
    wrong_grid.z0_m.clear();
    rejects([&]{
        (void)p6g::selected_iavet1_elustr_after_heatfx(
            wrong_grid,all,f.series.hourly.front(),surface,selected,fr,ec);
    },"G17C2 accepted missing source GEO roughness");
    rejects([&]{
        (void)p6g::selected_iavet1_elustr_after_heatfx(
            f.grid,reordered,f.series.hourly.front(),surface,selected,fr,ec);
    },"G17C2 accepted station reorder");
    // ELUSTR may revise QH under stable conditions, but cannot yet
    // certify the subsequent DIAGI stability or COMP hour as completed.
    check(!stages.run(p6::NativeHourStage::DiagnoElustr,frame).completed,
          "G17C2 accidentally promoted selected ELUSTR to production");
    check(frame.next.ziconv_m==prior.ziconv_m,
          "G17C2 ELUSTR test modified previous-hour committed state");
    auto stale_heat=elustr.selected_slope_fixture(selected);
    stale_heat.temperature_k=surface.first_temperature();
    rejects([&]{stages.provide_slope_heat(stale_heat);},
            "G17C2 SLOPE accepted obsolete first TEMP2D");
    const auto genuine_heat=elustr.selected_slope_fixture(selected);
    check(genuine_heat.sensible_heat_w_m2==elustr.qh_wm2 &&
          genuine_heat.temperature_k==selected.temperature_k,
          "G17C2 stale HEATFX QH used after stable ELUSTR");
    // G18E5: execute original SLOPE at G14 slot 6, consuming G18E3's
    // actual post-ELUSTR QH (stable cells may have changed it), never
    // the earlier HEATFX field. The standalone formula remains frozen.
    p6g::G18E5SelectedSlopeStageAdapter slope_stage(
        stages,heat_stage,thermal_stage);
    check(!slope_stage.run(
              p6::NativeHourStage::DiagnoSlope,frame).completed,
          "G18E5 test-only SLOPE falsely promoted to production");
    rejects([&]{
        slope_stage.run_selected(p6::NativeHourStage::DiagnoElustr,frame,true);
    },"G18E5 executed SLOPE before its original G14 slot");
    rejects([&]{
        slope_stage.run_selected(p6::NativeHourStage::DiagnoSlope,frame,false);
    },"G18E5 promoted selected thermal fixtures to production");
    auto cloned_slope_frame=frame;
    rejects([&]{
        slope_stage.run_selected(
            p6::NativeHourStage::DiagnoSlope,cloned_slope_frame,true);
    },"G18E5 used a detached G14 hour for source ELUSTR SLOPE");
    const float held_dptt=prior.dptt_k[0];
    prior.dptt_k[0]=held_dptt+1.f;
    rejects([&]{
        slope_stage.run_selected(p6::NativeHourStage::DiagnoSlope,frame,true);
    },"G18E5 SLOPE accepted mutated committed previous-hour DPTT");
    prior.dptt_k[0]=held_dptt;
    // Scoped inputs are still test-only: do not claim production HEATFX/COMP.
    check(!stages.run(p6::NativeHourStage::DiagnoHeatfx,frame).completed,
          "G17C marked experimental coefficient-controlled heat as production");
    slope_stage.run_selected(p6::NativeHourStage::DiagnoSlope,frame,true);
    const auto& native_slope=slope_stage.selected_slope_wind_for(frame);
    check(native_slope.u==stages.after_slope().u &&
          native_slope.v==stages.after_slope().v &&
          native_slope.u.size()==144u*9u &&
          native_slope.v.size()==144u*9u,
          "G18E5 staged SLOPE differs from the original frozen kernel");
    rejects([&]{
        slope_stage.run_selected(p6::NativeHourStage::DiagnoSlope,frame,true);
    },"G18E5 duplicated SLOPE after stage completion");
    rejects([&]{
        (void)slope_stage.selected_slope_wind_for(cloned_slope_frame);
    },"G18E5 leaked source slope wind to a copied G14 frame");
    // G18E6: first WINDBC is the seventh source-ordered DIAGNO slot,
    // authorized by the SAME staged G18E5 SLOPE and live G14 frame.
    p6g::G18E6SelectedWindTailStageAdapter wind_tail(stages,slope_stage);
    check(!wind_tail.run(
              p6::NativeHourStage::DiagnoWindbcFirstGuess,frame).completed,
          "G18E6 fixture WINDBC pretended to be production CALMET");
    rejects([&]{
        wind_tail.run_selected(p6::NativeHourStage::DiagnoInter2,frame,true);
    },"G18E6 attempted INTER2 before first WINDBC/STHEOR");
    rejects([&]{
        wind_tail.run_selected(
            p6::NativeHourStage::DiagnoWindbcFirstGuess,frame,false);
    },"G18E6 allowed fixture-to-production promotion");
    wind_tail.run_selected(
        p6::NativeHourStage::DiagnoWindbcFirstGuess,frame,true);
    check(wind_tail.completed_wind_stages()==1,
          "G18E6 first source WINDBC not staged");
    rejects([&]{
        wind_tail.run_selected(
            p6::NativeHourStage::DiagnoWindbcFirstGuess,frame,true);
    },"G18E6 duplicated source first WINDBC");
    p6g::G17C3StationControls sc;
    sc.upper_ordinal_for_surface=
        p6g::g18d6_station_uppers_from_source_setcom(
            f.grid,all,source_metinp,true);
    check(sc.upper_ordinal_for_surface==std::vector<std::size_t>({0,1}),
          "G18D6 original SETCOM NEARU did not choose correct 2US for STHEOR");
    rejects([&]{
        (void)p6g::g18d6_station_uppers_from_source_setcom(
            f.grid,all,source_metinp,false);
    },"G18D6 selected station map masqueraded as whole P6 production");
    auto alternative_grid=f.grid;
    alternative_grid.grid_km=10.f;
    auto wrong_station=all;
    wrong_station.surface[0].local_x_m=-10000.f;
    rejects([&]{
        (void)p6g::g18d6_station_uppers_from_source_setcom(
            alternative_grid,wrong_station,source_metinp,true);
    },"G18D6 accepted STHEOR station outside source GEO");
    sc.heat_coefficients=ancillary.coefficients;
    sc.zimin_m=50.f;sc.zimax_m=3000.f;sc.constn=2400.f;
    sc.dptmin_kperm=.001f;sc.dzzi_m=200.f;
    sc.threshl=0.f;sc.fcori_s=1.e-4f;sc.cmech=100.f;
    rejects([&]{
        (void)p6g::selected_station_diagi_from_previous_comp(
            frame,surface,selected,sc);
    },"G17C3 accepted unmarked STHEOR/MIXHTST station mapping");
    sc.explicitly_test_only=true;
    const auto diagi=p6g::selected_station_diagi_from_previous_comp(
        frame,surface,selected,sc);
    check(diagi.size()==2&&diagi[0].surface_id==58321&&
          diagi[0].upper_id==58424&&diagi[1].surface_id==58322&&
          diagi[1].upper_id==58425,
          "G17C3 multi-station source ordinal provenance wrong");
    // B2C: original CALMET NOOBS=0 requires 1SS + 1US, not 2+2.
    // Execute real selected physics kernels on an independently assembled
    // 1SS/1US subset of this case. This remains synthetic-input UNIT
    // science, NOT the NOAA P6 newsite 45-field acceptance.
    auto one_f=f;
    one_f.station_set=all;
    one_f.station_set.surface.resize(1);
    one_f.station_set.upper.resize(1);
    one_f.series.station_ids.resize(1);
    one_f.series.hourly.front().by_station.resize(1);
    auto one_frame=frame;
    one_frame.stations=one_f.station_set;
    one_frame.surface=one_f.series.hourly.front();
    one_frame.upper.resize(1);
    one_frame.input.upper.resize(1);
    auto one_surface=one_f.make();
    const auto& initial_first=stages.wind_stages().first_guess;
    one_surface.after_wind1_before_fradj(
        one_frame.input.end,initial_first.u_mps,initial_first.v_mps);
    one_surface.after_fradj_before_heatfx(
        one_frame.input.end,fr.u,fr.v);
    const auto one_heat=p6g::selected_iavet1_heat_after_fradj(
        one_f.grid,one_f.station_set,one_frame.surface,one_surface,ancillary);
    auto one_sc=sc;
    one_sc.upper_ordinal_for_surface={0};
    const auto single_diagi=p6g::selected_station_diagi_from_previous_comp(
        one_frame,one_surface,one_heat,one_sc);
    check(single_diagi.size()==1 &&
          single_diagi[0].surface_id==58321 &&
          single_diagi[0].upper_id==58424 &&
          single_diagi[0].levels_filled>=1 &&
          single_diagi[0].levels_filled<=9 &&
          std::isfinite(single_diagi[0].station_flux.sensible_wm2) &&
          std::isfinite(single_diagi[0].station_mixing.zii_to_similt_m) &&
          one_frame.previous.zi_m==prior.zi_m &&
          one_frame.previous.ziconv_m==prior.ziconv_m &&
          one_frame.previous.dptt_k==prior.dptt_k,
          "G17C3 actual-count 1SS1US selected STHEOR/MIXHTST/DIAGI failed");
    auto bad_one_frame=one_frame;
    bad_one_frame.stations.surface.clear();
    rejects([&]{
        (void)p6g::selected_station_diagi_from_previous_comp(
            bad_one_frame,one_surface,one_heat,one_sc);
    },"G17C3 admitted zero source surface stations");
    bad_one_frame=one_frame;
    bad_one_frame.stations.upper.clear();
    rejects([&]{
        (void)p6g::selected_station_diagi_from_previous_comp(
            bad_one_frame,one_surface,one_heat,one_sc);
    },"G17C3 admitted zero source upper stations");
    auto wrong_one_sc=one_sc;
    wrong_one_sc.upper_ordinal_for_surface={1};
    rejects([&]{
        (void)p6g::selected_station_diagi_from_previous_comp(
            one_frame,one_surface,one_heat,wrong_one_sc);
    },"G17C3 invented nonexistent single upper ordinal");
    bad_one_frame=one_frame;
    bad_one_frame.upper[0].soundings.front().end=one_frame.input.end+hours{2};
    rejects([&]{
        (void)p6g::selected_station_diagi_from_previous_comp(
            bad_one_frame,one_surface,one_heat,one_sc);
    },"G17C3 used future-only upper sounding for 1SS1US STHEOR");
    bad_one_frame=one_frame;
    bad_one_frame.surface.by_station[0].wind_valid=false;
    rejects([&]{
        (void)p6g::selected_station_diagi_from_previous_comp(
            bad_one_frame,one_surface,one_heat,one_sc);
    },"G17C3 invented invalid single surface wind observation");
    p6g::G16ObservedProfiles single_columns;
    single_columns.end=initial_profiles.end;
    single_columns.station_ids={58321,58424};
    for(std::size_t k=0;k<9;++k) {
        const auto s0=k*4, u0=s0+2;
        single_columns.wind1_u_mps.insert(
            single_columns.wind1_u_mps.end(),
            {initial_profiles.wind1_u_mps[s0],initial_profiles.wind1_u_mps[u0]});
        single_columns.wind1_v_mps.insert(
            single_columns.wind1_v_mps.end(),
            {initial_profiles.wind1_v_mps[s0],initial_profiles.wind1_v_mps[u0]});
        single_columns.wind1_present.insert(single_columns.wind1_present.end(),
            {initial_profiles.wind1_present[s0],initial_profiles.wind1_present[u0]});
        // This upper PREPDI INTER2 source is deliberately NOT validated.
        single_columns.inter2_u_mps.insert(
            single_columns.inter2_u_mps.end(),{999.f,999.f});
        single_columns.inter2_v_mps.insert(
            single_columns.inter2_v_mps.end(),{999.f,999.f});
        single_columns.inter2_present.insert(
            single_columns.inter2_present.end(),{0U,0U});
    }
    const auto merged_one=p6g::merge_g17c3_surface_diagi(
        single_columns,one_f.station_set,single_diagi);
    check(merged_one.wind1_u_mps==single_columns.wind1_u_mps &&
          merged_one.wind1_v_mps==single_columns.wind1_v_mps,
          "G17C3 single station DIAGI mutated validated neutral WIND1");
    for(std::size_t k=0;k<9;++k) {
        const auto idx=k*2+1;
        check(merged_one.inter2_present[idx]==0U &&
              merged_one.inter2_u_mps[idx]==999.f &&
              merged_one.inter2_v_mps[idx]==999.f,
              "G17C3 single station DIAGI forged unvalidated PREPDI upper INTER2");
    }
    std::cout<<"PASS_G17C3_1SS1US_STHEOR_MIXHTST_DIAGI_UNIT_ONLY"
             <<" PREPDI_UPPER_INTER2=NOT_ACCEPTED"
             <<" ORIGINAL_VENDOR_SINGLE_STATION=NOT_RUN"
             <<" P6_MET45=NOT_RUN\\n";
    for(std::size_t i=0;i<diagi.size();++i) {
        const auto& state=diagi[i];
        const auto& station=all.surface[i];
        const auto& obs=f.series.hourly.front().by_station[i];
        const auto z=state.cell;
        const float angle=0.0174533f*obs.wind_direction_deg;
        p6::StationElustr2Input stheor;
        stheor.surface_u_mps=-obs.wind_speed_mps*std::sin(angle);
        stheor.surface_v_mps=-obs.wind_speed_mps*std::cos(angle);
        stheor.zmid1_m=.5f*(wind.zface_m[0]+wind.zface_m[1]);
        stheor.anemometer_m=station.anemometer_height_m;
        stheor.z0_m=f.grid.z0_m[z];stheor.solar_sine=selected.sun_sine[z];
        stheor.temp_k=selected.temperature_k[z];
        stheor.rho_kg_m3=.3484321f*obs.pressure_mb/stheor.temp_k;
        stheor.cloud_tenths=obs.opaque_cloud_tenths;
        stheor.ipsifcn=sc.ipsifcn;
        const auto& c=sc.heat_coefficients;
        stheor.ha1=c.ha1;stheor.ha2=c.ha2;stheor.hb1=c.hb1;
        stheor.hb2=c.hb2;stheor.hc1=c.hc1;stheor.hc2=c.hc2;
        stheor.hc3p1=c.hc3p1;
        stheor.albedo=f.grid.albedo[z];stheor.bowen=f.grid.bowen[z];
        stheor.hcg=f.grid.hcg[z];stheor.qf=f.grid.qf[z];
        const auto expected=p6::station_elustr2_flux(stheor);
        p6::StationMixhtstInput direct_mix;
        direct_mix.previous={prior.zi_m[z],prior.ziconv_m[z],prior.dptt_k[z]};
        const auto& src_upper=upper[i].soundings.front();
        for(const auto& level:src_upper.data) {
            direct_mix.older_sounding.height_m.push_back(level.height_lgl_m);
            direct_mix.older_sounding.temp_k.push_back(level.temperature_k);
        }
        direct_mix.qh_wm2=expected.sensible_wm2;
        direct_mix.ustar_mps=expected.friction_velocity_mps;
        direct_mix.el_m=expected.monin_obukhov_m;
        direct_mix.rho_kg_m3=stheor.rho_kg_m3;
        direct_mix.zimin_m=sc.zimin_m;direct_mix.zimax_m=sc.zimax_m;
        direct_mix.constn=sc.constn;direct_mix.dptmin_kperm=sc.dptmin_kperm;
        direct_mix.dzzi_m=sc.dzzi_m;direct_mix.threshl=sc.threshl;
        direct_mix.onedte_s=sc.onedte_s;direct_mix.twodte_s=sc.twodte_s;
        direct_mix.tzicrlx_s=sc.tzicrlx_s;direct_mix.imixh=sc.imixh;
        direct_mix.izicrlx=sc.izicrlx;direct_mix.fcori_s=sc.fcori_s;
        direct_mix.cmech=sc.cmech;direct_mix.landuse=f.grid.landuse[z];
        direct_mix.water_first=f.grid.iwat1;direct_mix.water_last=f.grid.iwat2;
        const auto expected_mix=p6::station_mixhtst(direct_mix);
        check(state.station_flux.sensible_wm2==expected.sensible_wm2 &&
              state.station_flux.friction_velocity_mps==expected.friction_velocity_mps &&
              state.station_flux.monin_obukhov_m==expected.monin_obukhov_m &&
              state.station_mixing.zii_to_similt_m==expected_mix.zii_to_similt_m &&
              state.station_mixing.ziconv_after_m==expected_mix.ziconv_after_m &&
              state.station_mixing.dptt_for_comp_k==expected_mix.dptt_for_comp_k &&
              state.levels_filled>=1&&state.levels_filled<=9,
              "G17C3 original station ELUSTR2/MIXHTST source parity mismatch");
        const auto projection=cteas::p6e::utm_north_projection(f.grid.zone);
        double latitude=0.,longitude=0.;
        cteas::p6e::utm_north_to_latlon_deg(
            projection,static_cast<double>(station.utm_x_km)*1000.0,
            static_cast<double>(station.utm_y_km)*1000.0,latitude,longitude);
        p6::SimiltProfileInput direct_diagi;
        direct_diagi.station_lat_deg=static_cast<float>(latitude);
        direct_diagi.anemometer_height_m=station.anemometer_height_m;
        direct_diagi.roughness_m=f.grid.z0_m[z];
        direct_diagi.anemometer_u_mps=stheor.surface_u_mps;
        direct_diagi.anemometer_v_mps=stheor.surface_v_mps;
        direct_diagi.obukhov_length_m=expected.monin_obukhov_m;
        direct_diagi.mixing_height_m=expected_mix.zii_to_similt_m;
        direct_diagi.minimum_mixing_height_m=sc.zimin_m;
        direct_diagi.zface_m=wind.zface_m;
        const auto source_diagi=p6::original_similt_profile(direct_diagi);
        check(state.levels_filled==source_diagi.levels_filled &&
              state.diagi_profile.u_mps==source_diagi.u_mps &&
              state.diagi_profile.v_mps==source_diagi.v_mps,
              "G17C3 source DIAGI SIMILT cap/values disagree elementwise");
    }
    auto modified=sc;
    modified.upper_ordinal_for_surface={2,0};
    rejects([&]{
        (void)p6g::selected_station_diagi_from_previous_comp(
            frame,surface,selected,modified);
    },"G17C3 silently invented missing third UP station");
    auto future_upper=upper;
    future_upper[0].soundings.front().end=f.series.end+hours{1};
    const p6g::MultiHourFrame broken_frame{
        0,f.grid,all,f.series.hourly.front(),slot,future_upper,
        &wind,prior,prior,{}};
    rejects([&]{
        (void)p6g::selected_station_diagi_from_previous_comp(
            broken_frame,surface,selected,sc);
    },"G17C3 accepted missing older model-begin UP sounding");
    const auto combined=p6g::merge_g17c3_surface_diagi(
        initial_profiles,all,diagi);
    check(combined.wind1_u_mps==initial_profiles.wind1_u_mps&&
          combined.wind1_v_mps==initial_profiles.wind1_v_mps,
          "G17C3 overwrote neutral WIND1 station physics");
    for(std::size_t k=0;k<9;++k)
        for(std::size_t i=2;i<4;++i) {
            const auto z=k*4+i;
            check(combined.inter2_u_mps[z]==initial_profiles.inter2_u_mps[z]&&
                  combined.inter2_v_mps[z]==initial_profiles.inter2_v_mps[z]&&
                  combined.inter2_present[z]==initial_profiles.inter2_present[z],
                  "G17C3 changed source PREPDI upper-air columns");
        }
    // G18E1: compute selected STHEOR/ELUSTR2/MIXHTST/DIAGI in the
    // frozen #53 G14 stage slot, not outside the stage as manual setup.
    p6g::G18E1SelectedStheorStageAdapter stheor_stage(
        stages,initial_profiles,surface,selected,sc);
    rejects([&]{wind_tail.bind_stheor_stage(stheor_stage,frame,true);},
            "G18E6 bound STHEOR before original G14 slot 8");
    check(!stheor_stage.run(
              p6::NativeHourStage::DiagnoStheorElustr2Mixhtst,frame).completed,
          "G18E1 test-only station stage impersonated production physics");
    rejects([&]{(void)stheor_stage.stations();},
            "G18E1 exposed DIAGI before original stage");
    rejects([&]{
        stheor_stage.run_selected(
            p6::NativeHourStage::CompGridMixht,frame,true);
    },"G18E1 allowed STHEOR after DIAGNO outside the frozen G14 slot");
    rejects([&]{
        stheor_stage.run_selected(
            p6::NativeHourStage::DiagnoStheorElustr2Mixhtst,frame,false);
    },"G18E1 promoted partial physical station state into full production");
    auto wrong_slot=slot;
    wrong_slot.end+=hours{1};
    p6g::MultiHourFrame wrong_hour{
        0,f.grid,all,f.series.hourly.front(),wrong_slot,upper,
        &wind,prior,prior,{}};
    rejects([&]{
        stheor_stage.run_selected(
            p6::NativeHourStage::DiagnoStheorElustr2Mixhtst,
            wrong_hour,true);
    },"G18E1 accepted a future DIAGI slot over previous-hour state");
    stheor_stage.run_selected(
        p6::NativeHourStage::DiagnoStheorElustr2Mixhtst,frame,true);
    check(stheor_stage.selected_complete()&&
          stheor_stage.selected_hour_index()==frame.hour_index &&
          stheor_stage.stations().size()==diagi.size(),
          "G18E1 selected G14 STHEOR source-stage output absent");
    for(std::size_t i=0;i<diagi.size();++i) {
        const auto& actual=stheor_stage.stations()[i];
        const auto& expected=diagi[i];
        check(actual.surface_id==expected.surface_id&&
              actual.upper_id==expected.upper_id&&
              actual.cell==expected.cell&&
              actual.levels_filled==expected.levels_filled&&
              actual.station_mixing.dptt_for_comp_k==
                  expected.station_mixing.dptt_for_comp_k&&
              actual.diagi_profile.u_mps==expected.diagi_profile.u_mps&&
              actual.diagi_profile.v_mps==expected.diagi_profile.v_mps,
              "G18E1 staged DIAGI is not the same G17C3 native calculation");
    }
    // A cloned preview can carry the same hour_index/end and station IDs,
    // yet it does not represent the authoritative in-flight G14 transaction.
    auto counterfeit_stheor_frame=frame;
    rejects([&]{
        (void)stheor_stage.stations_for_comp(counterfeit_stheor_frame);
    },"G18E1 permitted stage station memory from a cloned G14 frame");
    const float original_prior_zi=prior.zi_m[0];
    prior.zi_m[0]=original_prior_zi+1.f;
    rejects([&]{
        (void)stheor_stage.stations_for_comp(frame);
    },"G18E1 allowed prior-hour ZI mutation before COMP");
    prior.zi_m[0]=original_prior_zi;
    check(stheor_stage.stations_for_comp(frame).size()==diagi.size(),
          "G18E1 did not authorize the same source G14 COMP frame");
    const auto& staged_profiles=stheor_stage.observed_after_diagi();
    check(staged_profiles.wind1_u_mps==combined.wind1_u_mps&&
          staged_profiles.wind1_v_mps==combined.wind1_v_mps&&
          staged_profiles.inter2_u_mps==combined.inter2_u_mps&&
          staged_profiles.inter2_v_mps==combined.inter2_v_mps&&
          staged_profiles.inter2_present==combined.inter2_present,
          "G18E1 altered source PREPDI or missed the STHEOR station handoff");
    rejects([&]{
        stheor_stage.run_selected(
            p6::NativeHourStage::DiagnoStheorElustr2Mixhtst,frame,true);
    },"G18E1 duplicated source STHEOR/MIXHTST current-hour stage");
    rejects([&]{stages.provide_selected_diagi_before_inter2(combined);},
            "G18E1 permitted a second DIAGI handoff outside source stage");
    wind_tail.bind_stheor_stage(stheor_stage,frame,true);
    rejects([&]{wind_tail.bind_stheor_stage(stheor_stage,frame,true);},
            "G18E6 allowed duplicate DIAGI handoff to INTER2");
    rejects([&]{
        (void)wind_tail.selected_wind_for_comp(frame);
    },"G18E6 exposed incomplete physical U/V/W to COMP");
    rejects([&]{
        (void)stages.run(p6::NativeHourStage::DiagnoSmoothDivcelW,frame);
    },"G17D ran final W before second WINDBC source stage");
    wind_tail.run_selected(p6::NativeHourStage::DiagnoInter2,frame,true);
    check(wind_tail.completed_wind_stages()==2,
          "G18E6 did not route source MIXHTST-capped DIAGI into native INTER2");
    auto fake_wind_tail_frame=frame;
    rejects([&]{
        wind_tail.run_selected(
            p6::NativeHourStage::DiagnoWindbcPostInter2Htfac1,
            fake_wind_tail_frame,true);
    },"G18E6 accepted a detached G14 frame after INTER2");
    const auto first_ub=stages.wind_stages().original_ub_west_east_mps;
    const auto first_vb=stages.wind_stages().original_vb_south_north_mps;
    wind_tail.run_selected(
        p6::NativeHourStage::DiagnoWindbcPostInter2Htfac1,frame,true);
    check(wind_tail.completed_wind_stages()==3,
          "G18E6 source HTFAC=1 post-INTER2 WINDBC not staged");
    const auto& input=stages.selected_post_inter2_windbc();
    const auto& blend=stages.wind_stages();
    check(input.passes_per_layer==std::vector<int>(wind.nsmth.begin(),wind.nsmth.end()) &&
          input.u_mps==blend.blended_u.component_mps &&
          input.v_mps==blend.blended_v.component_mps,
          "G17D post-INTER2 stage used old step-one field or wrong NSMTH");
    for(std::size_t k=0;k<9;++k) {
        for(std::size_t j=0;j<12;++j) {
            const auto r=k*144+j*12;
            check(input.ub_west_east_mps[k*24+j]==input.u_mps[r] &&
                  input.ub_west_east_mps[k*24+12+j]==input.u_mps[r+11],
                  "G17D source second WINDBC U uses previous stage boundary");
        }
        for(std::size_t i=0;i<12;++i) {
            const auto r=k*144+i;
            check(input.vb_south_north_mps[k*24+i]==input.v_mps[r] &&
                  input.vb_south_north_mps[k*24+12+i]==input.v_mps[r+132],
                  "G17D source second WINDBC V uses previous stage boundary");
        }
    }
    rejects([&]{
        (void)stages.run(p6::NativeHourStage::DiagnoWindbcPostInter2Htfac1,frame);
    },"G17D duplicated post-INTER2 boundary before final W");
    wind_tail.run_selected(p6::NativeHourStage::DiagnoSmoothDivcelW,frame,true);
    check(wind_tail.completed_wind_stages()==4,
          "G18E6 final SMOOTH/DIVCEL/W not staged");
    const auto& tail=wind_tail.selected_wind_for_comp(frame);
    rejects([&]{
        (void)wind_tail.selected_wind_for_comp(fake_wind_tail_frame);
    },"G18E6 released final U/V/W through detached G14 frame");
    std::vector<float> dz;
    for(std::size_t k=0;k<9;++k)
        dz.push_back(wind.zface_m[k+1]-wind.zface_m[k]);
    const auto independent=p6::original_smooth_divcel_w(
        input,f.grid.grid_km*1000.f,f.grid.grid_km*1000.f,dz,false);
    check(tail.u_mps==independent.u_mps &&
          tail.v_mps==independent.v_mps &&
          tail.w_face_mps==independent.w_face_mps &&
          tail.divergence_per_s==independent.divergence_per_s &&
          tail.ub_west_east_mps==independent.ub_west_east_mps &&
          tail.vb_south_north_mps==independent.vb_south_north_mps,
          "G17D mismatch against frozen original CALMET SMOOTH/DIVCEL/W kernel");
    check(frame.fields.u_mps==tail.u_mps &&
          frame.fields.v_mps==tail.v_mps &&
          frame.fields.w_face_mps==tail.w_face_mps &&
          tail.w_face_mps.size()==144*10 &&
          tail.divergence_per_s.size()==144*9,
          "G17D output not connected to native current-hour U/V/W fields");
    for(std::size_t cell=0;cell<144;++cell)
        check(tail.w_face_mps[cell]==0.f,
              "G17D original W bottom boundary is nonzero");
    for(float x:tail.w_face_mps)
        check(std::isfinite(x),"G17D final source W contains nonfinite value");
    check(blend.original_ub_west_east_mps==first_ub &&
          blend.original_vb_south_north_mps==first_vb,
          "G17D overwrote original pre-INTER2 WINDBC provenance");
    rejects([&]{
        (void)stages.run(p6::NativeHourStage::DiagnoSmoothDivcelW,frame);
    },"G17D repeated mass segment in same source hour");
    p6g::G18ASelectedCompControls comp;
    comp.initial_wstar_mps.assign(144,0.f);
    auto& mix=comp.grid_mixht;
    mix.nx=12;mix.ny=12;
    mix.water_first=f.grid.iwat1;mix.water_last=f.grid.iwat2;
    mix.landuse=f.grid.landuse;
    mix.iupt=-1;
    p6g::g18d5_bind_original_mixht_scalars(source_metinp,comp);
    check(mix.imixh==1&&mix.izicrlx==1&&
          mix.constn==2400.f&&mix.zimin==50.f&&mix.zimax==3000.f&&
          mix.threshl==0.f&&mix.dptmin==.001f&&mix.dzzi==200.f&&
          mix.tzicrlx==800.f&&mix.timestep_s==3600&&
          mix.onedte==4140.f&&mix.twodte==1080.f,
          "G18D5 original met.inp/SETCOM COMP READCF scalar mismatch");
    const auto modified_source_constn=std::regex_replace(
        source_metinp,
        std::regex(R"(!\s*CONSTN\s*=\s*2400\.\s*!)",
                   std::regex_constants::icase),
        "! CONSTN = 2600. !");
    check(modified_source_constn!=source_metinp,
          "G18D5 original CONSTN not found in pinned source met.inp");
    auto modified_comp=comp;
    p6g::g18d5_bind_original_mixht_scalars(
        modified_source_constn,modified_comp);
    check(modified_comp.grid_mixht.constn==2600.f&&
          comp.grid_mixht.constn==2400.f,
          "G18D5 still hardcoded MIXHT CONSTN instead of reading source deck");
    rejects([&]{
        auto altered=comp;
        p6g::g18d5_bind_original_mixht_scalars(
            source_metinp+"\n! CONSTN = bogus !",altered);
    },"G18D5 tolerated duplicate/invalid source mixing coefficient");
    rejects([&]{
        auto altered=comp;
        p6g::g18d5_bind_original_mixht_scalars(
            source_metinp,altered,1800);
    },"G18D5 silently accepted unverified subhourly COMP relaxation");
    const auto choice=p6g::g18b3_source_deck_upper_choice(
        f.grid,all,source_metinp);
    check(choice.iupt==-1 && choice.nearu.size()==144 &&
          choice.nearu[diagi[0].cell]==1 &&
          choice.nearu[diagi[1].cell]==2,
          "G18B3 original-deck IUPT or US geometry selection mismatched");
    rejects([&]{
        p6g::g18b3_bind_test_only_upper_choice(
            mix,f.grid,all,choice,false);
    },"G18B3 allowed unverified NEARU into production");
    p6g::g18b3_bind_test_only_upper_choice(
        mix,f.grid,all,choice,true);
    p6g::G18BUpperBufferClock upper_clock;
    const auto observed_upper=upper_clock.select(frame);
    p6g::g18b_bind_physical_upper(mix,frame,observed_upper);
    check(observed_upper.station_ids==std::vector<int>({58424,58425}) &&
          observed_upper.justa==std::vector<int>({1,1}) &&
          observed_upper.physical_aa_index==std::vector<std::size_t>({0,0}) &&
          observed_upper.physical_bb_index==std::vector<std::size_t>({1,1}),
          "G18B first model-hour AA/BB source allocation mismatched");
    const auto uncommitted_again=upper_clock.select(frame);
    check(uncommitted_again.justa==observed_upper.justa &&
          !upper_clock.has_hour(),
          "G18B source AA/BB clock advanced before successful G14 hour");
    for(std::size_t site=0;site<diagi.size();++site)
        check(mix.nearu[diagi[site].cell]==static_cast<int>(site+1),
              "G18B3 geometry NEARU inconsistent with station MIXHTST ordinal");
    mix.fcori.assign(144,sc.fcori_s);
    mix.cmech.assign(144,sc.cmech);
    rejects([&]{
        (void)p6g::selected_comp_mixht_wstarr_from_previous(
            frame,selected,elustr,diagi,comp);
    },"G18A unmarked MIXHT controls could impersonate source COMP");
    comp.explicitly_test_only=true;
    // Actual G18A COMP consumes the G18E1 G14-stage station results,
    // not the independent direct-call G17C3 numerical oracle above.
    const auto calculated=p6g::selected_comp_mixht_with_observed_upper(
        frame,selected,elustr,stheor_stage.stations_for_comp(frame),
        observed_upper,comp);
    auto corrupt_source=observed_upper;
    corrupt_source.justa[1]=-1;
    rejects([&]{
        (void)p6g::selected_comp_mixht_with_observed_upper(
            frame,selected,elustr,diagi,corrupt_source,comp);
    },"G18B accepted stale JUSTA from a different source UP slot");
    corrupt_source=observed_upper;
    corrupt_source.physical_sounding[0][1].temp_k[0]+=5.f;
    rejects([&]{
        (void)p6g::selected_comp_mixht_with_observed_upper(
            frame,selected,elustr,diagi,corrupt_source,comp);
    },"G18B accepted fabricated same-ID AA thermal observation");
    const auto av_ctrl=p6g::g18c1_parse_original_avemix(source_metinp);
    check(av_ctrl.iavezi==1&&av_ctrl.ilevzi==1&&av_ctrl.mnmdav==1&&
          av_ctrl.hafang_deg==30.f,
          "G18C1 AVEMIX source controls must come from pinned met.inp");
    rejects([&]{
        (void)p6g::g18c1_selected_after_mixht(
            frame,calculated,av_ctrl,false);
    },"G18C1 accepted unsourced candidate ZI mixing as completed COMP");
    const auto averaged=p6g::g18c1_selected_after_mixht(
        frame,calculated,av_ctrl,true);
    check(averaged.zi_m.size()==144&&averaged.ziconv_m.size()==144,
          "G18C1 source AVEMIX failed after G18A MIXHT");
    for(std::size_t cell=0;cell<144;++cell)
        check(std::isfinite(averaged.zi_m[cell])&&
              std::isfinite(averaged.ziconv_m[cell])&&
              averaged.zi_m[cell]>=0.f&&averaged.ziconv_m[cell]>=0.f,
              "G18C1 AVEMIX invalid averaged heights");
    const auto original_zi=calculated.candidate_next.zi_m;
    const auto original_ziconv=calculated.candidate_next.ziconv_m;
    auto invalid_ctrl=av_ctrl;
    invalid_ctrl.iavezi=0;
    rejects([&]{
        (void)p6g::g18c1_selected_after_mixht(
            frame,calculated,invalid_ctrl,true);
    },"G18C1 accepted original CALMET IAVEZI=0 as averaged source");
    check(calculated.candidate_next.zi_m==original_zi&&
          calculated.candidate_next.ziconv_m==original_ziconv&&
          frame.next.ziconv_m==prior.ziconv_m,
          "G18C1 mutated pre-AVEMIX or previous-hour committed state");
    rejects([&]{
        (void)p6g::g18c2_wstarr_after_avemix(
            frame,calculated,averaged,selected,elustr,false);
    },"G18C2 promoted partial COMP result as accepted native hour");
    const auto final_conv=p6g::g18c2_wstarr_after_avemix(
        frame,calculated,averaged,selected,elustr,true);
    p6e::WstarrInput independent_conv;
    independent_conv.nx=12;independent_conv.ny=12;
    independent_conv.water_first=f.grid.iwat1;
    independent_conv.water_last=f.grid.iwat2;
    independent_conv.landuse=f.grid.landuse;
    independent_conv.zi_conv_m=averaged.ziconv_m;
    independent_conv.heat_flux_wm2=elustr.qh_wm2;
    independent_conv.temp_k=selected.temperature_k;
    independent_conv.rho_kgm3=selected.density_kg_m3;
    independent_conv.initial_wstar_ms.assign(144,0.f);
    const auto source_conv=p6e::wstarr(independent_conv);
    const auto temp_controls=p6g::g18c3_parse_original_temp3d_controls(
        source_metinp);
    check(temp_controls.lcalgrd&&temp_controls.itprog==0&&
          temp_controls.irad==1,
          "G18C3 actual source TEMP3D controls not selected");
    const auto source_faces=p6g::g18b5_selected_native_temperature_faces(
        frame,observed_upper);
    rejects([&]{
        (void)p6g::g18c3_selected_native_temp3d(
            frame,observed_upper,source_faces,selected,
            final_conv,temp_controls,false);
    },"G18C3 fixture TEMP3D falsely promoted to production CALMET");
    const auto selected_temp=p6g::g18c3_selected_native_temp3d(
        frame,observed_upper,source_faces,selected,
        final_conv,temp_controls,true);
    check(selected_temp.end==frame.input.end&&
          selected_temp.station_ids==std::vector<int>({58424,58425})&&
          selected_temp.temperature_k.size()==144*9,
          "G18C3 native multi-UP TEMP3D dimensions/clock invalid");
    p6e::Temp3dObservedInput independent_temperature;
    independent_temperature.nx=12;independent_temperature.ny=12;
    independent_temperature.nz=9;independent_temperature.irad=1;
    independent_temperature.dgrid_m=f.grid.grid_km*1000.f;
    independent_temperature.current_hour_utc=static_cast<int>(
        duration_cast<hours>(
            frame.input.end-floor<days>(frame.input.end)).count()%12);
    independent_temperature.face_z_m=source_faces.face_height_m;
    independent_temperature.justa=source_faces.justa;
    independent_temperature.past_seconds=source_faces.past_seconds;
    independent_temperature.to_go_seconds=source_faces.to_go_seconds;
    independent_temperature.aa_face_temp_k=source_faces.aa_face_k;
    independent_temperature.bb_face_temp_k=source_faces.bb_face_k;
    independent_temperature.surface_temp_k=selected.temperature_k;
    independent_temperature.convective_zi_m=final_conv.candidate_next.ziconv_m;
    for(const auto& st:all.upper) {
        independent_temperature.station_x_m.push_back(st.local_x_m);
        independent_temperature.station_y_m.push_back(st.local_y_m);
    }
    const auto expected_temp=p6e::temp3d_observed_land(independent_temperature);
    check(selected_temp.temperature_k==expected_temp,
          "G18C3 native 2UP TEMP3D differs from immutable PR #53 physical kernel");
    rejects([&]{
        (void)p6g::g18c4_assemble_selected_hour(
            frame,selected,elustr,final_conv,selected_temp,false);
    },"G18C4 allowed incomplete P6E fixture to impersonate a full G14 commit");
    const auto full_candidate=p6g::g18c4_assemble_selected_hour(
        frame,selected,elustr,final_conv,selected_temp,true);
    rejects([&]{
        (void)p6g::g18c5_selected_p6f_fields(
            frame,selected,full_candidate,source_metinp,false);
    },"G18C5 incomplete real P6F output impersonated native full 45 field output");
    const auto p6f_candidate=p6g::g18c5_selected_p6f_fields(
        frame,selected,full_candidate,source_metinp,true);
    rejects([&]{
        (void)p6g::g18c6_selected_one_hour_dataset(
            frame,p6f_candidate,selected.nearest_surface,source_metinp,false);
    },"G18C6 accepted selected G14 fixture as production original meteorology");
    const auto native_file=p6g::g18c6_selected_one_hour_dataset(
        frame,p6f_candidate,selected.nearest_surface,source_metinp,true);
    check(native_file.header.nssta==2&&native_file.header.nusta==2&&
          native_file.header.nx==12&&native_file.header.ny==12&&
          native_file.header.nz==9&&native_file.header.irlg==1&&
          native_file.hourly.size()==45&&
          native_file.statics.nears==
            std::vector<std::int32_t>(selected.nearest_surface.begin(),
                                      selected.nearest_surface.end())&&
          native_file.statics.zface_m==
            std::vector<float>(wind.zface_m.begin(),wind.zface_m.end())&&
          native_file.statics.z0_m==f.grid.z0_m&&
          native_file.statics.elev_m==f.grid.terrain_m&&
          native_file.statics.xlai==f.grid.lai,
          "G18C6 missing real 2SS/2US GEO and original ZFACE P6F statics");
    const auto bytes=cteas::p6f::serialize_calmet_dat21(native_file);
    // G18D1: read the native G18C4 field candidate into the SAME G14
    // source frame the authoritative scheduler would validate after all
    // 17 stages; no alternate time ownership or extra physics calculation.
    auto pending_g14=frame;
    pending_g14.next=full_candidate.candidate_memory;
    pending_g14.fields=full_candidate.candidate_fields;
    const auto precommitted=p6g::g18d1_validate_p6f_precommit(
        pending_g14,native_file);
    check(precommitted==bytes,
          "G18D1 G14 precommit writer bytes differed from original frozen P6F");
    auto contaminated=pending_g14;
    contaminated.fields.u_mps[0]+=0.5f;
    rejects([&]{
        (void)p6g::g18d1_validate_p6f_precommit(contaminated,native_file);
    },"G18D1 accepted MET.DAT U-field backfill not from current G14 physics");
    auto contaminated_zi=pending_g14;
    contaminated_zi.next.zi_m[0]+=25.f;
    rejects([&]{
        (void)p6g::g18d1_validate_p6f_precommit(contaminated_zi,native_file);
    },"G18D1 accepted stale pre-AVEMIX ZI instead of current COMP state");
    auto contaminated_w=pending_g14;
    contaminated_w.fields.w_face_mps[144]+=1.f;
    rejects([&]{
        (void)p6g::g18d1_validate_p6f_precommit(contaminated_w,native_file);
    },"G18D1 accepted wrong 3D WFACE top-face value");
    auto wrong_time_file=native_file;
    wrong_time_file.header.end_hour=(wrong_time_file.header.end_hour+1)%24;
    rejects([&]{
        (void)p6g::g18d1_validate_p6f_precommit(pending_g14,wrong_time_file);
    },"G18D1 published binary from wrong original model hour");
    auto wrong_static_file=native_file;
    wrong_static_file.statics.upper_x_m[0]+=100.f;
    rejects([&]{
        (void)p6g::g18d1_validate_p6f_precommit(pending_g14,wrong_static_file);
    },"G18D1 accepted substituted original upper-station metadata");
    const auto parsed=cteas::p6f::parse_calmet_dat21(bytes);
    check(parsed.header.irlg==1&&parsed.hourly.size()==45&&
          cteas::p6f::serialize_calmet_dat21(parsed)==bytes,
          "G18C6 frozen P6F writer did not roundtrip selected source binary");
    for(const auto& field:parsed.hourly) {
        if(field.integer) {
            check(field.integer_values==p6f_candidate.integer.at(field.label),
                  "G18C6 P6F binary lost original IPGT/IRH integer values");
        }else{
            check(field.real_values==p6f_candidate.real.at(field.label),
                  "G18C6 P6F binary changed an original meteorological value");
        }
    }
    if(!selected_output_file.empty()) {
        cteas::p6f::write_calmet_dat21(selected_output_file,native_file);
        const auto disk=cteas::p6f::read_calmet_dat21(selected_output_file);
        check(cteas::p6f::serialize_calmet_dat21(disk)==bytes,
              "G18C6 selected CALMET.DAT file differed from native writer memory");
    }
    auto invalid_p6f=p6f_candidate;
    invalid_p6f.real.erase("RHO     ");
    rejects([&]{
        (void)p6g::g18c6_selected_one_hour_dataset(
            frame,invalid_p6f,selected.nearest_surface,source_metinp,true);
    },"G18C6 silently restored missing RHO from MET.DAT");
    auto invalid_nears=selected.nearest_surface;
    invalid_nears[0]=3;
    rejects([&]{
        (void)p6g::g18c6_selected_one_hour_dataset(
            frame,p6f_candidate,invalid_nears,source_metinp,true);
    },"G18C6 accepted out-of-bounds original SETCOM nearest site");
    auto wrong_but_valid_nears=selected.nearest_surface;
    wrong_but_valid_nears[0]=selected.nearest_surface[0]==1?2:1;
    rejects([&]{
        (void)p6g::g18c6_selected_one_hour_dataset(
            frame,p6f_candidate,wrong_but_valid_nears,source_metinp,true);
    },"G18C6 accepted fabricated in-range NEARS instead of SETCOM geometry");
    auto wrong_site=p6f_candidate;
    std::swap(wrong_site.station_ids[0],wrong_site.station_ids[1]);
    rejects([&]{
        (void)p6g::g18c6_selected_one_hour_dataset(
            frame,wrong_site,selected.nearest_surface,source_metinp,true);
    },"G18C6 crossed original SS station ordinal metadata");
    const auto shifted_deck=std::regex_replace(
        source_metinp,std::regex(R"(!\s*IUTMZN\s*=\s*50\s*!)"),
        "! IUTMZN = 51 !");
    rejects([&]{
        (void)p6g::g18c6_selected_one_hour_dataset(
            frame,p6f_candidate,selected.nearest_surface,shifted_deck,true);
    },"G18C6 accepted mismatched source UTM zone");
    check(p6f_candidate.end==frame.input.end&&
          p6f_candidate.station_ids==std::vector<int>({58321,58322})&&
          p6f_candidate.real.size()==43&&p6f_candidate.integer.size()==2&&
          p6f_candidate.real.at("T-LEV  1")==
              std::vector<float>(selected_temp.temperature_k.begin(),
                                 selected_temp.temperature_k.begin()+144),
          "G18C5 invalid source 45-field record mapping");
    check(p6f_candidate.real.at("TEMPK   ")==selected.temperature_k&&
          p6f_candidate.real.at("RHO     ")==selected.density_kg_m3&&
          p6f_candidate.real.at("QSW     ")==selected.shortwave_wm2&&
          p6f_candidate.real.at("WFACE  1").size()==144&&
          p6f_candidate.real.at("WFACE  1")[0]==frame.fields.w_face_mps[144]&&
          p6f_candidate.real.at("ZI      ")==averaged.zi_m&&
          p6f_candidate.real.at("WSTAR   ")==final_conv.wstar_mps,
          "G18C5 source REAL*4 CALMET.DAT arrays not mapped by native ownership");
    p6e::PgtInput direct_pgt;
    direct_pgt.nx=12;direct_pgt.ny=12;direct_pgt.mcloud=1;
    direct_pgt.water_first=f.grid.iwat1;direct_pgt.water_last=f.grid.iwat2;
    direct_pgt.u10.assign(frame.fields.u_mps.begin(),
                          frame.fields.u_mps.begin()+144);
    direct_pgt.v10.assign(frame.fields.v_mps.begin(),
                          frame.fields.v_mps.begin()+144);
    direct_pgt.sinalp=selected.sun_sine;
    direct_pgt.nearest=selected.nearest_surface;
    direct_pgt.landuse=f.grid.landuse;
    direct_pgt.station_cloud={2,7};
    direct_pgt.station_ceil={150,75};
    direct_pgt.ccgrid.assign(144,0.f);
    direct_pgt.ceilgrid.assign(144,0);
    const auto frozen_pgt=p6e::pgtstb(direct_pgt);
    check(p6f_candidate.integer.at("IPGT    ")==
              std::vector<std::int32_t>(frozen_pgt.begin(),frozen_pgt.end()),
          "G18C5 original PGTSTB grid not reused");
    p6e::SurfvarMultistationInput direct_rh;
    direct_rh.nx=12;direct_rh.ny=12;direct_rh.dgrid_m=10000.f;
    direct_rh.irad=f.controls.source.irad;
    direct_rh.numts=f.controls.source.numts;
    direct_rh.trad_grid=f.controls.source.trad_km/10.f;
    direct_rh.stations={{10000.f,10000.f,281.f,60},
                        {100000.f,100000.f,302.f,73}};
    const auto source_rh=p6e::surfvar_multistation(direct_rh).rh2d_pct;
    check(p6f_candidate.integer.at("IRH     ")==
              std::vector<std::int32_t>(source_rh.begin(),source_rh.end()),
          "G18C5 original multi-station SURFVAR RH field not reused");
    const auto invalid_icloud=std::regex_replace(
        source_metinp,std::regex(R"(!\s*ICLOUD\s*=\s*0\s*!)",
                                std::regex_constants::icase),
        "! ICLOUD = 3 !");
    rejects([&]{
        (void)p6g::g18c5_selected_p6f_fields(
            frame,selected,full_candidate,invalid_icloud,true);
    },"G18C5 accepted unimplemented gridded CLOUD output as NWS observations");
    auto bad_heat=selected;
    bad_heat.shortwave_wm2.pop_back();
    rejects([&]{
        (void)p6g::g18c5_selected_p6f_fields(
            frame,bad_heat,full_candidate,source_metinp,true);
    },"G18C5 filled missing QSW from reference or omitted required field");
    // G18D4: run the SAME accepted COMP physical kernels only at their
    // exact original G14 stage boundary, never by directly shortcutting
    // the final four stage results from a prefilled fixture.
    auto staged_frame=frame;
    p6g::G18D4SelectedCompStageAdapter routed_comp(
        selected,elustr,stheor_stage.stations_for_comp(frame),
        observed_upper,comp,av_ctrl,temp_controls);
    check(!routed_comp.run(p6::NativeHourStage::CompGridMixht,
                           staged_frame).completed,
          "G18D4 fixture callback falsely certified production COMP");
    rejects([&]{
        routed_comp.run_selected(
            p6::NativeHourStage::CompAvemix,staged_frame,true);
    },"G18D4 AVEMIX ran before original MIXHT");
    rejects([&]{
        routed_comp.run_selected(
            p6::NativeHourStage::CompGridMixht,staged_frame,false);
    },"G18D4 test fixture COMP entered production G14 without scientific parity");
    routed_comp.run_selected(
        p6::NativeHourStage::CompGridMixht,staged_frame,true);
    check(!routed_comp.selected_complete()&&
          staged_frame.next.ziconv_m==prior.ziconv_m,
          "G18D4 MIXHT prematurely committed prior ZICONV");
    auto cloned_comp_frame=staged_frame;
    rejects([&]{
        routed_comp.run_selected(
            p6::NativeHourStage::CompAvemix,cloned_comp_frame,true);
    },"G18D4 accepted AVEMIX from a cloned, same-hour G14 frame");
    const float original_wind_u=staged_frame.fields.u_mps[0];
    staged_frame.fields.u_mps[0]=original_wind_u+1.f;
    rejects([&]{
        routed_comp.run_selected(
            p6::NativeHourStage::CompAvemix,staged_frame,true);
    },"G18D4 accepted mutated DIAGNO wind between COMP stages");
    staged_frame.fields.u_mps[0]=original_wind_u;
    const float original_pending_zi=staged_frame.next.zi_m[0];
    staged_frame.next.zi_m[0]=original_pending_zi+1.f;
    rejects([&]{
        routed_comp.run_selected(
            p6::NativeHourStage::CompAvemix,staged_frame,true);
    },"G18D4 accepted uncommitted MIXHT/COMP memory injected between stages");
    staged_frame.next.zi_m[0]=original_pending_zi;
    prior.zi_m[0]=original_prior_zi+1.f;
    rejects([&]{
        routed_comp.run_selected(
            p6::NativeHourStage::CompAvemix,staged_frame,true);
    },"G18D4 accepted external mutation of prior-hour memory");
    prior.zi_m[0]=original_prior_zi;
    rejects([&]{
        routed_comp.run_selected(
            p6::NativeHourStage::CompWstarr,staged_frame,true);
    },"G18D4 WSTARR executed before AVEMIX averaged ZICONV");
    routed_comp.run_selected(
        p6::NativeHourStage::CompAvemix,staged_frame,true);
    routed_comp.run_selected(
        p6::NativeHourStage::CompWstarr,staged_frame,true);
    check(!routed_comp.selected_complete()&&
          staged_frame.next.ziconv_m==prior.ziconv_m,
          "G18D4 partial COMP WSTARR mutated previous committed state");
    routed_comp.run_selected(
        p6::NativeHourStage::CompTemp3d,staged_frame,true);
    check(routed_comp.selected_complete()&&
          staged_frame.next.zi_m==full_candidate.candidate_memory.zi_m&&
          staged_frame.next.ziconv_m==full_candidate.candidate_memory.ziconv_m&&
          staged_frame.next.dptt_k==full_candidate.candidate_memory.dptt_k&&
          staged_frame.fields.u_mps==full_candidate.candidate_fields.u_mps&&
          staged_frame.fields.v_mps==full_candidate.candidate_fields.v_mps&&
          staged_frame.fields.w_face_mps==full_candidate.candidate_fields.w_face_mps&&
          staged_frame.fields.temperature_k==full_candidate.candidate_fields.temperature_k&&
          staged_frame.fields.qh_wm2==full_candidate.candidate_fields.qh_wm2&&
          staged_frame.fields.ustar_mps==full_candidate.candidate_fields.ustar_mps&&
          staged_frame.fields.el_m==full_candidate.candidate_fields.el_m&&
          staged_frame.fields.wstar_mps==full_candidate.candidate_fields.wstar_mps&&
          routed_comp.selected_candidate().end==frame.input.end,
          "G18D4 four real COMP-stage executions diverged from vetted G18C4 outputs");
    rejects([&]{
        routed_comp.run_selected(
            p6::NativeHourStage::CompTemp3d,staged_frame,true);
    },"G18D4 duplicated original COMP TEMP3D stage");
    check(frame.next.ziconv_m==prior.ziconv_m&&
          frame.next.zi_m==prior.zi_m,
          "G18D4 second stage executor contaminated original G14 previous state");
    check(full_candidate.end==frame.input.end&&
          full_candidate.candidate_fields.u_mps==frame.fields.u_mps&&
          full_candidate.candidate_fields.v_mps==frame.fields.v_mps&&
          full_candidate.candidate_fields.w_face_mps==frame.fields.w_face_mps&&
          full_candidate.candidate_fields.temperature_k==selected_temp.temperature_k&&
          full_candidate.candidate_fields.qh_wm2==elustr.qh_wm2&&
          full_candidate.candidate_fields.ustar_mps==elustr.ustar_mps&&
          full_candidate.candidate_fields.el_m==elustr.el_m&&
          full_candidate.candidate_fields.wstar_mps==final_conv.wstar_mps&&
          full_candidate.candidate_memory.zi_m==averaged.zi_m&&
          full_candidate.candidate_memory.ziconv_m==averaged.ziconv_m&&
          full_candidate.candidate_memory.dptt_k==calculated.candidate_next.dptt_k,
          "G18C4 did not preserve all frozen G14 field/memory components");
    auto broken_temp=selected_temp;
    broken_temp.temperature_k[0]=9999.f;
    rejects([&]{
        (void)p6g::g18c4_assemble_selected_hour(
            frame,selected,elustr,final_conv,broken_temp,true);
    },"G18C4 accepted incomplete P6F candidate 3D temperature");
    check(frame.next.zi_m==prior.zi_m&&
          frame.next.ziconv_m==prior.ziconv_m&&
          frame.next.dptt_k==prior.dptt_k,
          "G18C4 committed selected candidate despite incomplete G14/P6F");
    for(std::size_t idx=0;idx<144;++idx)
        check(selected_temp.temperature_k[idx]==selected.temperature_k[idx],
              "G18C3 original TEMP3D level-1 was not second SURFVAR TEMP2D");
    auto tampered_faces=source_faces;
    tampered_faces.aa_face_k[1]+=1.f;
    rejects([&]{
        (void)p6g::g18c3_selected_native_temp3d(
            frame,observed_upper,tampered_faces,selected,
            final_conv,temp_controls,true);
    },"G18C3 accepted fabricated same-hour upper FACET thermal contents");
    const auto wrong_temp=final_conv;
    auto stale_temp=wrong_temp;
    stale_temp.end+=hours{1};
    rejects([&]{
        (void)p6g::g18c3_selected_native_temp3d(
            frame,observed_upper,source_faces,selected,
            stale_temp,temp_controls,true);
    },"G18C3 accepted previous/future hour COMP mixing-height");
    check(final_conv.end==frame.input.end&&
          final_conv.candidate_next.zi_m==averaged.zi_m&&
          final_conv.candidate_next.ziconv_m==averaged.ziconv_m&&
          final_conv.candidate_next.dptt_k==calculated.candidate_next.dptt_k&&
          final_conv.wstar_mps==source_conv,
          "G18C2 failed original source AVEMIX->WSTARR ordering and DPTT preservation");
    auto wrong_avemix=averaged;
    wrong_avemix.ziconv_m.pop_back();
    rejects([&]{
        (void)p6g::g18c2_wstarr_after_avemix(
            frame,calculated,wrong_avemix,selected,elustr,true);
    },"G18C2 accepted incomplete source AVEMIX ZICONV field");
    check(frame.next.zi_m==prior.zi_m&&
          frame.next.ziconv_m==prior.ziconv_m&&
          frame.next.dptt_k==prior.dptt_k,
          "G18C2 prematurely committed source COMP candidate to G14");
    check(calculated.end==frame.input.end&&
          calculated.candidate_next.zi_m.size()==144&&
          calculated.candidate_next.ziconv_m.size()==144&&
          calculated.candidate_next.dptt_k.size()==144&&
          calculated.wstar_mps.size()==144,
          "G18A source-staged COMP MIXHT/WSTARR result incomplete");
    // Independent execution of the *unchanged* frozen P6E source
    // physics with the same explicitly selected 2-UP AA/BB/JUSTA inputs.
    auto direct_input=mix;
    direct_input.qh=elustr.qh_wm2;
    direct_input.ustar=elustr.ustar_mps;
    direct_input.el=elustr.el_m;
    direct_input.rho=selected.density_kg_m3;
    direct_input.initial_zi=prior.zi_m;
    direct_input.initial_ziconv=prior.ziconv_m;
    direct_input.initial_dptt=prior.dptt_k;
    for(const auto& st:diagi)
        direct_input.initial_dptt[st.cell]=st.station_mixing.dptt_for_comp_k;
    const auto expected_mix=p6e::mixht_observed_mc(direct_input);
    p6e::WstarrInput direct_wstar;
    direct_wstar.nx=12;direct_wstar.ny=12;
    direct_wstar.water_first=f.grid.iwat1;
    direct_wstar.water_last=f.grid.iwat2;
    direct_wstar.landuse=f.grid.landuse;
    direct_wstar.zi_conv_m=expected_mix.ziconv;
    direct_wstar.heat_flux_wm2=elustr.qh_wm2;
    direct_wstar.temp_k=selected.temperature_k;
    direct_wstar.rho_kgm3=selected.density_kg_m3;
    direct_wstar.initial_wstar_ms=comp.initial_wstar_mps;
    const auto expected_wstar=p6e::wstarr(direct_wstar);
    check(calculated.candidate_next.zi_m==expected_mix.zi &&
          calculated.candidate_next.ziconv_m==expected_mix.ziconv &&
          calculated.candidate_next.dptt_k==expected_mix.dptt &&
          calculated.wstar_mps==expected_wstar,
          "G18A differs from unchanged PR #53 MIXHT/WSTARR kernels");
    auto wrong_sources=comp;
    wrong_sources.grid_mixht.nearu[diagi[1].cell]=1;
    rejects([&]{
        (void)p6g::selected_comp_mixht_wstarr_from_previous(
            frame,selected,elustr,diagi,wrong_sources);
    },"G18A accepted station MIXHTST/COMP upper-sounding mismatch");
    auto bad_sites=diagi;
    bad_sites[1].cell=bad_sites[0].cell;
    rejects([&]{
        (void)p6g::selected_comp_mixht_wstarr_from_previous(
            frame,selected,elustr,bad_sites,comp);
    },"G18A accepted two SS MIXHTST writes into the same COMP cell");
    auto fake_fields=frame.fields;
    fake_fields.w_face_mps.clear();
    const p6g::MultiHourFrame fake_frame{
        0,f.grid,all,f.series.hourly.front(),slot,upper,
        &wind,prior,prior,std::move(fake_fields)};
    rejects([&]{
        (void)p6g::selected_comp_mixht_wstarr_from_previous(
            fake_frame,selected,elustr,diagi,comp);
    },"G18A used MIXHT without the source-complete DIAGNO W segment");
    check(frame.next.zi_m==prior.zi_m &&
          frame.next.ziconv_m==prior.ziconv_m &&
          frame.next.dptt_k==prior.dptt_k,
          "G18A prematurely committed fixture MIXHT to the G14 hourly scheduler");
    check(!stages.run(p6::NativeHourStage::CompGridMixht,frame).completed,
          "G18A misrepresented partial selected MIXHT as complete COMP");
    check(frame.next.ziconv_m==prior.ziconv_m,
          "G17C selected heat bridge modified n-1 accepted P6E state");
    // G18E7: unlike the detached G18D4 scientific comparator above,
    // this second independently executed 4-stage COMP physically consumes
    // the SAME live frame that ran all selected G18E2/E3/E5/E6 and G18E1
    // stage adapters. This closes the last DIAGNO -> COMP frame handoff.
    p6g::G18E7SelectedLiveCompStageAdapter live_comp(
        wind_tail,stheor_stage,heat_stage,thermal_stage,
        observed_upper,comp,av_ctrl,temp_controls);
    check(!live_comp.run(
              p6::NativeHourStage::CompGridMixht,frame).completed,
          "G18E7 selected live COMP falsely became production NativeCpp");
    rejects([&]{
        (void)live_comp.selected_candidate_for(frame);
    },"G18E7 released uncomputed COMP result");
    rejects([&]{
        live_comp.run_selected(
            p6::NativeHourStage::CompAvemix,frame,true);
    },"G18E7 accepted COMP AVEMIX without preceding source MIXHT");
    auto detached_live_frame=frame;
    rejects([&]{
        live_comp.run_selected(
            p6::NativeHourStage::CompGridMixht,detached_live_frame,true);
    },"G18E7 allowed copied DIAGNO frame to drive source COMP");
    rejects([&]{
        live_comp.run_selected(
            p6::NativeHourStage::CompGridMixht,frame,false);
    },"G18E7 promoted selected COMP fixture into production");
    live_comp.run_selected(p6::NativeHourStage::CompGridMixht,frame,true);
    const float saved_comp_u=frame.fields.u_mps[0];
    frame.fields.u_mps[0]+=1.f;
    rejects([&]{
        live_comp.run_selected(p6::NativeHourStage::CompAvemix,frame,true);
    },"G18E7 accepted altered G17D final DIAGNO wind for AVEMIX");
    frame.fields.u_mps[0]=saved_comp_u;
    const float saved_zi=prior.zi_m[0];
    prior.zi_m[0]+=1.f;
    rejects([&]{
        live_comp.run_selected(p6::NativeHourStage::CompAvemix,frame,true);
    },"G18E7 accepted modified immutable previous-hour mixing state");
    prior.zi_m[0]=saved_zi;
    live_comp.run_selected(p6::NativeHourStage::CompAvemix,frame,true);
    live_comp.run_selected(p6::NativeHourStage::CompWstarr,frame,true);
    rejects([&]{
        (void)live_comp.selected_candidate_for(frame);
    },"G18E7 released COMP candidate before original TEMP3D");
    live_comp.run_selected(p6::NativeHourStage::CompTemp3d,frame,true);
    const auto& live_candidate=live_comp.selected_candidate_for(frame);
    check(frame.fields.u_mps==full_candidate.candidate_fields.u_mps &&
          frame.fields.v_mps==full_candidate.candidate_fields.v_mps &&
          frame.fields.w_face_mps==full_candidate.candidate_fields.w_face_mps &&
          frame.fields.temperature_k==full_candidate.candidate_fields.temperature_k &&
          frame.fields.qh_wm2==full_candidate.candidate_fields.qh_wm2 &&
          frame.fields.ustar_mps==full_candidate.candidate_fields.ustar_mps &&
          frame.fields.el_m==full_candidate.candidate_fields.el_m &&
          frame.fields.wstar_mps==full_candidate.candidate_fields.wstar_mps &&
          frame.next.zi_m==full_candidate.candidate_memory.zi_m &&
          frame.next.ziconv_m==full_candidate.candidate_memory.ziconv_m &&
          frame.next.dptt_k==full_candidate.candidate_memory.dptt_k &&
          live_candidate.end==frame.input.end &&
          frame.previous.ziconv_m==prior.ziconv_m,
          "G18E7 live G14 DIAGNO -> COMP fields/memory differ from source kernel");
    rejects([&]{
        (void)live_comp.selected_candidate_for(detached_live_frame);
    },"G18E7 returned COMP result to detached earlier-hour frame");
    rejects([&]{
        live_comp.run_selected(p6::NativeHourStage::CompTemp3d,frame,true);
    },"G18E7 duplicated finished original COMP");
    // G18E8 completes the selected G14 original stage list's final
    // slot 16, using THIS frame (not pending_g14 or detached G18D4).
    // No publication occurs until the caller's scheduler precommit.
    p6g::G18E8SelectedP6fCommitStageAdapter final_output(
        live_comp,heat_stage,source_metinp);
    check(!final_output.run(p6::NativeHourStage::CommitOutput,frame).completed,
          "G18E8 fixture P6F output wrongly promoted to production");
    rejects([&]{
        (void)final_output.selected_bytes_for(frame);
    },"G18E8 exposed output before original slot 16");
    rejects([&]{
        final_output.run_selected(
            p6::NativeHourStage::CompTemp3d,frame,true);
    },"G18E8 accepted CommitOutput before original stage 16");
    rejects([&]{
        final_output.run_selected(
            p6::NativeHourStage::CommitOutput,frame,false);
    },"G18E8 allowed selected P6F fixture as production output");
    auto copied_output_frame=frame;
    rejects([&]{
        final_output.run_selected(
            p6::NativeHourStage::CommitOutput,copied_output_frame,true);
    },"G18E8 accepted a detached full-hour COMP frame");
    const float saved_output_qh=frame.fields.qh_wm2[0];
    frame.fields.qh_wm2[0]+=1.f;
    rejects([&]{
        final_output.run_selected(
            p6::NativeHourStage::CommitOutput,frame,true);
    },"G18E8 prepared P6F bytes after QH was changed after COMP");
    frame.fields.qh_wm2[0]=saved_output_qh;
    const float original_output_dptt=prior.dptt_k[0];
    prior.dptt_k[0]+=1.f;
    rejects([&]{
        final_output.run_selected(
            p6::NativeHourStage::CommitOutput,frame,true);
    },"G18E8 staged P6F from mutated previous-hour DPTT");
    prior.dptt_k[0]=original_output_dptt;
    final_output.run_selected(p6::NativeHourStage::CommitOutput,frame,true);
    const auto& exact_prepared=final_output.selected_bytes_for(frame);
    check(exact_prepared==bytes && exact_prepared==precommitted,
          "G18E8 live G14 slot-16 P6F differed from independent selected 45-field file");
    rejects([&]{
        (void)final_output.selected_bytes_for(copied_output_frame);
    },"G18E8 leaked current-hour bytes into cloned frame");
    const float original_output_zi=frame.next.zi_m[0];
    frame.next.zi_m[0]+=1.f;
    rejects([&]{
        (void)final_output.selected_bytes_for(frame);
    },"G18E8 P6F byte image survived mutation of pending COMP ZI");
    frame.next.zi_m[0]=original_output_zi;
    check(final_output.selected_bytes_for(frame)==bytes,
          "G18E8 prepared result was lost after a rejected, restored pending-state probe");
    rejects([&]{
        final_output.run_selected(p6::NativeHourStage::CommitOutput,frame,true);
    },"G18E8 allowed double output stage in the same G14 hour");
    check(frame.previous.ziconv_m==prior.ziconv_m &&
          frame.previous.dptt_k==prior.dptt_k,
          "G18E8 stage validation wrote previous-hour CALMET memory");

    // G18F6: run selected PREPDI -> DIAGNO -> COMP -> 45-field P6F on
    // the SAME G14 live frame, in all 17 original physical stage slots.
    // At slot 16 the test generates and checks real bytes, then returns
    // Unknown/false to prevent production admission of selected fixtures.
    struct PhysicalTrace {
        bool prepdi=false,wind1=false,fradj=false;
        bool heatfx=false,airden=false,elustr=false,slope=false;
        bool windbc1=false,stheor=false,inter2=false,windbc2=false,wind3d=false;
        bool mixht=false,avemix=false,wstarr=false,temp3d=false,p6f=false;
        p6::NativeHourStage first_missing=
            p6::NativeHourStage::PrepdiPreviousZiconv;
        std::vector<float> wind1_u,wind1_v,fradj_u,fradj_v,temp2d;
        std::vector<float> heat_qh,air_density,elustr_qh,slope_u,slope_v;
        std::vector<float> final_u,final_v,final_w;
        p6::NativeHourFields final_fields;
        p6::NativeGridMemory final_memory;
        std::vector<std::uint8_t> p6f_bytes;
    } physical_trace;
    struct G18F3PartialSelectedExecutor final : p6g::MultiHourPhysics {
        p6g::G18E4SelectedPrepdiStageAdapter prepdi;
        p6g::G17SelectedTerrainFixturePhysics physics;
        p6g::G17B4TwoPassSurfvar two_pass;
        p6g::G18E2SelectedHeatfxStageAdapter heatfx;
        p6g::G18E3SelectedAirdenElustrStageAdapter thermal;
        p6g::G18E5SelectedSlopeStageAdapter slope_stage;
        p6g::G18E6SelectedWindTailStageAdapter wind_tail;
        std::optional<p6g::G18E1SelectedStheorStageAdapter> stheor_stage;
        std::optional<p6g::G18E7SelectedLiveCompStageAdapter> comp_stage;
        std::optional<p6g::G18E8SelectedP6fCommitStageAdapter> p6f_stage;
        p6g::G16ObservedProfiles original_profiles;
        p6g::G17C3StationControls station_controls;
        p6g::G18ASelectedCompControls comp_controls;
        p6g::G18C1AvemixControls avemix;
        p6g::G18C3Temp3dControls temp3d;
        std::string source_deck;
        const p6g::MultiHourFrame* live;
        PhysicalTrace& trace;
        G18F3PartialSelectedExecutor(
            const p6g::UnifiedMultistationHourlyScheduler& scheduler,
            p6g::G18D2StationClockAuthority& clocks,
            const std::string& deck,
            const p6g::MultiHourFrame& source_frame,
            const p6g::SurfaceSeries& source_surface,
            const p6g::G17B4SurfaceControls& surf_controls,
            const p6g::G16ObservedProfiles& native_profiles,
            const p6g::TerrainStaticG11& static_terrain,
            const p6g::G17FradjSource& source_fradj,
            const p6g::G17CSelectedHeatInputs& heat_inputs,
            const p6g::G17C2SelectedElustrControls& elustr_controls,
            const p6g::G17C3StationControls& original_station_controls,
            const p6g::G18ASelectedCompControls& original_comp_controls,
            const p6g::G18C1AvemixControls& source_avemix,
            const p6g::G18C3Temp3dControls& source_temp3d,
            PhysicalTrace& captured)
            :prepdi(scheduler,clocks,deck),
             physics(native_profiles,static_terrain,source_fradj),
             two_pass(source_frame.grid,source_frame.stations,
                      source_surface,source_frame.surface,surf_controls),
             heatfx(physics,two_pass,heat_inputs),
             thermal(physics,heatfx,two_pass,elustr_controls),
             slope_stage(physics,heatfx,thermal),
             wind_tail(physics,slope_stage),
             original_profiles(native_profiles),
             station_controls(original_station_controls),
             comp_controls(original_comp_controls),
             avemix(source_avemix),temp3d(source_temp3d),
             source_deck(deck),
             live(&source_frame),trace(captured) {
            physics.provide_selected_readge_htfac_fixture(1.f,true);
        }
        p6::NativeHourStageResult run(
            p6::NativeHourStage stage,p6g::MultiHourFrame& hour) override {
            check(&hour==live,
                  "G18F3 actual native physics did not receive live G14 frame");
            if(stage==p6::NativeHourStage::PrepdiPreviousZiconv) {
                // Synthetic acceptance wrapper ONLY for testing that
                // real G18E4 source candidates reach the following
                // G17 physical kernels. Not a production PREPDI claim.
                prepdi.run_selected(stage,hour,true);
                prepdi.require_publishable_before_g14_commit(hour);
                trace.prepdi=true;
                return {p6::NativeHourSource::NativeCpp,true};
            }
            if(stage==p6::NativeHourStage::DiagnoWind1) {
                const auto result=physics.run(stage,hour);
                physics.prepare_original_iavet1_before_fradj(two_pass);
                trace.wind1_u=physics.wind_stages().first_guess.u_mps;
                trace.wind1_v=physics.wind_stages().first_guess.v_mps;
                trace.wind1=true;
                return result;
            }
            if(stage==p6::NativeHourStage::DiagnoFradj) {
                const auto result=physics.run(stage,hour);
                physics.finish_original_iavet1_after_fradj(two_pass);
                trace.fradj_u=physics.after_fradj().u;
                trace.fradj_v=physics.after_fradj().v;
                trace.temp2d=two_pass.final_temperature();
                trace.fradj=true;
                return result;
            }
            // The G18E2/E3/E5 selected adapters reuse existing frozen
            // native kernels. Synthetic admission here is TEST-ONLY;
            // do not use these returns as production parity evidence.
            if(stage==p6::NativeHourStage::DiagnoHeatfx) {
                heatfx.run_selected(stage,hour,true);
                trace.heat_qh=heatfx.selected_heat_for(hour).sensible_heat_wm2;
                trace.heatfx=true;
                return {p6::NativeHourSource::NativeCpp,true};
            }
            if(stage==p6::NativeHourStage::DiagnoAirden) {
                thermal.run_selected(stage,hour,true);
                trace.air_density=physics.selected_air_density();
                trace.airden=true;
                return {p6::NativeHourSource::NativeCpp,true};
            }
            if(stage==p6::NativeHourStage::DiagnoElustr) {
                thermal.run_selected(stage,hour,true);
                trace.elustr_qh=thermal.selected_elustr_for(hour).qh_wm2;
                trace.elustr=true;
                return {p6::NativeHourSource::NativeCpp,true};
            }
            if(stage==p6::NativeHourStage::DiagnoSlope) {
                slope_stage.run_selected(stage,hour,true);
                const auto& w=slope_stage.selected_slope_wind_for(hour);
                trace.slope_u=w.u;trace.slope_v=w.v;
                trace.slope=true;
                return {p6::NativeHourSource::NativeCpp,true};
            }
            if(stage==p6::NativeHourStage::DiagnoWindbcFirstGuess) {
                wind_tail.run_selected(stage,hour,true);
                trace.windbc1=true;
                return {p6::NativeHourSource::NativeCpp,true};
            }
            if(stage==p6::NativeHourStage::DiagnoStheorElustr2Mixhtst) {
                stheor_stage.emplace(
                    physics,original_profiles,two_pass,
                    heatfx.selected_heat_for(hour),station_controls);
                stheor_stage->run_selected(stage,hour,true);
                wind_tail.bind_stheor_stage(*stheor_stage,hour,true);
                trace.stheor=true;
                return {p6::NativeHourSource::NativeCpp,true};
            }
            if(stage==p6::NativeHourStage::DiagnoInter2 ||
               stage==p6::NativeHourStage::DiagnoWindbcPostInter2Htfac1 ||
               stage==p6::NativeHourStage::DiagnoSmoothDivcelW) {
                wind_tail.run_selected(stage,hour,true);
                if(stage==p6::NativeHourStage::DiagnoInter2)
                    trace.inter2=true;
                else if(stage==p6::NativeHourStage::DiagnoWindbcPostInter2Htfac1)
                    trace.windbc2=true;
                else {
                    trace.wind3d=true;
                    trace.final_u=hour.fields.u_mps;
                    trace.final_v=hour.fields.v_mps;
                    trace.final_w=hour.fields.w_face_mps;
                }
                return {p6::NativeHourSource::NativeCpp,true};
            }
            if(stage==p6::NativeHourStage::CompGridMixht ||
               stage==p6::NativeHourStage::CompAvemix ||
               stage==p6::NativeHourStage::CompWstarr ||
               stage==p6::NativeHourStage::CompTemp3d) {
                if(stage==p6::NativeHourStage::CompGridMixht) {
                    if(!stheor_stage || !stheor_stage->selected_complete())
                        throw std::logic_error(
                            "G18F6 COMP has no G14 STHEOR station profiles");
                    comp_stage.emplace(
                        wind_tail,*stheor_stage,heatfx,thermal,
                        prepdi.selected_upper_for(hour),comp_controls,
                        avemix,temp3d);
                }
                comp_stage->run_selected(stage,hour,true);
                if(stage==p6::NativeHourStage::CompGridMixht)trace.mixht=true;
                if(stage==p6::NativeHourStage::CompAvemix)trace.avemix=true;
                if(stage==p6::NativeHourStage::CompWstarr)trace.wstarr=true;
                if(stage==p6::NativeHourStage::CompTemp3d) {
                    trace.temp3d=true;
                    trace.final_fields=hour.fields;
                    trace.final_memory=hour.next;
                }
                return {p6::NativeHourSource::NativeCpp,true};
            }
            if(stage==p6::NativeHourStage::CommitOutput) {
                if(!comp_stage)
                    throw std::logic_error("G18F6 P6F has no G14 COMP");
                p6f_stage.emplace(*comp_stage,heatfx,source_deck);
                p6f_stage->run_selected(stage,hour,true);
                trace.p6f_bytes=p6f_stage->selected_bytes_for(hour);
                trace.p6f=true;
                trace.first_missing=stage;
                // No production elevation: fixture-only 45-field binary
                // must fail the real G14 NativeCpp admission gate.
                return {p6::NativeHourSource::Unknown,false};
            }
            trace.first_missing=stage;
            return {p6::NativeHourSource::Unknown,false};
        }
    };
    p6g::UnifiedMultistationHourlyScheduler fresh_owner(
        f.grid,all,f.series,upper,wind);
    p6g::G18D2StationClockAuthority fresh_station_clocks;
    std::size_t fresh_attempts=0;
    rejects([&]{
        fresh_owner.advance_with_fresh_physics(
            [&](const p6g::MultiHourFrame& live)
                ->std::unique_ptr<p6g::MultiHourPhysics> {
                ++fresh_attempts;
                return std::make_unique<G18F3PartialSelectedExecutor>(
                    fresh_owner,fresh_station_clocks,source_metinp,
                    live,f.series,controls,initial_profiles,terrain,
                    fresh_g14_fradj_source,ancillary,ec,sc,
                    comp,av_ctrl,temp_controls,physical_trace);
            });
    },"G18F3 allowed partial selected physical CALMET as a full G14 hour");
    check(fresh_attempts==1 && physical_trace.prepdi &&
          physical_trace.wind1 && physical_trace.fradj &&
          physical_trace.heatfx && physical_trace.airden &&
          physical_trace.elustr && physical_trace.slope &&
          physical_trace.windbc1 && physical_trace.stheor &&
          physical_trace.inter2 && physical_trace.windbc2 &&
          physical_trace.wind3d &&
          physical_trace.mixht && physical_trace.avemix &&
          physical_trace.wstarr && physical_trace.temp3d &&
          physical_trace.p6f &&
          physical_trace.first_missing==
              p6::NativeHourStage::CommitOutput &&
          physical_trace.wind1_u==stages.wind_stages().first_guess.u_mps &&
          physical_trace.wind1_v==stages.wind_stages().first_guess.v_mps &&
          physical_trace.fradj_u==stages.after_fradj().u &&
          physical_trace.fradj_v==stages.after_fradj().v &&
          physical_trace.temp2d==surface.final_temperature() &&
          physical_trace.heat_qh==selected.sensible_heat_wm2 &&
          physical_trace.air_density==selected.density_kg_m3 &&
          physical_trace.elustr_qh==elustr.qh_wm2 &&
          physical_trace.slope_u==stages.after_slope().u &&
          physical_trace.slope_v==stages.after_slope().v &&
          physical_trace.final_u==frame.fields.u_mps &&
          physical_trace.final_v==frame.fields.v_mps &&
          physical_trace.final_w==frame.fields.w_face_mps &&
          physical_trace.final_fields.u_mps==full_candidate.candidate_fields.u_mps &&
          physical_trace.final_fields.v_mps==full_candidate.candidate_fields.v_mps &&
          physical_trace.final_fields.w_face_mps==full_candidate.candidate_fields.w_face_mps &&
          physical_trace.final_fields.temperature_k==full_candidate.candidate_fields.temperature_k &&
          physical_trace.final_fields.qh_wm2==full_candidate.candidate_fields.qh_wm2 &&
          physical_trace.final_fields.ustar_mps==full_candidate.candidate_fields.ustar_mps &&
          physical_trace.final_fields.el_m==full_candidate.candidate_fields.el_m &&
          physical_trace.final_fields.wstar_mps==full_candidate.candidate_fields.wstar_mps &&
          physical_trace.final_memory.zi_m==full_candidate.candidate_memory.zi_m &&
          physical_trace.final_memory.ziconv_m==full_candidate.candidate_memory.ziconv_m &&
          physical_trace.final_memory.dptt_k==full_candidate.candidate_memory.dptt_k &&
          physical_trace.p6f_bytes==bytes &&
          physical_trace.p6f_bytes==precommitted &&
          fresh_owner.completed_hours()==0 &&
          !fresh_station_clocks.has_published_hour() &&
          fresh_owner.committed_memory().ziconv_m==prior.ziconv_m,
          "G18F6 fresh G14 full selected 45-field P6F differs from source or wrongly admitted fixture hour");
}
static void verify_g18b_asynchronous_upper_turnover(
    const std::string& source_metinp) {
    const auto begin=sys_days{year{2024}/December/31}+hours{18};
    p6g::StationSet sites;
    sites.surface={station(58321,10000.f,10000.f),
                   station(58322,30000.f,30000.f)};
    sites.upper={station(58424,20000.f,20000.f),
                 station(58425,40000.f,40000.f)};
    p6g::GeoGrid grid;
    grid.nx=12;grid.ny=12;grid.zone=50;grid.hemisphere='N';
    grid.grid_km=10.f;grid.landuse.assign(144,20);
    p6g::SurfaceSeries surf;
    surf.begin=begin;surf.end=begin+hours{30};
    surf.station_ids={58321,58322};
    for(int h=0;h<30;++h){
        p6g::SurfaceHour sh;
        sh.start=begin+hours{h};sh.end=sh.start+hours{1};
        sh.by_station.resize(2);
        surf.hourly.push_back(sh);
    }
    std::vector<p6g::UpperSeries> upper(2);
    for(int site=0;site<2;++site){
        auto& row=upper[static_cast<std::size_t>(site)];
        row.station_id=site?58425:58424;
        const int offset=site?-8:-12;
        for(int h=offset;h<52;h+=12){
            p6::UpperSounding profile;
            profile.station_id=row.station_id;
            profile.start=begin+hours{h};profile.end=profile.start;
            for(int k=0;k<4;++k){
                p6::UpperLevel level;
                level.height_valid=true;level.temperature_valid=true;
                level.height_lgl_m=500.f*static_cast<float>(k);
                level.temperature_k=280.f+static_cast<float>(site*10+h/12+k);
                profile.data.push_back(level);
            }
            row.soundings.push_back(std::move(profile));
        }
    }
    const auto input=p6g::bind_original_calmet_station_inputs(sites,surf,upper);
    check(input.size()==30,"G18B cross-year station inputs truncated");
    p6g::OriginalWindControls controls;
    for(std::size_t k=0;k<10;++k)
        controls.zface_m[k]=static_cast<float>(k*100);
    p6::NativeGridMemory prior;
    prior.zi_m.assign(144,0.f);
    prior.ziconv_m.assign(144,0.f);
    prior.dptt_k.assign(144,0.f);
    p6g::G18BUpperBufferClock clock;
    p6g::G18B4CGammaClock gamma_clock;
    const auto gamma_controls=p6g::g18b9_parse_original_gamma_controls(
        source_metinp,sites.upper.size());
    check(gamma_controls.iupt==-1&&gamma_controls.idiopt2==0&&
          gamma_controls.zupt_m==200.f,
          "G18B9 original model controls not read from met.inp");
    const auto gamma_near_choice=p6g::g18b3_source_deck_upper_choice(
        grid,sites,source_metinp);
    auto gamma_fixed_choice=gamma_near_choice;
    gamma_fixed_choice.iupt=2;
    std::vector<p6::CGammaState> independent_gamma(2);
    bool saw_cgamma_conv=false,saw_cgamma_retained=false;
    bool saw_different_turnover=false,saw_negative_justa=false;
    for(std::size_t h=0;h<input.size();++h){
        prior.ziconv_m.assign(144,0.f);
        if(h==1) {
            const auto first=p6::upper_reference_cell(
                {sites.upper[0].local_x_m,sites.upper[0].local_y_m},
                grid.nx,grid.ny,grid.grid_km*1000.f);
            prior.ziconv_m[static_cast<std::size_t>(first.j-1)*grid.nx+
                           static_cast<std::size_t>(first.i-1)]=300.f;
        }
        const p6g::MultiHourFrame frame{
            h,grid,sites,surf.hourly[h],input[h],upper,&controls,prior,prior,{}};
        if(h==8){
            auto bad_upper=upper;
            bad_upper[1].soundings[input[h].upper[1].later].station_id=12345;
            const p6g::MultiHourFrame bad{
                h,grid,sites,surf.hourly[h],input[h],bad_upper,
                &controls,prior,prior,{}};
            rejects([&]{(void)clock.select(bad);},
                    "G18B advanced first upper on second-station failure");
        }
        const auto observed=clock.select(frame);
        check(observed.end==input[h].end &&
              observed.justa.size()==2 &&
              observed.source_reads.size()==2 &&
              (h!=0||!clock.has_hour()),
              "G18B model-hour source preparation invalid");
        const auto faces=p6g::g18b5_selected_native_temperature_faces(
            frame,observed);
        check(faces.end==frame.input.end&&
              faces.aa_face_k.size()==20&&faces.bb_face_k.size()==20&&
              faces.justa==observed.justa&&faces.station_ids==observed.station_ids,
              "G18B5 physical AA/BB frozen FACET dimensions/identity mismatch");
        auto empty=p6e::MixhtObservedMcInput{};
        p6g::g18b_bind_physical_upper(empty,frame,observed);
        check(empty.justa==observed.justa &&
              empty.sounding[0].size()==2 &&
              empty.sounding[1].size()==2,
              "G18B failed frozen MIXHT physical AA/BB array binding");
        for(std::size_t site=0;site<2;++site) {
            const auto earlier=input[h].upper[site].earlier;
            const auto later=input[h].upper[site].later;
            const auto sign=(earlier%2==0)?1:-1;
            check(observed.justa[site]==sign &&
                  observed.chronological_older[site]==earlier &&
                  observed.chronological_newer[site]==later &&
                  observed.turnovers[site]==static_cast<int>(earlier) &&
                  observed.source_reads[site]==static_cast<int>(later+1) &&
                  observed.physical_aa_index[site]==(sign>0?earlier:later) &&
                  observed.physical_bb_index[site]==(sign>0?later:earlier),
                  "G18B source independent upper buffer turnover parity failed");
            const auto aa=observed.physical_aa_index[site];
            const auto bb=observed.physical_bb_index[site];
            check(empty.sounding[0][site].temp_k[0]==
                      upper[site].soundings[aa].data[0].temperature_k &&
                  empty.sounding[1][site].temp_k[0]==
                      upper[site].soundings[bb].data[0].temperature_k,
                  "G18B physical AA/BB thermal data crossed upper station");
            const auto physical_aa=p6::calmet_facet_temperatures(
                upper[site].soundings[aa],faces.face_height_m);
            const auto physical_bb=p6::calmet_facet_temperatures(
                upper[site].soundings[bb],faces.face_height_m);
            for(std::size_t k=0;k<10;++k)
                check(faces.aa_face_k[site*10+k]==physical_aa[k]&&
                      faces.bb_face_k[site*10+k]==physical_bb[k],
                      "G18B5 different original FACET temperature due to source UP ordering");
            saw_negative_justa|=sign<0;
        }
        if(h==4) {
            auto invalid_controls=controls;
            invalid_controls.zface_m[8]=-1.f;
            const p6g::MultiHourFrame invalid_face{
                h,grid,sites,surf.hourly[h],input[h],upper,
                &invalid_controls,prior,prior,{}};
            rejects([&]{
                (void)p6g::g18b5_selected_native_temperature_faces(
                    invalid_face,observed);
            },"G18B5 silently accepted malformed original layer geometry");
        }
        // The source CGAMMA kernel is original #53; each US retains its own
        // convective history, but no state may commit before G14 completes.
        const std::vector<float> station_previous_ziconv{
            h==1?300.f:0.f,0.f};
        const auto sampled=p6g::g18b7_source_previous_station_ziconv(
            frame,observed);
        check(sampled==station_previous_ziconv,
              "G18B7 previous-ZICONV must sample source IIUP/JJUP per US");
        if(h==4){
            auto modified=sites;
            std::swap(modified.upper[0],modified.upper[1]);
            const p6g::MultiHourFrame bad{
                h,grid,modified,surf.hourly[h],input[h],upper,
                &controls,prior,prior,{}};
            rejects([&]{
                (void)p6g::g18b7_source_previous_station_ziconv(bad,observed);
            },"G18B7 accepted swapped upper stations with stale prior sampling");
        }
        rejects([&]{
            (void)gamma_clock.prepare(
                frame,observed,station_previous_ziconv,200.f,false);
        },"G18B4 accepted unsourced CGAMMA controls as production");
        if(h==8) {
            rejects([&]{
                (void)gamma_clock.prepare(
                    frame,observed,{0.f},200.f,true);
            },"G18B4 accepted incomplete 2US previous ZICONV");
        }
        rejects([&]{
            (void)p6g::g18b9_selected_original_hour_gamma(
                gamma_clock,frame,observed,gamma_near_choice,gamma_controls,false);
        },"G18B9 promoted test-only source CGAMMA to production");
        const auto selected_gamma=p6g::g18b9_selected_original_hour_gamma(
            gamma_clock,frame,observed,gamma_near_choice,gamma_controls,true);
        const auto& gamma=selected_gamma.upper;
        check(selected_gamma.grid.end==frame.input.end&&
              selected_gamma.grid.original_iupt==gamma_controls.iupt&&
              selected_gamma.grid.gamma_k_per_m.size()==144,
              "G18B9 original-deck CGAMMA→GAMMA source control handoff failed");
        check(gamma.end==frame.input.end&&
              gamma.station_ids==std::vector<int>({58424,58425})&&
              gamma.lapse.size()==2,
              "G18B4 per-upper source CGAMMA station state absent");
        rejects([&]{
            (void)p6g::g18b8_source_gamma_from_hour(
                frame,gamma_near_choice,gamma,false);
        },"G18B8 unmarked selected gamma field impersonated native PREPDI");
        const auto spatial=p6g::g18b8_source_gamma_from_hour(
            frame,gamma_near_choice,gamma,true);
        check(spatial.gamma_k_per_m==selected_gamma.grid.gamma_k_per_m,
              "G18B9 independently source-parsed GAMMA differs from G18B8");
        const auto uniform=p6g::g18b8_source_gamma_from_hour(
            frame,gamma_fixed_choice,gamma,true);
        check(spatial.end==frame.input.end&&
              spatial.gamma_k_per_m.size()==144&&
              spatial.upper_station_ids==std::vector<int>({58424,58425})&&
              spatial.original_iupt==-1&&
              uniform.original_iupt==2&&
              uniform.gamma_k_per_m.size()==144,
              "G18B8 source CGAMMA→grid GAMMA provenance or shape invalid");
        const auto first=gamma.lapse[0].kelvin_per_m;
        const auto second=gamma.lapse[1].kelvin_per_m;
        const auto min_lapse=std::min(first,second);
        const auto max_lapse=std::max(first,second);
        for(std::size_t k=0;k<144;++k) {
            check(uniform.gamma_k_per_m[k]==second,
                  "G18B8 IUPT>0 did not broadcast source specified US GAMUP");
            const auto source=spatial.gamma_k_per_m[k];
            check(std::isfinite(source)&&source>=min_lapse-1.e-8f&&
                  source<=max_lapse+1.e-8f,
                  "G18B8 original inverse-distance lapse exceeded station bounds");
        }
        if(h==4){
            auto stale=gamma;
            stale.end+=hours{1};
            rejects([&]{
                (void)p6g::g18b8_source_gamma_from_hour(
                    frame,gamma_near_choice,stale,true);
            },"G18B8 allowed GAMMA from another source hour");
            auto shuffled=gamma;
            std::swap(shuffled.station_ids[0],shuffled.station_ids[1]);
            rejects([&]{
                (void)p6g::g18b8_source_gamma_from_hour(
                    frame,gamma_near_choice,shuffled,true);
            },"G18B8 crossed independent CGAMMA upper-station identities");
            auto invalid=gamma;
            invalid.lapse[1].kelvin_per_m=
                std::numeric_limits<float>::quiet_NaN();
            rejects([&]{
                (void)p6g::g18b8_source_gamma_from_hour(
                    frame,gamma_near_choice,invalid,true);
            },"G18B8 accepted invalid REAL4 upper-station lapse");
        }
        for(std::size_t us=0;us<2;++us) {
            p6::Upper2022 direct;
            direct.station_id=upper[us].station_id;
            direct.soundings={
                upper[us].soundings[input[h].upper[us].earlier],
                upper[us].soundings[input[h].upper[us].later]};
            p6::CompBufferedHour hour;
            hour.aa_profile=0;hour.bb_profile=1;
            hour.jorder=observed.justa[us];
            hour.interpolated.end=input[h].end;
            hour.interpolated.gap_seconds=observed.gap_seconds[us];
            hour.interpolated.to_go_seconds=observed.to_go_seconds[us];
            const auto expected=independent_gamma[us].calculate(
                direct,hour,gamma_controls.zupt_m,station_previous_ziconv[us]);
            check(gamma.lapse[us].branch==expected.branch &&
                  gamma.lapse[us].kelvin_per_m==expected.kelvin_per_m,
                  "G18B4 frozen CGAMMA numerical/branch parity mismatch");
        }
        if(h==1) {
            check(gamma.lapse[0].branch==1&&
                  gamma.lapse[1].branch==0,
                  "G18B4 first US CGAMMA convection leaked into second US");
            saw_cgamma_conv=true;
        }
        if(h==2) {
            check(gamma.lapse[0].branch==2&&
                  gamma.lapse[1].branch==0,
                  "G18B4 retained CGAMMA history not independent per UP");
            saw_cgamma_retained=true;
        }
        rejects([&]{
            gamma_clock.commit_after_completed_g14_hour(gamma,h);
        },"G18B4 committed convective history before accepted G14 hour");
        const auto repeated=gamma_clock.prepare(
            frame,observed,station_previous_ziconv,
            gamma_controls.zupt_m,true);
        check(repeated.lapse[0].kelvin_per_m==gamma.lapse[0].kelvin_per_m,
              "G18B4 failed atomic candidate retry after later COMP failure");
        rejects([&]{
            clock.commit_after_completed_g14_hour(frame,observed,h);
        },"G18B accepted a source cache commit before G14 completed this hour");
        const auto second_prepare=clock.select(frame);
        check(second_prepare.justa==observed.justa,
              "G18B failed to retry the same source hour after later COMP failure");
        clock.commit_after_completed_g14_hour(frame,observed,h+1);
        gamma_clock.commit_after_completed_g14_hour(gamma,h+1);
        check(gamma_clock.committed_end()==input[h].end,
              "G18B4 frozen CGAMMA prior state not committed after G14 hour");
        rejects([&]{
            gamma_clock.commit_after_completed_g14_hour(gamma,h+1);
        },"G18B4 accepted duplicate current-hour CGAMMA state");
        check(clock.last_hour()==input[h].end,
              "G18B successful G14 hour did not advance source AA/BB clock");
        rejects([&]{
            clock.commit_after_completed_g14_hour(frame,observed,h+1);
        },"G18B accepted a duplicate already committed G14 hour");
        saw_different_turnover|=observed.chronological_older[0]!=
                                observed.chronological_older[1];
    }
    check(saw_cgamma_conv&&saw_cgamma_retained,
          "G18B4 did not exercise both current and retained convective history");
    check(saw_different_turnover&&saw_negative_justa &&
          input.front().end<sys_days{year{2025}/January/1} &&
          input.back().end>sys_days{year{2025}/January/1},
          "G18B did not test asynchronous multi-UP rollover and cross-year clock");
}
static void verify_g18b3_source_iupt_choice(const std::string& deck) {
    p6g::GeoGrid grid;grid.nx=2;grid.ny=2;grid.grid_km=10.f;
    grid.zone=50;grid.hemisphere='N';
    p6g::StationSet stations;
    stations.upper={station(58424,0.f,5000.f),
                    station(58425,10000.f,5000.f)};
    const auto choice=p6g::g18b3_source_deck_upper_choice(grid,stations,deck);
    check(choice.iupt==-1&&choice.nearu.size()==4&&
          choice.nearu[0]==1&&choice.nearu[1]==2 &&
          !choice.independently_fortran_verified,
          "G18B3 original -1 IUPT and REAL4 strict first-US distance tie");
    auto altered=stations;
    std::swap(altered.upper[0],altered.upper[1]);
    const auto reordered=p6g::g18b3_source_deck_upper_choice(grid,altered,deck);
    check(reordered.nearu[0]==1&&reordered.nearu[1]==1,
          "G18B3 source US ordinal tie and actual distance not respected");
    const auto token=std::regex(
        R"(!\s*IUPT\s*=\s*-1\s*!)",std::regex_constants::icase);
    check(std::regex_search(deck,token),
          "G18B3 original met.inp lacks expected IUPT=-1");
    const auto user_forced=std::regex_replace(deck,token,"! IUPT = 2 !");
    const auto forced=p6g::g18b3_source_deck_upper_choice(
        grid,stations,user_forced);
    check(forced.iupt==2&&forced.nearu==choice.nearu,
          "G18B3 positive IUPT replaced geometry rather than selecting US");
    p6e::MixhtObservedMcInput mixed;
    p6g::g18b3_bind_test_only_upper_choice(
        mixed,grid,stations,forced,true);
    check(mixed.iupt==2&&mixed.nearu==choice.nearu,
          "G18B3 positive source IUPT not bound to reused MIXHT kernel");
    const auto selected_controls=p6g::g18b9_parse_original_gamma_controls(
        deck,stations.upper.size());
    const auto forced_controls=p6g::g18b9_parse_original_gamma_controls(
        user_forced,stations.upper.size());
    check(selected_controls.iupt==-1&&selected_controls.idiopt2==0&&
          selected_controls.zupt_m==200.f&&forced_controls.iupt==2,
          "G18B9 source-defined ZUPT/IDIOPT2/IUPT values diverged");
    const auto zupt_pattern=std::regex(
        R"(!\s*ZUPT\s*=\s*200\.\s*!)",std::regex_constants::icase);
    const auto idiopt_pattern=std::regex(
        R"(!\s*IDIOPT2\s*=\s*0\s*!)",std::regex_constants::icase);
    check(std::regex_search(deck,zupt_pattern)&&
          std::regex_search(deck,idiopt_pattern),
          "G18B9 missing original source DIAGNO gamma controls");
    for(const auto& value:{"-1","0","NaN","garbage","200.0 trailing"}) {
        const auto modified=std::regex_replace(
            deck,zupt_pattern,std::string("! ZUPT = ")+value+" !");
        rejects([&]{
            (void)p6g::g18b9_parse_original_gamma_controls(
                modified,stations.upper.size());
        },"G18B9 accepted invalid source ZUPT");
    }
    const auto diagnostic_file=std::regex_replace(
        deck,idiopt_pattern,"! IDIOPT2 = 1 !");
    rejects([&]{
        (void)p6g::g18b9_parse_original_gamma_controls(
            diagnostic_file,stations.upper.size());
    },"G18B9 silently accepted unsupported source diagnostic-file lapse");
    rejects([&]{
        (void)p6g::g18b9_parse_original_gamma_controls(
            deck+"\n! ZUPT = 200. !",stations.upper.size());
    },"G18B9 ignored duplicate original ZUPT control");
    for(const auto& v:{"0","3","-2","1.5","abc"}) {
        const auto invalid=std::regex_replace(
            deck,token,std::string("! IUPT = ")+v+" !");
        rejects([&]{
            (void)p6g::g18b3_source_deck_upper_choice(grid,stations,invalid);
        },"G18B3 accepted malformed/out-of-range original IUPT");
    }
    rejects([&]{
        (void)p6g::g18b3_source_deck_upper_choice(
            grid,stations,deck+"\n! IUPT = -1 !");
    },"G18B3 silently accepted duplicate source IUPT");
    auto bad=stations;
    bad.upper[0].local_y_m=std::numeric_limits<float>::infinity();
    rejects([&]{
        (void)p6g::g18b3_source_deck_upper_choice(grid,bad,deck);
    },"G18B3 silently accepted invalid original UTM upper station");
}
int main(int argc,char** argv){
    try{
        check(argc==3,"G17B4 pinned met.inp and selected output path required");
        std::ifstream file(argv[1]);
        check(static_cast<bool>(file),"G17B4 source met.inp not found");
        const std::string deck((std::istreambuf_iterator<char>(file)),
                               std::istreambuf_iterator<char>());
        const auto control=p6g::parse_g17b4_surface_controls(deck);
        const auto wind=p6g::parse_original_wind_controls(deck);
        check(control.source.iavet==1&&control.mnmdav==1&&
              control.hafang_deg==30.f&&control.source.irad==1&&
              control.source.numts==5&&control.source.trad_km==500.f,
              "G17B4 original Hefei wind-averaging controls diverged");
        const auto begin=sys_days{year{2024}/January/1}+hours{2};
        verify(control,begin);
        verify_source_staged_iavet(control,wind,begin,deck,argv[2]);
        verify_source_staged_iavet(control,wind,begin+hours{12},deck,"");
        verify_g18b_asynchronous_upper_turnover(deck);
        verify_g18b3_source_iupt_choice(deck);
        verify(control,begin+hours{11});
        verify_single_surface_source(control,begin+hours{12});
        // Accept original Fortran freeform control spacing, not a
        // hardcoded literal (e.g. source uses ! IAVET =   1 !).
        const std::regex control_pattern(
            R"(!\s*IAVET\s*=\s*1\s*!)",std::regex_constants::icase);
        check(std::regex_search(deck,control_pattern),
              "original source IAVET=1 field not found");
        const auto bad=std::regex_replace(
            deck,control_pattern,"! IAVET = 0 !");
        rejects([&]{(void)p6g::parse_g17b4_surface_controls(bad);},
                "G17B4 silently accepted source IAVET=0 alternative");
        std::cout<<"PASS_G17B4_SOURCE_IAVET1_TWO_PASS "
                    "METINP_MNMDAV_HAFANG_REAL4 "
                    "WIND1_FIRST_FRADJ_SECOND DIAGNO_ORDER "
                    "G17C_SECOND_TEMP_NATIVE_SOLAR_HEATFX_AIRDEN_PASS "
                    "G17C2_SOURCE_FRADJ_STABLE_DAYTIME_ELUSTR_PASS "
                    "G17C3_STHEOR_ELUSTR2_MIXHTST_DIAGI_SOURCE_SELECTED_PASS "
                    "G17D_HTFAC_SECOND_WINDBC_SMOOTH_DIVCEL_W_FROZEN_KERNEL_PASS "
                    "G18A_PRIOR_COMP_MIXHT_STATION_DPTT_WSTARR_SOURCE_PASS "
                    "G18B_SOURCE_UP_AABB_JUSTA_TEMPORAL_PASS "
                    "G18B3_SOURCE_IUPT_CANDIDATE_NEARU_TEST_ONLY_PASS "
                    "G18B4_PER_UP_FROZEN_CGAMMA_TRANSACTIONAL_HISTORY_PASS "
                    "G18B5_FROZEN_FACET_MULTISITE_SOURCE_FACES_PASS "
                    "G18B7_SOURCE_PREVIOUS_IIUP_JJUP_ZICONV_PASS "
                    "G18B8_SOURCE_IUPT_GAMMA_HOURLY_HANDOFF_PASS "
                    "G18B9_ORIGINAL_ZUPT_IDIOPT2_IUPT_SOURCE_CONTROLS_PASS "
                    "G18C1_SOURCE_IAVEZI_MNMDAV_HAFANG_AVEMIX_PASS "
                    "G18C2_AVEMIX_BEFORE_FROZEN_WSTARR_ORDER_PASS "
                    "G18C3_TRUE_UP_FACET_POST_AVEMIX_TEMP3D_PASS "
                    "G18C4_EIGHT_G14_FIELDS_UNCOMMITTED_SOURCE_CANDIDATE_PASS "
                    "G18C5_SELECTED_45_P6F_NO_REFERENCE_BACKFILL_PASS "
                    "G18C6_SELECTED_CALMET_DAT21_BINARY_NO_REFERENCE_STATICS_PASS "
                    "G18D1_P6F_45_RECORDS_G14_PRECOMMIT_ORIGIN_PASS "
                    "G18D3_LITERAL_VENDOR_HFLUX_DEFAULTS_SOURCE_PASS "
                    "G18D4_ORIGINAL_COMP_FOUR_STAGES_SOURCE_CANDIDATE_PASS "
                    "G18D5_ORIGINAL_METINP_SET_CMECH_MIXHT_SCALARS_PASS "
                    "G18D6_VENDOR_NEARU_STHEOR_SURFACE_ASSIGNMENT_PASS "
                    "IAVET1_FULL_MULTI_SITE_PHYSICS=NOT_YET_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"FAIL_G17B4 "<<e.what()<<"\n";
        return 1;
    }
}
