#include "cteas/puff/original_rise_met.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cteas::puff {
namespace {
void check(bool p,const char* msg) {
    if(!p) throw std::invalid_argument(msg);
}
float real4(float v,const char* msg) {
    check(std::isfinite(v),msg);
    return v;
}
}
OriginalRiseMetResult original_rise_wind_met(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const OriginalRiseMetInputs& input) {
    const float x=real4(input.x_cells,"nonfinite rise puff x");
    const float y=real4(input.y_cells,"nonfinite rise puff y");
    const float start=real4(input.start_distance_m,"nonfinite rise distance");
    const float final_x=real4(input.final_distance_m,"nonfinite final-rise distance");
    const float dt=real4(input.step_seconds,"nonfinite rise time");
    const float dz=real4(input.rise_half_depth_m,"nonfinite vertical extent");
    check(start>=0.0F && final_x>0.0F && dt>0.0F && dz>=0.0F,
          "rise geometry must have valid positive range and duration");
    check(input.rise_iterations>=1 && input.rise_iterations<=8,
          "unsupported RISEWIND iteration count");
    check(input.plume.source_type==1 && input.plume.downwash_code==0 &&
          input.plume.rise_method==1 && input.plume.shear_flag==0,
          "original selected GRISE requires point Briggs without building/shear");
    check(std::isfinite(input.plume.final_rise_m) &&
          input.plume.final_rise_m>=0.0,
          "invalid native PRFIN final plume height");
    const auto cell=original_met_cell(x,y,met.nx,met.ny);
    const float h=static_cast<float>(input.plume.final_rise_m);
    check(std::isfinite(h),"final plume height overflows REAL4");
    const float bottom=std::max(0.0F,h-dz);
    const float top=h+dz;
    check(std::isfinite(top),"final plume wind top overflows REAL4");
    const auto final_wind=original_met_cell_advect(
        met,statics,cell,bottom,top);
    auto plume=input.plume;
    plume.x_m=start;
    const auto initial=gradual_plume_height(plume);
    const auto rise=[plume](double distance)->double {
        auto state=plume;
        state.x_m=distance;
        return gradual_plume_height(state).height_m;
    };
    const auto advect=[&met,&statics,cell](double zbot,double ztop)
            ->AdvectiveWind {
        check(std::isfinite(zbot) && std::isfinite(ztop),
              "GRISE returned nonfinite vertical range");
        return original_met_cell_advect(met,statics,cell,
                                       static_cast<float>(zbot),
                                       static_cast<float>(ztop));
    };
    RiseWindInputs wind;
    wind.puff=true;
    wind.iterations=input.rise_iterations;
    wind.dz_m=dz;
    wind.start_distance_m=start;
    wind.final_distance_m=final_x;
    wind.final_height_m=h;
    wind.step_seconds=dt;
    wind.u_final_ms=final_wind.u_ms;
    wind.v_final_ms=final_wind.v_ms;
    wind.wind_speed_ms=std::hypot(final_wind.u_ms,final_wind.v_ms);
    const auto adjusted=transitional_rise_wind(wind,rise,advect);
    check(std::isfinite(adjusted.u_ms) &&
          std::isfinite(adjusted.v_ms) &&
          std::isfinite(adjusted.wind_speed_ms),
          "native RISEWIND produced nonfinite wind");
    return {cell,final_wind,adjusted,initial};
}
} // namespace cteas::puff
