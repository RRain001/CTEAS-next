#pragma once
// G24: selected original CALMET post-INTER2 HTFAC>0 WINDBC then
// SMOOTH / DIVCEL / W on the same G19-G23 file-backed first G14 hour.
// Original numeric kernel from frozen PR #53; no production stage
// completion/COMP state commit and no full multi-station vendor parity.
#include "cteas/p6/p6g_g23_file_backed_stheor_inter2.hpp"
#include "cteas/p6/diagno_segment.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G24SourceWindTail {
    std::chrono::sys_seconds end{};
    p6::FinalWindSegment wind;
    std::vector<float> second_ub_west_east_mps;
    std::vector<float> second_vb_south_north_mps;
    std::vector<float> pre_inter2_ub_west_east_mps;
    std::vector<float> pre_inter2_vb_south_north_mps;
};

// Shared selected original G24 tail, invoked by both the frozen G19
// all-LAND G23 route and a *separately guarded* G41 real-WATER forensic
// frame. Physical operations remain exclusively original_smooth_divcel_w.
// No stage completion or COMP history is committed by this helper.
inline G24SourceWindTail g24_selected_original_wind_tail_from_g16(
    const MultiHourFrame& frame,
    const p6::Inter2SelectedOutput& inter2_u,
    const p6::Inter2SelectedOutput& inter2_v,
    const std::vector<float>& first_ub,
    const std::vector<float>& first_vb,
    bool explicitly_test_only) {
    const auto nx=static_cast<std::size_t>(frame.grid.nx);
    const auto ny=static_cast<std::size_t>(frame.grid.ny);
    const auto n=nx*ny;
    if(!explicitly_test_only||!frame.source_controls||
       frame.grid.nx<2||frame.grid.ny<2||
       inter2_u.component_mps.size()!=9*n||
       inter2_v.component_mps.size()!=9*n||
       first_ub.size()!=18*ny||first_vb.size()!=18*nx||
       frame.source_controls->iobr!=0||frame.source_controls->iprog!=0)
        throw std::invalid_argument("G24 shared selected INTER2 handoff not source accepted");
    // Both G19 all-LAND and G41 mixed-WATER use this SINGLE frozen
    // HTFAC>0 tail, but only after upstream source admission.
    // CALMET L6092-L6101 then performs SECOND WINDBC after INTER2,
    // overwriting the transient SMOOTH boundary. The first WINDBC
    // boundary is preserved separately in G23 and cannot be erased.
    p6::SmoothInput smooth;
    smooth.nx=frame.grid.nx;
    smooth.ny=frame.grid.ny;
    smooth.nz=9;
    smooth.lake_breeze=false;
    smooth.passes_per_layer.assign(frame.source_controls->nsmth.begin(),
                                   frame.source_controls->nsmth.end());
    smooth.u_mps=inter2_u.component_mps;
    smooth.v_mps=inter2_v.component_mps;
    smooth.ub_west_east_mps.resize(18*ny);
    smooth.vb_south_north_mps.resize(18*nx);
    for(std::size_t k=0;k<9;++k) {
        for(std::size_t j=0;j<ny;++j) {
            const auto row=k*n+j*nx;
            const auto index=k*2*ny+j;
            smooth.ub_west_east_mps[index]=smooth.u_mps[row];
            smooth.ub_west_east_mps[index+ny]=smooth.u_mps[row+nx-1];
        }
        for(std::size_t i=0;i<nx;++i) {
            const auto row=k*n+i;
            const auto index=k*2*nx+i;
            smooth.vb_south_north_mps[index]=smooth.v_mps[row];
            smooth.vb_south_north_mps[index+nx]=
                smooth.v_mps[row+(ny-1)*nx];
        }
    }
    std::vector<float> dz;
    dz.reserve(9);
    for(std::size_t k=0;k<9;++k) {
        const float lo=frame.source_controls->zface_m[k];
        const float hi=frame.source_controls->zface_m[k+1];
        if(!std::isfinite(lo)||!std::isfinite(hi)||!(hi>lo))
            throw std::invalid_argument("G24 original ZFACE monotonicity broken");
        dz.push_back(hi-lo);
    }
    G24SourceWindTail result;
    result.end=frame.input.end;
    result.pre_inter2_ub_west_east_mps=first_ub;
    result.pre_inter2_vb_south_north_mps=first_vb;
    result.second_ub_west_east_mps=smooth.ub_west_east_mps;
    result.second_vb_south_north_mps=smooth.vb_south_north_mps;
    result.wind=p6::original_smooth_divcel_w(
        smooth,frame.grid.grid_km*1000.f,frame.grid.grid_km*1000.f,dz,false);
    if(result.wind.u_mps.size()!=9*n||result.wind.v_mps.size()!=9*n||
       result.wind.w_face_mps.size()!=10*n)
        throw std::logic_error("G24 original selected DIAGNO U/V/W incomplete");
    return result;
}
}

inline G24SourceWindTail g24_selected_original_wind_tail(
    const MultiHourFrame& frame,
    const G19FileBackedCase& source,
    const G23SelectedSourceStheorInter2& g23,
    bool explicitly_test_only) {
    const auto nx=static_cast<std::size_t>(frame.grid.nx);
    const auto ny=static_cast<std::size_t>(frame.grid.ny);
    const auto n=nx*ny;
    if(!explicitly_test_only||!frame.source_controls||
       frame.input.end!=g23.end||frame.hour_index!=g23.hour_index||
       source.grid.nx!=frame.grid.nx||source.grid.ny!=frame.grid.ny||
       source.grid.landuse!=frame.grid.landuse||
       source.grid.terrain_m!=frame.grid.terrain_m||
       frame.grid.grid_km!=source.grid.grid_km||
       g23.inter2_u.component_mps.size()!=9*n||
       g23.inter2_v.component_mps.size()!=9*n||
       g23.original_ub_west_east_mps.size()!=18*ny||
       g23.original_vb_south_north_mps.size()!=18*nx||
       frame.source_controls->iobr!=0||frame.source_controls->iprog!=0)
        throw std::invalid_argument("G24 original G14 first WINDBC/INTER2 source not accepted");
    return g24_selected_original_wind_tail_from_g16(
        frame,g23.inter2_u,g23.inter2_v,
        g23.original_ub_west_east_mps,
        g23.original_vb_south_north_mps,true);
}
} // namespace cteas::calmet::p6g
