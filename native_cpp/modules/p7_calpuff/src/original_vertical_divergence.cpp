#include "cteas/puff/original_vertical_divergence.hpp"
#include "cteas/puff/advection.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace cteas::puff {
NativeOriginalWdivResult original_vertical_divergence(
    const OriginalMetHour& met,const Calmet21Static& statics,
    OriginalMetCell begin,OriginalMetCell end,
    float zbot_m,float ztop_m,float tsamp_s,
    float sigma_z_before_m,int puff_code,
    const NativeOriginalWdivControls& cfg) {
    if(met.nx<=0||met.ny<=0||met.nz<=0||
       !(std::isfinite(zbot_m)&&std::isfinite(ztop_m)&&zbot_m<=ztop_m)||
       !(std::isfinite(tsamp_s)&&tsamp_s>0.0F)||
       !(std::isfinite(sigma_z_before_m)&&sigma_z_before_m>=0.0F)||
       !(std::isfinite(cfg.cdiv_begin_s)&&std::isfinite(cfg.cdiv_full_s)&&
         cfg.cdiv_begin_s>=0.0F&&cfg.cdiv_full_s>=cfg.cdiv_begin_s))
        throw std::invalid_argument("original WDIV requires valid MET, CDIV, sigma and TSAMP");
    NativeOriginalWdivResult result;
    result.sigma_z_m=sigma_z_before_m;
    if(puff_code%2==0)return result; // original only Gaussian ICODE.
    const auto xy=static_cast<std::size_t>(met.nx)*static_cast<std::size_t>(met.ny);
    const auto nz=static_cast<std::size_t>(met.nz);
    if(met.w.size()!=xy*nz||statics.cell_face_m.size()!=nz+1U||
       begin.offset_0based>=xy||end.offset_0based>=xy)
        throw std::invalid_argument("original WDIV needs complete CALMET W and ZFACE");
    AdvectiveWindInputs a;
    a.met_format=1;
    a.z_bottom_m=zbot_m;
    a.z_top_m=ztop_m;
    a.face_heights_m.reserve(nz+1U);
    a.u_profile_ms.reserve(nz);
    a.v_profile_ms.reserve(nz);
    for(const float face:statics.cell_face_m)a.face_heights_m.push_back(face);
    for(std::size_t k=0;k<nz;++k){
        const float depth=statics.cell_face_m[k+1U]-statics.cell_face_m[k];
        if(!(std::isfinite(depth)&&depth>0.0F))
            throw std::invalid_argument("original WDIV requires positive ZFACE layer");
        const float invdepth=1.0F/depth; // DELZI(K), REAL4
        const auto b=k*xy+begin.offset_0based;
        const auto e=k*xy+end.offset_0based;
        const float bs=met.w[b],es=met.w[e];
        const float bp=k?met.w[(k-1U)*xy+begin.offset_0based]:0.0F;
        const float ep=k?met.w[(k-1U)*xy+end.offset_0based]:0.0F;
        if(!std::isfinite(bs)||!std::isfinite(es)||
           !std::isfinite(bp)||!std::isfinite(ep))
            throw std::invalid_argument("original WDIV encountered nonfinite CALMET W");
        // Vendor first computes WDIV fields in descending K (L9555), then
        // independently averages start and end profiles with ADVWND.
        a.u_profile_ms.push_back(invdepth*(bs-bp));
        a.v_profile_ms.push_back(invdepth*(es-ep));
    }
    const auto avg=advective_wind(a);
    const float ds=static_cast<float>(avg.u_ms);
    const float de=static_cast<float>(avg.v_ms);
    const float maximum=std::max(ds,de);
    result.start_divergence_s=ds;
    result.end_divergence_s=de;
    result.max_divergence_s=maximum;
    if(maximum>cfg.cdiv_begin_s) {
        float fraction=1.0F;
        if(maximum<cfg.cdiv_full_s)
            fraction=(maximum-cfg.cdiv_begin_s)/
                     (cfg.cdiv_full_s-cfg.cdiv_begin_s);
        const float fac=1.0F+fraction*maximum*tsamp_s;
        if(!(std::isfinite(fac)&&fac>0.0F))
            throw std::invalid_argument("original WDIV generated invalid sigma factor");
        result.factor=fac;
        result.sigma_z_m=sigma_z_before_m*fac;
    }
    return result;
}
} // namespace cteas::puff
