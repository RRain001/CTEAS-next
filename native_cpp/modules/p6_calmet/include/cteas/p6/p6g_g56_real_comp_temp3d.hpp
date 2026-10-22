#pragma once
// S4-R1c8h: actual 2SS/1US source-only TEMP3D after G54 AVEMIX and G55
// WSTARR. Reuse physical G18B upper/FACET and unchanged P6E TEMP3D.
// Existing G18C3 all-LAND fail-closed protection stays UNMODIFIED.
// Fortran TEMP3D outputs are not inputs; no production G26 authority.
#include "cteas/p6/p6g_g55_real_comp_wstarr.hpp"
#include "cteas/p6/p6g_g18b5_upper_temp_faces.hpp"
#include "cteas/p6/p6g_g18c3_temp3d_after_comp.hpp"
#include "cteas/p6e/temp3d_observed_land.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace cteas::calmet::p6g {
struct G56RealSourceTemp3d {
    std::chrono::sys_seconds end{};
    std::vector<float> temperature_k;
    std::size_t source_upper_stations=0,original_water_cells=0;
    bool firsthour_temp3d_forensic_only=false;
    bool native_g26_45field_ready=false;
    bool six_hour_comp_causal_ready=false;
};
inline G56RealSourceTemp3d g56_real_source_comp_temp3d(
    const G19SourceFilePaths& paths,bool explicitly_test_only){
    if(!explicitly_test_only)
        throw std::invalid_argument("G56 real source TEMP3D production unaccepted");
    const auto source=g41_load_selected_noow_water_first_hour_source(
        paths,true);
    const auto mixed=g54_real_noaa_firsthour_land_mixht(paths,true);
    const auto conv=g55_native_real_comp_wstarr(paths,true);
    auto scheduler=source.source.make_scheduler();
    const auto frame=scheduler.preview_next_hour();
    const auto& grid=source.source.grid;
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    const auto n=nx*ny;
    const auto ctrl=g18c3_parse_original_temp3d_controls(
        source.source.original_metinp);
    const auto partition=g26b_real_water_comp_partition_source_only(
        source,frame,true);
    if(!mixed.sparse_first_hour_research_only||
       !mixed.native_avemix_candidate_unverified||
       mixed.native_avemix_ready||mixed.g26_45field_ready||
       !conv.firsthour_source_only||conv.native_temp3d_ready||
       source.source.stations.surface.size()!=2||
       source.source.stations.upper.size()!=1||
       frame.hour_index!=0||scheduler.completed_hours()!=0||
       mixed.end!=frame.input.end||conv.end!=frame.input.end||
       ctrl.itprog!=0||!ctrl.lcalgrd||
       partition.original_water_cell_ordinals.size()!=63||
       mixed.comp_third_heat_k.size()!=n||
       mixed.ziconv_after_avemix_m.size()!=n||
       conv.wstar_mps.size()!=n)
        throw std::invalid_argument("G56 independent original G54/G55 source not ready");
    const auto upper=G18BUpperBufferClock{}.select(frame);
    const auto faces=g18b5_selected_native_temperature_faces(frame,upper);
    if(faces.end!=frame.input.end||faces.station_ids.size()!=1||
       faces.face_height_m.size()!=10||
       faces.aa_face_k.size()!=10||faces.bb_face_k.size()!=10)
        throw std::invalid_argument("G56 real upper FACET not source ordered");
    p6e::Temp3dObservedInput physical;
    physical.nx=nx;physical.ny=ny;physical.nz=9;
    physical.dgrid_m=grid.grid_km*1000.f;
    physical.irad=ctrl.irad;
    using namespace std::chrono;
    const auto hh=duration_cast<hours>(
        frame.input.end-floor<days>(frame.input.end)).count();
    physical.current_hour_utc=static_cast<int>(hh%12);
    physical.face_z_m=faces.face_height_m;
    physical.justa=faces.justa;
    physical.past_seconds=faces.past_seconds;
    physical.to_go_seconds=faces.to_go_seconds;
    physical.aa_face_temp_k=faces.aa_face_k;
    physical.bb_face_temp_k=faces.bb_face_k;
    physical.surface_temp_k=mixed.comp_third_heat_k;
    physical.convective_zi_m=mixed.ziconv_after_avemix_m;
    for(const auto& st:frame.stations.upper) {
        physical.station_x_m.push_back(st.local_x_m);
        physical.station_y_m.push_back(st.local_y_m);
    }
    auto t=p6e::temp3d_observed_land(physical);
    if(t.size()!=9*n)
        throw std::logic_error("G56 original source TEMP3D size missing");
    for(std::size_t i=0;i<n;++i)
        if(t[i]!=mixed.comp_third_heat_k[i])
            throw std::logic_error("G56 source TEMP3D k=1 must equal COMP third TEMP2D");
    for(const auto v:t)
        if(!std::isfinite(v)||v<180.f||v>350.f)
            throw std::logic_error("G56 nonfinite/nonphysical TEMP3D");
    return {frame.input.end,std::move(t),1,63,true,false,false};
}
} // namespace cteas::calmet::p6g
