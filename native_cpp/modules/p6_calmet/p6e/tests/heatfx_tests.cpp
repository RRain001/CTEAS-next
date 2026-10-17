#include "cteas/p6e/heatfx.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void rejects(F fn){bool b=false;try{fn();}catch(const std::invalid_argument&){b=true;}assert(b);}
int main(){
    HeatFluxInput x;
    x.nx=3;x.ny=1;x.mcloud=1;x.station_cloud={2,8};
    x.nearest={1,2,1};x.landuse={12,12,55};
    x.sun={-0.1f,0.7f,0.8f};x.temp_k={280.f,290.f,300.f};
    x.cloud_grid={0.f,0.f,0.f};x.albedo={0.2f,0.2f,0.2f};
    x.bowen={1.f,1.5f,2.f};x.soil_heat_fraction={0.1f,0.1f,0.1f};
    x.anthropogenic_wm2={5.f,5.f,5.f};x.initial_qh={-7777.f,-7777.f,-7777.f};
    x.ha1=1000.f;x.ha2=50.f;x.hb1=-0.75f;x.hb2=3.f;
    x.hc1=1e-13f;x.hc2=30.f;x.hc3p1=1.5f;
    auto r=heatfx(x);
    assert(r.shortwave_wm2.size()==3);
    assert(r.sensible_wm2[0]==-0.1f);  // original negative sentinel at night
    assert(r.sensible_wm2[1]>0.f);
    assert(r.sensible_wm2[2]==-7777.f); // water unmodified
    assert(r.shortwave_wm2[2]>0.f); // water shortwave computed!
    x.mcloud=3;x.cloud_grid={1.f,0.f,0.5f};
    assert(heatfx(x).shortwave_wm2[1]>0.f);
    x.cloud_grid[0]=-1.f;rejects([&]{(void)heatfx(x);});
    x.cloud_grid[0]=0.f;x.hc3p1=0.f;rejects([&]{(void)heatfx(x);});
    x.hc3p1=1.5f;x.temp_k[0]=9999.f;rejects([&]{(void)heatfx(x);});
    x.temp_k[0]=280.f;x.mcloud=5;rejects([&]{(void)heatfx(x);});
}
