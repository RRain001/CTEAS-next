// S4-R1c1: first real NOAA water hour, G20 WIND1 -> G21 FRADJ ->
// 2 original SURFVAR passes -> G39 HEATFX/ELUSTR (water pending).
// Strictly source-only: do not emit or commit G14/P6F/COMP, nor use any
// original Fortran MET.DAT or instrumental oracle as an input.
#include "cteas/p6/p6g_g41_real_water_first_hour_source.hpp"
#include "cteas/p6/p6g_g42_selected_real_water_missing_wind1.hpp"
#include "cteas/p6/p6g_g21_file_backed_fradj.hpp"
#include "cteas/p6/p6g_g39_selected_water_thermal_reference.hpp"
#include "cteas/p6/p6g_g18d2_station_clock_transaction.hpp"
#include <cmath>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace p6g=cteas::calmet::p6g;
namespace p6=cteas::calmet::p6;
int main(int argc,char** argv) {
    try {
        if(argc!=6||
           std::string(argv[1])!="--selected-noow-water-first-hour")
            throw std::invalid_argument(
                "G41 requires explicit first-hour source-only opt-in plus "
                "met.inp GEO.DAT SURF.DAT US1_UP.DAT; no default production");
        const p6g::G19SourceFilePaths paths={
            argv[2],argv[3],argv[4],{argv[5]}};
        auto water=p6g::g41_load_selected_noow_water_first_hour_source(
            paths,true);
        auto& source=water.source;
        if(source.stations.upper.size()!=1 ||
           source.stations.surface.size()!=2)
            throw std::invalid_argument(
                "G41 first authentic NOAA first-hour study requires actual 2SS+1US");
        auto scheduler=source.make_scheduler();
        auto frame=scheduler.preview_next_hour();
        p6g::G18D2StationClockAuthority clocks;
        const auto prepared=clocks.prepare_selected(
            scheduler,source.original_metinp,true);
        // A genuinely missing station in the original source is NOT a
        // made-up zero-wind measurement. G42 preserves source present=0
        // and delegates REAL*4 BIAS/ICALM/1/r² weights to frozen G9.
        const auto native=p6g::g42_selected_real_water_missing_wind1(
            frame,water,true);
        if(native.g14_g26_production_ready)
            throw std::logic_error("G42 promoted unaccepted WATER source");
        const auto& wind1=native.native_firstguess;
        std::cerr<<"S4R1C1_SOURCE_NOAA_MISSING_SURFACE_COUNT="
                 <<native.missing_observed_surface_sites
                 <<" CALM_COUNT="<<native.calm_observed_surface_sites<<"\n";
        const auto fradj=p6g::g41_real_water_first_hour_native_fradj(
            frame,water,prepared.cgamma,wind1,true);
        const auto n=static_cast<std::size_t>(source.grid.nx)*
                     static_cast<std::size_t>(source.grid.ny);
        if(fradj.temperature_before_k.size()!=n||
           fradj.temperature_after_k.size()!=n||
           fradj.corrected_wind.u.size()!=n*9||
           fradj.corrected_wind.v.size()!=n*9)
            throw std::logic_error("G41 selected G21 water fields incomplete");
        p6g::G17B4TwoPassSurfvar twice(
            source.grid,source.stations,source.surface,frame.surface,
            water.surface_controls,true);
        twice.after_wind1_before_fradj(
            frame.input.end,wind1.u_mps,wind1.v_mps);
        twice.after_fradj_before_heatfx(
            frame.input.end,fradj.corrected_wind.u,
            fradj.corrected_wind.v);
        if(twice.first_temperature()!=fradj.temperature_before_k||
           twice.final_temperature()!=fradj.temperature_after_k)
            throw std::logic_error(
                "G41 G39 second SURFVAR detached from actual native G21 FRADJ");
        const float zm=0.5f*(
            source.controls.zface_m[0]+source.controls.zface_m[1]);
        const auto thermal=p6g::g39_original_noow_water_postfradj_thermal_reference(
            source.grid,source.stations,frame.surface,twice,
            fradj.corrected_wind,source.original_metinp,zm,true);
        if(thermal.selected_original_water_cells!=
           water.water_heat_source.original_water_cell_indices.size()||
           thermal.water_ustar_el_zi_ready||thermal.g22_g24_wind_ready||
           thermal.g14_g26_production_ready||
           scheduler.completed_hours()!=0||clocks.has_published_hour())
            throw std::logic_error("G41 physically unaccepted hour was published");
        const auto epoch=frame.input.end.time_since_epoch().count();
        std::cout<<std::setprecision(std::numeric_limits<float>::max_digits10);
        std::cout<<"i,j,hour_end_utc_seconds,landuse,pre_temp_k,post_temp_k,"
                    "sinalpc,qsw_wm2,qh_water_wm2,wind1_u_mps,wind1_v_mps,"
                    "fradj_u_mps,fradj_v_mps\n";
        for(const auto k:water.water_heat_source.original_water_cell_indices) {
            if(thermal.heat.sensible_heat_wm2[k]!=0.f||
               thermal.elustr.qh_wm2[k]!=0.f||
               !std::isfinite(thermal.heat.shortwave_wm2[k])||
               !std::isfinite(fradj.temperature_after_k[k]))
                throw std::logic_error(
                    "G41 selected source original WATER placeholder invalid");
            std::cout<<k%static_cast<std::size_t>(source.grid.nx)+1<<','
                     <<k/static_cast<std::size_t>(source.grid.nx)+1<<','
                     <<epoch<<','<<source.grid.landuse[k]<<','
                     <<fradj.temperature_before_k[k]<<','
                     <<fradj.temperature_after_k[k]<<','
                     <<thermal.heat.sun_sine[k]<<','
                     <<thermal.heat.shortwave_wm2[k]<<','
                     <<thermal.elustr.qh_wm2[k]<<','
                     <<wind1.u_mps[k]<<','<<wind1.v_mps[k]<<','
                     <<fradj.corrected_wind.u[k]<<','
                     <<fradj.corrected_wind.v[k]<<'\n';
        }
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C1_SELECTED_WATER_FIRST_HOUR_DENIED "
                 <<e.what()<<"\n";
        return 2;
    }
}
