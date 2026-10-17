#pragma once
// G18B4 selected multi-UP CGAMMA temporal handoff. Use only the
// frozen PR #53 CGammaState physics, one copied state per upper site.
// Prior-hour ZICONV at each US and source ZUPT remain TEST-ONLY until
// independently verified original CALMET multi-site source provenance.
// Never publish a lapse or convective history before full G14 commit.
#include "cteas/p6/p6g_g18b_upper_buffer_clock.hpp"
#include "cteas/p6/cgamma.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G18B4CGammaPrepared {
    std::chrono::sys_seconds end{};
    std::size_t hour_index=0;
    std::vector<int> station_ids;
    std::vector<p6::CGammaResult> lapse;
    std::vector<p6::CGammaState> candidate;
};
class G18B4CGammaClock {
public:
    [[nodiscard]] G18B4CGammaPrepared prepare(
        const MultiHourFrame& frame,const G18BUpperHour& upper,
        const std::vector<float>& source_previous_station_ziconv,
        float source_zupt_m,bool explicitly_test_only) const {
        if(!explicitly_test_only||!std::isfinite(source_zupt_m)||
           source_zupt_m<=0.f||upper.end!=frame.input.end||
           upper.justa.size()!=frame.stations.upper.size()||
           source_previous_station_ziconv.size()!=frame.stations.upper.size()||
           (committed_&&frame.hour_index!=last_index_+1)||
           (!committed_&&frame.hour_index!=0)||
           (committed_&&frame.input.end!=last_end_+std::chrono::hours{1})||
           (committed_&&states_.size()!=frame.stations.upper.size())||
           (committed_&&upper.station_ids!=station_ids_))
            throw std::invalid_argument("G18B4 CGAMMA previous-hour provenance invalid");
        // Existing G18B1 source read contract independently validates the
        // physical AA/BB payload and its slot-to-chronological translation.
        p6e::MixhtObservedMcInput guard;
        g18b_bind_physical_upper(guard,frame,upper);
        G18B4CGammaPrepared result;
        result.end=frame.input.end;
        result.hour_index=frame.hour_index;
        result.station_ids=upper.station_ids;
        result.candidate=states_;
        if(result.candidate.empty())
            result.candidate.resize(frame.stations.upper.size());
        for(std::size_t i=0;i<frame.stations.upper.size();++i) {
            const auto z=source_previous_station_ziconv[i];
            if(!std::isfinite(z)||z<0.f)
                throw std::invalid_argument("G18B4 missing independently sourced prior ZICONV");
            p6::Upper2022 one;
            one.station_id=frame.upper[i].station_id;
            one.pstop_hpa=frame.upper[i].pstop_hpa;
            // CGammaState needs only the chronological AA/BB pair and
            // timestamp; copying a whole multi-year UP series every hour
            // would be quadratic work with no change in original physics.
            one.soundings={
                frame.upper[i].soundings.at(upper.chronological_older[i]),
                frame.upper[i].soundings.at(upper.chronological_newer[i])};
            p6::CompBufferedHour h;
            h.aa_profile=0;
            h.bb_profile=1;
            h.jorder=upper.justa[i];
            h.interpolated.end=frame.input.end;
            h.interpolated.prior_sounding=h.aa_profile;
            h.interpolated.following_sounding=h.bb_profile;
            h.interpolated.past_seconds=upper.past_seconds[i];
            h.interpolated.to_go_seconds=upper.to_go_seconds[i];
            h.interpolated.gap_seconds=upper.gap_seconds[i];
            result.lapse.push_back(
                result.candidate[i].calculate(one,h,source_zupt_m,z));
        }
        // Invalid second station invalidates the entire candidate set:
        // committed CGAMMAState never changes until all stages succeed.
        return result;
    }

    void commit_after_completed_g14_hour(
        const G18B4CGammaPrepared& prepared,
        std::size_t actual_completed_hours) {
        if(actual_completed_hours!=prepared.hour_index+1||
           prepared.station_ids.empty()||
           prepared.station_ids.size()!=prepared.candidate.size()||
           prepared.lapse.size()!=prepared.candidate.size()||
           (committed_&&prepared.hour_index!=last_index_+1)||
           (!committed_&&prepared.hour_index!=0)||
           (committed_&&prepared.end!=last_end_+std::chrono::hours{1}))
            throw std::invalid_argument("G18B4 attempted premature/stale CGAMMA commit");
        for(const auto& v:prepared.lapse)
            if(!std::isfinite(v.kelvin_per_m)||v.branch<0||v.branch>2)
                throw std::invalid_argument("G18B4 CGAMMA invalid native lapse");
        states_=prepared.candidate;
        station_ids_=prepared.station_ids;
        last_end_=prepared.end;
        last_index_=prepared.hour_index;
        committed_=true;
    }
    [[nodiscard]] bool has_committed_hour() const noexcept {return committed_;}
    [[nodiscard]] std::chrono::sys_seconds committed_end() const noexcept {
        return last_end_;
    }
private:
    bool committed_=false;
    std::size_t last_index_=0;
    std::chrono::sys_seconds last_end_{};
    std::vector<int> station_ids_;
    std::vector<p6::CGammaState> states_;
};
} // namespace cteas::calmet::p6g
