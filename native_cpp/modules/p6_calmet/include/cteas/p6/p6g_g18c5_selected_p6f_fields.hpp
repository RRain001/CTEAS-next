#pragma once
// G18C5: source-stamped, selected-only 45 record candidate for P6F.
// Reuse accepted P6E PGTSTB and SURFVAR multi-SS for IPGT and IRH.
// Uses genuine G18C4 U/V/W/T/USTAR/ZI/EL/WSTAR and G17C1 TEMPK/RHO/QSW.
// This is NOT a full P6F writer or original 45-field multi-SS acceptance:
// no file is emitted, and no reference data may backfill a missing field.
#include "cteas/p6/p6g_g18c4_selected_hour_candidate.hpp"
#include "cteas/p6/p6g_original_surfvar_controls.hpp"
#include "cteas/p6e/pgtstb.hpp"
#include "cteas/p6e/surfvar_multistation.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6g {
struct G18C5SelectedHourFields {
    std::chrono::sys_seconds end{};
    std::vector<int> station_ids;
    std::map<std::string,std::vector<float>> real;
    std::map<std::string,std::vector<std::int32_t>> integer;
};
inline std::string g18c5_level_label(const char* prefix,int k) {
    const std::string name=prefix;
    if(name.size()!=5||k<1||k>9)
        throw std::invalid_argument("G18C5 unsupported source P6F level");
    return name+"  "+std::to_string(k);
}
inline G18C5SelectedHourFields g18c5_selected_p6f_fields(
    const MultiHourFrame& frame,
    const G17CSelectedHeatResult& heat,
    const G18C4SelectedCandidate& candidate,
    const std::string& original_metinp,
    bool explicitly_test_only,
    bool allow_one_one_source_audit=false,
    bool allow_asymmetric_source_audit=false) {
    const auto nx=static_cast<std::size_t>(frame.grid.nx);
    const auto ny=static_cast<std::size_t>(frame.grid.ny);
    const auto n=nx*ny;
    if(!explicitly_test_only||!frame.source_controls||
       nx<2||ny<2||nx>400||ny>400||
       frame.input.end!=heat.end||frame.input.end!=candidate.end||
       heat.temperature_k.size()!=n||heat.density_kg_m3.size()!=n||
       heat.shortwave_wm2.size()!=n||heat.sun_sine.size()!=n||
       heat.nearest_surface.size()!=n||
       frame.grid.landuse.size()!=n||
       frame.surface.by_station.size()!=frame.stations.surface.size()||
       ((frame.stations.surface.size()<2||frame.stations.surface.size()>6)&&
        !((allow_one_one_source_audit&&frame.stations.surface.size()==1&&
           frame.stations.upper.size()==1)||
          (allow_asymmetric_source_audit&&frame.stations.surface.size()==1&&
           frame.stations.upper.size()>=2&&frame.stations.upper.size()<=4)))||
       candidate.candidate_memory.zi_m.size()!=n||
       candidate.candidate_memory.ziconv_m.size()!=n||
       candidate.candidate_memory.dptt_k.size()!=n)
        throw std::invalid_argument("G18C5 source native hour/static multi-SS incomplete");
    for(int lu:frame.grid.landuse)
        if(lu>=frame.grid.iwat1&&lu<=frame.grid.iwat2)
            throw std::invalid_argument("G18C5 water PGT/IRH output source not accepted");
    const auto surfvar=parse_original_surfvar_controls(original_metinp);
    // CALMET READCF: original ICLOUD=0/1 => internal MCLOUD=1.
    // The original met.inp contains ICLOUD, not internal MCLOUD.
    const int icloud=g18c1_source_integer(original_metinp,"ICLOUD");
    constexpr int mcloud=1;
    if(surfvar.iavet!=1||surfvar.itprog!=0||
       surfvar.irhprog!=0||surfvar.npsta!=0||
       (icloud!=0&&icloud!=1)||surfvar.irad!=1)
        throw std::invalid_argument("G18C5 unsupported source IAVET/IRAD/MCLOUD/IRH");
    p6e::SurfvarMultistationInput rh;
    rh.nx=nx;rh.ny=ny;rh.dgrid_m=frame.grid.grid_km*1000.f;
    rh.irad=surfvar.irad;rh.numts=surfvar.numts;
    rh.trad_grid=surfvar.trad_km/frame.grid.grid_km;
    p6e::PgtInput pgt;
    pgt.nx=nx;pgt.ny=ny;pgt.mcloud=mcloud;
    pgt.water_first=frame.grid.iwat1;
    pgt.water_last=frame.grid.iwat2;
    pgt.landuse=frame.grid.landuse;
    pgt.nearest=heat.nearest_surface;
    pgt.sinalp=heat.sun_sine;
    pgt.ccgrid.assign(n,0.f);
    pgt.ceilgrid.assign(n,0);
    const auto& fields=candidate.candidate_fields;
    if(fields.u_mps.size()!=9*n||fields.v_mps.size()!=9*n||
       fields.w_face_mps.size()!=10*n||
       fields.temperature_k.size()!=9*n||
       fields.ustar_mps.size()!=n||fields.el_m.size()!=n||
       fields.wstar_mps.size()!=n||fields.qh_wm2.size()!=n)
        throw std::invalid_argument("G18C5 incomplete eight-field G14 candidate");
    pgt.u10.assign(fields.u_mps.begin(),fields.u_mps.begin()+n);
    pgt.v10.assign(fields.v_mps.begin(),fields.v_mps.begin()+n);
    G18C5SelectedHourFields result;
    result.end=frame.input.end;
    for(std::size_t k=0;k<frame.stations.surface.size();++k) {
        const auto& st=frame.stations.surface[k];
        const auto& obs=frame.surface.by_station[k];
        if(st.id<=0||!std::isfinite(st.local_x_m)||
           !std::isfinite(st.local_y_m)||
           !obs.cloud_valid||!obs.ceiling_valid||
           obs.opaque_cloud_tenths<0||obs.opaque_cloud_tenths>10||
           obs.ceiling_hundreds_ft<0||
           (obs.humidity_valid&&(obs.humidity_pct<0||obs.humidity_pct>100)))
            throw std::invalid_argument("G18C5 invalid source surface station cloud/RH");
        result.station_ids.push_back(st.id);
        rh.stations.push_back({st.local_x_m,st.local_y_m,
              obs.temperature_valid?obs.temperature_k:9999.f,
              obs.humidity_valid?obs.humidity_pct:9999});
        pgt.station_cloud.push_back(obs.opaque_cloud_tenths);
        pgt.station_ceil.push_back(obs.ceiling_hundreds_ft);
    }
    const auto humidity=p6e::surfvar_multistation(rh);
    const auto stability=p6e::pgtstb(pgt);
    result.integer["IPGT    "]=std::vector<std::int32_t>(
        stability.begin(),stability.end());
    result.integer["IRH     "]=std::vector<std::int32_t>(
        humidity.rh2d_pct.begin(),humidity.rh2d_pct.end());
    for(int k=1;k<=9;++k) {
        const auto begin=static_cast<std::ptrdiff_t>(k-1)*static_cast<std::ptrdiff_t>(n);
        const auto end=begin+static_cast<std::ptrdiff_t>(n);
        const auto wbegin=static_cast<std::ptrdiff_t>(k)*static_cast<std::ptrdiff_t>(n);
        result.real[g18c5_level_label("U-LEV",k)]=
            std::vector<float>(fields.u_mps.begin()+begin,fields.u_mps.begin()+end);
        result.real[g18c5_level_label("V-LEV",k)]=
            std::vector<float>(fields.v_mps.begin()+begin,fields.v_mps.begin()+end);
        result.real[g18c5_level_label("WFACE",k)]=
            std::vector<float>(fields.w_face_mps.begin()+wbegin,
             fields.w_face_mps.begin()+wbegin+static_cast<std::ptrdiff_t>(n));
        result.real[g18c5_level_label("T-LEV",k)]=
            std::vector<float>(fields.temperature_k.begin()+begin,
                               fields.temperature_k.begin()+end);
    }
    result.real["USTAR   "]=fields.ustar_mps;
    result.real["ZI      "]=candidate.candidate_memory.zi_m;
    result.real["EL      "]=fields.el_m;
    result.real["WSTAR   "]=fields.wstar_mps;
    result.real["TEMPK   "]=heat.temperature_k;
    result.real["RHO     "]=heat.density_kg_m3;
    result.real["QSW     "]=heat.shortwave_wm2;
    // Original IRTYPE=1/LCALGRD=T/NPSTA=0 is 9*4 + 9 = 45 records.
    if(result.real.size()!=43||result.integer.size()!=2)
        throw std::logic_error("G18C5 original P6F 45 field label inventory incomplete");
    for(const auto& pair:result.real) {
        if(pair.first.size()!=8||pair.second.size()!=n)
            throw std::logic_error("G18C5 mis-sized original P6F real record");
        for(float value:pair.second)
            if(!std::isfinite(value)||value==9999.f)
                throw std::invalid_argument("G18C5 original P6F real missing/uncomputed");
    }
    for(const auto& pair:result.integer) {
        if(pair.first.size()!=8||pair.second.size()!=n)
            throw std::logic_error("G18C5 mis-sized original P6F integer record");
        for(int value:pair.second)
            if(value<0||value==9999)
                throw std::invalid_argument("G18C5 original P6F IPGT/IRH incomplete");
    }
    return result;
}
} // namespace cteas::calmet::p6g
