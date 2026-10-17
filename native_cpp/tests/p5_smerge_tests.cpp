#include "cteas/met_input/p5_smerge.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <sstream>
#include <string>
using namespace cteas::met_input::p5;
static std::string generic(int id,const std::string& rows,const std::string& unit="Month,Day,Year,Hour,DegC,mm,mb,%,deg,ms-1,tenths,hundreds_of_feet"){
 return "GENERIC,Version,'2.0',Manuallygenerated,Timeasendinghour,\n"
        "Station,ID,=',"+std::to_string(id)+",Temp,Precip,Pressure,RH,Wdir10m,Wspeed10m,Ccover,Cheight\n"+
        unit+"\n"+rows;
}
static bool fails(const std::string& s,int id=58321){std::istringstream in(s);try{(void)read_generic(in,id);}catch(const ParseError&){return true;}return false;}
int main(){
 const auto rows="1,1,2022,0,20,1.5,1010,60,180,2.5,4,10\n1,1,2022,200,0,0,9999,9999,9999,0,9999,9999\n";
 std::istringstream in(generic(58321,rows));
 const auto a=read_generic(in,58321);
 assert(a.id==58321&&a.records.size()==2);
 assert(a.records[0].precipitation_code==1&&a.records[0].temperature_k.valid);
 assert(a.records[1].precipitation_code==0&&!a.records[1].wind_speed_mps.valid);
 assert(!a.records[1].pressure_hpa.valid&&!a.records[1].wind_direction_deg.valid);
 std::istringstream in2(generic(58345,"1,1,2022,100,-5,1,990,40,90,0,2,15\n"));
 const auto b=read_generic(in2,58345);
 assert(b.records[0].precipitation_code==2);
 auto m=merge_utc_hourly({a,b},{{2022,1,1,0},{2022,1,1,2}},{0,0});
 assert(m.station_ids.size()==2&&m.hours.size()==3);
 assert(m.missing_hours_by_station[0]==1&&m.missing_hours_by_station[1]==2);
 assert(!m.hours[0].by_station[1]&&!m.hours[1].by_station[0]);
 assert(m.hours[2].by_station[0].has_value());
 // Scheme C: the P5 C++ GENERIC reader must not clamp calm/low speeds.
 std::istringstream calm_input(generic(58321,
   "1,1,2022,0,10,0,1010,50,0,0,2,10\n"
   "1,1,2022,100,10,0,1010,50,75,0.2,2,10\n"));
 const auto scheme_c=read_generic(calm_input,58321);
 assert(scheme_c.records.size()==2);
 assert(scheme_c.records[0].wind_speed_mps.valid);
 assert(scheme_c.records[0].wind_direction_deg.valid);
 assert(scheme_c.records[0].wind_speed_mps.value==0.0);
 assert(scheme_c.records[0].wind_direction_deg.value==0.0);
 assert(std::abs(scheme_c.records[1].wind_speed_mps.value-0.2)<1e-12);
 assert(scheme_c.records[1].wind_direction_deg.value==75.0);
 assert(fails(generic(58321,rows),58322));
 assert(fails(generic(58321,"1,1,2022,30,20,0,1010,60,180,2,4,10\n")));
 assert(fails(generic(58321,"1,1,2022,0,20,0,1010,60,180,2,4,10\n1,1,2022,0,20,0,1010,60,180,2,4,10\n")));
 assert(fails(generic(58321,rows,"Month,Day,Year,Hour,DegC,mm,mb,%,deg,knot,tenths,hundreds_of_feet")));
 assert(fails(generic(58321,"1,1,2022,0,20,-1,1010,60,180,2,4,10\n")));
 assert(fails(generic(58321,"1,1,2022,0,nan,0,1010,60,180,2,4,10\n")));
 bool reject=false;try{(void)merge_utc_hourly({a},{{2022,1,1,0},{2022,1,1,2}},{480});}catch(const ParseError&){reject=true;}
 assert(reject);
}
