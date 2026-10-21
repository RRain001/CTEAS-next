// S4-R0: actual READCF-selected WATER prior HFLUX source contract.
// No G14/G26 physics, original vendor field, or native G24 claim.
#include "cteas/p6/p6g_g38_selected_noow_water_hflux_source.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace p6g=cteas::calmet::p6g;
static void require(bool ok,const char* msg) {
    if(!ok)throw std::runtime_error(msg);
}
template<class F> static void rejects(F&& call,const char* msg) {
    bool rejected=false;
    try {call();} catch(const std::exception&) {rejected=true;}
    require(rejected,msg);
}
static std::string replace_once(std::string s,const std::string& a,
                                const std::string& b) {
    const auto p=s.find(a);
    require(p!=std::string::npos,"fixture READCF control missing");
    require(s.find(a,p+a.size())==std::string::npos,
            "fixture READCF control duplicated");
    s.replace(p,a.size(),b);
    return s;
}
int main(int argc,char** argv) {
    try {
        if(argc!=2||std::string(argv[1])!="--self-test")
            throw std::invalid_argument("S4R0 only supports explicit --self-test");
        p6g::GeoGrid grid{};
        grid.nx=2;grid.ny=2;grid.iwat1=50;grid.iwat2=55;
        grid.landuse={20,52,20,20};
        const std::string deck=
            "! NOWSTA = 0 !\n"
            "! ITWPROG = 0 !\n"
            "! ICOARE = 10 !\n"
            "! IMIXH = 1 !\n"
            "! NOOBS = 0 !\n"
            "! IAVET = 1 !\n"
            "! ISURFT = -1 !\n";
        const auto got=p6g::g38_selected_noow_water_hflux_source_only(
            grid,deck,true);
        require(got.original_water_cell_indices==std::vector<std::size_t>{1},
                "selected original water GEO identity");
        require(got.reference_heat.explicitly_test_only,
                "reference-only heat authority missing");
        require(got.reference_heat.initial_water_qh_wm2==
                std::vector<float>(4,0.f),"neutral selected WATER QH prior");
        require(got.reference_heat.coefficients.ha1==990.f&&
                got.reference_heat.coefficients.ha2==-30.f&&
                got.reference_heat.coefficients.hb1==-0.75f&&
                got.reference_heat.coefficients.hc2==60.f,
                "literal original BLOCK DATA source constants");
        require(!got.native_final_wind_ready&&!got.g14_g26_production_ready,
                "source admission falsely promoted to native G14/G26");
        // CRITICAL: the existing accepted G18D3 strong physics path must
        // continue to deny precisely this water GEO even with test opt-in.
        rejects([&]{(void)p6g::g18d3_source_hflux_inputs(grid,deck,true);},
                "S4R0 inadvertently bypassed frozen G18D3 water guard");
        rejects([&]{(void)p6g::g38_selected_noow_water_hflux_source_only(
                grid,deck,false);},"implicit source authority");
        auto no_water=grid;no_water.landuse[1]=20;
        rejects([&]{(void)p6g::g38_selected_noow_water_hflux_source_only(
                no_water,deck,true);},"land GEO admitted to water path");
        auto all_water=grid;all_water.landuse={52,52,52,52};
        rejects([&]{(void)p6g::g38_selected_noow_water_hflux_source_only(
                all_water,deck,true);},"all-water non-selected site");
        auto bad_lu=grid;bad_lu.iwat2=54;
        rejects([&]{(void)p6g::g38_selected_noow_water_hflux_source_only(
                bad_lu,deck,true);},"historical water category contract");
        auto bad_shape=grid;bad_shape.nx=3;
        rejects([&]{(void)p6g::g38_selected_noow_water_hflux_source_only(
                bad_shape,deck,true);},"source grid size mismatch");
        const auto changed=[&](const std::string& before,
                               const std::string& after) {
            rejects([&]{(void)p6g::g38_selected_noow_water_hflux_source_only(
                grid,replace_once(deck,before,after),true);},
                "unaccepted source branch admitted");
        };
        changed("! NOWSTA = 0 !","! NOWSTA = 1 !");
        changed("! ITWPROG = 0 !","! ITWPROG = 1 !");
        changed("! ICOARE = 10 !","! ICOARE = 0 !");
        changed("! IMIXH = 1 !","! IMIXH = 2 !");
        changed("! NOOBS = 0 !","! NOOBS = 1 !");
        changed("! IAVET = 1 !","! IAVET = 2 !");
        changed("! ISURFT = -1 !","! ISURFT = 1 !");
        changed("! NOWSTA = 0 !","");
        rejects([&]{(void)p6g::g38_selected_noow_water_hflux_source_only(
            grid,deck+"! HC1 = 0 !\n",true);},"override of original HFLUX");
        std::cout<<"S4R0_SELECTED_WATER_HFLUX_SOURCE_NEGATIVE_GATES=PASS\n"
                 <<"S4R0_NATIVE_WATER_G24_63X6=NOT_RUN\n"
                 <<"S4R0_NATIVE_45_FIELD_G14_G26=NOT_RUN\n"
                 <<"S4R0_G26_PRODUCTION=NOT_ACCEPTED\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"S4R0_FAIL_CLOSED "<<e.what()<<"\n";
        return 2;
    }
}
