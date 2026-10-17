#pragma once
// G18B5: Per-UP FACET temperature-face interpolation for physical AA/BB
// through the unchanged PR #53 calmet_facet_temperatures kernel.
// The next TEMP3D/COMP step must still supply actual grid ZICONV and
// source-authenticated spatial/time weighting; never call this a full P6F.
#include "cteas/p6/p6g_g18b_upper_buffer_clock.hpp"
#include "cteas/p6/temperature_faces.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G18B5FaceTemperatures {
    std::chrono::sys_seconds end{};
    std::vector<int> station_ids,justa,past_seconds,to_go_seconds;
    std::vector<float> face_height_m;
    // Physical AA / BB, station-major, stride face_height_m.size().
    std::vector<float> aa_face_k,bb_face_k;
};
inline G18B5FaceTemperatures g18b5_selected_native_temperature_faces(
    const MultiHourFrame& frame,const G18BUpperHour& upper) {
    if(!frame.source_controls||frame.input.end!=upper.end||
       frame.upper.size()!=frame.stations.upper.size()||
       upper.station_ids.size()!=frame.upper.size()||
       upper.physical_aa_index.size()!=frame.upper.size()||
       upper.physical_bb_index.size()!=frame.upper.size()||
       upper.justa.size()!=frame.upper.size())
        throw std::invalid_argument("G18B5 original hour/UP model source mismatch");
    // Enforce original thermal profile, source order, timestamp and
    // AA/BB identities before invoking frozen numerical interpolation.
    p6e::MixhtObservedMcInput probe;
    g18b_bind_physical_upper(probe,frame,upper);
    G18B5FaceTemperatures output;
    output.end=frame.input.end;
    output.station_ids=upper.station_ids;
    output.justa=upper.justa;
    output.past_seconds=upper.past_seconds;
    output.to_go_seconds=upper.to_go_seconds;
    output.face_height_m.assign(
        frame.source_controls->zface_m.begin(),
        frame.source_controls->zface_m.end());
    const auto face_count=output.face_height_m.size();
    if(face_count!=10)
        throw std::invalid_argument("G18B5 only source-certified nine layers");
    for(std::size_t k=0;k<face_count;++k) {
        if(!std::isfinite(output.face_height_m[k])||
           output.face_height_m[k]<0.f||
           (k>0&&output.face_height_m[k]<=output.face_height_m[k-1]))
            throw std::invalid_argument("G18B5 original ZFACE malformed");
    }
    output.aa_face_k.reserve(frame.upper.size()*face_count);
    output.bb_face_k.reserve(frame.upper.size()*face_count);
    for(std::size_t i=0;i<frame.upper.size();++i) {
        const auto& series=frame.upper[i].soundings;
        const auto aa=p6::calmet_facet_temperatures(
            series.at(upper.physical_aa_index[i]),output.face_height_m);
        const auto bb=p6::calmet_facet_temperatures(
            series.at(upper.physical_bb_index[i]),output.face_height_m);
        output.aa_face_k.insert(output.aa_face_k.end(),aa.begin(),aa.end());
        output.bb_face_k.insert(output.bb_face_k.end(),bb.begin(),bb.end());
    }
    return output;
}
} // namespace cteas::calmet::p6g
