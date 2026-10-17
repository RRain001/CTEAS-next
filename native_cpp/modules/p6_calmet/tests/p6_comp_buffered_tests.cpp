#include "cteas/p6/comp_buffered_timeline.hpp"
#include <chrono>
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace cteas::calmet::p6;
static void check(bool x,const char* msg){if(!x)throw std::runtime_error(msg);}
int main(){
 try{
  using namespace std::chrono;
  const auto start=sys_seconds{sys_days{year{2022}/January/1}};
  Upper2022 upper;
  std::vector<std::vector<LayerWind>> layers(3,std::vector<LayerWind>(2));
  std::vector<std::vector<float>> temps(3,std::vector<float>(3));
  for(int i=0;i<3;++i) {
   UpperSounding s;s.end=start+hours{12*i};s.start=s.end;
   upper.soundings.push_back(s);
   for(int k=0;k<2;++k) {
    layers[i][k].u_mps=static_cast<float>(10*i+k);
    layers[i][k].v_mps=static_cast<float>(-20*i-k);
   }
   for(int k=0;k<3;++k)temps[i][k]=static_cast<float>(280-i-k);
  }
  CompBufferedTimeline state(upper,layers,temps);
  const auto h1=state.hour(start+hours{1});
  check(h1.aa_profile==0&&h1.bb_profile==1&&h1.aa_slot==0&&
        h1.bb_slot==1&&h1.jorder==1&&h1.turnovers==0&&h1.total_reads==2,
        "initial AA/BB physical buffers");
  check(h1.interpolated.gap_seconds==43200&&
        std::abs(h1.interpolated.winds[0].u_mps-10.f/12.f)<1e-4f,
        "first-hour PREPDI interpolation");
  const auto h11=state.hour(start+hours{11});
  check(h11.aa_slot==0&&h11.bb_slot==1&&h11.turnovers==0,
        "buffer not rotated before next sounding");
  const auto h12=state.hour(start+hours{12});
  check(h12.aa_profile==1&&h12.bb_profile==2&&h12.aa_slot==1&&
        h12.bb_slot==0&&h12.jorder==-1&&h12.turnovers==1&&
        h12.total_reads==3,"AA/BB physical buffer turnover on exact sounding");
  check(h12.interpolated.past_seconds==0 &&
        h12.interpolated.winds[0].u_mps==10.f &&
        h12.aa_face_temperature_k[1]==temps[1][1] &&
        h12.bb_face_temperature_k[2]==temps[2][2],
        "hour-ending time/temperature faces survive buffer turnover");
  const auto h23=state.hour(start+hours{23});
  check(h23.aa_slot==1&&h23.bb_slot==0&&h23.turnovers==1 &&
        h23.interpolated.prior_sounding==1,
        "buffer held between sounding updates");
  bool bad=false;
  try{(void)state.hour(start+hours{23});}
  catch(const std::invalid_argument&){bad=true;}
  check(bad,"repeated hour rejected");
  bad=false;
  try{(void)state.hour(start+hours{24});}
  catch(const std::invalid_argument&){bad=true;}
  check(bad,"missing upper lookahead rejected");
  upper.soundings[2].end=start+hours{27};
  CompBufferedTimeline gap(upper,layers,temps);
  (void)gap.hour(start+hours{11});
  bad=false;
  try{(void)gap.hour(start+hours{13});}
  catch(const std::invalid_argument&){bad=true;}
  check(bad,"MAXSEP failure on actual buffer transition");
  bad=false;
  try{CompBufferedTimeline invalid(upper,layers,temps,90000,86400);}
  catch(const std::invalid_argument&){bad=true;}
  check(bad,"invalid separation policy rejected");
  std::cout<<"PASS_P6C_BUFFERED_AA_BB_STATE_SOFTWARE_CANDIDATE\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
