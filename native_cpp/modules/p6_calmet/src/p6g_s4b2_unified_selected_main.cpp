// S4-B2: one experimental, source-backed P6 G14 selected-physics driver.
// Shares the EXACT physical hour actor with frozen C2 G34B; does not alter
// C1/C2 comparison baselines or claim production/original-vendor acceptance.
// G19 owns READCF, original station IDs and genuine source UTC brackets;
// G14 owns PREPDI -> DIAGNO -> COMP -> P6F and every historical state commit.
#include "cteas/p6/p6g_s4b2_selected_hour.hpp"
#include "cteas/p6/p6g_g65_shared_noaa_firsthour_actor.hpp"
#include "cteas/p6/p6g_g65_shared_native_water_history.hpp"
#include "cteas/p6/p6g_g43_comp_missfc_source.hpp"
#include "cteas/p6/p6g_s4b1_admission.hpp"
#include <cstddef>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <sstream>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

struct S4B2Options {
    std::string met, geo, surf, output, native_comp_trace;
    std::vector<std::string> up;
    std::size_t hours=0;
    std::size_t probe_prefix_hours=0;
    std::size_t max_retained_field_bytes=0;
    bool experimental=false;
    bool g26_normal_entry_trial=false;
    bool water_source_preflight_only=false;
    bool water_firsthour_g14_trial_only=false;
    bool water_secondhour_g14_trial_only=false;
    bool water_thirdhour_g14_trial_only=false;
    bool water_fourthhour_g14_trial_only=false;
    bool water_fifthhour_g14_trial_only=false;
    bool water_sixthhour_g14_trial_only=false;
};

