#include "cteas/puff/original_pufrecs_geometry.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cteas::puff {
OriginalSlgfrac original_slgfrac(
    float x,float y,float x1,float y1,float x2,float y2) {
    for(float v:{x,y,x1,y1,x2,y2})
        if(!std::isfinite(v))
            throw std::invalid_argument("SLGFRAC coordinates must be finite");
    const float x12=x1-x2;
    const float y12=y1-y2;
    float length=std::sqrt(x12*x12+y12*y12);
    if(!std::isfinite(length))
        throw std::overflow_error("SLGFRAC projected length overflow");
    if(length>=1.0F) {
        const float inv=1.0F/length;
        const float cosom=y12*inv;
        const float sinom=x12*inv;
        const float xr=x-x2;
        const float yr=y-y2;
        const float along=yr*cosom+xr*sinom;
        const float across=-xr*cosom+yr*sinom;
        return {along,across,along*inv,length,inv};
    }
    // Original small/zero trajectory branch: DXY12=RDXY12=1.0;
    // RHOA=FRACS=0; RHOC=distance from younger end.
    const float xr=x-x2,yr=y-y2;
    return {0.0F,std::sqrt(xr*xr+yr*yr),0.0F,1.0F,1.0F};
}
OriginalPufrecsGeometry original_pufrecs_geometry(
    const OriginalPufrecsGeometryInputs& in) {
    for(float v:{in.x_receptor_m,in.y_receptor_m,
        in.x_begin_m,in.y_begin_m,in.x_end_m,in.y_end_m,
        in.sigma_y_begin_m,in.sigma_y_end_m,
        in.fclip,in.travel_distance_begin_m,in.mean_wind_ms})
        if(!std::isfinite(v))
            throw std::invalid_argument("PUFRECS geometry requires finite REAL4 inputs");
    if(in.mean_wind_ms<=0.0F || in.fclip<0.0F ||
       in.sigma_y_begin_m<0.0F || in.sigma_y_end_m<0.0F)
        throw std::invalid_argument("PUFRECS non-calm UAVG/FCLIP/sigma invalid");
    // Original PUFRECS L4950 passes XE1,YE1 as SLGFRAC old end x1/y1,
    // and XB1,YB1 as the new end x2/y2.
    const auto p=original_slgfrac(
        in.x_receptor_m,in.y_receptor_m,
        in.x_end_m,in.y_end_m,in.x_begin_m,in.y_begin_m);
    float frac=p.fraction,along=p.along_m;
    if(in.clip){
        frac=std::max(frac,-in.fclip*in.sigma_y_begin_m*p.inverse_length_per_m);
        frac=std::min(frac,1.0F+in.fclip*in.sigma_y_end_m*p.inverse_length_per_m);
        along=frac*p.projected_length_m;
    }
    float xtt1=in.travel_distance_begin_m+along;
    if(xtt1<0.0F){
        xtt1=0.0F;
        frac=-in.travel_distance_begin_m*p.inverse_length_per_m;
    }
    return {frac,along,xtt1,xtt1/in.mean_wind_ms,
            frac!=p.fraction};
}
OriginalPufrecsGeometry original_pufrecs_grid_receptor_geometry(
    const OriginalPufrecsGridStepInputs& in,
    std::size_t receptor_index) {
    if(in.ibsamp<1 || in.jbsamp<1 || in.sampling_nx<=0 ||
       in.sampling_ny<=0 || !std::isfinite(in.met_spacing_m) ||
       in.met_spacing_m<=0.0F)
        throw std::invalid_argument("PUFRECS invalid MET/sampling-grid frame");
    const auto nx=static_cast<std::size_t>(in.sampling_nx);
    const auto ny=static_cast<std::size_t>(in.sampling_ny);
    if(receptor_index>=nx*ny)
        throw std::out_of_range("PUFRECS receptor index outside native grid");
    // CALCPF/PFSAMP uses XOLD=XPB-(IBSAMP-.5)+1 and receptor I=1..NX.
    // In the original MET-cell frame receptor 0 is therefore IBSAMP-.5,
    // NOT IBSAMP, and every subsequent grid receiver is one cell apart.
    // Keep each conversion/multiply at the original REAL*4 boundary.
    const float xrec_cells=(static_cast<float>(in.ibsamp)-0.5F)+
                           static_cast<float>(receptor_index%nx);
    const float yrec_cells=(static_cast<float>(in.jbsamp)-0.5F)+
                           static_cast<float>(receptor_index/nx);
    return original_pufrecs_geometry({
        .x_receptor_m=xrec_cells*in.met_spacing_m,
        .y_receptor_m=yrec_cells*in.met_spacing_m,
        .x_begin_m=in.x_begin_cells*in.met_spacing_m,
        .y_begin_m=in.y_begin_cells*in.met_spacing_m,
        .x_end_m=in.x_end_cells*in.met_spacing_m,
        .y_end_m=in.y_end_cells*in.met_spacing_m,
        .sigma_y_begin_m=in.sigma_y_begin_m,
        .sigma_y_end_m=in.sigma_y_end_m,
        .fclip=in.fclip,
        .travel_distance_begin_m=in.distance_begin_m,
        .mean_wind_ms=in.mean_wind_ms,
        .clip=in.clip
    });
}
} // namespace cteas::puff
