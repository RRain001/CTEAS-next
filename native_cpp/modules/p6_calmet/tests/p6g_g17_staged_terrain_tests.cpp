// G17A: explicit stage source order, selected original native FRADJ
// and SLOPE reused from P6, WIND1/INTER2 reused from G16. The sensible
// heat, radiation and DIAGI mixing height are CONTROLLED TEST FIXTURES.
// No P6E or full multi-station source acceptance follows from this test.
#include "cteas/p6/p6g_g17_staged_terrain.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <exception>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

namespace p6=cteas::calmet::p6;
namespace p6g=cteas::calmet::p6g;
using namespace std::chrono;

static void check(bool yes,const char* reason){
    if(!yes)throw std::runtime_error(reason);
}
template<class F>static void reject(F&& f,const char* why){
    bool caught=false;
    try{f();}catch(const std::exception&){caught=true;}
    check(caught,why);
}
static p6::DeckStation station(int id,float x,float y){
    p6::DeckStation st{};
    st.id=id;st.local_x_m=x;st.local_y_m=y;
    return st;
}
static p6g::G16ObservedProfiles profiles(sys_seconds end){
    p6g::G16ObservedProfiles p;
    p.end=end;p.station_ids={58321,58322,58424,58425};
    for(int k=0;k<9;++k){
        const std::vector<float> u{3.f,-3.f,8.f,9.f};
        const std::vector<float> v{4.f,4.f,-2.f,10.f};
        p.wind1_u_mps.insert(p.wind1_u_mps.end(),u.begin(),u.end());
        p.wind1_v_mps.insert(p.wind1_v_mps.end(),v.begin(),v.end());
    }
    p.wind1_present.assign(36,1);
    p.inter2_u_mps=p.wind1_u_mps;
    p.inter2_v_mps=p.wind1_v_mps;
    p.inter2_present=p.wind1_present;
    for(std::size_t k=4;k<9;++k){
        p.inter2_present[k*4]=0;
        p.inter2_u_mps[k*4]=999.f;
        p.inter2_v_mps[k*4]=999.f;
    }
    return p;
}
static p6g::GeoGrid grid(){
    p6g::GeoGrid g;
    g.nx=12;g.ny=12;g.zone=50;g.hemisphere='N';
    g.grid_km=10.f;g.iwat1=50;g.iwat2=55;
    for(int j=0;j<12;++j)
        for(int i=0;i<12;++i){
            g.terrain_m.push_back(100.f+250.f*i+150.f*j);
            g.landuse.push_back((i==3&&j==3)?50:20);
        }
    return g;
}
static p6g::G17FradjSource fradj(sys_seconds end){
    p6g::G17FradjSource x;
    x.end=end;
    x.provenance=p6g::TerrainHourProvenance::SyntheticReferenceFixture;
    x.isurft=-1;
    x.domain_temperature_k=285.f;
    x.critfn=10.f;
    x.lapse_k_per_m.assign(144,0.002f);
    x.temperature_k.assign(144,280.f);
    return x;
}
static p6g::G17SlopeHeatSource heat(sys_seconds end){
    p6g::G17SlopeHeatSource h;
    h.end=end;
    h.provenance=p6g::TerrainHourProvenance::SyntheticReferenceFixture;
    h.sensible_heat_w_m2.assign(144,-120.f);
    h.temperature_k.assign(144,280.f);
    return h;
}
int main(int argc,char** argv) {
    try {
        check(argc==2,"G17 missing pinned original met.inp path");
        std::ifstream input(argv[1]);
        check(static_cast<bool>(input),"G17 original met.inp unavailable");
        const std::string decktext((std::istreambuf_iterator<char>(input)),
                                   std::istreambuf_iterator<char>());
        const auto controls=p6g::parse_original_wind_controls(decktext);
        const auto end=sys_days{year{2024}/January/1}+hours{1};
        const auto geo=grid();
        const auto stations=p6g::StationSet{
            {station(58321,10000.f,10000.f),station(58322,30000.f,40000.f)},
            {station(58424,20000.f,20000.f),station(58425,50000.f,50000.f)}
        };
        auto terrain=p6g::prepare_g11_terrain(geo,35.f);
        p6g::SurfaceHour observation;
        observation.start=end-hours{1};observation.end=end;
        observation.by_station.resize(2);
        for(auto& surf:observation.by_station){
            surf.wind_valid=true;surf.wind_speed_mps=5.f;
        }
        p6g::InputHour slot{};
        slot.end=end;slot.upper.resize(2);
        std::vector<p6g::UpperSeries> upper(2);
        upper[0].station_id=58424;upper[1].station_id=58425;
        p6::NativeGridMemory memory;
        memory.zi_m.assign(144,0.f);memory.ziconv_m.assign(144,0.f);
        memory.dptt_k.assign(144,0.f);
        p6g::MultiHourFrame hour{0,geo,stations,observation,slot,upper,
                                &controls,memory,memory,{}};
        p6g::G17SelectedTerrainFixturePhysics stages(
            profiles(end),terrain,fradj(end));
        auto obsolete_geo=geo;
        obsolete_geo.terrain_m[0]+=1.f;
        p6g::MultiHourFrame stale{0,obsolete_geo,stations,observation,slot,upper,
                                 &controls,memory,memory,{}};
        p6g::G17SelectedTerrainFixturePhysics stale_terrain(
            profiles(end),terrain,fradj(end));
        reject([&]{
            (void)stale_terrain.run(p6::NativeHourStage::DiagnoWind1,stale);
        },"G17 accepted terrain envelope from a different GEO source");
        check(!stages.run(p6::NativeHourStage::PrepdiPreviousZiconv,hour).completed,
              "G17 fabricated original PREPDI native processing");
        reject([&]{stages.run(p6::NativeHourStage::DiagnoFradj,hour);},
               "G17 permitted FRADJ before WIND1");
        reject([&]{stages.provide_slope_heat(heat(end));},
               "G17 accepted QH before FRADJ");
        auto res=stages.run(p6::NativeHourStage::DiagnoWind1,hour);
        check(res.completed&&res.source==p6::NativeHourSource::NativeCpp,
              "G17 original-source selected WIND1 incomplete");
        reject([&]{stages.run(p6::NativeHourStage::DiagnoSlope,hour);},
               "G17 allowed SLOPE before FRADJ and HEATFX");
        reject([&]{stages.run(p6::NativeHourStage::DiagnoWindbcFirstGuess,hour);},
               "G17 first WINDBC executed before slope correction");
        res=stages.run(p6::NativeHourStage::DiagnoFradj,hour);
        check(res.completed&&res.source==p6::NativeHourSource::NativeCpp,
              "G17 source-native FRADJ failed to execute");
        // Compare stage FRADJ directly, not only the final combined field.
        const auto& first=stages.wind_stages().first_guess;
        const std::vector<float> zface(controls.zface_m.begin(),
                                       controls.zface_m.end());
        const auto origin=p6::WindUV{first.u_mps,first.v_mps};
        const auto direct_fradj=p6::froude_adjust(
            12,12,9,10000.f,10000.f,terrain.terrain_m,terrain.hmax_m,
            fradj(end).lapse_k_per_m,fradj(end).temperature_k,
            -1,285.f,10.f,zface,origin);
        check(stages.after_fradj().u==direct_fradj.u&&
              stages.after_fradj().v==direct_fradj.v,
              "G17 real staged FRADJ differed from immutable original-source kernel");
        reject([&]{stages.run(p6::NativeHourStage::DiagnoFradj,hour);},
               "G17 allowed duplicate FRADJ");
        check(!stages.run(p6::NativeHourStage::DiagnoHeatfx,hour).completed,
              "G17 falsely marked still-synthetic P6E HEATFX completed");
        check(!stages.run(p6::NativeHourStage::DiagnoAirden,hour).completed,
              "G17 falsely marked real P6E AIRDEN completed");
        check(!stages.run(p6::NativeHourStage::DiagnoElustr,hour).completed,
              "G17 falsely marked real P6E ELUSTR completed");
        reject([&]{stages.run(p6::NativeHourStage::DiagnoSlope,hour);},
               "G17 executed SLOPE without explicit QH");
        auto wrong_time=heat(end+hours{1});
        reject([&]{stages.provide_slope_heat(wrong_time);},
               "G17 silently accepted next-hour QH for SLOPE");
        auto wrong_source=heat(end);
        wrong_source.provenance=
            p6g::TerrainHourProvenance::ValidatedP6EHourlyPhysics;
        reject([&]{stages.provide_slope_heat(wrong_source);},
               "G17 accepted unverified production P6E QH assertion");
        auto inconsistent_temp=heat(end);
        inconsistent_temp.temperature_k[0]+=1.f;
        reject([&]{stages.provide_slope_heat(inconsistent_temp);},
               "G17 used different SURFVAR TEMP2D in FRADJ and SLOPE");
        stages.provide_slope_heat(heat(end));
        res=stages.run(p6::NativeHourStage::DiagnoSlope,hour);
        check(res.completed&&res.source==p6::NativeHourSource::NativeCpp,
              "G17 native SLOPE callback was not executed");
        p6g::TerrainHourG11 source;
        source.end=end;
        source.provenance=p6g::TerrainHourProvenance::SyntheticReferenceFixture;
        source.isurft=-1;source.domain_temperature_k=285.f;
        source.critfn=10.f;
        source.lapse_k_per_m=fradj(end).lapse_k_per_m;
        source.temperature_k=fradj(end).temperature_k;
        source.sensible_heat_w_m2=heat(end).sensible_heat_w_m2;
        const auto g11=p6g::apply_g11_terrain_after_wind1(
            terrain,source,zface,origin);
        check(stages.after_slope().u==g11.field.u&&
              stages.after_slope().v==g11.field.v,
              "G17 independent FRADJ→SLOPE stages differ from G11 source subchain");
        reject([&]{stages.run(p6::NativeHourStage::DiagnoSlope,hour);},
               "G17 accepted repeated SLOPE");
        res=stages.run(p6::NativeHourStage::DiagnoWindbcFirstGuess,hour);
        check(res.completed&&res.source==p6::NativeHourSource::NativeCpp,
              "G17 first pre-INTER2 WINDBC incomplete");
        reject([&]{stages.run(p6::NativeHourStage::DiagnoWindbcFirstGuess,hour);},
               "G17 incorrectly recomputed first WINDBC");
        reject([&]{stages.run(p6::NativeHourStage::DiagnoInter2,hour);},
               "G17 accepted INTER2 before source STHEOR DIAGI station refresh");
        stages.provide_selected_diagi_before_inter2(profiles(end));
        res=stages.run(p6::NativeHourStage::DiagnoInter2,hour);
        check(res.completed&&res.source==p6::NativeHourSource::NativeCpp,
              "G17 INTER2 after genuine native FRADJ/SLOPE/WINDBC failed");
        check(stages.wind_stages().inter2_complete&&
              stages.wind_stages().original_ub_west_east_mps.size()==216&&
              stages.wind_stages().original_vb_south_north_mps.size()==216,
              "G17 original L5748 first WINDBC boundary not retained");
        for(std::size_t k=0;k<9;++k)
            for(std::size_t j=0;j<12;++j){
                const auto row=k*144+j*12,edge=k*24+j;
                check(stages.wind_stages().original_ub_west_east_mps[edge]==
                          stages.after_slope().u[row],
                      "G17 UB west was recomputed after INTER2");
            }
        check(!stages.run(p6::NativeHourStage::DiagnoSmoothDivcelW,hour).completed,
              "G17 pretended full CALMET SMOOTH/DIVCEL/W stage exists");
        check(!stages.run(p6::NativeHourStage::CompGridMixht,hour).completed,
              "G17 pretended native multi-station COMP/MIXHT exists");
        check(memory.ziconv_m==hour.next.ziconv_m,
              "G17 test mutated previous-hour P6E thermal state");
        std::cout<<"PASS_P6G_G17_STAGE_FRADJ_SLOPE_FIRST_WINDBC_SOURCE_SELECTED "
                   "FRADJ_EQUALS_FROUDE SLOPE_EQUALS_G11 "
                   "NATIVE_INTER2_AFTER_L5748 FIRST_BOUNDARY_UNCHANGED "
                   "REAL_MULTI_SITE_HEATFX_COMP=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"FAIL_P6G_G17 "<<e.what()<<"\n";
        return 1;
    }
}
