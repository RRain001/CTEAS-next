#include "cteas/geo/terrain_grid.hpp"
#include "cteas/geo/grid_origin.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(int argc,char** argv) {
  if(argc!=5) {std::cerr<<"usage: cteas_p1_terrain SRTM_TIF X0_KM Y0_KM OUTPUT_CSV\n";return 2;}
  try {
    // No silent high-precision origin: the P1/P2/P3 case is defined by
    // the historical three-decimal kilometer grid.cmn, not the crop center.
    cteas::reconstruction::geo::require_frozen_hefei_origin_km(argv[2],argv[3]);
    const auto x0=cteas::reconstruction::geo::three_decimal_origin_km(argv[2])*1000.0;
    const auto y0=cteas::reconstruction::geo::three_decimal_origin_km(argv[3])*1000.0;
    const auto source=cteas::reconstruction::geo::read_srtm_geotiff(argv[1]);
    const auto r=cteas::reconstruction::geo::grid_geotiff_terrain_utm50n(
       source,{x0,y0,100.0,50,50});
    std::ofstream out(argv[4]);
    if(!out) throw std::runtime_error("P1 cannot write CSV");
    // Preserve enough decimal digits to audit the pre-F8.1 Fortran mean.
    out<<"i,j,hits,elevation_m\n"<<std::fixed<<std::setprecision(9);
    for(std::size_t j=0;j<50;++j)for(std::size_t i=0;i<50;++i) {
      const auto k=j*50+i;
      out<<i+1<<","<<j+1<<","<<r.point_count[k]<<","<<r.elevation_m[k]<<"\n";
    }
    if(!out)throw std::runtime_error("P1 CSV incomplete");
    std::cout<<"P1_ACCEPTED="<<r.accepted_points<<" OUTSIDE="<<r.rejected_outside
             <<" NODATA="<<r.rejected_missing<<"\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
