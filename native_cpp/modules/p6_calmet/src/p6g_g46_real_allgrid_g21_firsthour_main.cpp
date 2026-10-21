// S4-R1c4b: independent full 6970-cell 1h native WIND1/FRADJ/
// two-pass SURFVAR oracle-independent export. Reuses already accepted
// G44 genuine NOAA P5/G43 MISSFC -> G42 -> G21 uncommitted source path.
// Emits no original MET, no previous ZICONV/ZI or G24/G26 production.
#include "cteas/p6/p6g_g44_real_missfc_thermal_first_hour.hpp"
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
           std::string(argv[1])!="--original-noow-full-grid-first-hour-only")
            throw std::invalid_argument(
                "G46 requires explicit original-source only NOAA first hour "
                "met.inp GEO.DAT SURF.DAT UP.DAT; no production mode");
        p6g::G19SourceFilePaths paths;
        paths.met_inp=argv[2];paths.geo_dat=argv[3];
        paths.surf_dat=argv[4];paths.ordered_up_dat={argv[5]};
        const auto data=p6g::g44_native_missfc_thermal_first_hour(paths,true);
        if(!data.p5_raw_unchanged||data.model_hour_committed||
           data.accepted_for_g24_or_g26||
           data.native_heat.g22_g24_wind_ready||
           data.native_heat.g14_g26_production_ready)
            throw std::logic_error("G46 cannot publish fake accepted G14 state");
        // Read independent REAL GEO solely for positions/clock/cell types:
        // scientific values are exclusively G42/G21 native outputs.
        const auto source=p6g::g19_load_source_clock_only(paths);
        const auto nx=static_cast<std::size_t>(source.grid.nx);
        const auto ny=static_cast<std::size_t>(source.grid.ny);
        const auto n=nx*ny;
        if(nx!=82||ny!=85||source.grid.landuse.size()!=n||
           source.surface.hourly.size()!=6||
           data.native_heat.selected_original_water_cells!=63||
           source.stations.surface.size()!=2||
           source.stations.upper.size()!=1)
            throw std::invalid_argument("G46 actual NOAA mixed source mismatch");
        const auto& first=data.native_wind1.native_firstguess;
        const auto& after=data.native_fradj;
        if(first.u_mps.size()!=9*n||first.v_mps.size()!=9*n||
           after.corrected_wind.u.size()!=9*n||
           after.corrected_wind.v.size()!=9*n||
           after.temperature_before_k.size()!=n||
           after.temperature_after_k.size()!=n||
           after.end!=source.surface.hourly.front().end)
            throw std::logic_error("G46 actual native grid/stage clock incomplete");
        const auto epoch=after.end.time_since_epoch().count();
        std::size_t water=0,land=0;
        std::cout<<std::setprecision(std::numeric_limits<float>::max_digits10)
                 <<"i,j,hour_end_utc_seconds,landuse,wind1_u_mps,"
                   "wind1_v_mps,fradj_u_mps,fradj_v_mps,"
                   "pre_temp_k,post_temp_k\n";
        for(std::size_t j=0;j<ny;++j)
            for(std::size_t i=0;i<nx;++i) {
                const auto cell=j*nx+i;
                const auto landuse=source.grid.landuse[cell];
                water+=(landuse>=source.grid.iwat1&&
                        landuse<=source.grid.iwat2);
                land+=(landuse<source.grid.iwat1||
                       landuse>source.grid.iwat2);
                const float fields[]={
                    first.u_mps[cell],first.v_mps[cell],
                    after.corrected_wind.u[cell],
                    after.corrected_wind.v[cell],
                    after.temperature_before_k[cell],
                    after.temperature_after_k[cell]};
                for(float field:fields)
                    if(!std::isfinite(field))
                        throw std::logic_error(
                            "G46 refuses nonfinite native full-grid physics");
                std::cout<<i+1<<','<<j+1<<','<<epoch<<','<<landuse;
                for(float field:fields)std::cout<<','<<field;
                std::cout<<'\n';
            }
        if(water!=63||land!=6907||
           data.native_wind1.g14_g26_production_ready)
            throw std::logic_error("G46 mixed-water scope or G14 guard changed");
        std::cerr<<"S4R1C4B_NATIVE_6970_G42_G21_UNCOMMITTED="
                 <<"PRODUCED_UNVERIFIED WATER="<<water
                 <<" LAND="<<land
                 <<" MISSING_SS="<<data.native_wind1.missing_observed_surface_sites
                 <<" G24_G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C4B_ALLGRID_NATIVE_DENIED "<<e.what()<<'\n';
        return 2;
    }
}
