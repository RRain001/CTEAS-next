#include "cteas/p6/vertical_wind_average.hpp"
#include <array>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
int main(int argc,char** argv){
    if(argc!=4){std::cerr<<"usage: cteas_p6_vertav UP.DAT OUT.csv STATION_ID\n";return 2;}
    try{
        using namespace cteas::calmet::p6;
        const Upper2022 up=read_upper_2022(argv[1],std::stoi(argv[3]));
        const std::vector<float> faces{0,20,40,80,160,320,640,1200,2000,3000};
        std::ofstream out(argv[2]);
        if(!out)throw std::runtime_error("VERTAV output unavailable");
        out<<"station_id,sounding_index,epoch_end,layer,u_mps,v_mps\n";
        out<<std::fixed<<std::setprecision(8);
        for(std::size_t n=0;n<up.soundings.size();++n){
            const auto winds=calmet_vertav(up.soundings[n],faces);
            for(std::size_t k=0;k<winds.size();++k)
                out<<up.station_id<<','<<n+1<<','
                   <<up.soundings[n].end.time_since_epoch().count()
                   <<','<<k+1<<','<<winds[k].u_mps<<','<<winds[k].v_mps<<'\n';
        }
        if(!out)throw std::runtime_error("VERTAV output incomplete");
        std::cout<<"P6C_VERTAV_COMPUTED "<<up.soundings.size()*9*2
                 <<" layer wind values (isolated vertical kernel)\n";return 0;
    }catch(const std::exception& e){
        std::cerr<<"P6C_VERTAV_ERROR: "<<e.what()<<'\n';return 1;
    }
}
