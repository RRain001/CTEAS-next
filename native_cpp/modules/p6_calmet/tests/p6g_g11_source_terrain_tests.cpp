#include "cteas/p6/p6g_terrain_hour.hpp"
#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
using namespace cteas::calmet::p6g;
static void check(bool condition,const char* reason){
    if(!condition)throw std::runtime_error(reason);
}
template<class F> static void reject(F fun,const char* what){
    bool failed=false;
    try{(void)fun();}catch(const std::invalid_argument&){failed=true;}
    check(failed,what);
}
int main() {
    try{
        GeoGrid geo;
        geo.nx=12;geo.ny=12;geo.grid_km=10.f;
        geo.iwat1=50;geo.iwat2=55;
        for(int j=0;j<12;++j)for(int i=0;i<12;++i){
            geo.terrain_m.push_back(100.f+250.f*i+150.f*j);
            geo.landuse.push_back(i==3&&j==3?50:20);
        }
        const auto static_terrain=prepare_g11_terrain(geo,35.f);
        check(static_terrain.terrain_m.size()==144&&
              static_terrain.hmax_m.size()==144&&
              static_terrain.dist_hmin_m.size()==144,
              "G11 10km TERSET output geometry incorrect");
        auto hour=TerrainHourG11{};
        hour.provenance=TerrainHourProvenance::SyntheticReferenceFixture;
        hour.isurft=-1;hour.domain_temperature_k=285.f;hour.critfn=10.f;
        hour.lapse_k_per_m.assign(144,0.002f);
        hour.temperature_k.assign(144,280.f);
        hour.sensible_heat_w_m2.assign(144,-120.f);
        const std::vector<float> zface{0,20,40,80,160,320,640,1200,2000,3000};
        cteas::calmet::p6::WindUV wind;
        wind.u.assign(144*9,-3.f);
        wind.v.assign(144*9,-1.f);
        const auto result=apply_g11_terrain_after_wind1(
            static_terrain,hour,zface,wind);
        check(result.field.u.size()==1296&&result.field.v.size()==1296,
              "G11 dynamic FRADJ/SLOPE field size invalid");
        check(result.slope_modified>0,
              "G11 steeper 10km terrain with negative H should cause slope winds");
        check(result.field.u!=wind.u||result.field.v!=wind.v,
              "G11 terrain chain must modify nontrivial source wind");
        for(float x:result.field.u)check(std::isfinite(x),"G11 nonfinite U");
        for(float x:result.field.v)check(std::isfinite(x),"G11 nonfinite V");
        hour.provenance=TerrainHourProvenance::Missing;
        reject([&]{return apply_g11_terrain_after_wind1(
            static_terrain,hour,zface,wind);},
            "G11 implicitly fabricated missing hourly P6E heat fields");
        hour.provenance=TerrainHourProvenance::ValidatedP6EHourlyPhysics;
        reject([&]{return apply_g11_terrain_after_wind1(
            static_terrain,hour,zface,wind);},
            "G11 unaccepted P6E physics provenance was silently trusted");
        hour.provenance=TerrainHourProvenance::SyntheticReferenceFixture;
        hour.temperature_k.pop_back();
        reject([&]{return apply_g11_terrain_after_wind1(
            static_terrain,hour,zface,wind);},
            "G11 incomplete 2D grid accepted");
        hour.temperature_k.push_back(280.f);
        hour.sensible_heat_w_m2[0]=std::nanf("");
        reject([&]{return apply_g11_terrain_after_wind1(
            static_terrain,hour,zface,wind);},
            "G11 nonfinite heat source accepted");
        hour.sensible_heat_w_m2[0]=-120.f;
        auto water=static_terrain;
        water.landuse.assign(144,50);
        const auto blocked=apply_g11_terrain_after_wind1(
            water,hour,zface,wind);
        check(blocked.slope_modified==0,
              "G11 original SLOPE did not skip GEO water surfaces");
        std::cout<<"PASS_G11_SOURCE_TERRAIN_10KM_12X12 FRADJ_CHANGED="
                 <<result.froude_modified<<" SLOPE_CHANGED="<<result.slope_modified
                 <<" WATER_SLOPE_CHANGED="<<blocked.slope_modified<<"\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"FAIL_G11_SOURCE_TERRAIN "<<e.what()<<"\n";return 1;
    }
}
