#include "cteas/geo/ctgproc_original_bln_pnpoly.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <limits>
#include <regex>
#include <stdexcept>
#include <string>
#include <sstream>
#include <system_error>
#include <utility>
namespace cteas::reconstruction::geo {
namespace {
void demand(bool yes,const char* why){if(!yes)throw std::runtime_error(why);}
bool eor(bool a,bool b){return (a||b)&&!(a&&b);}
constexpr std::size_t kMaxPolygons=5000,kMaxPoints=2000000;
OriginalBlnVertexR4 parse_vertex(const std::string& line) {
  std::istringstream in(line);
  float x=0.f,y=0.f;
  char comma=0;
  if(!(in>>x>>comma>>y)||comma!=','||
     !std::isfinite(x)||!std::isfinite(y))
    throw std::invalid_argument("ORIGINAL_COASTRD_INVALID_BNL_VERTEX");
  in>>std::ws;
  if(!in.eof())throw std::invalid_argument("ORIGINAL_COASTRD_TRAILING_VERTEX_DATA");
  return {x,y};
}
} // namespace
int original_pnpoly_r4(float px,float py,
    std::span<const OriginalBlnVertexR4> points) {
  if(!std::isfinite(px)||!std::isfinite(py))
    throw std::invalid_argument("ORIGINAL_PNPOLY_NONFINITE_POINT");
  if(points.size()<3||points.size()>kMaxPoints)
    throw std::invalid_argument("ORIGINAL_PNPOLY_BAD_VERTEX_COUNT");
  int inout=-1;
  for(std::size_t i=0;i<points.size();++i){
    // Preserve Fortran implicit REAL (REAL*4), without double promotion.
    const float xi=points[i].x_km-px;
    const float yi=points[i].y_km-py;
    if(xi==0.f&&yi==0.f)return 0;
    const std::size_t j=(i+1)%points.size();
    const float xj=points[j].x_km-px;
    const float yj=points[j].y_km-py;
    if(xi==xj&&yi==yj)continue;
    const bool ix=xi>=0.f,iy=yi>=0.f,jx=xj>=0.f,jy=yj>=0.f;
    if(xi==0.f&&xj==0.f&&eor(iy,jy))return 0;
    if(yi==0.f&&yj==0.f&&eor(ix,jx))return 0;
    if(!((iy||jy)&&eor(ix,jx)))continue;
    if(iy&&jy&&eor(ix,jx)){
      inout=-inout;
      continue;
    }
    const float cross=(yi*xj-xi*yj)/(xj-xi);
    if(cross==0.f)return 0;
    if(cross>0.f)inout=-inout;
  }
  return inout;
}
OriginalBlnIptypeR4::OriginalBlnIptypeR4(
    std::vector<OriginalBlnPolygonR4> polygons):polygons_(std::move(polygons)) {
  demand(polygons_.size()<=kMaxPolygons,"ORIGINAL_IPTYPE_POLYGON_BUDGET");
  std::size_t total=0;
  for(auto& p:polygons_){
    demand(p.type>=0&&p.type<=4&&p.points.size()>=3,
           "ORIGINAL_IPTYPE_BAD_LEVEL_OR_VERTICES");
    demand(p.points.size()<=kMaxPoints-total,"ORIGINAL_IPTYPE_VERTEX_BUDGET");
    total+=p.points.size();
    p.xmin=p.ymin=std::numeric_limits<float>::infinity();
    p.xmax=p.ymax=-std::numeric_limits<float>::infinity();
    for(const auto& v:p.points){
      demand(std::isfinite(v.x_km)&&std::isfinite(v.y_km),
             "ORIGINAL_IPTYPE_NONFINITE_VERTEX");
      p.xmin=std::min(p.xmin,v.x_km);
      p.xmax=std::max(p.xmax,v.x_km);
      p.ymin=std::min(p.ymin,v.y_km);
      p.ymax=std::max(p.ymax,v.y_km);
    }
  }
}
int OriginalBlnIptypeR4::iptype(float px,float py,bool lcoast) const {
  if(!lcoast)return 1; // Fortran IPTYPE returns immediately when not LCOAST.
  if(!std::isfinite(px)||!std::isfinite(py))
    throw std::invalid_argument("ORIGINAL_IPTYPE_NONFINITE_POINT");
  int type=0; // for nshore==0, actual Fortran loop returns 0
  for(const auto& p:polygons_){
    // Fortran IPTYPE short circuits on bbox or lower/equal polygon type.
    if(px<p.xmin||px>p.xmax||py<p.ymin||py>p.ymax||type>=p.type)continue;
    const int status=original_pnpoly_r4(px,py,p.points);
    if(status<0)continue;
    if(status==0){
      if(p.type==1)type=0;
      if(p.type==2||p.type==3)type=2;
      if(p.type==4)type=4;
    }else{
      type=std::max(type,p.type);
    }
  }
  return type;
}
OriginalBlnIptypeR4 OriginalBlnIptypeR4::load_coastrd_bln(
    const std::filesystem::path& path,
    float xllk,float yllk,float xurk,float yurk) {
  if(!std::isfinite(xllk)||!std::isfinite(yllk)||!std::isfinite(xurk)||
     !std::isfinite(yurk)||xurk<=xllk||yurk<=yllk)
    throw std::invalid_argument("ORIGINAL_COASTRD_GRID_INVALID");
  demand(!std::filesystem::is_symlink(std::filesystem::symlink_status(path))&&
         std::filesystem::is_regular_file(path),"ORIGINAL_COASTRD_BNL_FILE_REQUIRED");
  demand(std::filesystem::file_size(path)<128ULL*1024ULL*1024ULL,
         "ORIGINAL_COASTRD_BNL_FILE_OVERSIZE");
  std::ifstream stream(path);
  demand(bool(stream),"ORIGINAL_COASTRD_FILE_READ_FAILED");
  // COASTEXT write (i7,',',i1,',"',i1,',',i1,',',i6,'"')
  // COASTRD list directed reads: NP,IISIDE,CPTYPE then CPTYPE=>ITYPE,SOURCE,ID.
  const std::regex hdr(
      R"BLN(^\s*([0-9]+)\s*,\s*([01])\s*,\s*"([0-4])\s*,\s*([0-9]+)\s*,\s*(-?[0-9]+)"\s*$)BLN");
  std::vector<OriginalBlnPolygonR4> polygons;
  std::string line;
  std::size_t total=0;
  while(std::getline(stream,line)){
    if(line.empty())throw std::invalid_argument("ORIGINAL_COASTRD_EMPTY_HEADER");
    std::smatch m;
    if(!std::regex_match(line,m,hdr))
      throw std::invalid_argument("ORIGINAL_COASTRD_BAD_HEADER");
    const unsigned long n=std::stoul(m[1].str());
    demand(n>=3&&n<=kMaxPoints-total,"ORIGINAL_COASTRD_VERTEX_BUDGET");
    demand(polygons.size()<kMaxPolygons,"ORIGINAL_COASTRD_POLYGON_BUDGET");
    OriginalBlnPolygonR4 p;
    p.type=std::stoi(m[3].str());p.source=std::stoi(m[4].str());
    p.polygon_id=std::stoi(m[5].str());p.iside=std::stoi(m[2].str());
    p.points.reserve(std::size_t(n));
    for(unsigned long i=0;i<n;++i){
      if(!std::getline(stream,line))
        throw std::invalid_argument("ORIGINAL_COASTRD_TRUNCATED_POINTS");
      p.points.push_back(parse_vertex(line));
    }
    total+=std::size_t(n);
    polygons.push_back(std::move(p));
  }
  demand(!polygons.empty(),"ORIGINAL_COASTRD_NO_POLYGONS");
  OriginalBlnIptypeR4 result(std::move(polygons));
  float xmin=std::numeric_limits<float>::infinity();
  float xmax=-xmin,ymin=xmin,ymax=-ymin;
  for(const auto& p:result.polygons_){
    xmin=std::min(xmin,p.xmin);xmax=std::max(xmax,p.xmax);
    ymin=std::min(ymin,p.ymin);ymax=std::max(ymax,p.ymax);
  }
  demand(!(xmax<xllk||xmin>xurk||ymax<yllk||ymin>yurk),
         "ORIGINAL_COASTRD_BNL_WRONG_DOMAIN");
  return result;
}
} // namespace cteas::reconstruction::geo
