#include "cteas/p6e/mixhbg.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
    int cases=0;
    if(!(std::cin>>cases)||cases<1)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c){
        cteas::p6e::MixhbgInput x;
        if(!(std::cin>>x.wt_mks>>x.gamma_kperm>>x.threshold_wm2perm
            >>x.zimax_m>>x.zimin_m>>x.ustar_ms>>x.el_m>>x.zicbgold_m
            >>x.tk_k>>x.izicrlx>>x.tzicrlx_s>>x.dptmin_kperm
            >>x.timestep_s))return 3;
        try{
            auto r=cteas::p6e::mixhbg_lapse2(x);
            std::cout<<c<<' '<<r.ziconv_m<<' '<<r.gamma_kperm<<'\n';
        }catch(const std::exception& e){
            std::cerr<<"MIXHBG "<<e.what()<<'\n';return 4;
        }
    }
}
