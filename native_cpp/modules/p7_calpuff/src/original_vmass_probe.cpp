#include "cteas/puff/original_vmass.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main() {
    using namespace cteas::puff;
    try {
        int id=0,code=0,stab=0,tilt=0;
        float pbl=0,zpb=0,zpe=0,sigzb=0,sigze=0,ziold=0,zmax=0;
        float qm1=0,qu1=0,qm2=0,qu2=0;
        while(std::cin>>id>>code>>stab>>tilt>>pbl>>zpb>>zpe>>
              sigzb>>sigze>>ziold>>zmax>>qm1>>qu1>>qm2>>qu2) {
            VmassInputs in;
            in.puff_code=code;in.stability_class=stab;in.plume_tilt=tilt;
            in.pbl_height_m=pbl;
            in.height_begin_m=zpb;in.height_end_m=zpe;
            in.sigma_z_begin_m=sigzb;in.sigma_z_end_m=sigze;
            in.ziold_m=ziold;in.zimax_m=zmax;
            in.mass_mixed={qm1,qm2};in.mass_above={qu1,qu2};
            const auto o=original_vmass(in);
            std::cout<<id<<" "<<o.puff_code<<" "
                <<std::scientific<<std::setprecision(16)
                <<o.reflecting_lid_m<<" "<<o.ziold_m<<" "<<o.zimax_m<<" "
                <<o.mass_mixed.at(0)<<" "<<o.mass_above.at(0)<<" "
                <<o.mass_mixed.at(1)<<" "<<o.mass_above.at(1)<<"\n";
        }
        if(!std::cin.eof())throw std::runtime_error("invalid VMASS test input");
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"P7_NATIVE_VMASS_PROBE=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
