#pragma once
// G18B1: actual, station-independent source UP.DAT/PREPDI AA/BB slot
// identity/turnovers for G18A MIXHT. Reuses PR #53 P6C physical buffer
// semantics and P6E MixdtSounding data contract, no interpolation physics.
// Source NEARU / IUPT and CGAMMA remain independent production gates.
#include "cteas/p6/p6g_unified_hourly.hpp"
#include "cteas/p6e/mixdt.hpp"
#include <array>
#include <chrono>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G18BUpperHour {
    std::chrono::sys_seconds end{};
    std::vector<int> station_ids,justa;
    std::vector<std::size_t> chronological_older,chronological_newer;
    std::vector<int> past_seconds,to_go_seconds,gap_seconds;
    std::array<std::vector<p6e::MixdtSounding>,2> physical_sounding;
    std::vector<std::size_t> physical_aa_index,physical_bb_index;
    std::vector<int> turnovers,source_reads;
};
inline p6e::MixdtSounding g18b_read_observed_thermal(
    const p6::UpperSounding& src) {
    if(src.data.size()<2)
        throw std::invalid_argument("G18B source UP sounding missing thermal levels");
    p6e::MixdtSounding data;
    data.height_m.reserve(src.data.size());
    data.temp_k.reserve(src.data.size());
    for(const auto& lvl:src.data) {
        if(!lvl.height_valid||!std::isfinite(lvl.height_lgl_m)||
           (!data.height_m.empty()&&lvl.height_lgl_m<=data.height_m.back()))
            throw std::invalid_argument("G18B source UP level geometry invalid");
        data.height_m.push_back(lvl.height_lgl_m);
        data.temp_k.push_back(lvl.temperature_valid?lvl.temperature_k:9999.f);
    }
    return data;
}
inline bool g18b_equal_thermal(
    const p6e::MixdtSounding& a,const p6e::MixdtSounding& b) {
    return a.height_m==b.height_m&&a.temp_k==b.temp_k;
}
class G18BUpperBufferClock {
public:
    // A fresh instance belongs to exactly one chronological G14 simulation.
    // It never consumes an independently selected hour or oracle data.
    [[nodiscard]] G18BUpperHour select(const MultiHourFrame& frame) const {
        using namespace std::chrono;
        if(frame.upper.empty()||frame.upper.size()!=frame.stations.upper.size()||
           frame.input.upper.size()!=frame.upper.size()||
           frame.input.end!=frame.surface.end||
           frame.surface.end-frame.surface.start!=hours{1}||
           (visited_&&(frame.input.end!=previous_end_+hours{1}||
                        frame.hour_index!=previous_hour_+1))||
           (!visited_&&frame.hour_index!=0)||
           (visited_&&last_older_.size()!=frame.upper.size()))
            throw std::invalid_argument("G18B model clock or UP station count changed");
        G18BUpperHour result;
        result.end=frame.input.end;
        const auto n=frame.upper.size();
        result.station_ids.reserve(n);result.justa.reserve(n);
        result.chronological_older.reserve(n);
        result.chronological_newer.reserve(n);
        result.past_seconds.reserve(n);result.to_go_seconds.reserve(n);
        result.gap_seconds.reserve(n);
        result.physical_aa_index.reserve(n);result.physical_bb_index.reserve(n);
        result.turnovers.reserve(n);result.source_reads.reserve(n);
        for(auto& physical:result.physical_sounding)physical.reserve(n);
        for(std::size_t i=0;i<n;++i) {
            const auto& st=frame.upper[i];
            const auto& bound=frame.input.upper[i];
            const auto& raw=st.soundings;
            if(st.station_id!=frame.stations.upper[i].id||
               bound.earlier>=raw.size()||bound.later>=raw.size()||
               bound.later!=bound.earlier+1||
               (visited_&&bound.earlier<last_older_[i])||
               bound.earlier>static_cast<std::size_t>(std::numeric_limits<int>::max()-2)||
               raw[bound.earlier].station_id!=st.station_id||
               raw[bound.later].station_id!=st.station_id)
                throw std::invalid_argument("G18B physical AA/BB UP station identity/order invalid");
            const auto& earlier=raw[bound.earlier];
            const auto& later=raw[bound.later];
            const auto actual_gap=duration_cast<seconds>(later.end-earlier.end).count();
            const auto actual_past=duration_cast<seconds>(frame.input.end-earlier.end).count();
            const auto actual_future=duration_cast<seconds>(later.end-frame.input.end).count();
            if(earlier.start!=earlier.end||later.start!=later.end||
               !(earlier.end<later.end)||actual_gap<=0||
               actual_past<0||actual_future<=0||
               actual_past+actual_future!=actual_gap||
               actual_gap!=bound.span_seconds||
               actual_past!=bound.past_seconds||
               actual_future!=bound.future_seconds)
                throw std::invalid_argument("G18B original PREPDI input bracket/UTC mismatch");
            // PR #53 P6C CompBufferedTimeline initially loads slots 0/1
            // and swaps them on EACH chronological upper sounding turnover.
            // Physical AA/BB != chronological older/newer when JUSTA=-1.
            const auto justa=(bound.earlier%2==0)?1:-1;
            const auto aa=justa>0?bound.earlier:bound.later;
            const auto bb=justa>0?bound.later:bound.earlier;
            // Validate BOTH source thermal soundings before publishing any
            // changes to station clocks, so failures are retryable.
            auto phys_aa=g18b_read_observed_thermal(raw[aa]);
            auto phys_bb=g18b_read_observed_thermal(raw[bb]);
            result.station_ids.push_back(st.station_id);
            result.justa.push_back(justa);
            result.chronological_older.push_back(bound.earlier);
            result.chronological_newer.push_back(bound.later);
            result.past_seconds.push_back(bound.past_seconds);
            result.to_go_seconds.push_back(bound.future_seconds);
            result.gap_seconds.push_back(bound.span_seconds);
            result.physical_aa_index.push_back(aa);
            result.physical_bb_index.push_back(bb);
            result.physical_sounding[0].push_back(std::move(phys_aa));
            result.physical_sounding[1].push_back(std::move(phys_bb));
            result.turnovers.push_back(static_cast<int>(bound.earlier));
            result.source_reads.push_back(static_cast<int>(bound.later)+1);
        }
        // PREPDI/DIAGI may succeed and later COMP/P6F may fail.
        // Do not advance source AA/BB clocks until G14 has committed ALL
        // 17 original stages and completed an entire native hour.
        return result;
    }
    // The production caller must invoke commit only AFTER the corresponding
    // UnifiedMultistationHourlyScheduler::advance() has returned successfully.
    // An explicitly supplied accepted scheduler counter prevents accidental
    // commit from partial selected fixture adapters.
    void commit_after_completed_g14_hour(
        const MultiHourFrame& frame,const G18BUpperHour& prepared,
        std::size_t completed_g14_hours) {
        if(completed_g14_hours!=frame.hour_index+1)
            throw std::invalid_argument("G18B refuses premature or stale hour cache commit");
        const auto source=select(frame);
        if(prepared.end!=source.end||
           prepared.station_ids!=source.station_ids||
           prepared.justa!=source.justa||
           prepared.physical_aa_index!=source.physical_aa_index||
           prepared.physical_bb_index!=source.physical_bb_index||
           prepared.chronological_older!=source.chronological_older||
           prepared.chronological_newer!=source.chronological_newer||
           prepared.past_seconds!=source.past_seconds||
           prepared.to_go_seconds!=source.to_go_seconds||
           prepared.gap_seconds!=source.gap_seconds||
           prepared.turnovers!=source.turnovers||
           prepared.source_reads!=source.source_reads)
            throw std::invalid_argument("G18B stale or fabricated source buffer commit");
        for(std::size_t i=0;i<source.station_ids.size();++i)
            if(!g18b_equal_thermal(
                   prepared.physical_sounding[0].at(i),
                   source.physical_sounding[0].at(i))||
               !g18b_equal_thermal(
                   prepared.physical_sounding[1].at(i),
                   source.physical_sounding[1].at(i)))
                throw std::invalid_argument("G18B mutated UP thermal source before cache commit");
        last_older_=source.chronological_older;
        previous_end_=frame.input.end;
        previous_hour_=frame.hour_index;
        visited_=true;
    }
    [[nodiscard]] bool has_hour() const noexcept {return visited_;}
    [[nodiscard]] std::chrono::sys_seconds last_hour() const noexcept {
        return previous_end_;
    }
private:
    bool visited_=false;
    std::chrono::sys_seconds previous_end_{};
    std::size_t previous_hour_=0;
    std::vector<std::size_t> last_older_;
};
inline void g18b_bind_physical_upper(
    p6e::MixhtObservedMcInput& mixed,const MultiHourFrame& frame,
    const G18BUpperHour& source) {
    const auto n=frame.stations.upper.size();
    if(source.end!=frame.input.end||source.justa.size()!=n||
       source.station_ids.size()!=n||
       source.physical_sounding[0].size()!=n||
       source.physical_sounding[1].size()!=n||
       source.chronological_older.size()!=n||
       source.chronological_newer.size()!=n||
       source.physical_aa_index.size()!=n||
       source.physical_bb_index.size()!=n)
        throw std::invalid_argument("G18B upper buffer binding wrong hour/extent");
    for(std::size_t i=0;i<n;++i) {
        const auto& bracket=frame.input.upper[i];
        if(source.station_ids[i]!=frame.stations.upper[i].id||
           source.justa[i]!=(bracket.earlier%2==0?1:-1)||
           source.chronological_older[i]!=bracket.earlier||
           source.chronological_newer[i]!=bracket.later||
           source.physical_aa_index[i]!=(source.justa[i]>0?bracket.earlier:bracket.later)||
           source.physical_bb_index[i]!=(source.justa[i]>0?bracket.later:bracket.earlier)||
           !g18b_equal_thermal(source.physical_sounding[0][i],
               g18b_read_observed_thermal(
                   frame.upper[i].soundings[source.physical_aa_index[i]]))||
           !g18b_equal_thermal(source.physical_sounding[1][i],
               g18b_read_observed_thermal(
                   frame.upper[i].soundings[source.physical_bb_index[i]])))
            throw std::invalid_argument("G18B source AA/BB identity/thermal overwritten");
    }
    mixed.justa=source.justa;
    mixed.sounding=source.physical_sounding;
    // Deliberately does NOT invent NEARU/IUPT or previous-COMP values.
}
} // namespace cteas::calmet::p6g
