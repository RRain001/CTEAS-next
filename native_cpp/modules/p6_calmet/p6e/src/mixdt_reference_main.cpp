#include "cteas/p6e/mixdt.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
int main() {
    int cases=0, ns=0,nlev=0;
    if(!(std::cin>>cases>>ns>>nlev)||cases<1||ns<1||nlev<2)return 2;
    std::cout<<std::scientific<<std::setprecision(11);
    for(int c=1;c<=cases;++c) {
        int station=0;
        float htold=0.f,dptmin=0.f,dzzi=0.f;
        if(!(std::cin>>station>>htold>>dptmin>>dzzi))return 3;
        std::vector<cteas::p6e::MixdtSounding> snd(static_cast<std::size_t>(ns));
        for(int st=0;st<ns;++st) {
            auto& s=snd[static_cast<std::size_t>(st)];
            s.height_m.resize(static_cast<std::size_t>(nlev));
            s.temp_k.resize(static_cast<std::size_t>(nlev));
            for(int k=0;k<nlev;++k)
                if(!(std::cin>>s.height_m[static_cast<std::size_t>(k)]
                    >>s.temp_k[static_cast<std::size_t>(k)]))return 4;
        }
        if(station<1||station>ns)return 5;
        try {
            const auto y=cteas::p6e::mixdt(snd[static_cast<std::size_t>(station-1)],
                                           htold,dzzi,dptmin);
            std::cout<<c<<' '<<y.tht_k<<' '<<y.thtp_k
                     <<' '<<y.dtheta_k_per_m<<'\n';
        }catch(const std::exception& e){
            std::cerr<<"P6E MIXDT: "<<e.what()<<'\n';return 6;
        }
    }
}
