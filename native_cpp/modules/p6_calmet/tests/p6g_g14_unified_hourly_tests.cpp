// P6G G14: real multi-station input/clock binding, exact accepted #53
// 17-stage execution order, n-1 thermal-state ownership and strict rollback.
// This test's physical callback is explicitly SYNTHETIC. It does not qualify
// a multi-station CALMET physics implementation or original field parity.
#include "cteas/p6/p6g_unified_hourly.hpp"
#include "cteas/p6/p6g_g18d7_source_station_cell.hpp"
#include "cteas/p6/p6g_g18d2_station_clock_transaction.hpp"
#include "cteas/p6/p6g_g18e4_prepdi_stage_adapter.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <exception>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std::chrono;
namespace p6=cteas::calmet::p6;
namespace p6g=cteas::calmet::p6g;
static void check(bool yes, const char* why) {
    if (!yes)throw std::runtime_error(why);
}
template<class F> static void must_reject(F&& f,const char* why) {
    bool caught=false;
    try{f();}catch(const std::exception&){caught=true;}
    check(caught,why);
}
static p6g::StationSet stations() {
    p6g::StationSet v;
    const auto add=[](int id, float x, float y) {
        p6::DeckStation a{};
        a.id=id;a.local_x_m=x;a.local_y_m=y;
        return a;
    };
    v.surface={add(58321,10000.f,10000.f),add(58322,30000.f,30000.f)};
    v.upper={add(58424,20000.f,20000.f),add(58425,40000.f,40000.f)};
    return v;
}
static p6g::GeoGrid geo() {
    p6g::GeoGrid g;
    g.nx=12;g.ny=12;g.zone=50;g.hemisphere='N';g.grid_km=10.f;
    g.landuse.assign(144,10);
    return g;
}

// G18D7 regression: literal CALMET DIAGI uses REAL*4 (X/DGRID+1)
// assigned to INTEGER, then STHEOR clamps the 1-based index. Truncating
// X/DGRID before +1 selects the WRONG cell for near-boundary REAL*4 input.
static void original_station_cell_real4_boundary() {
    auto grid=geo();
    grid.grid_km=1.f;
    p6::DeckStation site{};
    site.local_x_m=std::nextafter(1000.f,0.f);
    site.local_y_m=100.f;
    check(p6g::g18d7_source_diagi_station_cell(grid,site)==1,
          "DIAGI REAL4 near 1km boundary did not round before INTEGER");
    site.local_x_m=std::nextafter(2000.f,0.f);
    check(p6g::g18d7_source_diagi_station_cell(grid,site)==2,
          "DIAGI REAL4 near 2km boundary did not round before INTEGER");
    site.local_x_m=100.f;
    site.local_y_m=std::nextafter(1000.f,0.f);
    check(p6g::g18d7_source_diagi_station_cell(grid,site)==12,
          "DIAGI REAL4 JST boundary was not source-equivalent");
    site.local_x_m=std::nextafter(12000.f,0.f);
    site.local_y_m=100.f;
    check(p6g::g18d7_source_diagi_station_cell(grid,site)==11,
          "STHEOR must clamp DIAGI rounded index to NX");
    site.local_x_m=12000.f;
    must_reject([&]{(void)p6g::g18d7_source_diagi_station_cell(grid,site);},
                "Outside scoped GEO station was silently clamped");
    grid.grid_km=10.f;
    site.local_x_m=std::nextafter(10000.f,0.f);
    check(p6g::g18d7_source_diagi_station_cell(grid,site)==0,
          "10km source REAL4 rounding unexpectedly changed station cell");
}

