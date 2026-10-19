#include "cteas/geo/ctgproc_original_sampling_recount.hpp"
#include <ogr_geometry.h>
#include <array>
#include <cmath>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>
using namespace cteas::reconstruction::geo;
namespace {
void check(bool valid,const char* msg){if(!valid)throw std::runtime_error(msg);}
template<class F> void rejects(F fn,const char* msg){
  bool rejected=false;
  try{fn();}catch(const std::exception&){rejected=true;}
  check(rejected,msg);
}
std::unique_ptr<OGRGeometry> square(){
  OGRLinearRing ring;
  ring.addPoint(0,0);ring.addPoint(10000,0);
  ring.addPoint(10000,10000);ring.addPoint(0,10000);ring.addPoint(0,0);
  auto p=std::make_unique<OGRPolygon>();
  p->addRing(&ring);
  return p;
}
std::size_t idx(int c){
  for(std::size_t i=0;i<kGlccUsgs92Classes.size();++i)
    if(kGlccUsgs92Classes[i]==c)return i;
  throw std::runtime_error("test unsupported class");
}
GlccRawResult source(){
  P2Grid g{0.,0.,10000.,3,1};
  GlccRawResult r{g,32652,1,{1,1,1,1},
      std::vector<std::uint32_t>(3*38,0),
      std::vector<std::uint32_t>{2,2,0},{},4,1,{}};
  const auto point=[&](int cat,int x,int ci) {
    r.diagnostic_mesh.push_back({1,1,1,1,cat,float(x),5.f,ci,1});
  };
  point(52,5,1);point(55,5,1); // first grid land
  point(52,15,2);point(54,15,2); // second grid ocean
  r.diagnostic_mesh.push_back({1,1,1,1,11,100.f,100.f,0,0});
  ++r.counts[idx(52)];
  ++r.counts[idx(55)];
  ++r.counts[38+idx(52)];
  ++r.counts[38+idx(54)];
  return r;
}
}
int main(){
  std::vector<OriginalCoastPolygon> polygons;
  polygons.push_back({1,square()});
  OriginalGshhsPointClassifier classifier(std::move(polygons));
  const auto before=source();
  OriginalCoastControl off{};
  const auto same=recount_glcc_original_coast(before,off,nullptr);
  check(same.counts==before.counts&&same.samples==before.cell_samples,
        "LCOAST off must perfectly reuse old P2A counts");
  check(same.outside==1&&same.included==4&&same.rejected_coast==0,
        "recount cannot change baseline original point numbers");
  rejects([&]{(void)same.fraction(2,0,idx(52));},
          "missing cell must not silently become ocean");

  OriginalCoastControl ctrl{true,true,true,false,55,
                            OriginalLanduseSource::HistoricalUsgs38};
  const auto result=recount_glcc_original_coast(before,ctrl,&classifier);
  check(result.included==3&&result.rejected_coast==1&&result.outside==1,
        "LUGRID original remap/landward-reject totals");
  check(result.samples==std::vector<std::uint32_t>({1,2,0}),
        "original NGRID ISUM only from included real samples");
  check(result.counts[idx(52)]==1&&result.counts[idx(55)]==0,
        "landward 52 accepted, 55 removed");
  check(result.counts[38+idx(55)]==1&&result.counts[38+idx(54)]==1,
        "ocean 52→55 and original 54 estuary special case");
  check(result.fraction(0,0,idx(52))==1.&&
        result.fraction(1,0,idx(54))==.5&&
        result.fraction(1,0,idx(55))==.5,
        "ORIGINAL_SAMPLING NGRID/ISUM still distinct 52/55");
  check(result.fill_ocean[2]==1&&result.samples[2]==0&&
        result.fraction(2,0,idx(55))==1.,
        "SVGRID LMARFILL must set DISPLAY ocean without inventing counts");
  OriginalCoastControl only_fill{true,false,true,false,55,
                                 OriginalLanduseSource::HistoricalUsgs38};
  const auto no_swap=recount_glcc_original_coast(before,only_fill,&classifier);
  check(no_swap.counts==before.counts&&no_swap.included==before.included,
        "LMARFILL alone must not change existing source point counts");
  check(no_swap.fill_ocean[2]&&no_swap.samples[2]==0,
        "LMARFILL sea-center empty only");
  rejects([&]{(void)recount_glcc_original_coast(before,ctrl,nullptr);},
          "LCOAST missing classifier must fail closed");
  auto invalid=before;invalid.diagnostic_mesh.pop_back();
  rejects([&]{(void)recount_glcc_original_coast(invalid,off,nullptr);},
          "incomplete native P2-A mesh trace must fail closed");
  std::cout<<"ISSUE123_D3_ORIGINAL_RECOUNT_SYNTHETIC_PASS "
             "P2A_BASELINE_COUNTS_PRESERVED=true "
             "ORIGINAL_FORTRAN_HITS_PARITY=NOT_RUN "
             "FROZEN_EXACT_AREA=UNCHANGED\n";
  return 0;
}
