// S4-R1c2. Authentic source-only CALMET COMP MISSFC, six NOAA hours.
// G43 never mutates the P5 SURF, wind or precipitation, nor starts G14.
#include "cteas/p6/p6g_g43_comp_missfc_source.hpp"
#include <chrono>
#include <cmath>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
namespace p6g=cteas::calmet::p6g;

static int original_end_yyyyjjjhh(std::chrono::sys_seconds t) {
    using namespace std::chrono;
    const auto date=floor<days>(t);
    const auto ymd=year_month_day{date};
    const auto y=int(ymd.year());
    const auto days_from_year_start=(date-sys_days{ymd.year()/January/1}).count();
    const auto hour=duration_cast<hours>(t-date).count();
    if(y<1900||y>2100||hour<0||hour>23||days_from_year_start<0)
        throw std::invalid_argument("G43 actual CALMET end hour invalid");
    return y*100000+(static_cast<int>(days_from_year_start)+1)*100+
           static_cast<int>(hour);
}
int main(int argc,char** argv) {
    try {
        if(argc!=6||std::string(argv[1])!="--original-comp-missfc-source-only")
            throw std::invalid_argument(
                "G43 explicit selected source-only mode and four real files required");
        p6g::G19SourceFilePaths paths;
        paths.met_inp=argv[2];paths.geo_dat=argv[3];
        paths.surf_dat=argv[4];paths.ordered_up_dat={argv[5]};
        const auto selection=p6g::g41_load_selected_noow_water_first_hour_source(
            paths,true);
        const auto& source=selection.source;
        if(source.stations.surface.size()!=2||source.stations.upper.size()!=1||
           source.surface.hourly.size()!=6||
           selection.water_heat_source.original_water_cell_indices.size()!=63)
            throw std::invalid_argument(
                "G43 science requires true 2SS 1US 63 WATER source six hours");
        std::cout<<std::setprecision(std::numeric_limits<float>::max_digits10);
        std::cout<<"original_yyyyjjjhh station_id phase ceiling cloud humidity "
                    "precip_code temperature_k pressure_mb wind_speed_mps "
                    "wind_direction_deg\n";
        std::size_t absent_pressure=0,absent_temp=0;
        for(const auto& hour:source.surface.hourly) {
            const auto result=p6g::g43_original_comp_missfc_source_only(
                selection,hour,true);
            if(!result.source_comp_missfc_complete||
               result.G14_G26_production_accepted||
               result.original_otempk_before_replacement.size()!=2)
                throw std::logic_error("G43 original COMP source state invalid");
            absent_pressure+=result.missing_repaired_count[
                static_cast<std::size_t>(p6g::G43MissfcField::Pressure)];
            absent_temp+=result.missing_repaired_count[
                static_cast<std::size_t>(p6g::G43MissfcField::Temperature)];
            const int time=original_end_yyyyjjjhh(hour.end);
            for(std::size_t station=0;station<2;++station) {
                for(int phase=0;phase<2;++phase) {
                    const auto& obs=phase?
                        result.original_comp_resolved.by_station[station]:
                        result.original_raw.by_station[station];
                    std::cout<<time<<' '<<source.stations.surface[station].id<<' '
                             <<phase<<' '<<obs.ceiling_hundreds_ft<<' '
                             <<obs.opaque_cloud_tenths<<' '<<obs.humidity_pct<<' '
                             <<obs.precip_code<<' '<<obs.temperature_k<<' '
                             <<obs.pressure_mb<<' '<<obs.wind_speed_mps<<' '
                             <<obs.wind_direction_deg<<'\n';
                }
            }
        }
        std::cerr<<"S4R1C2_ORIGINAL_SOURCE_PRESSURE_REPAIRS="
                 <<absent_pressure<<" TEMP_REPAIRS="<<absent_temp
                 <<" P5_SPARSE_UNCHANGED=TRUE\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C2_SOURCE_MISSFC_DENIED "<<e.what()<<"\n";
        return 2;
    }
}