static p6g::SurfaceSeries surface(sys_seconds begin,std::size_t hours) {
    p6g::SurfaceSeries s;
    s.begin=begin;s.end=begin+std::chrono::hours{static_cast<int>(hours)};
    s.station_ids={58321,58322};
    s.hourly.reserve(hours);
    for(std::size_t h=0;h<hours;++h){
        p6g::SurfaceHour row;
        row.start=begin+std::chrono::hours{static_cast<int>(h)};
        row.end=row.start+std::chrono::hours{1};
        row.by_station.resize(2);
        for(std::size_t st=0;st<2;++st){
            row.by_station[st].wind_valid=true;
            row.by_station[st].wind_speed_mps=static_cast<float>(st+3);
            row.by_station[st].wind_direction_deg=270.f;
        }
        s.hourly.push_back(std::move(row));
    }
    return s;
}
static std::vector<p6g::UpperSeries> upper(sys_seconds begin,
                                           std::size_t hours) {
    std::vector<p6g::UpperSeries> result(2);
    for(int st=0;st<2;++st){
        auto& v=result[static_cast<std::size_t>(st)];
        v.station_id=(st==0?58424:58425);v.pstop_hpa=500.f;
        v.begin=begin;v.end=begin+std::chrono::hours{static_cast<int>(hours)};
        // 12-hour bracketing throughout a 143h or 8784h model year;
        // midpoint model hour exactly at sounding uses NEXT 12h segment.
        for(int h=-12;h<=static_cast<int>(hours)+24;h+=12){
            p6::UpperSounding u;
            u.station_id=v.station_id;
            u.start=begin+std::chrono::hours{h};u.end=u.start;
            // Selected PREPDI/CGAMMA test needs true per-US thermal
            // soundings; these are explicitly SYNTHETIC, not vendor
            // multi-station meteorological acceptance inputs.
            for(int k=0;k<4;++k) {
                p6::UpperLevel level;
                level.height_valid=true;
                level.temperature_valid=true;
                level.height_lgl_m=static_cast<float>(k*500);
                level.temperature_k=285.f+static_cast<float>(st+k*2)+
                    static_cast<float>(h)*.001f;
                u.data.push_back(level);
            }
            v.soundings.push_back(std::move(u));
        }
    }
    return result;
}
struct SyntheticNativePhysics final : p6g::MultiHourPhysics {
    bool throw_at_mixht=false,inject_oracle=false,omit_w=false;
    bool expect_source_controls=false;
    bool varied_upper_ziconv=false;
    p6g::G18E4SelectedPrepdiStageAdapter* selected_prepdi=nullptr;
    std::size_t runs=0;
    std::vector<p6::NativeHourStage> order;
    p6::NativeHourStageResult run(p6::NativeHourStage stage,
                                  p6g::MultiHourFrame& f) override {
        order.push_back(stage);
        const auto n=static_cast<std::size_t>(f.grid.nx)*f.grid.ny;
        if(expect_source_controls)
            check(f.source_controls!=nullptr&&
                  f.source_controls->bias[0]==-1.f&&
                  f.source_controls->rmax1_km==100.f,
                  "G15 did not deliver source-effective controls into CALMET stage");
        else
            check(f.source_controls==nullptr,
                  "in-memory G14 test unexpectedly received forged original met.inp");
        check(f.surface.by_station.size()==2 && f.input.upper.size()==2 &&
              f.stations.surface.size()==2 && f.stations.upper.size()==2,
              "2SS+2US were not bound into the hourly stage frame");
        check(f.surface.end==f.input.end,"SURF/UP timestamp mismatch");
        check(f.previous.ziconv_m.size()==n,"n-1 native thermal state absent");
        check(f.previous.ziconv_m[0]==static_cast<float>(f.hour_index),
              "previous hour ZICONV was not used");
        if(stage==p6::NativeHourStage::PrepdiPreviousZiconv&&selected_prepdi) {
            // G14, not the test caller, executes selected multi-US PREPDI.
            selected_prepdi->run_selected(stage,f,true);
            const auto& up=selected_prepdi->selected_upper_for(f);
            const auto& gamma=selected_prepdi->selected_gamma_for(f);
            check(up.station_ids==std::vector<int>({58424,58425})&&
                  gamma.station_ids==up.station_ids&&
                  gamma.lapse.size()==2&&up.justa.size()==2,
                  "G18E4 2US PREPDI AA/BB + CGAMMA not joined to G14");
            for(const auto& lapse:gamma.lapse)
                check(std::isfinite(lapse.kelvin_per_m),
                      "G18E4 source CGAMMA invalid lapse");
        }
        if(stage==p6::NativeHourStage::DiagnoStheorElustr2Mixhtst)
            f.next.dptt_k[0]=static_cast<float>(f.hour_index+7);
        if(stage==p6::NativeHourStage::CompGridMixht){
            check(f.next.dptt_k[0]==static_cast<float>(f.hour_index+7),
                  "station DPTT DIAGNO mutation did not reach COMP");
            if(throw_at_mixht) throw std::runtime_error("synthetic stage failure");
            std::fill(f.next.zi_m.begin(),f.next.zi_m.end(),
                      static_cast<float>(f.hour_index+2));
            std::fill(f.next.ziconv_m.begin(),f.next.ziconv_m.end(),
                      static_cast<float>(f.hour_index+1));
            if(varied_upper_ziconv) {
                // The two USs must read *independent* prior ZICONV cells
                // through frozen #53 upper_reference_cell, not SS NEARU.
                for(std::size_t i=0;i<f.stations.upper.size();++i) {
                    const auto& site=f.stations.upper[i];
                    const auto pos=p6::upper_reference_cell(
                        {site.local_x_m,site.local_y_m},
                        f.grid.nx,f.grid.ny,f.grid.grid_km*1000.f);
                    const auto index=static_cast<std::size_t>(pos.j-1)*
                        static_cast<std::size_t>(f.grid.nx)+
                        static_cast<std::size_t>(pos.i-1);
                    f.next.ziconv_m.at(index)=
                        static_cast<float>(f.hour_index+1)+
                        (i==0?250.f:0.75f);
                }
            }
        }
        if(stage==p6::NativeHourStage::CommitOutput) {
            // Fabricated data only for testing the full-field gate, never a
            // claim of CALMET Fortran numerical equivalence.
            f.fields.u_mps.assign(n*9,3.f);
            f.fields.v_mps.assign(n*9,4.f);
            if(!omit_w) f.fields.w_face_mps.assign(n*10,0.f);
            f.fields.temperature_k.assign(n*9,281.f);
            f.fields.qh_wm2.assign(n,20.f);
            f.fields.ustar_mps.assign(n,0.2f);
            f.fields.el_m.assign(n,-50.f);
            f.fields.wstar_mps.assign(n,0.1f);
            ++runs;
            if(inject_oracle)
                return {p6::NativeHourSource::OriginalFortranOracle,true};
        }
        return {p6::NativeHourSource::NativeCpp,true};
    }
};
static void case_hours(sys_seconds begin,std::size_t count){
    // Synthetic callback values remain synthetic. But the stage receives a
    // typed original-source control object through the SAME G14 authority.
    p6g::OriginalWindControls config;
    config.bias[0]=-1.f;config.rmax1_km=100.f;
    p6g::UnifiedMultistationHourlyScheduler sched(
        geo(),stations(),surface(begin,count),upper(begin,count),config);
    check(sched.planned_hours()==count,"declared hour count was truncated");
    SyntheticNativePhysics synthetic;
    synthetic.expect_source_controls=true;
    for(std::size_t hour=0;hour<count;++hour){
        synthetic.order.clear();
        sched.advance(synthetic);
        check(synthetic.order.size()==p6::kHefeiOriginalStageOrder.size()&&
              std::equal(synthetic.order.begin(),synthetic.order.end(),
                         p6::kHefeiOriginalStageOrder.begin()),
              "multi station solver diverged from #53 original stage order");
        check(sched.committed_memory().ziconv_m[0]==static_cast<float>(hour+1),
              "cross-hour state failed to commit");
    }
    sched.require_complete();
    check(synthetic.runs==count,"missing complete hourly output attempts");
    must_reject([&]{sched.advance(synthetic);},
                "unbounded year-end hours accepted");
}
// G18F1 exercises the actual new G14 factory entry. All 17 stages still
// pass through the one strict NativeCpp gate, but the executor is
// independently allocated and destroyed on EVERY attempt. The captured
// pointer proves that the factory receives the exact live frame, not a
// stale detached next-hour preview. Numerical physics remain synthetic.
struct FreshOwnedPhysics final : p6g::MultiHourPhysics {
    SyntheticNativePhysics synthetic;
    const p6g::MultiHourFrame* live;
    std::size_t next_stage=0;
    int* destroyed=nullptr;
    bool stage_failure=false;
    bool oracle_failure=false;
    FreshOwnedPhysics(const p6g::MultiHourFrame& frame,int& counter,
                      bool fail_stage,bool fail_oracle)
        :live(&frame),destroyed(&counter),stage_failure(fail_stage),
         oracle_failure(fail_oracle) {
        synthetic.expect_source_controls=true;
    }
    ~FreshOwnedPhysics() override {++*destroyed;}
    p6::NativeHourStageResult run(
        p6::NativeHourStage stage,p6g::MultiHourFrame& frame) override {
        check(&frame==live,
              "G18F1 factory received copied preview rather than live G14 frame");
        check(next_stage<p6::kHefeiOriginalStageOrder.size() &&
              stage==p6::kHefeiOriginalStageOrder[next_stage],
              "G18F1 new owned physics was given a reordered/duplicate source stage");
        ++next_stage;
        if(stage_failure&&stage==p6::NativeHourStage::CompGridMixht)
            throw std::runtime_error("G18F1 injected stage failure");
        if(oracle_failure&&stage==p6::NativeHourStage::CommitOutput)
            return {p6::NativeHourSource::OriginalFortranOracle,true};
        return synthetic.run(stage,frame);
    }
};
static void case_fresh_owned_physics(sys_seconds begin) {
    p6g::OriginalWindControls deck;
    deck.bias[0]=-1.f;deck.rmax1_km=100.f;
    p6g::UnifiedMultistationHourlyScheduler sched(
        geo(),stations(),surface(begin,6),upper(begin,6),deck);
    std::size_t allocated=0;
    int destroyed=0;
    std::size_t published=0;
    bool postcommit_valid=true;
    // G18F1 final station-clock publication is strictly after G14
    // P6F verification but before the owned per-hour executor destructs.
    auto publish=[&](p6g::MultiHourPhysics& base,
                     const p6g::UnifiedMultistationHourlyScheduler& committed) noexcept {
        auto& owned=static_cast<FreshOwnedPhysics&>(base);
        ++published;
        postcommit_valid=postcommit_valid &&
            owned.next_stage==p6::kHefeiOriginalStageOrder.size() &&
            committed.completed_hours()==published &&
            committed.committed_memory().ziconv_m[0]==
                static_cast<float>(published) &&
            destroyed==static_cast<int>(allocated-1);
    };
    bool fail_stage=true,fail_oracle=false;
    auto factory=[&](const p6g::MultiHourFrame& live)
        ->std::unique_ptr<p6g::MultiHourPhysics> {
        check(live.hour_index==sched.completed_hours() &&
              &live.previous==&sched.committed_memory() &&
              live.input.end==live.surface.end &&
              live.source_controls==&sched.original_controls(),
              "G18F1 factory saw stale source data or different committed state");
        ++allocated;
        return std::make_unique<FreshOwnedPhysics>(
            live,destroyed,fail_stage,fail_oracle);
    };
    must_reject([&]{sched.advance_with_fresh_physics(
        [](const p6g::MultiHourFrame&)
            ->std::unique_ptr<p6g::MultiHourPhysics>{return nullptr;});
    },"G18F1 accepted absent owned native physics");
    check(allocated==0&&destroyed==0&&sched.completed_hours()==0,
          "G18F1 null factory advanced the G14 clock");
    must_reject([&]{sched.advance_with_fresh_physics(factory);},
                "G18F1 accepted interrupted source COMP without rollback");
    check(allocated==1&&destroyed==1&&
          sched.completed_hours()==0&&sched.committed_memory().ziconv_m[0]==0.f,
          "G18F1 native stage failure retained state or leaked executor");
    fail_stage=false;fail_oracle=true;
    must_reject([&]{sched.advance_with_fresh_physics(factory);},
                "G18F1 accepted original Fortran oracle as production physics");
    check(allocated==2&&destroyed==2&&sched.completed_hours()==0,
          "G18F1 oracle failure retained a poisoned physics object");
    fail_oracle=false;
    std::size_t checked=0;
    must_reject([&]{
        sched.advance_with_fresh_physics(factory,
          [&](const p6g::MultiHourFrame& result){
            ++checked;
            check(result.hour_index==0&&result.next.ziconv_m[0]==1.f,
                  "G18F1 precommit saw stale or uncomputed G14 COMP");
            throw std::runtime_error("G18F1 synthetic P6F rejection");
          },publish);
    },"G18F1 P6F failure committed prior-hour memory");
    check(published==0&&postcommit_valid,
          "G18F1 erroneously published station clocks after P6F failure");
    check(checked==1&&allocated==3&&destroyed==3&&
          sched.completed_hours()==0&&sched.committed_memory().ziconv_m[0]==0.f,
          "G18F1 failed P6F attempt was not isolated before retry");
    for(std::size_t h=0;h<6;++h) {
        sched.advance_with_fresh_physics(factory,
          [&](const p6g::MultiHourFrame& result){
            ++checked;
            check(result.hour_index==h &&
                  result.previous.ziconv_m[0]==static_cast<float>(h)&&
                  result.next.ziconv_m[0]==static_cast<float>(h+1),
                  "G18F1 accepted hour used stale n-1 CGAMMA/COMP memory");
          },publish);
        check(published==h+1&&postcommit_valid,
              "G18F1 publish was not after G14 memory commit/before executor destruction");
        check(sched.completed_hours()==h+1&&
              sched.committed_memory().ziconv_m[0]==static_cast<float>(h+1)&&
              allocated==h+4&&destroyed==static_cast<int>(h+4),
              "G18F1 reused native physics across successful source hours");
    }
    sched.require_complete();
    check(checked==7&&allocated==9&&destroyed==9&&
          published==6&&postcommit_valid,
          "G18F1 did not isolate the postcommit hook/executor per attempt");
    must_reject([&]{sched.advance_with_fresh_physics(factory);},
                "G18F1 accepted source hour after declared end of input");
    check(allocated==9&&destroyed==9,
          "G18F1 created a physics executor after final model hour");
}
// G18F1 selected PREPDI clock integration on a NEW owned G14 executor:
// real G18E4 AA/BB/CGAMMA runs at stage zero; all other fields in this
// case remain SYNTHETIC and may not assert multistation scientific parity.
struct FreshOwnedPrepdiPhysics final : p6g::MultiHourPhysics {
    p6g::G18E4SelectedPrepdiStageAdapter selected;
    SyntheticNativePhysics mock;
    const p6g::MultiHourFrame* live;
    int* destroyed;
    FreshOwnedPrepdiPhysics(
        const p6g::UnifiedMultistationHourlyScheduler& scheduler,
        p6g::G18D2StationClockAuthority& clocks,
        const std::string& deck,const p6g::MultiHourFrame& frame,
        int& destroyed_count)
        :selected(scheduler,clocks,deck),live(&frame),
         destroyed(&destroyed_count) {
        mock.expect_source_controls=true;
        mock.selected_prepdi=&selected;
    }
    ~FreshOwnedPrepdiPhysics() override {++*destroyed;}
    p6::NativeHourStageResult run(
        p6::NativeHourStage stage,p6g::MultiHourFrame& frame) override {
        check(&frame==live,
              "G18F1 PREPDI observed detached factory frame inside G14");
        const auto result=mock.run(stage,frame);
        if(stage==p6::NativeHourStage::PrepdiPreviousZiconv) {
            check(selected.staged()&&!selected.published()&&
                  !selected.try_publish_after_completed_g14_hour_noexcept(),
                  "G18F1 PREPDI clocks could publish ahead of G14");
            // A valid PREPDI candidate is ALREADY safe to publish only
            // after the imminent G14 physical/P6F commit. This check
            // neither publishes clocks nor advances the model hour.
            selected.require_publishable_before_g14_commit(frame);
            auto counterfeit=frame;
            must_reject([&]{
                selected.require_publishable_before_g14_commit(counterfeit);
            },"G18F2 station-clock preflight accepted a detached G14 frame");
        }
        return result;
    }
    [[nodiscard]] bool publish_noexcept() noexcept {
        return selected.try_publish_after_completed_g14_hour_noexcept();
    }
};
static void case_fresh_selected_prepdi_clock(sys_seconds begin) {
    p6g::OriginalWindControls controls;
    controls.bias[0]=-1.f;controls.rmax1_km=100.f;
    p6g::UnifiedMultistationHourlyScheduler sched(
        geo(),stations(),surface(begin,6),upper(begin,6),controls);
    p6g::G18D2StationClockAuthority clocks;
    const std::string deck=
        "! IUPT = -1 !\\n! IDIOPT2 = 0 !\\n! ZUPT = 200. !\\n";
    std::size_t made=0,published=0,preflighted=0;
    int destroyed=0;
    bool publication_valid=true,fail_preflight=false;
    auto maker=[&](const p6g::MultiHourFrame& frame)
        ->std::unique_ptr<p6g::MultiHourPhysics> {
        check(frame.hour_index==sched.completed_hours(),
              "G18F1 PREPDI factory constructed for a foreign source hour");
        ++made;
        return std::make_unique<FreshOwnedPrepdiPhysics>(
            sched,clocks,deck,frame,destroyed);
    };
    auto preflight=[&](p6g::MultiHourPhysics& base,
                       const p6g::MultiHourFrame& live,
                       const p6g::UnifiedMultistationHourlyScheduler& owner) {
        check(&owner==&sched && sched.completed_hours()==live.hour_index,
              "G18F2 precommit station-clock gate received foreign G14 owner");
        auto& owned=static_cast<FreshOwnedPrepdiPhysics&>(base);
        owned.selected.require_publishable_before_g14_commit(live);
        ++preflighted;
        if(fail_preflight)
            throw std::runtime_error("G18F2 injected station clock admission failure");
    };
    auto publisher=[&](p6g::MultiHourPhysics& base,
                       const p6g::UnifiedMultistationHourlyScheduler& committed) noexcept {
        auto& owned=static_cast<FreshOwnedPrepdiPhysics&>(base);
        publication_valid=publication_valid&&
            owned.selected.staged()&&!owned.selected.published()&&
            committed.completed_hours()==published+1 &&
            owned.publish_noexcept()&&owned.selected.published()&&
            destroyed==static_cast<int>(made-1);
        ++published;
    };
    must_reject([&]{
        sched.advance_with_fresh_physics(
            maker,[&](const p6g::MultiHourFrame& live) {
                // Explicit source-clock preflight is performed after
                // all 17 staged callbacks but before G14 memory commit.
                check(!clocks.has_published_hour()&&
                      sched.completed_hours()==0,
                      "G18F2 prematurely committed PREPDI clocks");
                // The callback has no access to a detached owner: its
                // source result can be obtained only on the same G14
                // frame inside the physics object.
                check(live.hour_index==0,
                      "G18F2 source P6F preflight wrong failed hour");
                throw std::runtime_error("G18F1 selected PREPDI P6F failure");
            },preflight,publisher);
    },"G18F1 selected PREPDI source clocks published after rejected P6F");
    check(made==1&&destroyed==1&&published==0&&preflighted==0&&
          !clocks.has_published_hour()&&sched.completed_hours()==0,
          "G18F2 P6F failure incorrectly reached station-clock preflight");
    // All physical stages and P6F pass, but clock admission fails.
    // An incomplete/stale PREPDI candidate must reject the entire hour
    // BEFORE committing physical memory, not leave an orphaned clock.
    fail_preflight=true;
    must_reject([&]{
        sched.advance_with_fresh_physics(
            maker,[](const p6g::MultiHourFrame&){},
            preflight,publisher);
    },"G18F2 failed clock preflight committed G14 physical memory");
    check(made==2&&destroyed==2&&preflighted==1&&published==0&&
          !clocks.has_published_hour()&&
          sched.completed_hours()==0&&
          sched.committed_memory().ziconv_m[0]==0.f,
          "G18F2 invalid PREPDI clock preflight poisoned physical hour");
    fail_preflight=false;
    for(std::size_t h=0;h<6;++h) {
        sched.advance_with_fresh_physics(
            maker,[&](const p6g::MultiHourFrame& frame){
                check(frame.hour_index==h&&
                      frame.previous.ziconv_m[0]==static_cast<float>(h)&&
                      frame.next.ziconv_m[0]==static_cast<float>(h+1)&&
                      sched.completed_hours()==h,
                      "G18F2 selected PREPDI preflight saw wrong prior-hour state");
                // The full G14 physical-hour validation runs next,
                // followed by noexcept source AA/BB + CGAMMA publish.
            },preflight,publisher);
        check(made==h+3&&destroyed==static_cast<int>(h+3)&&
              preflighted==h+2&&
              published==h+1&&publication_valid&&
              clocks.has_published_hour()&&
              clocks.latest_upper_hour()==begin+hours{static_cast<int>(h+1)}&&
              clocks.latest_gamma_hour()==begin+hours{static_cast<int>(h+1)},
              "G18F1 real selected AA/BB and per-US CGAMMA not atomically committed");
    }
    sched.require_complete();
}

 // S4-R1c9v: explicit third-hour G14 transaction contract. This is a
 // synthetic six-hour scheduler regression, NOT genuine NOAA physics parity.
 // It blocks accidental hour-three publication until real G64 stage16 has
 // its own source-native candidate and independent original-model audit.
