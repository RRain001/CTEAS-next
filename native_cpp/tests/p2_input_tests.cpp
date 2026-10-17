#include "cteas/geo/source_inputs.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
namespace fs=std::filesystem;
namespace geo=cteas::reconstruction::geo;
template<class F> void must_throw(F f) {
  bool caught=false; try{f();}catch(const std::exception&){caught=true;}
  if(!caught) throw std::runtime_error("expected P2 rejection");
}
int main() {
  const auto dir=fs::temp_directory_path()/"cteas_p2_input_unit";
  fs::create_directories(dir);
  const auto file=dir/"synthetic.generic.txt";
  const auto put=[&](const std::string& data){
    std::ofstream out(file); if(!out||!(out<<data)) throw std::runtime_error("fixture write failed");
  };
  try {
    const std::string prefix="GENERIC.LANDUSE 1.0\n1\nGLCC sample\nLL\nESR-S\nDEG\n2\n21 32\n";
    put(prefix+"21 117.1400000 31.9400000\n32 117.1450000 31.9410000\n");
    const auto data=geo::read_generic_landuse(file);
    if(data.datum!="ESR-S"||data.categories.size()!=2||data.points.size()!=2||
       data.points[0].usgs92_category!=21||data.points[1].usgs92_category!=32)
      throw std::runtime_error("P2 parser result mismatch");
    put(prefix+"33 117.14 31.94\n");
    must_throw([&]{(void)geo::read_generic_landuse(file);});
    put(prefix+"21 117.14 91.0\n");
    must_throw([&]{(void)geo::read_generic_landuse(file);});
    put(prefix+"21 117.14 31.94 trailing\n");
    must_throw([&]{(void)geo::read_generic_landuse(file);});
    put(prefix+"\n");
    must_throw([&]{(void)geo::read_generic_landuse(file);});
    put("GENERIC.LANDUSE 1.0\n1\nGLCC\nLL\nWGS84\nDEG\n1\n21\n21 117 31\n");
    must_throw([&]{(void)geo::read_generic_landuse(file);});
    put("GENERIC.LANDUSE 1.0\n1\nGLCC\nLL\nESR-S\nDEG\n2\n21 21\n21 117 31\n");
    must_throw([&]{(void)geo::read_generic_landuse(file);});
    fs::remove_all(dir);
    std::cout<<"PASS P2 GEN input contracts; original CTGPROC comparison NOT TESTED\n";
    return 0;
  }catch(...){fs::remove_all(dir);throw;}
}