static S4B2Options parse_args(int argc, char** argv) {
    S4B2Options o;
    for (int i=1; i<argc; ++i) {
        const std::string key=argv[i];
        if (key=="--selected-experimental") {
            if(o.experimental)throw std::invalid_argument("duplicate experimental flag");
            o.experimental=true;
            continue;
        }
        if (key=="--g26-normal-entry-trial") {
            if(o.g26_normal_entry_trial)
                throw std::invalid_argument("duplicate G26 normal entry trial flag");
            o.g26_normal_entry_trial=true;
            continue;
        }
        if (key=="--water-source-preflight-only") {
            if(o.water_source_preflight_only)
                throw std::invalid_argument("duplicate S4C water preflight flag");
            o.water_source_preflight_only=true;
            continue;
        }
        if (key=="--water-firsthour-g14-trial-only") {
            if(o.water_firsthour_g14_trial_only)
                throw std::invalid_argument("duplicate S4C WATER G14 firsthour trial");
            o.water_firsthour_g14_trial_only=true;
            continue;
        }
        if (key=="--water-secondhour-g14-trial-only") {
            if(o.water_secondhour_g14_trial_only)
                throw std::invalid_argument("duplicate S4C WATER G14 secondhour trial");
            o.water_secondhour_g14_trial_only=true;
            continue;
        }
        if (key=="--water-thirdhour-g14-trial-only") {
            if(o.water_thirdhour_g14_trial_only)
                throw std::invalid_argument("duplicate S4C WATER G14 thirdhour trial");
            o.water_thirdhour_g14_trial_only=true;
            continue;
        }
        if (key=="--water-fourthhour-g14-trial-only") {
            if(o.water_fourthhour_g14_trial_only)
                throw std::invalid_argument("duplicate S4C WATER G14 fourthhour trial");
            o.water_fourthhour_g14_trial_only=true;
            continue;
        }
        if (key=="--water-fifthhour-g14-trial-only") {
            if(o.water_fifthhour_g14_trial_only)
                throw std::invalid_argument("duplicate S4C WATER G14 fifthhour trial");
            o.water_fifthhour_g14_trial_only=true;
            continue;
        }
        if (key=="--water-sixthhour-g14-trial-only") {
            if(o.water_sixthhour_g14_trial_only)
                throw std::invalid_argument("duplicate S4C WATER G14 sixthhour trial");
            o.water_sixthhour_g14_trial_only=true;
            continue;
        }
        if(i+1>=argc)throw std::invalid_argument("S4B2 key missing argument");
        const std::string value=argv[++i];
        if(value.empty())throw std::invalid_argument("S4B2 empty argument");
        if(key=="--met" && o.met.empty())o.met=value;
        else if(key=="--geo" && o.geo.empty())o.geo=value;
        else if(key=="--surf" && o.surf.empty())o.surf=value;
        else if(key=="--up")o.up.push_back(value);
        else if(key=="--out" && o.output.empty())o.output=value;
        else if(key=="--native-comp-trace" && o.native_comp_trace.empty())o.native_comp_trace=value;
        else if(key=="--probe-prefix-hours" && o.probe_prefix_hours==0) {
            if(value[0]=='-')throw std::invalid_argument("S4B3 invalid probe hours");
            std::size_t consumed=0;
            const auto parsed=std::stoull(value,&consumed);
            if(consumed!=value.size()||parsed==0)
                throw std::invalid_argument("S4B3 invalid probe hours");
            o.probe_prefix_hours=static_cast<std::size_t>(parsed);
            if(parsed!=o.probe_prefix_hours)throw std::invalid_argument("S4B3 probe hours overflow");
        }
        else if(key=="--max-retained-field-bytes" && o.max_retained_field_bytes==0) {
            if(value[0]=='-')
                throw std::invalid_argument("S4E invalid retained field byte budget");
            std::size_t consumed=0;
            const auto parsed=std::stoull(value,&consumed);
            if(consumed!=value.size()||parsed==0)
                throw std::invalid_argument("S4E invalid retained field byte budget");
            o.max_retained_field_bytes=static_cast<std::size_t>(parsed);
            if(parsed!=o.max_retained_field_bytes)
                throw std::invalid_argument("S4E retained field byte budget overflow");
        }
        else if(key=="--hours" && o.hours==0) {
            std::size_t consumed=0;
            const auto parsed=std::stoull(value,&consumed);
            if(consumed!=value.size()||parsed==0)
                throw std::invalid_argument("S4B2 invalid positive hours");
            o.hours=static_cast<std::size_t>(parsed);
            if(parsed!=o.hours)throw std::invalid_argument("S4B2 hours overflow");
        } else throw std::invalid_argument("S4B2 unknown/repeated argument: "+key);
    }
    if(!o.experimental||o.met.empty()||o.geo.empty()||o.surf.empty()||
       o.up.empty()||o.hours==0||
       (!o.water_source_preflight_only&&o.output.empty()))
        throw std::invalid_argument(
            "S4B2 experimental ONLY: --selected-experimental --met met.inp "
            "--geo GEO.DAT --surf SURF.DAT --up UP1.DAT [--up UP2.DAT ...] "
            "--hours N [--probe-prefix-hours K] [--max-retained-field-bytes N] "
            "[--g26-normal-entry-trial] [--native-comp-trace native-state.csv] "
            "--out candidate-met.dat; OR --water-source-preflight-only "
            "without --out; optional --water-firsthour-g14-trial-only "
            "for original NOAA prefix=1 only, or --water-secondhour-g14-trial-only "
            "for original NOAA prefix=2 only, or --water-thirdhour-g14-trial-only "
            "for original NOAA prefix=3 only, or --water-fourthhour-g14-trial-only "
            "for original NOAA prefix=4 only, or --water-fifthhour-g14-trial-only "
            "for original NOAA prefix=5 only, or --water-sixthhour-g14-trial-only "
            "for original NOAA prefix=6 only; no production mode");
    // S4C source-only admission must NEVER be capable of emitting MET.DAT,
    // changing a physical-stage toggle or probing only some input hours.
    if(o.water_source_preflight_only&&
       (!o.output.empty()||!o.native_comp_trace.empty()||
        o.g26_normal_entry_trial||o.probe_prefix_hours!=0||
        o.max_retained_field_bytes!=0))
        throw std::invalid_argument(
            "S4C WATER preflight forbids output, trace and every physical trial flag");
    if(o.water_firsthour_g14_trial_only&&
       (o.water_secondhour_g14_trial_only||
        o.water_thirdhour_g14_trial_only||
        o.water_fourthhour_g14_trial_only||
        o.water_fifthhour_g14_trial_only||
        o.water_sixthhour_g14_trial_only||o.water_source_preflight_only||
        o.g26_normal_entry_trial||o.probe_prefix_hours!=1||o.hours!=6||
        o.output.empty()||!o.native_comp_trace.empty()))
        throw std::invalid_argument(
            "S4C NOAA WATER G14 requires 6h source, firsthour-only prefix, "
            "one fresh output and no normal G26/COMP trace/preflight mixing");
    if(o.water_secondhour_g14_trial_only&&
       (o.water_source_preflight_only||o.water_firsthour_g14_trial_only||
        o.water_thirdhour_g14_trial_only||
        o.water_fourthhour_g14_trial_only||
        o.water_fifthhour_g14_trial_only||
        o.water_sixthhour_g14_trial_only||o.g26_normal_entry_trial||
        o.probe_prefix_hours!=2||o.hours!=6||
        o.output.empty()||!o.native_comp_trace.empty()))
        throw std::invalid_argument(
            "S4C NOAA WATER secondhour requires full 6h source, "
            "exactly 2 committed G14 hours and no mixed trials/trace");
    if(o.water_thirdhour_g14_trial_only&&
       (o.water_source_preflight_only||o.water_firsthour_g14_trial_only||
        o.water_secondhour_g14_trial_only||
        o.water_fourthhour_g14_trial_only||
        o.water_fifthhour_g14_trial_only||
        o.water_sixthhour_g14_trial_only||o.g26_normal_entry_trial||
        o.probe_prefix_hours!=3||o.hours!=6||o.output.empty()||
        !o.native_comp_trace.empty()))
        throw std::invalid_argument(
            "S4C NOAA WATER thirdhour requires full 6h source, "
            "exactly 3 committed G14 hours and no mixed trials/trace");
    if(o.water_fourthhour_g14_trial_only&&
       (o.water_source_preflight_only||o.water_firsthour_g14_trial_only||
        o.water_secondhour_g14_trial_only||o.water_thirdhour_g14_trial_only||
        o.water_fifthhour_g14_trial_only||
        o.water_sixthhour_g14_trial_only||o.g26_normal_entry_trial||
        o.probe_prefix_hours!=4||o.hours!=6||
        o.output.empty()||!o.native_comp_trace.empty()))
        throw std::invalid_argument(
            "S4C NOAA WATER fourthhour requires full 6h source, "
            "exactly 4 committed G14 hours and no mixed trials/trace");
    if(o.water_fifthhour_g14_trial_only&&
       (o.water_source_preflight_only||o.water_firsthour_g14_trial_only||
        o.water_secondhour_g14_trial_only||o.water_thirdhour_g14_trial_only||
        o.water_fourthhour_g14_trial_only||
        o.water_sixthhour_g14_trial_only||o.g26_normal_entry_trial||
        o.probe_prefix_hours!=5||o.hours!=6||o.output.empty()||
        !o.native_comp_trace.empty()))
        throw std::invalid_argument(
            "S4C NOAA WATER fifthhour requires full 6h source, "
            "exactly 5 committed G14 hours and no mixed trials/trace");
    if(o.water_sixthhour_g14_trial_only&&
       (o.water_source_preflight_only||o.water_firsthour_g14_trial_only||
        o.water_secondhour_g14_trial_only||o.water_thirdhour_g14_trial_only||
        o.water_fourthhour_g14_trial_only||o.water_fifthhour_g14_trial_only||
        o.g26_normal_entry_trial||o.probe_prefix_hours!=6||o.hours!=6||
        o.output.empty()||!o.native_comp_trace.empty()))
        throw std::invalid_argument(
            "S4C NOAA WATER sixthhour requires full 6h source, "
            "exactly 6 committed G14 hours and no mixed trials/trace");
    if(o.probe_prefix_hours>o.hours)
        throw std::invalid_argument("S4B3 prefix exceeds complete declared G14 hours");
    return o;
}


