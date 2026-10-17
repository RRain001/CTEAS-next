#include "cteas/p6/surface_hourly_state.hpp"
#include <chrono>
#include <iostream>
#include <stdexcept>
using namespace cteas::calmet::p6;
static void check(bool yes,const char* msg) {
    if(!yes)throw std::runtime_error(msg);
}
int main() {
 try {
  using namespace std::chrono;
  auto base=sys_seconds{sys_days{year{2022}/January/1}};
  Surface2022 src;src.station_id=58321;
  for(int n=0;n<3;++n) {
    SurfaceInterval row;
    row.start=base+hours{n};row.end=base+hours{n+1};
    row.obs.wind_speed_mps=n==0?0.f:9999.f;
    row.obs.wind_valid=n==0;
    row.obs.precip_code=9999;
    src.hourly.push_back(row);
  }
  RdsnBufferedTimeline original(src);
  auto first=original.select(base,base+hours{1});
  check(first.source_row==0&&first.reads==1&&!first.reused,
        "RDSN first one-hour record read");
  check(first.record->obs.wind_valid&&!first.record->obs.precipitation_code_valid,
        "RDSN preserve calm and missing rain mask");
  auto second=original.select(base+hours{1},base+hours{2});
  check(second.source_row==1&&second.reads==2&&!second.reused,
        "RDSN on exact one-hour end advances physical record");
  bool fail=false;
  try{(void)original.select(base+hours{2},base+hours{2});}
  catch(const std::invalid_argument&){fail=true;}
  check(fail,"RDSN rejects zero timestep");
  RdsnBufferedTimeline half(src,1800);
  auto h0=half.select(base,base+minutes{30});
  auto h1=half.select(base+minutes{30},base+hours{1});
  auto h2=half.select(base+hours{1},base+minutes{90});
  check(!h0.reused&&h1.reused&&!h2.reused&&h2.reads==2,
        "RDSN subhourly reuse, new record only at time boundary");
  src.hourly[1].start=base+hours{1}+minutes{5};
  RdsnBufferedTimeline gap(src);
  (void)gap.select(base,base+hours{1});
  fail=false;
  try{(void)gap.select(base+hours{1},base+hours{2});}
  catch(const std::invalid_argument&){fail=true;}
  check(fail,"RDSN gaps must fail closed");
  src.hourly[1].start=base+hours{1};
  src.hourly[1].end=base+hours{1}+minutes{30};
  RdsnBufferedTimeline shortrecord(src);
  (void)shortrecord.select(base,base+hours{1});
  fail=false;
  try{(void)shortrecord.select(base+hours{1},base+hours{2});}
  catch(const std::invalid_argument&){fail=true;}
  check(fail,"COMP rejects surface record shorter than model timestep");
  std::cout<<"PASS_P6C_RDSN_BUFFERED_SURFACE_STATE_TEST\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
