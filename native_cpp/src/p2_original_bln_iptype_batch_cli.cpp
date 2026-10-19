// Issue #123 D8: same-authentic-BLN / identical REAL*4 point batch oracle.
// This program has NO GEOS source geometry and NO production P2-A link.
// It is an independent diagnostic for original COASTRD/IPTYPE/PNPOLY parity.
#include "cteas/geo/ctgproc_original_bln_pnpoly.hpp"
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
namespace geo=cteas::reconstruction::geo;

int main(int argc,char** argv) {
  try {
    if(argc!=3)throw std::runtime_error("D8_EXPECT_BNL_AND_CASES_PATH");
    auto bln=geo::OriginalBlnIptypeR4::load_coastrd_bln(
        argv[1],533.215f,3942.629f,553.215f,3962.629f);
    if(bln.polygon_count()<1)throw std::runtime_error("D8_EMPTY_BLN");
    std::ifstream in(argv[2]);
    if(!in)throw std::runtime_error("D8_CASE_INPUT_MISSING");
    int count=0;
    if(!(in>>count)||count<40000||count>500000)
      throw std::runtime_error("D8_UNEXPECTED_CASE_COUNT");
    for(int i=0;i<count;++i) {
      float x=0.f,y=0.f;
      if(!(in>>x>>y)||!std::isfinite(x)||!std::isfinite(y))
        throw std::runtime_error("D8_BAD_POINT_COORDINATE");
      std::cout<<bln.iptype(x,y)<<"\n";
    }
    in>>std::ws;
    if(!in.eof())throw std::runtime_error("D8_EXTRA_CASE_DATA");
    return 0;
  }catch(const std::exception& e){
    std::cerr<<"D8_CPP_ORIGINAL_IPTYPE_FAIL_CLOSED: "<<e.what()<<"\n";
    return 2;
  }
}
