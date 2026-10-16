#include "cteas/puff/original_vmass.hpp"
#include <bit>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>
namespace {
using namespace cteas::puff;
void check(bool condition,const char* reason) {
 if(!condition)throw std::runtime_error(reason);
}
VmassInputs sample(int code,int stability=4) {
 VmassInputs a;
 a.puff_code=code;a.stability_class=stability;
 a.pbl_height_m=150.0F;
 a.height_begin_m=100.0F;a.height_end_m=100.0F;
 a.sigma_z_begin_m=20.0F;a.sigma_z_end_m=20.0F;
 a.ziold_m=100.0F;a.zimax_m=200.0F;
 a.mass_mixed={60.0F,20.0F};
 a.mass_above={40.0F,10.0F};
 return a;
}
void equal(float actual,float expected,const char* what){
 check(std::bit_cast<std::uint32_t>(actual)==std::bit_cast<std::uint32_t>(expected),what);
}
template<class F> void fails(F&& f) {
 bool caught=false;try{f();}catch(const std::invalid_argument&){caught=true;}
 check(caught,"invalid VMASS input accepted");
}
void preserve(const VmassInputs& input,const VmassResult& result){
 check(result.mass_mixed.size()==input.mass_mixed.size() &&
       result.mass_above.size()==input.mass_above.size(),"missing species");
 for(std::size_t i=0;i<input.mass_mixed.size();++i)
  equal(result.mass_mixed[i]+result.mass_above[i],
        input.mass_mixed[i]+input.mass_above[i],"mass total changed");
}
}
int main(){
 try{
  // Exact source CODE 2/6: expanding lid entrains QU into QM, then
  // shrinking lid releases QM back into QU. Both species conserved.
  auto a=sample(2);
  auto first=original_vmass(a);
  check(first.puff_code==6 && first.ziold_m==150.0F &&
        first.zimax_m==200.0F,"uniform expansion lid/code wrong");
  equal(first.mass_mixed[0],80.0F,"uniform growth QM");
  equal(first.mass_above[0],20.0F,"uniform growth QU");
  preserve(a,first);
  a.puff_code=first.puff_code;a.mass_mixed=first.mass_mixed;
  a.mass_above=first.mass_above;a.ziold_m=first.ziold_m;
  a.zimax_m=first.zimax_m;a.pbl_height_m=120.0F;
  auto second=original_vmass(a);
  check(second.puff_code==6 && second.ziold_m==120.0F,
        "uniform PBL shrink branch wrong");
  equal(second.mass_mixed[0],64.0F,"uniform shrink QM");
  equal(second.mass_above[0],36.0F,"uniform shrink QU");
  preserve(a,second);
  a.pbl_height_m=250;
  const auto merged=original_vmass(a);
  check(merged.puff_code==2 && merged.ziold_m==250.0F &&
        merged.zimax_m==250.0F,"uniform 2-layer merge wrong");
  equal(merged.mass_above[0],0.0F,"merged upper layer not empty");
  preserve(a,merged);

  // CODE 4 -> 2 when PBL exceeds the center of a uniform upper puff.
  a=sample(4);a.pbl_height_m=110.0F;
  auto v=original_vmass(a);
  check(v.puff_code==2 && v.mass_above[0]==0.0F &&
        v.mass_mixed[0]==100.0F,"uniform upper-to-mixed transition");
  preserve(a,v);
  a.pbl_height_m=90.0F;
  v=original_vmass(a);
  check(v.puff_code==4 && v.mass_above[0]==40.0F,
        "uniform upper layer prematurely collapsed");

  // CODE 3 Gaussian above lid; part of upper mass enters reflected layer.
  a=sample(3);a.pbl_height_m=110.0F;
  v=original_vmass(a);
  check(v.puff_code==5 && v.ziold_m==110.0F &&
        v.zimax_m>125.0F && v.zimax_m<126.0F,
        "Gaussian above-lid partial penetration branch");
  preserve(a,v);
  a.pbl_height_m=200.0F;
  v=original_vmass(a);
  check(v.puff_code==1 && v.mass_above[0]==0.0F,
        "Gaussian upper layer not fully entrained");
  preserve(a,v);
  a=sample(3,6);a.pbl_height_m=50.0F;
  v=original_vmass(a);
  check(v.puff_code==1 && v.ziold_m==10000.0F &&
        v.zimax_m==10000.0F && v.mass_above[0]==0.0F,
        "stable Gaussian upper-layer transition");

  // CODE 1 non-stable lid falls below center of puff: code 5.
  a=sample(1);a.pbl_height_m=90.0F;
  v=original_vmass(a);
  check(v.puff_code==5 && v.reflecting_lid_m==100.0F,
        "Gaussian PBL below puff center branch");
  // CODE 5 growing lid below ZIMAX: real4 entrainment.
  a=sample(5);a.pbl_height_m=150.0F;
  v=original_vmass(a);
  check(v.puff_code==5 && v.ziold_m==150.0F &&
        v.mass_above[0]==20.0F && v.mass_mixed[0]==80.0F,
        "Gaussian two-layer growth");
  preserve(a,v);
  // Stable well-mixed code 1 becomes code 2.
  a=sample(1,5);a.sigma_z_begin_m=30000.0F;
  a.ziold_m=10000.0F;a.zimax_m=10000.0F;
  v=original_vmass(a);
  check(v.puff_code==2 && v.reflecting_lid_m==10000.0F,
        "stable Gaussian wellmixed limit");

  // Slug cases take end-height and max(SIGZB,SIGZE).
  a=sample(13);a.height_end_m=110.0F;a.pbl_height_m=110.0F;
  v=original_vmass(a);
  check(v.puff_code==15,"slug Gaussian above-layer switch");
  preserve(a,v);
  a=sample(12);a.pbl_height_m=250.0F;
  v=original_vmass(a);
  check(v.puff_code==12 && v.mass_above[0]==0.0F,
        "uniform slug mass merge");
  preserve(a,v);

  // Fail closed for invalid source branches and singular physical states.
  a=sample(9);fails([&]{(void)original_vmass(a);});
  a=sample(1);a.pbl_height_m=0;fails([&]{(void)original_vmass(a);});
  // Equal ZIMAX and ZIOLD is a LEGAL one-layer state. Vendor merges
  // layers before the two-layer denominator, so do not reject this case.
  a=sample(6);a.zimax_m=a.ziold_m;
  auto equal_lids=original_vmass(a);
  check(equal_lids.puff_code==2 && equal_lids.mass_above[0]==0.0F,
        "legal degenerate one-layer vendor state rejected");
  a=sample(6);a.sigma_z_begin_m=-1;
  fails([&]{(void)original_vmass(a);});
  a=sample(2);a.mass_above.pop_back();
  fails([&]{(void)original_vmass(a);});
  std::cout<<"P7_NATIVE_VMASS_SOURCE_BRANCHES=PASS"
           <<" Gaussian=1,3,5 Uniform=2,4,6 Slug=12,13"
           <<" REAL4_MASS_CONSERVATION=PASS"
           <<" ORIGINAL_FORTRAN_NUMERICAL_PARITY=NOT_YET_VERIFIED\\n";
  return 0;
 }catch(const std::exception& e) {
  std::cerr<<"P7_NATIVE_VMASS_SOURCE_BRANCHES=FAIL "<<e.what()<<"\\n";
  return 1;
 }
}
