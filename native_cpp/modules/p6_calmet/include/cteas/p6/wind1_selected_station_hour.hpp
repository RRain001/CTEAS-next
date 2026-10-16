#pragma once
// P6D8A selected WIND1 observation adapter for the fixed Hefei 2022 case.
//
// Consumes the P6C original-selected hourly SURF and PREPDI observations,
// converts observed meteorological wind direction into U/V using the same
// 0.0174533f coefficient as CALMET RDUPN, and invokes the separately proven
// neutral SIMILT kernel. It DOES NOT claim parity for the full original
// WIND1, interpolation of upper/lower stations onto the 3-D grid, or DIAGNO.
// Rejects missing or calm surface wind instead of fabricating a profile.
#include "cteas/p6/read_surface.hpp"
#include "cteas/p6/similt_profile.hpp"
#include "cteas/p6/upper_hourly_wind.hpp"
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace cteas::calmet::p6 {

struct Wind1SelectedStationHour {
    std::chrono::sys_seconds hour_end;
    int surface_station_id{};
    int upper_station_id{};
    float surface_observed_u_mps{};
    float surface_observed_v_mps{};
    std::array<LayerWind,9> surface_neutral_profile{};
    std::array<LayerWind,9> upper_observed_profile{};
    // SIMILT fill bookkeeping: the original's vertical extrapolation stops at
    // the mixing height (calmet.for L30345), so the levels above it carry the
    // missing sentinel and stay out of the objective analysis.
    std::size_t similt_levels_filled{1};
    float mixing_height_m{-1.f};
};

inline Wind1SelectedStationHour wind1_selected_station_hour(
    const SurfaceInterval& surface,
    int surface_station_id,
    const UpperHour& upper,
    int upper_station_id,
    float station_latitude_deg,
    float anemometer_height_m,
    float station_roughness_m) {

    using namespace std::chrono;
    const auto study_start=sys_seconds{sys_days{year{2022}/January/1}};
    if(surface_station_id<=0 || upper_station_id<=0 ||
       surface.end-surface.start!=hours{1} ||
       surface.end!=upper.end ||
       surface.start<study_start ||
       surface.end>study_start+hours{143}) {
        throw std::invalid_argument("WIND1 selected station/time contract mismatch");
    }
    const auto& obs=surface.obs;
    if(!obs.wind_valid ||
       !std::isfinite(obs.wind_speed_mps) ||
       !std::isfinite(obs.wind_direction_deg) ||
       !(obs.wind_speed_mps>=0.f && obs.wind_speed_mps<998.99f) ||
       !(obs.wind_direction_deg>=0.f && obs.wind_direction_deg<=360.f)) {
        throw std::invalid_argument("WIND1 missing or invalid surface wind");
    }
    if(upper.winds.size()!=9) {
        throw std::invalid_argument("WIND1 requires exactly 9 original PREPDI layers");
    }
    for(const auto& w : upper.winds) {
        if(!std::isfinite(w.u_mps)||!std::isfinite(w.v_mps) ||
           std::abs(w.u_mps)>=998.99f||std::abs(w.v_mps)>=998.99f) {
            throw std::invalid_argument("WIND1 invalid PREPDI wind layer");
        }
    }
    const float angle=0.0174533f*obs.wind_direction_deg;
    const float observed_u=-obs.wind_speed_mps*std::sin(angle);
    const float observed_v=-obs.wind_speed_mps*std::cos(angle);
    if(!std::isfinite(observed_u)||!std::isfinite(observed_v))
        throw std::invalid_argument("WIND1 failed wind vector conversion");

    // The selected WIND1 route skips SIMILT for calm winds. Do not
    // silently extrapolate an arbitrary wind direction at zero speed.
    if(std::hypot(observed_u,observed_v)<1.0e-4f)
        throw std::invalid_argument("WIND1 calm source needs separate original branch");

    // WIND1 IEXTRP=-4 calls SIMILT with EL=ZI=ZIMINI=10000 m (L36171), so the
    // first guess is neutral and uncapped.
    const SimiltProfileInput input{
        station_latitude_deg,anemometer_height_m,station_roughness_m,
        observed_u,observed_v,10000.f,10000.f,10000.f,0,{0.f,20.f,40.f,80.f,160.f,320.f,640.f,1200.f,2000.f,3000.f}
    };
    const auto neutral=original_similt_profile(input);
    Wind1SelectedStationHour result;
    result.hour_end=surface.end;
    result.surface_station_id=surface_station_id;
    result.upper_station_id=upper_station_id;
    result.surface_observed_u_mps=observed_u;
    result.surface_observed_v_mps=observed_v;
    for(std::size_t k=0;k<9;k++) {
        result.surface_neutral_profile[k]={
            neutral.u_mps[k],neutral.v_mps[k]
        };
        result.upper_observed_profile[k]=upper.winds[k];
    }
    return result;
}

} // namespace cteas::calmet::p6
