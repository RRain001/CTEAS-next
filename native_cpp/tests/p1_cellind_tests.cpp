#include "cteas/geo/terrain_grid.hpp"
#include <stdexcept>
#include <iostream>
using namespace cteas::reconstruction::geo;
int main() {
  TerrainGridSpec s{1000,2000,100,2,2};
  auto check=[&](float x,float y,int wantx,int wanty){
    const auto v=cell_index_terrel(x,y,s);
    if(wantx<0){if(v)throw std::runtime_error("unexpected grid hit");}
    else if(!v || static_cast<int>(v->first)!=wantx||static_cast<int>(v->second)!=wanty)
      throw std::runtime_error("CELLIND boundary mismatch");
  };
  check(1000,2000,0,0);
  check(1099,2099,0,0);
  check(1100,2000,1,0);
  check(1000,2100,0,1);
  check(999,2000,-1,-1);
  check(1000,1999,-1,-1);
  check(1200,2150,-1,-1);
  // NoData may not be silently dropped or converted to a fabricated zero.
  const cteas::atmos::Shape2D shape(1,1);
  TerrainRaster invalid{cteas::atmos::Array2D<std::int16_t>(shape),
                        cteas::atmos::ValidityMask2D(shape),
                        {117.0,0.001,0.0,32.0,0.0,-0.001},
                        "unverified-source-wkt",-32768};
  bool refused_nodata=false;
  try { (void)grid_geotiff_terrain_utm50n(invalid,s); }
  catch(const std::invalid_argument& e) {
    refused_nodata=std::string(e.what()).find("unsupported NoData")!=std::string::npos;
  }
  if(!refused_nodata) throw std::runtime_error("P1 failed to reject source NoData");
  std::cout<<"P1 original CELLIND boundary and explicit missing-source rejection PASS\n";
}
