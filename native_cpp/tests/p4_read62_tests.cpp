#include "cteas/met_input/p4_read62.hpp"
#include <cassert>
#include <iomanip>
#include <sstream>
#include <string>
using namespace cteas::met_input::p4;
static std::string pad(int n,int w){std::ostringstream o;o<<std::setw(w)<<n;return o.str();}
static std::string profile(int hour,int day,const std::string& unit="ms",int wind=100,int p2=500,bool bad_z=false){
 const std::string a="    254"+pad(hour,7)+pad(day,7)+"      JAN"+pad(2022,8);
 const std::string b="      1  99999"+pad(58321,7)+"  31.94N"+"117.14E"+pad(11,6)+"  32767";
 const std::string c="      2    100    100    194"+pad(6,7)+"  32767      3";
 const std::string d="      3          9999                32767     "+unit;
 auto lv=[](int p,int z,int t,int wd,int ws){return std::string("      9")+pad(p,7)+pad(z,7)+pad(t,7)+pad(32767,7)+pad(wd,7)+pad(ws,7)+"\n";};
 return a+"\n"+b+"\n"+c+"\n"+d+"\n"+lv(1000,bad_z?32767:11,205,32767,wind)+lv(p2,5500,0,180,200);
}
static bool fails(const std::string& text,Options opt={}){std::istringstream in(text);try{(void)read_fsl(in,opt);}catch(const ParseError&){return true;}return false;}
int main(){
 {std::istringstream in(profile(0,1)+profile(12,1));auto s=read_fsl(in);
  assert(s.size()==2&&s[0].levels.size()==2&&s[0].utc.year==2022);
  assert(s[0].station_lat_deg==31.94&&s[0].station_lon_deg==117.14);
  assert(s[0].levels[0].temperature_c.valid&&s[0].levels[0].temperature_c.value==20.5);
  assert(!s[0].levels[0].wind_direction_deg.valid);
  assert(s[0].levels[0].wind_speed_mps.value==10.0);
  assert(s[0].diagnostics.empty()&&s[1].diagnostics.empty());
 }
 {std::istringstream in(profile(0,1,"kt",32767,1010,true));auto s=read_fsl(in);
  assert(s[0].dropped_non_decreasing_pressure==1&&s[0].levels.size()==1);
  assert(!s[0].levels[0].height_m.valid&&!s[0].levels[0].wind_speed_mps.valid);
 }
 {Options o;o.drop_missing_direction=true;std::istringstream in(profile(0,1));assert(read_fsl(in,o)[0].levels.size()==1);}
 {std::istringstream in(profile(0,1)+profile(0,2));auto s=read_fsl(in);assert(s[1].diagnostics[0]=="TIME_GAP_OVER_12H");}
 {std::string f=profile(0,1);
  auto b=f.find('\n');auto b2=f.find('\n',b+1);
  f.insert(b2," P4EXACT_LAT=31.939774 P4EXACT_LON=117.141611");
  std::istringstream input(f);
  auto s=read_fsl(input);
  assert(s.size()==1);
  assert(std::abs(s[0].station_lat_deg-31.939774)<1e-9);
  assert(std::abs(s[0].station_lon_deg-117.141611)<1e-9);
 }
 assert(fails(profile(25,1)));assert(fails(profile(0,1,"zz")));assert(fails(profile(0,1).substr(0,30)));
 {Options o;o.pstop_hpa=0;assert(fails(profile(0,1),o));}
}
