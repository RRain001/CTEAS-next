// Independent selected-original water FCORI/first-layer WS10 arithmetic.
// Actual 378 rows are independently instrumented from untouched vendor copy.
// G37 never claims native G24 is executed or that full CALMET is accepted.
#include "cteas/p6/p6g_g37_water_original_fcori_wind_bridge.hpp"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
namespace p=cteas::calmet::p6g;
namespace {
constexpr std::size_t nx=82,ny=85,nz=9,plane=nx*ny;
struct Record {int i{},j{},hour{},land{};float u{},v{},ws{},fc{};};
void check(bool cond,const char* msg) {
    if(!cond)throw std::runtime_error(msg);
}
bool similar(float a,float b,float abs_tol,float rel_tol) {
    return std::isfinite(a)&&std::isfinite(b)&&
        std::abs(a-b)<=abs_tol+rel_tol*std::max(std::abs(a),std::abs(b));
}
p::G37WaterWindSource new_source(float fcoriol) {
    p::G37WaterWindSource source;
    source.nx=82;source.ny=85;source.nz=9;
    source.landuse.assign(plane,1);
    source.original_fcoriol=fcoriol;
    source.final_diagno_u_mps.assign(nz*plane,0.f);
    source.final_diagno_v_mps.assign(nz*plane,0.f);
    source.explicit_reference_only=true;
    return source;
}
void rejects(p::G37WaterWindSource s) {
    bool fail=false;
    try {(void)p::g37_original_fcori_final_wind1_surface_source(s);}
    catch(const std::invalid_argument&) {fail=true;}
    check(fail,"G37 wrongly accepted source-only/option/wind precondition");
}
void negatives() {
    auto s=new_source(0.0001f);
    s.landuse[50]=52;
    auto valid=p::g37_original_fcori_final_wind1_surface_source(s);
    check(valid.water_cells==1&&valid.fcori_s_inv[50]>0.f&&
          !valid.original_water_physics_ready&&!valid.g14_g26_production_ready,
          "G37 source-only ready leakage");
    s.explicit_reference_only=false;rejects(s);
    s.explicit_reference_only=true;s.original_fcoriol=999.f;rejects(s);
    s.original_fcoriol=0.0001f;s.final_diagno_u_mps.pop_back();rejects(s);
    s.final_diagno_u_mps.push_back(0.f);s.landuse[50]=9;rejects(s);
    s.landuse[50]=52;s.final_diagno_u_mps[50]=INFINITY;rejects(s);
    s.final_diagno_u_mps[50]=0.f;s.nz=10;rejects(s);
    std::cout<<"S4Q_WATER_FCORI_WS10_STRICT_SOURCE_NEGATIVES=PASS\n";
}
void real_source(const std::string& trace,float actual_fcoriol) {
    std::ifstream file(trace);
    check(bool(file),"S4Q independent original water trace missing");
    std::map<int,std::vector<Record>> hourly;
    std::set<std::pair<int,int>> original_water;
    std::string line;
    while(std::getline(file,line)) {
        if(line.empty())continue;
        Record r;
        std::istringstream in(line);
        check(bool(in>>r.i>>r.j>>r.hour>>r.land>>r.u>>r.v>>
                      r.ws>>r.fc),"S4Q vendor source numeric record parse failure");
        std::string tail;
        check(!(in>>tail),"S4Q original source trace has unexpected columns");
        check(r.i>=1&&r.i<=82&&r.j>=1&&r.j<=85&&
              r.land>=50&&r.land<=55,
              "S4Q original water identity out of bounds");
        hourly[r.hour].push_back(r);
        original_water.insert({r.i,r.j});
    }
    check(original_water.size()==63&&hourly.size()==6,
          "S4Q 63 authentic water points x 6h missing");
    std::size_t records=0;
    float ws_max=0.f,fc_max=0.f;
    std::set<std::pair<int,int>> comparison_cells;
    for(const auto& [hour,values]:hourly) {
        (void)hour;
        check(values.size()==63,"S4Q missing original surface wind rows");
        auto source=new_source(actual_fcoriol);
        comparison_cells.clear();
        for(const auto& r:values) {
            const auto k=std::size_t(r.j-1)*nx+std::size_t(r.i-1);
            check(source.landuse[k]==1,"S4Q duplicate original cell/hour");
            source.landuse[k]=r.land;
            // We only need the first wind plane to replay WATER's rank-2
            // U10/V10 reference alias. Unused nine-level planes are NOT
            // called actual C++ G24 output by this test.
            source.final_diagno_u_mps[k]=r.u;
            source.final_diagno_v_mps[k]=r.v;
            comparison_cells.insert({r.i,r.j});
        }
        check(comparison_cells==original_water,"S4Q water geometry changed by hour");
        const auto compared=p::g37_original_fcori_final_wind1_surface_source(source);
        check(compared.water_cells==63&&!compared.g14_g26_production_ready,
              "S4Q incorrectly admitted water physical computation");
        for(const auto& r:values) {
            const auto k=std::size_t(r.j-1)*nx+std::size_t(r.i-1);
            const float w=compared.ws10_mps[k],f=compared.fcori_s_inv[k];
            check(similar(w,r.ws,4.e-7f,2.e-5f),
                  "S4Q original Fortran WS10 differs from native first U/V plane");
            check(similar(f,r.fc,2.e-9f,1.e-6f),
                  "S4Q original SETCOM FCORI differs from native original control");
            ws_max=std::max(ws_max,std::abs(w-r.ws));
            fc_max=std::max(fc_max,std::abs(f-r.fc));
            ++records;
        }
    }
    check(records==378,"S4Q real NOAA source comparison count not 378");
    std::cout<<"S4Q_ORIGINAL_63_WATER_CELLS_X6H_NATIVE_FCORI_WS10_INPUT_ARITHMETIC=PASS_SCOPED\n"
             <<"S4Q_MAX_ABS_WS10_MPS="<<ws_max<<"\n"
             <<"S4Q_MAX_ABS_FCORI_S_INV="<<fc_max<<"\n"
             <<"S4Q_NATIVE_G24_FINAL_WIND_FROM_REAL_SOURCE=NOT_RUN\n"
             <<"S4Q_G14_G26_WATER_PRODUCTION=NOT_ACCEPTED\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2&&std::string(argv[1])=="--self-test") {
            negatives();return 0;
        }
        if(argc!=3) {
            std::cerr<<"Usage: g37 --self-test | <original WATER U/V trace> <source FCORIOL>\n";
            return 2;
        }
        const float value=std::stof(argv[2]);
        real_source(argv[1],value);
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4Q_SOURCE_ONLY_FCORI_WS10_FAILED "<<e.what()<<"\n";
        return 1;
    }
}
