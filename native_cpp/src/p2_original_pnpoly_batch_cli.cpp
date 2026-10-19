// Issue #123 D4: emit one PNPOLY (-1,0,+1) result per synthetic case,
// reading the very same REAL*4 input stream as the original Fortran probe.
// This is NOT an actual CTGPROC production CLI or coastline processor.
#include "cteas/geo/ctgproc_original_bln_pnpoly.hpp"
#include <cstddef>
#include <iostream>
#include <stdexcept>
#include <vector>
using cteas::reconstruction::geo::OriginalBlnVertexR4;
using cteas::reconstruction::geo::original_pnpoly_r4;

int main() {
  try {
    unsigned tests=0;
    if(!(std::cin>>tests)||tests==0||tests>25000)
      throw std::runtime_error("ORIGINAL_PNPOLY_CASE_COUNT");
    for(unsigned row=0;row<tests;++row) {
      unsigned n=0;
      float px=0.f,py=0.f;
      if(!(std::cin>>n>>px>>py)||n<3||n>1000)
        throw std::runtime_error("ORIGINAL_PNPOLY_BAD_CASE_HEADER");
      std::vector<OriginalBlnVertexR4> polygon;
      polygon.reserve(n);
      for(unsigned i=0;i<n;++i){
        OriginalBlnVertexR4 p;
        if(!(std::cin>>p.x_km>>p.y_km))
          throw std::runtime_error("ORIGINAL_PNPOLY_SHORT_CASE");
        polygon.push_back(p);
      }
      std::cout<<original_pnpoly_r4(px,py,polygon)<<"\n";
    }
    std::cin>>std::ws;
    if(!std::cin.eof())throw std::runtime_error("ORIGINAL_PNPOLY_TRAILING_INPUT");
    return 0;
  }catch(const std::exception& e){
    std::cerr<<"ORIGINAL_PNPOLY_BATCH_FAIL_CLOSED:"<<e.what()<<"\n";
    return 1;
  }
}
