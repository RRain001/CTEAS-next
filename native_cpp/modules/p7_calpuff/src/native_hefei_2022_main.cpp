// Scoped native-only CALPUFF 7.2.1 H-3 execution for the locked Hefei 2022 case.
// A production caller supplies MET, puff.inp, MAKEGEO, and a new output path.
// No vendor puff.con or original DGM path, reader, or state input exists here.
#include "cteas/puff/conc_file.hpp"
#include "cteas/puff/hourly_conc.hpp"
#include "cteas/puff/original_wrout1_hefei.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/dry_deposition.hpp"
#include "cteas/puff/original_comp_rise_hourly.hpp"
#include "cteas/puff/original_calm_sigma.hpp"
#include "cteas/puff/original_flat_calcpf.hpp"
#include "cteas/puff/original_met_hours.hpp"
#include "cteas/puff/original_met_cell.hpp"
#include "cteas/puff/original_native_terrain.hpp"
#include "cteas/puff/receptors.hpp"
#include "cteas/puff/native_p6_admission.hpp"
#include "cteas/puff/sha256.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>

using namespace cteas::puff;
namespace {
void require(bool pass,const char* reason) {
    if(!pass)throw std::runtime_error(reason);
}
std::string read_text(const std::string& path) {
    std::ifstream in(path,std::ios::binary);
    require(static_cast<bool>(in),"P7_NATIVE_MISSING_SOURCE_CONTROL");
    return {std::istreambuf_iterator<char>(in),
            std::istreambuf_iterator<char>()};
}
// Do not publish a partially written Fortran WROUT1 file on model failure.
// Link creation is atomic and refuses clobbering any concurrently created
// destination. Keep the partial file in the same filesystem/directory.
class OutputPublication {
public:
    explicit OutputPublication(const std::string& target)
        : final_(target),stage_(target+".cteas-partial") {
        require(!std::filesystem::exists(final_) &&
                !std::filesystem::exists(stage_),
                "P7_NATIVE_OUTPUT_OR_PARTIAL_ALREADY_EXISTS");
    }
    ~OutputPublication() {
        if(!published_) {
            std::error_code error;
            std::filesystem::remove(stage_,error);
        }
    }
    const std::string& staged_path() const noexcept { return stage_; }
    void publish() {
        require(std::filesystem::is_regular_file(stage_) &&
                std::filesystem::file_size(stage_)>10000U,
                "P7_NATIVE_PARTIAL_CON_INVALID");
        require(!std::filesystem::exists(final_),
                "P7_NATIVE_OUTPUT_CREATED_DURING_EXECUTION");
        // std::filesystem::rename can replace an existing POSIX file.
        // Hard-link publication instead is no-clobber and keeps full bytes.
        std::filesystem::create_hard_link(stage_,final_);
        published_=true;
        std::filesystem::remove(stage_);
    }
private:
    std::string final_,stage_;
    bool published_=false;
};
struct Args {
    std::string met,control,makegeo,output,p6_admission,p6_manifest,p6_driver;
    std::size_t hours=0;
};
Args parse(int argc,char** argv) {
    require(argc==17,
        "usage: cteas_p7_native_hefei_2022 --met MET.DAT --control puff.inp --makegeo makegeo.inp --output NEW_puff.con --hours 1|6|143 --p6-admission ADMISSION --p6-manifest MANIFEST --p6-driver DRIVER");
    Args a;
    for(int i=1;i<argc;i+=2) {
        const std::string key=argv[i];
        const std::string value=argv[i+1];
        if(key=="--met"&&a.met.empty())a.met=value;
        else if(key=="--control"&&a.control.empty())a.control=value;
        else if(key=="--makegeo"&&a.makegeo.empty())a.makegeo=value;
        else if(key=="--output"&&a.output.empty())a.output=value;
        else if(key=="--p6-admission"&&a.p6_admission.empty())a.p6_admission=value;
        else if(key=="--p6-manifest"&&a.p6_manifest.empty())a.p6_manifest=value;
        else if(key=="--p6-driver"&&a.p6_driver.empty())a.p6_driver=value;
        else if(key=="--hours"&&a.hours==0U) {
            require(value=="1"||value=="6"||value=="143",
                    "P7_NATIVE_HOUR_OUT_OF_SCOPE");
            a.hours=static_cast<std::size_t>(std::stoul(value));
        } else throw std::runtime_error("P7_NATIVE_UNKNOWN_OR_DUPLICATE_OPTION");
    }
    require(!a.met.empty()&&!a.control.empty()&&!a.makegeo.empty()&&
            !a.output.empty()&&!a.p6_admission.empty()&&
            !a.p6_manifest.empty()&&!a.p6_driver.empty()&&a.hours>0U,
            "P7_NATIVE_MISSING_ARGUMENT");
    const auto dest=std::filesystem::path(a.output);
    require(!std::filesystem::exists(dest),"P7_NATIVE_OUTPUT_EXISTS_NO_OVERWRITE");
    require(std::filesystem::is_directory(dest.parent_path()),
            "P7_NATIVE_OUTPUT_PARENT_MISSING");
    require(std::filesystem::is_regular_file(a.met)&&
            std::filesystem::is_regular_file(a.control)&&
            std::filesystem::is_regular_file(a.makegeo)&&
            std::filesystem::is_regular_file(a.p6_admission)&&
            std::filesystem::is_regular_file(a.p6_manifest)&&
            std::filesystem::is_regular_file(a.p6_driver),
            "P7_NATIVE_INPUT_NOT_A_REGULAR_FILE");
    require(std::filesystem::path(a.met)!=dest &&
            std::filesystem::path(a.control)!=dest &&
            std::filesystem::path(a.makegeo)!=dest,
            "P7_NATIVE_INPUT_OUTPUT_ALIAS");
    return a;
}
} // namespace

