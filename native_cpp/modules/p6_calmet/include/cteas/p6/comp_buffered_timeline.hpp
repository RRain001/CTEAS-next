#pragma once
// P6C buffered hourly observation assembly for the selected 2022 case.
//
// This models physical two-slot AA/BB turnover and checks against the
// independently tested chronological PREPDI bracket. It is a candidate
// implementation, NOT yet evidence of full original COMP state-machine parity:
// source-exact AA/BB buffer reads, MAXSEP, CGAMMA remain independent gates.
#include "cteas/p6/temperature_faces.hpp"
#include "cteas/p6/upper_hourly_wind.hpp"
#include <chrono>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6 {
struct CompBufferedHour {
    UpperHour interpolated;
    std::size_t aa_profile{}, bb_profile{};
    int aa_slot{}, bb_slot{}, jorder{}, turnovers{}, total_reads{};
    std::vector<float> aa_face_temperature_k, bb_face_temperature_k;
};

class CompBufferedTimeline {
public:
    CompBufferedTimeline(const Upper2022& profiles,
                         const std::vector<std::vector<LayerWind>>& layers,
                         const std::vector<std::vector<float>>& face_temperatures,
                         int min_separation_s=3600,
                         int max_separation_s=14*3600)
        : profiles_(profiles), layers_(layers), faces_(face_temperatures),
          min_sep_(min_separation_s), max_sep_(max_separation_s) {
        if(profiles_.soundings.size()<2 ||
           layers_.size()!=profiles_.soundings.size() ||
           faces_.size()!=profiles_.soundings.size() ||
           min_sep_<=0 || max_sep_<min_sep_)
            throw std::invalid_argument("COMP invalid profile arrays or gap policy");
        const auto nk=layers_.front().size();
        const auto nf=faces_.front().size();
        if(nk==0 || nf!=nk+1)
            throw std::invalid_argument("COMP missing model layers/faces");
        for(std::size_t i=0;i<layers_.size();++i) {
            if(layers_[i].size()!=nk || faces_[i].size()!=nf)
                throw std::invalid_argument("COMP profile layer/face mismatch");
            if(i>0 && profiles_.soundings[i].end<=profiles_.soundings[i-1].end)
                throw std::invalid_argument("COMP unordered or duplicate soundings");
        }
        slot_profile_[0]=0;
        slot_profile_[1]=1;
    }

    CompBufferedHour hour(std::chrono::sys_seconds hour_end) {
        if(visited_ && hour_end<=previous_)
            throw std::invalid_argument("COMP hours must advance strictly");
        if(hour_end<profiles_.soundings.front().end)
            throw std::invalid_argument("COMP clock before first sounding");
        // Original COMP's AA/BB two-buffer semantics: retain the previously
        // loaded later sounding and load a new later sounding into the freed
        // slot. JORDER distinguishes which physical slot is chronologically
        // earlier. The original routine must still be independently traced.
        while(hour_end>=profiles_.soundings[slot_profile_[bb_slot_]].end) {
            if(slot_profile_[bb_slot_]+1>=profiles_.soundings.size())
                throw std::invalid_argument("COMP next sounding unavailable");
            aa_slot_=bb_slot_;
            bb_slot_=1-aa_slot_;
            slot_profile_[bb_slot_]=slot_profile_[aa_slot_]+1;
            ++turnovers_;
            ++reads_;
        }
        auto interpolated=calmet_prepdi_hour(
            profiles_,hour_end,layers_,min_sep_,max_sep_);
        const auto aa=slot_profile_[aa_slot_],bb=slot_profile_[bb_slot_];
        if(interpolated.prior_sounding!=aa||interpolated.following_sounding!=bb)
            throw std::logic_error("COMP physical buffer / PREPDI bracket drift");
        CompBufferedHour r;
        r.interpolated=std::move(interpolated);
        r.aa_profile=aa;
        r.bb_profile=bb;
        r.aa_slot=aa_slot_;
        r.bb_slot=bb_slot_;
        r.jorder=aa_slot_==0?1:-1;
        r.turnovers=turnovers_;
        r.total_reads=reads_;
        r.aa_face_temperature_k=faces_[aa];
        r.bb_face_temperature_k=faces_[bb];
        visited_=true;
        previous_=hour_end;
        return r;
    }
private:
    const Upper2022& profiles_;
    const std::vector<std::vector<LayerWind>>& layers_;
    const std::vector<std::vector<float>>& faces_;
    int min_sep_,max_sep_;
    std::size_t slot_profile_[2]{};
    int aa_slot_=0,bb_slot_=1,turnovers_=0,reads_=2;
    bool visited_=false;
    std::chrono::sys_seconds previous_{};
};

inline std::vector<CompBufferedHour> comp_selected_2022_hours(
    const Upper2022& upper,const std::vector<float>& zfaces,
    int nsecdt=3600,int maxsep_hours=14) {
    using namespace std::chrono;
    std::vector<std::vector<LayerWind>> layers;
    std::vector<std::vector<float>> temperatures;
    for(const auto& s:upper.soundings) {
        layers.push_back(calmet_vertav(s,zfaces));
        temperatures.push_back(calmet_facet_temperatures(s,zfaces));
    }
    if(maxsep_hours<1 || maxsep_hours>100 || nsecdt<1 ||
       nsecdt>maxsep_hours*3600)
        throw std::invalid_argument("COMP invalid original NSECDT/MAXSEP control");
    CompBufferedTimeline state(upper,layers,temperatures,nsecdt,maxsep_hours*3600);
    const auto start=sys_seconds{sys_days{year{2022}/January/1}};
    std::vector<CompBufferedHour> hours;
    hours.reserve(143);
    for(int n=1;n<=143;++n)
        hours.push_back(state.hour(start+std::chrono::hours{n}));
    return hours;
}
} // namespace cteas::calmet::p6
