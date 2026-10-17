#include "cteas/p6e/mixdt.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
using namespace cteas::p6e;
template<class F> void rejects(F f) {
    bool threw=false;
    try {(void)f();} catch(const std::invalid_argument&) {threw=true;}
    assert(threw);
}
int main() {
    const MixdtSounding s{{0.f,100.f,300.f,500.f,800.f,1200.f,1800.f},
                          {297.f,296.f,294.f,292.f,290.f,287.f,283.f}};
    auto x=mixdt(s,400.f,200.f,0.001f);
    assert(x.tht_k>292.f && x.tht_k<294.f);
    assert(x.thtp_k>290.f && x.thtp_k<292.f);
    assert(x.dtheta_k_per_m>=0.001f);
    assert(mixdt(s,300.f,200.f,0.02f).dtheta_k_per_m==0.02f);
    MixdtSounding missing=s;
    missing.temp_k[2]=9999.f;missing.temp_k[3]=9999.f;
    assert(std::isfinite(mixdt(missing,400.f,200.f,0.001f).dtheta_k_per_m));
    rejects([&]{return mixdt(s,100.f,0.f,0.001f);});
    rejects([&]{return mixdt(s,1900.f,100.f,0.001f);});
    rejects([&]{return mixdt(s,-10.f,50.f,0.001f);});
    missing=s;missing.height_m[3]=missing.height_m[2];
    rejects([&]{return mixdt(missing,200.f,50.f,0.001f);});
    missing=s;missing.temp_k[0]=9999.f;
    rejects([&]{return mixdt(missing,0.f,50.f,0.001f);});
}
