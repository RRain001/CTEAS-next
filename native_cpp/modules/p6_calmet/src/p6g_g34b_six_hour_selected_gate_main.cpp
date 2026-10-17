// G34B: TEST-ONLY six consecutive native G14 hours. No GUI/production binding.
// G26A/G26B production adapters remain Unknown,false. Nothing is borrowed
// from an original-vendor CALMET.DAT; frozen scientific comparison is separate.
#include "cteas/p6/p6g_g19_file_backed_case.hpp"
#include "cteas/p6/p6g_g26b_file_backed_comp_bridge.hpp"
#include "cteas/p6/p6g_g18d1_p6f_precommit.hpp"
#include <bit>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

namespace p6g=cteas::calmet::p6g;
namespace p6=cteas::calmet::p6;

// G36C: the persisted checkpoint stores the real historical COMP arrays,
// actual two-upper station clock endpoints, and the *complete source-derived*
// P6F prefix. On restart, a new process replays the original source up to
// this boundary to reconstruct private per-station CGAMMA state, validates
// this saved checkpoint bit-for-bit, then continues beyond the boundary.
// This is explicit, slower REPLAY recovery, not a dishonest direct restore of
// the accepted frozen CGammaState private representation.
static void g36c_save_checkpoint(
    const std::filesystem::path& directory,std::size_t completed,
    const p6::NativeGridMemory& memory,
    const p6g::G18D2StationClockAuthority& clocks,
    const cteas::p6f::Calmet21File& native_prefix) {
    if(completed<1||completed>=143||native_prefix.hourly.size()!=completed*45)
        throw std::invalid_argument("G36C selected checkpoint missing complete source hours");
    std::filesystem::create_directories(directory);
    if(std::filesystem::exists(directory/"READY.json"))
        throw std::runtime_error("G36C refuses overwrite of already-sealed checkpoint");
    std::ofstream state(directory/"state.txt",std::ios::trunc);
    if(!state)throw std::runtime_error("G36C cannot write real physical memory snapshot");
    const auto epoch=[](std::chrono::sys_seconds instant) {
        return instant.time_since_epoch().count();
    };
    const auto n=memory.zi_m.size();
    if(n!=144||memory.ziconv_m.size()!=n||memory.dptt_k.size()!=n)
        throw std::invalid_argument("G36C checkpoint unaccepted physical grid");
    state<<"CTEAS_G36C_REPLAY_CHECKPOINT_V1\n"<<completed<<" "
         <<epoch(clocks.latest_upper_hour())<<" "
         <<epoch(clocks.latest_gamma_hour())<<" "<<n<<"\n";
    const auto words=[&](const std::vector<float>& vector) {
        for(const float value:vector)
            state<<std::hex<<std::setw(8)<<std::setfill('0')
                 <<std::bit_cast<std::uint32_t>(value)<<" ";
        state<<std::dec<<"\n";
    };
    words(memory.zi_m);
    words(memory.ziconv_m);
    words(memory.dptt_k);
    state.flush();
    if(!state)throw std::runtime_error("G36C real physical snapshot truncated");
    const auto payload=cteas::p6f::serialize_calmet_dat21(native_prefix);
    std::ofstream prefix(directory/"prefix.dat",std::ios::binary|std::ios::trunc);
    if(!prefix)throw std::runtime_error("G36C cannot save original-format P6F prefix");
    prefix.write(reinterpret_cast<const char*>(payload.data()),
                 static_cast<std::streamsize>(payload.size()));
    prefix.flush();
    if(!prefix)throw std::runtime_error("G36C prefix output truncated");
}

