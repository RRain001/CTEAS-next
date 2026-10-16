#include "cteas/p6e/surfvar_multistation.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void rejects(F f){bool ok=false;try{f();}catch(const std::invalid_argument&){ok=true;}assert(ok);}
int main(){
    SurfvarMultistationInput x;
    x.nx=3;x.ny=1;x.trad_grid=3.f;x.numts=2;
    x.stations={{50.f,50.f,280.f,20},{250.f,50.f,300.f,80}};
    auto r=surfvar_multistation(x);
    assert(r.temp2d_k.size()==3&&r.rh2d_pct.size()==3);
    assert(r.temp2d_k[0]>=280.f&&r.temp2d_k[0]<300.f);
    assert(r.rh2d_pct[2]>r.rh2d_pct[0]);
    assert(r.ipcode2d[0]==0&&r.ipcode2d[2]==0);
    x.stations[0].rh_pct=9999;x.stations[1].rh_pct=9999;
    r=surfvar_multistation(x);
    assert(r.rh2d_pct[0]==80&&r.rh2d_pct[1]==80);
    x.irad=2;
    assert(surfvar_multistation(x).temp2d_k.size()==3);
    x.stations[0].temp_k=9999.f;x.stations[1].temp_k=9999.f;
    rejects([&]{(void)surfvar_multistation(x);});
    x.stations[0].temp_k=280.f;
    x.irad=3;rejects([&]{(void)surfvar_multistation(x);});
}
