#include "cteas/p6e/avetmp.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
    int cases=0;
    if(!(std::cin>>cases)||cases<1)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c){
        int nx=0,ny=0,mnmdav=0;
        float hafang=0.f,dgrid=0.f;
        if(!(std::cin>>nx>>ny>>mnmdav>>hafang>>dgrid))return 3;
        if(nx<1||ny<1)return 3;
        const auto n=static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny);
        cteas::p6e::AvetmpInput a;
        a.nx=static_cast<std::size_t>(nx);a.ny=static_cast<std::size_t>(ny);
        a.mnmdav=mnmdav;a.hafang_deg=hafang;a.dgrid_m=dgrid;
        a.u_ms.resize(n);a.v_ms.resize(n);a.temperature_k.resize(n);
        for(std::size_t k=0;k<n;++k)
            if(!(std::cin>>a.u_ms[k]>>a.v_ms[k]>>a.temperature_k[k]))return 4;
        try{
            const auto out=cteas::p6e::avetmp(a);
            for(std::size_t j=0;j<a.ny;++j)
                for(std::size_t i=0;i<a.nx;++i)
                    std::cout<<c<<' '<<i+1U<<' '<<j+1U<<' '
                             <<out[j*a.nx+i]<<'\n';
        }catch(const std::exception& e){
            std::cerr<<"AVETMP "<<e.what()<<'\n';return 5;
        }
    }
}
