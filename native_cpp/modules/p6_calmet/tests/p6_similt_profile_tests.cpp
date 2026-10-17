#include "cteas/p6/similt_profile.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
namespace {
using cteas::calmet::p6::SimiltProfileInput;
constexpr std::array<float,10> kZface{0.f,20.f,40.f,80.f,160.f,
    320.f,640.f,1200.f,2000.f,3000.f};
SimiltProfileInput base(float el,float zi){
    SimiltProfileInput in;
    in.station_lat_deg=31.939774f;
    in.anemometer_height_m=10.f;
    in.roughness_m=0.1f;
    in.anemometer_u_mps=3.f;
    in.anemometer_v_mps=4.f;
    in.obukhov_length_m=el;
    in.mixing_height_m=zi;
    in.minimum_mixing_height_m=50.f;
    in.ipsifcn=0;
    in.zface_m=kZface;
    return in;
}
}
int main(){
 try{
  using namespace cteas::calmet::p6;
  // Neutral WIND1 route: EL=ZI=ZIMINI=10000, all nine levels filled.
  const auto neutral=original_similt_profile(base(10000.f,10000.f));
  if(neutral.levels_filled!=9)
    throw std::runtime_error("SIMILT neutral must fill nine levels");
  const float scale=std::hypot(neutral.u_mps[0],neutral.v_mps[0]);
  if(!(scale>4.f&&scale<6.f))throw std::runtime_error("SIMILT first level speed");
  if(!(std::hypot(neutral.u_mps[8],neutral.v_mps[8])>scale))
    throw std::runtime_error("SIMILT neutral vertical shear missing");
  // PSIUD at zL=0 takes the stable branch and yields -0.005 in the original
  // (the port matches the compiled routine; see the parity report). SIMILT
  // never calls it there: |1/L|<5e-5 short-circuits to the neutral branch.
  if(std::abs(original_psiud(0.0)+0.005)>1.0e-3)
    throw std::runtime_error("PSIUD stable branch at zL=0");
  if(!(original_psiud(-0.5)>0.0&&original_psiud(0.5)<0.0))
    throw std::runtime_error("PSIUD stability signs");
  // Stability changes the profile: unstable mixes faster than stable.
  const auto unstable=original_similt_profile(base(-30.f,1000.f));
  const auto stable=original_similt_profile(base(30.f,1000.f));
  // Speeds, not components (the turning angle rotates the vector), and the
  // measured ordering of the original's profiles aloft is stable > neutral >
  // unstable: the Beljaars-Holtslag stable PSIUD is strongly negative, which
  // steepens the log profile, while the unstable branch mixes it flat.
  const float speed_unstable=std::hypot(unstable.u_mps[5],unstable.v_mps[5]);
  const float speed_stable=std::hypot(stable.u_mps[5],stable.v_mps[5]);
  const float speed_neutral=std::hypot(
      original_similt_profile(base(10000.f,1000.f)).u_mps[5],
      original_similt_profile(base(10000.f,1000.f)).v_mps[5]);
  if(!(speed_stable>speed_neutral&&speed_neutral>speed_unstable))
    throw std::runtime_error("SIMILT stability ordering stable>neutral>unstable");
  // The mixing-height cutoff stops the extrapolation (L30319 exit).
  const auto shallow=original_similt_profile(base(-30.f,50.f));
  if(shallow.levels_filled!=2)
    throw std::runtime_error("SIMILT cutoff must stop at zface>ZI");
  // Fail-closed paths.
  bool rejected=false;
  try{(void)original_similt_profile(base(0.f,1000.f));}
  catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("SIMILT accepted a zero Obukhov length");
  rejected=false;
  try{(void)original_similt_profile(base(30.f,-5.f));}
  catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("SIMILT accepted a negative mixing height");
  auto calm=base(30.f,1000.f);
  calm.anemometer_u_mps=0.f;calm.anemometer_v_mps=0.f;
  rejected=false;
  try{(void)original_similt_profile(calm);}catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("SIMILT unexpected calm extrapolation");
  auto singular=base(30.f,1000.f);
  singular.roughness_m=10.f;
  rejected=false;
  try{(void)original_similt_profile(singular);}catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("SIMILT singular logarithm accepted");
  auto not_ported=base(30.f,1000.f);
  not_ported.ipsifcn=1;
  rejected=false;
  try{(void)original_similt_profile(not_ported);}catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("SIMILT IPSIFCN=1 must fail closed");
  std::cout<<"P6D SIMILT PROFILE SOFTWARE PASS\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
