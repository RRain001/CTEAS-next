// Original 143-hour REAL*4 COMP sampling-cadence audit.
// Original DGM supplies the independent IOLD/NSAM/IPNO/REFTSAMP comparator
// ONLY. The C++ production sampling_cadence and POINTS1 release_cadence
// calculate the new-puff schedule without reading expected NSAM as input.
// Old-puff apparent divergence from final (post-rise) WS is DIAGNOSTIC ONLY,
// since COMP calculates its old-puff cadence using pre-RISEWIND ADVECT WS.
#include "cteas/puff/release.hpp"
#include "cteas/puff/step_integration.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>

namespace {
using namespace cteas::puff;
struct OriginalRecord {
    std::array<std::int32_t,24> i{};
    std::array<float,64> r{};
};
static_assert(sizeof(OriginalRecord)==352);
static_assert(std::endian::native==std::endian::little);
void need(bool p,const char* reason) {
    if(!p) throw std::runtime_error(reason);
}
std::uint32_t bits(float x) {
    return std::bit_cast<std::uint32_t>(x);
}
int main_run(const std::string& file,const int expected_hours) {
    std::ifstream input(file,std::ios::binary);
    need(bool(input),"original COMP DGM is missing");
    std::set<std::pair<int,int>> unique_new,unique_old;
    std::set<int> hours;
    std::size_t records=0,correct_new=0,wrong_new=0;
    std::size_t old_measured=0,old_postwind_differences=0;
    std::size_t effective_delta_count=0,tleft_positive_count=0;
    int first_effective_delta_hour=0,first_effective_delta_puff=0;
    int first_positive_tleft_hour=0,first_positive_tleft_puff=0;
    std::size_t old_pre_exact=0,old_pre_mismatch=0;
    int first_error_hour=0;
    int first_old_hour=0,first_old_puff=0,first_old_ns=0,first_old_pred=0;
    int first_pre_hour=0;
    OriginalRecord rec;
    while(input.read(reinterpret_cast<char*>(&rec),sizeof(rec))) {
        ++records;
        const int hour=rec.i[1], puff=rec.i[3], nsam=rec.i[10];
        const int nsstr=rec.i[11],iold=rec.i[12],ipno=rec.i[14],ksam=rec.i[16];
        const float wsvar=rec.r[18],postwind=rec.r[11];
        const float reftsamp=rec.r[17];
        const float effective_tsamp=rec.r[62];
        const float tleft=rec.r[60];
        need(std::isfinite(effective_tsamp) && effective_tsamp>0.0F &&
             std::isfinite(tleft),
             "original COMP TLEFT/TSAMP is not finite");
        if(bits(effective_tsamp)!=bits(reftsamp)){
            ++effective_delta_count;
            if(!first_effective_delta_hour){
                first_effective_delta_hour=hour;
                first_effective_delta_puff=puff;
            }
        }
        if(tleft>0.0F){
            ++tleft_positive_count;
            if(!first_positive_tleft_hour){
                first_positive_tleft_hour=hour;
                first_positive_tleft_puff=puff;
            }
        }
        need(rec.i[0]==1 && hour>202200000 && puff>0 &&
             nsam>=1 && nsam<=99 && nsstr>=1 && nsstr<=nsam &&
             ksam>=nsstr && ksam<=nsam && std::isfinite(reftsamp) &&
             reftsamp>0.0F,"malformed 143h original COMP DGM sampling row");
        hours.insert(hour);
        if(iold==0 && unique_new.emplace(hour,puff).second) {
            need(rec.i[13]==1,"only the selected point source is supported");
            ReleaseCadenceInputs q;
            q.wind_speed_ms=wsvar;
            q.emission_interval=36.0;  // DHR/(XSAMLEN*DGRIDM): 3600/100
            q.hour_seconds=3600;
            q.max_puffs=99;
            const ReleaseCadence source=release_cadence(q);
            const SamplingCadence plan=sampling_cadence({
                .new_puff=true,
                .source_type=1,
                .emission_period_s=source.emission_duration_s,
                .step_seconds=3600.0,
                .release_number=ipno,
                .wind_speed_ms=wsvar,
                .x_sam_len=1.0,
                .grid_spacing_m=100.0,
                .max_sampling_steps=99
            });
            const bool equal=plan.sampling_steps==nsam &&
                plan.start_substep==nsstr &&
                plan.old_flag==iold &&
                bits(static_cast<float>(plan.reference_step_s))==bits(reftsamp);
            if(equal) ++correct_new;
            else {
                ++wrong_new;
                if(!first_error_hour) {
                    first_error_hour=hour;
                    std::cerr<<"P7_ORIGINAL_COMP_NEW_FIRST_DIFFERENCE"
                             <<" HOUR="<<hour<<" PUFF="<<puff
                             <<" REF_NSAM="<<nsam<<" CPP_NSAM="<<plan.sampling_steps
                             <<" REF_NSSTR="<<nsstr<<" CPP_NSSTR="<<plan.start_substep
                             <<" REF_REFTSAMP="<<reftsamp
                             <<" CPP_REFTSAMP="<<plan.reference_step_s
                             <<" WSVAR="<<wsvar<<"\n";
                }
            }
        } else if(iold==1 && unique_old.emplace(hour,puff).second) {
            // This is NOT a numerical parity claim for old puffs. The DGM
            // captures WS after RISEWIND, but source L10119-10143 uses
            // ADVECT WS before entering the old-puff NSAM expression.
            const SamplingCadence guess=sampling_cadence({
                .new_puff=false,.source_type=1,
                .emission_period_s=0.0,.step_seconds=3600.0,
                .release_number=1,.wind_speed_ms=postwind,
                .x_sam_len=1.0,.grid_spacing_m=100.0,
                .max_sampling_steps=99
            });
            ++old_measured;
            if(guess.sampling_steps!=nsam) {
                ++old_postwind_differences;
                if(!first_old_hour) {
                    first_old_hour=hour;first_old_puff=puff;
                    first_old_ns=nsam;first_old_pred=guess.sampling_steps;
                }
            }
            // Real original input for the OLD cadence is the ADVECT
            // PUFFDZ-averaged wind BEFORE RISEWIND. On the first KSAM
            // of each old puff, DGM step4 samples the same cell/PUFFDZ as
            // the initial COMP L10119 ADVECT; do not use post-RISEWIND WS.
            const float ub=rec.r[9],vb=rec.r[10];
            const float speed=std::sqrt(ub*ub+vb*vb);
            need(std::isfinite(speed),"original pre-RISEWIND wind not finite");
            const float original_pre_ws=speed<0.5F?
                                         std::max(speed,0.001F):speed;
            const SamplingCadence pre=sampling_cadence({
                .new_puff=false,.source_type=1,
                .emission_period_s=0.0,.step_seconds=3600.0,
                .release_number=1,.wind_speed_ms=original_pre_ws,
                .x_sam_len=1.0,.grid_spacing_m=100.0,
                .max_sampling_steps=99
            });
            if(pre.sampling_steps==nsam &&
               pre.start_substep==nsstr && pre.old_flag==iold &&
               bits(static_cast<float>(pre.sampling_step_inverse))==
                   bits(rec.r[15]) &&
               bits(static_cast<float>(pre.reference_step_s))==
                   bits(reftsamp)) {
                ++old_pre_exact;
            } else {
                ++old_pre_mismatch;
                if(!first_pre_hour){
                    first_pre_hour=hour;
                    std::cerr<<"P7_ORIGINAL_COMP_OLD_PREWIND_FIRST_DIFFERENCE"
                             <<" HOUR="<<hour<<" PUFF="<<puff
                             <<" ORIG_NSAM="<<nsam<<" NATIVE_NSAM="<<pre.sampling_steps
                             <<" ORIG_REFTSAMP="<<reftsamp
                             <<" NATIVE_REFTSAMP="<<pre.reference_step_s
                             <<" ORIG_XSAMI="<<rec.r[15]
                             <<" NATIVE_XSAMI="<<pre.sampling_step_inverse
                             <<" ORIGINAL_ADVECT_U="<<ub
                             <<" ORIGINAL_ADVECT_V="<<vb<<"\n";
                }
            }
        }
    }
    need(input.eof(),"original COMP DGM truncated at a non-record boundary");
    if(expected_hours==143) {
        need(hours.size()==143,"not all 143 vendor COMP hours were audited");
        need(records==254687U,"vendor 143h COMP row count changed");
        need(unique_new.size()==11985U,
             "original 143h POINTS1 release episodes changed");
    } else {
        need(hours.size()==1 && records==1275U &&
             unique_new.size()==54U,
             "original first-hour COMP reference changed");
    }
    std::cout<<"P7_COMP_NEW_NATIVE_CADENCE"
             <<" HOURS="<<hours.size()
             <<" RECORDS="<<records
             <<" NEW_PUFF_EPISODES="<<unique_new.size()
             <<" NEW_EXACT="<<correct_new
             <<" NEW_MISMATCH="<<wrong_new
             <<" OLD_PUFF_EPISODES="<<old_measured
             <<" OLD_POSTRISE_WS_PROXY_DIFFERENCES="<<old_postwind_differences
             <<" OLD_PRE_RISE_WIND_EXACT="<<old_pre_exact
             <<" OLD_PRE_RISE_WIND_MISMATCH="<<old_pre_mismatch
             <<" OLD_UV=ORIGINAL_ADVECT_DGM_STEP4"
             <<" EFFECTIVE_TSAMP_DIFFERS_REF_RECORDS="<<effective_delta_count
             <<" TLEFT_POSITIVE_RECORDS="<<tleft_positive_count
             <<" FIRST_TSAMP_DIFFERENCE_HOUR="<<first_effective_delta_hour
             <<" FIRST_TSAMP_DIFFERENCE_PUFF="<<first_effective_delta_puff
             <<" FIRST_TLEFT_HOUR="<<first_positive_tleft_hour
             <<" FIRST_TLEFT_PUFF="<<first_positive_tleft_puff
             <<" ORIGINAL_SOURCE_MUTATED=NO"
             <<" FULL_NATIVE_COMP_MXSAM99=NOT_ACCEPTED\n";
    if(first_old_hour)
        std::cout<<"P7_COMP_OLD_POSTRISE_PROXY_FIRST_DIFFERENCE"
                 <<" HOUR="<<first_old_hour
                 <<" PUFF="<<first_old_puff
                 <<" REF_NSAM="<<first_old_ns
                 <<" POSTRISE_PROXY_CPP_NSAM="<<first_old_pred<<"\n";
    need(wrong_new==0,"source-ported POINTS1/COMP NEW REAL4 cadence diverges");
    need(correct_new==unique_new.size(),"new-puff cadence coverage incomplete");
    need(old_pre_mismatch==0,
         "source-ported old-puff NSAM XSAMI REFTSAMP differs from original");
    need(old_pre_exact==unique_old.size(),
         "old-puff cadence coverage incomplete");
    return 0;
}
}
int main(int argc,char** argv) {
    try {
        if(argc!=3)throw std::invalid_argument("use DGM.bin [1|143]");
        const int hours=std::stoi(argv[2]);
        if(hours!=1 && hours!=143)throw std::invalid_argument("unsupported hour span");
        return main_run(argv[1],hours);
    } catch(const std::exception& e) {
        std::cerr<<"P7_COMP_NEW_NATIVE_CADENCE=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
