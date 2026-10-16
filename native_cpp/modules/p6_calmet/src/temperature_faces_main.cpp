#include "cteas/p6/temperature_faces.hpp"
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
int main(int argc,char** argv){
 if(argc!=4){std::cerr<<"usage: cteas_p6_facet UP.DAT OUT.csv STATION_ID\n";return 2;}
 try{
  using namespace cteas::calmet::p6;
  const auto up=read_upper_2022(argv[1],std::stoi(argv[3]));
  const std::vector<float> faces{0,20,40,80,160,320,640,1200,2000,3000};
  std::ofstream out(argv[2]);
  if(!out)throw std::runtime_error("FACET output unavailable");
  out<<"station_id,sounding_index,epoch_end,face_index,height_m,temperature_k\n"
     <<std::fixed<<std::setprecision(8);
  for(std::size_t n=0;n<up.soundings.size();++n){
    const auto temp=calmet_facet_temperatures(up.soundings[n],faces);
    for(std::size_t k=0;k<temp.size();++k)
       out<<up.station_id<<','<<n+1<<','
          <<up.soundings[n].end.time_since_epoch().count()<<','
          <<k+1<<','<<faces[k]<<','<<temp[k]<<'\n';
  }
  if(!out)throw std::runtime_error("FACET output incomplete");
  std::cout<<"P6C_FACET_MODEL_FACE_TEMPERATURES_ONLY profiles="
           <<up.soundings.size()<<"\n";return 0;
 }catch(const std::exception& e){std::cerr<<"P6C_FACET_ERROR: "<<e.what()<<'\n';return 1;}
}