static void g36c_verify_replayed_checkpoint(
    const std::filesystem::path& directory,std::size_t completed,
    const p6::NativeGridMemory& memory,
    const p6g::G18D2StationClockAuthority& clocks,
    const cteas::p6f::Calmet21File& replayed_prefix) {
    if(!std::filesystem::is_regular_file(directory/"READY.json"))
        throw std::runtime_error("G36C uncommitted checkpoint refused");
    std::ifstream state(directory/"state.txt");
    std::string magic;
    std::size_t saved_count=0,saved_n=0;
    long long saved_upper=0,saved_gamma=0;
    if(!(state>>magic>>saved_count>>saved_upper>>saved_gamma>>saved_n)||
       magic!="CTEAS_G36C_REPLAY_CHECKPOINT_V1"||
       saved_count!=completed||saved_n!=memory.zi_m.size()||
       saved_n!=memory.ziconv_m.size()||saved_n!=memory.dptt_k.size()||
       saved_upper!=clocks.latest_upper_hour().time_since_epoch().count()||
       saved_gamma!=clocks.latest_gamma_hour().time_since_epoch().count())
        throw std::runtime_error("G36C replayed PREPDI/COMP/CGAMMA checkpoint differs");
    const auto require_bits=[&](const std::vector<float>& vector) {
        state>>std::hex;
        for(float value:vector) {
            std::uint32_t bits=0;
            if(!(state>>bits)||bits!=std::bit_cast<std::uint32_t>(value))
                throw std::runtime_error(
                    "G36C restarted COMP ZI/ZICONV/DPTT bit-for-bit replay mismatch");
        }
        state>>std::dec;
    };
    require_bits(memory.zi_m);
    require_bits(memory.ziconv_m);
    require_bits(memory.dptt_k);
    std::string extra;
    if(state>>extra)
        throw std::runtime_error("G36C checkpoint has unexplained trailing state");
    std::ifstream existing(directory/"prefix.dat",std::ios::binary);
    if(!existing)throw std::runtime_error("G36C checkpoint P6F prefix absent");
    const std::vector<std::uint8_t> persisted(
        std::istreambuf_iterator<char>{existing},std::istreambuf_iterator<char>{});
    const auto reproduced=cteas::p6f::serialize_calmet_dat21(replayed_prefix);
    if(persisted!=reproduced)
        throw std::runtime_error(
            "G36C replayed 45xN CALMET.DAT is not byte-identical to checkpoint prefix");
}

class G34BSelectedOnlyHour final : public p6g::MultiHourPhysics {
public:
    G34BSelectedOnlyHour(const p6g::UnifiedMultistationHourlyScheduler& owner,
                         p6g::G18D2StationClockAuthority& clocks,
                         const p6g::G19FileBackedCase& source)
        :source_(source),diagno_(owner,clocks,source),comp_(diagno_,source) {}

    p6::NativeHourStageResult run(p6::NativeHourStage stage,
                                  p6g::MultiHourFrame& frame) override {
        if(cursor_>=17||stage!=p6::kHefeiOriginalStageOrder[cursor_])
            throw std::logic_error("G34B native stage skipped/reordered");
        if(cursor_<12) diagno_.run_selected(stage,frame,true);
        else if(cursor_<16) comp_.run_selected(stage,frame,true);
        else {
            const auto& candidate=comp_.selected_p6f_candidate(frame);
            const auto& heat=comp_.source_comp_heat_for_p6f(frame);
            const auto records=p6g::g18c5_selected_p6f_fields(
                frame,heat,candidate,source_.original_metinp,true);
            const auto dataset=p6g::g18c6_selected_one_hour_dataset(
                frame,records,p6g::source_setcom_nears(frame.grid,frame.stations),
                source_.original_metinp,true);
            const auto bytes=p6g::g18d1_validate_p6f_precommit(frame,dataset);
            if(bytes.empty()||dataset.hourly.size()!=45)
                throw std::logic_error("G34B native P6F candidate incomplete");
            output_.emplace(dataset);
        }
        ++cursor_;
        // Only this opt-in executable converts independently computed
        // selected kernels to a G14 transaction attempt, not production.
        return {p6::NativeHourSource::NativeCpp,true};
    }

