// G16A: first numerical CALMET stages using the EXACT accepted original
// stage enums: WIND1 is computed natively, INTER2 requires explicit
// post-FRADJ/SLOPE/first-WINDBC field handoff and physical WO inputs.
// All upstream test profiles and post-SLOPE fields are controlled fixtures;
// no full DIAGNO/COMP, P6E or original 45-field parity is asserted.
#include "cteas/p6/p6g_g16_staged_wind.hpp"
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
static void need(bool yes,const char* label) {
    if(!yes)throw std::runtime_error(label);
}
template<class F>static void refuse(F&& action,const char* label){
    bool denied=false;
    try{action();}
    catch(const std::exception&){denied=true;}
    need(denied,label);
}
static p6::DeckStation station(int id,float x,float y) {
    p6::DeckStation st{};
    st.id=id;st.local_x_m=x;st.local_y_m=y;
    return st;
}
static p6g::StationSet station_set() {
    p6g::StationSet deck;
    deck.surface={station(58321,10000.f,10000.f),
                  station(58322,30000.f,40000.f)};
    deck.upper={station(58424,20000.f,20000.f),
                station(58425,50000.f,50000.f)};
    return deck;
}
static p6g::G16ObservedProfiles inputs(sys_seconds end) {
    p6g::G16ObservedProfiles p;
    p.end=end;p.station_ids={58321,58322,58424,58425};
    p.wind1_u_mps.resize(36);p.wind1_v_mps.resize(36);
    p.wind1_present.assign(36,1);
    for(std::size_t k=0;k<9;++k) {
        p.wind1_u_mps[k*4]=0.f;p.wind1_v_mps[k*4]=0.f;
        p.wind1_u_mps[k*4+1]=3.f;p.wind1_v_mps[k*4+1]=4.f;
        p.wind1_u_mps[k*4+2]=5.f;p.wind1_v_mps[k*4+2]=-2.f;
        p.wind1_u_mps[k*4+3]=9.f;p.wind1_v_mps[k*4+3]=10.f;
    }
    p.wind1_present[1*4+3]=0;
    p.wind1_u_mps[1*4+3]=999999.f;
    p.wind1_v_mps[1*4+3]=999999.f;
    // Controlled DIFFERENT DIAGI source profiles; stability/cutoff
    // prevents the surface profile above ZI from reaching INTER2.
    // These are fixtures, NOT accepted original multi-site P6E ZI.
    p.inter2_u_mps=p.wind1_u_mps;
    p.inter2_v_mps=p.wind1_v_mps;
    p.inter2_present=p.wind1_present;
    for(std::size_t k=4;k<9;++k) {
        p.inter2_present[k*4]=0;
        p.inter2_u_mps[k*4]=999.f;
        p.inter2_v_mps[k*4]=999.f;
    }
    return p;
}
static p6g::GeoGrid geo() {
    p6g::GeoGrid g;
    g.nx=3;g.ny=3;g.zone=50;g.hemisphere='N';g.grid_km=10.f;
    g.iwat1=50;g.iwat2=55;
    g.landuse.assign(9,10);
    return g;
}
static p6g::SurfaceHour observation(sys_seconds end) {
    p6g::SurfaceHour row;
    row.start=end-hours{1};row.end=end;
    row.by_station.resize(2);
    row.by_station[0].wind_valid=true;
    row.by_station[0].wind_speed_mps=0.f;
    row.by_station[1].wind_valid=true;
    row.by_station[1].wind_speed_mps=5.f;
    return row;
}
static p6g::G16PostSlopeFields controlled_corrected(sys_seconds end,
                                              const p6g::G16WindStages& wind){
    p6g::G16PostSlopeFields correct;
    correct.end=end;
    // Explicit controlled identity is NOT original FRADJ/SLOPE physics.
    // This is only an INTER2 handoff and ordering contract.
    correct.u_mps=wind.first_guess.u_mps;
    correct.v_mps=wind.first_guess.v_mps;
    correct.observation_weight.assign(correct.u_mps.size(),1.f);
    const auto nx=static_cast<std::size_t>(wind.first_guess.nx);
    const auto ny=static_cast<std::size_t>(wind.first_guess.ny);
    const auto cells=nx*ny;
    correct.ub_west_east_mps.resize(9*2*ny);
    correct.vb_south_north_mps.resize(9*2*nx);
    for(std::size_t k=0;k<9;++k){
        for(std::size_t j=0;j<ny;++j){
            const auto row=k*cells+j*nx,edge=k*2*ny+j;
            correct.ub_west_east_mps[edge]=correct.u_mps[row];
            correct.ub_west_east_mps[edge+ny]=correct.u_mps[row+nx-1];
        }
        for(std::size_t i=0;i<nx;++i){
            const auto row=k*cells+i,edge=k*2*nx+i;
            correct.vb_south_north_mps[edge]=correct.v_mps[row];
            correct.vb_south_north_mps[edge+nx]=
                correct.v_mps[row+(ny-1)*nx];
        }
    }
    return correct;
}
int main(int argc,char** argv) {
    try {
        need(argc==2,"source met.inp argument missing");
        std::ifstream f(argv[1]);
        need(static_cast<bool>(f),"original met.inp inaccessible");
        const std::string decktext((std::istreambuf_iterator<char>(f)),
                                   std::istreambuf_iterator<char>());
        const auto controls=p6g::parse_original_wind_controls(decktext);
        need(controls.bias[0]==-1.f&&controls.rmin_km==0.1f,
             "G16 not using original READCF-corrected source controls");
        const auto end=sys_days{year{2024}/January/1}+hours{1};
        auto grid=geo();
        auto deck=station_set();
        auto surf=observation(end);
        p6g::InputHour slot{};
        slot.end=end;slot.upper.resize(2);
        std::vector<p6g::UpperSeries> upper(2);
        upper[0].station_id=58424;upper[1].station_id=58425;
        p6::NativeGridMemory previous;
        previous.zi_m.assign(9,0.f);previous.ziconv_m.assign(9,0.f);
        previous.dptt_k.assign(9,0.f);
        p6g::MultiHourFrame hour{0,grid,deck,surf,slot,upper,&controls,
                                previous,previous,{}};
        auto profiles=inputs(end);
        p6g::G16SelectedWindPhysics stages(profiles);
        need(!stages.run(p6::NativeHourStage::PrepdiPreviousZiconv,hour).completed,
             "G16 pretended full thermal PREPDI was already implemented");
        refuse([&]{(void)stages.run(p6::NativeHourStage::DiagnoInter2,hour);},
               "G16 allowed INTER2 before WIND1/FRADJ/SLOPE");
        const auto w=stages.run(p6::NativeHourStage::DiagnoWind1,hour);
        need(w.completed&&w.source==p6::NativeHourSource::NativeCpp,
             "G16 native multi-station WIND1 stage did not execute");
        need(stages.selected_result().wind1_complete&&
             stages.selected_result().first_guess.u_mps.size()==81,
             "G16 failed to preserve original WIND1 3x3x9 field");
        p6g::Wind1MultiInput expected;
        expected.nx=3;expected.ny=3;expected.nz=9;expected.spacing_m=10000.f;
        expected.surface_count=2;expected.upper_count=2;
        expected.station_x_m={10000.f,30000.f,20000.f,50000.f};
        expected.station_y_m={10000.f,40000.f,20000.f,50000.f};
        expected.surface_speeds_mps={0.f,5.f};
        expected.station_u_mps=profiles.wind1_u_mps;
        expected.station_v_mps=profiles.wind1_v_mps;
        expected.present=profiles.wind1_present;
        expected.vertical_bias.assign(controls.bias.begin(),controls.bias.end());
        expected.icalm=controls.icalm;
        const auto comparison=p6g::multi_station_wind1_firstguess(expected);
        need(comparison.u_mps==stages.selected_result().first_guess.u_mps&&
             comparison.v_mps==stages.selected_result().first_guess.v_mps,
             "G16 stage diverged from accepted original-source G9 WIND1");
        refuse([&]{(void)stages.run(p6::NativeHourStage::DiagnoWind1,hour);},
               "G16 repeated WIND1 after source clock committed");
        refuse([&]{stages.provide_selected_diagi_after_wind1(profiles);},
               "G16 accepted DIAGI after WIND1 without post-SLOPE first WINDBC");
        refuse([&]{
            auto wrong=controlled_corrected(end+hours{1},stages.selected_result());
            stages.provide_post_slope(std::move(wrong));
        },"G16 allowed next-hour FRADJ/SLOPE field");
        refuse([&]{(void)stages.run(p6::NativeHourStage::DiagnoInter2,hour);},
               "G16 accepted INTER2 without explicit corrected wind and WO");
        auto corrected=controlled_corrected(end,stages.selected_result());
        auto missing_windbc=corrected;
        missing_windbc.ub_west_east_mps.pop_back();
        refuse([&]{stages.provide_post_slope(missing_windbc);},
               "G16 accepted absent first source WINDBC boundary");
        auto wrong_windbc=corrected;
        wrong_windbc.ub_west_east_mps[0]+=1.f;
        refuse([&]{stages.provide_post_slope(wrong_windbc);},
               "G16 accepted boundary reconstructed from incorrect first-pass U");
        stages.provide_post_slope(corrected);
        refuse([&]{(void)stages.run(p6::NativeHourStage::DiagnoInter2,hour);},
               "G16 accepted original INTER2 without post-STHEOR DIAGI station refresh");
        auto stale=profiles;
        stale.end+=hours{1};
        refuse([&]{stages.provide_selected_diagi_after_wind1(stale);},
               "G16 accepted next-hour STHEOR DIAGI profiles");
        auto corrupted=profiles;
        corrupted.inter2_u_mps[2]+=0.125f; // upper US1 from PREPDI
        refuse([&]{stages.provide_selected_diagi_after_wind1(corrupted);},
               "G16 accepted a replaced PREPDI upper station column");
        stages.provide_selected_diagi_after_wind1(profiles);
        refuse([&]{stages.provide_selected_diagi_after_wind1(profiles);},
               "G16 accepted duplicate DIAGI station refresh");
        const auto b=stages.run(p6::NativeHourStage::DiagnoInter2,hour);
        need(b.completed&&b.source==p6::NativeHourSource::NativeCpp&&
             stages.selected_result().inter2_complete,
             "G16 native source INTER2 stage did not execute");
        need(stages.selected_result().blended_u.component_mps.size()==81&&
             stages.selected_result().blended_v.component_mps.size()==81,
             "G16 did not generate full three-dimensional INTER2 fields");
        need(stages.selected_result().original_ub_west_east_mps==
                 corrected.ub_west_east_mps&&
             stages.selected_result().original_vb_south_north_mps==
                 corrected.vb_south_north_mps,
             "G16 re-initialized source first WINDBC after INTER2");
        // Independent direct invocation of the same immutable #53 INTER2
        // kernel verifies that stage-correct parameter/array mapping holds.
        p6::Inter2SelectedInput inter;
        inter.nx=3;inter.ny=3;inter.nz=9;inter.nstations=4;
        inter.dx_m=10000.f;inter.dy_m=10000.f;
        inter.rmin_km=controls.rmin_km;
        inter.rmax1_km=controls.rmax1_km;
        inter.rmax2_km=controls.rmax2_km;
        inter.rmax3_km=controls.rmax3_km;
        inter.r1_km=controls.r1_km;inter.r2_km=controls.r2_km;
        inter.landuse=grid.landuse;
        inter.water_first=grid.iwat1;inter.water_last=grid.iwat2;
        // Source operations: convert each REAL*4 local-metre coordinate
        // by multiplication with 0.001f. 10.f literal is NOT guaranteed
        // bit-identical to 10000.f * 0.001f on the original REAL*4 path.
        inter.station_x_km={10000.f*0.001f,30000.f*0.001f,
                            20000.f*0.001f,50000.f*0.001f};
        inter.station_y_km={10000.f*0.001f,40000.f*0.001f,
                            20000.f*0.001f,50000.f*0.001f};
        inter.nintrp_per_layer.assign(9,4);
        inter.observation_weight=corrected.observation_weight;
        inter.station_component_mps=profiles.inter2_u_mps;
        for(std::size_t k=0;k<9;++k)
            for(std::size_t l=0;l<4;++l)
                if(!profiles.inter2_present[k*4+l])
                    inter.station_component_mps[k*4+l]=inter.edit;
        inter.step1_mps=corrected.u_mps;
        const auto direct=p6::original_inter2_selected(inter);
        need(direct.component_mps==stages.selected_result().blended_u.component_mps,
             "G16 INTER2 stage and accepted source kernel differ");
        // Prove that accidentally supplying WIND1's neutral, uncapped
        // station profile to INTER2 materially changes higher-layer winds.
        auto wrong_neutral=inter;
        wrong_neutral.station_component_mps=profiles.wind1_u_mps;
        for(std::size_t k=0;k<9;++k)
            for(std::size_t l=0;l<4;++l)
                if(!profiles.wind1_present[k*4+l])
                    wrong_neutral.station_component_mps[k*4+l]=wrong_neutral.edit;
        const auto wrong_u=p6::original_inter2_selected(wrong_neutral);
        bool differs=false;
        for(std::size_t k=4;k<9;++k)
            for(std::size_t p=0;p<9;++p)
                differs|=wrong_u.component_mps[k*9+p]!=direct.component_mps[k*9+p];
        need(differs,"G16 neutral WIND1 and capped DIAGI INTER2 were incorrectly conflated");
        refuse([&]{(void)stages.run(p6::NativeHourStage::DiagnoInter2,hour);},
               "G16 accepted second INTER2 with stale corrected data");
        need(!stages.run(p6::NativeHourStage::CompGridMixht,hour).completed,
             "G16 forged a complete source P6E mixing-height field");
        need(hour.next.ziconv_m==previous.ziconv_m&&
             hour.next.zi_m==previous.zi_m,
             "G16 selected numerical stages mutated COMP previous-hour state");
        auto shuffled=inputs(end);
        std::swap(shuffled.station_ids[0],shuffled.station_ids[1]);
        p6g::G16SelectedWindPhysics wrong_order(shuffled);
        refuse([&]{
            (void)wrong_order.run(p6::NativeHourStage::DiagnoWind1,hour);
        },"G16 accepted shuffled ground station source identity");
        p6g::G16SelectedWindPhysics no_source(inputs(end));
        hour.source_controls=nullptr;
        refuse([&]{(void)no_source.run(p6::NativeHourStage::DiagnoWind1,hour);},
               "G16 accepted WIND1 without original met.inp source");
        std::cout<<"PASS_P6G_G16_STAGE_CORRECT_MULTI_WIND1_INTER2 "
                   "SOURCE_METINP_BIAS_NINTR2 WIND1_EQ_SOURCE_KERNEL "
                   "INTER2_AFTER_EXPLICIT_POST_SLOPE_ROLLBACK "
                   "COMP_NOT_IMPLEMENTED FULL_SITE_SOURCE_PARITY=NOT_PASS\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"FAIL_P6G_G16 "<<e.what()<<"\n";
        return 1;
    }
}
