// Independent C++20 SMERGE v5.7.0 SURF.DAT writer for JDAT=8, IOFORM=2.
// Exact legacy reference: SMERGE.FOR COMP/RDWRITS/WRHD/WRS (source unmodified).
// Direct GENERIC ingestion: no Fortran, no subprocess to SMERGE.
#include "cteas/met_input/p5_smerge.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs=std::filesystem;
using namespace cteas::met_input::p5;
namespace {

std::string read_text(const fs::path& path){
 std::ifstream in(path,std::ios::binary);
 if(!in)throw ParseError("cannot read input: "+path.string());
 return {std::istreambuf_iterator<char>(in),std::istreambuf_iterator<char>()};
}
std::string property(const std::string& text,const std::string& key,
                     const std::string& fallback=""){
 const std::regex r("!\\s*"+key+"\\s*=\\s*([^!]+?)\\s*!",std::regex::icase);
 std::smatch m;
 if(!std::regex_search(text,m,r)){
  if(fallback.empty())throw ParseError("control missing key "+key);
  return fallback;
 }
 return trim(m[1].str());
}
int ctrl_int(const std::string& c,const std::string& key,int def=-999999){
 const auto s=property(c,key,def==-999999?"":std::to_string(def));
 return to_int(s,key.c_str());
}
void require_control(const std::string& c,const std::string& key,const std::string& value){
 const auto got=property(c,key);
 if(got!=value)throw ParseError("unsupported "+key+"="+got+" (need "+value+")");
}
struct Source{fs::path file;int id;};
std::vector<Source> source_blocks(const std::string& text,const fs::path& cwd){
 const std::size_t begin=text.find("Subgroup (0b)");
 const std::size_t end=text.find("INPUT GROUP: 1",begin);
 if(begin==std::string::npos||end==std::string::npos||end<=begin)
  throw ParseError("missing SFCMET station list in SMERGE control");
 const auto blocks=text.substr(begin,end-begin);
 std::istringstream in(blocks);
 std::string line;
 std::map<std::string,std::string> attrs;
 std::vector<Source> out;
 const std::regex assignment(R"(!\s*(SFCMET|IFSTN|XELEV|ASTZ)\s*=\s*([^!]+)\s*!)",std::regex::icase);
 while(std::getline(in,line)){
  for(std::sregex_iterator it(line.begin(),line.end(),assignment),limit;it!=limit;++it)
   attrs[(*it)[1].str()]=trim((*it)[2].str());
  if(line.find("!END!")!=std::string::npos && attrs.count("SFCMET")){
   if(!attrs.count("IFSTN")||!attrs.count("ASTZ"))
    throw ParseError("SFCMET station requires IFSTN and ASTZ");
   if(attrs.at("ASTZ")!="UTC+0000")throw ParseError("ASTZ offset not yet supported");
   fs::path file(attrs.at("SFCMET"));
   if(file.is_relative())file=cwd/file;
   out.push_back({file.lexically_normal(),to_int(attrs.at("IFSTN"),"IFSTN")});
   attrs.clear();
  }
 }
 if(!attrs.empty())throw ParseError("incomplete SFCMET station block");
 return out;
}
Timestamp requested_time(const std::string& control,const char* prefix){
 const std::string p(prefix);
 return {ctrl_int(control,p+"YR"),ctrl_int(control,p+"MO"),
         ctrl_int(control,p+"DY"),ctrl_int(control,p+"HR")};
}
int doy(std::chrono::sys_seconds t){
 using namespace std::chrono;
 const year_month_day ymd{floor<days>(t)};
 const auto start=sys_days{year{int(ymd.year())}/1/1};
 return int((floor<days>(t)-start).count())+1;
}
void emit_time(std::ostream& out,std::chrono::sys_seconds at,
               int yw,int jw,int hw,int sw){
 using namespace std::chrono;
 const year_month_day ymd{floor<days>(at)};
 const auto hr=duration_cast<hours>(at-floor<days>(at)).count();
 out<<std::setw(yw)<<int(ymd.year())<<std::setw(jw)<<doy(at)
    <<std::setw(hw)<<hr<<std::setw(sw)<<0;
}
std::string padded(std::string s,std::size_t size){
 if(s.size()>size)throw ParseError("SURF.DAT fixed-width string overflow");
 s.resize(size,' ');
 return s;
}
struct OutputPoint{
 float ws=9999.0f,wd=9999.0f,tempk=9999.0f,pres=9999.0f;
 int ceil=9999,cover=9999,rh=9999,precip=9999;
};
int fortran_anint(float x){
 return x>=0?int(std::floor(x+0.5f)):int(std::ceil(x-0.5f));
}
OutputPoint output_point(const std::optional<SurfaceRecord>& value){
 OutputPoint out;
 if(!value)return out;
 const auto& r=*value;
 if(r.wind_direction_deg.valid && r.wind_speed_mps.valid){
  const float wd=static_cast<float>(r.wind_direction_deg.value);
  const float ws=static_cast<float>(r.wind_speed_mps.value);
  if(wd>=0.0f&&wd<=360.0f){out.ws=ws;out.wd=wd;}
 }
 if(r.temperature_k.valid){
  // Original SMERGE stores input DEGC in REAL*4, then adds REAL*4 273.15.
  const float c=static_cast<float>(r.temperature_k.value-273.15);
  out.tempk=c+273.15f;
 }
 if(r.ceiling_hundreds_ft.valid)out.ceil=static_cast<int>(static_cast<float>(r.ceiling_hundreds_ft.value));
 if(r.cloud_tenths.valid)out.cover=static_cast<int>(static_cast<float>(r.cloud_tenths.value));
 if(r.rh_percent.valid)out.rh=fortran_anint(static_cast<float>(r.rh_percent.value));
 if(r.pressure_hpa.valid)out.pres=static_cast<float>(r.pressure_hpa.value);
 if(r.precipitation_mm.valid){
  const float p=static_cast<float>(r.precipitation_mm.value);
  if(p<=0.0f)out.precip=0;
  else if(out.tempk>273.15f)out.precip=1;
  else if(out.tempk<=273.15f)out.precip=2;
  // If rain>0 and TEMP missing, Fortran keeps 9999.
 }
 return out;
}
void write_header(std::ostream& out,const Window& window,
                  const std::vector<int>& station_ids){
 using namespace std::chrono;
 // SMERGE 2.1 control supplies *explicit* beginning time. READCF
 // increments IBHR before RDWRITS. WRHD subtracts one again.
 const auto begin=utc_second(window.start);
 const auto end=utc_second(window.end);
 out<<padded("SURF.DAT",16)<<padded("2.1",16)
    <<padded("Hour Start and End Times with Seconds",64)<<"\n";
 out<<std::setw(4)<<1<<"\n";
 out<<padded(std::string("Produced by SMERGE Version: ")+"5.7.0"+"  "+"Level: "+"121203",80)<<"\n";
 out<<"NONE    \nUTC+0000\n";
 emit_time(out,begin,6,4,4,6);
 emit_time(out,end,6,4,4,6);
 out<<std::setw(5)<<station_ids.size()<<"\n";
 for(const auto id:station_ids)out<<std::setw(8)<<id<<"\n";
}
void write_one_hour(std::ostream& out,const HourlyRecord& rec){
 using namespace std::chrono;
 const auto end=utc_second(rec.utc);
 const auto start=end-hours{1};
 // Original WR S prints midnight end as previous day HH=24 (not 00).
 auto printed_end=end;
 bool midnight=rec.utc.hour==0;
 if(midnight)printed_end-=hours{1};
 auto formatted_time=[&](sys_seconds t,bool end_hour_24,bool first){
  const year_month_day ymd{floor<days>(t)};
  const auto hr=duration_cast<hours>(t-floor<days>(t)).count();
  out<<std::setw(4)<<int(ymd.year())<<std::setw(4)<<doy(t)
     <<std::setw(4)<<(end_hour_24?24:int(hr))<<std::setw(5)<<0;
  // Fortran sequential formatted records trim trailing X edit descriptors.
  // Only the delimiter between two time groups remains in the file.
  if(first)out<<"   ";
 };
 formatted_time(start,false,true);
 formatted_time(printed_end,midnight,false);
 out<<"\n";
 for(const auto& r:rec.by_station){
  const auto v=output_point(r);
  // SMERGE.FOR WRS: 1x,f8.3,1x,f8.3,1x,i4,1x,i4,1x,f8.3,
  //                 1x,i4,1x,f8.3,1x,i4
  out<<" "<<std::fixed<<std::setprecision(3)<<std::setw(8)<<v.ws
     <<" "<<std::setw(8)<<v.wd
     <<" "<<std::setw(4)<<v.ceil
     <<" "<<std::setw(4)<<v.cover
     <<" "<<std::setw(8)<<v.tempk
     <<" "<<std::setw(4)<<v.rh
     <<" "<<std::setw(8)<<v.pres
     <<" "<<std::setw(4)<<v.precip<<"\n";
 }
}
void run(const fs::path& inp){
 const auto cwd=fs::absolute(inp).parent_path();
 const std::string ctl=read_text(inp);
 require_control(ctl,"JDAT","8");
 require_control(ctl,"IOFORM","2");
 require_control(ctl,"IOPACK","0");
 require_control(ctl,"LPREV","F");
 require_control(ctl,"LPCALC","F");
 require_control(ctl,"ABTZ","UTC+0000");
 if(ctrl_int(ctl,"IBSEC")!=0||ctrl_int(ctl,"IESEC")!=0)
  throw ParseError("seconds!=0 not supported by hourly native writer");
 const auto sources=source_blocks(ctl,cwd);
 if(sources.size()!=std::size_t(ctrl_int(ctl,"NFF")))
  throw ParseError("NFF != SFCMET station count");
 std::vector<Station> stations;
 stations.reserve(sources.size());
 for(const auto& item:sources){
  std::ifstream in(item.file);
  if(!in)throw ParseError("cannot open station GENERIC: "+item.file.string());
  stations.push_back(read_generic(in,item.id));
  std::cerr<<"P5_CPP_READ station="<<item.id<<" rows="<<stations.back().records.size()<<"\n";
 }
 const Window explicit_times{requested_time(ctl,"IB"),requested_time(ctl,"IE")};
 const auto start=utc_second(explicit_times.start)+std::chrono::hours{1};
 const auto stop=utc_second(explicit_times.end);
 if(start>stop)throw ParseError("SMERGE 2.1 period contains no completed hours");
 const std::chrono::year_month_day d{
     std::chrono::floor<std::chrono::days>(start)};
 const int hour=int(std::chrono::duration_cast<std::chrono::hours>(
     start-std::chrono::floor<std::chrono::days>(start)).count());
 const Window effective{{int(d.year()),int(unsigned(d.month())),int(unsigned(d.day())),hour},
                        explicit_times.end};
 auto merged=merge_utc_hourly(stations,effective,std::vector<int>(stations.size(),0));
 fs::path target=property(ctl,"SURFDAT");
 if(target.is_relative())target=cwd/target;
 target=target.lexically_normal();
 fs::create_directories(target.parent_path());
 const fs::path temp=target.string()+".native.tmp";
 try{
  std::ofstream file(temp,std::ios::binary|std::ios::trunc);
  if(!file)throw ParseError("cannot create native SURF.DAT: "+temp.string());
  write_header(file,explicit_times,merged.station_ids);
  for(const auto& h:merged.hours)write_one_hour(file,h);
  file.flush();
  if(!file)throw ParseError("write failed: "+temp.string());
  file.close();
  fs::rename(temp,target);
 }catch(...){std::error_code ec;fs::remove(temp,ec);throw;}
 std::cerr<<"P5_CPP_SURFDAT_OK path="<<target.string()
          <<" stations="<<merged.station_ids.size()
          <<" hours="<<merged.hours.size()
          <<" format=JDAT8_IOFORM2_UNPACKED_NATIVE\n";
}
} // namespace
int main(int argc,char** argv){
 try{
  if(argc!=2)throw ParseError("usage: cteas_p5_smerge SURGE.INP");
  run(fs::absolute(argv[1]));
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P5_CPP_SURFDAT_ERROR: "<<e.what()<<"\n";
  return 2;
 }
}
