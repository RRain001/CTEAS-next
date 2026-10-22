// S4-R1c8c: prove real mixed-WATER COMP source and fail-closed provenance.
// Absolutely no native WATER/MIXHT/AVEMIX execution or G26 output here.
#include "cteas/p6/p6g_g52_real_water_comp_partition.hpp"
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
namespace p6g=cteas::calmet::p6g;
template<class F>static void deny(F func,const char* msg) {
    bool rejected=false;
    try{func();}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::logic_error(msg);
}
int main(int argc,char** argv) {
    try {
        if(argc!=6||std::string(argv[1])!="--authentic-noaa-water-comp-source-only")
            throw std::invalid_argument(
                "G52 source-only met.inp GEO SURF UP format required");
        const p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto source=p6g::g41_load_selected_noow_water_first_hour_source(
            paths,true);
        auto scheduler=source.source.make_scheduler();
        auto frame=scheduler.preview_next_hour();
        const auto partition=p6g::g26b_real_water_comp_partition_source_only(
            source,frame,true);
        if(partition.original_water_cell_ordinals.size()!=63||
           partition.original_land_cell_ordinals.size()!=6907||
           partition.original_land_cell_ordinals.size()+
             partition.original_water_cell_ordinals.size()!=82U*85U||
           partition.source_water_comp_physics_accepted||
           partition.original_causal_comp_history_accepted||
           partition.g26_45fields_accepted||
           partition.readcf_scalars_only.grid_mixht.imixh!=1)
            throw std::logic_error(
                "G52 exact genuine real-water G26B source preflight rejected");
        deny([&] {
            (void)p6g::g26b_real_water_comp_partition_source_only(
                source,frame,false);
        },"G52 unmarked real-water G26B admission silently accepted");
        auto forged=source;
        forged.water_heat_source.original_water_cell_indices.pop_back();
        deny([&] {
            (void)p6g::g26b_real_water_comp_partition_source_only(
                forged,frame,true);
        },"G52 missing source WATER ordinal silently accepted");
        forged=source;
        forged.water_heat_source.g14_g26_production_ready=true;
        deny([&] {
            (void)p6g::g26b_real_water_comp_partition_source_only(
                forged,frame,true);
        },"G52 forged native WATER COMP production approval");
        forged=source;
        forged.source.surface.station_ids[0]=-123;
        deny([&] {
            (void)p6g::g26b_real_water_comp_partition_source_only(
                forged,frame,true);
        },"G52 changed observed original SS station identity");
        auto reclassified=source;
        const auto water=partition.original_water_cell_ordinals.front();
        reclassified.source.grid.landuse[water]=10;
        deny([&] {
            (void)p6g::g26b_real_water_comp_partition_source_only(
                reclassified,frame,true);
        },"G52 WATER reclassified into LAND source mapping");
        std::cout<<"S4R1C8C_REAL_NOAA_WATER_COMP_SOURCE_PARTITION=PASS "
                    "LAND=6907 WATER=63 SS=2 US=1\n"
                 <<"S4R1C8C_RECLASSIFY_MISSING_ORDINALS_AND_PRODUCTION_FALSE=PASS\n"
                 <<"S4R1C8C_WATER_MIXHT_AVEMIX_G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"S4R1C8C_SOURCE_PARTITION_FAIL_CLOSED "<<e.what()<<"\n";
        return 2;
    }
}
