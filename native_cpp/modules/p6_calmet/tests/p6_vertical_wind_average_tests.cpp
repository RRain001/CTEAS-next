#include "cteas/p6/vertical_wind_average.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace cteas::calmet::p6;
void req(bool x,const char* msg){if(!x)throw std::runtime_error(msg);}
int main(){
    try{
        UpperSounding profile;profile.levels=3;
        for(const auto& [z,u,v]:{
            std::array<float,3>{0,1,2},
            std::array<float,3>{100,5,6},
            std::array<float,3>{500,10,10}}){
            UpperLevel level;level.height_lgl_m=z;level.u_mps=u;level.v_mps=v;
            profile.data.push_back(level);
        }
        auto winds=calmet_vertav(profile,{0,20,40,80,160,320});
        req(winds.size()==5,"five selected vertical layers");
        for(std::size_t k=0;k<winds.size();++k){
            const float midpoint=std::vector<float>{10,30,60,120,240}[k];
            const float uc=1.f+(midpoint/100.f)*4.f; // between 0 and 100 only
            if(k<3)req(std::abs(winds[k].u_mps-uc)<0.002f,
                       "integral must reproduce linear wind up to 80m");
        }
        profile.data[0].u_mps=999.f;
        bool threw=false;
        try{(void)calmet_vertav(profile,{0,20,40,80,160,320});}
        catch(const std::invalid_argument&){threw=true;}
        req(threw,"missing first-level wind without z=0 must fail");
        profile.data[0].u_mps=1.f;
        threw=false;
        try{(void)calmet_vertav(profile,{0,20,40,80,160,640});}
        catch(const std::invalid_argument&){threw=true;}
        req(threw,"face above top sounding fails");
        std::cout<<"PASS_P6C_ORIGINAL_VERTAV_MATH_SOFTWARE_ONLY\n";return 0;
    }catch(const std::exception& e){
        std::cerr<<e.what()<<'\n';return 1;
    }
}
