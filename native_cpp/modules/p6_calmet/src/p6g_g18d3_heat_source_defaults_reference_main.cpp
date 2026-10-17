// G18D3 strict REAL*4 oracle against the unmodified CALMET BLOCK DATA.
#include "cteas/p6/p6g_g18d3_heat_source_defaults.hpp"
#include <iomanip>
#include <iostream>
int main() {
    const auto c=cteas::calmet::p6g::g18d3_original_block_data_hflux();
    std::cout<<std::scientific<<std::setprecision(16)
             <<c.ha1<<"\n"<<c.ha2<<"\n"<<c.hb1<<"\n"<<c.hb2<<"\n"
             <<c.hc1<<"\n"<<c.hc2<<"\n"<<c.hc3p1<<"\n";
    return 0;
}
