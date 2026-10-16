#pragma once
// Original CALMET 6.5.0 SOLAR (calmet.for L30871-30990), independent P6E-E1.
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
struct Grid { std::size_t nx=0,ny=0; std::vector<float> lat,lon_east; };
struct Solar {
    std::size_t nx=0,ny=0;
    // 26 signed half-hour slots from previous day 23:30 to next day 00:30.
    // (slot*ny+j)*nx+i. Negative night values MUST be retained.
    std::vector<float> sine;
    float at(std::size_t slot,std::size_t i,std::size_t j) const {
        if(slot>=26||i>=nx||j>=ny)throw std::out_of_range("SOLAR index");
        return sine.at((slot*ny+j)*nx+i);
    }
};
inline Solar calculate(const Grid& g,int njul,int ibtz){
    if(njul<1||njul>366||ibtz< -14||ibtz>14||g.nx==0||g.ny==0||
       g.nx>static_cast<std::size_t>(-1)/g.ny||
       g.lat.size()!=g.nx*g.ny||g.lon_east.size()!=g.nx*g.ny)
        throw std::invalid_argument("SOLAR dimensions/time");
    const std::size_t n=g.nx*g.ny;
    if(n>static_cast<std::size_t>(-1)/26)throw std::invalid_argument("SOLAR overflow");
    for(std::size_t c=0;c<n;++c)
        if(!std::isfinite(g.lat[c])||!std::isfinite(g.lon_east[c])||
           g.lat[c]<-90.0f||g.lat[c]>90.0f||
           g.lon_east[c]<-180.0f||g.lon_east[c]>180.0f)
            throw std::invalid_argument("SOLAR coordinate");
    // Preserve source REAL*4 constant precision and expression grouping.
    const float d=(static_cast<float>(njul)-1.0f)*0.9856479f;
    const float radd=0.0174533f*d;
    const float xsind=std::sin(radd),xcosd=std::cos(radd);
    const float rad2d=2.0f*radd;
    const float sin2d=std::sin(rad2d),cos2d=std::cos(rad2d);
    const float em=12.0f+0.12357f*xsind-0.004289f*xcosd
                  +0.153809f*sin2d+0.060783f*cos2d;
    const float sigma=279.9348f+d+1.914827f*xsind-0.079525f*xcosd
                      +0.019938f*sin2d-0.00162f*cos2d;
    const float sincd=0.39784989f*std::sin(0.0174533f*sigma);
    const float capd=std::asin(sincd),coscd=std::cos(capd);
    Solar out{g.nx,g.ny,std::vector<float>(26*n)};
    for(std::size_t j=0;j<g.ny;++j)
        for(std::size_t i=0;i<g.nx;++i){
            const std::size_t c=j*g.nx+i;
            const float radlat=0.0174533f*g.lat[c];
            const float sinlat=std::sin(radlat),coslat=std::cos(radlat);
            for(int ihr=1;ihr<=26;++ihr){
                const float gmt=static_cast<float>(ihr-1)-0.5f+
                                static_cast<float>(ibtz);
                const float solha=15.0f*(gmt-em)+g.lon_east[c];
                out.sine[static_cast<std::size_t>(ihr-1)*n+c]=
                    sinlat*sincd+coslat*coscd*std::cos(0.0174533f*solha);
            }
        }
    return out;
}
} // namespace cteas::p6e
