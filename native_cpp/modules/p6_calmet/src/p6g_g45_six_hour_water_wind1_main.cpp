// S4-R1c4a source-only six authentic hours, only G42/WIND1.
// Existing G14 station clock and native previous ZICONV are not committed.
#include "cteas/p6/p6g_g45_six_hour_water_wind1.hpp"
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
        if(argc!=6||
           std::string(argv[1])!="--six-original-source-wind1-test-only")
            throw std::invalid_argument(
                "G45 requires explicitly selected original NOAA 6h "
                "WIND1, met.inp GEO.DAT SURF.DAT UP.DAT");
        p6g::G19SourceFilePaths paths;
        paths.met_inp=argv[2];paths.geo_dat=argv[3];
        paths.surf_dat=argv[4];paths.ordered_up_dat={argv[5]};
        const auto diagnostic=p6g::g45_selected_source_six_hour_wind1(
            paths,true);
        if(diagnostic.hours.size()!=6||
           diagnostic.source_end_utc.size()!=6||
           diagnostic.original_water_cells!=63||
           diagnostic.original_p5_surf_mutated||
           diagnostic.original_previous_ziconv_accepted||
           diagnostic.g21_g39_g24_g26_accepted)
            throw std::logic_error("G45 unaccepted G14 status promoted");
        const auto read=p6g::g19_load_source_clock_only(paths);
        const auto nx=static_cast<std::size_t>(read.grid.nx);
        const auto n=nx*static_cast<std::size_t>(read.grid.ny);
        std::cout<<std::setprecision(std::numeric_limits<float>::max_digits10);
        std::cout<<"hour_end_utc_seconds,i,j,landuse,wind1_u_mps,"
                    "wind1_v_mps,missing_surface_sites,calm_surface_sites\n";
        std::size_t count=0;
        for(std::size_t h=0;h<6;++h) {
            const auto& raw=diagnostic.hours[h];
            std::size_t rows=0;
            for(std::size_t k=0;k<n;++k) {
                const int cat=read.grid.landuse[k];
                if(cat<read.grid.iwat1||cat>read.grid.iwat2)continue;
                const float u=raw.native_firstguess.u_mps[k];
                const float v=raw.native_firstguess.v_mps[k];
                if(!std::isfinite(u)||!std::isfinite(v))
                    throw std::logic_error("G45 invalid native observed wind");
                std::cout<<diagnostic.source_end_utc[h].time_since_epoch().count()
                         <<','<<k%nx+1<<','<<k/nx+1<<','<<cat
                         <<','<<u<<','<<v<<','
                         <<raw.missing_observed_surface_sites<<','
                         <<raw.calm_observed_surface_sites<<'\n';
                ++rows;++count;
            }
            if(rows!=63)
                throw std::logic_error("G45 genuine hourly water grid changed");
            std::cerr<<"S4R1C4A_REAL_NOAA_HOUR="<<h+1
                     <<" SOURCE_END_UTC="
                     <<diagnostic.source_end_utc[h].time_since_epoch().count()
                     <<" MISSING_SS="<<raw.missing_observed_surface_sites
                     <<" CALM_SS="<<raw.calm_observed_surface_sites
                     <<" CELLS="<<rows<<"\n";
        }
        if(count!=378)
            throw std::logic_error("G45 63x6 source output incomplete");
        std::cerr<<"S4R1C4A_NATIVE_SIX_HOUR_378_WATER_WIND1=PRODUCED_UNVERIFIED "
                    "PREVIOUS_ZICONV_G21_G39_G24_G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C4A_NATIVE_SOURCE_WIND1_DENIED "<<e.what()<<"\n";
        return 2;
    }
}
