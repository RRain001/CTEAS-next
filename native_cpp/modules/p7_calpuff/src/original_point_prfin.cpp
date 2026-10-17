#include "cteas/puff/original_point_prfin.hpp"
#include "cteas/puff/original_ptlaps.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cteas::puff {
OriginalPointPrfinResult original_point_prfin_metfm1(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const Calmet21Header& grid,const OriginalPointPrfinRequest& in) {
    const auto finite=[](float v){return std::isfinite(v);};
    if(!finite(in.x_cells)||!finite(in.y_cells)||
       !finite(in.stack_height_m)||in.stack_height_m<=0.0F||
       !finite(in.diameter_m)||in.diameter_m<=0.0F||
       !finite(in.exit_velocity_ms)||in.exit_velocity_ms<0.0F||
       !finite(in.stack_temperature_k)||in.stack_temperature_k<=0.0F||
       !finite(in.momentum_flux_factor)||
       !(in.momentum_flux_factor==0.0F||in.momentum_flux_factor==1.0F)||
       !finite(in.calm_threshold_ms)||in.calm_threshold_ms<0.0F||
       !finite(in.max_sample_distance_cells)||
       in.max_sample_distance_cells<=0.0F||
       !finite(in.hour_seconds)||in.hour_seconds<=0.0F||
       in.max_new_puffs<=0||
       !finite(grid.dx_m)||grid.dx_m<=0.0F||
       grid.nx!=met.nx||grid.ny!=met.ny||grid.nz!=met.nz)
        throw std::invalid_argument("POINTS1 PRFIN requires valid original MET and source controls");
    const std::size_t n=static_cast<std::size_t>(met.nx)*
                        static_cast<std::size_t>(met.ny);
    if(met.tempk.size()!=n||met.zi.size()!=n||met.ipgt.size()!=n||
       statics.roughness_m.size()!=n)
        throw std::invalid_argument("POINTS1 PRFIN missing original TEMP2D/ZI/PGT/Z0");
    const auto cell=original_met_cell(
        in.x_cells,in.y_cells,met.nx,met.ny).offset_0based;
    const int pg=met.ipgt.at(cell);
    if(pg<1||pg>6)
        throw std::invalid_argument("POINTS1 invalid original stability class");
    // RLSMET L18345-18362 uses LCALGRD to select the live PTLAPS source.
    // Keep LCALGRD=false (PTG fallback) fail-closed until native PTG(1:2)
    // is available. The selected live METFM1 LCALGRD=true branch uses
    // PTLAPS(HTR,PTGRAD0=.005,DELZ=100) and then REAL4 SQRT(g*PTGRAD/T0).
    float sqrts=0.0F;
    if(pg>=5) {
        if(!in.use_calmet_profile_lapse)
            throw std::invalid_argument(
                "POINTS1 stable LCALGRD=false PTG fallback not yet supported");
        const std::size_t nz=static_cast<std::size_t>(met.nz);
        if(nz<2U || statics.cell_face_m.size()!=nz+1U ||
           met.t.size()!=n*nz)
            throw std::invalid_argument(
                "POINTS1 stable RLSMET needs genuine CALMET TMET/ZFACE");
        std::vector<float> zgpt,tprofile;
        zgpt.reserve(nz);
        tprofile.reserve(nz);
        for(std::size_t k=0;k<nz;++k) {
            zgpt.push_back(0.5F*(statics.cell_face_m[k]+
                                 statics.cell_face_m[k+1U]));
            tprofile.push_back(met.t[k*n+cell]);
        }
        const auto lapse=original_ptlaps_metfm1(
            zgpt,tprofile,in.stack_height_m,0.005F,100.0F);
        sqrts=std::sqrt(
            9.80665F*lapse.gradient_k_per_m/lapse.temperature_base_k);
        if(!finite(sqrts)||sqrts<=0.0F)
            throw std::invalid_argument("POINTS1 stable RLSMET SQRTS invalid");
    }
    const float temp=met.tempk.at(cell);
    const float pbl=met.zi.at(cell);
    if(!finite(temp)||temp<=0.0F||!finite(pbl))
        throw std::invalid_argument("POINTS1 invalid genuine TEMP2D or DPBL");
    const auto stack=original_release_wind_metfm1(
        met,statics,{in.x_cells,in.y_cells,in.stack_height_m,in.calm_threshold_ms});
    // POINTS1 L15509-15539: source-ordered float32 stack temperature excess,
    // buoyancy, momentum and stack-tip downwash. TEMP2D, not T3D-stack.
    const float excess=std::max(0.0F,in.stack_temperature_k-temp);
    const auto flux=stack_fluxes({
        in.diameter_m,in.exit_velocity_ms,in.stack_temperature_k,
        temp,excess,in.momentum_flux_factor});
    const float tip=static_cast<float>(stack_tip_downwash({
        in.stack_height_m,in.diameter_m,flux.momentum_m4s2,
        in.exit_velocity_ms,stack.wind_speed_ms}));
    const auto final=final_plume_rise({
        in.exit_velocity_ms,in.diameter_m,flux.momentum_m4s2,
        flux.buoyancy_m4s3,stack.wind_speed_ms,pg,sqrts});
    // Original POINTS1 L15562-15597: PRFPP is called only with
    // MPARTL=1, ISTAB<=4 and FB>0. Stable classes E/F do not enter it:
    // FMIX=1, HMAX=DPBL, RISE_B=PRFIN output.
    float final_rise=static_cast<float>(final.z_final_m);
    float fmix=1.0F;
    float hmax=pbl;
    FinalRise adjusted=final;
    if(pg<=4 && flux.buoyancy_m4s3>0.0) {
        // POINTS1 L15562-15588: PRFPP is unconditional for A-D with
        // positive FB, including stack above the diagnosed mixed layer.
        // PTLAPS is sourced at HTINV=max(DPBL,HTSTAK), thickness 30m.
        // A-D cases needing the inversion gradient fail closed unless the
        // selected live METFM1/LCALGRD temperature profile is provided.
        const float zi=pbl-in.stack_height_m;
        const float transition=0.67F*zi;
        float ptginv=0.0F;
        float dptinv=0.0F;
        if(zi<=0.0F || final_rise>transition) {
            if(!in.use_calmet_profile_lapse)
                throw std::invalid_argument(
                    "POINTS1 PRFPP penetration requires original LCALGRD PTLAPS");
            const std::size_t nz=static_cast<std::size_t>(met.nz);
            if(nz<2U || statics.cell_face_m.size()!=nz+1U ||
               met.t.size()!=n*nz)
                throw std::invalid_argument(
                    "POINTS1 PRFPP requires genuine CALMET TMET/ZFACE");
            std::vector<float> zgpt,tprofile;
            zgpt.reserve(nz);
            tprofile.reserve(nz);
            for(std::size_t k=0;k<nz;++k) {
                zgpt.push_back(0.5F*(statics.cell_face_m[k]+
                                     statics.cell_face_m[k+1U]));
                tprofile.push_back(met.t[k*n+cell]);
            }
            const auto inversion=original_ptlaps_metfm1(
                zgpt,tprofile,std::max(pbl,in.stack_height_m),0.005F,30.0F);
            ptginv=inversion.gradient_k_per_m;
            // Original POINTS1 L15581-15585: no observed DPTINVO in the
            // selected METFM1 CALMET.DAT request; compute PTGINV*DZINV.
            // Independent original H24 hourly parity remains the authority.
            dptinv=ptginv*30.0F;
        }
        const auto partial=partial_penetration_rise({
            final.z_final_m,flux.buoyancy_m4s3,stack.wind_speed_ms,
            in.stack_height_m,pbl,temp,ptginv,dptinv});
        final_rise=static_cast<float>(partial.final_rise_m);
        fmix=static_cast<float>(partial.mass_fraction_mixed);
        hmax=static_cast<float>(partial.max_height_m);
        // POINTS1 L15589-15590: both final component heights cannot
        // exceed the revised PRFPP rise used by GRISE/RISEWIND.
        if(adjusted.z_final_buoyancy_m>final_rise)
            adjusted.z_final_buoyancy_m=final_rise;
        if(adjusted.z_final_momentum_m>final_rise)
            adjusted.z_final_momentum_m=final_rise;
    }
    // POINTS1 L15603 evaluates HTSTAK-TIPDW+RISE_B in this order.
    const float heff=in.stack_height_m-tip+final_rise;
    // Original CALPUFF POINTS1 L15603 assigns HTSTAK-TIPDW+RISE_B
    // WITHOUT requiring HEFF>=HTSTAK: stack-tip downwash can lower
    // the effective release height below physical stack height.
    // Reject only a nonphysical nonpositive/nonfinite height here.
    if(!finite(heff)||heff<=0.0F)
        throw std::invalid_argument(
            "POINTS1 PRFIN effective height nonpositive/nonfinite: HEFF="+
            std::to_string(heff)+" TIPDW="+std::to_string(tip)+
            " RISE_B="+std::to_string(final_rise));
    const auto elevated=original_release_wind_metfm1(
        met,statics,{in.x_cells,in.y_cells,heff,in.calm_threshold_ms});
    const float wsnew=std::max(
        stack.wind_speed_ms,elevated.wind_speed_ms);
    const float xtmp1=in.hour_seconds/
        (grid.dx_m*in.max_sample_distance_cells);
    const auto cadence=release_cadence({
        wsnew,xtmp1,in.max_new_puffs,in.hour_seconds});
    OriginalPointPrfinResult result;
    result.ambient_temperature_k=temp;
    result.mixing_height_m=pbl;
    result.stability_class=pg;
    result.sqrt_stability_s=sqrts;
    result.stack_wind_ms=stack.wind_speed_ms;
    result.effective_wind_ms=elevated.wind_speed_ms;
    result.release_wind_ms=wsnew;
    result.buoyancy_flux=static_cast<float>(flux.buoyancy_m4s3);
    result.momentum_flux=static_cast<float>(flux.momentum_m4s2);
    result.stack_tip_downwash_m=tip;
    result.x_final_m=static_cast<float>(final.x_final_m);
    result.final_rise_m=final_rise;
    // CALPUFF POINTS1 15599-15600: BIDSQ_B=(RISE_B/3.5)**2, REAL*4.
    const float bid_ratio=result.final_rise_m/3.5F;
    result.buoyancy_variance_m2=bid_ratio*bid_ratio;
    result.effective_height_m=heff;
    result.mixed_fraction=fmix;
    result.max_layer_height_m=hmax;
    result.brigg=adjusted;
    result.release=cadence;
    return result;
}
} // namespace cteas::puff
