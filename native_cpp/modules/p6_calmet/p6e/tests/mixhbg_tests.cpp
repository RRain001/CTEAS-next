#include "cteas/p6e/mixhbg.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void rejects(F f){bool ok=false;try{f();}catch(const std::invalid_argument&){ok=true;}assert(ok);}
int main(){
    // Unstable convective growth with threshold flux.
    MixhbgInput a;
    a.wt_mks=0.05f;a.gamma_kperm=0.005f;a.el_m=-200.f;a.ustar_ms=0.3f;
    a.zicbgold_m=200.f;
    auto r=mixhbg_lapse2(a);
    assert(std::isfinite(r.ziconv_m)&&r.ziconv_m>a.zicbgold_m);
    assert(r.gamma_kperm==a.gamma_kperm);
    // Positive Lmo (stable): total collapse.
    a.el_m=50.f;r=mixhbg_lapse2(a);
    assert(r.ziconv_m==0.f);
    // Negative buoyancy flux below the threshold: collapse when IZICRLX=0.
    a.el_m=-100.f;a.wt_mks=0.0005f;a.threshold_wm2perm=1.f;
    r=mixhbg_lapse2(a);
    assert(r.ziconv_m==0.f);
    // Same state with IZICRLX=1 relaxes toward equilibrium instead.
    a.izicrlx=1;r=mixhbg_lapse2(a);
    assert(r.ziconv_m>0.f&&r.ziconv_m<a.zicbgold_m);
    // Zero net buoyancy flux keeps the previous height exactly (IZICRLX=0).
    a.izicrlx=0;a.threshold_wm2perm=0.f;a.wt_mks=0.f;
    r=mixhbg_lapse2(a);
    assert(r.ziconv_m==a.zicbgold_m);
    // Deep unstable limit (EL <= -500 m) stays finite and positive.
    a.el_m=-600.f;a.wt_mks=0.002f;a.gamma_kperm=0.005f;
    a.zicbgold_m=900.f;a.threshold_wm2perm=0.f;
    r=mixhbg_lapse2(a);
    assert(std::isfinite(r.ziconv_m)&&r.ziconv_m>0.f);
    // Lapse rate is floored by DPTMIN on the growth path.
    a.gamma_kperm=0.0001f;
    r=mixhbg_lapse2(a);
    assert(r.gamma_kperm==a.dptmin_kperm);
    // Fail-closed domain validation.
    a.gamma_kperm=0.001f;a.tzicrlx_s=0.f;rejects([&]{(void)mixhbg_lapse2(a);});
    a.tzicrlx_s=800.f;a.izicrlx=2;rejects([&]{(void)mixhbg_lapse2(a);});
    a.izicrlx=0;a.zimin_m=a.zimax_m;rejects([&]{(void)mixhbg_lapse2(a);});
    a.zimin_m=50.f;a.timestep_s=0;rejects([&]{(void)mixhbg_lapse2(a);});
}
