#include "cteas/p6e/pgtstb.hpp"
#include <cassert>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void bad(F f) {
    bool yes=false;
    try{f();}catch(const std::invalid_argument&){yes=true;}
    assert(yes);
}
int main() {
    PgtInput a;
    a.nx=1; a.ny=1;
    a.u10={0}; a.v10={0}; a.sinalp={-0.8f};
    a.ccgrid={0.0f};a.ceilgrid={100};
    a.nearest={1};a.landuse={12};
    a.station_cloud={0};a.station_ceil={100};
    assert(pgtstb(a)==std::vector<int>{6});  // calm, clear night
    a.sinalp[0]=0.91f;
    assert(pgtstb(a)==std::vector<int>{1});  // strong sun, calm, clear
    a.sinalp[0]=-0.1f; a.station_cloud[0]=10; a.station_ceil[0]=69;
    assert(pgtstb(a)==std::vector<int>{4});  // low solid-overcast night
    a.landuse[0]=55;
    assert(pgtstb(a)==std::vector<int>{missing_pgt}); // water unchanged
    a.landuse[0]=12; a.mcloud=3; a.ccgrid={1.f};a.ceilgrid={69};
    assert(pgtstb(a)==std::vector<int>{4}); // gridded cloud and ceiling
    a.nearest[0]=2;bad([&]{(void)pgtstb(a);});
    a.nearest[0]=1; a.ccgrid={-0.1f};bad([&]{(void)pgtstb(a);});
    a.ccgrid={1.f};a.ceilgrid={-1};bad([&]{(void)pgtstb(a);});
    a.ceilgrid={100};a.u10={-1e38f};bad([&]{(void)pgtstb(a);});
    a.u10={0.f};a.sinalp={-2.f};bad([&]{(void)pgtstb(a);});
    a.sinalp={-0.1f};a.mcloud=5;bad([&]{(void)pgtstb(a);});
    a.mcloud=1;a.nx=2;bad([&]{(void)pgtstb(a);});
}
