// Frozen Hefei 2022 first-hour native H-3 concentration diagnostic.
// Original puff.con is a post-run comparator ONLY: it is never fed to
// POINTS1, COMP, DRY, PUFRECS or CALCPF.
#include "cteas/puff/conc_file.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/dry_deposition.hpp"
#include "cteas/puff/original_comp_rise_hourly.hpp"
#include "cteas/puff/original_flat_calcpf.hpp"
#include "cteas/puff/original_met_hours.hpp"
#include "cteas/puff/original_native_terrain.hpp"
#include "cteas/puff/receptors.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

using namespace cteas::puff;
namespace {
void need(bool condition,const char* why) {
    if(!condition)throw std::runtime_error(why);
}
std::string control_bytes(const std::string& path) {
    std::ifstream file(path,std::ios::binary);
    need(bool(file),"frozen 2022 puff.inp unavailable");
    const std::string text((std::istreambuf_iterator<char>(file)),
                            std::istreambuf_iterator<char>());
    need(!text.empty(),"empty frozen puff.inp");
    return text;
}
}

int main(int argc,char** argv) {
  try {
    need(argc==4 || argc==5,
         "usage: p7_hefei_real_h3 MET.DAT puff.inp puff.con [read-only-native-trace.tsv]");
    const auto control=control_bytes(argv[2]);
    const auto deck=ControlFile::read_file(argv[2]);
    need(deck.required_int("METFM")==1 &&
         deck.required_int("NPT1")==1 &&
         deck.required_int("NSPEC")==2 &&
         deck.required_int("MCTADJ")==2 &&
         deck.required_int("MDRY")==1 &&
         deck.required_int("MTRANS")==1 &&
         deck.required_int("MXSAM")==99,
         "unexpected frozen source/meteorology/terrain/dry scenario");
    // Read immutable reference once for DIAGNOSTIC comparison, never to
    // supply source parameters, winds, mass, positions or gradients.
    const auto original=read_conc_species_fields(argv[3],50,50);
    need(original.size()>=143 && original.front().species_index==1 &&
         original.front().label.find("H-3")!=std::string::npos &&
         original.front().values.size()==2500,
         "frozen original puff.con first H-3 field unavailable");
    const auto stack=deck.required_float_list("X");
    const auto factors=deck.required_float_list("FMFAC");
    const auto ymin=deck.required_float_list("SYMIN");
    const auto zmin=deck.required_float_list("SZMIN");
    const auto lengths=deck.required_float_list("XSAMLEN");
    const auto cdiv=deck.required_float_list("CDIV");
    need(stack.size()==10 && factors.size()==1 &&
         ymin.size()==1 && zmin.size()==1 &&
         lengths.size()==1 && cdiv.size()==2,
         "frozen original point and COMP controls missing");

    bool evaluated=false;
    const auto summary=OriginalMetHourlyReader::read(argv[1],
      [&](const Calmet21Header& header,const Calmet21Static& static_met,
          const OriginalMetHour& met) {
        if(evaluated)return;
        evaluated=true;
        need(met.begin.year==2022 && met.begin.julian_day==1 &&
             met.begin.hour==0 &&
             header.nx==50 && header.ny==50 &&
             header.nz==9 && header.dx_m==100.0F,
             "not immutable first-hour 50x50x9 original MET");
        OriginalPointPrfinRequest request;
        request.x_cells=static_cast<float>(
            (static_cast<float>(stack[0])*1000.0F-header.origin_x_m)/
             header.dx_m);
        request.y_cells=static_cast<float>(
            (static_cast<float>(stack[1])*1000.0F-header.origin_y_m)/
             header.dx_m);
        request.stack_height_m=static_cast<float>(stack[2]);
        request.diameter_m=static_cast<float>(stack[4]);
        request.exit_velocity_ms=static_cast<float>(stack[5]);
        request.stack_temperature_k=static_cast<float>(stack[6]);
        request.momentum_flux_factor=static_cast<float>(factors[0]);
        request.calm_threshold_ms=0.5F;
        request.max_sample_distance_cells=static_cast<float>(lengths[0]);
        request.max_new_puffs=deck.required_int("MXNEW");
        const auto prfin=original_point_prfin_metfm1(
            met,static_met,header,request);
        OriginalPointNativeSourceParameters native_source;
        native_source.base_elevation_m=static_cast<float>(stack[3]);
        native_source.met_spacing_m=header.dx_m;
        native_source.initial_sigma_y_m=static_cast<float>(ymin[0]);
        native_source.initial_sigma_z_m=static_cast<float>(zmin[0]);
        native_source.emission_rates={stack[8],stack[9]};
        const auto source=original_point_hour_from_prfin(
            request,prfin,native_source);
        need(source.mass.species_count==2 &&
             source.mass.emission_rate.at(0)==834000 &&
             source.mass.emission_rate.at(1)==0 &&
             prfin.release.puff_count==54,
             "first-hour actual source emission/release changed");

        NeutralCompControls controls;
        controls.met_spacing_m=header.dx_m;
        controls.max_sample_distance_cells=
            static_cast<float>(lengths[0]);
        controls.calm_threshold_ms=0.5F;
        controls.max_sampling_steps=99;
        controls.original_wdiv=NativeOriginalWdivControls{
            static_cast<float>(cdiv[0]),static_cast<float>(cdiv[1])};
        const auto terrain=OriginalNativeTerrain::from_calmet(
            static_met,met.nx,met.ny,header.dx_m);
        NativeMctadj2Controls terrain_control;
        terrain_control.terrain=terrain.constraint_lookup();
        terrain_control.derive_bvf_from_metfm1=true;
        terrain_control.minimum_pt_gradient_k_per_m=0.005F;
        controls.mctadj2=terrain_control;
        controls.gaussian_dry=NativeGaussianDryControls{
            dry_deposition_setup_from_control(control),1.0F};
        DispersionSetup pg;
        pg.mdisp=3;
        pg.averaging_factor=1;
        pg.sigma_y_heffter_m=550;
        pg.heffter_sigma_z=false;
        pg.roughness_adjustment=false;

        const ReceptorSet receptors=receptors_from_original_met_grid(
            control,{header.origin_x_m,header.origin_y_m,header.dx_m});
        need(receptors.grid.size()==2500 &&
             receptors.sampling_nx==50 && receptors.sampling_ny==50 &&
             receptors.ibsamp==1 && receptors.jbsamp==1 &&
             receptors.mesh_down==1 && receptors.discrete.empty(),
             "original selected 2500-grid receptor geometry drifted");
        struct H3StageRecord {
            int puff_id=0;
            float before_time_s=0.0F,after_time_s=0.0F;
            OriginalCalcpfReceiverIntermediate intermediate;
        };
        std::vector<H3StageRecord> native_h3_stages;
        OriginalCalcpfIntermediateHook h3_hook;
        if(argc==5) {
            h3_hook=[&](const RiseCompSamplingState& state,
                        const OriginalCalcpfReceiverIntermediate& row) {
                if(row.receptor_index!=2468U)return;
                native_h3_stages.push_back({state.puff_id,
                    state.before.travel_time_s,state.after.travel_time_s,row});
            };
        }
        const auto receptor_sampler=make_original_flat_calcpf_sampler(
            receptors,header.dx_m,3600.0F,3.0F,
            OriginalFlatVerticalMethod::receptor_pg_vcoup_mctadj2,
            [&terrain,&receptors](const RiseCompSamplingState& state,
                std::size_t receiver,const OriginalPuffct2Result& position){
                need(state.original_ctadj2_step.has_value() &&
                     state.receptor_effective_wind_ms>0.0F &&
                     std::isfinite(state.receptor_brunt_vaisala_s),
                     "receptor METFM1 BVF/WS not sourced from live COMP");
                return terrain.receptor(
                    receiver,receptors.ibsamp,receptors.jbsamp,
                    receptors.sampling_nx,receptors.sampling_ny,position,
                    state.receptor_brunt_vaisala_s,
                    state.receptor_effective_wind_ms);
            },true,h3_hook,
            // Original first-hour PUFRECS receptor projection at (19,50)
            // clips leading fractions 6.57 -> 1 and trailing -0.288 -> 0.
            // Do not substitute CALCPF's separate NSIGMA=3 for FCLIP.
            0.0F);
        OriginalCompRiseMultiPuffHours driver;
        const OriginalCompPuffBounds bounds{0.0F,50.0F,0.0F,50.0F};
        // Capacity is deliberately nonbinding for the first hour. The
        // original MXPUFF/ROLLDN pressure chronology is a later gate.
        const auto hour=
            driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
                met,static_met,controls,pg,false,source,bounds,
                4096U,2500U,receptor_sampler);
        need(hour.steps.size()==1275U && hour.release.puff_count==54 &&
             hour.receptor_concentrations.size()==2500U &&
             driver.completed_hours()==1U,
             "real first-hour native 1275-step/2500-receptor integration failed");
        if(argc==5) {
            need(!native_h3_stages.empty(),
                 "native original-source hotspot intermediate trace is empty");
            std::ofstream stage_file(argv[4],std::ios::binary);
            need(bool(stage_file),"cannot create requested read-only native H3 trace");
            stage_file<<std::setprecision(9);
            std::size_t previous_step=0;
            std::size_t traced_rows=0;
            bool have_previous=false;
            for(const auto& item:native_h3_stages) {
                std::size_t matched=hour.steps.size();
                for(std::size_t idx=0;idx<hour.steps.size();++idx) {
                    const auto& st=hour.steps[idx];
                    if(st.puff_id==item.puff_id &&
                       st.step.before.travel_time_s==item.before_time_s &&
                       st.step.after.travel_time_s==item.after_time_s) {
                        need(matched==hour.steps.size(),
                             "multiple native COMP substeps match one CALCPF event");
                        matched=idx;
                    }
                }
                need(matched<hour.steps.size() &&
                     (!have_previous || previous_step<matched),
                     "CALCPF intermediate event not in canonical COMP step order");
                previous_step=matched;
                have_previous=true;
                const auto& st=hour.steps[matched];
                const auto& v=item.intermediate;
                if(traced_rows<8U) {
                    const auto& physical=st.step.sigma.step;
                    std::cout<<std::setprecision(9)
                        <<"P7_NATIVE_H3_PUFRECS_VIRTUAL"
                        <<" SEQ="<<matched+1U
                        <<" II="<<item.puff_id
                        <<" KSAM="<<st.ksam
                        <<" frac="<<v.receptor_fraction
                        <<" vtyb="<<physical.virtual_time_y_begin_s
                        <<" vtye="<<physical.virtual_time_y_end_s
                        <<" vdyb="<<physical.virtual_distance_y_begin_km
                        <<" vdye="<<physical.virtual_distance_y_end_km
                        <<" vtzb="<<physical.virtual_time_z_begin_s
                        <<" vtze="<<physical.virtual_time_z_end_s
                        <<" vdzb="<<physical.virtual_distance_z_begin_km
                        <<" vdze="<<physical.virtual_distance_z_end_km
                        <<"\n";
                }
                ++traced_rows;
                stage_file<<matched+1U<<" "<<item.puff_id<<" "<<st.ksam<<" "
                          <<v.sigma_y_m<<" "<<v.sigma_z_m<<" "
                          <<v.puff_height_m<<" "<<v.receptor_pole_m<<" "
                          <<v.vertical_factor<<" "<<v.xi1<<" "<<v.xi2<<" "
                          <<v.t1<<" "<<v.t2<<" "<<v.qold<<" "<<v.qnew<<" "
                          <<v.xtemp<<" "<<v.concentration<<"\n";
            }
            stage_file.flush();
            need(bool(stage_file),"native H3 stage trace flush failed");
            std::cout<<"P7_NATIVE_H3_CALCPF_STAGE_TRACE=PASS"
                     <<" RECORDS="<<native_h3_stages.size()
                     <<" RECEPTOR_I=19 RECEPTOR_J=50"
                     <<" FIELD_COUNT=13"
                     <<" ORIGINAL_VENDOR_STAGE_PARITY=NOT_YET_COMPARED\n";
        }
        std::size_t dried=0,receiver_nonzero=0;
        double dry_mass=0.0,max_abs_diff=0.0,sum_abs_diff=0.0;
        double native_total=0.0,reference_total=0.0;
        std::size_t max_diff_cell=0,bitwise_equal=0,reference_nonzero=0;
        struct ReceptorDifference {std::size_t cell;float native,reference;double error;};
        std::vector<ReceptorDifference> mismatches;
        for(const auto& step:hour.steps) {
            need(step.step.dry.has_value() &&
                 step.step.dry->removed_mass.size()==2 &&
                 step.step.dry->removed_mass[1]==0.0F,
                 "H-3/HE-3 physical original DRY species handling failed");
            const float r=step.step.dry->removed_mass[0];
            need(std::isfinite(r)&&r>=0.0F,
                 "original H-3 dry deposition became invalid");
            if(r>0)++dried;
            dry_mass+=r;
        }
        const auto& expected=original.front().values;
        for(std::size_t i=0;i<2500U;++i){
            const float observed=hour.receptor_concentrations[i];
            const float reference=expected[i];
            need(std::isfinite(observed)&&observed>=0.0F &&
                 std::isfinite(reference)&&reference>=0.0F,
                 "original/native H-3 concentration contains invalid value");
            receiver_nonzero+=observed>0.0F?1U:0U;
            reference_nonzero+=reference>0.0F?1U:0U;
            native_total+=observed;
            reference_total+=reference;
            if(std::bit_cast<std::uint32_t>(observed)==
               std::bit_cast<std::uint32_t>(reference))++bitwise_equal;
            else mismatches.push_back({i,observed,reference,
                static_cast<double>(observed)-static_cast<double>(reference)});
            const double diff=std::abs(
                static_cast<double>(observed)-static_cast<double>(reference));
            sum_abs_diff+=diff;
            if(diff>max_abs_diff){max_abs_diff=diff;max_diff_cell=i;}
        }
        // Compare spatial footprints, not only largest absolute errors.
        // Close field totals can conceal a displaced or widened plume;
        // centroids and signed row/column residuals distinguish that
        // from a nearly uniform mass scaling error.
        double nx_moment=0.0,ny_moment=0.0;
        double rx_moment=0.0,ry_moment=0.0;
        double positive_error=0.0,negative_error=0.0;
        std::size_t positive_cells=0,negative_cells=0;
        std::vector<double> signed_row_error(50U,0.0);
        std::vector<double> signed_column_error(50U,0.0);
        for(std::size_t cell=0;cell<2500U;++cell){
            const double n=hour.receptor_concentrations[cell];
            const double o=expected[cell];
            const double x=static_cast<double>(cell%50U)+0.5;
            const double y=static_cast<double>(cell/50U)+0.5;
            nx_moment+=n*x;ny_moment+=n*y;
            rx_moment+=o*x;ry_moment+=o*y;
            const double delta=n-o;
            signed_row_error[cell/50U]+=delta;
            signed_column_error[cell%50U]+=delta;
            if(delta>0.0){positive_error+=delta;++positive_cells;}
            if(delta<0.0){negative_error+=-delta;++negative_cells;}
        }
        need(native_total>0.0 && reference_total>0.0,
             "native/original first-hour H-3 field is empty");
        const double native_x=nx_moment/native_total;
        const double native_y=ny_moment/native_total;
        const double reference_x=rx_moment/reference_total;
        const double reference_y=ry_moment/reference_total;
        const auto top_positive_row=std::max_element(
            signed_row_error.begin(),signed_row_error.end());
        const auto top_negative_row=std::min_element(
            signed_row_error.begin(),signed_row_error.end());
        std::cout<<std::setprecision(9)
                 <<"P7_HEFEI_H3_FOOTPRINT_DIAGNOSTIC"
                 <<" NATIVE_CENTROID_CELL_X="<<native_x
                 <<" NATIVE_CENTROID_CELL_Y="<<native_y
                 <<" REFERENCE_CENTROID_CELL_X="<<reference_x
                 <<" REFERENCE_CENTROID_CELL_Y="<<reference_y
                 <<" DELTA_CENTROID_X_CELLS="<<native_x-reference_x
                 <<" DELTA_CENTROID_Y_CELLS="<<native_y-reference_y
                 <<" POSITIVE_DIFF_CELLS="<<positive_cells
                 <<" NEGATIVE_DIFF_CELLS="<<negative_cells
                 <<" TOTAL_POSITIVE_DIFF_BQ_M3="<<positive_error
                 <<" TOTAL_NEGATIVE_DIFF_BQ_M3="<<negative_error
                 <<" LARGEST_POSITIVE_ROW_J="<<
                    std::distance(signed_row_error.begin(),top_positive_row)+1
                 <<" POSITIVE_ROW_SUM_BQ_M3="<<*top_positive_row
                 <<" LARGEST_NEGATIVE_ROW_J="<<
                    std::distance(signed_row_error.begin(),top_negative_row)+1
                 <<" NEGATIVE_ROW_SUM_BQ_M3="<<*top_negative_row
                 <<" ORIGINAL_NUMERICAL_PARITY=OPEN\\n";
        std::sort(mismatches.begin(),mismatches.end(),
            [](const auto& left,const auto& right){
                return std::abs(left.error)>std::abs(right.error);
            });
        // Reconstruct the worst original/native receptor from independent
        // native per-COMP-substep CALCPF contributions, retaining float32
        // addition order. This is an audit of internal C++ causality,
        // never a second source of solver input or a vendor parity claim.
        constexpr std::size_t hotspot=2468U;  // (i=19,j=50), 0-based 2468
        struct HotspotStep {
            std::size_t sequence=0;
            int puff_id=0,release_number=0,ksam=0;
            float concentration=0.0F;
            float post_dry_mass=0.0F;
        };
        std::vector<HotspotStep> hotspot_steps;
        float hotspot_rebuilt=0.0F;
        std::size_t hotspot_nonzero_steps=0;
        for(std::size_t step_idx=0;step_idx<hour.steps.size();++step_idx){
            const auto& item=hour.steps[step_idx];
            need(item.step.receptor_increments.size()==2500U &&
                 item.step.vmass.mass_mixed.size()==2U,
                 "native per-step H-3 CALCPF audit missing source state");
            const float contribution=item.step.receptor_increments[hotspot];
            need(std::isfinite(contribution)&&contribution>=0.0F,
                 "native per-step H-3 CALCPF hotspot invalid");
            hotspot_rebuilt+=contribution;
            if(contribution>0.0F){
                ++hotspot_nonzero_steps;
                hotspot_steps.push_back({step_idx,item.puff_id,
                    item.release_number,item.ksam,contribution,
                    item.step.vmass.mass_mixed[0]});
            }
        }
        need(std::bit_cast<std::uint32_t>(hotspot_rebuilt)==
             std::bit_cast<std::uint32_t>(
                 hour.receptor_concentrations[hotspot]) &&
             hotspot_nonzero_steps>0U,
             "H-3 native hotspot lost REAL4 COMP substep accumulation");
        std::sort(hotspot_steps.begin(),hotspot_steps.end(),
            [](const auto& left,const auto& right){
                return left.concentration>right.concentration;
            });
        double hotspot_top_sum=0.0;
        for(std::size_t k=0;k<std::min<std::size_t>(hotspot_steps.size(),10U);++k){
            const auto& s=hotspot_steps[k];
            hotspot_top_sum+=s.concentration;
            std::cout<<std::setprecision(9)
                     <<"P7_HEFEI_H3_HOTSPOT_SOURCE_SUBSTEP"
                     <<" RANK="<<k+1U
                     <<" STEP_INDEX0="<<s.sequence
                     <<" PUFF_ID="<<s.puff_id
                     <<" RELEASE_NUMBER="<<s.release_number
                     <<" KSAM="<<s.ksam
                     <<" POST_DRY_H3_BQ="<<s.post_dry_mass
                     <<" RECEPTOR_INCREMENT_BQ_M3="<<s.concentration<<"\\n";
        }
        std::cout<<std::setprecision(9)
                 <<"P7_HEFEI_H3_HOTSPOT_SUBSTEP_AUDIT=PASS"
                 <<" INDEX0="<<hotspot
                 <<" TOTAL_COMP_SUBSTEPS="<<hour.steps.size()
                 <<" CONTRIBUTING_SUBSTEPS="<<hotspot_nonzero_steps
                 <<" TOP10_FRACTION="<<
                    hotspot_top_sum/static_cast<double>(hotspot_rebuilt)
                 <<" REAL4_REBUILT_BQ_M3="<<hotspot_rebuilt
                 <<" ORIGINAL_HOURLY_BQ_M3="<<expected[hotspot]
                 <<" ORIGINAL_STEP_ORACLE=NOT_YET_AVAILABLE\\n";
        const auto top=std::min<std::size_t>(mismatches.size(),12U);
        for(std::size_t k=0;k<top;++k){
            const auto& d=mismatches[k];
            std::cout<<std::setprecision(9)
                     <<"P7_HEFEI_H3_FIRSTHOUR_RECEPTOR_DIFF"
                     <<" RANK="<<k+1<<" INDEX0="<<d.cell
                     <<" GRID_I="<<d.cell%50U+1U
                     <<" GRID_J="<<d.cell/50U+1U
                     <<" NATIVE_BQ_M3="<<d.native
                     <<" ORIGINAL_BQ_M3="<<d.reference
                     <<" SIGNED_DIFFERENCE="<<d.error
                     <<" RELATIVE_TO_ORIGINAL="<<
                     (d.reference!=0.0F ?
                       d.error/static_cast<double>(d.reference):0.0)
                     <<" ORIGINAL_ZERO="<<(d.reference==0.0F?"YES":"NO")
                     <<"\n";
        }
        need(dried>0 && dry_mass>0,
             "real first-hour source-ordered MDRY=1 never removed H-3 mass");
        need(receiver_nonzero>0,
             "real first-hour PUFRECS/CALCPF produced all-zero H-3");
        std::cout<<std::setprecision(9)
                 <<"P7_HEFEI_REAL_FIRSTHOUR_NATIVE_H3_RECEPTORS=PASS"
                 <<" COMP_SUBSTEPS="<<hour.steps.size()
                 <<" GRID_CELLS="<<hour.receptor_concentrations.size()
                 <<" NONZERO_NATIVE="<<receiver_nonzero
                 <<" NONZERO_REFERENCE="<<reference_nonzero
                 <<" POSITIVE_DRY_SUBSTEPS="<<dried
                 <<" DRY_REMOVED_BQ="<<dry_mass
                 <<" REFERENCE_BITWISE_MATCH="<<bitwise_equal<<"/2500"
                 <<" REFERENCE_MEAN_ABS_ERROR="<<sum_abs_diff/2500.0
                 <<" REFERENCE_MAX_ABS_ERROR="<<max_abs_diff
                 <<" REFERENCE_MAX_ERROR_CELL="<<max_diff_cell
                 <<" NATIVE_FIELD_SUM_BQ_M3="<<native_total
                 <<" REFERENCE_FIELD_SUM_BQ_M3="<<reference_total
                 <<" CONCENTRATION_MISMATCH_CELLS="<<mismatches.size()
                 <<" REFERENCE_SCIENTIFIC_PARITY=PASS_FIRSTHOUR_H3_REAL4_ONLY"
                 <<" 6H_143H=NOT_YET_ACCEPTED\n";
        // This must remain a scientific acceptance gate, not merely a smoke
        // test that prints diagnostics and exits successfully. The original
        // frozen puff.con is a post-run oracle, never a solver input.
        need(bitwise_equal==2500U && mismatches.empty() &&
             max_abs_diff==0.0 && sum_abs_diff==0.0,
             "Hefei original first-hour H3 concentration REAL4 parity regressed");
        std::cout<<"P7_HEFEI_FIRST_HOUR_2500_REAL4_CONCENTRATION_PARITY=PASS"
                 <<" SPECIES=H3 GRID=50x50"
                 <<" RECEPTOR_WORDS=2500/2500"
                 <<" FULL_6H_143H_AND_OUTPUT=NOT_YET_ACCEPTED\n";
      },true);
    need(evaluated && summary.intervals==143,
         "full frozen MET provenance 143 hours is required");
    return 0;
  }catch(const std::exception& e){
    std::cerr<<"P7_HEFEI_REAL_FIRSTHOUR_NATIVE_H3_RECEPTORS=FAIL "
             <<e.what()<<"\n";
    return 1;
  }
}
