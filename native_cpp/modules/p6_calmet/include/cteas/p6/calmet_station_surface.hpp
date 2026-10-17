#pragma once
// Original CALMET station -> surface-grid parameter lookup.
//
// calmet.for DIAGI L5129-5130:
//   IST(I)=XSSTA(I)/DX + 1 ; JST(I)=YSSTA(I)/DY + 1
// calmet.for WIND1 L36179-36187:
//   ISC=IST(L); JSC=JST(L)
//   ISC=MIN(NX,MAX(1,ISC)); JSC=MIN(NY,MAX(1,JSC))
//   ZR=Z0(ISC,JSC)
//
// Model coordinates are ALREADY the READCF REAL*4 relative metres. Do not
// reproject latitude/longitude or retrieve Z0 at (1,1) by convenience.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6 {
struct CalmetStationSurfaceCell {
    int i_one_based=0;
    int j_one_based=0;
    std::size_t zero_based_linear=0;
};

inline CalmetStationSurfaceCell original_calmet_station_surface_cell(
    float local_x_m,float local_y_m,float dx_m,float dy_m,int nx,int ny) {
    if(!(std::isfinite(local_x_m)&&std::isfinite(local_y_m)&&
         std::isfinite(dx_m)&&std::isfinite(dy_m))||
       dx_m<=0.f||dy_m<=0.f||nx<=0||ny<=0)
        throw std::invalid_argument("invalid CALMET station/grid coordinates");
    // Fortran INTEGER assignment truncates toward zero after the REAL*4
    // division and '+1.' arithmetic; clipping happens AFTER assignment.
    const float fi=local_x_m/dx_m+1.f;
    const float fj=local_y_m/dy_m+1.f;
    if(!std::isfinite(fi)||!std::isfinite(fj)||
       std::abs(fi)>1.0e7f||std::abs(fj)>1.0e7f)
        throw std::invalid_argument("CALMET station grid index out of scope");
    const int i=std::clamp(static_cast<int>(fi),1,nx);
    const int j=std::clamp(static_cast<int>(fj),1,ny);
    return CalmetStationSurfaceCell{i,j,
        static_cast<std::size_t>(j-1)*static_cast<std::size_t>(nx)+
        static_cast<std::size_t>(i-1)};
}

inline float original_calmet_station_z0(
    const std::vector<float>& z0,
    float local_x_m,float local_y_m,
    float dx_m,float dy_m,int nx,int ny) {
    if(z0.size()!=static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny))
        throw std::invalid_argument("CALMET GEO roughness array has wrong extent");
    const auto cell=original_calmet_station_surface_cell(
        local_x_m,local_y_m,dx_m,dy_m,nx,ny);
    const float value=z0.at(cell.zero_based_linear);
    if(!std::isfinite(value)||value<=0.f)
        throw std::invalid_argument("invalid station GEO roughness value");
    return value;
}
} // namespace cteas::calmet::p6
