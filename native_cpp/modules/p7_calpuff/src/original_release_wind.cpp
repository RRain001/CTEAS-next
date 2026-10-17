#include "cteas/puff/original_release_wind.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace cteas::puff {
namespace {
void require(bool p,const char* reason){
    if(!p)throw std::invalid_argument(reason);
}
int fortran_nint(float x){
    require(std::isfinite(x),"RLSMET FLOW must be finite");
    // Fortran NINT rounds half values away from zero.
    return static_cast<int>(std::round(x));
}
}
OriginalReleaseWind original_release_wind_metfm1(
    const OriginalMetHour& hour,const Calmet21Static& statics,
    const OriginalReleaseWindRequest& in) {
    require(hour.nx>0 && hour.ny>0 && hour.nz>0,
            "WINDSET requires a positive original CALMET METFM1 grid");
    const auto xy=static_cast<std::size_t>(hour.nx)*
                  static_cast<std::size_t>(hour.ny);
    const auto nz=static_cast<std::size_t>(hour.nz);
    require(hour.u.size()==xy*nz && hour.v.size()==xy*nz &&
            statics.cell_face_m.size()==nz+1U &&
            statics.roughness_m.size()==xy,
            "WINDSET missing original UMET/VMET/ZFACE/Z0 data");
    require(std::isfinite(in.release_height_m) &&
            std::isfinite(in.calm_threshold_ms) &&
            in.calm_threshold_ms>=0.0F,
            "WINDSET received invalid release height or calm threshold");
    const auto cell=original_met_cell(
        in.x_cells,in.y_cells,hour.nx,hour.ny);
    const float z0=statics.roughness_m.at(cell.offset_0based);
    require(std::isfinite(z0) && z0>=0.0F,
            "RLSMET requires finite nonnegative original surface roughness");
    const float htr=std::max(in.release_height_m,z0); // AMAX1(HTR,Z0M)
    const auto zfaces=std::vector<double>(
        statics.cell_face_m.begin(),statics.cell_face_m.end());
    const int layer=find_layer(htr,zfaces); // original ZFIND
    require(layer>=1 && layer<=hour.nz,
            "RLSMET original ZFIND returned invalid layer");
    const auto i=(static_cast<std::size_t>(layer)-1U)*xy+
                 cell.offset_0based;
    const float u=hour.u.at(i),v=hour.v.at(i);
    require(std::isfinite(u) && std::isfinite(v),
            "original CALMET layer wind is nonfinite");
    // WINDSET L2842 METFM=1: ws = SQRT(UMET**2+VMET**2), REAL*4.
    const float ws=std::sqrt(u*u+v*v);
    constexpr float kRadToDeg=57.29578F; // original DATA RTOD
    float wd=180.0F;                    // WINDSET WDCALM
    if(ws>0.0F){
        wd=270.0F-std::atan2(v,u)*kRadToDeg;
    }
    // RLSMET L18290-L18296: output FLOW and IVEC (NINT before radians).
    float flow=wd+180.0F;
    if(flow<0.0F)flow+=360.0F;
    else if(flow>=360.0F)flow-=360.0F;
    const int vec=fortran_nint(flow);
    // RLSMET L18364-L18376: WSCALM is a threshold for puff mode.
    const bool calm=ws<in.calm_threshold_ms;
    const float adjusted=calm?std::max(ws,0.001F):ws;
    return {cell,layer,htr,ws,adjusted,wd,flow,flow*0.0174533F,vec,calm};
}
ReleaseCadence original_points1_cadence_from_release_wind(
    const OriginalMetHour& hour,const Calmet21Static& statics,
    const OriginalReleaseWindRequest& position,
    float stack_height_m,const ReleaseCadenceInputs& cadence) {
    require(std::isfinite(stack_height_m) && stack_height_m>=0.0F,
            "POINTS1 requires a finite original HTSTAK");
    const auto final=original_release_wind_metfm1(hour,statics,position);
    auto stack_position=position;
    stack_position.release_height_m=stack_height_m;
    const auto stack=original_release_wind_metfm1(
        hour,statics,stack_position);
    auto native=cadence;
    // Original POINTS1 L15970: WSNEW=AMAX1(WS,WSFR), REAL*4.
    native.wind_speed_ms=std::max(stack.wind_speed_ms,final.wind_speed_ms);
    return release_cadence(native);
}
} // namespace cteas::puff
