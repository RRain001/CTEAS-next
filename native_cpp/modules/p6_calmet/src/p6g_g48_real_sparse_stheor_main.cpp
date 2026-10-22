// S4-R1c7b actual NOAA first-hour sparse ground-station STHEOR/DIAGI.
// No INTER2, G24 final wind, G14 physical hour commit or G26/P7 admission.
#include "cteas/p6/p6g_g48_real_sparse_stheor.hpp"
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
        if(argc!=6||std::string(argv[1])!="--real-sparse-stheor-only")
            throw std::invalid_argument("G48 needs explicit original-real sparse research opt-in and met GEO SURF UP");
        p6g::G19SourceFilePaths paths{argv[2],argv[3],argv[4],{argv[5]}};
        const auto native=p6g::g48_real_sparse_stheor_first_hour(paths,true);
        if(!native.source_p5_raw_wind_unchanged||
           native.native_g23_inter2_or_g26_ready||
           native.native_valid_station.size()!=1||
           native.missing_wind_skipped!=1)
            throw std::logic_error("G48 original missing-wind STHEOR gate failed");
        const auto source=p6g::g19_load_source_clock_only(paths);
        const auto nx=static_cast<std::size_t>(source.grid.nx);
        const auto ny=static_cast<std::size_t>(source.grid.ny);
        if(nx!=82||ny!=85)throw std::logic_error("G48 unexpected original source GEO");
        std::cout<<std::setprecision(std::numeric_limits<float>::max_digits10)
                 <<"surface_ordinal_1based,surface_id,upper_id,i,j,k,"
                   "hour_end_utc_seconds,levels_filled,"
                   "native_u_mps,native_v_mps,native_zii_m,"
                   "native_station_qh_wm2,native_station_ustar_mps\n";
        for(const auto& site:native.native_valid_station) {
            const auto ordinal=native.source_valid_surface_ordinals.front();
            if(site.levels_filled<1||site.levels_filled>9||
               site.cell>=nx*ny)
                throw std::logic_error("G48 native station output invalid");
            const auto i=site.cell%nx+1, j=site.cell/nx+1;
            for(std::size_t k=0;k<9;++k) {
                if(!std::isfinite(site.diagi_profile.u_mps[k])||
                   !std::isfinite(site.diagi_profile.v_mps[k]))
                    throw std::logic_error("G48 finite source DIAGI required");
                std::cout<<ordinal<<','<<site.surface_id<<','<<site.upper_id
                         <<','<<i<<','<<j<<','<<k+1<<','
                         <<site.end.time_since_epoch().count()<<','
                         <<site.levels_filled<<','
                         <<site.diagi_profile.u_mps[k]<<','
                         <<site.diagi_profile.v_mps[k]<<','
                         <<site.station_mixing.zii_to_similt_m<<','
                         <<site.station_flux.sensible_wm2<<','
                         <<site.station_flux.friction_velocity_mps<<'\n';
            }
        }
        std::cerr<<"S4R1C7B_GENUINE_2SS1US_FIRSTHOUR_NATIVE_STHEOR=PRODUCED_UNVERIFIED "
                    "VALID_SS=1 SKIPPED_MISSING_SS=1 P5_RAW_UNCHANGED=TRUE "
                    "G23_INTER2_G24_G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C7B_NATIVE_REAL_STHEOR_DENIED "<<e.what()<<'\n';
        return 2;
    }
}
