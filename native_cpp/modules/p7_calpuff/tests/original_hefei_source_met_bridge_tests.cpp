// P7 frozen Hefei input-authority bridge: unmodified Group 13b point source
// plus ORIGINAL METFM1 full hourly winds. This is not PRFIN or CALCPF parity.
#include "cteas/puff/original_met_hours.hpp"
#include "cteas/puff/original_release_wind.hpp"
#include "cteas/puff/plume_rise.hpp"
#include "cteas/puff/original_point_prfin.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/release.hpp"
#include <bit>
#include <cstdint>
#include "cteas/puff/original_native_terrain.hpp"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void demand(bool condition,const char* reason){
    if(!condition)throw std::runtime_error(reason);
}
struct FrozenSource {
    std::string name;
    std::vector<float> row;
};
FrozenSource read_selected_point(const std::string& filename){
    std::ifstream in(filename);
    demand(static_cast<bool>(in),"missing original puff.inp");
    const std::regex identity(R"(^\s*1\s*!\s*SRCNAM\s*=\s*([^!]+)\s*!\s*$)");
    const std::regex data(R"(^\s*1\s*!\s*X\s*=\s*([^!]+)!\s*$)");
    const std::regex count(R"(!\s*NPT1\s*=\s*1\s*!)");
    const std::regex no_external(R"(!\s*NPT2\s*=\s*0\s*!)");
    const std::regex no_variable(R"(!\s*NSPT1\s*=\s*0\s*!)");
    FrozenSource source;
    int names=0,rows=0;
    bool one_point=false,no_file=false,no_variation=false;
    std::string line;
    while(std::getline(in,line)){
        std::smatch m;
        if(std::regex_search(line,count))one_point=true;
        if(std::regex_search(line,no_external))no_file=true;
        if(std::regex_search(line,no_variable))no_variation=true;
        if(std::regex_match(line,m,identity)){
            source.name=m[1].str();
            const auto end=source.name.find_last_not_of(" \t\r\n");
            if(end!=std::string::npos)source.name.resize(end+1);
            ++names;
        }
        if(std::regex_match(line,m,data)){
            std::string csv=m[1].str();
            std::replace(csv.begin(),csv.end(),',',' ');
            std::istringstream values(csv);
            double value;
            while(values>>value){
                demand(std::isfinite(value),"nonfinite original point field");
                source.row.push_back(static_cast<float>(value));
            }
            demand(values.eof(),"malformed original Group 13b value");
            ++rows;
        }
    }
    demand(one_point&&no_file&&no_variation&&names==1&&rows==1&&
           source.name=="HTO_STACK"&&source.row.size()==10,
           "not the locked original single constant point source");
    const auto& r=source.row;
    demand(r[0]==513.385F&&r[1]==3533.769F&&r[2]==70.8F&&
           r[3]==0.0F&&r[4]==1.6F&&r[5]==17.26F&&
           r[6]==298.15F&&r[7]==0.0F&&r[8]==834000.0F&&
           r[9]==0.0F,
           "frozen 2022 real source changed: no synthetic substitution");
    return source;
}
} // namespace

