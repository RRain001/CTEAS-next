// G18C1 native AVEMIX oracle; original vendor Fortran extracted separately.
#include "cteas/p6/p6g_g18c1_avemix.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main() {
    try {
        int nx=0,ny=0,mnmdav=0;
        float half=0.f,spacing=0.f;
        if(!(std::cin>>nx>>ny>>mnmdav>>half>>spacing)||
           nx<2||ny<2||nx>64||ny>64)
            throw std::invalid_argument("G18C1 source input invalid");
        const auto count=static_cast<std::size_t>(nx)*ny;
        std::vector<float> u(count),v(count),zi(count),zc(count);
        for(std::size_t j=0;j<count;++j)
            if(!(std::cin>>u[j]>>v[j]>>zi[j]>>zc[j]))
                throw std::invalid_argument("G18C1 missing source cell data");
        const auto r=cteas::calmet::p6g::g18c1_original_avemix_rebuild(
            nx,ny,mnmdav,half,spacing,u,v,zi,zc);
        std::cout<<std::scientific<<std::setprecision(10);
        for(std::size_t j=0;j<count;++j)
            std::cout<<r.zi_m[j]<<" "<<r.ziconv_m[j]<<"\n";
    }catch(const std::exception& e) {
        std::cerr<<"G18C1_AVEMIX_ERROR "<<e.what()<<"\n";
        return 1;
    }
}
