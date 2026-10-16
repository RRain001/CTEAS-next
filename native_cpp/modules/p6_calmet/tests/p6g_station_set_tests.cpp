#include "cteas/p6/calmet_station_set.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

using cteas::calmet::p6g::original_calmet_multi_station_deck;
static void check(bool value,const char* msg){
    if(!value)throw std::runtime_error(msg);
}

int main(){
    try{
        const std::string one=
            "! SS1 = 'S001' 58321 511.123 3532.271 0 10.0 !\n"
            "! US1 = 'U001' 58424 513.456 3533.789 0 !\n";
        const auto frozen=cteas::calmet::p6::original_calmet_station_deck(
            one,510.885f,3531.269f);
        const auto native=original_calmet_multi_station_deck(
            one,510.885f,3531.269f,1,1);
        check(native.surface.size()==1&&native.upper.size()==1,
              "single station count");
        check(native.surface[0].id==frozen.surface.id&&
              native.upper[0].id==frozen.upper.id,"single station identity");
        check(native.surface[0].local_x_m==frozen.surface.local_x_m&&
              native.surface[0].local_y_m==frozen.surface.local_y_m&&
              native.upper[0].local_x_m==frozen.upper.local_x_m&&
              native.upper[0].local_y_m==frozen.upper.local_y_m,
              "original REAL*4 single-station coordinate exact parity");

        const std::string many=
            "! US2 = 'U002' 58425 512.000 3535.000 0 !\n"
            "! SS3 = 'S003' 58323 514.000 3534.000 0 12.0 !\n"
            "! SS1 = 'S001' 58321 511.123 3532.271 0 10.0 !\n"
            "! US1 = 'U001' 58424 513.456 3533.789 0 !\n"
            "! SS2 = 'S002' 58322 512.500 3533.000 0 11.0 !\n";
        const auto multi=original_calmet_multi_station_deck(
            many,510.885f,3531.269f,3,2);
        check(multi.surface.size()==3&&multi.upper.size()==2,
              "3x2 group shape");
        check(multi.surface[0].id==58321&&multi.surface[1].id==58322&&
              multi.surface[2].id==58323&&multi.upper[0].id==58424&&
              multi.upper[1].id==58425,
              "declared station ordinal ordering");
        check(multi.surface[0].local_x_m==frozen.surface.local_x_m&&
              multi.upper[0].local_x_m==frozen.upper.local_x_m,
              "stable REAL*4 coords after adding stations");
        const auto reject=[&](const std::string& deck,int s,int u) {
            bool caught=false;
            try{(void)original_calmet_multi_station_deck(
                    deck,510.885f,3531.269f,s,u);}
            catch(const std::invalid_argument&){caught=true;}
            check(caught,"invalid station group unexpectedly accepted");
        };
        reject(many,4,2); // missing SS4
        reject(many,3,3); // missing US3
        reject(many+"! SS2 = 'DUPE' 58326 511 3531 0 10 !\n",3,2);
        reject(many+"! US3 = 'DUPID' 58424 511 3531 0 !\n",3,3);
        reject(many+"! SS4 = 'BADHT' 58327 511 3531 0 0 !\n",4,2);
        reject(many+"! US0 = 'BAD' 58426 511 3531 0 !\n",3,2);
        std::cout<<"PASS P6G_MULTI_STATION_REAL4_SINGLE_PAIR_PARITY\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P6G_MULTI_STATION_FAIL "<<e.what()<<'\n';
        return 1;
    }
}
