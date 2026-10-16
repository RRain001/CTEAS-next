#include "cteas/geo/source_inputs.hpp"
#include <exception>
#include <iostream>
#include <string>
int main(int argc,char** argv) {
  if(argc!=3) {
    std::cerr<<"usage: cteas_geo_inspect terrain|landuse PATH\n";
    return 2;
  }
  try {
    const std::string mode=argv[1];
    if(mode=="terrain") {
      auto data=cteas::reconstruction::geo::read_srtm_geotiff(argv[2]);
      std::size_t valid=0;
      for(const auto state:data.valid.raw_states())
        if(state==cteas::atmos::Validity::valid) ++valid;
      std::cout<<"P1_INPUT_ONLY width="<<data.raw_elevation_m.nx()<<" height="
               <<data.raw_elevation_m.ny()<<" valid="<<valid
               <<" missing="<<(data.valid.size()-valid)
               <<" nodata="<<data.no_data<<"\n";
    }else if(mode=="landuse") {
      const auto data=cteas::reconstruction::geo::read_generic_landuse(argv[2]);
      std::cout<<"P2_INPUT_ONLY datum="<<data.datum
               <<" categories="<<data.categories.size()
               <<" points="<<data.points.size()<<"\n";
    }else {
      std::cerr<<"invalid inspection mode\n";
      return 2;
    }
    return 0;
  }catch(const std::exception& e) {
    std::cerr<<e.what()<<"\n";
    return 1;
  }
}
