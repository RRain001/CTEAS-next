#include "cteas/p6/cgamma.hpp"
#include <chrono>
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
using namespace cteas::calmet::p6;
static void check(bool a,const char* msg){if(!a)throw std::runtime_error(msg);}
int main(){
 try{
  using namespace std::chrono;
  const auto start=sys_seconds{sys_days{year{2022}/January/1}};
  Upper2022 upper;
  std::vector<std::vector<LayerWind>> layers(3,std::vector<LayerWind>(1));
  std::vector<std::vector<float>> faces(3,std::vector<float>(2));
  for(int n=0;n<3;++n) {
   UpperSounding s;s.end=start+hours{12*n};s.start=s.end;
   UpperLevel base;base.height_lgl_m=0; base.temperature_k=280.f-n;
   base.temperature_valid=true;
   UpperLevel top;top.height_lgl_m=500;top.temperature_k=275.f-n;
   top.temperature_valid=true;
   s.data={base,top};upper.soundings.push_back(s);
  }
  CompBufferedTimeline timeline(upper,layers,faces);
  CGammaState state;
  const auto h1=timeline.hour(start+hours{1});
  auto direct=state.calculate(upper,h1,200.f,0.f);
  check(direct.branch==0&&std::abs(direct.kelvin_per_m+0.01f)<0.0001,
        "CGAMMA original direct lapse");
  const auto h2=timeline.hour(start+hours{2});
  auto conv=state.calculate(upper,h2,200.f,200.f);
  check(conv.branch==1&&conv.kelvin_per_m==-0.0098f,
        "CGAMMA convective early return and stored stamp");
  const auto h3=timeline.hour(start+hours{3});
  auto retained=state.calculate(upper,h3,200.f,0.f);
  check(retained.branch==2&&std::isfinite(retained.kelvin_per_m),
        "CGAMMA retained convective prior state");
  const auto h13=timeline.hour(start+hours{13});
  auto later=state.calculate(upper,h13,200.f,0.f);
  check(later.branch==0&&std::isfinite(later.kelvin_per_m),
        "CGAMMA no improper retained-hour interpolation outside brackets");
  bool failed=false;
  try{(void)state.calculate(upper,h13,200.f,0.f);}
  catch(const std::invalid_argument&){failed=true;}
  check(failed,"CGAMMA monotonic time");
  std::cout<<"PASS_P6C_CGAMMA_STATE_SOFTWARE_SELECTED\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
