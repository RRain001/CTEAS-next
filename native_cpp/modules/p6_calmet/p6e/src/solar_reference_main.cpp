#include "cteas/p6e/solar.hpp"
#include <array>
#include <iomanip>
#include <iostream>
int main(){
    constexpr std::array<int,6> dates{1,80,172,266,355,366};
    constexpr std::array<int,3> zones{-8,0,8};
    const cteas::p6e::Grid grid{
        3,2,{31.91f,31.94f,31.97f,0.f,-31.94f,66.6f},
        {117.11f,117.14f,117.17f,0.f,-120.f,90.f}
    };
    std::cout<<std::scientific<<std::setprecision(11);
    int n=0;
    for(int day:dates)for(int zone:zones){
        ++n;
        auto r=cteas::p6e::calculate(grid,day,zone);
        for(int h=1;h<=26;++h)
            for(std::size_t j=0;j<grid.ny;++j)
                for(std::size_t i=0;i<grid.nx;++i)
                    std::cout<<n<<' '<<(i+1)<<' '<<(j+1)<<' '<<h
                             <<' '<<r.at(static_cast<std::size_t>(h-1),i,j)<<'\n';
    }
}
