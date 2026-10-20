// S4-B2: one experimental, source-backed P6 G14 selected-physics driver.
// Shares the EXACT physical hour actor with frozen C2 G34B; does not alter
// C1/C2 comparison baselines or claim production/original-vendor acceptance.
// G19 owns READCF, original station IDs and genuine source UTC brackets;
// G14 owns PREPDI -> DIAGNO -> COMP -> P6F and every historical state commit.
#include "cteas/p6/p6g_s4b2_selected_hour.hpp"
#include "cteas/p6/p6g_s4b1_admission.hpp"
#include <cstddef>
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
    std::string met, geo, surf, output;
    std::vector<std::string> up;
    std::size_t hours=0;
    bool experimental=false;
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
        if(i+1>=argc)throw std::invalid_argument("S4B2 key missing argument");
        const std::string value=argv[++i];
        if(value.empty())throw std::invalid_argument("S4B2 empty argument");
        if(key=="--met" && o.met.empty())o.met=value;
        else if(key=="--geo" && o.geo.empty())o.geo=value;
        else if(key=="--surf" && o.surf.empty())o.surf=value;
        else if(key=="--up")o.up.push_back(value);
        else if(key=="--out" && o.output.empty())o.output=value;
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
       o.up.empty()||o.output.empty()||o.hours==0)
        throw std::invalid_argument(
            "S4B2 experimental ONLY: --selected-experimental --met met.inp "
            "--geo GEO.DAT --surf SURF.DAT --up UP1.DAT [--up UP2.DAT ...] "
            "--hours N --out candidate-met.dat; no production mode");
    return o;
}

int main(int argc, char** argv) {
    try {
        const auto opt=parse_args(argc,argv);
        if(std::filesystem::exists(opt.output))
            throw std::invalid_argument("S4B2 refuses to overwrite existing output");
        const p6g::G19SourceFilePaths paths{
            opt.met,opt.geo,opt.surf,opt.up
        };
        const auto source=p6g::g19_load_original_source_case(paths);
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
        p6g::G18D2StationClockAuthority clocks;
        std::optional<cteas::p6f::Calmet21File> all_hours;
        for(std::size_t hour=0;hour<opt.hours;++hour) {
            std::optional<cteas::p6f::Calmet21File> accepted;
            G34BSelectedOnlyHour* active=nullptr;
            bool published=false;
            scheduler.advance_with_fresh_physics(
                [&](const p6g::MultiHourFrame& live)
                    ->std::unique_ptr<p6g::MultiHourPhysics> {
                    if(live.hour_index!=hour||scheduler.completed_hours()!=hour)
                        throw std::logic_error("S4B2 duplicated/omitted real source hour");
                    auto current=std::make_unique<G34BSelectedOnlyHour>(
                        scheduler,clocks,source);
                    active=current.get();
                    return current;
                },
                [&](const p6g::MultiHourFrame& frame) {
                    if(!active)throw std::logic_error("S4B2 actor missing");
                    accepted=active->precommit(frame);
                    if(!accepted||accepted->hourly.size()!=45)
                        throw std::logic_error("S4B2 non-original-format P6F precommit");
                },
                [&](p6g::MultiHourPhysics&,
                    const p6g::MultiHourFrame& frame,
                    const p6g::UnifiedMultistationHourlyScheduler& owner) {
                    if(!active||owner.completed_hours()!=hour||
                       frame.hour_index!=hour)
                        throw std::logic_error("S4B2 causality/UTC boundary changed");
                },
                [&](p6g::MultiHourPhysics& physics,
                    const p6g::UnifiedMultistationHourlyScheduler&) noexcept {
                    auto* native=dynamic_cast<G34BSelectedOnlyHour*>(&physics);
                    published=native&&native->publish_after_commit_noexcept();
                });
            if(!published||!accepted||scheduler.completed_hours()!=hour+1||
               !clocks.has_published_hour())
                throw std::runtime_error("S4B2 AA/BB/CGAMMA/COMP commit incomplete");
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
        scheduler.require_complete();
        if(!all_hours||all_hours->hourly.size()!=admission.potential_field_records||
           all_hours->header.irlg!=static_cast<int>(opt.hours))
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
        try {std::filesystem::rename(staging,target);}
        catch(...) {std::filesystem::remove(staging);throw;}
        std::cout<<"S4B2_SELECTED_G14_17_STAGE_CANDIDATE=PRODUCED_UNVERIFIED"
                 <<" HOURS="<<opt.hours
                 <<" SS="<<admission.input.surface_stations
                 <<" US="<<admission.input.upper_stations
                 <<" NX="<<admission.input.nx
                 <<" NY="<<admission.input.ny
                 <<" FIELDS="<<admission.potential_field_records
                 <<" VENDOR_CALMET_PARITY=NOT_RUN"
                 <<" PRODUCTION_ADMISSION=NOT_ACCEPTED\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"S4B2_FAIL_CLOSED "<<e.what()<<"\n";
        return 2;
    }
}