static void case_third_hour_atomic_retry_contract(sys_seconds begin) {
    p6g::OriginalWindControls deck;
    deck.bias[0]=-1.f;deck.rmax1_km=100.f;
    p6g::UnifiedMultistationHourlyScheduler owner(
        geo(),stations(),surface(begin,6),upper(begin,6),deck);
    int destroyed=0;
    std::size_t allocated=0, published=0;
    auto committed_clock=begin;
    bool publish_order_ok=true;
    bool fail_stage=false,fail_p6f=false,fail_clock_preflight=false;
    bool preflight_ready=false;
    std::size_t precommit_calls=0, preflight_calls=0;
    auto factory=[&](const p6g::MultiHourFrame& live)
        ->std::unique_ptr<p6g::MultiHourPhysics> {
        check(live.hour_index==owner.completed_hours()&&
              live.surface.end==live.input.end&&
              &live.previous==&owner.committed_memory()&&
              live.source_controls==&owner.original_controls()&&
              live.previous.ziconv_m[0]==
                  static_cast<float>(owner.completed_hours()),
              "hour3 retry factory received detached/stale committed memory");
        ++allocated;
        return std::make_unique<FreshOwnedPhysics>(
            live,destroyed,fail_stage,false);
    };
    auto precommit=[&](const p6g::MultiHourFrame& live) {
        ++precommit_calls;
        check(live.hour_index==published&&
              live.previous.ziconv_m[0]==static_cast<float>(published)&&
              live.previous.dptt_k[0]==
                  (published==0?0.f:static_cast<float>(published+6))&&
              live.next.ziconv_m[0]==static_cast<float>(published+1)&&
              live.next.zi_m[0]==static_cast<float>(published+2)&&
              live.next.dptt_k[0]==static_cast<float>(published+7)&&
              owner.completed_hours()==published&&
              committed_clock==begin+hours{static_cast<int>(published)},
              "hour3 P6F precommit read a published/stale hour");
        if(fail_p6f)
            throw std::runtime_error("EXPECTED_HOUR3_P6F_REJECTION");
    };
    auto preflight=[&](p6g::MultiHourPhysics&,
                       const p6g::MultiHourFrame& live,
                       const p6g::UnifiedMultistationHourlyScheduler& committed) {
        ++preflight_calls;
        check(&committed==&owner&&
              live.hour_index==published&&
              committed.completed_hours()==published&&
              committed_clock==begin+hours{static_cast<int>(published)},
              "hour3 station clocks advanced ahead of G14");
        if(fail_clock_preflight)
            throw std::runtime_error("EXPECTED_HOUR3_CLOCK_REJECTION");
        preflight_ready=true;
    };
    auto publish=[&](p6g::MultiHourPhysics& physics,
                     const p6g::UnifiedMultistationHourlyScheduler& committed) noexcept {
        publish_order_ok=publish_order_ok&&preflight_ready&&
            &committed==&owner&&
            dynamic_cast<FreshOwnedPhysics*>(&physics)!=nullptr&&
            committed.completed_hours()==published+1&&
            committed.committed_memory().ziconv_m[0]==
                static_cast<float>(published+1)&&
            committed.committed_memory().zi_m[0]==
                static_cast<float>(published+2)&&
            committed.committed_memory().dptt_k[0]==
                static_cast<float>(published+7)&&
            committed_clock==begin+hours{static_cast<int>(published)};
        ++published;
        committed_clock=begin+hours{static_cast<int>(published)};
        preflight_ready=false;
    };
    auto advance=[&] {
        owner.advance_with_fresh_physics(factory,precommit,preflight,publish);
    };
    advance();
    advance();
    check(owner.completed_hours()==2&&published==2&&
          committed_clock==begin+hours{2}&&
          owner.committed_memory().ziconv_m[0]==2.f&&
          destroyed==static_cast<int>(allocated),
          "hour3 setup failed to commit the first two independent hours");
    const auto before=owner.committed_memory();
    const auto ensure_rolled_back=[&](std::size_t attempts) {
        check(owner.completed_hours()==2&&published==2&&
              committed_clock==begin+hours{2}&&
              owner.committed_memory().zi_m==before.zi_m&&
              owner.committed_memory().ziconv_m==before.ziconv_m&&
              owner.committed_memory().dptt_k==before.dptt_k&&
              allocated==attempts&&destroyed==static_cast<int>(attempts)&&
              !preflight_ready,
              "hour3 failed transaction published state/clocks or leaked executor");
        const auto next=owner.preview_next_hour();
        check(next.hour_index==2&&next.surface.start==begin+hours{2}&&
              &next.previous==&owner.committed_memory()&&
              next.next.ziconv_m==before.ziconv_m,
              "hour3 failed transaction poisoned its retry preview");
    };
    fail_stage=true;
    must_reject(advance,"hour3 COMP stage failure committed G14");
    fail_stage=false;
    ensure_rolled_back(3);
    check(precommit_calls==2&&preflight_calls==2,
          "hour3 interrupted COMP reached precommit/clock barrier");
    fail_p6f=true;
    must_reject(advance,"hour3 G64 precommit failure committed G14");
    fail_p6f=false;
    ensure_rolled_back(4);
    check(precommit_calls==3&&preflight_calls==2,
          "hour3 rejected P6F was passed to station-clock preflight");
    fail_clock_preflight=true;
    must_reject(advance,"hour3 station-clock preflight failure committed G14");
    fail_clock_preflight=false;
    ensure_rolled_back(5);
    check(precommit_calls==4&&preflight_calls==3,
          "hour3 PREPDI clock failure bypassed P6F candidate validation");
    advance();
    check(owner.completed_hours()==3&&published==3&&
          committed_clock==begin+hours{3}&&
          owner.committed_memory().ziconv_m[0]==3.f&&
          owner.preview_next_hour().previous.ziconv_m[0]==3.f&&
          precommit_calls==5&&preflight_calls==4,
          "hour3 positive G14 retry failed to publish atomic state");
    for(std::size_t i=3;i<6;++i)
        advance();
    owner.require_complete();
    check(publish_order_ok&&published==6&&allocated==9&&
          destroyed==9&&precommit_calls==8&&preflight_calls==7&&
          committed_clock==begin+hours{6},
          "hour3 retry contract changed six-hour G14 order or executor lifecycle");
}

