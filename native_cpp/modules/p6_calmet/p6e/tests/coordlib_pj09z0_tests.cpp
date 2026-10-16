// P6E COORDLIB UTM geometry software test.
//
// Pins the REAL*4 bits produced by `surface_solar_grid` for the frozen 2022
// case grid against the unmodified-source COORDLIB chain
// (reference/coordlib_utm_driver.f + engine/vendor/src/CALMET_v6.5.0_L150223/
// coordlib.for, sha256 abe1d9a69ed7a4b8fa98bf1092cd668feef9f5612619ae3a8b565ec5b9be3c93).
// The companion CTest `p6e_coordlib_utm_original_source_parity` re-derives the
// same numbers from the original Fortran over a wider parameter matrix.
#include "cteas/p6e/surface_solar.hpp"
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <utility>
using namespace cteas::p6e;
namespace {
std::uint32_t bits(float v) {
    std::uint32_t b=0U;
    std::memcpy(&b,&v,sizeof(b));
    return b;
}
template<class F> void rejects(F f) {
    bool ok=false;
    try { f(); } catch(const std::invalid_argument&) { ok=true; }
    assert(ok);
}
// CalmetDat21Header for the frozen case stores XORIGR/YORIGR/DGRID in metres.
constexpr float kXOrigM=510885.f,kYOrigM=3531269.f,kDGridM=100.f;
} // namespace
int main() {
    // Reference-system initialisation for zone 50 / WGS-84 (SPHDZ0 spheroid 12).
    const UtmProjection p=utm_north_projection(50);
    assert(p.zone==50);
    assert(p.A==6378137.0);
    assert(p.ES==0.0066943799901975076);
    assert(p.ESP==0.0067394967423333859);
    assert(p.E0==0.99832429845278114);
    assert(p.E1==0.0025146070605398473);
    assert(p.E2==2.6390465943820355e-06);
    assert(p.E3==3.4180460866818588e-09);
    assert(p.KS0==0.9996);
    assert(p.X0==500000.0);
    assert(p.Y0==0.0);
    assert(p.ML0==0.0);
    assert(!p.polar);
    assert(p.LON0==2.0420352248333651);
    rejects([]{(void)utm_north_projection(0);});
    rejects([]{(void)utm_north_projection(61);});

    // 50x50 real-case grid: the port must reproduce the original GLOBE/COORDLIB
    // REAL*4 bits exactly (cell (1,1), (50,25), (25,26), (50,50)).
    const auto g=surface_solar_grid(50U,50U,50,kXOrigM,kYOrigM,kDGridM);
    assert(g.nx==50U&&g.ny==50U);
    const auto at=[&](std::size_t i,std::size_t j){
        return std::pair<std::uint32_t,std::uint32_t>(
            bits(g.latitude_deg[j*50U+i]),bits(g.longitude_east_deg[j*50U+i]));
    };
    assert(at(0U,0U).first==0x41FF5772U);
    assert(at(0U,0U).second==0x42EA3B39U);
    assert(at(49U,24U).first==0x41FF83ACU);
    assert(at(49U,24U).second==0x42EA55C7U);
    assert(at(24U,25U).first==0x41FF8596U);
    assert(at(24U,25U).second==0x42EA483CU);
    assert(at(49U,49U).first==0x41FFB1DDU);
    assert(at(49U,49U).second==0x42EA55CDU);

    // The grid walks latitude down-range and longitude eastward monotonically.
    for(std::size_t j=1;j<50U;++j)
        assert(g.latitude_deg[j*50U+0U]>g.latitude_deg[(j-1U)*50U+0U]);
    for(std::size_t i=1;i<50U;++i)
        assert(g.longitude_east_deg[0U*50U+i]>g.longitude_east_deg[0U*50U+i-1U]);

    // A single-cell grid is allowed; degenerate inputs fail closed.
    const auto one=surface_solar_grid(1U,1U,50,kXOrigM,kYOrigM,kDGridM);
    assert(one.latitude_deg.size()==1U&&one.longitude_east_deg.size()==1U);
    rejects([&]{(void)surface_solar_grid(0U,50U,50,kXOrigM,kYOrigM,kDGridM);});
    rejects([&]{(void)surface_solar_grid(50U,0U,50,kXOrigM,kYOrigM,kDGridM);});
    rejects([&]{(void)surface_solar_grid(50U,50U,50,kXOrigM,kYOrigM,0.f);});
    rejects([&]{(void)surface_solar_grid(50U,50U,0,kXOrigM,kYOrigM,kDGridM);});
    rejects([]{(void)surface_solar_grid(50U,50U,50,
                                        std::numeric_limits<float>::quiet_NaN(),
                                        0.f,1.f);});
    return 0;
}
