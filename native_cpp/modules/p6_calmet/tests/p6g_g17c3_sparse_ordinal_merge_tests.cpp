// S4-R1c7d: validate real source SS ordinal retention at the existing G17C3
// merge boundary, never a test-only replacement for STHEOR, WIND1 or INTER2.
#include "cteas/p6/p6g_g17c3_station_diagi.hpp"
#include <chrono>
#include <cstddef>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace g=cteas::calmet::p6g;
using std::chrono::seconds;
static void check(bool yes,const char* what) {
    if(!yes)throw std::runtime_error(what);
}
template<typename F>static void rejects(F run,const char* what) {
    bool caught=false;
    try{run();}catch(const std::invalid_argument&){caught=true;}
    check(caught,what);
}
static g::G16ObservedProfiles original_source_profile() {
    g::G16ObservedProfiles p{};
    p.end=std::chrono::sys_seconds{seconds{123456}};
    p.station_ids={583140,583210,58424};
    for(std::size_t k=0;k<9;++k)for(std::size_t i=0;i<3;++i) {
        p.wind1_u_mps.push_back(static_cast<float>(k*3+i+11));
        p.wind1_v_mps.push_back(static_cast<float>(k*3+i+22));
        p.wind1_present.push_back(i==0?0U:1U);
        p.inter2_u_mps.push_back(i==2?static_cast<float>(k+42):999.f);
        p.inter2_v_mps.push_back(i==2?static_cast<float>(k+49):999.f);
        p.inter2_present.push_back(i==2?1U:0U);
    }
    return p;
}
static g::StationSet source_stations() {
    g::StationSet s{};
    cteas::calmet::p6::DeckStation a{},b{},up{};
    a.id=583140;b.id=583210;up.id=58424;
    s.surface={a,b};
    s.upper={up};
    return s;
}
static g::G17C3StationDiagi actual_second_station(
    const g::G16ObservedProfiles& profile) {
    g::G17C3StationDiagi p{};
    p.surface_id=583210;
    p.upper_id=58424;
    p.end=profile.end;
    p.levels_filled=7;
    for(std::size_t k=0;k<9;++k) {
        p.diagi_profile.u_mps[k]=static_cast<float>(k+0.5);
        p.diagi_profile.v_mps[k]=static_cast<float>(k-0.5);
    }
    return p;
}
int main() {
    try {
        const auto before=original_source_profile();
        const auto stations=source_stations();
        const auto valid=actual_second_station(before);
        const auto merged=g::merge_g17c3_surface_diagi(
            before,stations,{valid},{0,1});
        check(merged.station_ids==before.station_ids,
              "original 2SS1US ordinal changed");
        check(merged.wind1_u_mps==before.wind1_u_mps&&
              merged.wind1_v_mps==before.wind1_v_mps&&
              merged.wind1_present==before.wind1_present,
              "neutral WIND1 original columns mutated");
        for(std::size_t k=0;k<9;++k) {
            const auto absent=3*k,real=3*k+1,upper=3*k+2;
            check(merged.inter2_u_mps[absent]==before.inter2_u_mps[absent]&&
                  merged.inter2_v_mps[absent]==before.inter2_v_mps[absent]&&
                  merged.inter2_present[absent]==0,
                  "genuine missing surface wind became an observed calm or a reindexed wind");
            check(merged.inter2_u_mps[upper]==before.inter2_u_mps[upper]&&
                  merged.inter2_v_mps[upper]==before.inter2_v_mps[upper]&&
                  merged.inter2_present[upper]==before.inter2_present[upper],
                  "genuine upper PREPDI station column changed");
            check(merged.inter2_present[real]==(k<7?1U:0U)&&
                  merged.inter2_u_mps[real]==(k<7?static_cast<float>(k+0.5):999.f)&&
                  merged.inter2_v_mps[real]==(k<7?static_cast<float>(k-0.5):999.f),
                  "valid second original SS DIAGI mapped to wrong column or level");
        }
        rejects([&]{(void)g::merge_g17c3_surface_diagi(before,stations,{valid});},
                "sparse accepted without original wind mask opt-in");
        rejects([&]{(void)g::merge_g17c3_surface_diagi(before,stations,{valid},{1,0});},
                "source station reordering accepted");
        rejects([&]{(void)g::merge_g17c3_surface_diagi(before,stations,{valid},{1,1});},
                "invalid source-valid site count accepted");
        rejects([&]{(void)g::merge_g17c3_surface_diagi(before,stations,{valid},{0,2});},
                "non-binary source validity accepted");
        rejects([&]{(void)g::merge_g17c3_surface_diagi(before,stations,{valid},{0,1,0});},
                "mismatched surface mask length accepted");
        auto bad=before;
        bad.inter2_present[0]=1;
        rejects([&]{(void)g::merge_g17c3_surface_diagi(bad,stations,{valid},{0,1});},
                "contradictory original missing observation presence accepted");
        auto stale=valid;stale.end+=seconds{3600};
        rejects([&]{(void)g::merge_g17c3_surface_diagi(before,stations,{stale},{0,1});},
                "stale source station hour accepted");
        auto wrong=valid;wrong.surface_id=583140;
        rejects([&]{(void)g::merge_g17c3_surface_diagi(before,stations,{wrong},{0,1});},
                "wrong original SS identity accepted");
        auto duplicate=valid;
        rejects([&]{(void)g::merge_g17c3_surface_diagi(before,stations,{valid,duplicate},{0,1});},
                "duplicate source station mapped");
        std::cout<<"S4R1C7D_G17C3_REAL_SPARSE_ORDINAL_MERGE_UNIT=PASS\n"
                 <<"S4R1C7D_NEUTRAL_WIND1_UPPER_PREPDI_AND_MISSING_WIND_UNCHANGED=PASS\n"
                 <<"S4R1C7D_NATIVE_G16_WIND1_G23_INTER2_G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C7D_G17C3_SOURCE_MERGE_UNIT=FAIL "<<e.what()<<"\n";
        return 2;
    }
}
