#pragma once
// P6C station-to-grid geometry: selected original DIAGI 6.5.0 L5080-5182.
//
// The original *upper-air reference cell* rounds X/DGRID+1.5 by assignment
// to Fortran INTEGER (towards zero), clamped 1..NX/NY. The *wind model station*
// cell uses INTEGER(X/DX+1), which is a different rule and may be out of
// bounds; it is clamped only when obtaining local roughness for ZLOGSTA.
// Weather observations are allowed outside the 5 km × 5 km model grid.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6 {

struct StationXY {
    float relative_x_m{};
    float relative_y_m{};
};

struct GridCell1Based {
    int i{},j{};
};

struct OriginalStationMapping {
    GridCell1Based wind_station_cell;     // IST/JST, can be outside domain.
    GridCell1Based bounded_surface_cell;  // ISC/JSC, for roughness lookup.
    GridCell1Based upper_reference_cell;  // IIUP/JJUP, rounded and clipped.
    float relative_x_km{},relative_y_km{}; // UTMXST/UTMYST.
    float zlogsta = std::numeric_limits<float>::quiet_NaN();
};

// Mirrors Fortran's implicit real->INTEGER truncation. Do not use floor()
// or std::round(). Validate casting range to avoid C++ undefined behavior.
inline int trunc_fortran(float value) {
    if (!std::isfinite(value) ||
        value > static_cast<float>(std::numeric_limits<int>::max()/2) ||
        value < static_cast<float>(std::numeric_limits<int>::min()/2)) {
        throw std::invalid_argument("P6C station coordinate outside safe integer range");
    }
    return static_cast<int>(value);
}

inline GridCell1Based upper_reference_cell(StationXY point,
                                           int nx,int ny,float spacing_m) {
    if (nx<=0 || ny<=0 || !(spacing_m>0) ||
        !std::isfinite(spacing_m) ||
        !std::isfinite(point.relative_x_m) ||
        !std::isfinite(point.relative_y_m)) {
        throw std::invalid_argument("P6C invalid station or geometry");
    }
    return {
        std::clamp(trunc_fortran(point.relative_x_m/spacing_m+1.5f),1,nx),
        std::clamp(trunc_fortran(point.relative_y_m/spacing_m+1.5f),1,ny)
    };
}

inline GridCell1Based wind_station_cell(StationXY point,
                                        float spacing_m) {
    if(!(spacing_m>0)||!std::isfinite(spacing_m)||
        !std::isfinite(point.relative_x_m)||
        !std::isfinite(point.relative_y_m)) {
        throw std::invalid_argument("P6C invalid wind station geometry");
    }
    return {
        trunc_fortran(point.relative_x_m/spacing_m+1.0f),
        trunc_fortran(point.relative_y_m/spacing_m+1.0f)
    };
}

inline float first_layer_log_wind_factor(float first_center_agl_m,
                                        float anemometer_agl_m,
                                        float roughness_m) {
    if(!(first_center_agl_m>0) || !(anemometer_agl_m>0) ||
       !(roughness_m>0) || !std::isfinite(first_center_agl_m) ||
       !std::isfinite(anemometer_agl_m) || !std::isfinite(roughness_m)) {
       throw std::invalid_argument("P6C invalid logarithmic wind vertical levels");
    }
    const float ln_z0=std::log(roughness_m);
    const float ln_z1=std::log(first_center_agl_m);
    const float ln_z2=std::log(anemometer_agl_m);
    const float denom=ln_z2-ln_z0;
    if(!(std::abs(denom)>1.0e-6f)) {
       throw std::invalid_argument("P6C anemometer height almost equals roughness");
    }
    const float factor=(ln_z1-ln_z0)/denom;
    if(!std::isfinite(factor))throw std::invalid_argument("P6C invalid wind factor");
    return factor;
}

inline OriginalStationMapping surface_station_mapping(
        StationXY xy,int nx,int ny,float spacing_m,
        const std::vector<float>& roughness_i_fastest,
        float first_layer_midpoint_agl_m,float anemometer_agl_m) {
    if(nx<=0||ny<=0||
       roughness_i_fastest.size()!=static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny)){
        throw std::invalid_argument("P6C roughness grid mismatch");
    }
    const auto w=wind_station_cell(xy,spacing_m);
    const GridCell1Based bounded{
        std::clamp(w.i,1,nx),std::clamp(w.j,1,ny)
    };
    const std::size_t idx=static_cast<std::size_t>(bounded.j-1) *
                          static_cast<std::size_t>(nx) +
                          static_cast<std::size_t>(bounded.i-1);
    OriginalStationMapping out;
    out.wind_station_cell=w;
    out.bounded_surface_cell=bounded;
    out.upper_reference_cell=upper_reference_cell(xy,nx,ny,spacing_m);
    out.relative_x_km=0.001f*xy.relative_x_m;
    out.relative_y_km=0.001f*xy.relative_y_m;
    out.zlogsta=first_layer_log_wind_factor(
        first_layer_midpoint_agl_m,anemometer_agl_m,
        roughness_i_fastest[idx]);
    return out;
}

// Original CALMET READCF ZMID(i)=0.5*(ZFACE(i+1)+ZFACE(i)),
// DIAGI CELLZB(i)=ZFACE(i), DZ(i)=ZFACE(i+1)-ZFACE(i).
inline std::vector<float> original_layer_midpoints(
        const std::vector<float>& zfaces_m) {
    if(zfaces_m.size()<2 || zfaces_m.size()>13)
        throw std::invalid_argument("P6C invalid vertical interface count");
    std::vector<float> zmid;
    zmid.reserve(zfaces_m.size()-1);
    for(std::size_t k=0;k+1<zfaces_m.size();++k){
        if(!(std::isfinite(zfaces_m[k]) && std::isfinite(zfaces_m[k+1])) ||
           !(zfaces_m[k+1]>zfaces_m[k])) {
           throw std::invalid_argument("P6C vertical interfaces not increasing");
        }
        zmid.push_back(0.5f*(zfaces_m[k+1]+zfaces_m[k]));
    }
    return zmid;
}
} // namespace cteas::calmet::p6
