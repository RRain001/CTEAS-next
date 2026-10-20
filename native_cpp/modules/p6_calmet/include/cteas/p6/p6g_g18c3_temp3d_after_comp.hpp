#pragma once
// G18C3: source-ordered COMP TEMP3D land branch, AFTER MIXHT, AVEMIX,
// WSTARR, using PR #53 unchanged temp3d_observed_land and original G18B5
// physical AA/BB FACET. Only tested source ITPROG=0, LCALGRD=T,
// IRAD=1/2 and 9 layers; general water, TEMP3D_BACK and P6F still gated.
#include "cteas/p6/p6g_g18c2_wstarr_after_avemix.hpp"
#include "cteas/p6/p6g_g18b5_upper_temp_faces.hpp"
#include "cteas/p6e/temp3d_observed_land.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6g {
struct G18C3Temp3dControls {
    int irad=0,itprog=-1;
    bool lcalgrd=false;
    // Defaults false. Only exact 1SS/1US selected source COMP may opt in.
    bool allow_one_one_source_audit=false;
    bool allow_asymmetric_source_audit=false;
};
inline G18C3Temp3dControls g18c3_parse_original_temp3d_controls(
    const std::string& source_metinp) {
    G18C3Temp3dControls out;
    out.irad=g18c1_source_integer(source_metinp,"IRAD");
    out.itprog=g18c1_source_integer(source_metinp,"ITPROG");
    const auto v=source_wind_normalize(source_wind_value(source_metinp,"LCALGRD"));
    if(v=="T"||v==".TRUE.")out.lcalgrd=true;
    else if(v=="F"||v==".FALSE.")out.lcalgrd=false;
    else throw std::invalid_argument("G18C3 malformed original LCALGRD");
    if(!out.lcalgrd||out.itprog!=0||(out.irad!=1&&out.irad!=2))
        throw std::invalid_argument("G18C3 source 3D temperature branch not selected");
    return out;
}
struct G18C3SelectedTemperature {
    std::chrono::sys_seconds end{};
    std::vector<int> station_ids;
    std::vector<float> temperature_k; // original k-major, J-major/I-fastest
    // G29B forensic input snapshot before frozen TEMP3D calculation.
    p6e::Temp3dObservedInput source_temp3d_input;
};
inline G18C3SelectedTemperature g18c3_selected_native_temp3d(
    const MultiHourFrame& frame,
    const G18BUpperHour& original_upper,
    const G18B5FaceTemperatures& original_faces,
    const G17CSelectedHeatResult& heat,
    const G18C2SourceCompAfterAverage& comp,
    const G18C3Temp3dControls& control,
    bool explicitly_test_only) {
    using namespace std::chrono;
    const auto n=static_cast<std::size_t>(frame.grid.nx)*
                 static_cast<std::size_t>(frame.grid.ny);
    const auto nu=frame.stations.upper.size();
    if(!explicitly_test_only||!frame.source_controls||
       control.itprog!=0||!control.lcalgrd||
       (control.irad!=1&&control.irad!=2)||
       frame.input.end!=original_upper.end||
       frame.input.end!=original_faces.end||
       frame.input.end!=heat.end||frame.input.end!=comp.end||
       (nu<2 && !((control.allow_one_one_source_audit && nu==1 &&
                    frame.stations.surface.size()==1)||
                    (control.allow_asymmetric_source_audit && nu==1 &&
                    frame.stations.surface.size()>=2)))||
       frame.upper.size()!=nu||
       original_upper.station_ids.size()!=nu||
       original_faces.station_ids!=original_upper.station_ids||
       original_faces.justa!=original_upper.justa||
       original_faces.past_seconds!=original_upper.past_seconds||
       original_faces.to_go_seconds!=original_upper.to_go_seconds||
       heat.temperature_k.size()!=n||
       comp.candidate_next.ziconv_m.size()!=n||
       frame.fields.u_mps.size()!=9*n||
       frame.fields.v_mps.size()!=9*n||
       frame.fields.w_face_mps.size()!=10*n||
       original_faces.face_height_m.size()!=10||
       original_faces.aa_face_k.size()!=nu*10||
       original_faces.bb_face_k.size()!=nu*10)
        throw std::invalid_argument("G18C3 source COMP/TEMP3D provenance incomplete");
    // Validate data content as well as station identity: a previous or
    // unrelated AA/BB temperature profile must never silently enter this hour.
    const auto genuine=g18b5_selected_native_temperature_faces(frame,original_upper);
    if(original_faces.face_height_m!=genuine.face_height_m||
       original_faces.aa_face_k!=genuine.aa_face_k||
       original_faces.bb_face_k!=genuine.bb_face_k)
        throw std::invalid_argument("G18C3 stale/forged source FACET faces");
    for(std::size_t k=0;k<nu;++k)
        if(frame.stations.upper[k].id!=original_faces.station_ids[k]||
           frame.upper[k].station_id!=original_faces.station_ids[k]||
           !std::isfinite(frame.stations.upper[k].local_x_m)||
           !std::isfinite(frame.stations.upper[k].local_y_m))
            throw std::invalid_argument("G18C3 upper station source ordinal or UTM invalid");
    for(int lu:frame.grid.landuse)
        if(lu>=frame.grid.iwat1&&lu<=frame.grid.iwat2)
            throw std::invalid_argument("G18C3 water TEMP3D original branch not accepted");
    p6e::Temp3dObservedInput in;
    in.nx=static_cast<std::size_t>(frame.grid.nx);
    in.ny=static_cast<std::size_t>(frame.grid.ny);
    in.nz=9;
    in.dgrid_m=frame.grid.grid_km*1000.f;
    in.irad=control.irad;
    const auto t=duration_cast<hours>(frame.input.end-floor<days>(frame.input.end)).count();
    // The original single-site frozen routine validates clock modulo 12
    // while explicit source bracket seconds supply true per-US time factors.
    in.current_hour_utc=static_cast<int>(t%12);
    in.face_z_m=original_faces.face_height_m;
    in.justa=original_faces.justa;
    in.past_seconds=original_faces.past_seconds;
    in.to_go_seconds=original_faces.to_go_seconds;
    in.aa_face_temp_k=original_faces.aa_face_k;
    in.bb_face_temp_k=original_faces.bb_face_k;
    in.surface_temp_k=heat.temperature_k;  // post-FRADJ SECOND SURFVAR
    in.convective_zi_m=comp.candidate_next.ziconv_m; // POST AVEMIX, never prior ZI
    for(const auto& st:frame.stations.upper) {
        in.station_x_m.push_back(st.local_x_m);
        in.station_y_m.push_back(st.local_y_m);
    }
    auto values=p6e::temp3d_observed_land(in);
    return {frame.input.end,original_faces.station_ids,std::move(values),in};
}
} // namespace cteas::calmet::p6g
