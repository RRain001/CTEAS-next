#include "cteas/p6e/cloud3.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void rejects(F f){bool yes=false;try{f();}catch(const std::invalid_argument&){yes=true;}assert(yes);}
int main(){
    const auto c=cloud3(4,1,{0.f,50.f,99.f,100.f});
    assert(c.size()==4);
    assert(c[0]>0.1f&&c[0]<0.3f);
    assert(c[1]>c[0]);
    assert(c[2]==1.f&&c[3]==1.f);
    rejects([&]{(void)cloud3(2,2,{99.f});});
    rejects([&]{(void)cloud3(1,1,{-1.f});});
    rejects([&]{(void)cloud3(1,1,{101.f});});
    rejects([&]{(void)cloud3(0,1,{});});
}
