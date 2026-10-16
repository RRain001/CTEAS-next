// Original-CALPUFF six consecutive real Hefei MET hours: live native COMP,
// capacity inventory, and CALCPF at original REAL4 precision. No native state
// is seeded from vendor output or original DGM. Original puff.con is read
// exclusively AFTER each native hour has been independently advanced.
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

#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

using namespace cteas::puff;
namespace {
void require(bool good,const char* message){
    if(!good)throw std::runtime_error(message);
}
std::string bytes(const char* path) {
    std::ifstream file(path,std::ios::binary);
    require(bool(file),"frozen source file missing");
    return {std::istreambuf_iterator<char>(file),
            std::istreambuf_iterator<char>()};
}
struct OriginalDgmStep {
    std::array<std::int32_t,24> integers{};
    std::array<float,64> reals{};
};
static_assert(sizeof(OriginalDgmStep)==352U);
static_assert(std::endian::native==std::endian::little);
std::vector<OriginalDgmStep> read_original_dgm(const std::string& path, bool full_143h) {
    std::ifstream input(path,std::ios::binary);
    require(bool(input),"original pinned sixhour DGM oracle missing");
    std::vector<OriginalDgmStep> rows;
    OriginalDgmStep row;
    while(input.read(reinterpret_cast<char*>(&row),sizeof(row)))
        rows.push_back(row);
    require(input.eof() && input.gcount()==0 &&
                rows.size()==(full_143h?254687U:11458U),
            "original frozen DGM row count or record length drifted");
    return rows;
}
bool equal_real4(float a,float b) {
    return std::bit_cast<std::uint32_t>(a)==std::bit_cast<std::uint32_t>(b);
}
} // namespace

