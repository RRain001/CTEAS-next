#include "cteas/p6/station_geometry.hpp"
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
int main(int argc,char** argv){
    if(argc!=3){
        std::cerr<<"Usage: cteas_p6_stations INPUT.txt OUTPUT.csv\n";
        return 2;
    }
    try{
        std::ifstream in(argv[1]);
        if(!in)throw std::runtime_error("station input file absent");
        constexpr int nx=50,ny=50;
        int nssta=0,nusta=0;
        if(!(in>>nssta>>nusta) || nssta<1 || nssta>350 ||
           nusta<1 || nusta>99)throw std::runtime_error("station count invalid");
        std::vector<float> zfaces(10);
        for(auto& f:zfaces)if(!(in>>f))throw std::runtime_error("short ZFACE");
        const auto mid=cteas::calmet::p6::original_layer_midpoints(zfaces);
        std::vector<float> z0(2500);
        for(auto& v:z0)if(!(in>>v))throw std::runtime_error("short roughness");
        struct Station{float x,y,anem;};
        std::vector<Station> surf(static_cast<std::size_t>(nssta));
        for(auto& st:surf)if(!(in>>st.x>>st.y>>st.anem))
            throw std::runtime_error("short surface station entry");
        std::vector<cteas::calmet::p6::StationXY> upper(static_cast<std::size_t>(nusta));
        for(auto& st:upper)if(!(in>>st.relative_x_m>>st.relative_y_m))
            throw std::runtime_error("short upper station entry");
        std::string extra;
        if(in>>extra)throw std::runtime_error("trailing station data");
        std::ofstream out(argv[2]);
        if(!out)throw std::runtime_error("station output inaccessible");
        out<<"kind,n,x_km,y_km,ist,jst,isc,jsc,iiup,jjup,zlogsta\n";
        out<<std::fixed<<std::setprecision(9);
        for(std::size_t n=0;n<surf.size();++n){
            const auto& st=surf[n];
            const auto m=cteas::calmet::p6::surface_station_mapping(
                {st.x,st.y},nx,ny,100.0f,z0,mid[0],st.anem);
            out<<"S,"<<n+1<<','<<m.relative_x_km<<','<<m.relative_y_km
               <<','<<m.wind_station_cell.i<<','<<m.wind_station_cell.j
               <<','<<m.bounded_surface_cell.i<<','<<m.bounded_surface_cell.j
               <<",0,0"
               <<','<<m.zlogsta<<'\n';
        }
        for(std::size_t n=0;n<upper.size();++n){
            const auto& st=upper[n];
            const auto w=cteas::calmet::p6::wind_station_cell(st,100.0f);
            const auto u=cteas::calmet::p6::upper_reference_cell(st,nx,ny,100.0f);
            out<<"U,"<<n+1<<','<<st.relative_x_m*0.001f<<','
               <<st.relative_y_m*0.001f
               <<','<<w.i<<','<<w.j<<",0,0,"
               <<u.i<<','<<u.j<<",0.000000000\n";
        }
        if(!out)throw std::runtime_error("partial station output");
        std::cout<<"PASS_P6C_STATION_CANDIDATE_ONLY\n";
    }catch(const std::exception& e){
        std::cerr<<"P6C_STATION_ERROR "<<e.what()<<'\n';return 1;
    }
    return 0;
}
