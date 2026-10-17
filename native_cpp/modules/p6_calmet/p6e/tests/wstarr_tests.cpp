#include "cteas/p6e/wstarr.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void rejects(F f){bool ok=false;try{f();}catch(const std::invalid_argument&){ok=true;}assert(ok);}
int main(){
    WstarrInput x;
    x.nx=4;x.ny=1;
    x.landuse={12,12,12,55};
    x.zi_conv_m={1000.f,1000.f,0.f,0.f};
    x.heat_flux_wm2={200.f,-0.1f,200.f,-0.1f};
    x.temp_k={300.f,300.f,300.f,300.f};
    x.rho_kgm3={1.2f,1.2f,1.2f,1.2f};
    x.initial_wstar_ms={-7777.f,-7777.f,-7777.f,-7777.f};
    auto z=wstarr(x);
    assert(z.size()==4);
    assert(z[0]>1.f);
    assert(z[1]==0.f); // nighttime zero
    assert(z[2]==0.f); // no convective layer growth
    assert(z[3]==-7777.f); // water unmodified
    x.rho_kgm3[0]=0.f;rejects([&]{(void)wstarr(x);});
    x.rho_kgm3[0]=1.2f;x.zi_conv_m[0]=-1.f;rejects([&]{(void)wstarr(x);});
    x.zi_conv_m[0]=1000.f;x.nx=5;rejects([&]{(void)wstarr(x);});
}
