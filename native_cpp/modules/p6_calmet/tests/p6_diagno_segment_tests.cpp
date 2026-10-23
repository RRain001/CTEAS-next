#include "cteas/p6/diagno_segment.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>
int main(){
 try{
  using namespace cteas::calmet::p6;
  SmoothInput s;
  s.nx=3;s.ny=3;s.nz=2;s.passes_per_layer={0,0};
  s.u_mps.assign(18,0.f);s.v_mps.assign(18,0.f);
  s.ub_west_east_mps.assign(12,0.f);
  s.vb_south_north_mps.assign(12,0.f);
  // Divergence driven by constant +x boundary gradient.
  s.ub_west_east_mps[3]=1.f;
  const auto o=original_smooth_divcel_w(s,100.f,100.f,{20.f,40.f});
  if(o.u_mps.size()!=18||o.v_mps.size()!=18||
     o.w_face_mps.size()!=27||o.divergence_per_s.size()!=18)
    throw std::runtime_error("incorrect selected DIAGNO segment dimensions");
  if(o.w_face_mps[0]!=0.f)
    throw std::runtime_error("W ground interface not zero");
  const float d1=(1.f-0.f)/(2.f*100.f);
  if(std::abs(o.divergence_per_s[2]-d1)>1.e-7f||
     std::abs(o.w_face_mps[9+2]-(-20.f*d1))>1.e-6f)
    throw std::runtime_error("original W integration wrong");
  if(std::abs(o.w_face_mps[18+2]-o.w_face_mps[9+2])>1.e-6f)
    throw std::runtime_error("W integration across layers wrong");
  // Test-only stage100 observer is a read-only snapshot of the same
  // SMOOTH invocation and must not change final U/V/W or divergence.
  std::vector<float> stage100_u,stage100_v;
  const auto observed=original_smooth_divcel_w(
      s,100.f,100.f,{20.f,40.f},false,&stage100_u,&stage100_v);
  if(stage100_u.size()!=18||stage100_v.size()!=18||
     stage100_u!=o.u_mps||stage100_v!=o.v_mps||
     observed.u_mps!=o.u_mps||observed.v_mps!=o.v_mps||
     observed.w_face_mps!=o.w_face_mps||
     observed.divergence_per_s!=o.divergence_per_s||
     observed.ub_west_east_mps!=o.ub_west_east_mps||
     observed.vb_south_north_mps!=o.vb_south_north_mps)
      throw std::runtime_error("test-only stage100 observer changed physics");
  // Boundary renewal after integration has source-faithful original
  // WINDBC values based on smoothed final U/V (zero in this test).
  for(float x:o.ub_west_east_mps)
    if(x!=0.f)throw std::runtime_error("WINDBC was not refreshed");
  bool failed=false;
  try{(void)original_smooth_divcel_w(s,100.f,100.f,{20.f,40.f},true);}
  catch(const std::invalid_argument&){failed=true;}
  if(!failed)throw std::runtime_error("unsupported IOBR accepted");
  std::cout<<"PASS P6D_DIAGNO_FINAL_SEGMENT_SOFTWARE_ONLY\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
