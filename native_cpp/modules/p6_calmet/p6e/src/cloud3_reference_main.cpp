#include "cteas/p6e/cloud3.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
    int cases=0,nx=0,ny=0;
    if(!(std::cin>>cases>>nx>>ny)||cases<1||nx<1||ny<1)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    const auto n=static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny);
    for(int c=1;c<=cases;++c){
        std::vector<float> rh(n);
        for(int i=0;i<nx;++i)for(int j=0;j<ny;++j){
            const auto k=static_cast<std::size_t>(j)*static_cast<std::size_t>(nx)+
                         static_cast<std::size_t>(i);
            if(!(std::cin>>rh[k]))return 3;
        }
        try{
            const auto clouds=cteas::p6e::cloud3(
                static_cast<std::size_t>(nx),static_cast<std::size_t>(ny),rh);
            for(int i=0;i<nx;++i)for(int j=0;j<ny;++j){
                const auto k=static_cast<std::size_t>(j)*static_cast<std::size_t>(nx)+
                             static_cast<std::size_t>(i);
                std::cout<<c<<' '<<i+1<<' '<<j+1<<' '<<clouds[k]<<'\n';
            }
        }catch(const std::exception& e){
            std::cerr<<"P6E CLOUD3 "<<e.what()<<'\n';return 4;
        }
    }
}
