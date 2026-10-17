#include "cteas/p6e/solar.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void rejects(F f){
    bool thrown=false;
    try{f();}catch(const std::invalid_argument&){thrown=true;}
    assert(thrown);
}
int main(){
    Grid g{2,1,{31.94f,32.0f},{117.14f,117.18f}};
    auto s=calculate(g,172,-8);
    assert(s.sine.size()==52);
    assert(s.at(0,0,0)<0.0f); // keep night negatives
    assert(s.at(12,0,0)>0.0f);
    for(float v:s.sine)assert(std::isfinite(v)&&v>=-1.000001f&&v<=1.000001f);
    assert(calculate(g,1,0).sine.size()==52);
    assert(calculate(g,366,8).sine.size()==52);
    rejects([&]{(void)calculate(g,0,0);});
    rejects([&]{(void)calculate(g,367,0);});
    rejects([&]{(void)calculate(g,172,15);});
    rejects([&]{(void)calculate(Grid{2,1,{31.f},{117.f,117.f}},172,0);});
    rejects([&]{(void)calculate(Grid{1,1,{91.f},{117.f}},172,0);});
    rejects([&]{(void)calculate(Grid{1,1,{31.f},{181.f}},172,0);});
    rejects([&]{(void)calculate(Grid{1,1,{NAN},{117.f}},172,0);});
    try{(void)s.at(26,0,0);assert(false);}catch(const std::out_of_range&){}
}
