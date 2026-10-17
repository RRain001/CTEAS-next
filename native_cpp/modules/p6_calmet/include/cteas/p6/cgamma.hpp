#pragma once
// CALMET 6.5.0 original CGAMMA L3101-3250, selected NOOBS=0 instantaneous
// 2022 soundings. ZICONV is supplied as independently traced original
// boundary-layer forcing; never invented by the observation integration.
#include "cteas/p6/comp_buffered_timeline.hpp"
#include "cteas/p6/temperature_faces.hpp"
#include <chrono>
#include <cmath>
#include <stdexcept>
namespace cteas::calmet::p6 {
struct CGammaResult {
    float kelvin_per_m=0.0f;
    int branch=0; // 0 direct sounding; 1 current convective; 2 retained convective
};
class CGammaState {
public:
    CGammaResult calculate(const Upper2022& upper,const CompBufferedHour& h,
                            float zupt_m,float ziconv_m) {
        if(!std::isfinite(zupt_m)||!std::isfinite(ziconv_m)||zupt_m<=0 ||
           h.aa_profile>=upper.soundings.size()||
           h.bb_profile>=upper.soundings.size()||h.interpolated.gap_seconds<=0)
            throw std::invalid_argument("CGAMMA invalid physical inputs");
        const auto t=h.interpolated.end;
        if(visited_&&t<=last_calculated_)
            throw std::invalid_argument("CGAMMA time must increase");
        visited_=true;last_calculated_=t;
        if(ziconv_m>=zupt_m) {
            last_convective_=t;
            has_convective_=true;
            return {-0.0098f,1};
        }
        const auto physical_aa=h.jorder>=0?h.aa_profile:h.bb_profile;
        const auto physical_bb=h.jorder>=0?h.bb_profile:h.aa_profile;
        const auto& a=upper.soundings.at(physical_aa);
        const auto& b=upper.soundings.at(physical_bb);
        if(a.data.empty()||b.data.empty()||
           !a.data.front().temperature_valid||!b.data.front().temperature_valid ||
           a.data.front().temperature_k>=999.89f ||
           b.data.front().temperature_k>=999.89f)
            throw std::invalid_argument("CGAMMA missing base temperature");
        const float tsaa=a.data.front().temperature_k;
        const float tsbb=b.data.front().temperature_k;
        const float ttaa=calmet_intp_temperature(a,zupt_m);
        const float ttbb=calmet_intp_temperature(b,zupt_m);
        const int jtogo=h.interpolated.to_go_seconds;
        const int jdelta=h.interpolated.gap_seconds;
        const float factor=static_cast<float>(jtogo)/static_cast<float>(jdelta);
        const bool neg=h.jorder<0;
        const float ts=neg?tsaa-(tsaa-tsbb)*factor:
                           tsbb-(tsbb-tsaa)*factor;
        float tt=neg?ttaa-(ttaa-ttbb)*factor:
                     ttbb-(ttbb-ttaa)*factor;
        int branch=0;
        if(has_convective_) {
            const auto lower=upper.soundings.at(h.aa_profile).end;
            const auto higher=upper.soundings.at(h.bb_profile).end;
            const auto jtogo_c=std::chrono::duration_cast<std::chrono::seconds>(
                higher-last_convective_).count();
            const auto jpast_c=std::chrono::duration_cast<std::chrono::seconds>(
                last_convective_-lower).count();
            if(jpast_c+jtogo_c==jdelta && jtogo_c>jtogo &&
               jtogo_c<jdelta && jtogo_c>0) {
                const auto fc=static_cast<float>(jtogo_c)/
                              static_cast<float>(jdelta);
                const float tsc=(neg?tsaa-(tsaa-tsbb)*fc:
                                     tsbb-(tsbb-tsaa)*fc) -0.0098f*zupt_m;
                const float adjust=static_cast<float>(jtogo)/
                                   static_cast<float>(jtogo_c);
                tt=neg?ttaa-(ttaa-tsc)*adjust:
                       ttbb-(ttbb-tsc)*adjust;
                branch=2;
            }
        }
        return {(tt-ts)/zupt_m,branch};
    }
private:
    bool visited_=false,has_convective_=false;
    std::chrono::sys_seconds last_convective_{},last_calculated_{};
};
} // namespace cteas::calmet::p6