int main(int argc,char** argv){
    try{
        if(argc!=3)throw std::invalid_argument(
            "usage: original_hefei_source_met_bridge_tests MET.DAT puff.inp");
        const auto source=read_selected_point(argv[2]);
        const auto deck=cteas::puff::ControlFile::read_file(argv[2]);
        demand(deck.required_int("METFM")==1 &&
               deck.required_int("MTRANS")==1 &&
               deck.required_int("MTIP")==1 &&
               deck.required_int("MRISE")==1 &&
               deck.required_int("MPARTL")==1 &&
               deck.required_int("MSHEAR")==0 &&
               deck.required_int("MGAUSS")==1 &&
               deck.required_int("MXNEW")==99,
               "native first-hour bridge requires frozen original Briggs point flags");
        const auto factor=deck.required_float_list("FMFAC");
        const auto sampling=deck.required_float_list("XSAMLEN");
        demand(factor.size()==1&&factor[0]==1.0 &&
               sampling.size()==1&&sampling[0]==1.0,
               "native POINTS1 flux or XTMP1 control differs from frozen deck");
        std::size_t hours=0;
        float min_ws=std::numeric_limits<float>::infinity();
        float max_ws=0.0F;
        std::size_t calms=0;
        float source_x_cells=0.0F,source_y_cells=0.0F;
        const auto summary=cteas::puff::OriginalMetHourlyReader::read(
            argv[1],[&](const cteas::puff::Calmet21Header& header,
                         const cteas::puff::Calmet21Static& statics,
                         const cteas::puff::OriginalMetHour& hour){
                demand(header.nx==50&&header.ny==50&&header.nz==9&&
                       header.dx_m==100.0F&&
                       statics.elevation_m.size()==2500,
                       "original 2022 MET grid or static terrain changed");
                // Original XPT1GRD/YPT1GRD are RELATIVE met-grid units.
                // Do not pass UTM km 513.385/3533.769 to the puff solver.
                const float x=static_cast<float>(
                    (source.row[0]*1000.0F-header.origin_x_m)/header.dx_m);
                const float y=static_cast<float>(
                    (source.row[1]*1000.0F-header.origin_y_m)/header.dx_m);
                demand(std::isfinite(x)&&std::isfinite(y)&&
                       std::abs(x-25.0F)<0.001F&&std::abs(y-25.0F)<0.001F,
                       "original source / CALMET origin grid mismatch");
                if(hours==0){
                    source_x_cells=x;source_y_cells=y;
                    const auto n=static_cast<std::size_t>(header.nx)*header.ny;
                    const auto cell=cteas::puff::original_met_cell(
                        x,y,header.nx,header.ny).offset_0based;
                    demand(hour.tempk.size()==n&&hour.zi.size()==n&&
                           hour.ipgt.size()==n&&hour.el.size()==n&&
                           hour.t.size()==n*static_cast<std::size_t>(header.nz),
                           "first original MET hour lacks stack temperature or stability");
                    const auto layer=cteas::puff::original_release_wind_metfm1(
                        hour,statics,{.x_cells=x,.y_cells=y,
                            .release_height_m=source.row[2],
                            .calm_threshold_ms=0.5F}).layer_1based;
                    const auto column=(static_cast<std::size_t>(layer)-1U)*n+cell;
                    // POINTS1 L15454,15509,15527-15548: the locked
                    // METFM1 2-D TEMP2D controls BOTH buoyancy and momentum
                    // flux. The 3-D stack-level T is not this source TEMP.
                    // PRFIN is source-ported, but SQRTS is intentionally
                    // not fabricated: it is immaterial only at PG class A-D.
                    const auto pg=hour.ipgt[cell];
                    demand(pg>=1&&pg<=4,
                        "real first-hour PRFIN requires stable SQRTS/PTLAPS port");
                    const auto wind=cteas::puff::original_release_wind_metfm1(
                        hour,statics,{.x_cells=x,.y_cells=y,
                            .release_height_m=source.row[2],
                            .calm_threshold_ms=0.5F});
                    const auto flux=cteas::puff::stack_fluxes({
                        .diameter_m=source.row[4],
                        .exit_velocity_ms=source.row[5],
                        .stack_temperature_k=source.row[6],
                        .ambient_temperature_k=hour.tempk[cell],
                        .temperature_excess_k=std::max(0.0F,
                            source.row[6]-hour.tempk[cell]),
                        .momentum_flux_factor=factor[0] // actual Group 13b FMFAC
                    });
                    demand(flux.buoyancy_m4s3>0&&flux.momentum_m4s2>0,
                           "genuine HTO_STACK buoyancy/momentum flux absent");
                    const auto tip=cteas::puff::stack_tip_downwash({
                        .stack_height_m=source.row[2],
                        .diameter_m=source.row[4],
                        .momentum_flux=flux.momentum_m4s2,
                        .exit_velocity_ms=source.row[5],
                        .stack_wind_speed_ms=wind.wind_speed_ms
                    });
                    const auto rise=cteas::puff::final_plume_rise({
                        .exit_velocity_ms=source.row[5],
                        .diameter_m=source.row[4],
                        .momentum_flux=flux.momentum_m4s2,
                        .buoyancy_flux=flux.buoyancy_m4s3,
                        .stack_wind_speed_ms=wind.wind_speed_ms,
                        .stability_class=pg,
                        .sqrt_stability_s=0.0 // PRFIN A-D does not read SQRTS
                    });
                    const float pbl=hour.zi[cell];
                    const float stack=source.row[2];
                    const float transition=0.67F*(pbl-stack);
                    // Original POINTS1 L15562 calls PRFPP on A-D, positive
                    // buoyancy even if the plume does not penetrate. PRFPP
                    // only needs the upstream PTLAPS gradient if the final
                    // rise exceeds 0.67*(PBL-HTSTAK); fail closed otherwise.
                    demand(pbl>stack && rise.z_final_m<=transition,
                        "first-hour PRFPP depends on PTLAPS: native full case held");
                    const auto partial=cteas::puff::partial_penetration_rise({
                        .final_rise_m=rise.z_final_m,
                        .buoyancy_flux=flux.buoyancy_m4s3,
                        .stack_wind_speed_ms=wind.wind_speed_ms,
                        .stack_height_m=stack,
                        .mixing_height_m=pbl,
                        .ambient_temperature_k=hour.tempk[cell],
                        .inversion_gradient_k_per_m=0.0,
                        .inversion_jump_k=0.0
                    });
                    demand(partial.final_rise_m==rise.z_final_m &&
                           partial.mass_fraction_mixed==1.0 &&
                           partial.max_height_m==pbl,
                           "source PRFPP no-penetration branch changed plume physics");
                    const float heff=static_cast<float>(
                        stack+partial.final_rise_m-tip);
                    const auto upper=cteas::puff::original_release_wind_metfm1(
                        hour,statics,{.x_cells=x,.y_cells=y,
                            .release_height_m=heff,
                            .calm_threshold_ms=0.5F});
                    demand(std::isfinite(heff)&&heff>stack &&
                           std::isfinite(rise.x_final_m)&&rise.x_final_m>0,
                           "native first-hour PRFIN produced invalid effective height");
                    const float wsnew=std::max(
                        wind.wind_speed_ms,upper.wind_speed_ms);
                    const float xtmp1=3600.0F /
                        (header.dx_m*static_cast<float>(sampling[0]));
                    const auto cadence=cteas::puff::release_cadence({
                        .wind_speed_ms=wsnew,
                        .emission_interval=xtmp1,
                        .max_puffs=deck.required_int("MXNEW"),
                        .hour_seconds=3600.0
                    });
                    // ORIGINAL DGM 2022-first-hour slice manifest:
                    // zold min=max=136.40403747558594, wsvar=1.493919849395752,
                    // reftsamp=66.66666412353516. These are CHECKS only;
                    // the native values were calculated from met.dat + deck.
                    // Never use the DGM values as initial/solver inputs.
                    demand(std::bit_cast<std::uint32_t>(heff)==
                               std::bit_cast<std::uint32_t>(136.40403747558594F),
                           "first-hour PRFIN HEFF differs from frozen original DGM");
                    demand(std::bit_cast<std::uint32_t>(wsnew)==
                               std::bit_cast<std::uint32_t>(1.493919849395752F),
                           "first-hour RLSMET WSNEW differs from frozen original DGM");
                    demand(cadence.puff_count==54 &&
                           std::bit_cast<std::uint32_t>(
                               static_cast<float>(cadence.emission_duration_s))==
                           std::bit_cast<std::uint32_t>(66.66666412353516F),
                           "native first-hour POINTS1 cadence differs from original DGM");
                    const cteas::puff::OriginalPointPrfinRequest request{
                        x,y,source.row[2],source.row[4],source.row[5],
                        source.row[6],static_cast<float>(factor[0]),0.5F,
                        static_cast<float>(sampling[0]),
                        deck.required_int("MXNEW"),3600.0F};
                    const auto portable=cteas::puff::original_point_prfin_metfm1(
                        hour,statics,header,request);
                    demand(portable.effective_height_m==heff &&
                           portable.release_wind_ms==wsnew &&
                           portable.buoyancy_flux==
                               static_cast<float>(flux.buoyancy_m4s3) &&
                           portable.momentum_flux==
                               static_cast<float>(flux.momentum_m4s2) &&
                           portable.x_final_m==
                               static_cast<float>(rise.x_final_m) &&
                           portable.release.puff_count==cadence.puff_count &&
                           static_cast<float>(portable.release.emission_duration_s)==
                               static_cast<float>(cadence.emission_duration_s),
                           "native reusable PRFIN source differs from independent first-hour bridge");
                    auto stable=hour;
                    stable.ipgt[cell]=5;
                    bool stable_rejected=false;
                    try{
                        (void)cteas::puff::original_point_prfin_metfm1(
                            stable,statics,header,request);
                    }catch(const std::invalid_argument&){stable_rejected=true;}
                    demand(stable_rejected,
                        "stable RLSMET must reject missing LCALGRD provenance");
                    // Test native stable source PTLAPS using the real frozen
                    // 3D CALMET temperature column, not frozen original DGM.
                    auto stable_profile_request=request;
                    stable_profile_request.use_calmet_profile_lapse=true;
                    const auto stable_prfin=
                        cteas::puff::original_point_prfin_metfm1(
                            stable,statics,header,stable_profile_request);
                    demand(stable_prfin.stability_class==5 &&
                           std::isfinite(stable_prfin.sqrt_stability_s) &&
                           stable_prfin.sqrt_stability_s>0.0F &&
                           stable_prfin.mixed_fraction==1.0F &&
                           stable_prfin.max_layer_height_m==stable.zi[cell] &&
                           stable_prfin.final_rise_m>0.0F,
                           "stable RLSMET PTLAPS / no-PRFPP branch invalid");
                    // Force a true A-D inversion-penetration state from
                    // the same native temperature/wind inputs. No oracle
                    // or fitted constants are involved. This catches both
                    // erroneously bypassing PRFPP and missing PTLAPS input.
                    auto crossing=hour;
                    crossing.zi[cell]=75.0F; // above stack by only 4.2 m
                    const auto penetration=
                        cteas::puff::original_point_prfin_metfm1(
                            crossing,statics,header,stable_profile_request);
                    demand(penetration.stability_class==4 &&
                           penetration.final_rise_m>0.0F &&
                           penetration.mixed_fraction>=0.0F &&
                           penetration.mixed_fraction<=1.0F &&
                           penetration.final_rise_m<=
                               static_cast<float>(penetration.brigg.z_final_m) &&
                           penetration.effective_height_m>request.stack_height_m &&
                           std::isfinite(penetration.max_layer_height_m),
                           "native A-D PRFPP inversion penetration invalid");
                    bool crossing_without_profile_rejected=false;
                    try {
                        (void)cteas::puff::original_point_prfin_metfm1(
                            crossing,statics,header,request);
                    } catch(const std::invalid_argument&) {
                        crossing_without_profile_rejected=true;
                    }
                    demand(crossing_without_profile_rejected,
                           "A-D PRFPP used invented inversion gradient");
                    std::cout<<"P7_PRFPP_AD_INVERSION_NATIVE_TEST=PASS"
                             <<" FMIX="<<penetration.mixed_fraction
                             <<" RISE_M="<<penetration.final_rise_m
                             <<" HMAX_M="<<penetration.max_layer_height_m
                             <<" MISSING_PROFILE_REJECTED=YES"
                             <<" ORIGINAL_H24_PARITY=OPEN\\n";
                    std::cout<<"P7_NATIVE_PRODUCTION_PRFIN_REUSE=PASS"
                             <<" SITE_IS_GRID_RELATIVE=YES"
                             <<" STABLE_PTLAPS=PROFILE_REAL4"
                             <<" DGM_SEEDING=NO\\n";
                    std::cout<<"P7_FIRST_HOUR_PRFIN_DGM_COMPARE=PASS"
                             <<" HEFF_REAL4=BITWISE"
                             <<" WSNEW_REAL4=BITWISE"
                             <<" NPUFFS="<<cadence.puff_count
                             <<" DT_S="<<cadence.emission_duration_s
                             <<" ORACLE_USED_AS_SOLVER_INPUT=NO"
                             <<" COMPLETE_COMP=NOT_ACCEPTED\\n";
                    std::cout<<"P7_FIRST_HOUR_NATIVE_PRFIN"
                             <<" STACK_WS_MS="<<wind.wind_speed_ms
                             <<" HEFF_WS_MS="<<upper.wind_speed_ms
                             <<" TEMP2D_K="<<hour.tempk[cell]
                             <<" FLUXB="<<flux.buoyancy_m4s3
                             <<" FLUXM="<<flux.momentum_m4s2
                             <<" STKTIP_M="<<tip
                             <<" XFINAL_M="<<rise.x_final_m
                             <<" RISE_M="<<rise.z_final_m
                             <<" HEFF_M="<<heff
                             <<" PRFPP_FMIX="<<partial.mass_fraction_mixed
                             <<" PRFPP_HMAX="<<partial.max_height_m
                             <<" PTLAPS_INDEPENDENT=YES"
                             <<" FULL_COMP=NOT_YET_ACCEPTED\\n";
                    std::cout<<"P7_FIRST_HOUR_RELEASE_MET"
                             <<" YEAR="<<hour.begin.year
                             <<" JULIAN="<<hour.begin.julian_day
                             <<" HOUR="<<hour.begin.hour
                             <<" CELL="<<cell
                             <<" STACK_LAYER="<<layer
                             <<" PGT="<<hour.ipgt[cell]
                             <<" TEMP2D_K="<<hour.tempk[cell]
                             <<" TEMP3D_STACK_K="<<hour.t[column]
                             <<" DPBL_M="<<hour.zi[cell]
                             <<" EL_M="<<hour.el[cell]
                             <<" ROUGHNESS_M="<<statics.roughness_m[cell]
                             <<" DIAMETER_M="<<source.row[4]
                             <<" EXIT_MS="<<source.row[5]
                             <<" STACK_K="<<source.row[6]<<"\\n";
                }else demand(x==source_x_cells&&y==source_y_cells,
                            "source shifted between hourly MET snapshots");
                const auto stack=cteas::puff::original_release_wind_metfm1(
                    hour,statics,{
                        .x_cells=x,.y_cells=y,
                        .release_height_m=source.row[2],
                        .calm_threshold_ms=0.5F
                    });
                demand(stack.wind_speed_raw_ms>=0.0F&&
                       std::isfinite(stack.wind_speed_raw_ms)&&
                       stack.layer_1based>=1&&stack.layer_1based<=9,
                       "native real RLSMET stack wind invalid");
                min_ws=std::min(min_ws,stack.wind_speed_raw_ms);
                max_ws=std::max(max_ws,stack.wind_speed_raw_ms);
                calms+=static_cast<std::size_t>(stack.calm);
                ++hours;
            },true);
        demand(hours==143&&summary.intervals==143,
               "native case did not consume all 143 real MET hours");
        std::cout<<"P7_HEFEI_SOURCE_MET_STACK_BRIDGE=PASS HOURS="<<hours
                 <<" SOURCE_NAME="<<source.name
                 <<" XPT1GRD="<<source_x_cells
                 <<" YPT1GRD="<<source_y_cells
                 <<" STACK_HEIGHT_M="<<source.row[2]
                 <<" EMISSION_BQ_S="<<source.row[8]
                 <<" WIND_MIN_MS="<<min_ws<<" WIND_MAX_MS="<<max_ws
                 <<" CALM_HOURS="<<calms
                 <<" REAL_MET_DRIVER=YES DGM_DRIVING_INPUT=NO"
                 <<" NATIVE_FIRST_HOUR_PRFIN_DGM=PASS"
                 <<" MDRY_CALCPF_PARITY=NOT_YET_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P7_HEFEI_SOURCE_MET_STACK_BRIDGE=FAIL "<<e.what()<<'\n';
        return 1;
    }
}
