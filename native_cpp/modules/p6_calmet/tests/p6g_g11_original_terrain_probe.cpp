// P6G G11 deterministic independent original-vendor FRADJ/SLOPE
// source-lift comparator. Uses the SAME 12x12 10km synthetic fields as the
// Fortran probe, but invokes the separately rewritten C++ kernels.
#include "cteas/p6/p6g_terrain_hour.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
int main(){
    try{
        using namespace cteas::calmet::p6g;
        GeoGrid geo;
        geo.nx=12;geo.ny=12;geo.grid_km=10.f;
        geo.iwat1=50;geo.iwat2=55;
        for(int j=0;j<12;++j)for(int i=0;i<12;++i){
            geo.terrain_m.push_back(100.f+250.f*i+150.f*j);
            geo.landuse.push_back(i==3&&j==3?50:20);
        }
        const auto terrain=prepare_g11_terrain(geo,35.f);
        TerrainHourG11 hourly;
        hourly.provenance=TerrainHourProvenance::SyntheticReferenceFixture;
        hourly.isurft=-1;
        hourly.domain_temperature_k=285.f;
        hourly.critfn=10.f;
        hourly.lapse_k_per_m.assign(144,0.002f);
        hourly.temperature_k.assign(144,280.f);
        hourly.sensible_heat_w_m2.assign(144,-120.f);
        const std::vector<float> zface{
            0,20,40,80,160,320,640,1200,2000,3000
        };
        cteas::calmet::p6::WindUV raw;
        raw.u.assign(1296,3.f);
        raw.v.assign(1296,1.f);
        const auto output=apply_g11_terrain_after_wind1(
            terrain,hourly,zface,std::move(raw));
        if(output.froude_modified==0||output.slope_modified==0)
            throw std::runtime_error("G11 original-source fixture did not exercise both FRADJ and SLOPE");
        std::cout<<std::scientific<<std::setprecision(9);
        for(int k=0;k<9;++k)for(int j=0;j<12;++j)for(int i=0;i<12;++i){
            const auto n=static_cast<std::size_t>(k*144+j*12+i);
            std::cout<<"GRID "<<i+1<<" "<<j+1<<" "<<k+1<<" "
                     <<output.field.u[n]<<" "<<output.field.v[n]<<"\n";
        }
        std::cerr<<"G11_NATIVE_COMBINED fradj_modified="
                 <<output.froude_modified<<" slope_modified="
                 <<output.slope_modified<<"\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"G11_CXX_COMBINED_SOURCE_FAIL "<<e.what()<<"\n";
        return 1;
    }
}