// S4-R1c5b0: an OBSERVATION of an already completed native G14 transaction.
// Neither array here can ever be passed back into the solver. Keeping the
// 17-stage actor unchanged is essential for the C1/C2 scientific baseline.
static void append_committed_native_comp_trace(
    std::ostringstream& trace,std::size_t hour,std::int64_t end_epoch,
    std::size_t nx,std::size_t ny,const p6::NativeGridMemory& pre,
    const p6::NativeGridMemory& post) {
    const auto n=nx*ny;
    const auto check=[n](const p6::NativeGridMemory& m) {
        if(m.zi_m.size()!=n||m.ziconv_m.size()!=n||m.dptt_k.size()!=n)
            throw std::logic_error("R1c5b0 native state extent mismatch");
        for(std::size_t k=0;k<n;++k)
            if(!std::isfinite(m.zi_m[k])||!std::isfinite(m.ziconv_m[k])||
               !std::isfinite(m.dptt_k[k])||
               m.zi_m[k]<0.f||m.ziconv_m[k]<0.f)
                throw std::logic_error("R1c5b0 nonfinite or negative native COMP state");
    };
    check(pre);
    check(post);
    const auto emit=[&](const char* stage,const p6::NativeGridMemory& state) {
        for(std::size_t j=0;j<ny;++j)
            for(std::size_t i=0;i<nx;++i) {
                const auto k=j*nx+i;
                trace<<hour<<','<<end_epoch<<','<<stage<<','
                     <<i+1<<','<<j+1<<','<<std::hexfloat
                     <<state.zi_m[k]<<','<<state.ziconv_m[k]<<','
                     <<state.dptt_k[k]<<std::defaultfloat<<'\n';
            }
    };
    emit("PRE_DIAGNO",pre);
    emit("POST_COMP",post);
}
static void require_exact_native_state_carry(
    const p6::NativeGridMemory& prior_post,
    const p6::NativeGridMemory& current_pre) {
    const auto equal_bits=[](const std::vector<float>& a,
                             const std::vector<float>& b) {
        if(a.size()!=b.size())return false;
        for(std::size_t i=0;i<a.size();++i)
            if(std::bit_cast<std::uint32_t>(a[i])!=
               std::bit_cast<std::uint32_t>(b[i]))return false;
        return true;
    };
    if(!equal_bits(prior_post.zi_m,current_pre.zi_m)||
       !equal_bits(prior_post.ziconv_m,current_pre.ziconv_m)||
       !equal_bits(prior_post.dptt_k,current_pre.dptt_k))
        throw std::logic_error(
            "R1c5b0 prior committed native ZI/ZICONV/DPTT not carried into next G14 hour");
}

