#pragma once
// P5 SMERGE JDAT=8 GENERIC input and UTC hourly assembly.
// NOT a SURF.DAT-compatible writer or LPREV replacement.
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <istream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>
namespace cteas::met_input::p5 {
struct ParseError:std::runtime_error{using std::runtime_error::runtime_error;};
struct Timestamp{int year=0,month=0,day=0,hour=0;auto operator<=>(const Timestamp&) const=default;};
inline std::chrono::sys_seconds utc_second(const Timestamp& t){
 using namespace std::chrono;
 const year_month_day ymd{year{t.year},month{static_cast<unsigned>(t.month)},day{static_cast<unsigned>(t.day)}};
 if(!ymd.ok()||t.hour<0||t.hour>23)throw ParseError("invalid station date/hour");
 return sys_days{ymd}+hours{t.hour};
}
inline std::string trim(std::string_view v){
 const auto a=v.find_first_not_of(" \t\r\n");
 return a==std::string_view::npos?std::string{}:std::string(v.substr(a,v.find_last_not_of(" \t\r\n")-a+1));
}
inline std::vector<std::string> split_csv(const std::string& line){
 std::vector<std::string> f;std::size_t start=0;
 while(true){const auto pos=line.find(',',start);
  f.push_back(trim(std::string_view(line).substr(start,pos==std::string::npos?pos:pos-start)));
  if(pos==std::string::npos)return f;
  start=pos+1;
 }
}
inline int to_int(std::string_view s,const char* name){
 const auto v=trim(s);if(v.empty())throw ParseError(std::string("empty ")+name);
 std::size_t n=0;
 try{int x=std::stoi(v,&n);if(n==v.size())return x;}catch(const std::exception&){}
 throw ParseError(std::string("invalid integer ")+name);
}
inline double to_double(std::string_view s,const char* name){
 const auto v=trim(s);if(v.empty())throw ParseError(std::string("empty ")+name);
 std::size_t n=0;
 try{double x=std::stod(v,&n);if(n==v.size()&&std::isfinite(x))return x;}catch(const std::exception&){}
 throw ParseError(std::string("invalid numeric ")+name);
}
struct Value{double value=0.0;bool valid=false;};
inline Value observed(double v){return v==9999.0?Value{}:Value{v,true};}
struct SurfaceRecord{
 Timestamp utc;
 Value temperature_k,precipitation_mm,pressure_hpa,rh_percent,wind_direction_deg,wind_speed_mps,cloud_tenths,ceiling_hundreds_ft;
 std::optional<int> precipitation_code;
 std::vector<std::string> diagnostics;
};
struct Station{int id=0;std::vector<SurfaceRecord> records;};
struct Window{Timestamp start,end;};
struct HourlyRecord{Timestamp utc;std::vector<std::optional<SurfaceRecord>> by_station;};
struct Merge{std::vector<int> station_ids;std::vector<HourlyRecord> hours;std::vector<std::size_t> missing_hours_by_station;};
inline Station read_generic(std::istream& in,int expected_id){
 if(expected_id<=0)throw ParseError("invalid IFSTN");
 std::string line;
 if(!std::getline(in,line))throw ParseError("missing GENERIC header");
 auto f=split_csv(line);
 if(f.size()<3||f[0]!="GENERIC"||f[2]!="'2.0'")throw ParseError("requires GENERIC version 2.0");
 if(!std::getline(in,line))throw ParseError("missing station header");
 auto st=split_csv(line);
 if(st.size()<4||(st[0]!="Station"&&st[0]!="station")||st[1]!="ID")throw ParseError("invalid station header");
 const int id=to_int(st[3],"station ID");
 if(id!=expected_id)throw ParseError("station ID mismatches IFSTN");
 if(!std::getline(in,line))throw ParseError("missing units header");
 const auto u=split_csv(line);
 constexpr std::array<std::string_view,12> expected={"Month","Day","Year","Hour","DegC","mm","mb","%","deg","ms-1","tenths","hundreds_of_feet"};
 constexpr std::array<std::string_view,4> lower={"month","day","year","hour"};
 if(u.size()!=expected.size())throw ParseError("GENERIC units count mismatch");
 for(std::size_t i=0;i<expected.size();++i){
  if(u[i]!=expected[i]&&!(i<4&&u[i]==lower[i])&&!(i==4&&u[i]=="degC"))
   throw ParseError("GENERIC units mismatch");
 }
 Station out;out.id=id;
 while(std::getline(in,line)){
  if(trim(line).empty())throw ParseError("blank GENERIC record");
  f=split_csv(line);
  if(f.size()!=12)throw ParseError("GENERIC record must have 12 fields");
  SurfaceRecord r;
  const int hhmm=to_int(f[3],"HHMM");
  if(hhmm<0||hhmm>2300||hhmm%100!=0)throw ParseError("not an exact hour");
  r.utc={to_int(f[2],"year"),to_int(f[0],"month"),to_int(f[1],"day"),hhmm/100};
  const auto time=utc_second(r.utc);
  if(!out.records.empty()&&time<=utc_second(out.records.back().utc))
   throw ParseError("duplicate or unordered station hour");
  auto val=[&](int col,const char* name){return observed(to_double(f[static_cast<std::size_t>(col)],name));};
  const auto tc=val(4,"temperature");
  r.temperature_k=tc.valid?Value{tc.value+273.15,true}:Value{};
  r.precipitation_mm=val(5,"precipitation");
  r.pressure_hpa=val(6,"pressure");
  r.rh_percent=val(7,"RH");
  r.wind_direction_deg=val(8,"wind direction");
  r.wind_speed_mps=val(9,"wind speed");
  r.cloud_tenths=val(10,"cloud cover");
  r.ceiling_hundreds_ft=val(11,"cloud ceiling");
  if(!r.wind_direction_deg.valid||!r.wind_speed_mps.valid||
     r.wind_direction_deg.value<0||r.wind_direction_deg.value>360||r.wind_speed_mps.value<0){
   if(r.wind_direction_deg.valid||r.wind_speed_mps.valid)r.diagnostics.push_back("INVALID_OR_PARTIAL_WIND_PAIR");
   r.wind_direction_deg={};r.wind_speed_mps={};
  }
  if(r.precipitation_mm.valid){
   if(r.precipitation_mm.value<0)throw ParseError("negative precipitation");
   if(r.precipitation_mm.value==0)r.precipitation_code=0;
   else if(r.temperature_k.valid)r.precipitation_code=r.temperature_k.value>273.15?1:2;
   else r.diagnostics.push_back("PRECIP_TEMP_MISSING");
  }
  if(r.pressure_hpa.valid&&r.pressure_hpa.value<=0)throw ParseError("invalid pressure");
  if(r.rh_percent.valid&&(r.rh_percent.value<0||r.rh_percent.value>100))r.diagnostics.push_back("RH_OUT_OF_RANGE");
  if(r.cloud_tenths.valid&&(r.cloud_tenths.value<0||r.cloud_tenths.value>10))r.diagnostics.push_back("CLOUD_OUT_OF_RANGE");
  out.records.push_back(std::move(r));
 }
 return out;
}
inline Merge merge_utc_hourly(const std::vector<Station>& stations,const Window& win,
                              const std::vector<int>& astz_minutes,int abtz_minutes=0){
 using namespace std::chrono;
 if(stations.empty())throw ParseError("NFF=0");
 if(astz_minutes.size()!=stations.size())throw ParseError("ASTZ cardinality");
 if(abtz_minutes!=0)throw ParseError("ABTZ!=UTC not supported");
 for(int m:astz_minutes)if(m!=0)throw ParseError("ASTZ!=UTC not supported");
 const auto begin=utc_second(win.start),end=utc_second(win.end);
 if(end<begin)throw ParseError("end before start");
 if(duration_cast<hours>(end-begin).count()>100000)throw ParseError("unbounded range");
 Merge out;out.missing_hours_by_station.assign(stations.size(),0);
 std::vector<std::map<sys_seconds,SurfaceRecord>> lookup(stations.size());
 for(std::size_t i=0;i<stations.size();++i){
  if(stations[i].id<=0)throw ParseError("invalid IFSTN");
  for(auto old:out.station_ids)if(old==stations[i].id)throw ParseError("duplicate IFSTN");
  out.station_ids.push_back(stations[i].id);
  for(const auto& v:stations[i].records){
   auto [it,inserted]=lookup[i].emplace(utc_second(v.utc),v);
   (void)it;
   if(!inserted)throw ParseError("duplicate hour");
  }
 }
 for(auto time=begin;time<=end;time+=hours{1}){
  const year_month_day d{floor<days>(time)};
  const auto h=duration_cast<hours>(time-floor<days>(time)).count();
  HourlyRecord record{{int(d.year()),int(unsigned(d.month())),int(unsigned(d.day())),int(h)},{}};
  // Allocate exactly one slot per station. Besides deterministic layout,
  // this avoids expensive vector relocations of optional SurfaceRecord.
  record.by_station.reserve(stations.size());
  for(std::size_t i=0;i<stations.size();++i){
   const auto it=lookup[i].find(time);
   if(it==lookup[i].end()){record.by_station.push_back(std::nullopt);++out.missing_hours_by_station[i];}
   else record.by_station.push_back(it->second);
  }
  out.hours.push_back(std::move(record));
 }
 return out;
}
} // namespace cteas::met_input::p5
