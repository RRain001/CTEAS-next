#pragma once
// G18B7 selected CGAMMA input: original CALMET uses the PREVIOUS
// committed ZICONV(IIUP(iu),JJUP(iu)) for each US. IIUP/JJUP are the
// separately accepted PR #53 upper_reference_cell Fortran-truncated and
// clamped station-to-grid reference indices, NOT nearest-grid NEARU.
// Does not replace the existing #53 CGammaState numerical kernel.
// Full G14 source time/state authority and gamma grid weighting remain gated.
#include "cteas/p6/p6g_g18b4_cgamma_clock.hpp"
#include "cteas/p6/station_geometry.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
inline std::vector<float> g18b7_source_previous_station_ziconv(
    const MultiHourFrame& frame,const G18BUpperHour& sounding) {
    const auto& g=frame.grid;
    const auto nu=frame.stations.upper.size();
    if(g.nx<2||g.ny<2||g.nx>400||g.ny>400||
       !std::isfinite(g.grid_km)||g.grid_km<=0.f||
       sounding.end!=frame.input.end||
       sounding.station_ids.size()!=nu||
       frame.upper.size()!=nu||
       frame.previous.ziconv_m.size()!=
         static_cast<std::size_t>(g.nx)*static_cast<std::size_t>(g.ny))
        throw std::invalid_argument("G18B7 source clock/grid ZICONV authority missing");
    std::vector<float> samples;
    samples.reserve(nu);
    for(std::size_t iu=0;iu<nu;++iu) {
        const auto& station=frame.stations.upper[iu];
        if(sounding.station_ids[iu]!=station.id||
           frame.upper[iu].station_id!=station.id)
            throw std::invalid_argument("G18B7 wrong source upper station order");
        const auto pos=p6::upper_reference_cell(
            {station.local_x_m,station.local_y_m},
            g.nx,g.ny,g.grid_km*1000.f);
        const auto index=static_cast<std::size_t>(pos.j-1)*
                         static_cast<std::size_t>(g.nx)+
                         static_cast<std::size_t>(pos.i-1);
        const auto z=frame.previous.ziconv_m.at(index);
        if(!std::isfinite(z)||z<0.f)
            throw std::invalid_argument("G18B7 previous committed source ZICONV invalid");
        samples.push_back(z);
    }
    return samples;
}
inline G18B4CGammaPrepared g18b7_prepare_source_grid_cgamma(
    const G18B4CGammaClock& clock,const MultiHourFrame& frame,
    const G18BUpperHour& sounding,float original_zupt_m,
    bool explicitly_test_only) {
    // Clock remains candidate-only until complete G14 hourly commit.
    return clock.prepare(frame,sounding,
        g18b7_source_previous_station_ziconv(frame,sounding),
        original_zupt_m,explicitly_test_only);
}
} // namespace cteas::calmet::p6g
