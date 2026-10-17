#include "cteas/geo/source_inputs.hpp"
#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <utility>
namespace cteas::reconstruction::geo {
namespace {
std::string trimmed(std::string s) {
  const auto a=s.find_first_not_of(" \t\r\n");
  if(a==std::string::npos) return {};
  const auto b=s.find_last_not_of(" \t\r\n");
  return s.substr(a,b-a+1);
}
std::string required_line(std::istream& in,const char* what) {
  std::string line;
  if(!std::getline(in,line)) throw std::runtime_error(std::string("P2: missing ")+what);
  return trimmed(std::move(line));
}
template <class T> T singleton(const std::string& str,const char* what) {
  std::istringstream in(str);
  T value{};
  std::string rest;
  if(!(in>>value)||(in>>rest)) throw std::runtime_error(std::string("P2: malformed ")+what);
  return value;
}
}
GenericLanduse read_generic_landuse(const std::filesystem::path& path) {
  std::ifstream input(path);
  if(!input) throw std::runtime_error("P2: cannot open GEN landuse: "+path.string());
  if(required_line(input,"signature")!="GENERIC.LANDUSE 1.0")
    throw std::runtime_error("P2: invalid GENERIC.LANDUSE signature");
  if(singleton<int>(required_line(input,"selector"),"selector")!=1)
    throw std::runtime_error("P2: unsupported GENERIC selector");
  if(required_line(input,"description").empty())
    throw std::runtime_error("P2: empty source description");
  if(required_line(input,"coordinate kind")!="LL")
    throw std::runtime_error("P2: unsupported coordinate kind");
  GenericLanduse result;
  result.datum=required_line(input,"datum");
  if(result.datum!="ESR-S")
    throw std::runtime_error("P2: unsupported datum (expected ESR-S)");
  if(required_line(input,"angular unit")!="DEG")
    throw std::runtime_error("P2: expected degree units");
  const int count=singleton<int>(required_line(input,"number of classes"),"class count");
  if(count<1 || count>256) throw std::runtime_error("P2: invalid class count");
  std::istringstream class_stream(required_line(input,"class list"));
  std::unordered_set<int> known;
  for(int i=0;i<count;++i) {
    int c=0;
    if(!(class_stream>>c)||c<=0||!known.insert(c).second)
      throw std::runtime_error("P2: invalid/duplicate/short class list");
    result.categories.push_back(c);
  }
  std::string extra;
  if(class_stream>>extra) throw std::runtime_error("P2: trailing class list token");
  std::string line;
  std::size_t line_number=8;
  while(std::getline(input,line)) {
    ++line_number;
    if(trimmed(line).empty())
      throw std::runtime_error("P2: blank point record at line "+std::to_string(line_number));
    std::istringstream row(line);
    LandusePoint point;
    if(!(row>>point.usgs92_category>>point.longitude_deg>>point.latitude_deg)||
       (row>>extra)||!known.contains(point.usgs92_category)||
       !std::isfinite(point.longitude_deg)||!std::isfinite(point.latitude_deg)||
       point.longitude_deg< -180 || point.longitude_deg>180 ||
       point.latitude_deg< -90 || point.latitude_deg>90)
      throw std::runtime_error("P2: invalid landuse sample line "+std::to_string(line_number));
    result.points.push_back(point);
  }
  if(!input.eof()) throw std::runtime_error("P2: point stream read error");
  if(result.points.empty()) throw std::runtime_error("P2: no landuse points");
  return result;
}
}  // namespace cteas::reconstruction::geo
