#pragma once
// P6E integration-only consumer of the *existing* P6C selected
// COMP AA/BB and RDSN original hourly state; no P6C/P6D changes.
// The P6C CompBufferedHour aa_profile/bb_profile fields are
// CHRONOLOGICAL, not always physical AA/BB. When JUSTA=-1, physical
// AA holds the newer observation and physical BB the older one.
// Preserve this distinction when invoking CALMET P6E MIXHT/TEMP3D.
#include "cteas/p6/comp_buffered_timeline.hpp"
#include "cteas/p6/surface_hourly_state.hpp"
#include "cteas/p6e/mixht_observed_mc.hpp"
#include <array>
#include <chrono>
#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::p6e {
struct P6CObservedHour {
    std::chrono::sys_seconds end{};
    std::size_t chronological_older=0,chronological_newer=0;
    std::size_t physical_aa_profile=0,physical_bb_profile=0;
    int justa=0,aa_slot=-1,bb_slot=-1;
    int past_seconds=0,to_go_seconds=0,gap_seconds=0;
    std::size_t surface_row=0;
    float surface_temp_k=0.f;
    float surface_pressure_mb=9999.f;
    int surface_humidity_pct=9999,opaque_cloud_tenths=9999;
    // Original station ceiling in hundreds of feet (PGTSTB night branch).
    int ceiling_hundreds_ft=9999;
    int precipitation_code=9999;
    bool precipitation_code_observed=false;
    MixdtSounding physical_aa,physical_bb;
    std::vector<float> physical_aa_face_t_k,physical_bb_face_t_k;
};
inline MixdtSounding p6c_as_mixdt(const cteas::calmet::p6::UpperSounding& s) {
    if(s.data.size()<2)throw std::invalid_argument("P6C bridge sounding too short");
    MixdtSounding out;
    for(const auto& layer:s.data) {
        if(!layer.height_valid)
            throw std::invalid_argument("P6C bridge invalid sounding height");
        out.height_m.push_back(layer.height_lgl_m);
        out.temp_k.push_back(layer.temperature_valid?layer.temperature_k:9999.f);
    }
    return out;
}
inline P6CObservedHour p6c_observed_hour(
    const cteas::calmet::p6::Upper2022& upper,
    const cteas::calmet::p6::CompBufferedHour& h,
    const cteas::calmet::p6::RdsnHourlyState& s) {
    if(!s.record||upper.soundings.empty() ||
       h.aa_profile>=upper.soundings.size()||
       h.bb_profile>=upper.soundings.size()||
       h.aa_profile>=h.bb_profile||
       h.interpolated.prior_sounding!=h.aa_profile||
       h.interpolated.following_sounding!=h.bb_profile||
       (h.jorder!=1&&h.jorder!=-1)||
       h.aa_slot!=(h.jorder>0?0:1)||
       h.bb_slot!=(h.jorder>0?1:0)||
       h.interpolated.end!=s.record->end||
       h.interpolated.end<=s.record->start||
       h.interpolated.past_seconds<0||
       h.interpolated.to_go_seconds<0||
       h.interpolated.gap_seconds<=0||
       h.interpolated.past_seconds+h.interpolated.to_go_seconds!=
           h.interpolated.gap_seconds||
       !s.record->obs.temperature_valid)
        throw std::invalid_argument("P6C to P6E inconsistent hourly state");
    const auto na=h.aa_face_temperature_k.size();
    if(na<2||na!=h.bb_face_temperature_k.size())
        throw std::invalid_argument("P6C to P6E malformed temperature faces");
    P6CObservedHour x;
    x.end=h.interpolated.end;
    x.chronological_older=h.aa_profile;
    x.chronological_newer=h.bb_profile;
    x.justa=h.jorder;
    x.aa_slot=h.aa_slot;
    x.bb_slot=h.bb_slot;
    x.past_seconds=h.interpolated.past_seconds;
    x.to_go_seconds=h.interpolated.to_go_seconds;
    x.gap_seconds=h.interpolated.gap_seconds;
    x.surface_row=s.source_row;
    x.surface_temp_k=s.record->obs.temperature_k;
    x.surface_humidity_pct=s.record->obs.humidity_valid?
        s.record->obs.humidity_pct:9999;
    x.opaque_cloud_tenths=s.record->obs.cloud_valid?
        s.record->obs.opaque_cloud_tenths:9999;
    // Surface pressure feeds the original airden(): RHO = 0.3484321*PRES/TEMP2D.
    x.surface_pressure_mb=s.record->obs.pressure_valid?
        s.record->obs.pressure_mb:9999.f;
    x.ceiling_hundreds_ft=s.record->obs.ceiling_valid?
        s.record->obs.ceiling_hundreds_ft:9999;
    x.precipitation_code_observed=s.record->obs.precipitation_code_valid;
    // Missing 9999 MUST NOT be interpreted as observed dry (0).
    x.precipitation_code=x.precipitation_code_observed?
        s.record->obs.precip_code:9999;
    x.physical_aa_profile=h.jorder>0?h.aa_profile:h.bb_profile;
    x.physical_bb_profile=h.jorder>0?h.bb_profile:h.aa_profile;
    x.physical_aa=p6c_as_mixdt(upper.soundings[x.physical_aa_profile]);
    x.physical_bb=p6c_as_mixdt(upper.soundings[x.physical_bb_profile]);
    x.physical_aa_face_t_k=h.jorder>0?
        h.aa_face_temperature_k:h.bb_face_temperature_k;
    x.physical_bb_face_t_k=h.jorder>0?
        h.bb_face_temperature_k:h.aa_face_temperature_k;
    return x;
}
inline void apply_p6c_hour_to_mixht_one_station(
    MixhtObservedMcInput& phys,const P6CObservedHour& h) {
    if(phys.nx==0||phys.ny==0||
       phys.nx>std::numeric_limits<std::size_t>::max()/phys.ny)
        throw std::invalid_argument("P6C bridge invalid MIXHT grid");
    // Only maps the selected P6C one-upper-air-station case.
    // All gridded QH, USTAR, EL, RHO and previous-hour
    // ZICONV/DPTT must come from an independent, verified physics step.
    phys.justa={h.justa};
    phys.sounding[0]={h.physical_aa};
    phys.sounding[1]={h.physical_bb};
    phys.iupt=-1;
    if(phys.nearu.empty())
        phys.nearu.assign(phys.nx*phys.ny,1);
    for(int k:phys.nearu)
        if(k!=1)
            throw std::invalid_argument("P6C bridge only one upper-air station");
}
} // namespace cteas::p6e