int main(int argc,char** argv) {
  try {
    require(argc>=4 && argc<=8,
            "usage: sixhour_real_h3 MET.DAT puff.inp puff.con [original-DGM.bin] [hour2-25-28.tsv] [hour4-47-13.tsv] [native-puff200-mass.tsv]");
    require(argc<6 || std::string(argv[4]).size()>0U,
            "hour2 CALCPF trace requires an original DGM provenance input");
    // The accepted six-hour strict gate remains the DEFAULT. Longer
    // source-first probes are explicit opt-ins, never silent acceptance.
    // Explicit integration opt-in, never used by the immutable original-MET gate.
    const char* integration_mode=std::getenv("CTEAS_P7_INTEGRATION_C1");
    const bool coupling_c1=integration_mode && std::string(integration_mode)=="1";
    const char* c2_mode=std::getenv("CTEAS_P7_INTEGRATION_C2");
    const bool coupling_c2=c2_mode && std::string(c2_mode)=="1";
    require(!(coupling_c1 && coupling_c2),"only one coupling mode may be active");
    const bool coupling_candidate=coupling_c1 || coupling_c2;
    const int nx_expected=coupling_c2?12:50;
    const int ny_expected=coupling_c2?12:50;
    const float dx_expected=coupling_c2?10000.0F:100.0F;
    const int met_year_expected=coupling_c2?2024:2022;
    const int met_first_hour=coupling_c2?2:0;
    const std::size_t field_count=static_cast<std::size_t>(nx_expected)*ny_expected;
    const char* extended=std::getenv("CTEAS_P7_PROBE_HOURS");
    std::size_t probe_hours=6U;
    if(extended){
        char* end=nullptr;
        const long requested=std::strtol(extended,&end,10);
        require(end && end!=extended && *end=='\0' &&
                requested>=7L && requested<=143L,
                "CTEAS_P7_PROBE_HOURS must be a whole number in 7..143");
        probe_hours=static_cast<std::size_t>(requested);
    }
    // Optional native stage trace (argv[5]) must never disable the
    // independent original DGM step oracle carried in argv[4].
    require(probe_hours==6U || argc>=5 || coupling_candidate,
            "extended source probe requires the FULL original 143h DGM file");
    const auto dgm=(argc>=5 && !coupling_candidate)?read_original_dgm(argv[4],probe_hours>6U):
                           std::vector<OriginalDgmStep>{};
    require(coupling_candidate || argc!=6 || !dgm.empty(),
            "hour2 source trace must retain pinned original sixhour DGM gate");
    // Source order: strict GETCELL for pre-step puff centre, original
    // GRIDIJ clamping for the mid/end meteorological cell after movement.
    // A boundary crossing is sampled and retired by COMP, not aborted by
    // an inappropriately strict midpoint lookup.
    const auto mid=original_met_cell_clamped(18.251936F,50.00001F,50,50);
    require(mid.ix_1based==19 && mid.iy_1based==50 &&
            mid.offset_0based==2468U,
            "CALPUFF GETCELL outer-edge midpoint mapped to wrong REAL4 cell");
    bool strict_rejects=false;
    try {
        (void)original_met_cell(18.251936F,50.00001F,50,50);
    } catch(const std::out_of_range&) {strict_rejects=true;}
    require(strict_rejects,
            "original COMP start cell unexpectedly accepts out-of-grid puffs");
    const auto control=bytes(argv[2]);
    // Optional complete source-derived WROUT1 output. The output writer
    // consumes the live native COMP receptor field; it never consumes the
    // frozen puff.con field or original DGM as a state input.
    const char* original_con_output=std::getenv("CTEAS_P7_NATIVE_PUFF_CON");
    std::unique_ptr<ConcFileWriter> native_con_writer;
    std::unique_ptr<HourlyConcSeriesWriter> native_con_hours;
    if(original_con_output && *original_con_output)
        native_con_writer=create_original_hefei_2022_wrout1_writer(
            original_con_output,control,argv[1],coupling_candidate,coupling_c2);
    const auto deck=ControlFile::read_file(argv[2]);
    std::optional<NativeCalmMdisp3Controls> genuine_calm;
    if(probe_hours>6U || coupling_c2){
        // C2 must use the same source-derived XMINZI/XMAXZI and
        // midpoint COMP meteorology even in the first six-hour probe.
        // The old frozen 2022 six-hour science path remains unchanged.
        const char* makegeo=std::getenv("CTEAS_P7_MAKEGEO_INP");
        require(makegeo!=nullptr && *makegeo!='\0',
                "real extended calm trace requires original MAKEGEO control");
        genuine_calm=original_calm_mdisp3_from_decks(
            deck,ControlFile::read_file(makegeo));
        std::cout<<"P7_REAL_EXTENDED_CALM_SOURCE_DECK=PASS"
                 <<" IWAT1="<<genuine_calm->iwat1
                 <<" IWAT2="<<genuine_calm->iwat2<<"\n";
    }
    require(deck.required_int("METFM")==1 &&
            deck.required_int("NPT1")==1 &&
            deck.required_int("NSPEC")==2 &&
            deck.required_int("MCTADJ")==2 &&
            deck.required_int("MDRY")==1 &&
            deck.required_int("MTRANS")==1 &&
            deck.required_int("MXSAM")==99,
            "unapproved frozen 2022 CALPUFF controls");
    const auto original=read_conc_species_fields(argv[3],nx_expected,ny_expected);
    // Original WROUT1 emits 143 H-3 concentration fields. Its 286
    // period/grid descriptors are NOT 286 species fields; HE-3 is a
    // modeled species in NSPEC=2 but has no concentration OUTPUT record.
    require(original.size()==143U &&
            original.front().species_index==1 &&
            original.front().label.find("H-3")!=std::string::npos,
            "original 143-hour H3/HE3 concentration oracle changed");
    const auto stack=deck.required_float_list("X");
    const auto factors=deck.required_float_list("FMFAC");
    const auto ymin=deck.required_float_list("SYMIN");
    const auto zmin=deck.required_float_list("SZMIN");
    const auto lengths=deck.required_float_list("XSAMLEN");
    const auto cdiv=deck.required_float_list("CDIV");
    require(stack.size()==10U&&factors.size()==1U&&ymin.size()==1U&&
            zmin.size()==1U&&lengths.size()==1U&&cdiv.size()==2U,
            "original point-source or dispersion source fields missing");

    // ONE instance owns all six meteorological hours and all puff state.
    OriginalCompRiseMultiPuffHours driver;
    // Pinned write-only original Fortran DGM metadata, verified against
    // dgm_puffstep.json SHA cbbdaa29c6222e6ca6aefe9f605ad13e7dd6d258f6ad243afcac07cb578108c6.
    // These values validate scheduling AFTER native execution; they never
    // supply puff states, winds, positions, mass or source parameters.
    constexpr std::array<std::size_t,6> original_hour_steps{
        1275U,2242U,1906U,2132U,1742U,2161U};
    constexpr std::array<int,6> original_first_puff{
        1,22,113,183,247,314};
    constexpr std::array<int,6> original_last_puff{
        54,137,208,272,337,417};
    std::size_t completed=0U,matching_words=0U,physical_steps=0U;
    std::size_t matched_step_keys=0U,matched_new_xy=0U;
    std::size_t matched_stored_sigy=0U,matched_stored_sigz=0U;
    std::size_t first_dgm_mismatch_record=0U;
    std::string first_dgm_mismatch_field;
    struct NativeH3ReceptorRow {
        int episode=0;
        float time_before=0.0F,time_after=0.0F;
        OriginalCalcpfReceiverIntermediate values;
    };
    std::size_t original_hour2_trace_rows=0U;
    bool every_hour_real4=true;
    std::size_t first_mismatched_hour=0U,first_mismatched_cell=0U;
    const auto summary=OriginalMetHourlyReader::read(argv[1],
       [&](const Calmet21Header& header,const Calmet21Static& static_met,
           const OriginalMetHour& met) {
        if(completed>=probe_hours)return;
        const std::size_t hour_index=completed;
        require(met.begin.year==met_year_expected &&
                met.begin.hour==static_cast<int>((hour_index+met_first_hour)%24U) &&
                met.begin.julian_day==1+static_cast<int>((hour_index+met_first_hour)/24U) &&
                header.nx==nx_expected&&header.ny==ny_expected&&header.nz==9&&
                header.dx_m==dx_expected,
                "Hefei consecutive original MET time/grid drift");
        if(hour_index>=6U) {
            require(coupling_candidate || (matching_words==field_count*hour_index &&
                    first_mismatched_hour==0U &&
                    matched_step_keys==physical_steps &&
                    matched_new_xy==physical_steps &&
                    matched_stored_sigy==physical_steps &&
                    matched_stored_sigz==physical_steps),
                    "extended probe cannot bypass preceding contiguous REAL4 gate");
            std::cout<<"P7_REAL_EXTENDED_PROBE_ENTER_HOUR="<<hour_index+1U
                     <<" ACTIVE_BEFORE="<<driver.active_count()
                     <<" ORIGINAL_FULL_DGM_ROWS="<<dgm.size()<<"\n";
        }
        const auto active_before=driver.canonical_ids();
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
        // Selected frozen CALMET METFM1 case: use actual 3D TMET/ZFACE
        // for original RLSMET LCALGRD=true stable source, never DGM values.
        request.use_calmet_profile_lapse=true;
        const auto prfin=original_point_prfin_metfm1(
            met,static_met,header,request);
        // Read-only first unsupported POINTS1 source admission at real H9.
        // Report the native original-scoped PRFIN branch's exact physics
        // rather than relaxing it or seeding it from the vendor DGM.
        if(hour_index>=8U) {
            const auto src_cell=original_met_cell(
                request.x_cells,request.y_cells,met.nx,met.ny);
            std::cout<<std::setprecision(10)
                     <<"P7_REAL_EXTENDED_PRFIN_INPUT"
                     <<" HOUR="<<hour_index+1U
                     <<" SRC_CELL0="<<src_cell.offset_0based
                     <<" PGT="<<met.ipgt.at(src_cell.offset_0based)
                     <<" SQRTS="<<prfin.sqrt_stability_s
                     <<" LCALGRD_MET_PROFILE="<<request.use_calmet_profile_lapse
                     <<" TEMP="<<prfin.ambient_temperature_k
                     <<" PBL="<<prfin.mixing_height_m
                     <<" STACK_WIND="<<prfin.stack_wind_ms
                     <<" HEFF_WIND="<<prfin.effective_wind_ms
                     <<" RELEASE_WIND="<<prfin.release_wind_ms
                     <<" HEFF="<<prfin.effective_height_m
                     <<" STACK_HEIGHT="<<request.stack_height_m
                     <<" XFINAL="<<prfin.x_final_m
                     <<" RISE="<<prfin.final_rise_m
                     <<" BUOYANCY="<<prfin.buoyancy_flux
                     <<" MOMENTUM="<<prfin.momentum_flux
                     <<" BIDSQ="<<prfin.buoyancy_variance_m2
                     <<" NEWPUFFS="<<prfin.release.puff_count
                     <<"\n";
        }
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
                "Hefei native source emission parameters changed");

        NeutralCompControls controls;
        controls.met_spacing_m=header.dx_m;
        controls.max_sample_distance_cells=static_cast<float>(lengths[0]);
        controls.calm_threshold_ms=0.5F;
        controls.max_sampling_steps=99;
        controls.original_wdiv=NativeOriginalWdivControls{
            static_cast<float>(cdiv[0]),static_cast<float>(cdiv[1])};
        const auto terrain=OriginalNativeTerrain::from_calmet(
            static_met,met.nx,met.ny,header.dx_m);
        NativeMctadj2Controls mctadj2;
        mctadj2.terrain=terrain.constraint_lookup();
        mctadj2.derive_bvf_from_metfm1=true;
        mctadj2.minimum_pt_gradient_k_per_m=0.005F;
        controls.mctadj2=mctadj2;
        controls.gaussian_dry=NativeGaussianDryControls{
            dry_deposition_setup_from_control(control),1.0F};
        if(genuine_calm)controls.calm_mdisp3=*genuine_calm;
        DispersionSetup pg;
        pg.mdisp=3;
        pg.averaging_factor=1;
        pg.sigma_y_heffter_m=550;
        pg.heffter_sigma_z=false;
        pg.roughness_adjustment=false;
        const auto receptors=receptors_from_original_met_grid(
            control,{header.origin_x_m,header.origin_y_m,header.dx_m});
        require(receptors.grid.size()==field_count&&receptors.sampling_nx==nx_expected&&
                receptors.sampling_ny==ny_expected&&receptors.mesh_down==1&&
                receptors.discrete.empty(),"sixhour native receptor frame drift");

        const char* c2_receiver_path=std::getenv("CTEAS_P7_C2_H1_RECEIVER_TRACE");
        const bool trace_c2_h1=coupling_c2 && hour_index==0U &&
            c2_receiver_path && *c2_receiver_path;
        std::ofstream c2_receiver_file;
        if(trace_c2_h1) {
            c2_receiver_file.open(c2_receiver_path,std::ios::trunc);
            require(bool(c2_receiver_file),"C2 native receiver trace could not open");
            c2_receiver_file<<std::setprecision(17);
        }
        const bool trace_this_hour=
            (argc>=6 && hour_index==1U) ||
            (argc>=7 && hour_index==3U);
        // First new physical failure after strict H1-H8: H9 i=13,j=1.
        // Original source emits NO CALCPF receiver-stage rows for this cell.
        // Trace native CALCPF events without changing any sampler arithmetic.
        // Next H9 first residual following exact (21,1) source parity.
        // Extra H9 stage diagnostics are optional; strict 24h/48h gates
        // must not require a debug file path to prove physical parity.
        const char* h9_trace_path=std::getenv("CTEAS_P7_H9_RECEIVER_TRACE");
        const bool trace_h9_cell24=hour_index==8U && probe_hours>=9U &&
            h9_trace_path && *h9_trace_path;
        // The formerly first H9 receptor (25,1) remains the default; the
        // selected physical first-difference receptor can be traced without
        // editing production sampling or the preexisting accepted gates.
        std::size_t h9_trace_index=24U;
        if(trace_h9_cell24) {
            if(const char* target=std::getenv("CTEAS_P7_H9_RECEIVER_CELL0")) {
                char* end=nullptr;
                const long index=std::strtol(target,&end,10);
                require(end && end!=target && *end=='\0' &&
                        index>=0L && index<2500L,
                        "H9 receiver trace cell must be a 0-based 50x50 index");
                h9_trace_index=static_cast<std::size_t>(index);
            }
        }
        const std::size_t trace_cell=trace_c2_h1 ? 63U :
            (trace_h9_cell24 ? h9_trace_index :
             (hour_index==1U?1374U:646U));
        std::vector<NativeH3ReceptorRow> trace_rows;
        OriginalCalcpfIntermediateHook stage_hook;
        if(trace_this_hour || trace_h9_cell24 || trace_c2_h1) {
            stage_hook=[&trace_rows,trace_cell,trace_h9_cell24,
                        trace_c2_h1,&c2_receiver_file](
                const RiseCompSamplingState& state,
                const OriginalCalcpfReceiverIntermediate& row){
                if(row.receptor_index!=trace_cell)return;
                if(trace_c2_h1) {
                    // Diagnostic only: real native CALCPF receptor source
                    // terms, written AFTER source-faithful computation.
                    // Never read this file to advance COMP/P7 state.
                    const auto& r=row;
                    c2_receiver_file<<"P7_C2_NATIVE_RECEIVER"
                        <<" puff="<<state.puff_id
                        <<" code="<<state.vmass.puff_code
                        <<" x_begin="<<state.before.x_cells
                        <<" y_begin="<<state.before.y_cells
                        <<" x_end="<<state.after.x_cells
                        <<" y_end="<<state.after.y_cells
                        <<" z_begin="<<state.before.z_m
                        <<" z_end="<<state.after.z_m
                        <<" lid="<<state.vmass.reflecting_lid_m
                        <<" ziold="<<state.vmass.ziold_m
                        <<" zimax="<<state.vmass.zimax_m
                        <<" frac="<<r.receptor_fraction
                        <<" sy="<<r.sigma_y_m
                        <<" sz="<<r.sigma_z_m
                        <<" zpr="<<r.puff_height_m
                        <<" zrpole="<<r.receptor_pole_m
                        <<" f1="<<r.vertical_factor
                        <<" xi1="<<r.xi1<<" xi2="<<r.xi2
                        <<" t1="<<r.t1<<" t2="<<r.t2
                        <<" qold="<<r.qold<<" qnew="<<r.qnew
                        <<" vdpvd="<<state.receptor_deposition_ratio
                        <<" xtemp="<<r.xtemp<<" conc="<<r.concentration
                        <<" travel_begin="<<state.before.travel_time_s
                        <<" travel_end="<<state.after.travel_time_s
                        <<"\n";
                    if(!c2_receiver_file)
                        throw std::runtime_error("C2 native receiver trace write failed");
                }
                if(trace_h9_cell24 && trace_cell==24U && state.puff_id==594) {
                    require(state.receptor_calm_sigma.has_value(),
                            "H9 source residual requires native LCALM CSIGMA");
                    const auto& v=state.sigmas.step;
                    // Exact PUFRECS L5252/L5253 source grouping, after
                    // LCALM has forced receptor fraction to 0.5.
                    const float vtz=std::max(0.0F,
                        static_cast<float>(v.virtual_time_z_begin_s)+
                        0.5F*(static_cast<float>(v.virtual_time_z_end_s)-
                              static_cast<float>(v.virtual_time_z_begin_s)));
                    const float vdz=std::max(0.0F,
                        static_cast<float>(v.virtual_distance_z_begin_km)+
                        0.5F*(static_cast<float>(v.virtual_distance_z_end_km)-
                              static_cast<float>(v.virtual_distance_z_begin_km)));
                    auto sigma=*state.receptor_calm_sigma;
                    sigma.sy0=0.0F;
                    sigma.sz0=0.0F;
                    sigma.dt_s=vtz;
                    sigma.dx_km=vdz;
                    const float szar=original_calm_sigma(sigma).sz;
                    const float addbid=static_cast<float>(
                        state.receptor_buoyancy_variance_m2);
                    const float rawsz=addbid>0.0F ?
                        std::sqrt(szar*szar+addbid) : szar;
                    const float floor=static_cast<float>(
                        state.receptor_minimum_sigma_z_m);
                    std::cout<<std::setprecision(10)
                        <<"P7_NATIVE_H9_RECEPTOR_SIGTZ_INPUT"
                        <<" PUFF="<<state.puff_id
                        <<" FRACTION=0.5"
                        <<" VTZ="<<vtz<<" VDZ="<<vdz
                        <<" VTZB="<<static_cast<float>(v.virtual_time_z_begin_s)
                        <<" VTZE="<<static_cast<float>(v.virtual_time_z_end_s)
                        <<" VDZB="<<static_cast<float>(v.virtual_distance_z_begin_km)
                        <<" VDZE="<<static_cast<float>(v.virtual_distance_z_end_km)
                        <<" ZB1="<<state.before.z_m
                        <<" SIGW="<<sigma.sigw
                        <<" EL="<<sigma.el
                        <<" TZISDR="<<sigma.tzisdr
                        <<" UAVG="<<sigma.uavg
                        <<" SZAR="<<szar
                        <<" ADDBID="<<addbid
                        <<" RAW_SQRT="<<rawsz
                        <<" SZ0_FLOOR="<<floor
                        <<" FLOOR_APPLIED="<<(rawsz<floor?1:0)
                        <<" SZREC="<<row.sigma_z_m
                        <<" BIT_VTZ=0x"<<std::hex<<std::bit_cast<std::uint32_t>(vtz)
                        <<" BIT_SZAR=0x"<<std::bit_cast<std::uint32_t>(szar)
                        <<std::dec
                        <<" ORIGINAL_H9_INPUT_PARITY=TO_BE_COMPARED\n";
                }
                trace_rows.push_back({state.puff_id,
                    state.before.travel_time_s,state.after.travel_time_s,row});
            };
        }
        const auto sampling=make_original_flat_calcpf_sampler(
            receptors,header.dx_m,3600.0F,3.0F,
            OriginalFlatVerticalMethod::receptor_pg_vcoup_mctadj2,
            [&terrain,&receptors,hour_index,trace_cell](
                const RiseCompSamplingState& state,
                std::size_t receiver,const OriginalPuffct2Result& pos){
                require(state.original_ctadj2_step.has_value() &&
                        state.receptor_effective_wind_ms>0.0F &&
                        std::isfinite(state.receptor_brunt_vaisala_s),
                        "Hefei receptor terrain state is not native");
                const auto t=terrain.receptor(
                    receiver,receptors.ibsamp,receptors.jbsamp,
                    receptors.sampling_nx,receptors.sampling_ny,pos,
                    state.receptor_brunt_vaisala_s,
                    state.receptor_effective_wind_ms);
                // H9 first real receptor residual (42,11): print native
                // MCTADJ2 operands in REAL4. Pure read-only provenance; do
                // not change terrain, sampler, or original stage arithmetic.
                if(hour_index==8U && receiver==trace_cell) {
                    const float dsel=t.brunt_vaisala_s>0.0F ?
                        t.terrain_peak_elevation_msl-
                        t.wind_speed_ms/t.brunt_vaisala_s : 0.0F;
                    const float dsh=std::max(0.0F,dsel-
                        t.terrain_under_puff_msl);
                    const float zdiff=t.receptor_ground_elevation_msl-dsel;
                    std::cout<<std::setprecision(10)
                        <<"P7_NATIVE_H9_MCTADJ2_TERRAIN"
                        <<" PUFF="<<state.puff_id
                        <<" RECEIVER_I="<<(receiver%50U+1U)
                        <<" RECEIVER_J="<<(receiver/50U+1U)
                        <<" X="<<pos.x_m<<" Y="<<pos.y_m
                        <<" PUFFZ="<<pos.z_m
                        <<" ELEV="<<t.receptor_ground_elevation_msl
                        <<" TOP="<<t.terrain_peak_elevation_msl
                        <<" UNDER="<<t.terrain_under_puff_msl
                        <<" BVF="<<t.brunt_vaisala_s
                        <<" UAVG="<<t.wind_speed_ms
                        <<" POLE0="<<t.receptor_height_m
                        <<" DSEL="<<dsel<<" DSH="<<dsh
                        <<" ZDIFF="<<zdiff
                        <<" BIT_DSEL=0x"<<std::hex
                        <<std::bit_cast<std::uint32_t>(dsel)<<std::dec
                        <<" SOURCE_PARITY=NOT_YET_VERIFIED\n";
                }
                return t;
            },true,stage_hook,0.0F);
        // The pinned vendor params.puf sets MXPUFF=300000 (the preceding
        // 100000 assignment is commented out). An artificial 4096-slot
        // limit would force premature ROLLDN on a real multi-day run and
        // invalidate original COMP episode/slot authority comparisons.
        // Source-capacity pressure remains a separate small-MXPUFF test.
        constexpr std::size_t kOriginalVendorMxPuff=300000U;
        const OriginalCompPuffBounds bounds{0.0F,static_cast<float>(nx_expected),
            0.0F,static_cast<float>(ny_expected)};
        const auto hour=driver.advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled(
            met,static_met,controls,pg,false,source,bounds,
            kOriginalVendorMxPuff,field_count,sampling);
        require(driver.completed_hours()==hour_index+1U &&
                hour.hour_index==hour_index &&
                hour.receptor_concentrations.size()==field_count &&
                hour.steps.size()>0U,
                "real sixhour COMP hour transaction/cadence invalid");
        if(native_con_writer) {
            if(!native_con_hours)
                native_con_hours=std::make_unique<HourlyConcSeriesWriter>(
                    *native_con_writer,
                    original_total_source_descriptor(
                        header.origin_x_m,header.origin_y_m),nx_expected,ny_expected);
            // CALMET.DAT encodes the end of a one-hour interval with
            // boundary-style hour/seconds fields that need not satisfy the
            // WROUT1 convention of canonical YYYYJJJ HH:00 endpoints.
            // Original WROUT1 advances the begin timestamp by one whole
            // hour. Reconstruct that clock from independent MET begin,
            // not from frozen puff.con values or an output oracle.
            require(met.begin.seconds==0 &&
                    met.begin.year==met_year_expected &&
                    met.begin.julian_day>=1 &&
                    met.begin.julian_day<=(coupling_c2?7:6),
                    "native WROUT1 requires frozen hourly MET begin clock");
            const int next_hour=(met.begin.hour+1)%24;
            const int next_day=met.begin.julian_day+
                (met.begin.hour==23?1:0);
            const ConcPeriod period{
                met.begin.year,met.begin.julian_day,met.begin.hour,0,
                met.begin.year,next_day,next_hour,0};
            // Prevalidated contiguous 1h records: no oracle field supplied.
            native_con_hours->write_hour(period,hour.receptor_concentrations);
        }
        // Keep an original-source H9 puff598 history independent of any
        // gridded CALCPF receiver: QOLD after VMASS and QNEW after DRY.
        // The original stage trace records these at COMP L10965/L11108.
        if(hour_index==8U) {
            const char* trace=std::getenv("CTEAS_P7_H9_PUFF598_MASS_TRACE");
            if(trace && *trace) {
                std::ofstream out(trace,std::ios::binary);
                require(bool(out),"cannot open H9 puff598 mass diagnostic");
                out<<std::setprecision(9);
                std::size_t rows=0;
                for(std::size_t n=0;n<hour.steps.size();++n){
                    const auto& st=hour.steps[n];
                    if(st.puff_id!=598)continue;
                    const auto& step=st.step;
                    require(!step.pre_dry_qold_mixed.empty() &&
                            !step.vmass.mass_mixed.empty() &&
                            step.dry.has_value() &&
                            !step.dry->fraction_remaining.empty() &&
                            step.dry_input_resistance.has_value() &&
                            !step.dry_input_resistance->velocity_ms.empty(),
                            "H9 puff598 native QOLD/DRY provenance missing");
                    out<<physical_steps+n+1U<<" "<<st.puff_id<<" "
                       <<st.ksam<<" "<<step.pre_dry_qold_mixed[0]<<" "
                       <<step.vmass.mass_mixed[0]<<" "
                       <<step.dry->fraction_remaining[0]<<" "
                       <<step.dry_input_resistance->velocity_ms[0]<<" "
                       <<step.substep.step_s<<"\n";
                    // VCBAR uses the current SETPUF /CURRENT/ endpoints
                    // and vertical sigmas, not historical puff state.
                    const auto& zz=step.sigma.adjust;
                    std::cout<<std::setprecision(10)
                             <<"P7_NATIVE_H9_PUFF598_VCBAR"
                             <<" SEQ="<<physical_steps+n+1U
                             <<" KSAM="<<st.ksam
                             <<" VCBAR="<<step.dry->vcbar_m_inverse
                             <<" ZB="<<step.before.z_m
                             <<" ZE="<<step.after.z_m
                             <<" SZB="<<zz.sigma_z_begin_m
                             <<" SZM="<<zz.sigma_z_mid_m
                             <<" SZE="<<zz.sigma_z_end_m
                             <<" LID="<<step.vmass.reflecting_lid_m
                             <<" FRACDRY="<<step.dry->fraction_remaining[0]
                             <<" READ_ONLY=YES\n";
                    ++rows;
                }
                out.flush();
                require(bool(out)&&rows>=8U,
                        "H9 puff598 native mass trace missing history");
                std::cout<<"P7_NATIVE_H9_PUFF598_MASS_TRACE=SOURCE_ONLY"
                         <<" STEPS="<<rows
                         <<" ORIGINAL_MASS_PARITY=NOT_YET_COMPARED\n";
            }
        }
        // Keep the previously accepted H9 source-regression mandatory,
        // even when no optional receptor trace has been requested.
        if(hour_index==8U && !coupling_candidate) {
            require(equal_real4(hour.receptor_concentrations.at(12),
                                original.at(hour_index).values.at(12)),
                    "H9 calm PUFRECS former cell12 source regression");
        }
        if(trace_h9_cell24) {
            std::ofstream stage_file(h9_trace_path,std::ios::binary);
            require(bool(stage_file),"H9 native receptor stage output unavailable");
            stage_file<<std::setprecision(9);
            std::size_t total=0U;
            for(const auto& record:trace_rows) {
                std::size_t found=hour.steps.size();
                for(std::size_t n=0;n<hour.steps.size();++n){
                    const auto& step=hour.steps[n];
                    if(step.puff_id==record.episode &&
                       step.step.before.travel_time_s==record.time_before &&
                       step.step.after.travel_time_s==record.time_after){
                        require(found==hour.steps.size(),
                                "H9 CALCPF native substep key ambiguous");
                        found=n;
                    }
                }
                require(found<hour.steps.size(),
                        "H9 CALCPF native episode missing from COMP");
                const auto& v=record.values;
                stage_file<<physical_steps+found+1U<<" "
                    <<record.episode<<" "<<hour.steps[found].ksam<<" "
                    <<v.sigma_y_m<<" "<<v.sigma_z_m<<" "
                    <<v.puff_height_m<<" "<<v.receptor_pole_m<<" "
                    <<v.vertical_factor<<" "<<v.xi1<<" "<<v.xi2<<" "
                    <<v.t1<<" "<<v.t2<<" "<<v.qold<<" "<<v.qnew<<" "
                    <<v.xtemp<<" "<<v.concentration<<"\n";
                total++;
            }
            stage_file.flush();
            require(bool(stage_file),"H9 native receiver stages not flushed");
            std::cout<<std::setprecision(10)
                     <<"P7_REAL_H9_NATIVE_CALCPF_FIRST_DIFFERENT_CELL"
                     <<" GRID_I="<<(trace_cell%50U+1U)
                     <<" GRID_J="<<(trace_cell/50U+1U)
                     <<" SOURCE_RECEPTOR_CELL12_PARITY=PASS"
                     <<" STAGE_RECORDS="<<total
                     <<" NATIVE_HOURLY_CELL_CONC="
                     <<hour.receptor_concentrations.at(trace_cell)
                     <<" ORIGINAL_HOURLY_CELL_CONC="
                     <<original.at(hour_index).values.at(trace_cell)
                     <<" ORIGINAL_STAGE_PARITY=NOT_YET_COMPARED\n";
        }
        if(hour_index<6U && !coupling_candidate)
            require(hour.steps.size()==original_hour_steps[hour_index] &&
                    hour.steps.front().puff_id==original_first_puff[hour_index] &&
                    hour.steps.back().puff_id==original_last_puff[hour_index],
                    "real COMP old/new puff chronology differs from pinned original DGM");
        if(!dgm.empty()) {
            for(std::size_t n=0;n<hour.steps.size();++n){
                const std::size_t global=physical_steps+n;
                const auto& ref=dgm.at(global);
                const auto& stage=hour.steps[n];
                // Read-only source-aligned native VDCOMP inputs at the first
                // original puff200 foliage resistance disagreement (DGM #5823).
                if(global+1U==5823U){
                    require(stage.puff_id==200 && stage.ksam==2 &&
                            stage.step.dry_input_resistance.has_value() &&
                            controls.gaussian_dry.has_value(),
                            "native #5823 source key or DRY provenance missing");
                    const auto cell=stage.step.initial_met.cell.offset_0based;
                    const auto midpoint=original_met_cell_clamped(
                        0.5F*(stage.step.before.x_cells+
                              stage.step.after.x_cells),
                        0.5F*(stage.step.before.y_cells+
                              stage.step.after.y_cells),met.nx,met.ny);
                    const auto endpoint=original_met_cell_clamped(
                        stage.step.after.x_cells,stage.step.after.y_cells,
                        met.nx,met.ny);
                    const float t=met.tempk.at(cell);
                    const float sw=met.qsw.at(cell);
                    const float pd=static_cast<float>(
                        controls.gaussian_dry->setup.diffusivity_m2_s.at(0));
                    const float fr=std::max(0.0F,std::min(1.0F,sw/600.0F));
                    const float opening=t>308.0F?2.5e-6F:
                        t<283.0F?0.1e-6F:
                        2.5e-6F*fr+0.1e-6F*(1.0F-fr);
                    const float rs=2.3e-8F/(opening*pd);
                    const float native_rf=static_cast<float>(
                        stage.step.dry_input_resistance->
                            foliage_resistance_s_m.at(0));
                    std::cout<<std::setprecision(10)
                        <<"P7_NATIVE_VDCOMP5823"
                        <<" CELL0="<<cell
                        <<" MID_CELL0="<<midpoint.offset_0based
                        <<" MID_TEMPK="<<met.tempk.at(midpoint.offset_0based)
                        <<" MID_QSW="<<met.qsw.at(midpoint.offset_0based)
                        <<" END_CELL0="<<endpoint.offset_0based
                        <<" END_TEMPK="<<met.tempk.at(endpoint.offset_0based)
                        <<" END_QSW="<<met.qsw.at(endpoint.offset_0based)
                        <<" TEMPK="<<t<<" QSW="<<sw
                        <<" PDIFF="<<pd<<" B="<<opening
                        <<" RS="<<rs<<" RF="<<native_rf
                        <<" BIT_T=0x"<<std::hex<<std::bit_cast<std::uint32_t>(t)
                        <<" BIT_QSW=0x"<<std::bit_cast<std::uint32_t>(sw)
                        <<" BIT_PDIFF=0x"<<std::bit_cast<std::uint32_t>(pd)
                        <<" BIT_B=0x"<<std::bit_cast<std::uint32_t>(opening)
                        <<" BIT_RS=0x"<<std::bit_cast<std::uint32_t>(rs)
                        <<std::dec<<" ORIGINAL_VDCOMP_INPUT_PARITY=TO_BE_COMPARED"
                        <<"\n";
                }
                // Pinned original SETPUF #3874: record the native CTADJ2
                // end calculation even after full SIGZ parity is achieved.
                if(global+1U==3874U){
                    require(stage.step.sigma.terrain.has_value() &&
                            stage.puff_id==138 && stage.ksam==23,
                            "original CTADJ2 DGM3874 physical key missing");
                    const auto& t=*stage.step.sigma.terrain;
                    std::cout<<std::setprecision(10)
                        <<"P7_HEFEI_6H_NATIVE_SETPUF_END_DGM3874"
                        <<" RECORD=3874"
                        <<" R="<<t.end_ratio
                        <<" SIGTZ_END_INPUT="<<t.end_sigma_before_strain_m
                        <<" CTADJ2_STRAIN="<<t.end_strain
                        <<" SZADJ="<<t.end_sigma_adjusted_m
                        <<" SIGTZ_END_OUTPUT="<<t.end_sigma_after_sigtz_m
                        <<" BIT_R=0x"<<std::hex<<std::bit_cast<std::uint32_t>(t.end_ratio)
                        <<" BIT_STRAIN=0x"<<std::bit_cast<std::uint32_t>(t.end_strain)
                        <<" BIT_SZADJ=0x"<<std::bit_cast<std::uint32_t>(t.end_sigma_adjusted_m)
                        <<" BIT_SZE1=0x"<<std::bit_cast<std::uint32_t>(t.end_sigma_after_sigtz_m)
                        <<std::dec<<"\n";
                }
                // Read-only original-source first real LCALM sigma discrepancy.
                // DGM #16426 is the earliest post-integration H9 difference:
                // same puff/KSAM and exact XY/SIGY, differing SIGZ by REAL4
                // rounding. Compare source/current before-mid-end timelines,
                // not a fitted tolerance or DGM-fed native physical state.
                if(global+1U==16426U){
                    const auto& z=stage.step.sigma.step;
                    const auto& az=stage.step.sigma.adjust;
                    const auto start_cell=stage.step.initial_met.cell.offset_0based;
                    const auto mid_cell=original_met_cell_clamped(
                        0.5F*(stage.step.before.x_cells+stage.step.after.x_cells),
                        0.5F*(stage.step.before.y_cells+stage.step.after.y_cells),
                        met.nx,met.ny);
                    require(controls.calm_mdisp3.has_value(),
                            "real H9 precision probe requires native CALM deck");
                    const auto& cfg=*controls.calm_mdisp3;
                    const auto turb=original_turbset_mdisp3_from_cell(
                        cfg.original_turbulence,static_met,
                        static_cast<std::size_t>(met.nx),
                        static_cast<std::size_t>(met.ny),
                        mid_cell.offset_0based,
                        met.ipgt.at(mid_cell.offset_0based),
                        cfg.iwat1,cfg.iwat2);
                    std::cout<<std::setprecision(10)
                        <<"P7_REAL_H9_CALM_SIGTZ_MET_AUTHORITIES"
                        <<" RECORD=16426"
                        <<" ORIGINAL_PGT="<<ref.integers[8]
                        <<" START_CELL0="<<start_cell
                        <<" MID_CELL0="<<mid_cell.offset_0based
                        <<" START_EL="<<met.el.at(start_cell)
                        <<" MID_EL="<<met.el.at(mid_cell.offset_0based)
                        <<" START_PGT="<<met.ipgt.at(start_cell)
                        <<" MID_PGT="<<met.ipgt.at(mid_cell.offset_0based)
                        <<" MID_SIGW="<<turb.sigw_ms
                        <<" MID_SIGV="<<turb.sigv_ms
                        <<" ORIGINAL_EL="<<ref.reals[4]
                        <<" IWAT="<<turb.land_water
                        <<" TZISDR="<<cfg.original_turbulence.tzisdr
                        <<" ORIGINAL_PHYSICS_INPUT_PROVENANCE=TO_BE_COMPARED\\n";
                    std::cout<<std::setprecision(10)
                        <<"P7_REAL_H9_CALM_SIGTZ_FIRST_DIVERGENCE"
                        <<" RECORD=16426"
                        <<" PUFF_NATIVE="<<stage.puff_id
                        <<" PUFF_VENDOR="<<ref.integers[3]
                        <<" KSAM="<<stage.ksam
                        <<" ICODE_VENDOR="<<ref.integers[4]
                        <<" LCALM_VENDOR="<<ref.integers[17]
                        <<" EL_VENDOR="<<ref.reals[4]
                        <<" WS_VENDOR="<<ref.reals[11]
                        <<" TSAMP_VENDOR="<<ref.reals[16]
                        <<" TSAMP_EFFECTIVE_VENDOR="<<ref.reals[62]
                        <<" TSAMP_NATIVE="<<stage.step.substep.step_s
                        <<" SIGZ_START_VENDOR="<<ref.reals[22]
                        <<" SIGZ_START_NATIVE="<<z.sigma_z_begin_m
                        <<" RAW_BME_NATIVE="<<z.sigma_z_begin_m<<","
                                          <<z.sigma_z_mid_m<<","<<z.sigma_z_end_m
                        <<" ADJUSTED_BME_VENDOR="<<ref.reals[56]<<","
                                                 <<ref.reals[57]<<","<<ref.reals[58]
                        <<" ADJUSTED_BME_NATIVE="<<az.sigma_z_begin_m<<","
                                                 <<az.sigma_z_mid_m<<","<<az.sigma_z_end_m
                        <<" VIRTUAL_TZ_NATIVE="<<z.virtual_time_z_begin_s<<","
                                                <<z.virtual_time_z_mid_s<<","
                                                <<z.virtual_time_z_end_s
                        <<" VIRTUAL_DZ_NATIVE="<<z.virtual_distance_z_begin_km<<","
                                                <<z.virtual_distance_z_mid_km<<","
                                                <<z.virtual_distance_z_end_km
                        <<" SIGZ_STORED_VENDOR="<<ref.reals[43]
                        <<" SIGZ_STORED_NATIVE="<<stage.step.vertical_after.sigma_z_m
                        <<" BIT_Z_VENDOR=0x"<<std::hex<<std::bit_cast<std::uint32_t>(ref.reals[43])
                        <<" BIT_Z_NATIVE=0x"<<std::bit_cast<std::uint32_t>(
                            static_cast<float>(stage.step.vertical_after.sigma_z_m))
                        <<std::dec
                        <<" READ_ONLY=YES"
                        <<" REAL_H9_PARITY=TO_BE_AUDITED\\n";
                }
                // Vendor DGM integer[1] records the active YYYYJJJHH
                // time stamp (202200123 -> 202200200 at Jan 1 midnight).
                // Linear addition of hour_index would incorrectly produce
                // 202200124 at H25 although the original puff/KSAM/XY/sigma
                // values are all bitwise equal.
                const int expected_dgm_clock=met.begin.year*100000+
                    met.begin.julian_day*100+met.begin.hour;
                const bool clock=ref.integers[1]==expected_dgm_clock;
                const bool puff_key=stage.puff_id==ref.integers[3] &&
                    stage.ksam==ref.integers[16];
                const bool keys=puff_key && clock;
                const bool xy=equal_real4(stage.step.after.x_cells,ref.reals[38]) &&
                    equal_real4(stage.step.after.y_cells,ref.reals[39]);
                const bool sy=equal_real4(stage.step.vertical_after.sigma_y_m,
                                          ref.reals[42]);
                const bool sz=equal_real4(stage.step.vertical_after.sigma_z_m,
                                          ref.reals[43]);
                matched_step_keys+=keys?1U:0U;
                matched_new_xy+=xy?1U:0U;
                matched_stored_sigy+=sy?1U:0U;
                matched_stored_sigz+=sz?1U:0U;
                if(first_dgm_mismatch_record==0U &&
                   (!keys||!xy||!sy||!sz)) {
                    first_dgm_mismatch_record=global+1U;
                    first_dgm_mismatch_field=!clock?"DGM_HOUR_CLOCK":
                        !puff_key?"PUFF_ID_KSAM":
                        !xy?"ADVECT_XY":!sy?"STORED_SIGY":"STORED_SIGZ";
                    std::cout<<std::setprecision(9)
                        <<"P7_HEFEI_6H_FIRST_ORIGINAL_DGM_DIFFERENCE"
                        <<" RECORD="<<global+1U
                        <<" HOUR="<<hour_index+1U
                        <<" STAGE="<<first_dgm_mismatch_field
                        <<" PUFF_NATIVE="<<stage.puff_id
                        <<" PUFF_VENDOR="<<ref.integers[3]
                        <<" KSAM_NATIVE="<<stage.ksam
                        <<" KSAM_VENDOR="<<ref.integers[16]
                        <<" DGM_CLOCK_EXPECTED="<<expected_dgm_clock
                        <<" DGM_CLOCK_VENDOR="<<ref.integers[1]
                        <<" XY_NATIVE="<<stage.step.after.x_cells<<","
                                         <<stage.step.after.y_cells
                        <<" XY_VENDOR="<<ref.reals[38]<<","<<ref.reals[39]
                        <<" SIGY_NATIVE="<<stage.step.vertical_after.sigma_y_m
                        <<" SIGY_VENDOR="<<ref.reals[42]
                        <<" SIGZ_NATIVE="<<stage.step.vertical_after.sigma_z_m
                        <<" SIGZ_VENDOR="<<ref.reals[43]
                        <<" SIGZ_IN_VENDOR="<<ref.reals[22]
                        <<" SIGZ_IN_NATIVE="<<stage.step.sigma.step.sigma_z_begin_m
                        <<" SIGZ_BME_VENDOR="<<ref.reals[56]<<","
                                               <<ref.reals[57]<<","<<ref.reals[58]
                        <<" SIGZ_BME_NATIVE="<<stage.step.sigma.adjust.sigma_z_begin_m<<","
                                               <<stage.step.sigma.adjust.sigma_z_mid_m<<","
                                               <<stage.step.sigma.adjust.sigma_z_end_m
                        <<" FIRST_BME_SOURCE_STAGE_DIAGNOSTIC=YES"<<"\n";
                    if(stage.step.sigma.terrain.has_value()){
                        const auto& t=*stage.step.sigma.terrain;
                        std::cout<<std::setprecision(10)
                            <<"P7_HEFEI_6H_NATIVE_SETPUF_END_FIRST_DIFFERENCE"
                            <<" RECORD="<<global+1U
                            <<" R="<<t.end_ratio
                            <<" SIGTZ_END_INPUT="<<t.end_sigma_before_strain_m
                            <<" CTADJ2_STRAIN="<<t.end_strain
                            <<" SZADJ="<<t.end_sigma_adjusted_m
                            <<" SIGTZ_END_OUTPUT="<<t.end_sigma_after_sigtz_m
                            <<" VDZE1="<<t.end_virtual_distance_km
                            <<" BIT_R=0x"<<std::hex<<std::bit_cast<std::uint32_t>(t.end_ratio)
                            <<" BIT_STRAIN=0x"<<std::bit_cast<std::uint32_t>(t.end_strain)
                            <<" BIT_SZADJ=0x"<<std::bit_cast<std::uint32_t>(t.end_sigma_adjusted_m)
                            <<" BIT_SZE1=0x"<<std::bit_cast<std::uint32_t>(t.end_sigma_after_sigtz_m)
                            <<std::dec<<"\n";
                    }
                }
            }
        }
        if(trace_this_hour){
            require(!trace_rows.empty(),
                    "native original hour2/4 H3 receptor had no physical trace");
            std::ofstream receiver_trace(
                hour_index==1U?argv[5]:argv[6],std::ios::binary);
            require(bool(receiver_trace),
                    "cannot open original hour2/4 native stage trace");
            receiver_trace<<std::setprecision(9);
            std::size_t prev=0U;bool seen_prev=false;
            for(const auto& record:trace_rows){
                std::size_t found=hour.steps.size();
                for(std::size_t j=0;j<hour.steps.size();++j){
                    const auto& stage=hour.steps[j];
                    if(stage.puff_id==record.episode &&
                       stage.step.before.travel_time_s==record.time_before &&
                       stage.step.after.travel_time_s==record.time_after){
                        require(found==hour.steps.size(),
                                "ambiguous native original COMP hour2 receptor step");
                        found=j;
                    }
                }
                require(found<hour.steps.size() && (!seen_prev || prev<found),
                        "native hour2 CALCPF step keys not in canonical COMP order");
                seen_prev=true;prev=found;
                const auto& d=record.values;
                const auto& st=hour.steps[found];
                receiver_trace<<physical_steps+found+1U<<" "<<record.episode
                    <<" "<<st.ksam<<" "<<d.sigma_y_m<<" "<<d.sigma_z_m
                    <<" "<<d.puff_height_m<<" "<<d.receptor_pole_m
                    <<" "<<d.vertical_factor<<" "<<d.xi1<<" "<<d.xi2
                    <<" "<<d.t1<<" "<<d.t2<<" "<<d.qold<<" "<<d.qnew
                    <<" "<<d.xtemp<<" "<<d.concentration<<"\n";
            }
            receiver_trace.flush();
            require(bool(receiver_trace),
                    "native original hour2 CALCPF stage trace flush failed");
            original_hour2_trace_rows=trace_rows.size();
            std::cout<<"P7_HEFEI_NATIVE_H3_CALCPF_TRACE=PASS"
                     <<" HOUR="<<hour_index+1U
                     <<" RECEPTOR_I="<<(hour_index==1U?25:47)
                     <<" RECEPTOR_J="<<(hour_index==1U?28:13)
                     <<" RECORDS="<<original_hour2_trace_rows
                     <<" ORIGINAL_VENDOR_PARITY=NOT_YET_COMPARED\\n";
        }
        if(argc==8){
            // Independent, read-only physical mass history of original puff 200.
            // Emit EVERY substep, not just ones that reach any receptor.
            std::ofstream mass_trace(argv[7],std::ios::app);
            require(bool(mass_trace),"cannot open native original puff200 mass trace");
            mass_trace<<std::setprecision(9);
            for(std::size_t n=0;n<hour.steps.size();++n){
                const auto& stage=hour.steps[n];
                if(stage.puff_id!=200)continue;
                const auto& step=stage.step;
                require(step.pre_dry_qold_mixed.size()>=1 &&
                        step.vmass.mass_mixed.size()>=1 && step.dry.has_value() &&
                        step.dry->fraction_remaining.size()>=1 &&
                        step.dry_input_resistance.has_value() &&
                        !step.dry_input_resistance->velocity_ms.empty(),
                        "puff200 original dry mass/VD source provenance missing");
                mass_trace<<physical_steps+n+1U<<" "
                    <<stage.puff_id<<" "<<stage.ksam<<" "
                    <<step.pre_dry_qold_mixed[0]<<" "
                    <<step.vmass.mass_mixed[0]<<" "
                    <<step.dry->fraction_remaining[0]<<" "
                    <<step.dry_input_resistance->velocity_ms[0]<<" "
                    <<1.0F<<" "
                    <<step.substep.step_s<<" "
                    <<step.dry->vcbar_m_inverse<<" "
                    <<static_cast<float>(step.substep.step_s*
                                        step.dry->vcbar_m_inverse)<<" "
                    <<step.dry_input_resistance->atmospheric_resistance_s_m<<" "
                    <<step.dry_input_resistance->deposition_layer_resistance_s_m[0]<<" "
                    <<step.dry_input_resistance->canopy_resistance_s_m[0]<<" "
                    <<step.dry_input_resistance->ground_resistance_s_m[0]<<" "
                    <<step.dry_input_resistance->foliage_resistance_s_m[0]<<" "
                    <<step.dry_input_resistance->cuticle_resistance_s_m[0]<<" "
                    <<step.dry_input_resistance->source_leaf_area_index<<"\n";
            }
            mass_trace.flush();
            require(bool(mass_trace),"native original puff200 mass trace failed");
        }
        physical_steps+=hour.steps.size();
        if(hour_index==0U && !coupling_candidate)
            require(hour.steps.size()==1275U &&
                    hour.release.puff_count==54 &&
                    active_before.empty(),
                    "first real original COMP hour was not preserved");

        // Read-only oracle: exactly one gridded H-3 field per hour;
        // HE-3 is carried in native species mass, not emitted as puff.con.
        const auto& reference=original.at(hour_index);
        require(reference.species_index==1 &&
                reference.label.find("H-3")!=std::string::npos &&
                reference.values.size()==field_count,
                "original H3/HE3 hourly record order or field size changed");
        std::size_t matches=0U,nonzero=0U,first_cell=field_count;
        double max_abs=0.0,sum_abs=0.0,native_sum=0.0,original_sum=0.0;
        for(std::size_t cell=0;cell<field_count;++cell) {
            const float native=hour.receptor_concentrations[cell];
            const float expected=reference.values[cell];
            require(std::isfinite(native)&&std::isfinite(expected)&&
                    native>=0.0F&&expected>=0.0F,
                    "invalid hour concentration/mass, source precision drift");
            native_sum+=native;
            original_sum+=expected;
            nonzero+=native>0.0F ? 1U:0U;
            if(equal_real4(native,expected))++matches;
            else if(first_cell==field_count)first_cell=cell;
            const double delta=std::abs(
                static_cast<double>(native)-static_cast<double>(expected));
            sum_abs+=delta;
            max_abs=std::max(max_abs,delta);
        }
        matching_words+=matches;
        if(matches!=field_count) {
            every_hour_real4=false;
            if(first_mismatched_hour==0U) {
                first_mismatched_hour=hour_index+1U;
                first_mismatched_cell=first_cell;
            }
        }
        // Verify native historical episode count and canonical stable IDs.
        require(driver.capacity_inventory().active_ids()==
                driver.canonical_ids() &&
                driver.active_count()==driver.canonical_ids().size(),
                "historical COMP active IDs diverged from capacity slots");
        require(std::is_sorted(driver.canonical_ids().begin(),
                               driver.canonical_ids().end()),
                "historical COMP puff chronology no longer canonical");
        std::cout<<std::setprecision(10)
                 <<"P7_HEFEI_6H_NATIVE_ORIGINAL_HOURLY"
                 <<" HOUR="<<hour_index+1U
                 <<" OLD_PUFFS="<<active_before.size()
                 <<" NEW_PUFFS="<<hour.release.puff_count
                 <<" ACTIVE_AFTER="<<driver.active_count()
                 <<" RETIRED="<<hour.retired.size()
                 <<" OCCUPIED_SLOTS="<<hour.occupied_slots_after
                 <<" FSTEP_SUBSTEPS="<<hour.steps.size()
                 <<" FSTEP_REENTRIES="<<hour.fstep_reentries
                 <<" REAL4_WORDS="<<matches<<"/"<<field_count
                 <<" FIRST_DIFFERENT_CELL0="<<first_cell
                 <<" NONZERO_NATIVE="<<nonzero
                 <<" MAX_ABS_BQ_M3="<<max_abs
                 <<" MAE_BQ_M3="<<sum_abs/static_cast<double>(field_count)
                 <<" NATIVE_SUM_BQ_M3="<<native_sum
                 <<" ORIGINAL_SUM_BQ_M3="<<original_sum
                 <<" SCIENTIFIC_6H_PARITY="
                 <<(matches==field_count?"PASS_THIS_HOUR":"OPEN_THIS_HOUR")
                 <<"\n";
        // Both first two source-real hours are now scientifically accepted.
        // This gate must not loosen when investigating the hour3 SIGZ.
        require(coupling_candidate || hour_index>=3U || matches==field_count,
                "first three real H3 concentration fields lost REAL4 parity");
        if(hour_index==1U && !dgm.empty())
            require(first_dgm_mismatch_record==0U,
                    "original/native first two hours of puff history diverged");
        ++completed;
       },!coupling_c2);
    require(summary.intervals==143U&&completed==probe_hours&&
            driver.completed_hours()==probe_hours&&
            (coupling_candidate || physical_steps>=11458U)&&
            (coupling_candidate || probe_hours>6U||physical_steps==11458U),
            "frozen MET and requested contiguous native COMP hours required");
    if(!dgm.empty()) {
        require(matched_step_keys==physical_steps &&
                matched_new_xy==physical_steps &&
                matched_stored_sigy==physical_steps &&
                matched_stored_sigz==physical_steps,
                "requested-hour original REAL4 COMP puff identity/XY/SIGY/SIGZ parity regressed");
        std::cout<<"P7_HEFEI_6H_ORIGINAL_DGM_REAL4_DIAGNOSTIC=PASS"
                 <<" KEYS="<<matched_step_keys<<"/11458"
                 <<" ADVECT_XY="<<matched_new_xy<<"/11458"
                 <<" STORED_SIGY="<<matched_stored_sigy<<"/11458"
                 <<" STORED_SIGZ="<<matched_stored_sigz<<"/11458"
                 <<" FIRST_DIFFERENCE_RECORD="<<first_dgm_mismatch_record
                 <<" FIRST_DIFFERENCE_STAGE="<<first_dgm_mismatch_field
                 <<" 6H_STAGE_BITWISE="
                 <<(first_dgm_mismatch_record==0U?"YES":"OPEN")<<"\n";
    }
    // The frozen native/original six-hour numerical equivalence is now
    // an acceptance gate, not a diagnostic trend. Do not silently reduce
    // it to first-three-hour parity or a floating-point tolerance.
    if(!coupling_candidate)
        require(every_hour_real4 && matching_words==field_count*probe_hours &&
                first_mismatched_hour==0U && first_mismatched_cell==0U,
                "real original/native H-3 must match every requested hour in REAL4 bits");
    if(native_con_writer) {
        require(native_con_hours &&
                native_con_hours->hours_written()==probe_hours,
                "native puff.con hours not equal to continuous COMP hours");
        require(native_con_writer->records_written()==6U+3U*probe_hours,
                "native original WROUT1 header/data record count drift");
        native_con_writer->close();
        const std::string actual=bytes(original_con_output);
        const std::string frozen=bytes(argv[3]);
        std::size_t first=0U;
        const auto shorter=std::min(actual.size(),frozen.size());
        while(first<shorter && actual[first]==frozen[first])++first;
        if(!coupling_candidate && (first!=actual.size() || actual.size()>frozen.size())) {
            std::cout<<"P7_NATIVE_PUFF_CON_FIRST_DIFFERENCE"
                     <<" BYTE0="<<first
                     <<" NATIVE_BYTES="<<actual.size()
                     <<" ORIGINAL_BYTES="<<frozen.size()
                     <<" HOURS="<<probe_hours<<"\n";
            require(false,"native WROUT1 prefix/data differs from frozen puff.con bytes");
        }
        if(coupling_candidate) {
            std::cout<<(coupling_c2?"P7_C2_NATIVE_PUFF_CON_CREATED":"P7_C1_NATIVE_PUFF_CON_CREATED")
                     <<" HOURS="<<probe_hours
                     <<" BYTES="<<actual.size()
                     <<" HEADER_DIFFERENCE_FROM_VENDOR_ALLOWED=YES"
                     <<" NO_ORACLE_INJECTION=YES\n";
        }
        if(!coupling_candidate)std::cout<<"P7_NATIVE_PUFF_CON_PREFIX=PASS"
                 <<" HOURS="<<probe_hours
                 <<" RECORDS="<<(3226U+3U*probe_hours)
                 <<" BYTES="<<actual.size()
                 <<" BINARY_EXACT=YES NO_ORACLE_INJECTION=YES\n";
        if(probe_hours==143U && !coupling_candidate) {
            require(actual.size()==frozen.size() &&
                    actual.size()==1896056U &&
                    native_con_writer->records_written()==435U,
                    "full 143h original puff.con byte size/record count drift");
            std::cout<<"P7_NATIVE_PUFF_CON_FULL=PASS"
                     <<" HOURS=143 RECORDS=3655 BYTES=1896056"
                     <<" BINARY_EXACT=YES\n";
        }
    }
    if(coupling_candidate) {
        std::cout<<(coupling_c2?"P7_C2_NATIVE_ON_PR63_MET":"P7_C1_NATIVE_ON_PR53_MET")
                 <<" HOURS="<<completed
                 <<" REAL4_MATCHED="<<matching_words<<"/"<<field_count*completed
                 <<" FIRST_MISMATCH_HOUR="<<first_mismatched_hour
                 <<" FIRST_MISMATCH_CELL0="<<first_mismatched_cell
                 <<" SAME_MET_VENDOR_PARITY="<<(every_hour_real4?"PASS":"MISMATCH")
                 <<" NO_ORIGINAL_DGM_AS_INPUT=YES\n";
        require(every_hour_real4 && matching_words==field_count*probe_hours,
            "C1 native P7 vs vendor CALPUFF on SAME PR53 MET has REAL4 differences");
    }
    if(probe_hours>6U && !coupling_candidate)
        std::cout<<"P7_HEFEI_REAL_EXTENDED_SOURCE_PROBE=PASS"
                 <<" HOURS="<<probe_hours
                 <<" ORIGINAL_DGM_ROWS="<<physical_steps
                 <<" H3_REAL4_WORDS="<<matching_words<<"/"<<2500U*probe_hours
                 <<" FIRST_DIFFERENCE=NONE"
                 <<" 143H_SCIENTIFIC_ACCEPTED="
                 <<(probe_hours==143U?"YES":"NO")
                 <<" FULL_PUFF_CON_ACCEPTED="
                 <<(probe_hours==143U && native_con_writer?"YES":"NO")
                 <<"\n";
    if(probe_hours==6U && !coupling_candidate)std::cout<<"P7_HEFEI_6H_COMP_ORIGINAL_SUBSTEP_SCHEDULE=PASS"
             <<" ORIGINAL_DGM_ROWS=11458/11458"
             <<" HOURLY_ROWS=1275,2242,1906,2132,1742,2161"
             <<" FIRST_AND_LAST_EPISODE_IDS=SOURCE_EQUIVALENT"
             <<" DGM_EXPORTED_XY_SIGY_SIGZ=BITWISE_11458_OF_11458"
             <<" OTHER_INTERNAL_STAGES=NOT_YET_ALL_BITWISE"<<"\n";
    if(probe_hours==6U && !coupling_candidate)std::cout<<"P7_HEFEI_REAL_6H_COMPUTATION_AND_PRECISION_DIAGNOSTIC=PASS"
             <<" HOURS=6 METFM1=ORIGINAL"
             <<" COMP_AUTHORITY=SINGLE_STATEFUL_DRIVER"
             <<" REAL4_WORDS_MATCHED="<<matching_words<<"/15000"
             <<" FIRST_DIFFERENT_HOUR="<<first_mismatched_hour
             <<" FIRST_DIFFERENT_CELL0="<<first_mismatched_cell
             <<" EVERY_HOUR_BITWISE="<<(every_hour_real4?"YES":"NO")
             <<" REAL_6H_SCIENTIFIC_PARITY="
             <<(every_hour_real4?"PASS":"OPEN")
             <<" ORIGINAL_143H=NOT_ACCEPTED"
             <<" WROUT1_FULL_OUTPUT=NOT_ACCEPTED\n";
    return 0; // Strict requested-hour REAL4 concentration and DGM gate.
  }catch(const std::exception& e){
    std::cerr<<"P7_HEFEI_REAL_6H_COMPUTATION_AND_PRECISION_DIAGNOSTIC=FAIL "
             <<e.what()<<"\n";
    return 1;
  }
}
