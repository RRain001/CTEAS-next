#pragma once
// P4 READ62 JDAT=2 FSL input seam, NOT an equivalent UP.DAT writer.
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <istream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>
namespace cteas::met_input::p4 {
struct ParseError:std::runtime_error{using std::runtime_error::runtime_error;};
struct Sample{double value=0.0;bool valid=false;};
struct Level{Sample pressure_hpa,height_m,temperature_c,wind_direction_deg,wind_speed_mps;};
struct Timestamp{int year=0,month=0,day=0,hour=0;auto operator<=>(const Timestamp&) const=default;};
struct Sounding{
 Timestamp utc;double station_lat_deg=0.0,station_lon_deg=0.0;int station_elevation_m=0;
 std::string wind_unit;std::vector<Level> levels;
 std::size_t raw_level_count=0,dropped_non_decreasing_pressure=0;
 std::vector<std::string> diagnostics;
};
struct Options{
 double pstop_hpa=500.0;
 bool drop_missing_height=false,drop_missing_temperature=false,drop_missing_direction=false,drop_missing_speed=false;
};
inline std::string trim(std::string_view v){
 const auto a=v.find_first_not_of(" \t\r\n");
 return a==std::string_view::npos?std::string{}:std::string(v.substr(a,v.find_last_not_of(" \t\r\n")-a+1));
}
inline std::string field(const std::string& line,std::size_t pos,std::size_t width,const char* tag){
 if(line.size()<pos+width)throw ParseError(std::string("short FSL ")+tag);
 return trim(std::string_view(line).substr(pos,width));
}
inline int integer(const std::string& s,const char* name){
 if(s.empty())throw ParseError(std::string("empty ")+name);
 std::size_t n=0;
 try{const int v=std::stoi(s,&n);if(n==s.size())return v;}catch(const std::exception&){}
 throw ParseError(std::string("invalid integer ")+name);
}
inline double real(const std::string& s,const char* name,int implied=0){
 if(s.empty())throw ParseError(std::string("empty ")+name);
 std::size_t n=0;
 try{
  double v=std::stod(s,&n);
  if(n==s.size()&&std::isfinite(v)){
   if(implied>0&&s.find('.')==std::string::npos&&s.find('e')==std::string::npos&&s.find('E')==std::string::npos)
    v/=std::pow(10.0,implied);
   return v;
  }
 }catch(const std::exception&){}
 throw ParseError(std::string("invalid numeric ")+name);
}
inline std::chrono::sys_seconds when(const Timestamp& t){
 using namespace std::chrono;
 const year_month_day ymd{year{t.year},month{static_cast<unsigned>(t.month)},day{static_cast<unsigned>(t.day)}};
 if(!ymd.ok()||t.hour<0||t.hour>23)throw ParseError("invalid FSL UTC time");
 return sys_days{ymd}+hours{t.hour};
}
inline int month_number(const std::string& n){
 constexpr std::array<std::string_view,12> months={"JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"};
 for(std::size_t i=0;i<months.size();++i)if(n==months[i])return static_cast<int>(i+1);
 throw ParseError("invalid FSL month");
}
inline Sample sample(double v,bool valid){return {valid?v:0.0,valid};}
inline Level decode_level(const std::string& line,std::string_view unit){
 const double p=real(field(line,7,7,"PRES"),"PRES");
 const double z=real(field(line,14,7,"HEIGHT"),"HEIGHT");
 const double t=real(field(line,21,7,"TEMP"),"TEMP",1);
 const int wd=integer(field(line,35,7,"WD"),"WD");
 const int ws=integer(field(line,42,7,"WS"),"WS");
 return {sample(p,p>0.0&&p<=1500.0),sample(z,z<32767.0),sample(t,std::abs(t-3276.7)>1e-7),
         sample(wd,wd!=32767&&wd>=0&&wd<=360),
         sample(unit=="kt"?ws*0.514791:ws/10.0,ws!=32767&&ws>=0)};
}
inline bool drop_level(const Level& l,const Options& o){
 return (o.drop_missing_height&&!l.height_m.valid)||(o.drop_missing_temperature&&!l.temperature_c.valid)||
        (o.drop_missing_direction&&!l.wind_direction_deg.valid)||(o.drop_missing_speed&&!l.wind_speed_mps.valid);
}
inline std::vector<Sounding> read_fsl(std::istream& in,const Options& opt={}){
 if(!(opt.pstop_hpa>0.0&&opt.pstop_hpa<=1500.0&&std::isfinite(opt.pstop_hpa)))throw ParseError("invalid PSTOP");
 std::vector<Sounding> out;std::string a,b,c,d,line;
 while(std::getline(in,a)){
  if(trim(a).empty())throw ParseError("blank FSL header");
  if(!std::getline(in,b)||!std::getline(in,c)||!std::getline(in,d))throw ParseError("truncated FSL header");
  Sounding s;
  s.utc.hour=integer(field(a,7,7,"hour"),"hour");
  s.utc.day=integer(field(a,14,7,"day"),"day");
  s.utc.month=month_number(field(a,27,3,"month"));
  s.utc.year=integer(field(a,34,4,"year"),"year");
  (void)when(s.utc);
  const auto lat_h=field(b,28,1,"lat hemisphere"),lon_h=field(b,35,1,"lon hemisphere");
  if((lat_h!="N"&&lat_h!="S")||(lon_h!="E"&&lon_h!="W"))throw ParseError("invalid hemisphere");
  s.station_lat_deg=real(field(b,21,7,"latitude"),"latitude")*(lat_h=="S"?-1:1);
  s.station_lon_deg=real(field(b,29,6,"longitude"),"longitude")*(lon_h=="W"?-1:1);
  // Backwards-compatible 3-6-decimal coordinate suffix. Original Fortran
  // ignores everything after the old header2 fixed fields. Keep the exact
  // coordinates only if they round consistently to the legacy F7.2/F6.2.
  const auto exact_pos=b.find("P4EXACT_LAT=");
  if(exact_pos!=std::string::npos){
   std::istringstream ext(b.substr(exact_pos));
   std::string lat_tok,lon_tok;
   if(!(ext>>lat_tok>>lon_tok) || lat_tok.rfind("P4EXACT_LAT=",0)!=0
      || lon_tok.rfind("P4EXACT_LON=",0)!=0)
    throw ParseError("malformed P4EXACT FSL extension");
   const double exact_lat=real(lat_tok.substr(12),"P4EXACT latitude");
   const double exact_lon=real(lon_tok.substr(12),"P4EXACT longitude");
   if(std::abs(exact_lat-s.station_lat_deg)>0.011
      ||std::abs(exact_lon-s.station_lon_deg)>0.011)
    throw ParseError("P4EXACT coordinates disagree with legacy fixed fields");
   s.station_lat_deg=exact_lat;
   s.station_lon_deg=exact_lon;
  }
  if(std::abs(s.station_lat_deg)>90.0||std::abs(s.station_lon_deg)>180.0)throw ParseError("invalid coordinates");
  s.station_elevation_m=integer(field(b,36,6,"elevation"),"elevation");
  const int lines=integer(field(c,28,7,"NLINES"),"NLINES");
  if(lines<4||lines>204)throw ParseError("invalid NLINES (MXLEV 200)");
  s.wind_unit=field(d,47,2,"WSUNIT");
  if(s.wind_unit!="ms"&&s.wind_unit!="kt")throw ParseError("unsupported WSUNIT");
  s.raw_level_count=static_cast<std::size_t>(lines-4);
  double prev=0.0;bool have_prev=false;
  for(int j=0;j<lines-4;++j){
   if(!std::getline(in,line))throw ParseError("truncated levels");
   auto lv=decode_level(line,s.wind_unit);
   if(!lv.pressure_hpa.valid)throw ParseError("invalid pressure");
   if(have_prev&&lv.pressure_hpa.value>=prev){++s.dropped_non_decreasing_pressure;continue;}
   prev=lv.pressure_hpa.value;have_prev=true;
   if(!drop_level(lv,opt))s.levels.push_back(std::move(lv));
  }
  if(s.levels.size()<2)s.diagnostics.push_back("FEWER_THAN_TWO_LEVELS");
  if(!s.levels.empty()){
   const auto& v=s.levels.front().height_m;
   if(!v.valid||v.value>s.station_elevation_m)s.diagnostics.push_back("FIRST_LEVEL_ABOVE_SURFACE_OR_MISSING");
   if(s.levels.back().pressure_hpa.value>opt.pstop_hpa+1.0)s.diagnostics.push_back("TOP_BELOW_PSTOP");
   for(std::size_t j=1;j<s.levels.size();++j){
    const auto& x=s.levels[j-1].height_m;const auto& y=s.levels[j].height_m;
    if(x.valid&&y.valid&&y.value<x.value){s.diagnostics.push_back("HEIGHT_DECREASES");break;}
   }
  }
  if(!out.empty()){
   const auto gap=when(s.utc)-when(out.back().utc);
   if(gap<=std::chrono::seconds{0})s.diagnostics.push_back("DUPLICATE_OR_NON_MONOTONIC_TIME");
   else if(gap>std::chrono::hours{12})s.diagnostics.push_back("TIME_GAP_OVER_12H");
  }
  out.push_back(std::move(s));
 }
 return out;
}
} // namespace cteas::met_input::p4
