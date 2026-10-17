#pragma once
// G18D1: before the sole G14 hourly scheduler updates prior-hour ZICONV,
// compare its actual accepted 17-stage NativeHourFields to the selected P6F
// 45-record binary candidate and run the unchanged frozen P6F validator.
// No output file is published here; the returned complete byte image is a
// PREPARED result. Tests using synthetic/native-selected stage fixtures are
// not scientific original-CALMET 45-field multi-site validation.
#include "cteas/p6/p6g_g18c6_selected_p6f_dataset.hpp"
#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {

inline std::vector<std::uint8_t> g18d1_validate_p6f_precommit(
    const MultiHourFrame& frame,
    const cteas::p6f::Calmet21File& selected_output) {
    using namespace std::chrono;
    const auto n=static_cast<std::size_t>(frame.grid.nx)*
                 static_cast<std::size_t>(frame.grid.ny);
    const auto& h=selected_output.header;
    const auto& m=frame.next;
    const auto& f=frame.fields;
    if(!frame.source_controls||
       frame.input.end!=frame.surface.end||
       frame.surface.end-frame.surface.start!=hours{1}||
       h.irlg!=1||h.irtype!=1||!h.lcalgrd||
       h.nx!=frame.grid.nx||h.ny!=frame.grid.ny||h.nz!=9||
       h.nssta!=static_cast<int>(frame.stations.surface.size())||
       h.nusta!=static_cast<int>(frame.stations.upper.size())||
       h.npsta!=0||
       h.dgrid_m!=frame.grid.grid_km*1000.f||
       h.xorigin_m!=frame.grid.xorigin_km*1000.f||
       h.yorigin_m!=frame.grid.yorigin_km*1000.f||
       h.projection.iutmzn!=frame.grid.zone||
       h.projection.utmhem!=std::string(1,frame.grid.hemisphere)||
       selected_output.hourly.size()!=45||
       selected_output.statics.zface_m!=
           std::vector<float>(frame.source_controls->zface_m.begin(),
                              frame.source_controls->zface_m.end())||
       m.zi_m.size()!=n||m.ziconv_m.size()!=n||m.dptt_k.size()!=n||
       f.u_mps.size()!=9*n||f.v_mps.size()!=9*n||
       f.w_face_mps.size()!=10*n||
       f.temperature_k.size()!=9*n||
       f.qh_wm2.size()!=n||f.ustar_mps.size()!=n||
       f.el_m.size()!=n||f.wstar_mps.size()!=n)
        throw std::invalid_argument("G18D1 G14 hour/P6F grid or physical frame mismatch");
    const auto now=cteas::p6f::calendar_from_instant(
        frame.surface.end.time_since_epoch().count());
    if(h.end_year!=now.year||h.end_month!=now.month||
       h.end_day!=now.day||h.end_hour!=now.hour||
       h.end_second!=0)
        throw std::invalid_argument("G18D1 cannot publish P6F from another model hour");
    for(std::size_t k=0;k<frame.stations.surface.size();++k)
        if(selected_output.statics.surface_x_m.at(k)!=
               frame.stations.surface[k].local_x_m||
           selected_output.statics.surface_y_m.at(k)!=
               frame.stations.surface[k].local_y_m)
            throw std::invalid_argument("G18D1 wrong original SS output station");
    for(std::size_t k=0;k<frame.stations.upper.size();++k)
        if(selected_output.statics.upper_x_m.at(k)!=
               frame.stations.upper[k].local_x_m||
           selected_output.statics.upper_y_m.at(k)!=
               frame.stations.upper[k].local_y_m)
            throw std::invalid_argument("G18D1 wrong original US output station");

    // Requiring the actual in-flight G14 arrays prevents a valid-looking
    // binary constructed from an earlier hour or frozen MET.DAT weather
    // fields from passing merely because 45 record labels exist.
    const auto& records=selected_output.hourly;
    const auto expected=cteas::p6f::hourly_labels(9,1,true,0);
    if(records.size()!=expected.size())
        throw std::invalid_argument("G18D1 missing P6F hourly field");
    std::size_t slot=0;
    const auto compare_plane=[&](const std::vector<float>& current,
                                  std::size_t plane) {
        const auto& record=records.at(slot++);
        const auto start=plane*n;
        if(record.real_values.size()!=n||start+n>current.size()||
           !std::equal(record.real_values.begin(),record.real_values.end(),
                       current.begin()+static_cast<std::ptrdiff_t>(start)))
            throw std::invalid_argument("G18D1 P6F field differs from G14 physical state");
    };
    for(int k=0;k<9;++k) {
        compare_plane(f.u_mps,static_cast<std::size_t>(k));
        compare_plane(f.v_mps,static_cast<std::size_t>(k));
        compare_plane(f.w_face_mps,static_cast<std::size_t>(k+1));
    }
    for(int k=0;k<9;++k)
        compare_plane(f.temperature_k,static_cast<std::size_t>(k));
    // Original nine surface labels: IPGT(int), USTAR, ZI, EL,
    // WSTAR, TEMPK, RHO, QSW, IRH(int). The source hourly candidate
    // separately certifies the non-G14 TEMPK/RHO/QSW and IPGT/IRH.
    if(records.at(slot++).label!="IPGT    ")
        throw std::invalid_argument("G18D1 original IPGT source order");
    compare_plane(f.ustar_mps,0);
    compare_plane(m.zi_m,0);
    compare_plane(f.el_m,0);
    compare_plane(f.wstar_mps,0);
    // TEMPK/RHO/QSW each remain derived from the original G17C heat
    // handoff and are validated by G18C5/G18C6 source conversion.
    slot+=3;
    if(records.at(slot++).label!="IRH     "||slot!=45)
        throw std::invalid_argument("G18D1 original IRH source order");
    for(std::size_t k=0;k<45;++k)
        if(records[k].label!=expected[k])
            throw std::invalid_argument("G18D1 P6F original record order drift");
    // This call validates ALL fields, exact clocks and static geometry;
    // only after it succeeds can G14's precommit callback return normally.
    return cteas::p6f::serialize_calmet_dat21(selected_output);
}
} // namespace cteas::calmet::p6g
