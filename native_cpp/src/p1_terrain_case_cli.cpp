// #54: dynamic P1 executable. The caller MUST use #42 shared case admission.
// Retain the frozen cteas_p1_terrain legacy binary unchanged.
#include "cteas/geo/terrain_grid.hpp"
#include "cteas/geo/grid_origin.hpp"
#include <charconv>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>

namespace {
std::size_t positive_integer(std::string_view s, const char* field) {
  std::size_t value=0;
  auto [ptr,ec]=std::from_chars(s.data(),s.data()+s.size(),value);
  if(ec!=std::errc{} || ptr!=s.data()+s.size() || value==0)
    throw std::invalid_argument(std::string("P1 invalid positive integer: ")+field);
  return value;
}
double positive_decimal(const std::string& value, const char* field) {
  std::size_t n=0;
  const double result=std::stod(value,&n);
  if(n!=value.size() || !std::isfinite(result) || result<=0.0)
    throw std::invalid_argument(std::string("P1 invalid numeric grid spacing: ")+field);
  return result;
}
} // namespace

int main(int argc,char** argv) {
  if(argc!=10) {
    std::cerr<<"usage: cteas_p1_terrain_case SELECTED_TIF XREFKM YREFKM NX NY DGRIDKM ZONE N_OR_S OUTPUT_CSV\n";
    return 2;
  }
  try {
    using namespace cteas::reconstruction::geo;
    const double x0=three_decimal_origin_km(argv[2])*1000.0;
    const double y0=three_decimal_origin_km(argv[3])*1000.0;
    const auto nx=positive_integer(argv[4],"NX");
    const auto ny=positive_integer(argv[5],"NY");
    const double spacing_m=positive_decimal(argv[6],"DGRIDKM")*1000.0;
    const auto zone=positive_integer(argv[7],"IUTMZN");
    const std::string hemisphere=argv[8];
    if(zone>60 || (hemisphere!="N" && hemisphere!="S"))
      throw std::invalid_argument("P1 invalid UTM zone or hemisphere");
    if(nx>100000 || ny>100000 || nx>10'000'000/ny)
      throw std::invalid_argument("P1 grid exceeds 10-million-cell budget");
    auto source=read_srtm_geotiff(argv[1]);
    const auto computed=grid_geotiff_terrain_utm(
       source,{x0,y0,spacing_m,nx,ny},{static_cast<int>(zone),hemisphere=="S"});
    for(auto hits:computed.point_count)
      if(hits==0)
        throw std::invalid_argument("P1 uncovered grid cell (hits=0); no fabricated terrain permitted");
    std::ofstream out(argv[9],std::ios::out|std::ios::trunc);
    if(!out)throw std::runtime_error("P1 cannot write output CSV");
    out<<"i,j,hits,elevation_m\n"<<std::fixed<<std::setprecision(9);
    for(std::size_t j=0;j<ny;++j)for(std::size_t i=0;i<nx;++i) {
      const auto index=j*nx+i;
      out<<i+1<<","<<j+1<<","<<computed.point_count[index]<<","
         <<computed.elevation_m[index]<<"\n";
    }
    if(!out)throw std::runtime_error("P1 incomplete CSV write");
    std::cout<<"P1_NATIVE_PRODUCED_UNVERIFIED ACCEPTED="<<computed.accepted_points
             <<" OUTSIDE="<<computed.rejected_outside
             <<" NODATA="<<computed.rejected_missing<<"\n";
    return 0;
  } catch(const std::exception& e) {
    std::cerr<<e.what()<<"\n";
    return 1;
  }
}
