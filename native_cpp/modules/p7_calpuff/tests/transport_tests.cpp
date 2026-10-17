#include "cteas/puff/transport.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
#include <string>
using namespace cteas::puff;
namespace {
template<class Function>void must_fail(Function f) {
    bool threw=false;
    try {f();} catch(const std::exception&) {threw=true;}
    assert(threw);
}
WindField wind(double u,double v,double w) {
    WindField x;
    x.nx=3;x.ny=2;x.nz=2;x.spacing_m=100;
    x.level_m={10,30};
    x.u.assign(12,static_cast<float>(u));
    x.v.assign(12,static_cast<float>(v));
    x.w.assign(12,static_cast<float>(w));
    return x;
}
}
int main(int argc, char** argv) {
    auto g=wind(1,0,0);
    g.validate();
    auto vx=g.velocity(150,50,20);
    assert(vx[0]==1&&vx[1]==0&&vx[2]==0);
    PointRelease s{100,50,20,{2,0.5}};
    PuffTransport p(2);
    p.emit(s,10);
    p.advect(g,10);
    assert(p.packets().size()==1&&p.packets()[0].id==1);
    assert(p.packets()[0].x_m==110);
    auto b=p.balance();
    assert(b.total==1&&b.active==1&&b.released[0]==20&&b.inventory[0]==20);
    assert(b.released[1]==5&&b.inventory[1]==5);
    p.advect(wind(20,0,0),10);
    b=p.balance();
    assert(b.active==0&&b.outflow[0]==20&&b.outflow[1]==5&&b.inventory[0]==0);
    p.emit(s,10);
    b=p.balance();
    assert(b.total==2&&b.active==1&&b.released[0]==40);
    must_fail([&]{p.emit(PointRelease{0,0,0,{-1,1}},1);});
    assert(p.balance().total==2);
    must_fail([&]{p.emit(s,0);});
    must_fail([&]{p.advect(g,-1);});
    auto bad=g;bad.u.pop_back();
    must_fail([&]{bad.validate();});
    bad=g;bad.u[0]=std::nanf("");
    must_fail([&]{bad.validate();});
    bad=g;bad.level_m={30,10};
    must_fail([&]{bad.validate();});
    auto z=level_centers_from_zface({0,20,40});
    assert(z.size()==2&&z[0]==10&&z[1]==30);
    must_fail([&]{(void)level_centers_from_zface({0,20,20});});
    // Bilinear interpolation of x-fastest original Fortran grid:
    auto interp=g;
    for(int j=0;j<interp.ny;++j)for(int i=0;i<interp.nx;++i)
      for(int k=0;k<interp.nz;++k)
        interp.u[(k*interp.ny+j)*interp.nx+i]=float(i+2*j+3*k);
    const auto speed=interp.velocity(100,100,20);
    // Midpoint of 4 surrounding grid-cell centres, then mid-layer.
    assert(std::abs(speed[0]-3.0)<1e-9);
    const std::string control=R"(
! NSPEC=2 !
! NPT1=1 !
! IPTU=8 !
! X=500.000,3540.436,70.000,0,2,11.110,293,0,2.222E+05,0 !
)";
    auto source=point_source_from_control(ControlFile::parse(control));
    assert(source.x_m==500000.0 && source.z_m==70.0);
    assert(source.y_m==static_cast<double>(static_cast<float>(3540.436))*1000.0);
    assert(source.rate_per_s[0]==222200&&source.rate_per_s[1]==0);
    must_fail([&]{(void)point_source_from_control(ControlFile::parse(
        R"(! NSPEC=2 ! ! NPT1=2 ! ! IPTU=8 ! ! X=500,3540,70,0,2,11,293,0,1,0 !)" ));});
    // A wrong IPTU value may otherwise turn Bq/s into an unmarked mass rate.
    must_fail([&]{(void)point_source_from_control(ControlFile::parse(
        R"(! NSPEC=2 ! ! NPT1=1 ! ! IPTU=1 ! ! X=500,3540,70,0,2,11,293,0,1,0 !)" ));});
    must_fail([&]{(void)point_source_from_control(ControlFile::parse(
        R"(! NSPEC=2 ! ! NPT1=1 ! ! X=500,3540,70,0,2,11,293,0,1,0 !)" ));});

    if (argc == 2) {
        // The locked-case gate accepts original puff.inp as its sole authority.
        // Do not substitute the pre-rounded stack_lonlat-to-UTM coordinates.
        const auto locked = ControlFile::read_file(argv[1]);
        const auto raw = locked.required_float_list("X");
        if (raw.size() != 10U || locked.required_int("IPTU") != 8 ||
            raw[0] != 513.385 || raw[1] != 3533.769 || raw[2] != 70.800) {
            throw std::runtime_error("P7 original-compatible 2022 point-source input drift");
        }
        const auto exact = point_source_from_control(locked);
        if (exact.x_m != static_cast<double>(static_cast<float>(raw[0]))*1000.0 ||
            exact.y_m != static_cast<double>(static_cast<float>(raw[1]))*1000.0 ||
            exact.z_m != raw[2]+raw[3] || exact.rate_per_s[0] != raw[8] ||
            exact.rate_per_s[1] != raw[9]) {
            throw std::runtime_error("P7 original source coordinates/units were re-derived or altered");
        }
        // Reconstructed absolute-UTM prototype positions are NOT the original
        // relative-grid POINTS1 values; separate original instrumentation is
        // required before declaring end-to-end position parity.
    } else if (argc != 1) {
        throw std::invalid_argument("usage: cteas_p7_transport_tests [frozen_2022_puff.inp]");
    }
}
