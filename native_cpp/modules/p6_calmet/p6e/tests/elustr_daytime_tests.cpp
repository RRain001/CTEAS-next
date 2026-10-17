#include "cteas/p6e/elustr_daytime.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void rejects(F f){bool yes=false;try{f();}catch(const std::invalid_argument&){yes=true;}assert(yes);}
int main(){
    DaytimeElustrInput a;
    a.nx=4;a.ny=1;a.landuse={12,12,12,55};
    a.z0={0.03f,0.05f,0.2f,0.08f};
    a.u1={3.f,0.0f,7.f,1.f};a.v1={1.f,0.f,1.f,0.f};
    a.rho={1.15f,1.2f,1.0f,1.0f};
    a.temp_k={300.f,280.f,290.f,300.f};
    a.heat_flux_initial={100.f,150.f,0.f,100.f};
    a.initial_ustar={-7777.f,-7777.f,-7777.f,-7777.f};
    a.initial_el={-7777.f,-7777.f,-7777.f,-7777.f};
    const auto c=elustr_daytime(a);
    assert(c.ustar_ms[0]>=0.05f&&c.ustar_ms[1]>=0.05f);
    assert(c.monin_obukhov_m[0]<0.f);
    assert(c.monin_obukhov_m[2]==-9.9e9f); // neutral original sentinel
    assert(c.ustar_ms[3]==-7777.f&&c.monin_obukhov_m[3]==-7777.f);
    a.ipsifcn=1;
    auto z=elustr_daytime(a);
    assert(z.monin_obukhov_m[0]<0.f);
    a.heat_flux_initial[0]=-0.1f;rejects([&]{(void)elustr_daytime(a);});
    a.heat_flux_initial[0]=100.f;a.ipsifcn=2;rejects([&]{(void)elustr_daytime(a);});
    a.ipsifcn=0;a.z0[0]=0.f;rejects([&]{(void)elustr_daytime(a);});
}
