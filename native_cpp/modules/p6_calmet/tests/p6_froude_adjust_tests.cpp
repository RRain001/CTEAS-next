#include "cteas/p6/froude_adjust.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>
int main(){
 try{
    using namespace cteas::calmet::p6;
    std::vector<float> z={0,20};
    std::vector<float> h={100,101,102,103};
    std::vector<float> hmax={110,110,110,110};
    std::vector<float> gamma(4,0.006f),temp(4,285.0f);
    WindUV calm{std::vector<float>(4,0),std::vector<float>(4,0)};
    const auto result=froude_adjust(2,2,1,100,100,h,hmax,gamma,temp,-1,285,1.0f,z,calm);
    for(float x:result.u)if(x!=0)throw std::runtime_error("calm FRADJ changed");
    for(float x:result.v)if(x!=0)throw std::runtime_error("calm FRADJ changed");
    bool failed=false;
    gamma[0]=std::numeric_limits<float>::quiet_NaN();
    try{(void)froude_adjust(2,2,1,100,100,h,hmax,gamma,temp,-1,285,1,z,calm);}
    catch(const std::invalid_argument&){failed=true;}
    if(!failed)throw std::runtime_error("nonfinite lapse rate accepted");
    std::cout<<"PASS P6D_FRADJ_SOFTWARE_ONLY\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
