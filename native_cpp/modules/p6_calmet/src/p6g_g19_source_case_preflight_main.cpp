// G19 original-file source and time-only versus PHYSICS-ready admission.
// No producer or CALMET field computation occurs in either preflight mode.
#include "cteas/p6/p6g_g19_file_backed_case.hpp"
#include <exception>
#include <iostream>
#include <string>
#include <type_traits>
#include <vector>
namespace p6g=cteas::calmet::p6g;
// It must be impossible to pass a source-only result to G14/G26 production.
static_assert(!std::is_convertible_v<p6g::G19SourceClockCase,
                                     p6g::G19FileBackedCase>);

int main(int argc,char** argv) {
    if(argc==2&&std::string(argv[1])=="--help") {
        std::cout<<"Usage: cteas_p6g_g19_source_case_preflight "
                    "[--source-clock-only] <met.inp> <GEO.DAT> <SURF.DAT> "
                    "<US1_UP.DAT> [US2_UP.DAT ...]\n"
                    "--source-clock-only validates actual source, station order "
                    "and all original UTC brackets; does NOT make a physical "
                    "HEATFX/G14/G26 admission. Default still rejects "
                    "unsupported water HFLUX physics.\n";
        return 0;
    }
    const bool source_only=argc>=2&&
        std::string(argv[1])=="--source-clock-only";
    const int first=source_only?2:1;
    if(argc<first+4) {
        std::cerr<<"G19 requires met.inp GEO.DAT SURF.DAT and "
                    "at least one ordered UP.DAT file; --help for usage\n";
        return 2;
    }
    try {
        p6g::G19SourceFilePaths paths;
        paths.met_inp=argv[first];
        paths.geo_dat=argv[first+1];
        paths.surf_dat=argv[first+2];
        for(int i=first+3;i<argc;++i)paths.ordered_up_dat.emplace_back(argv[i]);
        const auto emit=[source_only](const auto& source) {
            const auto scheduler=source.make_scheduler();
            const auto first_hour=scheduler.preview_next_hour();
            std::cout<<(source_only
                ?"PASS_P6G_G19_SOURCE_AND_CLOCK_ONLY_NO_PHYSICS"
                :"PASS_P6G_G19_FILE_SOURCE_CONTRACT")<<"\n"
                <<"NX="<<source.grid.nx<<" NY="<<source.grid.ny
                <<" DGRID_KM="<<source.grid.grid_km
                <<" UTM_ZONE="<<source.grid.zone
                <<" UTM_HEM="<<source.grid.hemisphere<<"\n"
                <<"NSSTA="<<source.stations.surface.size()
                <<" NUSTA="<<source.stations.upper.size()
                <<" HOURS="<<scheduler.planned_hours()
                <<" FIRST_END_UTC_SECONDS="
                <<first_hour.input.end.time_since_epoch().count()
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
            if(source_only)
                std::cout<<"G19_WATER_HEATFX=NOT_EVALUATED_OR_ACCEPTED\n"
                         <<"G26_PHYSICS_AND_MET_OUTPUT=NOT_RUN\n";
        };
        if(source_only) {
            const auto source=p6g::g19_load_source_clock_only(paths);
            emit(source);
        } else {
            const auto source=p6g::g19_load_original_source_case(paths);
            emit(source);
        }
        return 0;
    }catch(const std::exception& error) {
        std::cerr<<"FAIL_P6G_G19_SOURCE_INPUT "<<error.what()<<"\n";
        return 1;
    }
}