int main(int argc,char** argv) {
  try {
    const Args a=parse(argc,argv);
    // Block before writing any staged output: no arbitrary native-looking MET.
    cteas::puff::verify_native_p6_admission(
        a.p6_admission,a.p6_manifest,a.p6_driver,a.met,
        P7_EXPECTED_SOURCE_SHA,static_cast<int>(a.hours));
    require(cteas::puff::sha256_hex_file(a.control)==
             "cf5cca70cb75b1aac92f86fdc100500e901a8b904d056c73b2330175793532bc",
            "P7_NATIVE_LOCKED_PUFF_CONTROL_SHA256_MISMATCH");
    require(cteas::puff::sha256_hex_file(a.makegeo)==
             "e87b166346abe1c16136a790cda3acffdec6e29d9fb558ab2c9738ef426238b7",
            "P7_NATIVE_LOCKED_MAKEGEO_SHA256_MISMATCH");
    OutputPublication output(a.output);
    const auto control_text=read_text(a.control);
    const auto deck=ControlFile::read_file(a.control);
    // Scientific scope intentionally frozen: no rain and no other CALPUFF modes.
    require(deck.required_int("METFM")==1 &&
            deck.required_int("NPT1")==1 &&
            deck.required_int("NSPEC")==2 &&
            deck.required_int("MCTADJ")==2 &&
            deck.required_int("MDRY")==1 &&
            deck.required_int("MTRANS")==1 &&
            deck.required_int("MXSAM")==99 &&
            deck.required_int("IWET")==0,
            "P7_NATIVE_UNAPPROVED_PHYSICS_OR_SOURCE");
    const auto stack=deck.required_float_list("X");
    const auto factors=deck.required_float_list("FMFAC");
    const auto ymin=deck.required_float_list("SYMIN");
    const auto zmin=deck.required_float_list("SZMIN");
    const auto lengths=deck.required_float_list("XSAMLEN");
    const auto cdiv=deck.required_float_list("CDIV");
    require(stack.size()==10U&&factors.size()==1U&&ymin.size()==1U&&
            zmin.size()==1U&&lengths.size()==1U&&cdiv.size()==2U,
            "P7_NATIVE_UNAPPROVED_POINT_SOURCE_PARAMETERS");

    std::unique_ptr<ConcFileWriter> writer;
    std::unique_ptr<HourlyConcSeriesWriter> written_hours;
    OriginalCompRiseMultiPuffHours driver;
    std::size_t completed=0U,positive_values=0U,physical_steps=0U;
    double integrated_concentration=0.0;
    const auto calm=a.hours>6U ?
        std::optional<NativeCalmMdisp3Controls>(
            original_calm_mdisp3_from_decks(
                deck,ControlFile::read_file(a.makegeo))) :
        std::nullopt;
    const auto summary=OriginalMetHourlyReader::read(a.met,
      [&](const Calmet21Header& header,const Calmet21Static& statics,
          const OriginalMetHour& met) {
        if(completed==a.hours)return;
        const auto hour_index=completed;
        require(header.nx==50&&header.ny==50&&header.nz==9&&
                header.dx_m==100.0F&&
                header.origin_x_m==510885.0F &&
                header.origin_y_m==3531269.0F,
                "P7_NATIVE_GRID_ORIGIN_PRECISION_OR_SHAPE_MISMATCH");
        require(met.begin.year==2022 &&
                met.begin.julian_day==1+static_cast<int>(hour_index/24U) &&
                met.begin.hour==static_cast<int>(hour_index%24U) &&
                met.begin.seconds==0,
                "P7_NATIVE_MET_HOURLY_AXIS_MISMATCH");
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
        request.use_calmet_profile_lapse=true;
        const auto prfin=original_point_prfin_metfm1(
            met,statics,header,request);
        OriginalPointNativeSourceParameters native_source;
        native_source.base_elevation_m=static_cast<float>(stack[3]);
        native_source.met_spacing_m=header.dx_m;
        native_source.initial_sigma_y_m=static_cast<float>(ymin[0]);
        native_source.initial_sigma_z_m=static_cast<float>(zmin[0]);
        native_source.emission_rates={stack[8],stack[9]};
        const auto source=original_point_hour_from_prfin(
            request,prfin,native_source);
        require(source.mass.species_count==2 &&
                source.mass.emission_rate[0]==834000.0F &&
                source.mass.emission_rate[1]==0.0F,
                "P7_NATIVE_LOCKED_CASE_EMISSION_MISMATCH");

        NeutralCompControls controls;
        controls.met_spacing_m=header.dx_m;
        controls.max_sample_distance_cells=static_cast<float>(lengths[0]);
        controls.calm_threshold_ms=0.5F;
        controls.max_sampling_steps=99;
        controls.original_wdiv=NativeOriginalWdivControls{
            static_cast<float>(cdiv[0]),static_cast<float>(cdiv[1])};
        const auto terrain=OriginalNativeTerrain::from_calmet(
            statics,met.nx,met.ny,header.dx_m);
        NativeMctadj2Controls mctadj2;
        mctadj2.terrain=terrain.constraint_lookup();
        mctadj2.derive_bvf_from_metfm1=true;
        mctadj2.minimum_pt_gradient_k_per_m=0.005F;
        controls.mctadj2=mctadj2;
        controls.gaussian_dry=NativeGaussianDryControls{
            dry_deposition_setup_from_control(control_text),1.0F};
        if(calm)controls.calm_mdisp3=*calm;
        DispersionSetup pg;
        pg.mdisp=3;
        pg.averaging_factor=1;
        pg.sigma_y_heffter_m=550;
        pg.heffter_sigma_z=false;
        pg.roughness_adjustment=false;
        const auto receptors=receptors_from_original_met_grid(
            control_text,{header.origin_x_m,header.origin_y_m,header.dx_m});
        require(receptors.grid.size()==2500U&&receptors.sampling_nx==50&&
                receptors.sampling_ny==50&&receptors.mesh_down==1&&
                receptors.discrete.empty(),
                "P7_NATIVE_UNAPPROVED_RECEPTOR_GRID");
        const auto sampler=make_original_flat_calcpf_sampler(
            receptors,header.dx_m,3600.0F,3.0F,
            OriginalFlatVerticalMethod::receptor_pg_vcoup_mctadj2,
            [&terrain,&receptors](const RiseCompSamplingState& state,
                                 std::size_t receptor,const OriginalPuffct2Result& position){
                require(state.original_ctadj2_step.has_value() &&
                        state.receptor_effective_wind_ms>0.0F &&
                        std::isfinite(state.receptor_brunt_vaisala_s),
                        "P7_NATIVE_NONPHYSICAL_RECEPTOR_TERRAIN");
                return terrain.receptor(
                    receptor,receptors.ibsamp,receptors.jbsamp,
                    receptors.sampling_nx,receptors.sampling_ny,position,
                    state.receptor_brunt_vaisala_s,
                    state.receptor_effective_wind_ms);
            },true,{},0.0F);
        constexpr std::size_t capacity=300000U;
        const OriginalCompPuffBounds bounds{0.0F,50.0F,0.0F,50.0F};
        const auto hour=driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
            met,statics,controls,pg,false,source,bounds,
            capacity,2500U,sampler);
        require(driver.completed_hours()==hour_index+1U &&
                hour.hour_index==hour_index &&
                hour.receptor_concentrations.size()==2500U &&
                !hour.steps.empty(),
                "P7_NATIVE_HOUR_TRANSACTION_OR_CADENCE_FAILURE");
        if(!writer) {
            // Header is reconstructed from active control and MET; no
            // original CON bytes/records enter this writer.
            writer=create_original_hefei_2022_wrout1_writer(
                output.staged_path(),control_text,a.met,true,false);
            written_hours=std::make_unique<HourlyConcSeriesWriter>(
                *writer,original_total_source_descriptor(
                    header.origin_x_m,header.origin_y_m),50,50);
        }
        const int next_hour=(met.begin.hour+1)%24;
        const int next_day=met.begin.julian_day+(met.begin.hour==23?1:0);
        const ConcPeriod period{
            2022,met.begin.julian_day,met.begin.hour,0,
            2022,next_day,next_hour,0};
        written_hours->write_hour(period,hour.receptor_concentrations);
        for(const float c:hour.receptor_concentrations){
            require(std::isfinite(c)&&c>=0.0F,
                    "P7_NATIVE_INVALID_H3_CONCENTRATION");
            positive_values+=c>0.0F?1U:0U;
            integrated_concentration+=c;
        }
        require(driver.capacity_inventory().active_ids()==driver.canonical_ids() &&
                driver.active_count()==driver.canonical_ids().size() &&
                std::is_sorted(driver.canonical_ids().begin(),
                               driver.canonical_ids().end()),
                "P7_NATIVE_NONCANONICAL_PUFF_INVENTORY");
        physical_steps+=hour.steps.size();
        ++completed;
        std::cout<<"P7_NATIVE_HOUR_FINISHED="<<completed
                 <<" SUBSTEPS="<<hour.steps.size()
                 <<" ACTIVE="<<driver.active_count()
                 <<" POSITIVE_ACCUMULATED="<<positive_values<<"\n";
      },true);
    require(summary.intervals==143U&&completed==a.hours&&
            driver.completed_hours()==a.hours &&
            writer!=nullptr&&written_hours!=nullptr &&
            written_hours->hours_written()==a.hours&&
            writer->records_written()==6U+3U*a.hours&&
            positive_values>0U&&std::isfinite(integrated_concentration)&&
            integrated_concentration>0.0,
            "P7_NATIVE_INCOMPLETE_HOURS_OR_ALL_ZERO_H3");
    writer->close();
    output.publish();
    require(std::filesystem::is_regular_file(a.output) &&
            std::filesystem::file_size(a.output)>10000U,
            "P7_NATIVE_WRITER_PUBLISHED_EMPTY_CON");
    std::cout<<std::setprecision(17)
             <<"P7_NATIVE_NO_ORIGINAL_CON_DGM=PASS"
             <<" HOURS="<<completed
             <<" H3_VALUES="<<completed*2500U
             <<" POSITIVE_VALUES="<<positive_values
             <<" PHYSICAL_STEPS="<<physical_steps
             <<" INTEGRATED_H3_BQ_M3="<<integrated_concentration
             <<" OUTPUT_BYTES="<<std::filesystem::file_size(a.output)
             <<" PRODUCER=CTEAS_P7_NATIVE_HEFEI_2022"
             <<" SCIENTIFIC_PARITY=NOT_EVALUATED\n";
    return 0;
  } catch(const std::exception& e) {
    std::cerr<<"P7_NATIVE_EXECUTION=FAIL "<<e.what()<<"\n";
    return 2;
  }
}
