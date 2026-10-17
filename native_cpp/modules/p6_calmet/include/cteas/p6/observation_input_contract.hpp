#pragma once
// P6G G7c: input-only intersection of SSn/USn, SURF.DAT, UP.DAT,
// model clock. Constructs upper sounding bracket indices without performing
// WIND1/COMP interpolation. No frozen real-case P6D computation changes.
#include "cteas/p6/read_surface_dynamic.hpp"
#include "cteas/p6/read_upper_dynamic.hpp"
#include "cteas/p6/calmet_station_set.hpp"
#include <algorithm>
#include <chrono>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct UpperBracket {
    std::size_t earlier{},later{};
    int span_seconds{},past_seconds{},future_seconds{};
};
struct InputHour {
    std::chrono::sys_seconds end;
    std::vector<UpperBracket> upper;
};
inline std::vector<InputHour> bind_original_calmet_station_inputs(
    const StationSet& deck,
    const SurfaceSeries& surf,
    const std::vector<UpperSeries>& upper,
    int min_upper_gap_seconds=3600,
    int max_upper_gap_seconds=14*3600,
    std::size_t max_upper_hour_slots=2000000) {
    using namespace std::chrono;
    if(deck.surface.empty()||deck.upper.empty()||
       surf.station_ids.size()!=deck.surface.size()||
       upper.size()!=deck.upper.size()||
       min_upper_gap_seconds<=0||
       max_upper_gap_seconds<min_upper_gap_seconds||
       max_upper_hour_slots==0)
        throw std::invalid_argument("P6G station-count, time window or capacity invalid");
    for(std::size_t i=0;i<deck.surface.size();++i)
        if(surf.station_ids[i]!=deck.surface[i].id)
            throw std::invalid_argument("P6G SURF.DAT station ordering differs from met.inp SSn");
    for(std::size_t i=0;i<deck.upper.size();++i)
        if(upper[i].station_id!=deck.upper[i].id)
            throw std::invalid_argument("P6G UP.DAT station ordering differs from met.inp USn");
    if(surf.hourly.empty()||
       upper.size()>max_upper_hour_slots/surf.hourly.size())
        throw std::invalid_argument("P6G hourly station-slot budget exceeded");
    auto expected=surf.begin;
    std::vector<InputHour> result;
    result.reserve(surf.hourly.size());
    for(const auto& sh:surf.hourly) {
        if(sh.start!=expected||sh.end-sh.start!=hours{1}||
           sh.by_station.size()!=deck.surface.size())
            throw std::invalid_argument("P6G SURF hour continuity or station width invalid");
        InputHour slot;
        slot.end=sh.end;
        slot.upper.reserve(upper.size());
        for(const auto& series:upper) {
            const auto& records=series.soundings;
            if(records.size()<2)
                throw std::invalid_argument("P6G upper station needs two bracketing soundings");
            const auto ahead=std::upper_bound(
                records.begin(),records.end(),slot.end,
                [](const auto& t,const frozen_upper::UpperSounding& s){
                    return t<s.end;
                });
            if(ahead==records.begin()||ahead==records.end())
                throw std::invalid_argument("P6G model hour lacks bracketing upper sounding");
            const auto later=static_cast<std::size_t>(ahead-records.begin());
            const auto earlier=later-1;
            const auto span=duration_cast<seconds>(
                records[later].end-records[earlier].end).count();
            const auto past=duration_cast<seconds>(
                slot.end-records[earlier].end).count();
            const auto future=duration_cast<seconds>(
                records[later].end-slot.end).count();
            if(span<min_upper_gap_seconds||span>max_upper_gap_seconds||
               past<0||future<0||past+future!=span)
                throw std::invalid_argument(
                    "P6G upper sounding separation exceeds original PREPDI scoped rule");
            slot.upper.push_back({earlier,later,static_cast<int>(span),
                                  static_cast<int>(past),static_cast<int>(future)});
        }
        result.push_back(std::move(slot));
        expected=sh.end;
    }
    if(expected!=surf.end)
        throw std::invalid_argument("P6G SURF final timestamp inconsistent with header");
    return result;
}
} // namespace cteas::calmet::p6g
