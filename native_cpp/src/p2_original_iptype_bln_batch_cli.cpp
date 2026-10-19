// #123 D8: independent C++ original-BLN IPTYPE batch comparator.
// Exact authentic BLN produced and SHA-admitted by original D6 workflow;
// never use diagnostic GEOS polygons or the frozen EXACT_AREA_V1 producer.
#include "cteas/geo/ctgproc_original_bln_pnpoly.hpp"
#include <iostream>
#include <stdexcept>
#include <string>

using cteas::reconstruction::geo::OriginalBlnIptypeR4;

int main(int argc,char** argv) {
  try {
    if(argc!=2)throw std::runtime_error("D8_REQUIRES_AUTHENTIC_BLN_PATH");
    const auto classifier=OriginalBlnIptypeR4::load_coastrd_bln(
        argv[1],533.215f,3942.629f,553.215f,3962.629f);
    unsigned n=0;
    if(!(std::cin>>n)||n==0||n>100000)
      throw std::runtime_error("D8_POINT_COUNT_INVALID");
    for(unsigned i=0;i<n;++i) {
      float x=0.f,y=0.f;
      if(!(std::cin>>x>>y))
        throw std::runtime_error("D8_INPUT_POINT_PARSE_FAILED");
      std::cout<<classifier.iptype(x,y,true)<<'\n';
    }
    std::cin>>std::ws;
    if(!std::cin.eof())
      throw std::runtime_error("D8_TRAILING_POINTS");
  }catch(const std::exception& e) {
    std::cerr<<"D8_CPP_FAIL_CLOSED:"<<e.what()<<'\n';
    return 2;
  }
  return 0;
}
