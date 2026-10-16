#include "cteas/p6e/mixht_stable.hpp"
#include <cassert>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void bad(F fn){bool yes=false;try{fn();}catch(const std::invalid_argument&){yes=true;}assert(yes);}
int main(){
    StableMixingInput x;
    x.nx=4;x.ny=1;
    x.landuse={12,12,12,55};
    x.qh_wm2={-1.f,-10.f,-0.1f,-0.1f};
    x.ustar_ms={0.05f,0.2f,2.f,0.3f};
    x.el_m={10.f,30.f,500.f,50.f};
    x.fcori_s={0.00007f,0.00007f,0.00007f,0.00007f};
    x.initial_zi_m={-7777.f,-7777.f,-7777.f,-7777.f};
    x.initial_ziconv_m={-7777.f,-7777.f,-7777.f,-7777.f};
    auto r=mixht_stable(x);
    assert(r.zi_m[0]>=x.zimin&&r.zi_m[0]<=x.zimax);
    assert(r.zi_m[1]>r.zi_m[0]);
    assert(r.ziconv_m[2]==0.f);
    assert(r.zi_m[3]==-7777.f&&r.ziconv_m[3]==-7777.f);
    x.qh_wm2[0]=0.f;bad([&]{(void)mixht_stable(x);});
    x.qh_wm2[0]=-1.f;x.fcori_s[0]=0.f;bad([&]{(void)mixht_stable(x);});
    x.fcori_s[0]=0.00007f;x.zimin=x.zimax+1.f;
    bad([&]{(void)mixht_stable(x);});
}
