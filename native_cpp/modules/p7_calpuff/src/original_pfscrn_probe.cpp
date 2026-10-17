#include "cteas/puff/receptors.hpp"
#include <bit>
#include <cstdint>
#include <iomanip>
#include <iostream>

int main() {
    float xo=0,yo=0,xn=0,yn=0,xr=0,yr=0,r2=0;
    while(std::cin>>xo>>yo>>xn>>yn>>xr>>yr>>r2) {
        const auto result=cteas::puff::original_puff_screen(
            xo,yo,xn,yn,xr,yr,r2);
        const float dist=static_cast<float>(result.closest_distance_squared);
        std::cout<<std::hex<<std::setfill('0')<<std::setw(8)
                 <<std::bit_cast<std::uint32_t>(dist)
                 <<std::dec<<" "<<(result.has_impact?1:0)<<"\n";
    }
    return std::cin.eof()?0:2;
}
