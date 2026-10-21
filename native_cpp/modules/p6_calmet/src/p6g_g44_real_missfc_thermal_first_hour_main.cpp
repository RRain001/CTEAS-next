// S4-R1c3: REAL NOAA G43 original COMP MISSFC, detached P6 copy,
// then native G42 WIND1 -> G21 FRADJ -> G39 HEATFX/AIRDEN/ELUSTR.
// TEST-ONLY first hour; no G24/WATER/G26/45-field approval.
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
           std::string(argv[1])!="--selected-real-missfc-thermal-only")
            throw std::invalid_argument(
                "G44 explicit real NOAA 2SS1US first-hour MISSFC heat "
                "opt-in and met.inp GEO.DAT SURF.DAT UP.DAT required");
        p6g::G19SourceFilePaths paths;
        paths.met_inp=argv[2];paths.geo_dat=argv[3];
        paths.surf_dat=argv[4];paths.ordered_up_dat={argv[5]};
        const auto a=p6g::g44_native_missfc_thermal_first_hour(paths,true);
        if(!a.p5_raw_unchanged||a.model_hour_committed||
           a.accepted_for_g24_or_g26)
            throw std::logic_error("G44 cannot publish unverified hourly science");
        // Reload only the *immutable* source GEO and clock for coordinates.
        // All calculated physical fields come exclusively from the G44
        // first invocation, never from original MET.DAT or scratch trace.
        const auto raw=p6g::g19_load_source_clock_only(paths);
        const auto nx=static_cast<std::size_t>(raw.grid.nx);
        const auto ny=static_cast<std::size_t>(raw.grid.ny);
        const auto n=nx*ny;
        const auto& heat=a.native_heat.heat;
        const auto& el=a.native_heat.elustr;
        if(heat.end!=raw.surface.hourly.front().end||
           heat.temperature_k.size()!=n||
           heat.shortwave_wm2.size()!=n||
           heat.sensible_heat_wm2.size()!=n||
           heat.density_kg_m3.size()!=n||
           el.qh_wm2.size()!=n||
           el.ustar_mps.size()!=n||
           el.el_m.size()!=n)
            throw std::logic_error("G44 original first-hour output extent changed");
        const auto epoch=heat.end.time_since_epoch().count();
        std::size_t water=0,land=0;
        std::cout<<std::setprecision(std::numeric_limits<float>::max_digits10)
                 <<"i,j,hour_end_utc_seconds,landuse,temp2d_k,qsw_wm2,"
                   "qh_before_elustr_wm2,qh_after_elustr_wm2,rho_kg_m3,"
                   "ustar_mps,el_m\n";
        for(std::size_t j=0;j<ny;++j)for(std::size_t i=0;i<nx;++i) {
            const auto k=j*nx+i;
            if(!std::isfinite(heat.temperature_k[k])||
               !std::isfinite(heat.shortwave_wm2[k])||
               !std::isfinite(heat.sensible_heat_wm2[k])||
               !std::isfinite(heat.density_kg_m3[k])||
               heat.density_kg_m3[k]<=0.f||
               !std::isfinite(el.qh_wm2[k])||
               !std::isfinite(el.ustar_mps[k])||
               !std::isfinite(el.el_m[k]))
                throw std::logic_error("G44 nonfinite genuine native thermal field");
            const bool is_water=raw.grid.landuse[k]>=raw.grid.iwat1&&
                                raw.grid.landuse[k]<=raw.grid.iwat2;
            if(is_water) {
                ++water;
                if(heat.sensible_heat_wm2[k]!=0.f||
                   el.qh_wm2[k]!=0.f||
                   el.ustar_mps[k]!=0.f||
                   el.el_m[k]!=0.f)
                    throw std::logic_error(
                        "G44 original WATER cannot synthesize USTAR/EL/ZI before WATER");
            }else{++land;}
            std::cout<<i+1<<','<<j+1<<','<<epoch<<','
                     <<raw.grid.landuse[k]<<','
                     <<heat.temperature_k[k]<<','
                     <<heat.shortwave_wm2[k]<<','
                     <<heat.sensible_heat_wm2[k]<<','
                     <<el.qh_wm2[k]<<','
                     <<heat.density_kg_m3[k]<<','
                     <<el.ustar_mps[k]<<','
                     <<el.el_m[k]<<'\n';
        }
        if(water!=63||water+land!=6970)
            throw std::logic_error("G44 actual NOAA 63 water/6907 land grid changed");
        std::cerr<<"S4R1C3_REAL_NOAA_G43_MISSFC_G39_NATIVE_FIRST_HOUR_PRODUCED_UNVERIFIED "
                 <<"WATER="<<water<<" LAND="<<land<<" P5_RAW_UNCHANGED=TRUE "
                 <<"G24_G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C3_G44_REAL_MISSFC_THERMAL_DENIED "<<e.what()<<"\n";
        return 2;
    }
}
