#include "cteas/p6e/mixhmc.hpp"
#include <cassert>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void rejects(F f){bool ok=false;try{f();}catch(const std::invalid_argument&){ok=true;}assert(ok);}
int main(){
    MixhmcInput a;
    a.wt_mks=0.1f;a.gamma_kperm=0.002f;a.dptt_k=0.5f;
    auto r=mixhmc_lapse2(a);
    assert(r.ziconv_m>0.f&&r.ziconv_m<=a.zimax_m);
    assert(r.dptt_k>=0.f&&r.gamma_kperm==a.gamma_kperm);
    a.wt_mks=-0.01f;r=mixhmc_lapse2(a);
    assert(r.ziconv_m==0.f&&r.dptt_k==a.dptt_k);
    a.izicrlx=1;a.threshold_wm2perm=1.f;a.wt_mks=0.01f;
    r=mixhmc_lapse2(a);
    assert(r.ziconv_m>0.f); // relaxation, not instant collapse
    a.tzicrlx_s=0.f;rejects([&]{(void)mixhmc_lapse2(a);});
    a.tzicrlx_s=800.f;a.izicrlx=2;rejects([&]{(void)mixhmc_lapse2(a);});
}
