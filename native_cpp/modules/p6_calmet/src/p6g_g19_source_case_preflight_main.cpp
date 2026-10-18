// G19: CLI for validating ACTUAL original CALMET multi-station input files.
// This tool never executes or certifies multi-station CALMET physics.
#include "cteas/p6/p6g_g19_file_backed_case.hpp"
#include <exception>
#include <iostream>
#include <string>
#include <vector>

int main(int argc,char** argv) {
    if(argc==2&&std::string(argv[1])=="--help") {
        std::cout<<"Usage: cteas_p6g_g19_source_case_preflight "
                    "<met.inp> <GEO.DAT> <SURF.DAT> "
                    "<US1_UP.DAT> [US2_UP.DAT ...]\n"
                    "Checks >=1 SS / >=1 US original stations, UTM 9-layer GEO, "
                    "ordered SURF and per-US upper file brackets. "
                    "Does NOT run or validate P6D/P6E/P6F physics.\n";
        return 0;
    }
    if(argc<5) {
        std::cerr<<"G19 requires met.inp GEO.DAT SURF.DAT and "
                    "at least one ordered UP.DAT file; --help for usage\n";
        return 2;
    }
    try {
        cteas::calmet::p6g::G19SourceFilePaths paths;
        paths.met_inp=argv[1];
        paths.geo_dat=argv[2];
        paths.surf_dat=argv[3];
        for(int i=4;i<argc;++i)paths.ordered_up_dat.emplace_back(argv[i]);
        const auto source=
            cteas::calmet::p6g::g19_load_original_source_case(paths);
        const auto scheduler=source.make_scheduler();
        const auto first=scheduler.preview_next_hour();
        std::cout<<"PASS_P6G_G19_FILE_SOURCE_CONTRACT\n"
                 <<"NX="<<source.grid.nx<<" NY="<<source.grid.ny
                 <<" DGRID_KM="<<source.grid.grid_km
                 <<" UTM_ZONE="<<source.grid.zone
                 <<" UTM_HEM="<<source.grid.hemisphere<<"\n"
                 <<"NSSTA="<<source.stations.surface.size()
                 <<" NUSTA="<<source.stations.upper.size()
                 <<" HOURS="<<scheduler.planned_hours()
                 <<" FIRST_END_UTC_SECONDS="
                 <<first.input.end.time_since_epoch().count()
                 <<" LAST_END_UTC_SECONDS="
                 <<source.surface.end.time_since_epoch().count()<<"\n"
                 <<"SS_IDS=";
        for(std::size_t i=0;i<source.stations.surface.size();++i) {
            if(i)std::cout<<",";
            std::cout<<source.stations.surface[i].id;
        }
        std::cout<<"\nUS_IDS=";
        for(std::size_t i=0;i<source.stations.upper.size();++i) {
            if(i)std::cout<<",";
            std::cout<<source.stations.upper[i].id;
        }
        std::cout<<"\nP6D_P6E_MULTISTATION_PRODUCTION=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& error){
        std::cerr<<"FAIL_P6G_G19_SOURCE_INPUT "<<error.what()<<"\n";
        return 1;
    }
}
