// Real 82x85 2SS+1US first-hour post-SLOPE U/V, all 9 levels.
// This is NOT G23 INTER2, G24 final wind or G26 source production.
#include "cteas/p6/p6g_g47_real_water_post_slope.hpp"
#include <cmath>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
namespace p6g=cteas::calmet::p6g;
int main(int argc,char** argv) {
    try {
        if(argc!=6||std::string(argv[1])!="--selected-real-slope-only")
            throw std::invalid_argument(
                "G47 explicit source real NOAA SLOPE and four path arguments required");
        p6g::G19SourceFilePaths files{argv[2],argv[3],argv[4],{argv[5]}};
        const auto result=p6g::g47_actual_noow_water_after_elustr_slope(files,true);
        if(!result.source_raw_p5_unchanged||
           result.native_g23_g24_g26_accepted)
            throw std::logic_error("G47 was promoted to unaccepted G14");
        const auto raw=p6g::g19_load_source_clock_only(files);
        const auto nx=static_cast<std::size_t>(raw.grid.nx);
        const auto ny=static_cast<std::size_t>(raw.grid.ny);
        const auto n=nx*ny;
        const auto& original=result.thermal.native_fradj.corrected_wind;
        const auto& final=result.slope.post_slope_wind;
        if(n!=6970||final.u.size()!=9*n||final.v.size()!=9*n||
           original.u.size()!=9*n||original.v.size()!=9*n)
            throw std::logic_error("G47 original selected 9-layer U/V incomplete");
        const auto epoch=result.end.time_since_epoch().count();
        std::cout<<std::setprecision(std::numeric_limits<float>::max_digits10)
                 <<"i,j,k,hour_end_utc_seconds,landuse,pre_slope_u_mps,"
                   "pre_slope_v_mps,post_slope_u_mps,post_slope_v_mps\n";
        std::size_t water=0;
        for(std::size_t k=0;k<9;++k)
            for(std::size_t j=0;j<ny;++j)
                for(std::size_t i=0;i<nx;++i) {
                    const auto c=j*nx+i,p=k*n+c;
                    if(!std::isfinite(final.u[p])||!std::isfinite(final.v[p]))
                        throw std::logic_error("G47 native SLOPE wind nonfinite");
                    if(k==0&&raw.grid.landuse[c]>=raw.grid.iwat1&&
                       raw.grid.landuse[c]<=raw.grid.iwat2)++water;
                    std::cout<<i+1<<','<<j+1<<','<<k+1<<','<<epoch<<','
                             <<raw.grid.landuse[c]<<','
                             <<original.u[p]<<','<<original.v[p]<<','
                             <<final.u[p]<<','<<final.v[p]<<'\n';
                }
        if(water!=63)throw std::logic_error("G47 water mask changed");
        std::cerr<<"S4R1C6_REAL_NOAA_6970X9_POST_SLOPE_PRODUCED_UNVERIFIED "
                    "G23_G24_G26_P7=NOT_ACCEPTED "
                 <<"SLOPE_CHANGED_COMPONENTS="<<result.slope.changed_slope_components
                 <<" P5_RAW_UNCHANGED=TRUE\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C6_REAL_SOURCE_SLOPE_DENIED "<<e.what()<<'\n';
        return 2;
    }
}