    const cteas::p6f::Calmet21File& precommit(
        const p6g::MultiHourFrame& frame) const {
        if(cursor_!=17||!output_)
            throw std::logic_error("G34B missing native 17th stage or output");
        diagno_.require_station_clock_preflight(frame);
        return *output_;
    }

    bool publish_after_commit_noexcept() noexcept {
        return cursor_==17&&diagno_.try_publish_after_selected_g14_commit_noexcept();
    }
private:
    const p6g::G19FileBackedCase& source_;
    p6g::G26SourceFileBackedG14DiagnoBridge diagno_;
    p6g::G26BSourceFileBackedCompBridge comp_;
    std::size_t cursor_=0;
    std::optional<cteas::p6f::Calmet21File> output_;
};

int main(int argc,char** argv) {
    try {
        if(argc!=7&&argc!=9&&argc!=13)
            throw std::invalid_argument(
                "Usage: g34b <met.inp> <GEO.DAT> <SURF.DAT> <UP1.DAT> <UP2.DAT> <candidate-calmet.dat> [--hours 143 [--checkpoint-hour N --checkpoint-dir DIR | --resume-hour N --resume-dir DIR]]");
        std::size_t requested_hours=6;
        if(argc>=9) {
            if(std::string(argv[7])!="--hours"||std::string(argv[8])!="143")
                throw std::invalid_argument("G35 long-run requires explicit --hours 143");
            requested_hours=143;
        }
        std::string g36c_mode;
        std::size_t checkpoint_hour=0;
        std::filesystem::path checkpoint_dir;
        if(argc==13) {
            g36c_mode=argv[9];
            if((g36c_mode!="--checkpoint-hour"&&g36c_mode!="--resume-hour")||
               (std::string(argv[11])!=(g36c_mode=="--checkpoint-hour"?
                    "--checkpoint-dir":"--resume-dir")))
                throw std::invalid_argument("G36C checkpoint arguments malformed");
            const std::string n=argv[10];
            std::size_t pos=0;
            checkpoint_hour=std::stoul(n,&pos);
            if(pos!=n.size()||checkpoint_hour==0||checkpoint_hour>=143)
                throw std::invalid_argument("G36C checkpoint hour must be 1..142");
            checkpoint_dir=argv[12];
        }
        const p6g::G19SourceFilePaths paths{argv[1],argv[2],argv[3],{argv[4],argv[5]}};
        const auto source=p6g::g19_load_original_source_case(paths);
        auto scheduler=source.make_scheduler();
        if(source.stations.surface.size()!=2||source.stations.upper.size()!=2||
           source.grid.nx!=12||source.grid.ny!=12||
           scheduler.planned_hours()!=requested_hours)
            throw std::invalid_argument(
                "G35 only G19 12x12 2SS/2US 6h or 143h original-format case");
        p6g::G18D2StationClockAuthority clocks;
        std::optional<cteas::p6f::Calmet21File> six_hour;
        for(std::size_t hour=0;hour<requested_hours;++hour) {
            std::optional<cteas::p6f::Calmet21File> accepted;
            G34BSelectedOnlyHour* active=nullptr;
            bool published=false;
            scheduler.advance_with_fresh_physics(
                [&](const p6g::MultiHourFrame& live)
                    ->std::unique_ptr<p6g::MultiHourPhysics> {
                    if(live.hour_index!=hour||scheduler.completed_hours()!=hour)
                        throw std::logic_error("G34B duplicate/omitted source hour");
                    auto current=std::make_unique<G34BSelectedOnlyHour>(
                        scheduler,clocks,source);
                    active=current.get();
                    return current;
                },
                [&](const p6g::MultiHourFrame& frame) {
                    if(!active)
                        throw std::logic_error("G34B missing live native executor");
                    accepted=active->precommit(frame);
                    if(!accepted||accepted->hourly.size()!=45)
                        throw std::logic_error("G34B native P6F precommit missing");
                },
                [&](p6g::MultiHourPhysics&,const p6g::MultiHourFrame& frame,
                    const p6g::UnifiedMultistationHourlyScheduler& owner) {
                    if(!active||owner.completed_hours()!=hour||
                       frame.hour_index!=hour)
                        throw std::logic_error("G34B clock preflight detached");
                },
                [&](p6g::MultiHourPhysics& physics,
                    const p6g::UnifiedMultistationHourlyScheduler&) noexcept {
                    auto* native=dynamic_cast<G34BSelectedOnlyHour*>(&physics);
                    published=native&&native->publish_after_commit_noexcept();
                });
            if(!published||!accepted||scheduler.completed_hours()!=hour+1||
               !clocks.has_published_hour())
                throw std::runtime_error(
                    "G34B failed postcommit AA/BB/CGAMMA transaction");
            if(!six_hour) {
                six_hour=std::move(accepted);
            } else {
                auto& result=*six_hour;
                auto& next=*accepted;
                if(result.header.nx!=next.header.nx||
                   result.header.ny!=next.header.ny||
                   result.header.nssta!=next.header.nssta||
                   result.header.nusta!=next.header.nusta||
                   result.statics.zface_m!=next.statics.zface_m||
                   result.statics.nears!=next.statics.nears||
                   result.statics.elev_m!=next.statics.elev_m||
                   result.hourly.size()!=hour*45)
                    throw std::logic_error(
                        "G34B original static inventory drifted across hours");
                result.hourly.insert(result.hourly.end(),
                    std::make_move_iterator(next.hourly.begin()),
                    std::make_move_iterator(next.hourly.end()));
                result.header.irlg=static_cast<int>(hour+1);
                result.header.end_year=next.header.end_year;
                result.header.end_month=next.header.end_month;
                result.header.end_day=next.header.end_day;
                result.header.end_hour=next.header.end_hour;
                result.header.end_second=next.header.end_second;
            }
            std::cout<<"G34B_NATIVE_HOUR_COMMITTED="<<hour+1
                     <<" AA_BB_CGAMMA_CLOCKS=1\n";
            if(hour+1==checkpoint_hour&&g36c_mode=="--checkpoint-hour") {
                g36c_save_checkpoint(checkpoint_dir,hour+1,
                                     scheduler.committed_memory(),clocks,*six_hour);
                std::cout<<"G36C_CHECKPOINT_STAGED_HOUR="<<hour+1
                         <<" STATUS=NOT_YET_DURABLY_SEALED\n";
                return 0;
            }
            if(hour+1==checkpoint_hour&&g36c_mode=="--resume-hour") {
                g36c_verify_replayed_checkpoint(
                    checkpoint_dir,hour+1,
                    scheduler.committed_memory(),clocks,*six_hour);
                std::cout<<"G36C_REPLAY_STATE_BIT_EXACT_AND_PREFIX_MATCH_HOUR="
                         <<hour+1<<"\n";
            }
        }
        scheduler.require_complete();
        if(!six_hour||six_hour->hourly.size()!=45*requested_hours||
           six_hour->header.irlg!=static_cast<int>(requested_hours))
            throw std::logic_error("G35 native output lacks full 45 fields each hour");
        const auto bytes=cteas::p6f::serialize_calmet_dat21(*six_hour);
        std::ofstream output(argv[6],std::ios::binary|std::ios::trunc);
        if(!output)throw std::runtime_error("G34B output file unavailable");
        output.write(reinterpret_cast<const char*>(bytes.data()),
                     static_cast<std::streamsize>(bytes.size()));
        output.flush();
        if(!output)throw std::runtime_error("G34B native output truncated");
        std::cout<<"PASS_G35_NATIVE_CONTINUOUS_HOUR_TRANSACTION_TEST_ONLY "
                 <<"HOURS="<<requested_hours
                 <<" FIELDS="<<45*requested_hours<<" STATIONS=2SS_2US "
                 <<"ORIGINAL_VENDOR_PARITY=NOT_YET_CALCULATED\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr<<"BLOCKED_G34B_NATIVE_SIX_HOUR "<<error.what()<<"\n";
        return 2;
    }
}
