// G21: source-file-driven first-hour PREPDI/CGAMMA/WIND1/SURFVAR/FRADJ
// stage data for independent ORIGINAL Fortran TERSET+FRADJ numeric parity.
// This is a scoped scientific diagnostic, never a production 17-stage hour.
#include "cteas/p6/p6g_g19_file_backed_case.hpp"
#include "cteas/p6/p6g_g20_file_backed_wind1_profiles.hpp"
#include "cteas/p6/p6g_g21_file_backed_fradj.hpp"
#include "cteas/p6/p6g_g22_file_backed_thermal_slope.hpp"
#include "cteas/p6/p6g_g23_file_backed_stheor_inter2.hpp"
#include "cteas/p6/p6g_g24_file_backed_wind_tail.hpp"
#include "cteas/p6/p6g_g18d2_station_clock_transaction.hpp"
#include "cteas/p6/p6g_g18b3_upper_choice.hpp"
#include "cteas/p6/p6g_g26b_file_backed_comp_bridge.hpp"
#include "cteas/p6/p6g_g18d1_p6f_precommit.hpp"
#include <cmath>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

int main(int argc,char** argv) {
    if(argc==2&&std::string(argv[1])=="--help") {
        std::cout<<"Usage: cteas_p6g_g21_source_fradj_probe "
                    "<met.inp> <GEO.DAT> <SURF.DAT> <US1_UP.DAT> "
                    "[US2_UP.DAT ...] "
                    "--output <fradj-native.csv> --source-stage <fradj-input.dat> "
                    "[--real-one-ss-one-us-fradj-test-only] "
                    "[--real-one-ss-one-us-slope-test-only]\n"
                    "Source-only 1h native PREPDI CGAMMA GAMMA, original "
                    "SURFVAR(TEMP2D), TERSET and FRADJ. TEST ONLY; "
                    "45-field CALMET/COMP/P6F NOT ACCEPTED.\n";
        return 0;
    }
    try {
        cteas::calmet::p6g::G19SourceFilePaths paths;
        if(argc<8)throw std::invalid_argument("G21 requires real original source file set");
        paths.met_inp=argv[1];
        paths.geo_dat=argv[2];
        paths.surf_dat=argv[3];
        std::string output_file,stage_file,slope_output_file,slope_stage_file;
        std::string inter2_output_file,inter2_original_stage_prefix;
        std::string diagi_similt_prefix,wind_tail_stage,wind_tail_output,wind_tail_boundaries;
        std::string station_flux_prefix,original_nearu_prefix,comp_original_prefix;
        std::string mixht_original_prefix,temp3d_original_prefix;
        std::string p6f_candidate_file,surfvar_two_pass_output,comp_third_surfvar_output;
        bool real_one_one_fradj_test_only=false;
        bool real_one_one_slope_test_only=false;
        for(int i=4;i<argc;++i) {
            const std::string arg=argv[i];
            if(arg=="--real-one-ss-one-us-slope-test-only") {
                if(real_one_one_slope_test_only)
                    throw std::invalid_argument("G22 duplicated real 1SS1US slope opt-in");
                real_one_one_slope_test_only=true;
            } else if(arg=="--real-one-ss-one-us-fradj-test-only") {
                if(real_one_one_fradj_test_only)
                    throw std::invalid_argument("G21 duplicate real 1SS1US diagnostic opt-in");
                real_one_one_fradj_test_only=true;
            } else if(arg=="--output"||arg=="--source-stage"||
               arg=="--slope-output"||arg=="--slope-stage"||
               arg=="--inter2-output"||arg=="--inter2-original-stage-prefix"||
               arg=="--diagi-similt-prefix"||arg=="--wind-tail-stage"||
               arg=="--wind-tail-output"||arg=="--wind-tail-boundaries"||
               arg=="--station-flux-prefix"||arg=="--nearu-prefix"||
               arg=="--comp-original-prefix"||arg=="--mixht-original-prefix"||
               arg=="--temp3d-original-prefix"||arg=="--p6f-candidate-file"||
               arg=="--surfvar-two-pass-output"||
               arg=="--comp-third-surfvar-output") {
                if(i+1>=argc||std::string(argv[i+1]).empty())
                    throw std::invalid_argument("G21/G22 source output missing path");
                auto& selected=arg=="--output"?output_file:
                               arg=="--source-stage"?stage_file:
                               arg=="--slope-output"?slope_output_file:
                               arg=="--slope-stage"?slope_stage_file:
                               arg=="--inter2-output"?inter2_output_file:
                               arg=="--inter2-original-stage-prefix"?inter2_original_stage_prefix:
                               arg=="--diagi-similt-prefix"?diagi_similt_prefix:
                               arg=="--wind-tail-stage"?wind_tail_stage:
                               arg=="--wind-tail-output"?wind_tail_output:
                               arg=="--wind-tail-boundaries"?wind_tail_boundaries:
                               arg=="--station-flux-prefix"?station_flux_prefix:
                               arg=="--nearu-prefix"?original_nearu_prefix:arg=="--comp-original-prefix"?comp_original_prefix:
                               arg=="--mixht-original-prefix"?mixht_original_prefix:
                               arg=="--temp3d-original-prefix"?temp3d_original_prefix:
                               arg=="--surfvar-two-pass-output"?surfvar_two_pass_output:
                               arg=="--comp-third-surfvar-output"?comp_third_surfvar_output:
                               p6f_candidate_file;
                if(!selected.empty())
                    throw std::invalid_argument("G21/G22 duplicate output argument");
                selected=argv[++i];
            } else {
                if(arg.starts_with("--"))throw std::invalid_argument("G21 unknown source option");
                paths.ordered_up_dat.push_back(arg);
            }
        }
        if(output_file.empty()||stage_file.empty()||
           stage_file==output_file||paths.ordered_up_dat.empty()||
           (paths.ordered_up_dat.size()<2&&!real_one_one_fradj_test_only)||
           slope_output_file.empty()!=slope_stage_file.empty()||
           (!inter2_output_file.empty()&&slope_output_file.empty())||
           (!inter2_original_stage_prefix.empty()&&inter2_output_file.empty())||
           (!diagi_similt_prefix.empty()&&inter2_output_file.empty())||
           (!station_flux_prefix.empty()&&inter2_output_file.empty())||
           (!mixht_original_prefix.empty()&&comp_original_prefix.empty())||
           (!temp3d_original_prefix.empty()&&comp_original_prefix.empty())||
           (!p6f_candidate_file.empty()&&comp_original_prefix.empty())||
           (!comp_third_surfvar_output.empty()&&wind_tail_stage.empty())||
           ((!wind_tail_stage.empty()||!wind_tail_output.empty()||
             !wind_tail_boundaries.empty())&&
            (wind_tail_stage.empty()||wind_tail_output.empty()||
             wind_tail_boundaries.empty()||inter2_output_file.empty())))
            throw std::invalid_argument("G21/G22 requires independent stage/output file pairs");
        const std::vector<std::string> outputs={
            output_file,stage_file,slope_output_file,slope_stage_file,
            inter2_output_file,
            inter2_original_stage_prefix.empty()?std::string{}:inter2_original_stage_prefix+".u.input",
            inter2_original_stage_prefix.empty()?std::string{}:inter2_original_stage_prefix+".v.input",
            diagi_similt_prefix.empty()?std::string{}:diagi_similt_prefix+".s1.input",
            diagi_similt_prefix.empty()?std::string{}:diagi_similt_prefix+".s2.input",
            diagi_similt_prefix.empty()?std::string{}:diagi_similt_prefix+".native.csv",
            wind_tail_stage,wind_tail_output,wind_tail_boundaries,
            station_flux_prefix.empty()?std::string{}:station_flux_prefix+".s1.input",
            station_flux_prefix.empty()?std::string{}:station_flux_prefix+".s2.input",
            station_flux_prefix.empty()?std::string{}:station_flux_prefix+".native.csv",
            station_flux_prefix.empty()?std::string{}:station_flux_prefix+".mixht.s1.input",
            station_flux_prefix.empty()?std::string{}:station_flux_prefix+".mixht.s2.input",
            station_flux_prefix.empty()?std::string{}:station_flux_prefix+".mixht.native.csv",
            station_flux_prefix.empty()?std::string{}:station_flux_prefix+".mixht.day.s1.input",
            station_flux_prefix.empty()?std::string{}:station_flux_prefix+".mixht.day.s2.input",
            original_nearu_prefix.empty()?std::string{}:original_nearu_prefix+".source.input",
            original_nearu_prefix.empty()?std::string{}:original_nearu_prefix+".native.csv",
            comp_original_prefix.empty()?std::string{}:comp_original_prefix+".source.input",
            comp_original_prefix.empty()?std::string{}:comp_original_prefix+".native.csv",
            mixht_original_prefix.empty()?std::string{}:mixht_original_prefix+".source.input",
            mixht_original_prefix.empty()?std::string{}:mixht_original_prefix+".native.csv",
            temp3d_original_prefix.empty()?std::string{}:temp3d_original_prefix+".source.input",
            temp3d_original_prefix.empty()?std::string{}:temp3d_original_prefix+".native.csv",
            p6f_candidate_file,surfvar_two_pass_output,comp_third_surfvar_output};
        for(std::size_t i=0;i<outputs.size();++i)
            if(!outputs[i].empty())
                for(std::size_t j=0;j<i;++j)
                    if(outputs[i]==outputs[j])
                        throw std::invalid_argument("G21/G22 output filename collision");
        const auto source=cteas::calmet::p6g::g19_load_original_source_case(paths);
        if(real_one_one_slope_test_only&&!real_one_one_fradj_test_only)
            throw std::invalid_argument("G22 separate slope opt-in also requires G21 single-source opt-in");
        const bool real_one_one=(source.stations.surface.size()==1&&
                                 source.stations.upper.size()==1);
        if(real_one_one_slope_test_only&&!real_one_one)
            throw std::invalid_argument("G22 selected single-source flag invalid on multistation");
        if(real_one_one!=real_one_one_fradj_test_only)
            throw std::invalid_argument(
                "G21 1SS1US source FRADJ requires explicit test-only flag; "
                "old multisite source may not opt into single-site mode");
        if(real_one_one && (
           (real_one_one_slope_test_only &&
             (slope_output_file.empty()||slope_stage_file.empty()))||
           (!real_one_one_slope_test_only && !slope_output_file.empty())||
           !inter2_output_file.empty()||
            !diagi_similt_prefix.empty()||!wind_tail_stage.empty()||
            !comp_original_prefix.empty()||!p6f_candidate_file.empty()||
            !station_flux_prefix.empty()||!original_nearu_prefix.empty())))

            throw std::invalid_argument(
                "G21 1SS1US G22 requires separate opt-in and only "
                "uncommitted selected SLOPE, no G23/G24/COMP");
        auto scheduler=source.make_scheduler();
        auto frame=scheduler.preview_next_hour();
        cteas::calmet::p6g::G18D2StationClockAuthority clocks;
        const auto prepared=clocks.prepare_selected(
            scheduler,source.original_metinp,true);
        const auto source_profiles=
            cteas::calmet::p6g::g20_file_backed_source_wind1_profiles(frame,true);
        cteas::calmet::p6g::G16SelectedWindPhysics wind(source_profiles);
        const auto result=wind.run(
            cteas::calmet::p6::NativeHourStage::DiagnoWind1,frame);
        if(!result.completed||
           result.source!=cteas::calmet::p6::NativeHourSource::NativeCpp)
            throw std::logic_error("G21 native source WIND1 unavailable");
        const auto& first=wind.selected_result().first_guess;
        const auto selected=cteas::calmet::p6g::g21_selected_original_file_fradj(
            frame,source,prepared.cgamma,first,true);
        if(scheduler.completed_hours()!=0||clocks.has_published_hour()||
           selected.end!=frame.input.end)
            throw std::logic_error("G21 incorrectly published incomplete source hour");
        const auto nx=static_cast<std::size_t>(source.grid.nx);
        const auto ny=static_cast<std::size_t>(source.grid.ny);
        const auto cells=nx*ny;
        if(first.u_mps.size()!=cells*9||
           selected.corrected_wind.u.size()!=cells*9||
           selected.gamma_k_per_m.size()!=cells||
           selected.temperature_before_k.size()!=cells)
            throw std::logic_error("G21 stage source geometry mismatch");

        if(!surfvar_two_pass_output.empty()) {
            // G33A forensic-only PRE/POST FRADJ source temperatures.  These
            // are native G17B4 calculations, never original-vendor oracle
            // inputs, and may not commit a G14 hour or populate P6F output.
            if(selected.temperature_after_k.size()!=cells||
               selected.temperature_before_k.size()!=cells||
               scheduler.completed_hours()!=0||clocks.has_published_hour())
                throw std::logic_error(
                    "G33A two-pass SURFVAR not in one uncommitted G14 hour");
            std::ofstream native(surfvar_two_pass_output,std::ios::trunc);
            if(!native)
                throw std::runtime_error("G33A cannot export native two-pass SURFVAR");
            native<<"hour_end_utc_seconds,i,j,pre_fradj_temp_k,post_fradj_temp_k\n";
            native<<std::setprecision(std::numeric_limits<float>::max_digits10);
            for(std::size_t j=0;j<ny;++j)
                for(std::size_t i=0;i<nx;++i) {
                    const auto p=j*nx+i;
                    const auto before=selected.temperature_before_k[p];
                    const auto after=selected.temperature_after_k[p];
                    if(!std::isfinite(before)||!std::isfinite(after))
                        throw std::logic_error("G33A nonfinite native two-pass temperature");
                    native<<frame.input.end.time_since_epoch().count()<<","
                          <<i+1<<","<<j+1<<","<<before<<","<<after<<"\n";
                }
            native.flush();
            if(!native)throw std::runtime_error(
                "G33A native two-pass SURFVAR export incomplete");
        }
        if(!original_nearu_prefix.empty()) {
            // G27 independently invokes literal original SETCOM.
            // Feed genuine G19 UTM-local REAL*4 grid and upper stations,
            // never the C++ nearest ordinal as reference data.
            const auto selected_upper=
                cteas::calmet::p6g::g18b3_source_deck_upper_choice(
                    frame.grid,frame.stations,source.original_metinp);
            if(source.stations.upper.size()!=2||
               selected_upper.iupt!=-1||
               selected_upper.nearu.size()!=cells)
                throw std::invalid_argument(
                    "G27 original 2US SETCOM/IUPT=-1 branch unavailable");
            std::ofstream inp(original_nearu_prefix+".source.input",std::ios::trunc);
            if(!inp)throw std::runtime_error("G27 SETCOM source input unavailable");
            inp<<std::setprecision(std::numeric_limits<float>::max_digits10);
            inp<<nx<<" "<<ny<<" 9 "<<source.stations.upper.size()<<" "
               <<source.grid.grid_km*1000.f<<"\n";
            for(float z:source.controls.zface_m) inp<<z<<" ";
            inp<<"\n";
            for(const auto& us:source.stations.upper)
                inp<<us.id<<" "<<us.local_x_m<<" "<<us.local_y_m<<"\n";
            inp.flush();
            if(!inp)throw std::runtime_error("G27 original SETCOM stage incomplete");
            std::ofstream native(original_nearu_prefix+".native.csv",
                                 std::ios::trunc);
            if(!native)throw std::runtime_error("G27 C++ station choice unavailable");
            native<<"i,j,upper_ordinal,upper_station_id\n";
            for(std::size_t j=0;j<ny;++j)
                for(std::size_t i=0;i<nx;++i) {
                    const int u=selected_upper.nearu[j*nx+i];
                    if(u<1||static_cast<std::size_t>(u)>source.stations.upper.size())
                        throw std::logic_error("G27 C++ source NEARU ordinal invalid");
                    native<<i+1<<","<<j+1<<","<<u<<","
                          <<source.stations.upper[static_cast<std::size_t>(u-1)].id
                          <<"\n";
                }
            native.flush();
            if(!native)throw std::runtime_error("G27 native SETCOM output incomplete");
            std::cout<<"PASS_P6G_G27_ORIGINAL_SETCOM_SOURCE_INPUT "
                     <<"SITES="<<source.stations.upper.size()
                     <<" CELLS="<<cells
                     <<" ORIGINAL_VENDOR_PARITY=NOT_YET_CALCULATED\n";
        }
        if(!comp_original_prefix.empty()) {
            // G28 AVEMIX/WSTARR independent ORIGINAL Fortran source gate.
            // Use a single G14 frame for all original 16 physics stages.
            // The pre-AVEMIX grid heights below are generated by native
            // MIXHT, NOT copied from the C++ final (averaged) reference.
            cteas::calmet::p6g::G26SourceFileBackedG14DiagnoBridge g26(
                scheduler,clocks,source);
            for(std::size_t step=0;step<12;++step)
                g26.run_selected(
                    cteas::calmet::p6::kHefeiOriginalStageOrder[step],frame,true);
            cteas::calmet::p6g::G26BSourceFileBackedCompBridge g26b(g26,source);
            for(std::size_t step=12;step<16;++step)
                g26b.run_selected(
                    cteas::calmet::p6::kHefeiOriginalStageOrder[step],frame,true);
            const auto& mixed=g26b.source_mixht_before_avemix(frame);
            const auto& ave=g26b.source_avemix_after_mixht(frame);
            const auto& candidate=g26b.selected_p6f_candidate(frame);
            const auto& thermal=g26.selected_thermal_for_comp(frame);
            const auto control=cteas::calmet::p6g::g18c1_parse_original_avemix(
                source.original_metinp);
            const std::size_t offset=static_cast<std::size_t>(control.ilevzi-1)*cells;
            if(g26b.source_comp_ready()==false||
               mixed.candidate_next.zi_m.size()!=cells||
               mixed.candidate_next.ziconv_m.size()!=cells||
               ave.zi_m.size()!=cells||ave.ziconv_m.size()!=cells||
               candidate.candidate_fields.wstar_mps.size()!=cells||
               candidate.candidate_fields.u_mps.size()!=9*cells||
               thermal.heat.temperature_k.size()!=cells||
               thermal.heat.density_kg_m3.size()!=cells||
               thermal.elustr.qh_wm2.size()!=cells||
               scheduler.completed_hours()!=0||clocks.has_published_hour())
                throw std::logic_error(
                    "G28 original COMP MIXHT/AVEMIX/WSTARR source provenance invalid");
            std::ofstream inp(comp_original_prefix+".source.input",
                              std::ios::trunc);
            if(!inp)
                throw std::runtime_error("G28 original source COMP input not writable");
            inp<<std::setprecision(std::numeric_limits<float>::max_digits10);
            inp<<nx<<" "<<ny<<" "<<control.mnmdav<<" "<<control.hafang_deg<<" "
               <<source.grid.grid_km*1000.f<<" "
               <<source.grid.iwat1<<" "<<source.grid.iwat2<<" "
               <<control.ilevzi<<"\n";
            for(std::size_t j=0;j<ny;++j)
                for(std::size_t i=0;i<nx;++i) {
                    const auto p=j*nx+i;
                    inp<<candidate.candidate_fields.u_mps[offset+p]<<" "
                       <<candidate.candidate_fields.v_mps[offset+p]<<" "
                       <<mixed.candidate_next.zi_m[p]<<" "
                       <<mixed.candidate_next.ziconv_m[p]<<" "
                       <<thermal.elustr.qh_wm2[p]<<" "
                       <<thermal.heat.temperature_k[p]<<" "
                       <<thermal.heat.density_kg_m3[p]<<" "
                       <<source.grid.landuse[p]<<"\n";
                }
            inp.flush();
            if(!inp)
                throw std::runtime_error("G28 original source COMP stage truncated");
            std::ofstream native(comp_original_prefix+".native.csv",
                                 std::ios::trunc);
            if(!native)
                throw std::runtime_error("G28 source candidate results missing");
            native<<"i,j,zi_after_avemix_m,ziconv_after_avemix_m,wstar_mps\n";
            native<<std::setprecision(std::numeric_limits<float>::max_digits10);
            for(std::size_t j=0;j<ny;++j)
                for(std::size_t i=0;i<nx;++i) {
                    const auto p=j*nx+i;
                    native<<i+1<<","<<j+1<<","<<ave.zi_m[p]<<","
                          <<ave.ziconv_m[p]<<","
                          <<candidate.candidate_fields.wstar_mps[p]<<"\n";
                }
            native.flush();
            if(!native)
                throw std::runtime_error("G28 native original COMP candidates truncated");
            if(!mixht_original_prefix.empty()) {
                // G29A: capture the TRUE call input, not an inverse from
                // post-MIXHT output. No Fortran result enters native physics.
                const auto& m=mixed.source_mixht_input;
                const auto& z=mixed.candidate_next;
                const auto nlev=m.sounding.at(0).at(0).height_m.size();
                if(nlev<2||nlev>10||m.nx!=nx||m.ny!=ny||
                   m.sounding[0].size()!=2||m.sounding[1].size()!=2||
                   m.justa.size()!=2||m.nearu.size()!=cells||
                   m.initial_zi.size()!=cells||m.initial_ziconv.size()!=cells||
                   m.initial_dptt.size()!=cells||m.qh.size()!=cells||
                   m.ustar.size()!=cells||m.el.size()!=cells||
                   m.rho.size()!=cells||m.cmech.size()!=cells||
                   m.fcori.size()!=cells||m.landuse.size()!=cells||
                   z.zi_m.size()!=cells||z.ziconv_m.size()!=cells||
                   z.dptt_k.size()!=cells||m.iupt!=-1||
                   m.timestep_s!=3600)
                    throw std::logic_error("G29A MIXHT source input mismatch");
                for(const auto& buff:m.sounding)
                    for(const auto& station:buff)
                        if(station.height_m.size()!=nlev||
                           station.temp_k.size()!=nlev)
                            throw std::logic_error("G29A MIXHT varying sounding shape");
                std::ofstream out(mixht_original_prefix+".source.input",
                                  std::ios::trunc);
                if(!out)throw std::runtime_error("G29A original MIXHT source cannot open");
                out<<std::setprecision(std::numeric_limits<float>::max_digits10);
                out<<"1 "<<nx<<" "<<ny<<" 2 "<<nlev<<"\n";
                out<<m.iupt<<" "<<m.constn<<" "<<m.zimin<<" "<<m.zimax
                   <<" "<<m.threshl<<" "<<m.dptmin<<" "<<m.dzzi
                   <<" "<<m.onedte<<" "<<m.twodte<<" "<<m.izicrlx
                   <<" "<<m.tzicrlx<<" "<<m.timestep_s<<" "<<m.imixh<<"\n";
                for(int k:m.justa)out<<k<<"\n";
                for(const auto& buff:m.sounding)
                    for(const auto& site:buff)
                        for(std::size_t k=0;k<nlev;++k)
                            out<<site.height_m[k]<<" "<<site.temp_k[k]<<"\n";
                // Original Fortran driver loops I outside J.
                for(std::size_t i=0;i<nx;++i)
                    for(std::size_t j=0;j<ny;++j) {
                        const auto p=j*nx+i;
                        out<<m.qh[p]<<" "<<m.ustar[p]<<" "<<m.el[p]<<" "
                           <<m.rho[p]<<" "<<m.cmech[p]<<" "<<m.fcori[p]<<" "
                           <<m.landuse[p]<<" "<<m.nearu[p]<<" "
                           <<m.initial_zi[p]<<" "<<m.initial_ziconv[p]<<" "
                           <<m.initial_dptt[p]<<"\n";
                    }
                out.flush();
                if(!out)throw std::runtime_error("G29A MIXHT input write failed");
                std::ofstream native(mixht_original_prefix+".native.csv",
                                     std::ios::trunc);
                if(!native)throw std::runtime_error("G29A MIXHT candidate cannot open");
                native<<"i,j,zi_m,ziconv_m,dptt_k\n";
                native<<std::setprecision(std::numeric_limits<float>::max_digits10);
                for(std::size_t i=0;i<nx;++i)
                    for(std::size_t j=0;j<ny;++j) {
                        const auto p=j*nx+i;
                        native<<i+1<<","<<j+1<<","<<z.zi_m[p]<<","
                              <<z.ziconv_m[p]<<","<<z.dptt_k[p]<<"\n";
                    }
                native.flush();
                if(!native)throw std::runtime_error("G29A MIXHT output write failed");
                if(scheduler.completed_hours()!=0||clocks.has_published_hour())
                    throw std::logic_error("G29A incorrectly committed G14");
                std::cout<<"PASS_P6G_G29A_SOURCE_MIXHT_INPUT CELLS="
                         <<cells<<" G14_HOURS_COMMITTED=0"
                         <<" ORIGINAL_VENDOR_PARITY=NOT_YET_CALCULATED\n";
            }
            if(!temp3d_original_prefix.empty()) {
                // G29B: use EXACT native TEMP3D call inputs from same G14
                // hour AFTER AVEMIX, never reverse-engineer reference from T.
                const auto& temperature=g26b.source_temp3d_input_and_result(frame);
                const auto& t=temperature.source_temp3d_input;
                const auto nlevels=static_cast<std::size_t>(9);
                if(t.nx!=nx||t.ny!=ny||t.nz!=nlevels||
                   t.justa.size()!=2||t.irad<1||t.irad>2||
                   t.face_z_m.size()!=nlevels+1||
                   t.station_x_m.size()!=2||t.station_y_m.size()!=2||
                   t.aa_face_temp_k.size()!=2*(nlevels+1)||
                   t.bb_face_temp_k.size()!=2*(nlevels+1)||
                   t.surface_temp_k.size()!=cells||
                   t.convective_zi_m.size()!=cells||
                   t.past_seconds.size()!=2||t.to_go_seconds.size()!=2||
                   temperature.temperature_k.size()!=cells*nlevels||
                   candidate.candidate_fields.temperature_k!=temperature.temperature_k)
                    throw std::logic_error("G29B source TEMP3D dimensions not genuine");
                // This unchanged-original Fortran test driver uses one
                // same-day 00/12 UTC bracket. Reject a shifted/non-12h
                // sounding rather than fabricating equivalent timestamps.
                for(std::size_t st=0;st<2;++st)
                    if(t.past_seconds[st]!=t.current_hour_utc*3600||
                       t.to_go_seconds[st]!=(12-t.current_hour_utc)*3600)
                        throw std::logic_error(
                            "G29B source TEMP3D non-00/12 bracket not yet certified");
                std::ofstream inp(temp3d_original_prefix+".source.input",
                                  std::ios::trunc);
                if(!inp)throw std::runtime_error("G29B TEMP3D original source unavailable");
                inp<<std::setprecision(std::numeric_limits<float>::max_digits10);
                inp<<"1 "<<nx<<" "<<ny<<" "<<nlevels<<" 2\n";
                inp<<t.irad<<" "<<t.current_hour_utc<<" "<<t.dgrid_m<<"\n";
                for(float z:t.face_z_m)inp<<z<<"\n";
                for(std::size_t st=0;st<2;++st)
                    inp<<t.justa[st]<<" "<<t.station_x_m[st]<<" "
                       <<t.station_y_m[st]<<"\n";
                for(std::size_t st=0;st<2;++st)
                    for(std::size_t k=0;k<=nlevels;++k) {
                        const auto p=st*(nlevels+1)+k;
                        inp<<t.aa_face_temp_k[p]<<" "<<t.bb_face_temp_k[p]<<"\n";
                    }
                for(std::size_t i=0;i<nx;++i)
                    for(std::size_t j=0;j<ny;++j) {
                        const auto p=j*nx+i;
                        inp<<t.surface_temp_k[p]<<" "
                           <<t.convective_zi_m[p]<<"\n";
                    }
                inp.flush();
                if(!inp)throw std::runtime_error("G29B TEMP3D original source truncated");
                std::ofstream native(temp3d_original_prefix+".native.csv",
                                     std::ios::trunc);
                if(!native)throw std::runtime_error("G29B TEMP3D C++ source unavailable");
                native<<"i,j,k,temp_k\n";
                native<<std::setprecision(std::numeric_limits<float>::max_digits10);
                for(std::size_t i=0;i<nx;++i)
                    for(std::size_t j=0;j<ny;++j)
                        for(std::size_t k=0;k<nlevels;++k) {
                            const auto p=k*cells+j*nx+i;
                            native<<i+1<<","<<j+1<<","<<k+1<<","
                                  <<temperature.temperature_k[p]<<"\n";
                        }
                native.flush();
                if(!native)throw std::runtime_error("G29B TEMP3D source truncated");
                if(scheduler.completed_hours()!=0||clocks.has_published_hour())
                    throw std::logic_error("G29B incorrectly committed G14");
                std::cout<<"PASS_P6G_G29B_SOURCE_TEMP3D_INPUT "
                         <<"CELLS="<<cells<<" LEVELS="<<nlevels
                         <<" G14_HOURS_COMMITTED=0"
                         <<" ORIGINAL_VENDOR_PARITY=NOT_YET_CALCULATED\n";
            }
            if(!p6f_candidate_file.empty()) {
                // G30A: candidate bytes ONLY after the actual same-frame
                // source G26A/G26B 16 selected physics slots have completed.
                // The original G14 CommitOutput [16] is NOT advanced and
                // no prior COMP/upper-station clock may be published here.
                const auto& c=g26b.selected_p6f_candidate(frame);
                // G33D: original COMP SURFVAR runs THIRD on FINAL U/V
                // then HEATFX/AIRDEN/ELUSTR; DIAGNO G22 density is stale.
                // G32F demonstrated original COMP RHO/TEMP2D bit exact;
                // use precisely that actual same-frame G26B source heat
                // for original P6F TEMPK/RHO/QSW output records.
                const auto& comp_heat=g26b.source_comp_heat_for_p6f(frame);
                if(comp_heat.end!=frame.input.end||
                   comp_heat.density_kg_m3.size()!=cells||
                   comp_heat.temperature_k.size()!=cells||
                   comp_heat.shortwave_wm2.size()!=cells)
                    throw std::logic_error(
                        "G33D source P6F COMP heat has no completed original hour");
                const auto nears=cteas::calmet::p6g::source_setcom_nears(
                    frame.grid,frame.stations);
                const auto records=cteas::calmet::p6g::g18c5_selected_p6f_fields(
                    frame,comp_heat,c,source.original_metinp,true);
                if(records.real.at("RHO     ")!=comp_heat.density_kg_m3||
                   records.real.at("TEMPK   ")!=comp_heat.temperature_k||
                   records.real.at("QSW     ")!=comp_heat.shortwave_wm2)
                    throw std::logic_error(
                        "G33D P6F output backfilled stale DIAGNO instead of COMP");
                const auto dataset=cteas::calmet::p6g::g18c6_selected_one_hour_dataset(
                    frame,records,nears,source.original_metinp,true);
                const auto bytes=cteas::calmet::p6g::g18d1_validate_p6f_precommit(
                    frame,dataset);
                if(bytes.empty()||dataset.hourly.size()!=45||
                   dataset.header.nx!=frame.grid.nx||
                   dataset.header.ny!=frame.grid.ny||
                   dataset.header.nz!=9||
                   scheduler.completed_hours()!=0||clocks.has_published_hour())
                    throw std::logic_error("G30A native P6F candidate/clock gate failed");
                std::ofstream binary(p6f_candidate_file,
                                     std::ios::binary|std::ios::trunc);
                if(!binary)throw std::runtime_error("G30A P6F audit output cannot open");
                binary.write(reinterpret_cast<const char*>(bytes.data()),
                             static_cast<std::streamsize>(bytes.size()));
                binary.flush();
                if(!binary)throw std::runtime_error("G30A P6F candidate bytes truncated");
                if(scheduler.completed_hours()!=0||clocks.has_published_hour()||
                   frame.previous.zi_m!=scheduler.committed_memory().zi_m||
                   frame.previous.ziconv_m!=scheduler.committed_memory().ziconv_m||
                   frame.previous.dptt_k!=scheduler.committed_memory().dptt_k)
                    throw std::logic_error("G30A P6F audit altered authoritative G14");
                std::cout<<"PASS_P6G_G30A_P6F_PREPARED_ONLY FIELDS=45 BYTES="
                         <<bytes.size()<<" G14_HOURS_COMMITTED=0"
                         <<" ORIGINAL_VENDOR_45FIELD_PARITY=NOT_YET_CALCULATED\n";
            }
            std::cout<<"PASS_P6G_G28_SOURCE_ORIGINAL_AVEMIX_WSTARR_INPUT "
                     <<"CELLS="<<cells<<" CANDIDATE_COLUMNS=3 "
                     <<"G14_HOURS_COMMITTED=0 ORIGINAL_VENDOR_PARITY=NOT_YET_CALCULATED\n";
        }
        std::ofstream stage(stage_file,std::ios::trunc);
        if(!stage)throw std::runtime_error("G21 cannot write original FRADJ stage input");
        stage<<std::setprecision(std::numeric_limits<float>::max_digits10);
        stage<<nx<<" "<<ny<<" 9 "<<source.grid.grid_km*1000.f<<" "
             <<source.grid.grid_km*1000.f<<" "<<selected.source_terrad_km<<" "
             <<selected.source_critfn<<" "<<selected.temperature_before_k[0]
             <<" -1\n";
        for(const auto z:source.controls.zface_m)stage<<z<<" ";
        stage<<"\n";
        for(std::size_t j=0;j<ny;++j)
            for(std::size_t i=0;i<nx;++i) {
                const auto p=j*nx+i;
                stage<<source.grid.terrain_m[p]<<" "
                     <<selected.gamma_k_per_m[p]<<" "
                     <<selected.temperature_before_k[p]<<"\n";
            }
        for(std::size_t k=0;k<9;++k)
            for(std::size_t j=0;j<ny;++j)
                for(std::size_t i=0;i<nx;++i) {
                    const auto p=k*cells+j*nx+i;
                    stage<<first.u_mps[p]<<" "<<first.v_mps[p]<<"\n";
                }
        stage.flush();
        if(!stage)throw std::runtime_error("G21 source FRADJ input write failed");

        std::ofstream csv(output_file,std::ios::trunc);
        if(!csv)throw std::runtime_error("G21 cannot write native FRADJ CSV");
        csv<<"hour_end_utc_seconds,k_1based,j_1based,i_1based,u_mps_real4,v_mps_real4\n";
        csv<<std::setprecision(std::numeric_limits<float>::max_digits10);
        for(std::size_t k=0;k<9;++k)
            for(std::size_t j=0;j<ny;++j)
                for(std::size_t i=0;i<nx;++i) {
                    const auto p=k*cells+j*nx+i;
                    if(!std::isfinite(selected.corrected_wind.u[p])||
                       !std::isfinite(selected.corrected_wind.v[p]))
                        throw std::runtime_error("G21 source FRADJ U/V nonfinite");
                    csv<<frame.input.end.time_since_epoch().count()<<","
                       <<(k+1)<<","<<(j+1)<<","<<(i+1)<<","
                       <<selected.corrected_wind.u[p]<<","
                       <<selected.corrected_wind.v[p]<<"\n";
                }
        csv.flush();
        if(!csv)throw std::runtime_error("G21 native FRADJ output write failed");
        if(!slope_output_file.empty()) {
            const auto joined=cteas::calmet::p6g::g22_selected_source_thermal_slope(
                frame,source,{first.u_mps,first.v_mps},selected,true);
            if(scheduler.completed_hours()!=0||clocks.has_published_hour())
                throw std::logic_error("G22 incomplete source hour was committed");
            std::ofstream stage22(slope_stage_file,std::ios::trunc);
            if(!stage22)throw std::runtime_error("G22 cannot export original SLOPE input");
            stage22<<std::setprecision(std::numeric_limits<float>::max_digits10);
            stage22<<nx<<" "<<ny<<" 9 "<<source.grid.grid_km*1000.f<<" "
                   <<source.grid.grid_km*1000.f<<" "
                   <<selected.source_terrad_km<<" "<<joined.heat.temperature_k[0]
                   <<" "<<source.grid.iwat1<<" "<<source.grid.iwat2<<" -1\n";
            for(const auto z:source.controls.zface_m)stage22<<z<<" ";
            stage22<<"\n";
            for(std::size_t j=0;j<ny;++j)
                for(std::size_t i=0;i<nx;++i) {
                    const auto p=j*nx+i;
                    stage22<<source.grid.terrain_m[p]<<" "
                           <<joined.heat.temperature_k[p]<<" "
                           <<joined.elustr.qh_wm2[p]<<" "
                           <<source.grid.landuse[p]<<"\n";
                }
            for(std::size_t k=0;k<9;++k)
                for(std::size_t j=0;j<ny;++j)
                    for(std::size_t i=0;i<nx;++i) {
                        const auto p=k*cells+j*nx+i;
                        stage22<<selected.corrected_wind.u[p]<<" "
                               <<selected.corrected_wind.v[p]<<"\n";
                    }
            stage22.flush();
            if(!stage22)throw std::runtime_error("G22 SLOPE input export failed");
            std::ofstream csv22(slope_output_file,std::ios::trunc);
            if(!csv22)throw std::runtime_error("G22 cannot export native slope winds");
            csv22<<"hour_end_utc_seconds,k_1based,j_1based,i_1based,"
                    "u_mps_real4,v_mps_real4\n";
            csv22<<std::setprecision(std::numeric_limits<float>::max_digits10);
            for(std::size_t k=0;k<9;++k)
                for(std::size_t j=0;j<ny;++j)
                    for(std::size_t i=0;i<nx;++i) {
                        const auto p=k*cells+j*nx+i;
                        csv22<<frame.input.end.time_since_epoch().count()<<","
                             <<(k+1)<<","<<(j+1)<<","<<(i+1)<<","
                             <<joined.post_slope_wind.u[p]<<","
                             <<joined.post_slope_wind.v[p]<<"\n";
                    }
            csv22.flush();
            if(!csv22)throw std::runtime_error("G22 native SLOPE CSV failed");
            if(!inter2_output_file.empty()) {
                const auto station=cteas::calmet::p6g::g23_source_stheor_diagi_inter2(
                    frame,source,source_profiles,selected,joined,true);
                if(scheduler.completed_hours()!=0||clocks.has_published_hour())
                    throw std::logic_error("G23 incomplete G14 hour was published");
                std::ofstream i2(inter2_output_file,std::ios::trunc);
                if(!i2)throw std::runtime_error("G23 source INTER2 output unavailable");
                i2<<"hour_end_utc_seconds,k_1based,j_1based,i_1based,"
                     "u_mps_real4,v_mps_real4\n";
                i2<<std::setprecision(std::numeric_limits<float>::max_digits10);
                if(station.inter2_u.component_mps.size()!=cells*9||
                   station.inter2_v.component_mps.size()!=cells*9)
                    throw std::logic_error("G23 source INTER2 dimensions invalid");
                for(std::size_t k=0;k<9;++k)
                    for(std::size_t j=0;j<ny;++j)
                        for(std::size_t i=0;i<nx;++i) {
                            const auto p=k*cells+j*nx+i;
                            const auto u=station.inter2_u.component_mps[p];
                            const auto v=station.inter2_v.component_mps[p];
                            if(!std::isfinite(u)||!std::isfinite(v))
                                throw std::runtime_error("G23 source INTER2 nonfinite U/V");
                            i2<<frame.input.end.time_since_epoch().count()<<","
                              <<(k+1)<<","<<(j+1)<<","<<(i+1)<<","
                              <<u<<","<<v<<"\n";
                        }
                i2.flush();
                if(!i2)throw std::runtime_error("G23 source INTER2 CSV write failed");
                if(!inter2_original_stage_prefix.empty()) {
                    // Feed untouched original CALMET INTER2 its EXACT
                    // source-file selected DIAGI(SS)/PREPDI(US), post-SLOPE
                    // first-guess grid and original READCF radii.  This
                    // captures intermediate *inputs*, NOT reference results.
                    const auto& c=source.controls;
                    const auto ns=source.stations.surface.size();
                    const auto nu=source.stations.upper.size();
                    const auto nst=ns+nu;
                    const auto& profiles=station.observed_after_diagi;
                    if(profiles.inter2_u_mps.size()!=9*nst||
                       profiles.inter2_v_mps.size()!=9*nst||
                       profiles.inter2_present.size()!=9*nst||
                       c.iprog!=0||nst!=4u)
                        throw std::logic_error("G23 original INTER2 reference input not sourced");
                    for(const auto& [tag,observations,firstguess]:
                        {std::tuple<const char*,const std::vector<float>*,
                                    const std::vector<float>*>{
                            "u",&profiles.inter2_u_mps,&joined.post_slope_wind.u},
                         std::tuple<const char*,const std::vector<float>*,
                                    const std::vector<float>*>{
                            "v",&profiles.inter2_v_mps,&joined.post_slope_wind.v}}) {
                        std::ofstream original(inter2_original_stage_prefix+
                                              "."+tag+".input",std::ios::trunc);
                        if(!original)
                            throw std::runtime_error("G23 original INTER2 input not writable");
                        original<<std::setprecision(std::numeric_limits<float>::max_digits10);
                        original<<nst<<" "<<static_cast<int>(c.lvary)<<" "
                                <<c.rmin_km<<" "<<c.rmax1_km<<" "
                                <<c.rmax2_km<<" "<<c.rmax3_km<<" "
                                <<c.r1_km<<" "<<c.r2_km<<" 999999 999998\n";
                        for(std::size_t k=0;k<9;++k)
                            original<<std::min(c.nintr2[k],static_cast<int>(nst))<<" ";
                        original<<"\n";
                        for(const auto& st:source.stations.surface)
                            original<<st.local_x_m*0.001f<<" ";
                        for(const auto& st:source.stations.upper)
                            original<<st.local_x_m*0.001f<<" ";
                        original<<"\n";
                        for(const auto& st:source.stations.surface)
                            original<<st.local_y_m*0.001f<<" ";
                        for(const auto& st:source.stations.upper)
                            original<<st.local_y_m*0.001f<<" ";
                        original<<"\n";
                        for(std::size_t j=0;j<ny;++j) {
                            for(std::size_t i=0;i<nx;++i)
                                original<<source.grid.landuse[j*nx+i]<<" ";
                            original<<"\n";
                        }
                        for(std::size_t k=0;k<9;++k) {
                            for(std::size_t l=0;l<nst;++l) {
                                const auto p=k*nst+l;
                                original<<(profiles.inter2_present[p]?
                                    (*observations)[p]:999999.f)<<" ";
                            }
                            original<<"\n";
                        }
                        for(std::size_t k=0;k<9;++k)
                            for(std::size_t j=0;j<ny;++j) {
                                for(std::size_t i=0;i<nx;++i)
                                    original<<(*firstguess)[k*cells+j*nx+i]<<" ";
                                original<<"\n";
                            }
                        // Same READCF IPROG=0 and original RDWT WO=1
                        // physically consumed by frozen G16::do_inter2.
                        for(std::size_t k=0;k<9;++k)
                            for(std::size_t j=0;j<ny;++j) {
                                for(std::size_t i=0;i<nx;++i)original<<"1 ";
                                original<<"\n";
                            }
                        original.flush();
                        if(!original)
                            throw std::runtime_error("G23 source original INTER2 file not complete");
                    }
                    std::cout<<"PASS_P6G_G23_ORIGINAL_INTER2_INPUT_STAGES "
                             <<"STATIONS="<<nst<<" LAYERS=9 "
                             <<"WIND_UV_VALUES="<<cells*9*2
                             <<" REFERENCE_CALCULATION=NOT_YET_PERFORMED\n";
                }
                if(!station_flux_prefix.empty()) {
                    if(cteas::calmet::p6g::g18d5_source_integer(
                           source.original_metinp,"ICLOUD")>1||
                       cteas::calmet::p6g::g18d5_source_integer(
                           source.original_metinp,"IUPT")!=-1)
                        throw std::invalid_argument(
                            "G25 original ELUSTR2 NWS-cloud/IUPT source scope missing");
                    const auto& h=source.heat_inputs.coefficients;
                    std::ofstream values(station_flux_prefix+".native.csv",
                                         std::ios::trunc);
                    if(!values)
                        throw std::runtime_error("G25 original-source ELUSTR2 CSV inaccessible");
                    values<<"surface_ordinal,surface_id,upper_id,shortwave_wm2,"
                              "sensible_wm2,friction_velocity_mps,monin_obukhov_m\n";
                    values<<std::setprecision(
                        std::numeric_limits<float>::max_digits10);
                    for(std::size_t ss=0;ss<station.station_diagi.size();++ss) {
                        const auto& st=station.station_diagi[ss];
                        const auto& site=source.stations.surface[ss];
                        const auto& obs=frame.surface.by_station[ss];
                        if(st.surface_id!=site.id||st.end!=frame.input.end||
                           !st.station_flux.extrapolate)
                            throw std::logic_error("G25 station source ELUSTR2 identity invalid");
                        const float rad=0.0174533f*obs.wind_direction_deg;
                        const float uu=-obs.wind_speed_mps*std::sin(rad);
                        const float vv=-obs.wind_speed_mps*std::cos(rad);
                        const auto cell=st.cell;
                        if(cell>=cells)
                            throw std::logic_error("G25 station GEO index invalid");
                        const float t=joined.heat.temperature_k[cell];
                        const float rho=0.3484321f*obs.pressure_mb/t;
                        std::ofstream input(station_flux_prefix+".s"+
                                            std::to_string(ss+1)+".input",
                                            std::ios::trunc);
                        if(!input)
                            throw std::runtime_error("G25 original station flux file inaccessible");
                        input<<std::setprecision(
                            std::numeric_limits<float>::max_digits10);
                        input<<uu<<" "<<vv<<" "
                             <<0.5f*(source.controls.zface_m[0]+
                                      source.controls.zface_m[1])<<" "
                             <<site.anemometer_height_m<<" "
                             <<source.grid.z0_m[cell]<<" "
                             <<joined.heat.sun_sine[cell]<<" "
                             <<t<<" "<<rho<<" "
                             <<obs.opaque_cloud_tenths<<" "
                             <<h.ha1<<" "<<h.ha2<<" "<<h.hb1<<" "<<h.hb2<<" "
                             <<h.hc1<<" "<<h.hc2<<" "<<h.hc3p1<<" "
                             <<source.grid.albedo[cell]<<" "
                             <<source.grid.bowen[cell]<<" "
                             <<source.grid.hcg[cell]<<" "
                             <<source.grid.qf[cell]<<"\n";
                        input.flush();
                        if(!input)throw std::runtime_error("G25 original ELUSTR2 input incomplete");
                        values<<(ss+1)<<","<<st.surface_id<<","<<st.upper_id<<","
                              <<st.station_flux.shortwave_wm2<<","
                              <<st.station_flux.sensible_wm2<<","
                              <<st.station_flux.friction_velocity_mps<<","
                              <<st.station_flux.monin_obukhov_m<<"\n";
                    }
                    values.flush();
                    if(!values)
                        throw std::runtime_error("G25 original ELUSTR2 candidate output incomplete");
                    // G25B: expose the *previous COMP* station-cell state
                    // and source-read controls for literal original stable
                    // MIXHTST, never synthesized prior station outputs.
                    std::ofstream mix_values(station_flux_prefix+".mixht.native.csv",
                                             std::ios::trunc);
                    if(!mix_values)
                        throw std::runtime_error("G25B native station mixing output unavailable");
                    mix_values<<"surface_ordinal,surface_id,upper_id,zi_m,"
                                  "ziconv_m,dptt_k\n";
                    mix_values<<std::setprecision(
                        std::numeric_limits<float>::max_digits10);
                    const auto mix_controls=
                        cteas::calmet::p6g::g23_stheor_original_readcf_controls(
                            source,true);
                    for(std::size_t ss=0;ss<station.station_diagi.size();++ss) {
                        const auto& st=station.station_diagi[ss];
                        const auto c=st.cell;
                        std::ofstream orig(station_flux_prefix+".mixht.s"+
                                           std::to_string(ss+1)+".input",
                                           std::ios::trunc);
                        if(!orig)
                            throw std::runtime_error("G25B original station mixing source not writable");
                        orig<<std::setprecision(std::numeric_limits<float>::max_digits10);
                        orig<<st.station_flux.sensible_wm2<<" "
                            <<st.station_flux.friction_velocity_mps<<" "
                            <<st.station_flux.monin_obukhov_m<<" "
                            <<0.3484321f*frame.surface.by_station[ss].pressure_mb/
                               joined.heat.temperature_k[c]<<" "
                            <<frame.previous.zi_m[c]<<" "
                            <<frame.previous.ziconv_m[c]<<" "
                            <<frame.previous.dptt_k[c]<<" "
                            <<mix_controls.fcori_s<<" "
                            <<mix_controls.cmech<<" "
                            <<mix_controls.zimin_m<<" "
                            <<mix_controls.zimax_m<<" "
                            <<mix_controls.constn<<" "
                            <<source.grid.landuse[c]<<" "
                            <<source.grid.iwat1<<" "<<source.grid.iwat2<<" "
                            <<mix_controls.imixh<<"\n";
                        orig.flush();
                        if(!orig)
                            throw std::runtime_error("G25B original station mixing input incomplete");
                        mix_values<<(ss+1)<<","<<st.surface_id<<","
                                  <<st.upper_id<<","
                                  <<st.station_mixing.zii_to_similt_m<<","
                                  <<st.station_mixing.ziconv_after_m<<","
                                  <<st.station_mixing.dptt_for_comp_k<<"\n";
                    }
                    // Source 00/12 UTC UP buffer owned by G14 G19, not
                    // an invented vertical sounding.  Export the actual
                    // older sounding used by original selected MIXHTST.
                    for(std::size_t ss=0;ss<station.station_diagi.size();++ss) {
                        const auto& st=station.station_diagi[ss];
                        const auto cell=st.cell;
                        const auto upid=source.stheor_upper_ordinal_for_surface[ss];
                        if(upid>=frame.upper.size())
                            throw std::logic_error("G25C source selected upper site missing");
                        const cteas::calmet::p6::UpperSounding* older=nullptr;
                        for(const auto& sounding:frame.upper[upid].soundings) {
                            if(sounding.end<=frame.surface.start)older=&sounding;
                            else break;
                        }
                        if(!older||older->data.size()<2||older->data.size()>100)
                            throw std::logic_error("G25C physical older UP thermal sounding incomplete");
                        std::ofstream day(station_flux_prefix+".mixht.day.s"+
                                          std::to_string(ss+1)+".input",
                                          std::ios::trunc);
                        if(!day)
                            throw std::runtime_error("G25C original UP/surface stage file unavailable");
                        day<<std::setprecision(std::numeric_limits<float>::max_digits10);
                        const auto mc=cteas::calmet::p6g::g23_stheor_original_readcf_controls(
                            source,true);
                        day<<st.station_flux.sensible_wm2<<" "
                           <<st.station_flux.friction_velocity_mps<<" "
                           <<st.station_flux.monin_obukhov_m<<" "
                           <<0.3484321f*frame.surface.by_station[ss].pressure_mb/
                              joined.heat.temperature_k[cell]<<" "
                           <<frame.previous.zi_m[cell]<<" "
                           <<frame.previous.ziconv_m[cell]<<" "
                           <<frame.previous.dptt_k[cell]<<" "
                           <<mc.fcori_s<<" "<<mc.cmech<<" "<<mc.zimin_m<<" "
                           <<mc.zimax_m<<" "<<mc.constn<<" "
                           <<source.grid.landuse[cell]<<" "
                           <<source.grid.iwat1<<" "<<source.grid.iwat2<<" "
                           <<mc.imixh<<" "<<mc.dptmin_kperm<<" "<<mc.dzzi_m<<" "
                           <<mc.threshl<<" "<<mc.onedte_s<<" "<<mc.twodte_s<<" "
                           <<mc.tzicrlx_s<<" "<<mc.izicrlx<<"\n";
                        day<<older->data.size()<<"\n";
                        for(const auto& level:older->data)
                            day<<level.height_lgl_m<<" "
                               <<(level.temperature_valid?level.temperature_k:9999.f)
                               <<"\n";
                        day.flush();
                        if(!day)
                            throw std::runtime_error("G25C original UP station source data incomplete");
                    }
                    mix_values.flush();
                    if(!mix_values)
                        throw std::runtime_error("G25B station MIXHTST source output incomplete");
                    std::cout<<"PASS_P6G_G25_STATION_ELUSTR2_ORIGINAL_SOURCE_INPUT "
                             <<"STATIONS="<<station.station_diagi.size()
                             <<" ORIGINAL_VENDOR_PARITY=NOT_YET_CALCULATED "
                               "G14_HOURS_COMMITTED=0\n";
                }
                if(!diagi_similt_prefix.empty()) {
                    // Same actual STHEOR/MIXHTST physical station controls
                    // passed into frozen original_similt_profile. The
                    // independent source will rerun literal vendor SIMILT,
                    // not any C++-reconstructed U/V or synthetic profiles.
                    const auto projection=
                        cteas::p6e::utm_north_projection(source.grid.zone);
                    std::ofstream diagi_csv(diagi_similt_prefix+".native.csv",
                                            std::ios::trunc);
                    if(!diagi_csv)
                        throw std::runtime_error("G23 native DIAGI CSV not writable");
                    diagi_csv<<"surface_ordinal,surface_id,upper_id,"
                                "levels_filled,k_1based,u_mps_real4,v_mps_real4\n";
                    diagi_csv<<std::setprecision(
                        std::numeric_limits<float>::max_digits10);
                    if(station.station_diagi.size()!=source.stations.surface.size())
                        throw std::logic_error("G23 DIAGI original site count incorrect");
                    for(std::size_t ss=0;ss<station.station_diagi.size();++ss) {
                        const auto& output=station.station_diagi[ss];
                        const auto& site=source.stations.surface[ss];
                        const auto& obs=frame.surface.by_station[ss];
                        double latitude=0.,longitude=0.;
                        cteas::p6e::utm_north_to_latlon_deg(
                            projection,static_cast<double>(site.utm_x_km)*1000.,
                            static_cast<double>(site.utm_y_km)*1000.,
                            latitude,longitude);
                        if(!std::isfinite(latitude)||latitude<=0.||
                           output.surface_id!=site.id)
                            throw std::logic_error("G23 DIAGI station source UTM invalid");
                        const float radians=0.0174533f*obs.wind_direction_deg;
                        const float u=-obs.wind_speed_mps*std::sin(radians);
                        const float v=-obs.wind_speed_mps*std::cos(radians);
                        std::ofstream input(diagi_similt_prefix+".s"+
                                            std::to_string(ss+1)+".input",
                                            std::ios::trunc);
                        if(!input)
                            throw std::runtime_error("G23 original SIMILT station input not writable");
                        input<<std::setprecision(std::numeric_limits<float>::max_digits10);
                        input<<static_cast<float>(latitude)<<" "
                             <<site.anemometer_height_m<<" "
                             <<source.grid.z0_m[output.cell]<<" "
                             <<u<<" "<<v<<" "
                             <<output.station_flux.monin_obukhov_m<<" "
                             <<output.station_mixing.zii_to_similt_m<<" "
                             <<cteas::calmet::p6g::g18d5_source_scalar(
                                source.original_metinp,"ZIMIN")
                             <<" -4 0\n";
                        for(const float z:source.controls.zface_m)input<<z<<" ";
                        input<<"\n";
                        input.flush();
                        if(!input)
                            throw std::runtime_error("G23 source SIMILT station input write failure");
                        for(std::size_t k=0;k<9;++k) {
                            diagi_csv<<(ss+1)<<","<<output.surface_id<<","
                                     <<output.upper_id<<","
                                     <<output.levels_filled<<","<<(k+1)<<","
                                     <<output.diagi_profile.u_mps[k]<<","
                                     <<output.diagi_profile.v_mps[k]<<"\n";
                        }
                    }
                    diagi_csv.flush();
                    if(!diagi_csv)
                        throw std::runtime_error("G23 native DIAGI station CSV write failure");
                    std::cout<<"PASS_P6G_G23_LITERAL_SIMILT_STATION_INPUT "
                             <<"STATIONS="<<station.station_diagi.size()
                             <<" ORIGINAL_SOURCE_REFERENCE=NOT_YET_EXECUTED\n";
                }
                if(!wind_tail_stage.empty()) {
                    const auto g24=cteas::calmet::p6g::g24_selected_original_wind_tail(
                        frame,source,station,true);
                    if(scheduler.completed_hours()!=0||clocks.has_published_hour())
                        throw std::logic_error("G24 selected source wind leaked into G14");
                    if(!comp_third_surfvar_output.empty()) {
                        // G33B: genuine G19 source hour, original COMP runs
                        // SURFVAR for the THIRD time with the DIAGNO-final
                        // wind (U,V), unlike G22's second FRADJ-adjusted UG/VG.
                        // Do not backfill oracle TEMP2D into COMP or P6F.
                        cteas::calmet::p6g::G17B4TwoPassSurfvar three_pass(
                            source.grid,frame.stations,source.surface,
                            frame.surface,source.surface_controls);
                        three_pass.after_wind1_before_fradj(
                            frame.input.end,first.u_mps,first.v_mps);
                        three_pass.after_fradj_before_heatfx(
                            frame.input.end,selected.corrected_wind.u,
                            selected.corrected_wind.v);
                        if(three_pass.first_temperature()!=
                             selected.temperature_before_k||
                           three_pass.final_temperature()!=
                             selected.temperature_after_k)
                            throw std::logic_error(
                                "G33B duplicate DIAGNO temperature mismatch");
                        const auto comp_temp=
                            three_pass.diagnostic_comp_final_wind_temperature(
                                frame.input.end,g24.wind.u_mps,
                                g24.wind.v_mps,true);
                        if(comp_temp.size()!=cells||
                           scheduler.completed_hours()!=0||
                           clocks.has_published_hour())
                            throw std::logic_error(
                                "G33B COMP third SURFVAR leaked G14 state");
                        std::ofstream third(comp_third_surfvar_output,
                                            std::ios::trunc);
                        if(!third)throw std::runtime_error(
                            "G33B third SURFVAR diagnostic CSV unavailable");
                        third<<"hour_end_utc_seconds,i,j,temp_k\n";
                        third<<std::setprecision(
                            std::numeric_limits<float>::max_digits10);
                        for(std::size_t j=0;j<ny;++j)
                            for(std::size_t i=0;i<nx;++i) {
                                const auto p=j*nx+i;
                                if(!std::isfinite(comp_temp[p]))
                                    throw std::logic_error(
                                        "G33B third SURFVAR nonfinite");
                                third<<frame.input.end.time_since_epoch().count()
                                     <<","<<i+1<<","<<j+1<<","
                                     <<comp_temp[p]<<"\n";
                            }
                        third.flush();
                        if(!third)throw std::runtime_error(
                            "G33B third SURFVAR native export incomplete");
                    }
                    std::ofstream stage24(wind_tail_stage,std::ios::trunc);
                    if(!stage24)
                        throw std::runtime_error("G24 original DIAGNO stage not writable");
                    stage24<<std::setprecision(std::numeric_limits<float>::max_digits10);
                    for(std::size_t k=0;k<9;++k)
                        stage24<<(source.controls.zface_m[k+1]-
                                  source.controls.zface_m[k])<<" ";
                    stage24<<"\n";
                    for(const int passes:source.controls.nsmth)
                        stage24<<passes<<" ";
                    stage24<<"\n";
                    for(const auto* field:{
                        &station.inter2_u.component_mps,&station.inter2_v.component_mps}) {
                        for(std::size_t k=0;k<9;++k)
                            for(std::size_t j=0;j<ny;++j) {
                                for(std::size_t i=0;i<nx;++i)
                                    stage24<<(*field)[k*cells+j*nx+i]<<" ";
                                stage24<<"\n";
                            }
                    }
                    for(std::size_t k=0;k<9;++k)
                        for(std::size_t side=0;side<2;++side) {
                            for(std::size_t j=0;j<ny;++j)
                                stage24<<g24.second_ub_west_east_mps[
                                    k*2*ny+side*ny+j]<<" ";
                            stage24<<"\n";
                        }
                    for(std::size_t k=0;k<9;++k)
                        for(std::size_t side=0;side<2;++side) {
                            for(std::size_t i=0;i<nx;++i)
                                stage24<<g24.second_vb_south_north_mps[
                                    k*2*nx+side*nx+i]<<" ";
                            stage24<<"\n";
                        }
                    stage24.flush();
                    if(!stage24)
                        throw std::runtime_error("G24 original DIAGNO stage file incomplete");
                    std::ofstream output24(wind_tail_output,std::ios::trunc);
                    if(!output24)
                        throw std::runtime_error("G24 native full U/V/DIV/W not writable");
                    output24<<"i,j,k,u,v,div,w_below,w_above\n";
                    output24<<std::setprecision(std::numeric_limits<float>::max_digits10);
                    for(std::size_t k=0;k<9;++k)
                        for(std::size_t j=0;j<ny;++j)
                            for(std::size_t i=0;i<nx;++i) {
                                const auto p=k*cells+j*nx+i;
                                output24<<(i+1)<<","<<(j+1)<<","<<(k+1)<<","
                                        <<g24.wind.u_mps[p]<<","
                                        <<g24.wind.v_mps[p]<<","
                                        <<g24.wind.divergence_per_s[p]<<","
                                        <<g24.wind.w_face_mps[p]<<","
                                        <<g24.wind.w_face_mps[p+cells]<<"\n";
                            }
                    output24.flush();
                    if(!output24)
                        throw std::runtime_error("G24 native wind tail output incomplete");
                    std::ofstream boundary24(wind_tail_boundaries,std::ios::trunc);
                    if(!boundary24)
                        throw std::runtime_error("G24 native boundary file not writable");
                    boundary24<<std::setprecision(std::numeric_limits<float>::max_digits10);
                    for(std::size_t k=0;k<9;++k)
                        for(std::size_t side=0;side<2;++side) {
                            for(std::size_t j=0;j<ny;++j)
                                boundary24<<"U "<<(k+1)<<" "<<(side+1)<<" "
                                          <<(j+1)<<" "<<g24.wind.ub_west_east_mps[
                                            k*2*ny+side*ny+j]<<"\n";
                            for(std::size_t i=0;i<nx;++i)
                                boundary24<<"V "<<(k+1)<<" "<<(side+1)<<" "
                                          <<(i+1)<<" "<<g24.wind.vb_south_north_mps[
                                            k*2*nx+side*nx+i]<<"\n";
                        }
                    boundary24.flush();
                    if(!boundary24)
                        throw std::runtime_error("G24 native wind boundary file incomplete");
                    std::size_t nonzero_w=0;
                    for(const float w:g24.wind.w_face_mps)
                        nonzero_w+=std::abs(w)>1.e-6f;
                    std::cout<<"PASS_P6G_G24_FILE_SOURCE_POST_INTER2_SMOOOTH_DIVCEL_W "
                             <<"UV_DIV_W_SCALARS="<<1296*5
                             <<" NONZERO_W_FACE="<<nonzero_w
                             <<" ORIGINAL_REFERENCE=NOT_YET_RUN "
                               "G14_HOURS_COMMITTED=0\n";
                }
                std::cout<<"PASS_P6G_G23_SOURCE_STHEOR_DIAGI_INTER2 "
                         <<"STATIONS="<<station.station_diagi.size()
                         <<" CELLS="<<cells
                         <<" UV_VALUES="<<cells*9*2
                         <<" CHANGED_DIAGI_SS_COMPONENTS="
                         <<station.replaced_surface_profile_values
                         <<" SOURCE_CMECH="<<station.source_cmech
                         <<" PREVIOUS_STATE_MUTATED=0 G14_HOURS_COMMITTED=0 "
                           "FULL_VENDOR_45_FIELD=NOT_ACCEPTED\n";
            }
            std::cout<<"PASS_P6G_G22_SOURCE_HEATFX_AIRDEN_ELUSTR_SLOPE "
                     <<"CELLS="<<cells<<" WIND_UV_VALUES="<<cells*9*2
                     <<" CHANGED_SLOPE_COMPONENTS="<<joined.changed_slope_components
                     <<" STABLE_CELLS="<<joined.elustr.stable_cells
                     <<" DAYTIME_CELLS="<<joined.elustr.daytime_cells
                     <<" G14_HOURS_COMMITTED=0 FULL_45_FIELD=NOT_ACCEPTED\n";
        }
        std::cout<<(real_one_one ? "PASS_P6G_G21_REAL_1SS1US_FRADJ_TEST_ONLY " :
                   "PASS_P6G_G21_FILE_SOURCE_SELECTED_FRADJ ")
                 <<"GRID_CELLS="<<cells<<" UV_VALUES="<<cells*9*2
                 <<" FRADJ_CHANGED_COMPONENTS="<<selected.corrected_uv_values
                 <<" TWO_PASS_IAVET=1 HOURLY_COMMITTED=0 "
                 <<"FULL_CALMET_VENDOR_PARITY=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"FAIL_P6G_G21_SELECTED_FRADJ "<<e.what()<<"\n";
        return 1;
    }
}
