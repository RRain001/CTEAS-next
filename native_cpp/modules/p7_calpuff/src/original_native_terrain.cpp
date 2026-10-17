#include "cteas/puff/original_native_terrain.hpp"
#include "cteas/puff/terrain_relief.hpp"
#include "cteas/puff/terrain_width.hpp"
#include "cteas/puff/step_integration.hpp"
#include <cmath>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::puff {
struct OriginalNativeTerrain::Data {
    int nx=0,ny=0;
    float spacing_m=0.0F;
    std::vector<float> elevation_msl;
    TerrainRelief relief;
    ValleyWidths width;
};
OriginalNativeTerrain::OriginalNativeTerrain(std::shared_ptr<const Data> p)
    :data_(std::move(p)) {}
OriginalNativeTerrain OriginalNativeTerrain::from_calmet(
    const Calmet21Static& statics,int nx,int ny,float spacing) {
    if(!statics.present || nx<3 || ny<3 ||
       !std::isfinite(spacing) || spacing<=0.0F ||
       statics.elevation_m.size()!=
           static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny))
        throw std::invalid_argument(
            "MCTADJ2 requires native CALMET OUTHD 2-D ELEV and positive grid");
    auto data=std::make_shared<Data>();
    data->nx=nx;data->ny=ny;data->spacing_m=spacing;
    data->elevation_msl=statics.elevation_m;
    for(float height:data->elevation_msl)
        if(!std::isfinite(height))
            throw std::invalid_argument(
                "MCTADJ2 native CALMET elevation is non-finite");
    const ElevationCell cell=[p=data](int i,int j){
        if(i<1||j<1||i>p->nx||j>p->ny)
            throw std::out_of_range("MCTADJ2 MET cell outside ELEV grid");
        return static_cast<double>(
            p->elevation_msl[static_cast<std::size_t>(j-1)*
                static_cast<std::size_t>(p->nx)+static_cast<std::size_t>(i-1)]);
    };
    data->relief=terrain_relief(nx,ny,cell);
    ValleyWidthInputs widths;
    widths.nx=nx;widths.ny=ny;widths.max_levels=10;
    data->width=valley_widths(widths,cell);
    return OriginalNativeTerrain(std::move(data));
}
TerrainLookup OriginalNativeTerrain::constraint_lookup() const {
    if(!data_)throw std::logic_error("missing native original terrain cache");
    const auto p=data_;
    const ElevationCell cell=[p](int i,int j){
        if(i<1||j<1||i>p->nx||j>p->ny)
            throw std::out_of_range("native MCTADJ2 ELEV outside MET grid");
        return static_cast<double>(
            p->elevation_msl[static_cast<std::size_t>(j-1)*
                static_cast<std::size_t>(p->nx)+static_cast<std::size_t>(i-1)]);
    };
    const auto index=[p](double x,double y){
        if(!std::isfinite(x)||!std::isfinite(y))
            throw std::invalid_argument("native MCTADJ2 non-finite MET position");
        // CALPUFF GETCELL/GRIDIJ (L82559-82720) returns a clamped
        // outer-edge cell even when the puff endpoint leaves the grid.
        // COMP retires the puff only AFTER the current SETPUF step.
        // Reuse the already source-ported REAL*4 grid_cell rather than
        // rejecting this physically valid last substep.
        const auto cell=grid_cell({
            .x_cells=x,.y_cells=y,
            .nx=p->nx,.ny=p->ny,.domains=1,.domain=1,.nest_factor=1.0
        });
        return std::pair<int,int>{cell.i,cell.j};
    };
    TerrainLookup out;
    out.elevation_msl=[p,cell](double x,double y){
        return interpolated_elevation({
            .x=x,.y=y,.nx=p->nx,.ny=p->ny,.nest_factor=1.0,
            .nest_offset_x=0.0,.nest_offset_y=0.0
        },cell);
    };
    out.cell_elevation_msl=[cell,index](double x,double y){
        const auto [i,j]=index(x,y);return cell(i,j);
    };
    out.relief=[p,index](double x,double y,int corner){
        if(corner<1||corner>5)
            throw std::out_of_range("invalid original TRELIEF corner index");
        const auto [i,j]=index(x,y);
        return p->relief.at(corner,i,j);
    };
    out.valley_width=[p,index](double x,double y,int level){
        if(level<1||level>p->width.max_levels)
            throw std::out_of_range("invalid original VWIDTH layer");
        const auto [i,j]=index(x,y);
        return p->width.at(level,i,j);
    };
    return out;
}
OriginalMctadj2ReceptorTerrain OriginalNativeTerrain::receptor(
    std::size_t i,int ibsamp,int jbsamp,int nxsam,int nysam,
    const OriginalPuffct2Result& puff,float bvf,float wind,float z)const{
    if(!data_||ibsamp<1||jbsamp<1||nxsam<1||nysam<1||
       i>=static_cast<std::size_t>(nxsam)*static_cast<std::size_t>(nysam)||
       !std::isfinite(bvf)||!std::isfinite(wind)||wind<=0.0F||
       !std::isfinite(z)||!std::isfinite(puff.x_m)||
       !std::isfinite(puff.y_m))
        throw std::invalid_argument("native PUFRECS MCTADJ2 invalid frame/state");
    const int ix=ibsamp+static_cast<int>(i%static_cast<std::size_t>(nxsam));
    const int iy=jbsamp+static_cast<int>(i/static_cast<std::size_t>(nxsam));
    if(ix>data_->nx||iy>data_->ny)
        throw std::out_of_range("native PUFRECS receptor outside MET ELEV");
    const auto idx=static_cast<std::size_t>(iy-1)*
        static_cast<std::size_t>(data_->nx)+static_cast<std::size_t>(ix-1);
    const auto lookup=constraint_lookup();
    // Original CALPUFF PUFRECS L5341-L5343 uses
    // XR1MET=XR1*DGRIDI / YR1MET=YR1*DGRIDI, where DGRIDI is
    // precomputed REAL*4 1/DGRID. Dividing by DGRID per receiver is
    // NOT REAL*4 equivalent and can shift GETELEV by a terrain ULP.
    const float dgridi=1.0F/data_->spacing_m;
    const float xr1met=puff.x_m*dgridi;
    const float yr1met=puff.y_m*dgridi;
    const auto under_puff=lookup.elevation_msl(
        static_cast<double>(xr1met),static_cast<double>(yr1met));
    return {
        .receptor_ground_elevation_msl=data_->elevation_msl[idx],
        .terrain_peak_elevation_msl=static_cast<float>(
            data_->relief.at(5,ix,iy)),
        .terrain_under_puff_msl=static_cast<float>(under_puff),
        .brunt_vaisala_s=bvf,.wind_speed_ms=wind,.receptor_height_m=z
    };
}
} // namespace cteas::puff
