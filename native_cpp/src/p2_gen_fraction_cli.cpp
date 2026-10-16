#include "cteas/geo/landuse_fraction.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace cteas::reconstruction::geo;
int main(int argc,char** argv) {
  if(argc!=5){std::cerr<<"usage: p2_gen_fraction GEN_FILE X0_KM Y0_KM OUT_CSV\n";return 2;}
  try {
    auto input=read_generic_landuse(argv[1]);
    auto r=compute_generic_utm50n(input,{std::stod(argv[2])*1000.,
                                        std::stod(argv[3])*1000.,100.,50,50});
    std::ofstream out(argv[4]);
    if(!out)throw std::runtime_error("cannot open P2 CSV output");
    out<<"i,j,samples";
    for(int cat:r.categories)out<<",cat"<<cat;
    out<<"\n"<<std::fixed<<std::setprecision(12);
    for(std::size_t j=0;j<r.grid.ny;++j)for(std::size_t i=0;i<r.grid.nx;++i) {
      const auto cell=j*r.grid.nx+i;
      out<<i+1<<","<<j+1<<","<<r.cell_samples[cell];
      for(std::size_t k=0;k<r.categories.size();++k) {
        if(r.cell_samples[cell])out<<","<<r.fraction(i,j,k);
        else out<<",MISSING";
      }
      out<<"\n";
    }
    if(!out)throw std::runtime_error("P2 CSV write error");
    std::cout<<"P2_GEN_INCLUDED="<<r.included<<" OUTSIDE="<<r.outside<<"\n";
    return 0;
  } catch(const std::exception& e) {std::cerr<<e.what()<<"\n";return 1;}
}