int main(int argc, char** argv) {
    try {
        const auto opt=parse_args(argc,argv);
        if(opt.water_source_preflight_only) {
            // Genuine original G19 + G14 UTC/shape checks, with the already
            // source-audited G38 neutral-water HFLUX inputs. No G26/G26B,
            // G14 transaction, P6F construction, or output path is available.
            const p6g::G19SourceFilePaths paths{
                opt.met,opt.geo,opt.surf,opt.up
            };
            const auto source=p6g::g19_load_original_source_case(paths,true);
            const auto scheduler=source.make_scheduler();
            if(scheduler.planned_hours()!=opt.hours||
               !scheduler.has_original_controls()||
               !source.research_noow_water_source_only)
                throw std::invalid_argument(
                    "S4C WATER preflight requires full original G19/G14 source interval");
            const auto admitted=p6g::s4b1_admit_source_only({
                static_cast<std::size_t>(source.grid.nx),
                static_cast<std::size_t>(source.grid.ny),
                9,source.stations.surface.size(),
                source.stations.upper.size(),scheduler.planned_hours(),true,true
            });
            const auto water=source.source_water_cells.size();
            if(water==0||water>admitted.cells_per_layer)
                throw std::invalid_argument(
                    "S4C WATER preflight requires authentic G38 water cells");
            std::cout<<"S4C_G19_WATER_SOURCE_PREFLIGHT=PASS_SOURCE_ONLY"
                     <<" HOURS="<<scheduler.planned_hours()
                     <<" SS="<<source.stations.surface.size()
                     <<" US="<<source.stations.upper.size()
                     <<" NX="<<source.grid.nx<<" NY="<<source.grid.ny
                     <<" WATER_CELLS="<<water
                     <<" LAND_CELLS="<<admitted.cells_per_layer-water
                     <<" G14_UTC=ADMITTED"
                     <<" G26_G26B_P6F=NOT_RUN"
                     <<" MET_DAT=NOT_WRITTEN"
                     <<" ORIGINAL_PARITY=NOT_RUN"
                     <<" PRODUCTION_ADMISSION=NOT_ACCEPTED\n";
            return 0;
        }
        if(std::filesystem::exists(opt.output))
            throw std::invalid_argument("S4B2 refuses to overwrite existing output");
        if(!opt.native_comp_trace.empty()) {
            const std::filesystem::path trace_path(opt.native_comp_trace);
            const std::filesystem::path out_path(opt.output);
            auto trace_staging=trace_path;
            trace_staging+=".s4b2-staging";
            if(trace_path.lexically_normal()==out_path.lexically_normal()||
               std::filesystem::exists(trace_path)||
               std::filesystem::exists(trace_staging))
                throw std::invalid_argument(
                    "R1c5b0 refuses occupied/equal native trace path");
        }
        const p6g::G19SourceFilePaths paths{
            opt.met,opt.geo,opt.surf,opt.up
        };
        // The source-only G19(true) water admission never grants production.
        // Research-only first-hour actor uses the SAME native 17-stage G65
        // implementation and immutable original G41/G43 model-internal
        // MISSFC source snapshot; no oracle or MET.DAT fields enter physics.
        const bool scoped_water_physics=(
            opt.water_firsthour_g14_trial_only||
            opt.water_secondhour_g14_trial_only||
            opt.water_thirdhour_g14_trial_only||
            opt.water_fourthhour_g14_trial_only||
            opt.water_fifthhour_g14_trial_only||
            opt.water_sixthhour_g14_trial_only);
        std::optional<p6g::G41SelectedNoowWaterFirstHourSource> water_original;
        auto source=p6g::g19_load_original_source_case(
            paths,scoped_water_physics);
        if(scoped_water_physics) {
            water_original.emplace(
                p6g::g41_load_selected_noow_water_first_hour_source(paths,true));
            if(source.grid.nx!=82||source.grid.ny!=85||
               source.stations.surface.size()!=2||
               source.stations.upper.size()!=1||
               source.source_water_cells.size()!=63||
               source.surface.hourly.size()!=6)
                throw std::invalid_argument(
                    "S4C firsthour G65 shared WATER trial is NOAA-shape scoped");
            const auto& raw=water_original->source.surface.hourly.front();
            const auto repaired=p6g::g43_original_comp_missfc_source_only(
                *water_original,raw,true);
            if(!repaired.source_comp_missfc_complete||
               repaired.original_comp_resolved.by_station.size()!=2||
               repaired.original_raw.by_station.size()!=2)
                throw std::logic_error("S4C firsthour original-source MISSFC missing");
            for(std::size_t i=0;i<2;++i) {
                const auto& before=repaired.original_raw.by_station[i];
                const auto& after=repaired.original_comp_resolved.by_station[i];
                if(!after.pressure_valid||!after.temperature_valid||
                   !after.humidity_valid||!after.cloud_valid||
                   !after.ceiling_valid||
                   before.wind_valid!=after.wind_valid||
                   before.wind_speed_mps!=after.wind_speed_mps||
                   before.wind_direction_deg!=after.wind_direction_deg||
                   before.precip_code!=after.precip_code||
                   before.precipitation_code_valid!=
                       after.precipitation_code_valid)
                    throw std::logic_error(
                        "S4C firsthour G43 altered original wind/precip");
            }
            // Raw P5 source remains immutable in G41. The G14-specific
            // detached input copies only CALMET COMP's five nonwind fields.
            source.surface.hourly.front()=repaired.original_comp_resolved;
            if(opt.water_secondhour_g14_trial_only||
               opt.water_thirdhour_g14_trial_only||
               opt.water_fourthhour_g14_trial_only||
               opt.water_fifthhour_g14_trial_only||
               opt.water_sixthhour_g14_trial_only) {
                // Second hour must use genuine unmodified P5 observations,
                // the same as G65's accepted positive second-hour G14 actor.
                // G43 is model-internal diagnostics ONLY at this stage; the
                // raw hour2 data must not be silently synthesized or altered.
                const auto& hour2_raw=water_original->source.surface.hourly.at(1);
                const auto hour2_missfc=p6g::g43_original_comp_missfc_source_only(
                    *water_original,hour2_raw,true);
                if(!hour2_missfc.source_comp_missfc_complete||
                   hour2_missfc.original_raw.by_station.size()!=2||
                   hour2_missfc.original_comp_resolved.by_station.size()!=2)
                    throw std::logic_error("S4C secondhour original G43 source unavailable");
                for(std::size_t i=0;i<2;++i) {
                    const auto& a=hour2_missfc.original_raw.by_station[i];
                    const auto& b=hour2_missfc.original_comp_resolved.by_station[i];
                    if(a.wind_valid!=b.wind_valid||
                       a.wind_speed_mps!=b.wind_speed_mps||
                       a.wind_direction_deg!=b.wind_direction_deg||
                       a.precip_code!=b.precip_code||
                       a.precipitation_code_valid!=b.precipitation_code_valid)
                        throw std::logic_error(
                            "S4C secondhour source G43 changed P5 wind/precip");
                }
            }
            if(opt.water_thirdhour_g14_trial_only||
               opt.water_fourthhour_g14_trial_only||
               opt.water_fifthhour_g14_trial_only||
               opt.water_sixthhour_g14_trial_only) {
                // Preserve raw P5; only detached G14 COMP model fields may
                // use G43's five nonwind nearest-station replacements.
                const auto& raw=water_original->source.surface.hourly.at(2);
                const auto resolved=p6g::g43_original_comp_missfc_source_only(
                    *water_original,raw,true);
                if(!resolved.source_comp_missfc_complete||
                   resolved.original_comp_resolved.by_station.size()!=2)
                    throw std::logic_error("S4C thirdhour genuine G43 incomplete");
                for(std::size_t i=0;i<2;++i) {
                    const auto& before=raw.by_station[i];
                    const auto& after=resolved.original_comp_resolved.by_station[i];
                    if(!after.pressure_valid||!after.temperature_valid||
                       !after.humidity_valid||!after.cloud_valid||
                       !after.ceiling_valid||
                       before.wind_valid!=after.wind_valid||
                       before.wind_speed_mps!=after.wind_speed_mps||
                       before.wind_direction_deg!=after.wind_direction_deg||
                       before.precip_code!=after.precip_code||
                       before.precipitation_code_valid!=after.precipitation_code_valid)
                        throw std::logic_error(
                            "S4C thirdhour G43 damaged P5 wind/precip");
                }
                source.surface.hourly.at(2)=resolved.original_comp_resolved;
            }
            if(opt.water_fourthhour_g14_trial_only||
               opt.water_fifthhour_g14_trial_only||
               opt.water_sixthhour_g14_trial_only) {
                // Raw hour4 P5 wind/precip MUST remain identical. Original
                // CALMET COMP repairs only model-internal five nonwind fields.
                const auto& raw=water_original->source.surface.hourly.at(3);
                const auto resolved=p6g::g43_original_comp_missfc_source_only(
                    *water_original,raw,true);
                if(!resolved.source_comp_missfc_complete||
                   resolved.original_raw.end!=raw.end||
                   resolved.original_comp_resolved.end!=raw.end||
                   resolved.original_comp_resolved.by_station.size()!=2)
                    throw std::logic_error("S4C fourthhour genuine G43 invalid");
                for(std::size_t i=0;i<2;++i) {
                    const auto& a=raw.by_station[i];
                    const auto& b=resolved.original_comp_resolved.by_station[i];
                    if(!b.pressure_valid||!b.temperature_valid||
                       !b.humidity_valid||!b.cloud_valid||!b.ceiling_valid||
                       a.wind_valid!=b.wind_valid||
                       a.wind_speed_mps!=b.wind_speed_mps||
                       a.wind_direction_deg!=b.wind_direction_deg||
                       a.precip_code!=b.precip_code||
                       a.precipitation_code_valid!=b.precipitation_code_valid)
                        throw std::logic_error(
                            "S4C fourthhour G43 modified P5 wind/precip");
                }
                source.surface.hourly.at(3)=resolved.original_comp_resolved;
            }
            if(opt.water_fifthhour_g14_trial_only||
               opt.water_sixthhour_g14_trial_only) {
                // The fifth-hour G43 source is a detached model-internal
                // COMP five-nonwind replacement; original wind and precip
                // remain unchanged and the physical G14 source stays scoped.
                const auto& raw=water_original->source.surface.hourly.at(4);
                const auto resolved=p6g::g43_original_comp_missfc_source_only(
                    *water_original,raw,true);
                if(!resolved.source_comp_missfc_complete||
                   resolved.original_raw.end!=raw.end||
                   resolved.original_comp_resolved.end!=raw.end||
                   resolved.original_comp_resolved.by_station.size()!=2)
                    throw std::logic_error("S4C fifthhour genuine G43 invalid");
                for(std::size_t i=0;i<2;++i) {
                    const auto& a=raw.by_station[i];
                    const auto& b=resolved.original_comp_resolved.by_station[i];
                    if(!b.pressure_valid||!b.temperature_valid||
                       !b.humidity_valid||!b.cloud_valid||!b.ceiling_valid||
                       a.wind_valid!=b.wind_valid||
                       a.wind_speed_mps!=b.wind_speed_mps||
                       a.wind_direction_deg!=b.wind_direction_deg||
                       a.precip_code!=b.precip_code||
                       a.precipitation_code_valid!=b.precipitation_code_valid)
                        throw std::logic_error(
                            "S4C fifthhour G43 modified P5 wind/precip");
                }
                source.surface.hourly.at(4)=resolved.original_comp_resolved;
            }
            if(opt.water_sixthhour_g14_trial_only) {
                // Original P5 winds and rain are immutable, only detached
                // G14 COMP nonwind fields may be repaired for sixth hour.
                const auto& raw=water_original->source.surface.hourly.at(5);
                const auto resolved=p6g::g43_original_comp_missfc_source_only(
                    *water_original,raw,true);
                if(!resolved.source_comp_missfc_complete||
                   resolved.original_raw.end!=raw.end||
                   resolved.original_comp_resolved.end!=raw.end||
                   resolved.original_comp_resolved.by_station.size()!=2)
                    throw std::logic_error("S4C sixthhour genuine G43 invalid");
                for(std::size_t i=0;i<2;++i) {
                    const auto& a=raw.by_station[i];
                    const auto& b=resolved.original_comp_resolved.by_station[i];
                    if(!b.pressure_valid||!b.temperature_valid||
                       !b.humidity_valid||!b.cloud_valid||!b.ceiling_valid||
                       a.wind_valid!=b.wind_valid||
                       a.wind_speed_mps!=b.wind_speed_mps||
                       a.wind_direction_deg!=b.wind_direction_deg||
                       a.precip_code!=b.precip_code||
                       a.precipitation_code_valid!=b.precipitation_code_valid)
                        throw std::logic_error(
                            "S4C sixthhour G43 modified original P5 wind/precip");
                }
                source.surface.hourly.at(5)=resolved.original_comp_resolved;
            }
        }
        auto scheduler=source.make_scheduler();
        if(!scheduler.has_original_controls() ||
           scheduler.planned_hours()!=opt.hours)
            throw std::invalid_argument(
                "S4B2 requested hours must match complete real G14 source window");
        const auto admission=p6g::s4b1_admit_source_only({
            static_cast<std::size_t>(source.grid.nx),
            static_cast<std::size_t>(source.grid.ny),
            9,
            source.stations.surface.size(),
            source.stations.upper.size(),
            scheduler.planned_hours(),true,true
        });
        const auto executed_hours=opt.probe_prefix_hours>0?opt.probe_prefix_hours:opt.hours;
        // S4-E bounded staging authority: the selected CLI retains all
        // emitted 45-field hours in memory before whole-file serialization.
        // This is only a RAW field-value lower bound, NOT a peak RSS cap.
        // Budget applies to emitted hours when this is a prefix probe.
        if(opt.max_retained_field_bytes!=0) {
            const auto raw=p6g::s4b1_checked_product(
                admission.one_hour_raw_field_bytes,executed_hours);
            if(raw>opt.max_retained_field_bytes)
                throw std::invalid_argument(
                    "S4E source selected G14 output exceeds caller raw field byte budget");
        }
        // Trace is explicitly six-hour bounded evidence, not an unrelated
        // 143h file/field retention expansion (that work belongs to S5).
        if(!opt.native_comp_trace.empty() &&
           (executed_hours!=6||admission.input.nx*admission.input.ny>10000))
            throw std::invalid_argument(
                "R1c5b0 native COMP trace limited to six hours and <=10000 cells");
        std::ostringstream native_trace;
        p6::NativeGridMemory last_native_post;
        if(!opt.native_comp_trace.empty())
            native_trace<<"hour_index,end_epoch_s,stage,i,j,zi_m,ziconv_m,dptt_k\n";
        p6g::G18D2StationClockAuthority clocks;
        std::optional<cteas::p6f::Calmet21File> all_hours;
        std::optional<p6g::G66NativeHour2WaterState> next_native_water_prior;
        for(std::size_t hour=0;hour<executed_hours;++hour) {
            p6::NativeGridMemory before_native_comp;
            if(!opt.native_comp_trace.empty()||
               opt.water_secondhour_g14_trial_only||
               opt.water_thirdhour_g14_trial_only||
               opt.water_fourthhour_g14_trial_only||
               opt.water_fifthhour_g14_trial_only||
               opt.water_sixthhour_g14_trial_only) {
                before_native_comp=scheduler.committed_memory();
                if(hour>0)require_exact_native_state_carry(
                    last_native_post,before_native_comp);
            }
            std::optional<cteas::p6f::Calmet21File> accepted;
            G34BSelectedOnlyHour* land_active=nullptr;
            p6g::G65RealNoaaFirstHourActor* water_active=nullptr;
            p6g::G65RealNoaaSecondHourActor* water_second_active=nullptr;
            p6g::G65RealNoaaThirdHourTrialActor* water_third_active=nullptr;
            p6g::G65RealNoaaFourthHourTrialActor* water_fourth_active=nullptr;
            p6g::G65RealNoaaFifthHourTrialActor* water_fifth_active=nullptr;
            p6g::G65RealNoaaSixthHourTrialActor* water_sixth_active=nullptr;
            bool published=false;
            scheduler.advance_with_fresh_physics(
                [&](const p6g::MultiHourFrame& live)
                    ->std::unique_ptr<p6g::MultiHourPhysics> {
                    if(live.hour_index!=hour||scheduler.completed_hours()!=hour)
                        throw std::logic_error("S4B2 duplicated/omitted real source hour");
                    if(scoped_water_physics) {
                        if(!water_original||hour>5||
                           (hour>0&&!opt.water_secondhour_g14_trial_only&&
                            !opt.water_thirdhour_g14_trial_only&&
                            !opt.water_fourthhour_g14_trial_only&&
                            !opt.water_fifthhour_g14_trial_only&&
                            !opt.water_sixthhour_g14_trial_only)||
                           (hour==2&&!opt.water_thirdhour_g14_trial_only&&
                            !opt.water_fourthhour_g14_trial_only&&
                            !opt.water_fifthhour_g14_trial_only&&
                            !opt.water_sixthhour_g14_trial_only)||
                           (hour==3&&!opt.water_fourthhour_g14_trial_only&&
                            !opt.water_fifthhour_g14_trial_only&&
                            !opt.water_sixthhour_g14_trial_only)||
                           (hour==4&&!opt.water_fifthhour_g14_trial_only&&
                            !opt.water_sixthhour_g14_trial_only)||
                           (hour==5&&!opt.water_sixthhour_g14_trial_only))
                            throw std::logic_error(
                                "S4C G65 WATER actor outside admitted hour");
                        if(hour==0) {
                            auto current=std::make_unique<
                                p6g::G65RealNoaaFirstHourActor>(
                                    scheduler,clocks,source,*water_original);
                            water_active=current.get();
                            return current;
                        }
                        if(&live.previous!=&scheduler.committed_memory()||
                           !clocks.has_published_hour())
                            throw std::logic_error(
                                "S4C secondhour cannot inherit uncommitted G14 memory");
                        if(hour==1) {
                            auto current=std::make_unique<
                                p6g::G65RealNoaaSecondHourActor>(
                                    scheduler,clocks,source,*water_original);
                            water_second_active=current.get();
                            return current;
                        }
                        if(!next_native_water_prior||
                           !next_native_water_prior->explicitly_native_p6f_origin||
                           next_native_water_prior->end!=source.surface.hourly.at(hour-1).end||
                           next_native_water_prior->begin!=source.surface.hourly.at(hour-1).start||
                           next_native_water_prior->ustar_mps.size()!=6970||
                           next_native_water_prior->el_m.size()!=6970)
                            throw std::logic_error(
                                "S4C hour3 missing native hour2 P6F water history");
                        if(hour==2) {
                            auto current=std::make_unique<
                                p6g::G65RealNoaaThirdHourTrialActor>(
                                    scheduler,clocks,source,*water_original,
                                    *next_native_water_prior);
                            water_third_active=current.get();
                            return current;
                        }
                        if(hour==3) {
                            auto current=std::make_unique<
                                p6g::G65RealNoaaFourthHourTrialActor>(
                                    scheduler,clocks,source,*water_original,
                                    *next_native_water_prior);
                            water_fourth_active=current.get();
                            return current;
                        }
                        if(hour==4) {
                            auto current=std::make_unique<
                                p6g::G65RealNoaaFifthHourTrialActor>(
                                    scheduler,clocks,source,*water_original,
                                    *next_native_water_prior);
                            water_fifth_active=current.get();
                            return current;
                        }
                        auto current=std::make_unique<
                            p6g::G65RealNoaaSixthHourTrialActor>(
                                scheduler,clocks,source,*water_original,
                                *next_native_water_prior);
                        water_sixth_active=current.get();
                        return current;
                    }
                    auto current=std::make_unique<G34BSelectedOnlyHour>(
                        scheduler,clocks,source,opt.g26_normal_entry_trial);
                    land_active=current.get();
                    return current;
                },
                [&](const p6g::MultiHourFrame& frame) {
                    if(water_active)accepted=water_active->precommit(frame);
                    else if(water_second_active)
                        accepted=water_second_active->precommit(frame).candidate_dataset;
                    else if(water_third_active)
                        accepted=water_third_active->precommit(frame).candidate_dataset;
                    else if(water_fourth_active)
                        accepted=water_fourth_active->precommit(frame).candidate_dataset;
                    else if(water_fifth_active)
                        accepted=water_fifth_active->precommit(frame).candidate_dataset;
                    else if(water_sixth_active)
                        accepted=water_sixth_active->precommit(frame).candidate_dataset;
                    else if(land_active)accepted=land_active->precommit(frame);
                    else throw std::logic_error("S4B2 actor missing");
                    if(!accepted||accepted->hourly.size()!=45)
                        throw std::logic_error("S4B2 non-original-format P6F precommit");
                },
                [&](p6g::MultiHourPhysics&,
                    const p6g::MultiHourFrame& frame,
                    const p6g::UnifiedMultistationHourlyScheduler& owner) {
                    if((!land_active&&!water_active&&!water_second_active&&
                        !water_third_active&&!water_fourth_active&&
                        !water_fifth_active&&!water_sixth_active)||
                       owner.completed_hours()!=hour||
                       frame.hour_index!=hour)
                        throw std::logic_error("S4B2 causality/UTC boundary changed");
                },
                [&](p6g::MultiHourPhysics& physics,
                    const p6g::UnifiedMultistationHourlyScheduler&) noexcept {
                    if(water_active) {
                        auto* actor=dynamic_cast<
                            p6g::G65RealNoaaFirstHourActor*>(&physics);
                        published=actor==water_active&&
                                  actor->publish_after_commit_noexcept();
                    } else if(water_second_active) {
                        auto* actor=dynamic_cast<
                            p6g::G65RealNoaaSecondHourActor*>(&physics);
                        published=actor==water_second_active&&
                                  actor->publish_after_commit_noexcept();
                    } else if(water_third_active) {
                        auto* actor=dynamic_cast<
                            p6g::G65RealNoaaThirdHourTrialActor*>(&physics);
                        published=actor==water_third_active&&
                                  actor->publish_after_commit_noexcept();
                    } else if(water_fourth_active) {
                        auto* actor=dynamic_cast<
                            p6g::G65RealNoaaFourthHourTrialActor*>(&physics);
                        published=actor==water_fourth_active&&
                                  actor->publish_after_commit_noexcept();
                    } else if(water_fifth_active) {
                        auto* actor=dynamic_cast<
                            p6g::G65RealNoaaFifthHourTrialActor*>(&physics);
                        published=actor==water_fifth_active&&
                                  actor->publish_after_commit_noexcept();
                    } else if(water_sixth_active) {
                        auto* actor=dynamic_cast<
                            p6g::G65RealNoaaSixthHourTrialActor*>(&physics);
                        published=actor==water_sixth_active&&
                                  actor->publish_after_commit_noexcept();
                    } else {
                        auto* actor=dynamic_cast<G34BSelectedOnlyHour*>(&physics);
                        published=actor==land_active&&
                                  actor->publish_after_commit_noexcept();
                    }
                });
            if(!published||!accepted||scheduler.completed_hours()!=hour+1||
               !clocks.has_published_hour())
                throw std::runtime_error("S4B2 AA/BB/CGAMMA/COMP commit incomplete");
            if((opt.water_thirdhour_g14_trial_only||
                opt.water_fourthhour_g14_trial_only||
                opt.water_fifthhour_g14_trial_only||
                opt.water_sixthhour_g14_trial_only)&&
               (hour==1||
                ((opt.water_fourthhour_g14_trial_only||
                  opt.water_fifthhour_g14_trial_only||
                  opt.water_sixthhour_g14_trial_only)&&hour==2)||
                ((opt.water_fifthhour_g14_trial_only||
                  opt.water_sixthhour_g14_trial_only)&&hour==3)||
                (opt.water_sixthhour_g14_trial_only&&hour==4))) {
                const auto expected_end=source.surface.hourly.at(hour).end;
                if(clocks.latest_upper_hour()!=expected_end||
                   clocks.latest_gamma_hour()!=expected_end)
                    throw std::logic_error(
                        "S4C hour2 committed clocks disagree with native P6F");
                next_native_water_prior.emplace(p6g::g65_native_hour2_water_from_p6f(
                    *accepted,expected_end));
            }
            if(!opt.native_comp_trace.empty()||
               opt.water_secondhour_g14_trial_only||
               opt.water_thirdhour_g14_trial_only||
               opt.water_fourthhour_g14_trial_only||
               opt.water_fifthhour_g14_trial_only||
               opt.water_sixthhour_g14_trial_only) {
                const auto& post=scheduler.committed_memory();
                const auto end=source.surface.hourly.at(hour).end;
                if(source.surface.hourly.at(hour).start+
                      std::chrono::hours{1}!=end||
                   (hour>0&&
                    source.surface.hourly.at(hour-1).end!=
                      source.surface.hourly.at(hour).start))
                    throw std::logic_error(
                        "R1c5b0 native COMP source chronology discontinuity");
                if(!opt.native_comp_trace.empty())
                    append_committed_native_comp_trace(
                        native_trace,hour,end.time_since_epoch().count(),
                        admission.input.nx,admission.input.ny,
                        before_native_comp,post);
                last_native_post=post;
            }
            if(!all_hours)all_hours=std::move(accepted);
            else {
                auto& combined=*all_hours;
                auto& next=*accepted;
                if(combined.header.nx!=next.header.nx||
                   combined.header.ny!=next.header.ny||
                   combined.header.nssta!=next.header.nssta||
                   combined.header.nusta!=next.header.nusta||
                   combined.statics.zface_m!=next.statics.zface_m||
                   combined.statics.nears!=next.statics.nears||
                   combined.statics.elev_m!=next.statics.elev_m||
                   combined.hourly.size()!=hour*45)
                    throw std::logic_error("S4B2 cross-hour original static drift");
                combined.hourly.insert(combined.hourly.end(),
                    std::make_move_iterator(next.hourly.begin()),
                    std::make_move_iterator(next.hourly.end()));
                combined.header.irlg=static_cast<int>(hour+1);
                combined.header.end_year=next.header.end_year;
                combined.header.end_month=next.header.end_month;
                combined.header.end_day=next.header.end_day;
                combined.header.end_hour=next.header.end_hour;
                combined.header.end_second=next.header.end_second;
            }
        }
        // Six-hour research commits a complete original source window;
        // never classify it as a partial probe solely due to its opt-in CLI.
        if(opt.probe_prefix_hours==0||opt.water_sixthhour_g14_trial_only)
            scheduler.require_complete();
        else if(scheduler.completed_hours()!=executed_hours)
            throw std::logic_error("S4B3 incomplete selected G14 probe prefix");
        if(!all_hours||all_hours->hourly.size()!=executed_hours*45||
           all_hours->header.irlg!=static_cast<int>(executed_hours))
            throw std::logic_error("S4B2 missing exact 45 original-format records/hour");
        const auto bytes=cteas::p6f::serialize_calmet_dat21(*all_hours);
        const std::filesystem::path target(opt.output);
        auto staging=target;
        staging+=".s4b2-staging";
        if(std::filesystem::exists(staging))
            throw std::invalid_argument("S4B2 refuses occupied output staging path");
        {
            std::ofstream output(staging,std::ios::binary|std::ios::trunc);
            if(!output)throw std::runtime_error("S4B2 cannot stage candidate MET");
            output.write(reinterpret_cast<const char*>(bytes.data()),
                         static_cast<std::streamsize>(bytes.size()));
            output.flush();
            if(!output) {
                output.close();
                std::filesystem::remove(staging);
                throw std::runtime_error("S4B2 incomplete candidate MET write");
            }
        }
        std::filesystem::path trace_staging;
        if(!opt.native_comp_trace.empty()) {
            trace_staging=std::filesystem::path(opt.native_comp_trace);
            trace_staging+=".s4b2-staging";
            std::ofstream evidence(trace_staging,std::ios::binary|std::ios::trunc);
            if(!evidence) {
                std::filesystem::remove(staging);
                throw std::runtime_error("R1c5b0 cannot stage native state trace");
            }
            const auto data=native_trace.str();
            evidence.write(data.data(),static_cast<std::streamsize>(data.size()));
            evidence.flush();
            if(!evidence) {
                evidence.close();
                std::filesystem::remove(trace_staging);
                std::filesystem::remove(staging);
                throw std::runtime_error("R1c5b0 incomplete native state trace");
            }
        }
        try {
            std::filesystem::rename(staging,target);
            if(!opt.native_comp_trace.empty())
                std::filesystem::rename(trace_staging,opt.native_comp_trace);
        }catch(...) {
            std::filesystem::remove(staging);
            if(!trace_staging.empty())std::filesystem::remove(trace_staging);
            if(!opt.native_comp_trace.empty())std::filesystem::remove(target);
            throw;
        }
        if(!opt.native_comp_trace.empty())
            std::cout<<"S4R1C5B0_NATIVE_G14_POSTCOMP_STATE_TRACE=PRODUCED_UNVERIFIED"
                     <<" HOURS="<<executed_hours
                     <<" SOURCE="<<"NATIVE_CPP_ONLY"
                     <<" ORIGINAL_6H_PARITY=NOT_RUN\n";
        std::cout<<"S4B2_SELECTED_G14_17_STAGE_CANDIDATE=PRODUCED_UNVERIFIED"
                 <<" HOURS="<<executed_hours
                 <<" DECLARED_SOURCE_HOURS="<<admission.input.hours
                 <<" PREFIX_PROBE="<<(opt.probe_prefix_hours>0?"YES":"NO")
                 <<" SS="<<admission.input.surface_stations
                 <<" US="<<admission.input.upper_stations
                 <<" NX="<<admission.input.nx
                 <<" NY="<<admission.input.ny
                 <<" FIELDS="<<executed_hours*45
                 <<" RETAINED_RAW_FIELD_BYTES_MIN="
                 <<p6g::s4b1_checked_product(
                     admission.one_hour_raw_field_bytes,executed_hours)
                 <<" VENDOR_CALMET_PARITY=NOT_RUN"
                 <<" G26_NORMAL_ENTRY_TRIAL="<<(opt.g26_normal_entry_trial?"YES":"NO")
                 <<" S4C_SHARED_G65_WATER_FIRSTHOUR="
                 <<(opt.water_firsthour_g14_trial_only?"YES":"NO")
                 <<" S4C_SHARED_G65_WATER_SECONDHOUR="
                 <<(opt.water_secondhour_g14_trial_only?"YES":"NO")
                 <<" S4C_SHARED_G65_WATER_THIRDHOUR="
                 <<(opt.water_thirdhour_g14_trial_only?"YES":"NO")
                 <<" S4C_SHARED_G65_WATER_FOURTHHOUR="
                 <<(opt.water_fourthhour_g14_trial_only?"YES":"NO")
                 <<" S4C_SHARED_G65_WATER_FIFTHHOUR="
                 <<(opt.water_fifthhour_g14_trial_only?"YES":"NO")
                 <<" S4C_SHARED_G65_WATER_SIXTHHOUR="
                 <<(opt.water_sixthhour_g14_trial_only?"YES":"NO")
                 <<" PRODUCTION_ADMISSION=NOT_ACCEPTED\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"S4B2_FAIL_CLOSED "<<e.what()<<"\n";
        return 2;
    }
}
