#include "cteas/puff/original_comp_exit.hpp"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace cteas::puff;
namespace {
void require(bool good,const char* why){if(!good)throw std::runtime_error(why);}
void run() {
    const OriginalCompPuffBounds bound{.xb=0.0F,.xe=10.0F,.yb=-2.0F,.ye=9.0F};
    using X=OriginalCompExitReason;
    require(original_comp_before_step_exit({0.0F,0.0F},{0.0F,0.0F})==X::ExhaustedMass,
            "zero-mass puff not removed before wind");
    require(original_comp_before_step_exit({0.0F,4.0F},{-3.0F,0.0F})==X::Active,
            "positive QALL incorrectly retired");
    require(original_comp_before_step_exit({0.0F,0.0F},{-1.0F,-0.5F})==X::ExhaustedMass,
            "negative QALL not retired");
    require(original_comp_before_step_exit({1.0F},{-1.0F})==X::ExhaustedMass,
            "exactly zero TOTAL mass not retired");
    require(original_comp_after_step_exit(0.0F,-2.0F,bound)==X::Active &&
            original_comp_after_step_exit(10.0F,9.0F,bound)==X::Active,
            "original domain edges must be inclusive");
    require(original_comp_after_step_exit(std::nextafter(10.0F,11.0F),0.0F,bound)
            ==X::OutsideComputationalDomain &&
            original_comp_after_step_exit(2.0F,std::nextafter(-2.0F,-3.0F),bound)
            ==X::OutsideComputationalDomain &&
            original_comp_after_step_exit(2.0F,std::nextafter(9.0F,10.0F),bound)
            ==X::OutsideComputationalDomain &&
            original_comp_after_step_exit(-0.0001F,1.0F,bound)
            ==X::OutsideComputationalDomain,
            "original center-based strict .LT/.GT comparison changed");
    for(const auto& bad: {
        OriginalCompPuffBounds{0,0,-2,9},
        OriginalCompPuffBounds{0,10,9,-2},
        OriginalCompPuffBounds{std::numeric_limits<float>::quiet_NaN(),10,-2,9}
    }) {
        bool rejected=false;
        try{(void)original_comp_after_step_exit(1,1,bad);}
        catch(const std::invalid_argument&){rejected=true;}
        require(rejected,"invalid CALPUFF computation bound accepted");
    }
    bool rejected=false;
    try{(void)original_comp_before_step_exit({1,2},{2});}
    catch(const std::invalid_argument&){rejected=true;}
    require(rejected,"inconsistent QM/QU length accepted");
    rejected=false;
    try{(void)original_comp_before_step_exit({std::numeric_limits<float>::quiet_NaN()},{1});}
    catch(const std::invalid_argument&){rejected=true;}
    require(rejected,"nonfinite QA mass accepted");
    std::cout<<"P7_NATIVE_COMP_ORIGINAL_EXIT_DECISIONS=PASS"
             <<" SOURCE_L10450_10457_QALL_REAL4=YES"
             <<" SOURCE_L11400_11413_CENTER_BOUNDARIES=YES"
             <<" EQUAL_BOUNDARY_KEPT=YES"
             <<" DOMAIN_FROM_CALPUFF_NOT_MET_ARRAY=YES"
             <<" FULL_AUTO_ROLLDN=NOT_YET_ACCEPTED\n";
}
}
int main() {
    try{run();return 0;}
    catch(const std::exception& e){
        std::cerr<<"P7_NATIVE_COMP_ORIGINAL_EXIT_DECISIONS=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
