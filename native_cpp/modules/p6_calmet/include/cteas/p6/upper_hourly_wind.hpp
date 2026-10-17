#pragma once
// Source-backed CALMET PREPDI selected NOOBS=0, v2.1 instantaneous upper air:
// COMP checks that aa/bb soundings straddle *hour-end* model clock
// (calmet.for L4123-4268); PREPDI interpolates already-VERTAV-averaged U/V
// using jpast/jtogo and XFACT (L13914-13985). Does not implement complete
// COMP state machine, multi-station, meteorology or cloud/precipitation.
#include "cteas/p6/read_upper.hpp"
#include "cteas/p6/vertical_wind_average.hpp"
#include <algorithm>
#include <chrono>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6 {
struct UpperHour {
    std::chrono::sys_seconds end;
    std::size_t prior_sounding{},following_sounding{};
    int past_seconds{},to_go_seconds{},gap_seconds{};
    std::vector<LayerWind> winds;
};
inline UpperHour calmet_prepdi_hour(
    const Upper2022& profiles,std::chrono::sys_seconds clock,
    const std::vector<std::vector<LayerWind>>& layer_averages,
    int min_sounding_separation_seconds=3600,
    int max_sounding_separation_seconds=14*3600){
    const auto& ss=profiles.soundings;
    if(ss.size()<2||layer_averages.size()!=ss.size())
        throw std::invalid_argument("PREPDI needs >=2 complete soundings");
    if(min_sounding_separation_seconds<=0 ||
       max_sounding_separation_seconds<min_sounding_separation_seconds)
        throw std::invalid_argument("PREPDI invalid time-window policy");
    const auto next=std::upper_bound(ss.begin(),ss.end(),clock,
        [](const auto& t,const UpperSounding& s){return t<s.end;});
    if(next==ss.begin()||next==ss.end())
        throw std::invalid_argument("PREPDI model hour is not bracketed by soundings");
    const auto higher=static_cast<std::size_t>(next-ss.begin());
    const auto lower=higher-1;
    const auto span=std::chrono::duration_cast<std::chrono::seconds>(
        ss[higher].end-ss[lower].end).count();
    const auto past=std::chrono::duration_cast<std::chrono::seconds>(
        clock-ss[lower].end).count();
    const auto togo=std::chrono::duration_cast<std::chrono::seconds>(
        ss[higher].end-clock).count();
    if(span<min_sounding_separation_seconds || span>max_sounding_separation_seconds||
       past<0 || togo<0 || past+togo!=span)
        throw std::invalid_argument("PREPDI sounding frequency/gap rejected");
    const auto& aa=layer_averages[lower];
    const auto& bb=layer_averages[higher];
    if(aa.empty()||aa.size()!=bb.size())
        throw std::invalid_argument("PREPDI unequal layer counts");
    const int jdelta=static_cast<int>(span),jtogo=static_cast<int>(togo);
    const float xfact=static_cast<float>(jtogo)/static_cast<float>(jdelta);
    UpperHour out;
    out.end=clock;
    out.prior_sounding=lower;
    out.following_sounding=higher;
    out.past_seconds=static_cast<int>(past);
    out.to_go_seconds=jtogo;
    out.gap_seconds=jdelta;
    out.winds.resize(aa.size());
    for(std::size_t i=0;i<aa.size();++i){
        // PREPDI jorder=+1 branch (bb newer); order may alternate in
        // original COMP's AA/BB buffers without altering chrono ordering.
        out.winds[i].u_mps=bb[i].u_mps-(bb[i].u_mps-aa[i].u_mps)*xfact;
        out.winds[i].v_mps=bb[i].v_mps-(bb[i].v_mps-aa[i].v_mps)*xfact;
    }
    return out;
}
inline std::vector<UpperHour> calmet_prepdi_2022_hours(
    const Upper2022& upper,const std::vector<float>& zface){
    using namespace std::chrono;
    std::vector<std::vector<LayerWind>> layers;
    layers.reserve(upper.soundings.size());
    for(const auto& s:upper.soundings)
        layers.push_back(calmet_vertav(s,zface));
    const auto start=sys_days{year{2022}/January/1};
    std::vector<UpperHour> hours;
    hours.reserve(143);
    for(int n=1;n<=143;++n)
        hours.push_back(calmet_prepdi_hour(
            upper,sys_seconds{start}+std::chrono::hours{n},layers));
    return hours;
}
} // namespace cteas::calmet::p6
