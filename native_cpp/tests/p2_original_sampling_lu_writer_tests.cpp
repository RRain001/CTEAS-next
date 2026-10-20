#include "cteas/geo/ctgproc_original_sampling_lu_writer.hpp"
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace cteas::reconstruction::geo;
namespace {
void require(bool v,const char* m) {
  if(!v)throw std::runtime_error(m);
}
template<class F> void rejects(F f,const char* m) {
  bool threw=false;try{f();}catch(const std::exception&){threw=true;}
  require(threw,m);
}
}
int main() {
  // Small synthetic fixture checks format/zero-hit flags only.
  // These synthetic tests can never claim genuine Wolsong science.
  const P2Grid grid{533215.,3942629.,100.,2,1};
  OriginalSamplingRecount source{grid,
      std::vector<std::uint32_t>(2*38,0),{3,0},{0,0},55,3,0,0};
  source.counts[0]=1;
  source.counts[1]=2;
  std::ostringstream actual;
  const auto stats=write_original_sampling_lu(actual,source,false);
  require(stats.total_hits==3&&stats.nonempty_cells==1&&
          stats.missing_cells==1&&stats.fraction_fields==76,
          "D11_SYNTHETIC_SCOPED_STATS");
  const std::string result=actual.str();
  require(result.find("LU.DAT")!=std::string::npos&&
          result.find("FRACTION\nUTM\n")!=std::string::npos,
          "D11_LU_HEADER_CONTRACT");
  require(result.find("0.333")!=std::string::npos&&
          result.find("0.667")!=std::string::npos,
          "D11_F6_3_REAL4_FORMAT");
  require(result.find("Missing")!=std::string::npos,
          "D11_MISSING_FLAG");
  rejects([&]{
      std::ostringstream out;write_original_sampling_lu(out,source);
  },"D11_ONLY_VERIFIED_WOLSONG_DOMAIN_BY_DEFAULT");
  auto bad=source;bad.samples[0]=4;
  rejects([&]{
      std::ostringstream out;write_original_sampling_lu(out,bad,false);
  },"D11_REJECT_BAD_CELL_HIT_CONSERVATION");
  bad=source;bad.fill_ocean[1]=1;
  rejects([&]{
      std::ostringstream out;write_original_sampling_lu(out,bad,false);
  },"D11_NOT_SILENT_LMARFILL");
  std::cout<<"D11_ORIGINAL_LU_WRITER=PASS_SYNTHETIC_ONLY"
           <<" REAL_ORIGINAL_SOURCE_PARITY=NOT_RUN\n";
  return 0;
}
