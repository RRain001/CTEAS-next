// S4-R1b authentic source clock and water-only shortwave emission.
// Never reads the original MET.DAT, original trace, or native G24 wind.
#include "cteas/p6/p6g_g40_real_water_shortwave_source.hpp"
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
namespace p6g=cteas::calmet::p6g;
int main(int argc,char** argv) {
    try {
        if(argc<6||std::string(argv[1])!="--real-source-only")
            throw std::invalid_argument(
                "G40 requires --real-source-only original-met.inp GEO.DAT SURF.DAT ordered-UP.DAT...");
        p6g::G19SourceFilePaths paths;
        paths.met_inp=argv[2];paths.geo_dat=argv[3];paths.surf_dat=argv[4];
        for(int i=5;i<argc;++i)paths.ordered_up_dat.emplace_back(argv[i]);
        const auto actual=p6g::g19_load_source_clock_only(paths);
        const auto result=p6g::g40_real_source_water_shortwave(actual,true);
        if(result.post_fradj_iavet_two_pass_accepted||
           result.land_thermal_elustr_accepted||
           result.native_g24_wind_accepted||
           result.native_g14_g26_production_accepted)
            throw std::logic_error("G40 source-only result promoted");
        std::cout<<std::scientific<<std::setprecision(9);
        for(const auto& r:result.rows)
            std::cout<<r.one_based_i<<' '<<r.one_based_j<<' '<<r.utc_hour_end
                     <<' '<<r.category<<' '<<r.nearest_station_ordinal
                     <<' '<<r.cloud_tenths<<' '<<r.solar_sine<<' '
                     <<r.qsw_wm2<<' '<<r.qh_water_wm2<<' '
                     <<r.observed_temperature_carrier_k<<'\n';
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"S4R1B_FAIL_CLOSED "<<e.what()<<'\n';
        return 2;
    }
}
