#include "cteas/puff/original_met_cell.hpp"
#include "cteas/puff/step_integration.hpp"

#include <cmath>
#include <stdexcept>

namespace cteas::puff {
OriginalMetCell original_met_cell(float x,float y,int nx,int ny) {
    if(nx<=0 || ny<=0 || !std::isfinite(x) || !std::isfinite(y) ||
       x<0.0F || y<0.0F || x>=static_cast<float>(nx) ||
       y>=static_cast<float>(ny))
        throw std::out_of_range("P7 original GETCELL: puff outside MET grid");
    // The original CALPUFF GETCELL/GRIDIJ implementation is already ported
    // as grid_cell(). Reuse that authoritative routine rather than creating
    // another, subtly different rounding / boundary algorithm.
    CellLookupInputs request;
    request.x_cells=x;
    request.y_cells=y;
    request.nx=nx;request.ny=ny;
    request.domains=1;request.domain=1;request.nest_factor=1.0;
    const auto found=grid_cell(request);
    return {found.i,found.j,
            static_cast<std::size_t>(found.j-1)*static_cast<std::size_t>(nx)
            +static_cast<std::size_t>(found.i-1)};
}

OriginalMetCell original_met_cell_clamped(
    float x,float y,int nx,int ny) {
    if(nx<=0 || ny<=0 || !std::isfinite(x) || !std::isfinite(y))
        throw std::invalid_argument("P7 original GETCELL: invalid midpoint inputs");
    const auto selected=grid_cell({
        .x_cells=x,.y_cells=y,.nx=nx,.ny=ny,
        .domains=1,.domain=1,.nest_factor=1.0
    });
    return {selected.i,selected.j,
            static_cast<std::size_t>(selected.j-1)*static_cast<std::size_t>(nx)+
            static_cast<std::size_t>(selected.i-1)};
}

AdvectiveWind original_met_cell_advect(
    const OriginalMetHour& hour,const Calmet21Static& statics,
    OriginalMetCell cell,float bottom,float top) {
    if(hour.nx<=0 || hour.ny<=0 || hour.nz<=0 ||
       cell.ix_1based<1 || cell.ix_1based>hour.nx ||
       cell.iy_1based<1 || cell.iy_1based>hour.ny ||
       !std::isfinite(bottom) || !std::isfinite(top) || bottom>top)
        throw std::invalid_argument("P7 original METFM1: bad cell, grid or Z bounds");
    const auto xy=static_cast<std::size_t>(hour.nx)*static_cast<std::size_t>(hour.ny);
    const auto offset=static_cast<std::size_t>(cell.iy_1based-1)*
                      static_cast<std::size_t>(hour.nx)+
                      static_cast<std::size_t>(cell.ix_1based-1);
    if(cell.offset_0based!=offset || statics.cell_face_m.size()!=
       static_cast<std::size_t>(hour.nz+1) ||
       hour.u.size()!=xy*static_cast<std::size_t>(hour.nz) ||
       hour.v.size()!=xy*static_cast<std::size_t>(hour.nz))
        throw std::invalid_argument("P7 original METFM1: inconsistent typed hour or cell");
    AdvectiveWindInputs input;
    input.met_format=1;
    input.z_bottom_m=bottom;
    input.z_top_m=top;
    for(float z:statics.cell_face_m) input.face_heights_m.push_back(z);
    for(int z=0;z<hour.nz;++z) {
        const auto at=static_cast<std::size_t>(z)*xy+offset;
        input.u_profile_ms.push_back(hour.u.at(at));
        input.v_profile_ms.push_back(hour.v.at(at));
    }
    return advective_wind(input);
}
} // namespace cteas::puff
