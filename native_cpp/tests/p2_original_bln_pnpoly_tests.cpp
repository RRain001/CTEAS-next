#include "cteas/geo/ctgproc_original_bln_pnpoly.hpp"
#include "cteas/geo/ctgproc_original_coast_policy.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
using namespace cteas::reconstruction::geo;
namespace {
void ensure(bool ok,const char* what){if(!ok)throw std::runtime_error(what);}
template<class F> void rejects(F f,const char* why){
  bool failed=false;
  try{f();}catch(const std::exception&){failed=true;}
  ensure(failed,why);
}
std::vector<OriginalBlnVertexR4> box(float low,float high){
  return {{low,low},{high,low},{high,high},{low,high},{low,low}};
}
struct ScopedTemp {
  std::filesystem::path dir;
  ~ScopedTemp(){std::error_code ec;std::filesystem::remove_all(dir,ec);}
};
void test_pnpoly_real4(){
  const auto r=box(0.f,10.f);
  ensure(original_pnpoly_r4(5.f,5.f,r)==1,"PNPOLY interior");
  ensure(original_pnpoly_r4(-1.f,5.f,r)==-1,"PNPOLY exterior");
  ensure(original_pnpoly_r4(0.f,5.f,r)==0,"PNPOLY vertical edge");
  ensure(original_pnpoly_r4(5.f,0.f,r)==0,"PNPOLY horizontal edge");
  ensure(original_pnpoly_r4(10.f,10.f,r)==0,"PNPOLY vertex");
  ensure(original_pnpoly_r4(10.125f,5.f,r)==-1,"PNPOLY exterior right");
  auto rev=r;
  std::reverse(rev.begin(),rev.end());
  ensure(original_pnpoly_r4(5.f,5.f,rev)==1,"PNPOLY must ignore ring winding");
  ensure(original_pnpoly_r4(0.f,5.f,rev)==0,"PNPOLY edge independent of winding");
  std::vector<OriginalBlnVertexR4> duplicate=r;
  duplicate.insert(duplicate.begin()+2,r[1]);
  ensure(original_pnpoly_r4(5.f,5.f,duplicate)==1,"PNPOLY zero-length edge");
  rejects([&]{(void)original_pnpoly_r4(NAN,5.f,r);},"PNPOLY NaN point must fail");
  const std::array<OriginalBlnVertexR4,2> invalid{{{0.f,0.f},{1.f,1.f}}};
  rejects([&]{(void)original_pnpoly_r4(5.f,5.f,invalid);},
          "PNPOLY fewer than three vertices must fail closed");
}
void test_iptpe_five_levels_and_boundary(){
  std::vector<OriginalBlnPolygonR4> regions;
  for(int k=1;k<=4;++k) {
    const float v=float(k-1);
    regions.push_back({k,0,k,0,box(v,10.f-v)});
  }
  OriginalBlnIptypeR4 classify(std::move(regions));
  ensure(classify.iptype(-1.f,5.f)==0,"outside ocean0");
  ensure(classify.iptype(.5f,5.f)==1,"marine land1");
  ensure(classify.iptype(1.5f,5.f)==2,"lake2");
  ensure(classify.iptype(2.5f,5.f)==3,"island3");
  ensure(classify.iptype(5.f,5.f)==4,"pond4");
  ensure(classify.iptype(0.f,5.f)==0,"L1 coast edge ocean0");
  ensure(classify.iptype(1.f,5.f)==2,"L2 edge lake2");
  ensure(classify.iptype(2.f,5.f)==2,"L3 edge lake2");
  ensure(classify.iptype(3.f,5.f)==4,"L4 edge pond4");
  ensure(classify.iptype(-1.f,5.f,false)==1,"LCOAST false default land1");
  const OriginalCoastControl cfg{true,true,false,false,55,
                                 OriginalLanduseSource::HistoricalUsgs38};
  ensure(original_lugrid_coastal_category(cfg,52,classify.iptype(-1.f,5.f))==55,
         "LUGRID sea remapping");
  ensure(original_lugrid_coastal_category(cfg,54,classify.iptype(-1.f,5.f))==54,
         "LUGRID estuary exception");
  ensure(!original_lugrid_coastal_category(cfg,55,classify.iptype(1.5f,5.f)),
         "LUGRID landward ocean samples removed");
  rejects([&]{(void)classify.iptype(NAN,0.f);},"IPTYPE NaN point must fail");
}
void test_original_coastrd_bln(){
  const auto dir=std::filesystem::temp_directory_path()/"cteas_issue123_d4_bln_contract";
  ensure(!std::filesystem::exists(dir),"synthetic BLN temp directory collides");
  std::filesystem::create_directories(dir);
  ScopedTemp cleanup{dir};
  const auto path=dir/"synthetic_original_coastrd.bln";
  {
    std::ofstream out(path);
    out<<"5,0,\"1,0,123\"\n";
    for(const auto& p:box(0.f,10.f))out<<p.x_km<<","<<p.y_km<<"\n";
    out<<"5,1,\"2,0,124\"\n";
    for(const auto& p:box(1.f,9.f))out<<p.x_km<<","<<p.y_km<<"\n";
  }
  auto c=OriginalBlnIptypeR4::load_coastrd_bln(path,0.f,0.f,10.f,10.f);
  ensure(c.polygon_count()==2,"COASTRD polygon count");
  ensure(c.iptype(.5f,5.f)==1,"COASTRD main coast land1");
  ensure(c.iptype(5.f,5.f)==2,"COASTRD nested lake2");
  ensure(c.iptype(1.f,5.f)==2,"COASTRD inner lake edge2");
  rejects([&]{(void)OriginalBlnIptypeR4::load_coastrd_bln(path,15.f,15.f,20.f,20.f);},
          "COASTRD wrong-grid domain must fail");
  std::ofstream(path,std::ios::app)<<"garbled-header\n";
  rejects([&]{(void)OriginalBlnIptypeR4::load_coastrd_bln(path,0.f,0.f,10.f,10.f);},
          "COASTRD malformed BLN must fail");
}
} // namespace
int main(){
  test_pnpoly_real4();
  test_iptpe_five_levels_and_boundary();
  test_original_coastrd_bln();
  std::cout<<"ISSUE123_D4_ORIGINAL_PNPOLY_R4_BNL_SYNTHETIC_PASS "
              "ORIGINAL_FORTRAN_SAME_INPUT_PARITY=NOT_RUN "
              "EXACT_AREA_V1=UNCHANGED\n";
  return 0;
}
