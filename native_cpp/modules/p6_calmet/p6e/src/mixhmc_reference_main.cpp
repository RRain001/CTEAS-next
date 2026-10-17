#include "cteas/p6e/mixhmc.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(){
    int cases=0;
    if(!(std::cin>>cases)||cases<1)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c){
        cteas::p6e::MixhmcInput x;
        if(!(std::cin>>x.wt_mks>>x.gamma_kperm>>x.threshold_wm2perm
            >>x.zimax_m>>x.htold_m>>x.dptt_k>>x.tht_k>>x.thtp_k
            >>x.izicrlx>>x.tzicrlx_s>>x.dptmin_kperm
            >>x.twodte_s>>x.onedte_s>>x.timestep_s))return 3;
        try{
            auto r=cteas::p6e::mixhmc_lapse2(x);
            std::cout<<c<<' '<<r.ziconv_m<<' '<<r.dptt_k<<' '
                     <<r.gamma_kperm<<' '<<r.tht_k<<' '<<r.thtp_k<<'\n';
        }catch(const std::exception& e){
            std::cerr<<"MIXHMC "<<e.what()<<'\n';return 4;
        }
    }
}
