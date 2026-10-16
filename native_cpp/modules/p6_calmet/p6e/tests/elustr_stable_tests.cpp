#include "cteas/p6e/elustr_stable.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void bad(F f){bool ok=false;try{f();}catch(const std::invalid_argument&){ok=true;}assert(ok);}
int main(){
    StableElustr x;
    x.nx=3;x.ny=1;x.station_cloud={2,10};
    x.landuse={12,12,55};x.nearest={1,2,1};x.z0={0.1f,0.2f,0.1f};
    x.u1={0.f,5.f,1.f};x.v1={0.f,2.f,1.f};
    x.rho={1.2f,1.2f,1.2f};x.temp_k={280.f,290.f,280.f};
    x.cloud_grid={0.2f,0.8f,0.2f};x.heat_flux_initial={-0.1f,-0.1f,-0.1f};
    auto y=stable_elustr(x);
    assert(y.qh_wm2[0]<0.f&&y.qh_wm2[1]<0.f);
    assert(y.ustar_ms[0]>=0.05f&&y.monin_obukhov_m[0]>0.f);
    assert(y.qh_wm2[2]==-0.1f);
    assert(y.ustar_ms[2]==-7777.f&&y.monin_obukhov_m[2]==-7777.f);
    x.mcloud=3;
    assert(stable_elustr(x).ustar_ms[1]>0.f);
    x.heat_flux_initial[0]=0.f;bad([&]{(void)stable_elustr(x);});
    x.heat_flux_initial[0]=-0.1f;x.z0[0]=0.f;
    bad([&]{(void)stable_elustr(x);});
    x.z0[0]=0.1f;x.cloud_grid[0]=-0.1f;
    bad([&]{(void)stable_elustr(x);});
}
