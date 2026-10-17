#include "cteas/geo/landuse_fraction.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace cteas::reconstruction::geo;
int main() {
  GenericLanduse in;
  in.datum="ESR-S";in.categories={21,32};
  in.points={{21,117.141610855,31.939774444},
             {32,117.141610855,31.939774444},
             {21,117.141610855,31.939774444},
             {21,118.0,32.0}};
  const auto r=compute_generic_utm50n(in,{513300.,3533700.,100.,2,2});
  if(r.included!=3||r.outside!=1||r.cell_samples[0]!=3||
     std::abs(r.fraction(0,0,0)-2.0/3.0)>1e-12||
     std::abs(r.fraction(0,0,1)-1.0/3.0)>1e-12)
    throw std::runtime_error("P2 GEN synthetic count mismatch");
  bool rejected=false;
  try{(void)r.fraction(1,1,0);}catch(const std::domain_error&){rejected=true;}
  if(!rejected)throw std::runtime_error("missing cell was silently filled");
  // Original CTGPROC GLOBE/LUGRID assigns this explicitly frozen source
  // point to cell (38,49) in the 50x50 UTM50N Hefei domain.
  // Using exact x/1000 instead of float32 XMULTO wrongly gives (37,49).
  GenericLanduse edge;
  edge.datum="ESR-S"; edge.categories={21,32};
  edge.points={{21,117.1543426,31.9613914}};
  const auto reference_cell=compute_generic_utm50n(
      edge,{510884.6439571007,3531268.9269678035,100.,50,50});
  const auto expected_index=static_cast<std::size_t>(48*50+37);
  if(reference_cell.included!=1 ||
     reference_cell.cell_samples.at(expected_index)!=1 ||
     reference_cell.fraction(37,48,0)!=1.)
    throw std::runtime_error("P2 legacy COORDLIB XMULTO boundary regression");
  std::cout<<"P2 scoped synthetic count/mask PASS\n";
}
