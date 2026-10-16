#pragma once
// CALMET 6.5.0 L150223 WIND1 selected one-land-surface + one-upper station
// FIRST-GUESS interpolation (original calmet.for L36017–36402).
//
// Wind profiles MUST be prepared independently (P6D8A neutral SIMILT and
// P6C PREPDI). The calculation below is the original bulk 1/R^2 weighting,
// nine-level positive/negative BIAS adjustment, ICALM=0 reweighting,
// upper-layer missing-data reweighting, and UG/VG accumulation.
//
// Deliberately unsupported: overwater stations, barriers (NBAR>0), other
// IEXTRP, fully generalized multi-station interpolation, prognostic winds,
// FRADJ/SLOPE and subsequent DIAGNO. This kernel is not full P6D acceptance.
#include "cteas/p6/wind1_selected_station_hour.hpp"
#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6 {

struct Wind1FirstGuessSelectedControls {
    int nx=50,ny=50,nz=9;
    float grid_spacing_m=100.f;
    float surface_x_relative_m=0.f,surface_y_relative_m=0.f;
    float upper_x_relative_m=0.f,upper_y_relative_m=0.f;
    std::array<float,9> vertical_bias{};
    std::array<bool,9> upper_layer_valid{
        true,true,true,true,true,true,true,true,true
    };
    int icalm=0,iextrp=-4,nbar=0,nowsta=0,nusta=1,nssta=1;
};
struct Wind1FirstGuessSelectedFields {
    int nx{},ny{},nz{};
    // Flat k-major, j-major, i-fastest; original UG(i,j,k)/VG(i,j,k).
    std::vector<float> ug_mps,vg_mps;
    // Write-only diagnostic: actual normalized WIND1 two-station RSQWT per gridpoint.
    std::vector<float> rsq_surface,rsq_upper;
    // Final level-one weights after BIAS and upper missing-value redistribution.
    std::vector<float> vvw_surface1,vvw_upper1;
    // Weights after BETA/GAMMA, before any calm or upper-missing reallocation.
    std::vector<float> pre_vvw_surface1,pre_vvw_upper1;
    // VVW after BIAS/calm weighting but BEFORE upper missing-data rebalance.
    std::vector<float> vvw_surface_before1,vvw_upper_before1;
};
inline Wind1FirstGuessSelectedFields wind1_firstguess_selected(
    const Wind1SelectedStationHour& station,
    const Wind1FirstGuessSelectedControls& c) {

    if(c.nx!=50||c.ny!=50||c.nz!=9||
       c.nbar!=0||c.nowsta!=0||c.nusta!=1||c.nssta!=1||
       c.iextrp!=-4||(c.icalm!=0&&c.icalm!=1)||
       station.surface_station_id<=0||station.upper_station_id<=0||
       !(c.grid_spacing_m>0.f)||!std::isfinite(c.grid_spacing_m)||
       !std::isfinite(c.surface_x_relative_m)||
       !std::isfinite(c.surface_y_relative_m)||
       !std::isfinite(c.upper_x_relative_m)||
       !std::isfinite(c.upper_y_relative_m)||
       !std::isfinite(station.surface_observed_u_mps)||
       !std::isfinite(station.surface_observed_v_mps))
        throw std::invalid_argument("WIND1 selected first-guess controls unsupported");

    for(std::size_t k=0;k<9;k++){
        const auto b=c.vertical_bias[k];
        if(!std::isfinite(b)||b< -1.f||b>1.f)
            throw std::invalid_argument("WIND1 BIAS outside [-1,1]");
        const auto& s=station.surface_neutral_profile[k];
        const auto& u=station.upper_observed_profile[k];
        if(!std::isfinite(s.u_mps)||!std::isfinite(s.v_mps)||
           !std::isfinite(u.u_mps)||!std::isfinite(u.v_mps)||
           std::abs(s.u_mps)>=998.99f||std::abs(s.v_mps)>=998.99f)
            throw std::invalid_argument("WIND1 surface or upper nonfinite/missing");
        if(c.upper_layer_valid[k]) {
            if(std::abs(u.u_mps)>=998.99f||std::abs(u.v_mps)>=998.99f)
                throw std::invalid_argument("WIND1 upper validity mask disagrees with values");
        } else if(u.u_mps!=999.f||u.v_mps!=999.f) {
            // CALMET's DIAGNO initializes EDIT=999 (EDITL=900).
            // The IEXTRP<=0 PREPDI first upper level must use this exact
            // REAL*4 missing value. The earlier 999998 threshold incorrectly
            // rejected 999.f and aborted all native 143-hour production.
            throw std::invalid_argument("WIND1 invalid upper mask must use original EDIT=999 sentinel");
        }
    }
    const float first_speed=std::sqrt(
        station.surface_observed_u_mps*station.surface_observed_u_mps+
        station.surface_observed_v_mps*station.surface_observed_v_mps);
    if(!std::isfinite(first_speed))
        throw std::invalid_argument("WIND1 nonfinite original wind speed");
    if(first_speed<0.0001f)for(const auto& s:station.surface_neutral_profile){
        if(s.u_mps!=0.f||s.v_mps!=0.f)
            throw std::invalid_argument("WIND1 calm profile must have zero velocity");
    }

    Wind1FirstGuessSelectedFields out;
    out.nx=c.nx;out.ny=c.ny;out.nz=c.nz;
    const std::size_t cells=static_cast<std::size_t>(c.nx)*static_cast<std::size_t>(c.ny);
    out.ug_mps.assign(cells*9,0.f);
    out.vg_mps.assign(cells*9,0.f);
    out.rsq_surface.assign(cells,0.f);
    out.rsq_upper.assign(cells,0.f);
    out.vvw_surface1.assign(cells,0.f);
    out.vvw_upper1.assign(cells,0.f);
    out.pre_vvw_surface1.assign(cells,0.f);
    out.pre_vvw_upper1.assign(cells,0.f);
    out.vvw_surface_before1.assign(cells,0.f);
    out.vvw_upper_before1.assign(cells,0.f);

    // Original WIND1: DGRIDI=1./DGRID; XC=FLOAT(I)-0.5, YC likewise.
    const float dgridi=1.f/c.grid_spacing_m;
    for(int i=1;i<=c.nx;i++)for(int j=1;j<=c.ny;j++){
        const float xc=static_cast<float>(i)-0.5f;
        const float yc=static_cast<float>(j)-0.5f;
        const float dsx=c.surface_x_relative_m*dgridi-xc;
        const float dsy=c.surface_y_relative_m*dgridi-yc;
        const float dux=c.upper_x_relative_m*dgridi-xc;
        const float duy=c.upper_y_relative_m*dgridi-yc;
        const float r2_surface=dsx*dsx+dsy*dsy;
        const float r2_upper=dux*dux+duy*duy;
        const float w_surface=(r2_surface<1.f)?1.f:1.f/r2_surface;
        const float w_upper=(r2_upper<1.f)?1.f:1.f/r2_upper;
        // Original SUMWT is REAL*4, then overwritten by reciprocal.
        const float w_inverse=1.f/(w_surface+w_upper);
        const float rsq_surface=w_surface*w_inverse;
        const float rsq_upper=w_upper*w_inverse;
        if(!(std::isfinite(rsq_surface)&&std::isfinite(rsq_upper)&&
             rsq_surface>0.f&&rsq_upper>0.f))
            throw std::invalid_argument("WIND1 invalid inverse distance weights");
        const auto cell=static_cast<std::size_t>(j-1)*static_cast<std::size_t>(c.nx)+
                        static_cast<std::size_t>(i-1);
        out.rsq_surface[cell]=rsq_surface;
        out.rsq_upper[cell]=rsq_upper;

        for(std::size_t k=0;k<9;k++){
            const float bias=c.vertical_bias[k];
            float beta=0.f,gamma=0.f;
            if(bias>=0.f){
                beta=1.f-bias;
                gamma=(bias+(1.f-bias)*rsq_upper)/rsq_upper;
            }else{
                beta=(-bias+(1.f+bias)*rsq_surface)/rsq_surface;
                gamma=1.f+bias;
            }
            float vsurface=beta*rsq_surface;
            float vupper=gamma*rsq_upper;
            if(k==0){
                out.pre_vvw_surface1[cell]=vsurface;
                out.pre_vvw_upper1[cell]=vupper;
            }
            if(c.icalm==0&&first_speed<0.0001f&&k>0){
                if(vsurface<0.9999f) {
                    vupper=vupper/(1.f-vsurface);
                }else {
                    vupper=rsq_upper/(1.f-rsq_surface);
                }
                vsurface=0.f;
            }
            if(k==0) {
                out.vvw_surface_before1[cell]=vsurface;
                out.vvw_upper_before1[cell]=vupper;
            }
            if(bias> -0.9999f&&!c.upper_layer_valid[k]){
                if(vupper==1.f)
                    throw std::invalid_argument("WIND1 no valid upper observation at layer");
                vsurface=vsurface/(1.f-vupper);
                vupper=0.f;
            }
            if(k==0) {
                out.vvw_surface1[cell]=vsurface;
                out.vvw_upper1[cell]=vupper;
            }
            const auto& s=station.surface_neutral_profile[k];
            const auto& u=station.upper_observed_profile[k];
            const float ug=vsurface*s.u_mps+vupper*u.u_mps;
            const float vg=vsurface*s.v_mps+vupper*u.v_mps;
            if(!std::isfinite(ug)||!std::isfinite(vg))
                throw std::invalid_argument("WIND1 nonfinite first-guess wind");
            const std::size_t pos=k*cells+
                static_cast<std::size_t>(j-1)*static_cast<std::size_t>(c.nx)+
                static_cast<std::size_t>(i-1);
            out.ug_mps[pos]=ug;
            out.vg_mps[pos]=vg;
        }
    }
    return out;
}

} // namespace cteas::calmet::p6