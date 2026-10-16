#pragma once
// Independent source-first port of CALMET 6.5.0 L150223 WIND1.
// Original source: engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for
//   L36017-L36028: station input temporary state
//   L36204-L36251: inverse-square spatial weights
//   L36254-L36289: vertical BIAS
//   L36292-L36345: calm/upper-missing weight reassignment
//   L36384-L36397: field accumulation.
//
// Deliberately DOES NOT include any legacy CTEAS p6 header/implementation.
// This function takes the REAL*4 US/VS station profiles AFTER original
// PREPDI and original neutral SIMILT; reconstructing those is a separate
// source-based task. Scope: 1 land SS + 1 US, no overwater or barriers,
// IEXTRP=-4, IPROG=0, 50x50x9. Fail closed on unsupported controls.
//
// All original REAL*4 variables and intermediate values are float. Keep
// intermediate assignments distinct and avoid fused multiply-add; this is
// source-faithful numerical reproduction, not a double-precision rewrite.
#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::p6d_rebuild {

using Real4=float;
constexpr std::size_t K=9;

struct StationWind {
    Real4 x_m{},y_m{};
    std::array<Real4,K> u_mps{},v_mps{};
};
struct Wind1Controls {
    int nx=50,ny=50,nz=9;
    int nssta=1,nusta=1,nowsta=0,nbar=0,iextrp=-4,icalm=0;
    // Frozen original-source WIND1 oracle sets EDITL=900.f; 999.f marks
    // missing upper-air levels. Keep the threshold aligned with Fortran.
    Real4 dgrid_m=100.f,editl=900.f;
    Real4 surface_measured_u{},surface_measured_v{};
    std::array<Real4,K> bias{};
    StationWind surface,upper;
};
struct Wind1Field {
    std::vector<Real4> u_mps,v_mps;
};
inline Real4 real4(Real4 value) noexcept {
    volatile Real4 stored=value;
    return stored;
}
inline void validate(const Wind1Controls& c) {
    if(c.nx!=50||c.ny!=50||c.nz!=9||c.nssta!=1||c.nusta!=1||
       c.nowsta!=0||c.nbar!=0||c.iextrp!=-4||
       (c.icalm!=0&&c.icalm!=1)||!(c.dgrid_m>0.f)||
       !std::isfinite(c.dgrid_m)||!(c.editl>0.f))
        throw std::invalid_argument("unsupported source-first WIND1 configuration");
    if(!std::isfinite(c.surface.x_m)||!std::isfinite(c.surface.y_m)||
       !std::isfinite(c.upper.x_m)||!std::isfinite(c.upper.y_m)||
       !std::isfinite(c.surface_measured_u)||
       !std::isfinite(c.surface_measured_v))
        throw std::invalid_argument("WIND1 missing/invalid coordinate or source wind");
    for(std::size_t k=0;k<K;++k){
        if(!std::isfinite(c.bias[k])||c.bias[k]<-1.f||c.bias[k]>1.f)
            throw std::invalid_argument("WIND1 BIAS outside original -1..1");
        const auto valid=[&](Real4 v){return std::isfinite(v);};
        if(!valid(c.surface.u_mps[k])||!valid(c.surface.v_mps[k])||
           !valid(c.upper.u_mps[k])||!valid(c.upper.v_mps[k]))
            throw std::invalid_argument("WIND1 nonfinite US/VS");
        if(c.surface.u_mps[k]>=c.editl||c.surface.v_mps[k]>=c.editl)
            throw std::invalid_argument("WIND1 scoped path requires valid surface profile");
    }
}
inline Wind1Field wind1_from_original_station_profiles(const Wind1Controls& c) {
    validate(c);
    Wind1Field result;
    const std::size_t plane=static_cast<std::size_t>(c.nx)*static_cast<std::size_t>(c.ny);
    result.u_mps.assign(plane*K,0.f);
    result.v_mps.assign(plane*K,0.f);
    const Real4 dgridi=real4(1.f/c.dgrid_m);
    const Real4 ws10=real4(std::sqrt(real4(c.surface_measured_u*c.surface_measured_u)
                                   +real4(c.surface_measured_v*c.surface_measured_v)));
    if(ws10<0.0001f)for(std::size_t k=0;k<K;++k) {
        if(c.surface.u_mps[k]!=0.f||c.surface.v_mps[k]!=0.f)
            throw std::invalid_argument("WIND1 original calm state inconsistent");
    }
    // Preserve Fortran WIND1's I outer, J inner, K inner loop ordering.
    for(int i=1;i<=c.nx;++i)for(int j=1;j<=c.ny;++j){
        const Real4 xc=real4(static_cast<Real4>(i)-0.5f);
        const Real4 yc=real4(static_cast<Real4>(j)-0.5f);
        auto spatial_weight=[&](const StationWind& s) {
            const Real4 dx=real4(real4(s.x_m*dgridi)-xc);
            const Real4 dy=real4(real4(s.y_m*dgridi)-yc);
            const Real4 xr2=real4(real4(dx*dx)+real4(dy*dy));
            return xr2<1.f?Real4(1.f):real4(1.f/xr2);
        };
        const Real4 weight_s=spatial_weight(c.surface);
        const Real4 weight_u=spatial_weight(c.upper);
        const Real4 sumwt=real4(1.f/real4(weight_s+weight_u));
        const Real4 rsq_s=real4(weight_s*sumwt);
        const Real4 rsq_u=real4(weight_u*sumwt);
        for(std::size_t k=0;k<K;++k){
            const Real4 bias=c.bias[k];
            Real4 beta{},gamma{};
            if(bias>=0.f) {
                beta=real4(1.f-bias);
                gamma=real4(real4(bias+real4(real4(1.f-bias)*rsq_u))/rsq_u);
            } else {
                beta=real4(real4(real4(-bias)+real4(real4(1.f+bias)*rsq_s))/rsq_s);
                gamma=real4(1.f+bias);
            }
            Real4 vvw_s=real4(beta*rsq_s);
            Real4 vvw_u=real4(gamma*rsq_u);
            // original L36292-L36317: calm surface winds, only k>1
            if(c.icalm==0&&ws10<0.0001f&&k>0){
                if(vvw_s<0.9999f)
                    vvw_u=real4(vvw_u/real4(1.f-vvw_s));
                else
                    vvw_u=real4(rsq_u/real4(1.f-rsq_s));
                vvw_s=0.f;
            }
            // original L36319-L36345: upper station missing this level
            if(bias> -0.9999f &&
               (c.upper.u_mps[k]>c.editl||c.upper.v_mps[k]>c.editl)){
                if(vvw_u==1.f)
                    throw std::invalid_argument("WIND1 no valid station at upper level");
                vvw_s=real4(vvw_s/real4(1.f-vvw_u));
                vvw_u=0.f;
            }
            // Original accumulator starts at 0 for each component.
            Real4 unext=0.f,vnext=0.f;
            unext=real4(unext+real4(vvw_s*c.surface.u_mps[k]));
            vnext=real4(vnext+real4(vvw_s*c.surface.v_mps[k]));
            // Fortran multiplies zero weight with its 999999 sentinel; the
            // result is REAL*4 zero, not a missing value.
            unext=real4(unext+real4(vvw_u*c.upper.u_mps[k]));
            vnext=real4(vnext+real4(vvw_u*c.upper.v_mps[k]));
            if(!std::isfinite(unext)||!std::isfinite(vnext))
                throw std::invalid_argument("WIND1 nonfinite final wind");
            const std::size_t id=k*plane+static_cast<std::size_t>(j-1)*
                static_cast<std::size_t>(c.nx)+static_cast<std::size_t>(i-1);
            result.u_mps[id]=unext;
            result.v_mps[id]=vnext;
        }
    }
    return result;
}
} // namespace cteas::p6d_rebuild
