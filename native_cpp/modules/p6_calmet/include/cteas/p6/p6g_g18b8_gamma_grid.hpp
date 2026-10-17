#pragma once
// G18B8: Original CALMET DIAGNO GAMMA grid from candidate G18B4 per-UP
// CGAMMA. Vendor calmet.for: IUPT>0 uniform GAMUP(IUPT), else
// CMPD2 station distances + 1/R**2, lower bound 0.01 m^2.
// Source-authoritative REAL*4 expressions, loop order, and station ordinals
// are checked by a separate extracted-vendor-Fortran numerical oracle.
// Still selected-stage ONLY: no complete G14/P6F or 45-field acceptance.
#include "cteas/p6/p6g_g18b3_upper_choice.hpp"
#include "cteas/p6/p6g_g18b4_cgamma_clock.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G18B8GammaGrid {
    std::chrono::sys_seconds end{};
    int original_iupt=-1;
    std::vector<int> upper_station_ids;
    std::vector<float> gamma_k_per_m; // source J-major, I-minor grid
};
inline G18B8GammaGrid g18b8_source_gamma_grid(
    const GeoGrid& grid,const StationSet& stations,
    const G18B3UpperChoice& choice,const G18B4CGammaPrepared& cgamma,
    bool explicitly_test_only) {
    const auto nu=stations.upper.size();
    if(!explicitly_test_only||grid.nx<2||grid.ny<2||
       grid.nx>400||grid.ny>400||
       !std::isfinite(grid.grid_km)||grid.grid_km<=0.f||
       nu<1||nu>1000||choice.nearu.size()!=
        static_cast<std::size_t>(grid.nx)*static_cast<std::size_t>(grid.ny)||
       cgamma.station_ids.size()!=nu||cgamma.lapse.size()!=nu||
       (choice.iupt!=-1&&(choice.iupt<=0||
          static_cast<std::size_t>(choice.iupt)>nu)))
        throw std::invalid_argument("G18B8 incomplete original IUPT/CGAMMA grid source");
    G18B8GammaGrid out;
    out.end=cgamma.end;
    out.original_iupt=choice.iupt;
    out.upper_station_ids=cgamma.station_ids;
    const auto n=static_cast<std::size_t>(grid.nx)*
                 static_cast<std::size_t>(grid.ny);
    out.gamma_k_per_m.assign(n,0.f);
    for(std::size_t k=0;k<nu;++k) {
        if(stations.upper[k].id<=0||
           cgamma.station_ids[k]!=stations.upper[k].id||
           !std::isfinite(stations.upper[k].local_x_m)||
           !std::isfinite(stations.upper[k].local_y_m)||
           !std::isfinite(cgamma.lapse[k].kelvin_per_m))
            throw std::invalid_argument("G18B8 CGAMMA station identity/REAL4 invalid");
    }
    for(const int k:choice.nearu)
        if(k<=0||static_cast<std::size_t>(k)>nu)
            throw std::invalid_argument("G18B8 source NEARU ordinal outside US count");
    // Original DIAGNO positive IUPT branch does not apply CMPD2.
    if(choice.iupt>0) {
        std::fill(out.gamma_k_per_m.begin(),out.gamma_k_per_m.end(),
                  cgamma.lapse[static_cast<std::size_t>(choice.iupt-1)].kelvin_per_m);
        return out;
    }
    const float dgrid=grid.grid_km*1000.f;
    // Literal source computational order: outer I, inner J, then inner K.
    for(int i=1;i<=grid.nx;++i) {
        const float xgm=(static_cast<float>(i)-0.5f)*dgrid;
        for(int j=1;j<=grid.ny;++j) {
            const float ygm=(static_cast<float>(j)-0.5f)*dgrid;
            float top=0.f,bot=0.f;
            for(std::size_t k=0;k<nu;++k) {
                const auto& us=stations.upper[k];
                const float dx=us.local_x_m-xgm;
                const float dy=us.local_y_m-ygm;
                const float dist2=dx*dx+dy*dy;
                if(!std::isfinite(dist2))
                    throw std::invalid_argument("G18B8 source CMPD2 nonfinite distance");
                const float dis2saf=std::max(dist2,0.01f);
                top=top+cgamma.lapse[k].kelvin_per_m/dis2saf;
                bot=bot+1.0f/dis2saf;
            }
            if(!std::isfinite(bot)||bot<=0.f||!std::isfinite(top))
                throw std::invalid_argument("G18B8 source CMPD2 weight overflow");
            const float gamma=top/bot;
            if(!std::isfinite(gamma))
                throw std::invalid_argument("G18B8 source GAMMA nonfinite field");
            out.gamma_k_per_m[static_cast<std::size_t>(j-1)*
                             static_cast<std::size_t>(grid.nx)+
                             static_cast<std::size_t>(i-1)]=gamma;
        }
    }
    return out;
}
inline G18B8GammaGrid g18b8_source_gamma_from_hour(
    const MultiHourFrame& frame,const G18B3UpperChoice& choice,
    const G18B4CGammaPrepared& cgamma,bool explicitly_test_only) {
    if(frame.input.end!=cgamma.end||
       frame.hour_index!=cgamma.hour_index)
        throw std::invalid_argument("G18B8 stale or forged source model hour");
    return g18b8_source_gamma_grid(
        frame.grid,frame.stations,choice,cgamma,explicitly_test_only);
}
} // namespace cteas::calmet::p6g