int main(){
    try{
        original_station_cell_real4_boundary();
        case_fresh_owned_physics(sys_days{year{2024}/January/1});
        case_third_hour_atomic_retry_contract(sys_days{year{2024}/January/1});
        case_fresh_selected_prepdi_clock(sys_days{year{2024}/January/1});
        const auto jan1=sys_days{year{2024}/January/1};
        case_hours(jan1,1);
        case_hours(jan1,6);
        case_hours(jan1,143);
        case_hours(jan1,8784); // leap year 2024, 10km / 2SS / 2US
        p6g::UnifiedMultistationHourlyScheduler rollback(
            geo(),stations(),surface(jan1,6),upper(jan1,6));
        SyntheticNativePhysics mock;
        mock.throw_at_mixht=true;
        must_reject([&]{rollback.advance(mock);},"failed COMP/MIXHT was committed");
        check(rollback.completed_hours()==0&&
              rollback.committed_memory().ziconv_m[0]==0.f,
              "failed native hour changed the committed n-1 ZICONV");
        mock.throw_at_mixht=false;mock.inject_oracle=true;
        must_reject([&]{rollback.advance(mock);},"source-oracle injection was accepted");
        check(rollback.completed_hours()==0,"oracle attempt advanced clock");
        mock.inject_oracle=false;mock.omit_w=true;
        must_reject([&]{rollback.advance(mock);},"uncomputed WFACE was accepted");
        check(rollback.completed_hours()==0,"missing native WFACE advanced clock");
        mock.omit_w=false;
        // G18D1: the real G14 authority must offer a precommit barrier.
        // Even with all 17 stages marked native, failed output validation
        // cannot publish current ZICONV or advance source UTC time.
        std::size_t p6f_checked=0;
        must_reject([&]{
            rollback.advance_with_precommit(mock,
              [&](const p6g::MultiHourFrame& candidate) {
                ++p6f_checked;
                check(candidate.hour_index==0&&
                      candidate.previous.ziconv_m[0]==0.f&&
                      candidate.next.ziconv_m[0]==1.f&&
                      candidate.fields.temperature_k.size()==12*12*9,
                      "G18D1 G14 precommit candidate data incomplete");
                throw std::runtime_error("synthetic P6F readback failure");
              });
        },"G18D1 failed native P6F precommit gate advanced hour");
        check(p6f_checked==1&&rollback.completed_hours()==0&&
              rollback.committed_memory().ziconv_m[0]==0.f,
              "G18D1 P6F failure mutated accepted preceding-hour ZICONV");
        rollback.advance_with_precommit(mock,
          [&](const p6g::MultiHourFrame& candidate) {
            ++p6f_checked;
            check(candidate.hour_index==0&&
                  candidate.next.ziconv_m[0]==1.f,
                  "G18D1 P6F gate accepted stale stage-time candidate");
          });
        check(p6f_checked==2&&rollback.completed_hours()==1&&
              rollback.committed_memory().ziconv_m[0]==1.f,
              "G18D1 successful P6F precommit did not preserve atomic G14 hour");
        // The retry must not permit an arbitrary future-hour offset.
        rollback.advance_with_precommit(mock,
          [&](const p6g::MultiHourFrame& candidate) {
            check(candidate.hour_index==1&&
                  candidate.previous.ziconv_m[0]==1.f&&
                  candidate.next.ziconv_m[0]==2.f,
                  "G18D1 2nd hour re-read tentative rather than committed ZICONV");
          });
        check(rollback.completed_hours()==2&&
              rollback.committed_memory().ziconv_m[0]==2.f,
              "G18D1 successive 2SS/2US native hours lacked isolated histories");
        // G18D2: PREPDI AA/BB and per-US CGAMMA history are staged
        // from G14's *own* next-hour preview and cannot publish
        // on a failed precommit/oracle or to a foreign scheduler.
        p6g::OriginalWindControls deck_controls;
        deck_controls.bias[0]=-1.f;deck_controls.rmax1_km=100.f;
        p6g::UnifiedMultistationHourlyScheduler source(
            geo(),stations(),surface(jan1,6),upper(jan1,6),
            deck_controls);
        p6g::G18D2StationClockAuthority station_clocks;
        const std::string synthetic_deck=
            "! IUPT = -1 !\n! IDIOPT2 = 0 !\n! ZUPT = 200. !\n";
        must_reject([&]{
            (void)station_clocks.prepare_selected(source,synthetic_deck,false);
        },"G18D2 selected upper thermal clock misrepresented production acceptance");
        auto stage0=station_clocks.prepare_selected(source,synthetic_deck,true);
        check(stage0.hour_index==0&&stage0.observed.station_ids.size()==2&&
              stage0.cgamma.lapse.size()==2&&
              !station_clocks.has_published_hour(),
              "G18D2 source station transaction was not prepared off committed G14");
        must_reject([&]{
            station_clocks.publish_only_after_completed_g14(source,stage0);
        },"G18D2 source upper/CGAMMA published before G14 completed hour");
        SyntheticNativePhysics source_mock;
        source_mock.expect_source_controls=true;
        must_reject([&]{
            source.advance_with_precommit(source_mock,
              [](const p6g::MultiHourFrame&) {
                  throw std::runtime_error("G18D2 injected P6F write/read failure");
              });
        },"G18D2 stage accepted failed P6F original output");
        check(source.completed_hours()==0&&
              !station_clocks.has_published_hour()&&
              source.committed_memory().ziconv_m[0]==0.f,
              "G18D2 leaked upper/CGAMMA or previous ZICONV after P6F failure");
        must_reject([&]{
            station_clocks.publish_only_after_completed_g14(source,stage0);
        },"G18D2 accepted station history despite failed P6F barrier");
        source.advance_with_precommit(source_mock,
          [](const p6g::MultiHourFrame& accepted) {
              check(accepted.hour_index==0&&
                    accepted.previous.ziconv_m[0]==0.f,
                    "G18D2 P6F retry read tentative ZICONV");
          });
        station_clocks.publish_only_after_completed_g14(source,stage0);
        check(station_clocks.has_published_hour()&&
              station_clocks.latest_upper_hour()==jan1+hours{1}&&
              station_clocks.latest_gamma_hour()==jan1+hours{1}&&
              source.completed_hours()==1,
              "G18D2 did not publish both accepted upper/CGAMMA clocks");
        must_reject([&]{
            station_clocks.publish_only_after_completed_g14(source,stage0);
        },"G18D2 published source AA/BB/CGAMMA history twice");
        auto stage1=station_clocks.prepare_selected(source,synthetic_deck,true);
        source_mock.inject_oracle=true;
        must_reject([&]{source.advance(source_mock);},
                    "G18D2 source-oracle injection bypassed strict G14 native gate");
        must_reject([&]{
            station_clocks.publish_only_after_completed_g14(source,stage1);
        },"G18D2 staged second UP clock after rejected Fortran-oracle hour");
        check(source.completed_hours()==1&&
              station_clocks.latest_gamma_hour()==jan1+hours{1},
              "G18D2 failed second hour altered committed thermal history");
        source_mock.inject_oracle=false;
        source.advance_with_precommit(source_mock,
          [](const p6g::MultiHourFrame& accepted) {
              check(accepted.hour_index==1&&
                    accepted.previous.ziconv_m[0]==1.f,
                    "G18D2 second source CGAMMA hour did not read committed prior");
          });
        station_clocks.publish_only_after_completed_g14(source,stage1);
        check(source.completed_hours()==2&&
              station_clocks.latest_upper_hour()==jan1+hours{2}&&
              station_clocks.latest_gamma_hour()==jan1+hours{2},
              "G18D2 second accepted AA/BB/CGAMMA rollover lost source time");
        // G18E4: the same PREPDI is now evaluated INSIDE G14's real
        // stage-zero callback, not on an independently driven clock.
        // The rest of this test remains explicitly SYNTHETIC G14 physics.
        // Exercise a REAL 143-hour chronological source-clock run across
        // Dec 2023 / Jan 2024: repeated 12-hour AA/BB swaps and a failed
        // P6F hour cannot publish either upper-air station clock.
        const auto prepdi_begin=sys_days{year{2023}/December/30};
        p6g::UnifiedMultistationHourlyScheduler routed(
            geo(),stations(),surface(prepdi_begin,143),upper(prepdi_begin,143),
            deck_controls);
        p6g::G18D2StationClockAuthority routed_clocks;
        SyntheticNativePhysics routed_mock;
        routed_mock.expect_source_controls=true;
        routed_mock.varied_upper_ziconv=true;
        for(std::size_t h=0;h<143;++h) {
            if(h==12) {
                p6g::G18E4SelectedPrepdiStageAdapter rejected(
                    routed,routed_clocks,synthetic_deck);
                routed_mock.selected_prepdi=&rejected;
                must_reject([&]{
                    routed.advance_with_precommit(
                        routed_mock,[](const p6g::MultiHourFrame&){
                            throw std::runtime_error("synthetic P6F rollback at US turnover");
                        });
                },"G18E4 PREPDI turnover published despite failed P6F output");
                check(rejected.staged()&&!rejected.published()&&
                      routed.completed_hours()==h&&
                      routed.committed_memory().ziconv_m[0]==12.f&&
                      routed_clocks.latest_upper_hour()==prepdi_begin+hours{12}&&
                      routed_clocks.latest_gamma_hour()==prepdi_begin+hours{12},
                      "G18E4 source 2US clock leaked after failed G14 transaction");
                must_reject([&]{rejected.publish_after_completed_g14_hour();},
                            "G18E4 published source clocks after P6F failure");
            }
            p6g::G18E4SelectedPrepdiStageAdapter selected(
                routed,routed_clocks,synthetic_deck);
            routed_mock.selected_prepdi=&selected;
            auto preview=routed.preview_next_hour();
            check(!selected.run(
                      p6::NativeHourStage::PrepdiPreviousZiconv,
                      preview).completed,
                  "G18E4 test-only PREPDI masqueraded as production");
            must_reject([&]{
                selected.run_selected(
                    p6::NativeHourStage::DiagnoWind1,
                    preview,true);
            },"G18E4 allowed PREPDI after original WIND1");
            must_reject([&]{selected.publish_after_completed_g14_hour();},
                        "G18E4 published unexecuted PREPDI");
            routed.advance_with_precommit(
                routed_mock,[&](const p6g::MultiHourFrame& live){
                    const auto& up=selected.selected_upper_for(live);
                    const auto& gamma=selected.selected_gamma_for(live);
                    check(live.hour_index==h&&up.end==live.input.end&&
                          gamma.hour_index==h&&gamma.station_ids==up.station_ids&&
                          up.chronological_older.size()==2&&
                          up.physical_aa_index.size()==2&&
                          up.source_reads.size()==2,
                          "G18E4 PREPDI/CGAMMA missing real G14 stage provenance");
                    const auto previous_samples=
                        p6g::g18b7_source_previous_station_ziconv(live,up);
                    const float base=static_cast<float>(h);
                    check(previous_samples.size()==2&&
                          previous_samples[0]==(h==0?0.f:base+250.f)&&
                          previous_samples[1]==(h==0?0.f:base+0.75f),
                          "G18E4 used current ZICONV or confused two upper-site previous histories");
                    // Source ZUPT=200m: only US1's previously committed
                    // 250m+ ZICONV qualifies for original CGAMMA convective
                    // lapse (-0.0098 K/m); US2 must remain direct sounding.
                    check(gamma.lapse.size()==2&&
                          gamma.lapse[0].branch==(h==0?0:1)&&
                          gamma.lapse[1].branch==0,
                          "G18E4 CGAMMA mixed station-specific previous ZICONV branches");
                    const auto expected_slot=static_cast<std::size_t>((h+1)/12+1);
                    for(std::size_t station=0;station<2;++station) {
                        check(up.chronological_older[station]==expected_slot&&
                              up.justa[station]==(expected_slot%2==0?1:-1)&&
                              up.turnovers[station]==static_cast<int>(expected_slot),
                              "G18E4 multi-US 12h/24h physical AA/BB turnover wrong");
                    }
                    auto clone=live;
                    must_reject([&]{
                        (void)selected.selected_upper_for(clone);
                    },"G18E4 allowed PREPDI source state from copied G14 frame");
                });
            check(selected.staged()&&!selected.published()&&
                  routed.completed_hours()==h+1,
                  "G18E4 G14 hour accepted before source clock publication");
            selected.publish_after_completed_g14_hour();
            check(selected.published()&&
                  routed_clocks.latest_upper_hour()==prepdi_begin+hours{static_cast<int>(h+1)}&&
                  routed_clocks.latest_gamma_hour()==prepdi_begin+hours{static_cast<int>(h+1)},
                  "G18E4 source upper/CGAMMA commits not atomic after G14 hour");
            must_reject([&]{selected.publish_after_completed_g14_hour();},
                        "G18E4 allowed double publish of source PREPDI clocks");
            routed_mock.selected_prepdi=nullptr;
        }
        routed.require_complete();
        auto bad=surface(jan1,6);
        bad.station_ids={58322,58321};
        must_reject([&]{
            p6g::UnifiedMultistationHourlyScheduler impossible(
                geo(),stations(),bad,upper(jan1,6));
        },"reordered SURF station IDs were accepted");
        auto grid=geo();grid.landuse.pop_back();
        must_reject([&]{
            p6g::UnifiedMultistationHourlyScheduler impossible(
                grid,stations(),surface(jan1,6),upper(jan1,6));
        },"incorrect GEO field width was accepted");
        std::cout << "PASS_P6G_G14_UNIFIED_HOURLY_INPUT_AND_CLOCK "
                     "1h_6h_143h_8784h 2SS_2US dynamic_10km "
                     "17_accepted_stages prior_ZICONV DPTT rollback "
                     "oracle_rejected WFACE_required "
                     "G18D1_P6F_PRECOMMIT_ROLLBACK_AND_RETRY_PASS "
                     "G18D2_UPPER_CGAMMA_SAME_G14_COMMIT_PASS "
                     "S4R1C9V_HOUR3_SYNTHETIC_G14_RETRY_PASS "
                     "FULL_MULTI_SITE_PHYSICS=NOT_YET_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr << "FAIL_P6G_G14 "<<e.what()<<"\n";
        return 1;
    }
}
