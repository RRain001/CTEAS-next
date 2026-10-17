#include "cteas/puff/original_pufrecs_geometry.hpp"
#include <bit>
#include <cstdint>
#include <iomanip>
#include <iostream>

static void hex(float x){
    std::cout<<std::hex<<std::setfill('0')<<std::setw(8)
             <<std::bit_cast<std::uint32_t>(x)<<std::dec;
}
int main(){
    float x,y,x1,y1,x2,y2,syb,sye,fclip,xttb,uavg;
    int clip;
    while(std::cin>>x>>y>>x1>>y1>>x2>>y2>>syb>>sye
                  >>fclip>>xttb>>uavg>>clip){
        const auto slg=cteas::puff::original_slgfrac(
            x,y,x1,y1,x2,y2);
        const auto geom=cteas::puff::original_pufrecs_geometry({
            .x_receptor_m=x,.y_receptor_m=y,
            .x_begin_m=x2,.y_begin_m=y2,
            .x_end_m=x1,.y_end_m=y1,
            .sigma_y_begin_m=syb,.sigma_y_end_m=sye,
            .fclip=fclip,.travel_distance_begin_m=xttb,
            .mean_wind_ms=uavg,.clip=clip!=0
        });
        for(float v:{slg.along_m,slg.across_m,slg.fraction,
                     slg.projected_length_m,slg.inverse_length_per_m,
                     geom.fraction,geom.along_m,
                     geom.distance_to_receptor_m,geom.time_to_receptor_s}){
            hex(v);std::cout<<" ";
        }
        std::cout<<"\n";
    }
    return std::cin.eof()?0:2;
}
