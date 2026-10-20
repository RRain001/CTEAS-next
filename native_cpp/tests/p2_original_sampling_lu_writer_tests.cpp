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
  // #160 C1: inland mode may only change UTM header, site comment and
  // grid. The existing 52N Wolsong default must remain byte-equivalent.
  require(result.find("  52N   ")!=std::string::npos &&
          result.find("Produced by CTEAS C++ ORIGINAL_SAMPLING D11")!=std::string::npos,
          "D11_WOLSONG_HEADER_DEFAULT_NOT_CHANGED");
  auto inland=source;
  inland.grid=P2Grid{503385.,3523769.,100.,2,1};
  std::ostringstream inland_out;
  const auto inland_stats=write_original_sampling_lu(
      inland_out,inland,false,50,
      "Produced by CTEAS C++ ORIGINAL_SAMPLING #160 (Hefei GLCC historical)",
      "SHA-admitted historical GLCC; inland LCOAST=F; original parity NOT_RUN");
  require(inland_stats.total_hits==3&&inland_stats.missing_cells==1&&
          inland_stats.fraction_fields==76,
          "P2C_INLAND_WRITER_INTEGER_ACCOUNTING");
  require(inland_out.str().find("  50N   ")!=std::string::npos &&
          inland_out.str().find("503.385")!=std::string::npos &&
          inland_out.str().find("3523.769")!=std::string::npos &&
          inland_out.str().find("0.333")!=std::string::npos &&
          inland_out.str().find("Missing")!=std::string::npos,
          "P2C_INLAND_UTM50_F63_AND_MISSING_CONTRACT");
  std::ostringstream other_zone;
  write_original_sampling_lu(other_zone,inland,false,49,
      "P2-C new-site producer","Original-style subpoints; science NOT_RUN",'S');
  require(other_zone.str().find("  49S   ")!=std::string::npos,
          "P2C_GENERIC_UTM49S_HEADER");
  rejects([&]{
      std::ostringstream out;write_original_sampling_lu(out,inland,false,61);
  },"P2C_REJECT_INVALID_ZONE");
  rejects([&]{
      std::ostringstream out;write_original_sampling_lu(out,source,true,50);
  },"D11_REJECT_WOLSONG_UTM_HEADER_OVERRIDE");
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
