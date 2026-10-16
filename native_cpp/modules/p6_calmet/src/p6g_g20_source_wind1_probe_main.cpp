// G20: inspect REAL source-file-backed 2SS+2US native WIND1 at the
// first actual G14 model hour. This outputs one reproducible REAL*4
// per-gridcell trace for future independent original Fortran comparison.
// No native FRADJ/P6E/COMP/P6F output, no committed G14 hour, no oracle.
#include "cteas/p6/p6g_g19_file_backed_case.hpp"
#include "cteas/p6/p6g_g20_file_backed_wind1_profiles.hpp"
#include <cmath>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

int main(int argc,char** argv) {
    if(argc==2 && std::string(argv[1])=="--help") {
        std::cout<<"Usage: cteas_p6g_g20_source_wind1_probe "
                    "<met.inp> <GEO.DAT> <SURF.DAT> "
                    "<US1_UP.DAT> <US2_UP.DAT> [US3_UP.DAT ...] "
                    "--output <original-WIND1-candidate.csv> [--wind1-profiles <profiles.dat>]\n"
                    "Output: first-hour native WIND1 U/V for every (k,j,i), "
                    "source-ordered original 2-6 SS/US and actual "
                    "READCF/READGE/SURF/RDUPN files. "
                    "TEST-ONLY native DIAGNO subset: no original Fortran "
                    "whole-hour parity, COMP, P6F or accepted G14 commit.\n";
        return 0;
    }
    try {
        if(argc<8)
            throw std::invalid_argument(
                "G20 needs 2+ ordered UP.DAT files and --output CSV");
        cteas::calmet::p6g::G19SourceFilePaths paths;
        paths.met_inp=argv[1];
        paths.geo_dat=argv[2];
        paths.surf_dat=argv[3];
        std::string output_file,profile_file;
        for(int i=4;i<argc;++i) {
            const std::string arg=argv[i];
            if(arg=="--output"||arg=="--wind1-profiles") {
                if(i+1==argc||std::string(argv[i+1]).empty())
                    throw std::invalid_argument("G20 requires a path after output option");
                auto& destination=arg=="--output"?output_file:profile_file;
                if(!destination.empty())
                    throw std::invalid_argument("G20 duplicate output path option");
                destination=argv[++i];
            } else {
                if(arg.starts_with("--"))
                    throw std::invalid_argument("G20 unknown source argument");
                paths.ordered_up_dat.push_back(arg);
            }
        }
        if(output_file.empty()||paths.ordered_up_dat.size()<2||
           (!profile_file.empty()&&output_file==profile_file))
            throw std::invalid_argument("G20 source UP count/output path invalid");
        const auto source=cteas::calmet::p6g::g19_load_original_source_case(paths);
        auto scheduler=source.make_scheduler();
        auto frame=scheduler.preview_next_hour();
        auto profiles=cteas::calmet::p6g::g20_file_backed_source_wind1_profiles(
            frame,true);
        // The stage observation columns are written only when requested,
        // in READCF source ordinal/level order; never inferred from U/V.
        const auto selected_profiles=profiles;
        cteas::calmet::p6g::G16SelectedWindPhysics native(std::move(profiles));
        const auto stage=native.run(
            cteas::calmet::p6::NativeHourStage::DiagnoWind1,frame);
        if(!stage.completed||
           stage.source!=cteas::calmet::p6::NativeHourSource::NativeCpp||
           scheduler.completed_hours()!=0)
            throw std::runtime_error("G20 native WIND1 was not an uncommitted original hour");
        const auto& wind=native.selected_result().first_guess;
        const auto nx=static_cast<std::size_t>(source.grid.nx);
        const auto ny=static_cast<std::size_t>(source.grid.ny);
        const auto cells=nx*ny;
        if(wind.u_mps.size()!=cells*9||wind.v_mps.size()!=cells*9)
            throw std::runtime_error("G20 original U/V output dimensions invalid");
        // Parse/physics complete first; never leave an output from a
        // partially validated original file-backed WIND1 source hour.
        if(!profile_file.empty()) {
            std::ofstream values(profile_file,std::ios::trunc);
            if(!values)
                throw std::runtime_error("G20 original WIND1 station input output unavailable");
            values<<std::setprecision(std::numeric_limits<float>::max_digits10);
            const auto ns=source.stations.surface.size();
            const auto nu=source.stations.upper.size();
            const auto total=ns+nu;
            values<<source.grid.nx<<" "<<source.grid.ny<<" 9 "
                  <<ns<<" "<<nu<<" "<<source.controls.icalm<<" "
                  <<source.grid.grid_km*1000.f<<"\n";
            for(std::size_t i=0;i<ns;++i) {
                const auto& st=source.stations.surface[i];
                values<<st.local_x_m<<" "<<st.local_y_m<<" "
                      <<frame.surface.by_station[i].wind_speed_mps<<"\n";
            }
            for(const auto& st:source.stations.upper)
                values<<st.local_x_m<<" "<<st.local_y_m<<"\n";
            for(const auto bias:source.controls.bias)values<<bias<<"\n";
            if(selected_profiles.wind1_u_mps.size()!=9*total||
               selected_profiles.wind1_v_mps.size()!=9*total||
               selected_profiles.wind1_present.size()!=9*total)
                throw std::runtime_error("G20 source WIND1 profile dimensions invalid");
            for(std::size_t k=0;k<9;++k)
                for(std::size_t station=0;station<total;++station) {
                    const auto index=k*total+station;
                    if(selected_profiles.wind1_present[index]!=1)
                        throw std::runtime_error(
                            "G20 vendor source-column export requires all winds present");
                    values<<selected_profiles.wind1_u_mps[index]<<" "
                          <<selected_profiles.wind1_v_mps[index]<<" "
                          <<int(selected_profiles.wind1_present[index])<<"\n";
                }
            values.flush();
            if(!values)
                throw std::runtime_error("G20 original station input export failed");
        }
        std::ofstream csv(output_file,std::ios::trunc);
        if(!csv)throw std::runtime_error("G20 WIND1 output file unavailable");
        csv<<"hour_end_utc_seconds,k_1based,j_1based,i_1based,u_mps_real4,v_mps_real4\n";
        csv<<std::setprecision(std::numeric_limits<float>::max_digits10);
        std::size_t rows=0;
        for(std::size_t k=0;k<9;++k)
            for(std::size_t j=0;j<ny;++j)
                for(std::size_t i=0;i<nx;++i) {
                    const auto idx=k*cells+j*nx+i;
                    if(!std::isfinite(wind.u_mps[idx])||
                       !std::isfinite(wind.v_mps[idx]))
                        throw std::runtime_error("G20 non-finite source WIND1 output");
                    csv<<frame.input.end.time_since_epoch().count()<<","
                       <<(k+1)<<","<<(j+1)<<","<<(i+1)<<","
                       <<wind.u_mps[idx]<<","<<wind.v_mps[idx]<<"\n";
                    ++rows;
                }
        csv.flush();
        if(!csv)throw std::runtime_error("G20 WIND1 CSV write failed");
        std::cout<<"PASS_P6G_G20_FIRST_HOUR_FILE_BACKED_NATIVE_WIND1\n"
                 <<"HOUR_END_UTC_SECONDS="
                 <<frame.input.end.time_since_epoch().count()
                 <<" CELLS="<<cells<<" VERTICAL_LAYERS=9"
                 <<" ROWS="<<rows
                 <<" NATIVE_ORIGINAL_FORTRAN_WHOLE_HOUR_PARITY=NOT_ACCEPTED\n"
                 <<"P6D_P6E_COMP_P6F_PRODUCTION=NOT_ACCEPTED\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"FAIL_P6G_G20_SOURCE_WIND1 "<<e.what()<<"\n";
        return 1;
    }
}
