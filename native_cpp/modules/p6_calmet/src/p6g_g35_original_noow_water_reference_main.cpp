// S4-O independent native selected WATER no-OW numeric candidate.
// Replays original Fortran WATER-only scalar observations; NOT G14/G26.
#include "cteas/p6/p6g_g35_original_noow_water_neutral.hpp"
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <algorithm>

namespace p6g=cteas::calmet::p6g;
namespace {
void require(bool good,const char* error) {
    if(!good)throw std::runtime_error(error);
}
bool close(float a,float b,float abs_tol,float rel_tol) {
    return std::isfinite(a)&&std::isfinite(b)&&
           std::abs(a-b)<=abs_tol+rel_tol*std::max(std::abs(a),std::abs(b));
}
p6g::G35SelectedWaterNeutralControls input(float ws10,int category) {
    p6g::G35SelectedWaterNeutralControls c;
    c.original_land_category=category;
    c.source_ws10_mps=ws10;
    c.explicit_reference_only=true;
    return c;
}
void rejects(p6g::G35SelectedWaterNeutralControls c) {
    bool blocked=false;
    try {(void)p6g::g35_selected_original_nowsta0_water_reference(c);}
    catch(const std::invalid_argument&) {blocked=true;}
    require(blocked,"G35 invalid original physics path was accidentally admitted");
}
void self_test() {
    for(float ws:{0.f,.0001f,.2f,1.f,2.5f,9.f,22.f}) {
        const auto out=p6g::g35_selected_original_nowsta0_water_reference(
            input(ws,52));
        require(out.roughness_m>0.f&&out.ustar_mps>0.f,"G35 neutral source friction");
        require(out.pgt==4&&out.qh_buoyancy_wm2==0.f&&
                out.wt_kelvin_mps==0.f&&out.wstar_mps==0.f,
                "G35 neutral original-water output nonzero");
        require(!out.zi_ziconv_physics_ready&&!out.g14_g26_physics_ready,
                "G35 candidate somehow promoted to production");
    }
    auto c=input(2.f,52);
    c.explicit_reference_only=false;rejects(c);
    c=input(2.f,52);c.nowsta=1;rejects(c);
    c=input(2.f,52);c.itwprog=2;rejects(c);
    c=input(2.f,52);c.icoare=0;rejects(c);
    c=input(2.f,52);c.imixh=2;rejects(c);
    c=input(2.f,52);c.original_land_category=13;rejects(c);
    c=input(-1.f,52);rejects(c);
    std::cout<<"S4O_NEUTRAL_WATER_CANDIDATE_TEST_ONLY_NEGATIVES=PASS\n";
}
void compare_original_trace(const std::string& filename) {
    std::ifstream reader(filename);
    require(bool(reader),"S4O original measured vendor trace inaccessible");
    std::map<int,std::set<std::pair<int,int>>> each_hour;
    std::set<std::tuple<int,int,int>> seen;
    std::size_t rows=0;
    float max_ustar=0.f,max_roughness=0.f,max_el=0.f;
    std::string line;
    while(std::getline(reader,line)) {
        if(line.empty())continue;
        std::istringstream row(line);
        int i=0,j=0,hour=0,land=0,pgt=0;
        float qh=0.f,ustar=0.f,el=0.f,zi=0.f,
              wstar=0.f,z0=0.f,wt=0.f,ws10=0.f;
        require(bool(row>>i>>j>>hour>>land>>pgt>>qh>>ustar>>el>>zi>>
                        wstar>>z0>>wt>>ws10),"S4O original water trace parse error");
        std::string trailing;
        require(!(row>>trailing),"S4O original trace row unexpected fields");
        require(i>=1&&i<=82&&j>=1&&j<=85&&
                seen.emplace(i,j,hour).second,"S4O invalid or repeated water cell");
        require(land>=50&&land<=55,"S4O original GEO contains foreign LU");
        require(std::isfinite(zi)&&zi>=49.999f&&zi<=3000.001f,
                "S4O actual WATER ZI invalid; ZI native model not implemented");
        auto source=input(ws10,land);
        const auto native=p6g::g35_selected_original_nowsta0_water_reference(source);
        require(!native.zi_ziconv_physics_ready&&!native.g14_g26_physics_ready,
                "S4O internal science admission leak");
        require(pgt==native.pgt&&qh==native.qh_buoyancy_wm2&&
                wt==native.wt_kelvin_mps&&wstar==native.wstar_mps,
                "S4O selected original water buoyancy, stability or WSTAR differ");
        require(close(native.el_m,el,2048.f,1.e-6f),
                "S4O selected original neutral Monin-Obukhov parameter differs");
        require(close(native.roughness_m,z0,1.e-10f,8.e-6f),
                "S4O selected original water Hosker Z0 differs");
        require(close(native.ustar_mps,ustar,2.e-8f,5.e-5f),
                "S4O selected original water neutral USTAR differs");
        max_ustar=std::max(max_ustar,std::abs(native.ustar_mps-ustar));
        max_roughness=std::max(max_roughness,std::abs(native.roughness_m-z0));
        max_el=std::max(max_el,std::abs(native.el_m-el));
        each_hour[hour].emplace(i,j);
        ++rows;
    }
    require(rows==378&&each_hour.size()==6,
            "S4O requires all 63 genuine water cells, six actual hours");
    const auto& first=each_hour.begin()->second;
    require(first.size()==63,"S4O genuine NOAA water grid dimension changed");
    for(const auto& [hour,indices]:each_hour) {
        (void)hour;
        require(indices.size()==63&&indices==first,
                "S4O missing or changing original water coordinates across hours");
    }
    std::cout<<"S4O_NATIVE_ORIGINAL_WATER_63_CELLS_X_6H_378_RECORDS_SELECTED_NEUTRAL=PASS_SCOPED\n"
             <<"S4O_ORIGINAL_WATER_NEUTRAL_MAX_ABS_USTAR_MPS="<<max_ustar<<"\n"
             <<"S4O_ORIGINAL_WATER_NEUTRAL_MAX_ABS_Z0_M="<<max_roughness<<"\n"
             <<"S4O_ORIGINAL_WATER_NEUTRAL_MAX_ABS_EL_M="<<max_el<<"\n"
             <<"S4O_NATIVE_WATER_ZI_ZICONV_AND_FULL_45_FIELDS=NOT_RUN\n"
             <<"S4O_G14_G26_PRODUCTION=NOT_ACCEPTED\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2&&std::string(argv[1])=="--self-test") {
            self_test();return 0;
        }
        if(argc!=2) {
            std::cerr<<"Usage: cteas_p6g_g35_original_nowsta0_water_reference "
                        "--self-test | <fresh vendor-only WATER numeric trace>\n";
            return 2;
        }
        compare_original_trace(argv[1]);
        return 0;
    }catch(const std::exception& error) {
        std::cerr<<"S4O_G35_ORIGINAL_SELECTED_NEUTRAL_WATER_FAILED "
                 <<error.what()<<"\n";
        return 1;
    }
}
