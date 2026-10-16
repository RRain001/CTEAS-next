#include "cteas/puff/original_puffct2.hpp"
#include <bit>
#include <cstdint>
#include <iomanip>
#include <iostream>

static void hex(float value) {
    std::cout<<std::hex<<std::setfill('0')<<std::setw(8)
             <<std::bit_cast<std::uint32_t>(value)<<std::dec;
}
int main() {
    float frac,xb,yb,zb,xe,ye,ze,fracz;
    int upslope;
    while(std::cin>>frac>>xb>>yb>>zb>>xe>>ye>>ze>>fracz>>upslope) {
        const auto r=cteas::puff::original_puffct2({
            .x_begin_m=xb,.y_begin_m=yb,.z_begin_m=zb,
            .x_end_m=xe,.y_end_m=ye,.z_end_m=ze,
            .terrain_fraction=fracz,.upslope=upslope!=0
        },frac);
        hex(r.x_m);std::cout<<" ";
        hex(r.y_m);std::cout<<" ";
        hex(r.z_m);std::cout<<"\n";
    }
    return std::cin.eof()?0:2;
}
