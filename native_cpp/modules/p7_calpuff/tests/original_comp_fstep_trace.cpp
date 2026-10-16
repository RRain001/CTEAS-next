// Original 2022 COMP FSTEP/KSAM/TLEFT numerical trace; frozen instrumented
// original CALPUFF DGM is a read-only input for the STEP CONTROLLER ONLY.
// No DGM trajectory, concentration, height or mass enters a native solver.
#include "cteas/puff/step_integration.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

namespace {
struct Record { std::int32_t ints[24]; float values[64]; };
static_assert(sizeof(Record)==352);
struct Episode {
    int hour=0, slot=0, last_ksam=0, nsam=0;
    float left=0.0F;
    float reference=0.0F;
    float used=0.0F;
    bool initialized=false;
};
void require(bool condition,const std::string& message){
    if(!condition)throw std::runtime_error(message);
}
std::string key(const Record& row,std::uint64_t index){
    return "record="+std::to_string(index)+" hour="+std::to_string(row.ints[1])+ 
        " puff="+std::to_string(row.ints[3])+" ksam="+std::to_string(row.ints[16]);
}
// REAL*4 reference comparisons tolerate a few ULPs of compiler-level
// evaluation; any over-tolerance mismatch remains a HARD failure.
bool equal_step(float a,float b){
    return std::isfinite(a)&&std::isfinite(b)&&
        std::abs(a-b)<=std::max(0.0001F,std::abs(b)*3.0e-6F);
}
void run(const std::string& filename,int expected_hours){
    require(expected_hours==1||expected_hours==6||expected_hours==143,
            "only pinned original 1, 6 or 143 hours supported");
    std::ifstream input(filename,std::ios::binary);
    require(static_cast<bool>(input),"original DGM file not available");
    Episode current;
    std::uint64_t rows=0, short_steps=0, reentries=0, real_hours=0;
    std::uint64_t nonzero_left=0, correct_steps=0, mismatches=0;
    int last_hour=0;
    std::string first_failure;
    Record row{};
    while(input.read(reinterpret_cast<char*>(&row),sizeof(row))){
        ++rows;
        const auto label=key(row,rows);
        require(row.ints[0]==1 && row.ints[19]==1 && row.ints[20]==0,
                "non-Gaussian/invalid original DGM: "+label);
        const int hour=row.ints[1],slot=row.ints[3],ksam=row.ints[16];
        const int nsam=row.ints[10],nsstr=row.ints[11];
        require(nsam>=1 && nsam<=99 && ksam>=nsstr && ksam<=nsam &&
                slot>0 && (last_hour==0 || hour>=last_hour),
                "invalid source KSAM/NSAM order: "+label);
        if(hour!=last_hour){ ++real_hours;last_hour=hour; }
        const float reftsamp=row.values[17]; // slot 18, original L10347
        const float actual=row.values[62]; // slot 63, TSAMP at SETPUF
        const float original_left=row.values[60]; // slot 61 at L10581
        const float original_ws=row.values[11]; // slot 12 at L10528
        require(std::isfinite(reftsamp)&&reftsamp>0 &&
                std::isfinite(actual)&&actual>0 &&
                std::isfinite(original_ws)&&original_ws>=0 &&
                std::isfinite(original_left),
                "nonfinite/negative original sampling data: "+label);
        const bool new_episode=!current.initialized||
            current.hour!=hour||current.slot!=slot;
        if(new_episode){
            current={hour,slot,nsstr-1,nsam,0.0F,reftsamp,0.0F,true};
        }else{
            require(nsam==current.nsam,
                    "NSAM changed during puff episode: "+label);
            require(equal_step(reftsamp,current.reference),
                    "REFTSAMP changed (variable emissions not supported): "+label);
            require(ksam==current.last_ksam || ksam==current.last_ksam+1,
                    "nonadjacent original KSAM transition: "+label);
            const bool original_repeat=ksam==current.last_ksam;
            if(original_repeat)++reentries;
            const bool must_repeat= (current.left>=1.0F &&
                                    current.last_ksam==current.nsam) ||
                                   (current.left>current.used);
            // The vendor applies these conditions only if NSAM<MXSAM.
            if(original_repeat != (nsam<99 && must_repeat)){
                ++mismatches;
                if(first_failure.empty())first_failure=
                    "COMP label-500 reentry differs at "+label+
                    " native_left="+std::to_string(current.left)+
                    " previous_used="+std::to_string(current.used);
            }
        }
        // Source L10430-10433 and L11480-11486. Carry REAL*4 TLEFT,
        // not double precision, between original KSAM iterations.
        const float proposed=ksam==current.last_ksam ? current.left :
                             current.reference+current.left;
        const auto computed=cteas::puff::substep_length({
            .sampling_step_s=proposed,
            .wind_speed_ms=original_ws,
            .puff=true,.free_slug=false,
            .subsampling=nsam<99,
            .grid_spacing_m=100.0,
            .x_sam_len=1.0,
            .substep_index=ksam,.sampling_steps=nsam
        });
        const float native_used=static_cast<float>(computed.step_s);
        const float native_left=proposed-native_used;
        if(computed.split)++short_steps;
        if(std::abs(original_left)>0.0001F)++nonzero_left;
        if(!equal_step(native_used,actual) ||
           !equal_step(native_left,original_left)){
            ++mismatches;
            if(first_failure.empty())first_failure=
                "FSTEP numerical difference at "+label+
                " proposed="+std::to_string(proposed)+
                " WS="+std::to_string(original_ws)+
                " native_TSAMP="+std::to_string(native_used)+
                " original_TSAMP="+std::to_string(actual)+
                " native_TLEFT="+std::to_string(native_left)+
                " original_TLEFT="+std::to_string(original_left);
        }else{++correct_steps;}
        current.left=native_left;
        current.used=native_used;
        current.last_ksam=ksam;
    }
    require(input.eof(),"non-whole-record DGM or I/O error");
    require(rows>0 && static_cast<int>(real_hours)==expected_hours,
            "wrong number of original DGM hours");
    if(expected_hours==143)
        require(rows==254687 && reentries==758,
                "pinned 143h DGM record/reentry counts changed");
    std::cout<<"P7_NATIVE_COMP_FSTEP_DGM_REPLAY"
             <<" ORIGINAL_HOURS="<<real_hours<<" RECORDS="<<rows
             <<" REENTRIES="<<reentries
             <<" NATIVE_SHORTENED="<<short_steps
             <<" NONZERO_ORIGINAL_TLEFT="<<nonzero_left
             <<" MATCHED="<<correct_steps
             <<" MISMATCHES="<<mismatches<<"\n";
    if(!first_failure.empty())
        throw std::runtime_error(first_failure);
    std::cout<<"P7_NATIVE_FSTEP_STEP_CONTROLLER_PARITY=PASS"
             <<" ORACLE_FEEDS=INITIAL_NSAM_REFTSAMP_WS_ONLY"
             <<" NATIVE_TRAJECTORY_PARITY=NOT_YET_ACCEPTED\n";
}
}
int main(int argc,char** argv){
    try{
        if(argc!=3)throw std::invalid_argument(
            "usage: cteas_p7_original_fstep_trace <DGM.bin> <1|6|143>");
        run(argv[1],std::stoi(argv[2]));
        return 0;
    }catch(const std::exception& error){
        std::cerr<<"P7_NATIVE_FSTEP_STEP_CONTROLLER_PARITY=FAIL "
                 <<error.what()<<"\n";
        return 1;
    }
}
