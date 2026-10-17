#pragma once
// CALMET 6.5.0 ELUSTR2 -> MIXHTST (L6881-L6882, MIXHTST L107xx).
// Source-order station-cell coupling using the existing source-parity-tested
// P6E MIXHT/MIXHMC kernel. This API requires actual *previous COMP grid*
// ZI, ZICONV and /TJMP/ DPTT, NOT previous station MIXHTST output, NOT
// previous-hour AVEMIX ZI alone and NOT an original reference oracle.
//
// The returned DPTT is the in-place /TJMP/ mutation that must be passed
// onward to the current-hour COMP MIXHT grid stage. Keeping station
// and grid recurrence explicit prevents the known persistent P6D/P6E drift.
#include "cteas/p6e/mixht_observed_mc.hpp"
#include <cmath>
#include <stdexcept>

namespace cteas::calmet::p6 {
struct StationPreviousCompState {
    float zi_m=0.f,ziconv_m=0.f,dptt_k=0.f;
};
struct StationMixhtstInput {
    StationPreviousCompState previous;
    cteas::p6e::MixdtSounding older_sounding;
    // ORIGINAL MIXHTST chooses the chronologically older observed sounding
    // from the physical AA/BB buffers. The caller owns that buffer selection.
    float qh_wm2=0.f,ustar_mps=0.f,el_m=0.f,rho_kg_m3=0.f;
    float fcori_s=0.f,cmech=0.f;
    float zimin_m=50.f,zimax_m=3000.f,constn=2400.f;
    float dptmin_kperm=0.001f,dzzi_m=200.f,threshl=0.f;
    float onedte_s=4140.f,twodte_s=1080.f,tzicrlx_s=800.f;
    int timestep_s=3600,imixh=1,izicrlx=1;
    int landuse=20,water_first=50,water_last=55;
};
struct StationMixhtstResult {
    float zii_to_similt_m=0.f,ziconv_after_m=0.f,dptt_for_comp_k=0.f;
};
inline StationMixhtstResult station_mixhtst(const StationMixhtstInput& s) {
    if (s.landuse>=s.water_first&&s.landuse<=s.water_last)
        throw std::invalid_argument("MIXHTST station-water route requires WATER2");
    if (!(s.fcori_s>0.f&&s.cmech>0.f&&s.rho_kg_m3>0.f&&
          s.ustar_mps>0.f&&s.zimin_m>0.f&&
          std::isfinite(s.el_m)&&std::isfinite(s.previous.zi_m)&&
          s.previous.ziconv_m>=0.f&&
          std::isfinite(s.previous.dptt_k)))
        throw std::invalid_argument("MIXHTST station has invalid previous COMP state");
    cteas::p6e::MixhtObservedMcInput grid;
    grid.nx=1;grid.ny=1;
    grid.water_first=s.water_first;grid.water_last=s.water_last;
    grid.iupt=-1;grid.imixh=s.imixh;
    grid.izicrlx=s.izicrlx;grid.timestep_s=s.timestep_s;
    grid.constn=s.constn;grid.zimin=s.zimin_m;grid.zimax=s.zimax_m;
    grid.threshl=s.threshl;grid.dptmin=s.dptmin_kperm;grid.dzzi=s.dzzi_m;
    grid.onedte=s.onedte_s;grid.twodte=s.twodte_s;grid.tzicrlx=s.tzicrlx_s;
    // Only one upper-air station; physical AA holds the most recent past
    // sounding here. The other buffer is unused on the MIXHTST path.
    grid.sounding[0]={s.older_sounding};
    grid.sounding[1]={s.older_sounding};
    grid.justa={1};grid.nearu={1};
    grid.landuse={s.landuse};
    grid.qh={s.qh_wm2};grid.ustar={s.ustar_mps};
    grid.el={s.el_m};grid.rho={s.rho_kg_m3};
    grid.cmech={s.cmech};grid.fcori={s.fcori_s};
    grid.initial_zi={s.previous.zi_m};
    grid.initial_ziconv={s.previous.ziconv_m};
    grid.initial_dptt={s.previous.dptt_k};
    grid.dptt_refresh=0; // refresh belongs BEFORE grid COMP call, not here
    const auto r=cteas::p6e::mixht_observed_mc(grid);
    return {r.zi[0],r.ziconv[0],r.dptt[0]};
}
} // namespace cteas::calmet::p6
