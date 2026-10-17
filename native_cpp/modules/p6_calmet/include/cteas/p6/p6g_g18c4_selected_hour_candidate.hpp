#pragma once
// G18C4: assemble the eight frozen G14 NativeHourFields plus the
// post-AVEMIX current COMP state, without changing the G14 scheduler,
// committing an hour, or claiming a P6F/45-field scientific result.
#include "cteas/p6/p6g_g18c3_temp3d_after_comp.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G18C4SelectedCandidate {
    std::chrono::sys_seconds end{};
    p6::NativeGridMemory candidate_memory;
    p6::NativeHourFields candidate_fields;
};
inline G18C4SelectedCandidate g18c4_assemble_selected_hour(
    const MultiHourFrame& frame,
    const G17CSelectedHeatResult& heat,
    const G17C2SelectedElustrResult& elustr,
    const G18C2SourceCompAfterAverage& comp,
    const G18C3SelectedTemperature& temp,
    bool explicitly_test_only) {
    const auto n=static_cast<std::size_t>(frame.grid.nx)*
                 static_cast<std::size_t>(frame.grid.ny);
    if(!explicitly_test_only||
       frame.input.end!=heat.end||frame.input.end!=elustr.end||
       frame.input.end!=comp.end||frame.input.end!=temp.end||
       temp.station_ids.size()!=frame.stations.upper.size()||
       heat.temperature_k.size()!=n||elustr.qh_wm2.size()!=n||
       elustr.ustar_mps.size()!=n||elustr.el_m.size()!=n||
       comp.wstar_mps.size()!=n||
       comp.candidate_next.zi_m.size()!=n||
       comp.candidate_next.ziconv_m.size()!=n||
       comp.candidate_next.dptt_k.size()!=n||
       temp.temperature_k.size()!=9*n||
       frame.fields.u_mps.size()!=9*n||
       frame.fields.v_mps.size()!=9*n||
       frame.fields.w_face_mps.size()!=10*n)
        throw std::invalid_argument("G18C4 incomplete source-hour U/V/W/P6E candidate");
    for(std::size_t k=0;k<temp.station_ids.size();++k)
        if(temp.station_ids[k]!=frame.stations.upper[k].id)
            throw std::invalid_argument("G18C4 TEMP3D station identity not source ordered");
    p6::NativeHourFields fields;
    fields.u_mps=frame.fields.u_mps;
    fields.v_mps=frame.fields.v_mps;
    fields.w_face_mps=frame.fields.w_face_mps;
    fields.temperature_k=temp.temperature_k;
    fields.qh_wm2=elustr.qh_wm2;
    fields.ustar_mps=elustr.ustar_mps;
    fields.el_m=elustr.el_m;
    fields.wstar_mps=comp.wstar_mps;
    for(const auto* field:{&fields.u_mps,&fields.v_mps,&fields.w_face_mps,
                           &fields.temperature_k,&fields.qh_wm2,
                           &fields.ustar_mps,&fields.el_m,&fields.wstar_mps})
        for(const float value:*field)
            if(!std::isfinite(value)||value==9999.f)
                throw std::invalid_argument("G18C4 nonfinite source physical field");
    for(std::size_t k=0;k<n;++k)
        if(comp.candidate_next.zi_m[k]<0.f||
           comp.candidate_next.ziconv_m[k]<0.f||
           !std::isfinite(comp.candidate_next.zi_m[k])||
           !std::isfinite(comp.candidate_next.ziconv_m[k])||
           !std::isfinite(comp.candidate_next.dptt_k[k]))
            throw std::invalid_argument("G18C4 incomplete COMP candidate state");
    return {frame.input.end,comp.candidate_next,std::move(fields)};
}
} // namespace cteas::calmet::p6g
