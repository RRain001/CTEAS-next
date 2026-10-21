// S4-P, test-only original water IMIXH=1 / MIXHMC WT=0 ZI source comparison.
// Must not become a full G14/G26 CALMET computation or production admission.
#include "cteas/p6/p6g_g36_original_noow_water_zi.hpp"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
namespace p6g=cteas::calmet::p6g;
namespace {
using Key=std::tuple<int,int,int>; // original i,j,nhrz
struct Prior {
    int land{},pgt{};
    float qh{},ustar{},el{},zi{},wstar{},z0{},wt{},ws10{};
};
void check(bool ok,const char* message) {
    if(!ok)throw std::runtime_error(message);
}
bool near(float a,float b,float absolute,float relative) {
    return std::isfinite(a)&&std::isfinite(b)&&
           std::abs(a-b)<=absolute+relative*std::max(std::abs(a),std::abs(b));
}
void negative() {
    p6g::G36OriginalWaterZiInputs in;
    in.explicit_source_reference_only=true;
    in.original_neutral.explicit_reference_only=true;
    in.original_neutral.source_ws10_mps=2.f;
    in.original_fcori_s_inv=7.5e-5f;
    in.original_constw=.16f;
    in.original_ziminw_m=50.f;
    in.original_zimaxw_m=3000.f;
    const auto good=p6g::g36_selected_original_nowsta0_zi_source_reference(in);
    check(std::isfinite(good.zi_m)&&good.zi_m>0.f&&good.ziconv_m==0.f&&
          !good.full_original_water_state_ready&&!good.g14_g26_production_ready,
          "G36 must only expose a test-only selected reference");
    auto refused=[](const auto& x) {
        try {(void)p6g::g36_selected_original_nowsta0_zi_source_reference(x);}
        catch(const std::invalid_argument&) {return true;}
        return false;
    };
    auto x=in;x.explicit_source_reference_only=false;
    check(refused(x),"G36 implicit production request passed");
    x=in;x.original_neutral.explicit_reference_only=false;
    check(refused(x),"G36 G35 production request passed");
    x=in;x.original_neutral.nowsta=1;
    check(refused(x),"G36 nowsta!=0 passed");
    x=in;x.original_neutral.itwprog=2;
    check(refused(x),"G36 prognostic WATERP passed");
    x=in;x.original_neutral.imixh=2;
    check(refused(x),"G36 unvalidated mixing algorithm passed");
    x=in;x.original_fcori_s_inv=0.f;
    check(refused(x),"G36 invalid FCORI passed");
    x=in;x.original_constw=0.f;
    check(refused(x),"G36 invalid water CONSTW passed");
    x=in;x.original_ziminw_m=3001.f;
    check(refused(x),"G36 invalid ZI bounds passed");
    std::cout<<"S4P_NATIVE_WATER_ZI_ONLY_REFERENCE_NEGATIVES=PASS\n";
}
std::map<Key,Prior> prior_data(const std::string& name) {
    std::ifstream file(name);
    check(bool(file),"original S4N numerical water trace absent");
    std::map<Key,Prior> data;
    std::string line;
    while(std::getline(file,line)) {
        if(line.empty())continue;
        std::istringstream in(line);
        int i,j,h;
        Prior x;
        check(bool(in>>i>>j>>h>>x.land>>x.pgt>>x.qh>>x.ustar>>
                   x.el>>x.zi>>x.wstar>>x.z0>>x.wt>>x.ws10),
              "S4P invalid measured S4N source record");
        std::string extra;
        check(!(in>>extra),"S4P excess S4N source record data");
        check(data.emplace(Key{i,j,h},x).second,"S4P repeated original S4N state");
    }
    check(data.size()==378,"S4P original S4N source incomplete");
    return data;
}
void compare(const std::string& base,const std::string& zi_trace) {
    const auto prior=prior_data(base);
    std::ifstream file(zi_trace);
    check(bool(file),"genuine source instrumented original ZI trace missing");
    std::string line;
    std::map<int,std::set<std::pair<int,int>>> per_hour;
    std::set<Key> visited;
    float max_zi=0.f,max_zmech=0.f;
    while(std::getline(file,line)) {
        if(line.empty())continue;
        std::istringstream in(line);
        int i,j,h,land;
        float zi,f,constw,zmin,zmax,zold,dptt,zic,zmech;
        check(bool(in>>i>>j>>h>>land>>zi>>f>>constw>>zmin>>zmax>>
                   zold>>dptt>>zic>>zmech),"original water ZI state not parsed");
        std::string extra;
        check(!(in>>extra),"S4P unexpected original ZI trailing values");
        const Key key{i,j,h};
        const auto it=prior.find(key);
        check(it!=prior.end()&&it->second.land==land&&
              visited.insert(key).second,
              "S4P original ZI cell-hour not matched to genuine source");
        const auto& p=it->second;
        p6g::G36OriginalWaterZiInputs c;
        c.explicit_source_reference_only=true;
        c.original_neutral.explicit_reference_only=true;
        c.original_neutral.original_land_category=land;
        c.original_neutral.source_ws10_mps=p.ws10;
        c.original_fcori_s_inv=f;
        c.original_constw=constw;
        c.original_ziminw_m=zmin;
        c.original_zimaxw_m=zmax;
        const auto v=p6g::g36_selected_original_nowsta0_zi_source_reference(c);
        check(v.ziconv_m==0.f&&v.persisted_zicold_m==0.f&&
              zold==0.f&&zic==0.f,
              "S4P WATER MIXHMC neutral convective state not equivalent");
        check(near(v.zi_m,zi,5.e-3f,5.e-5f),
              "S4P native selected original ZI mismatch");
        check(near(v.zimech_m,zmech,5.e-3f,5.e-5f),
              "S4P native mechanical mixing height mismatch");
        check(near(zi,p.zi,1.e-4f,1.e-6f),
              "S4P independent prior S4N original ZI differs");
        check(!v.g14_g26_production_ready&&!v.full_original_water_state_ready,
              "S4P admitted incomplete water state into G14/G26");
        max_zi=std::max(max_zi,std::abs(v.zi_m-zi));
        max_zmech=std::max(max_zmech,std::abs(v.zimech_m-zmech));
        per_hour[h].emplace(i,j);
    }
    check(visited.size()==378&&per_hour.size()==6,"S4P original 378 water ZI entries missing");
    auto first=per_hour.begin()->second;
    check(first.size()==63,"S4P original must have exactly 63 water cells");
    for(const auto& [h,sites]:per_hour) {
        (void)h;
        check(sites==first,"S4P original grid differs between measured model hours");
    }
    std::cout<<"S4P_63_REAL_WATER_CELLS_X_6H_378_NATIVE_ZI_AND_ZIMECH_PARITY=PASS_SCOPED\n"
             <<"S4P_MAX_ABS_ZI_M="<<max_zi<<"\n"
             <<"S4P_MAX_ABS_ZIMECH_M="<<max_zmech<<"\n"
             <<"S4P_REAL_CELLS_NATIVE_FCORI_AND_G14_45_FIELD=NOT_RUN\n"
             <<"S4P_G14_G26_PRODUCTION=NOT_ACCEPTED\n";
}
} // namespace
int main(int argc,char** argv) {
    try {
        if(argc==2&&std::string(argv[1])=="--self-test") {negative();return 0;}
        if(argc!=3) {
            std::cerr<<"Usage: g36_nowsta0_water_zi --self-test | "
                        "<original S4N 378 source rows> <original S4P 378 ZI rows>\n";
            return 2;
        }
        compare(argv[1],argv[2]);
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"S4P_G36_REFERENCE_ONLY_FAILED "<<e.what()<<"\n";
        return 1;
    }
}
