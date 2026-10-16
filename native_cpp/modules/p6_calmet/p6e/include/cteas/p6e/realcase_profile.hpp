#pragma once
// Real-case CALMET micrometeorology option profile.
//
// The reference cold-start case deck
// project/cases/smoke5d_coldstart_20260701/run/met/met.inp selects
//   IRTYPE=1  IMIXH=1  THRESHL=0.0  IZICRLX=1  ISURFT=-1  IUPT=-1
//   ITPROG=0  NOOBS=0  NOWSTA=0  NM3D=0  LCALGRD=T
// over 50x50 @1 km with NZ=9. P6E has source-validated semantics for
// exactly that envelope (and for the IMIXH=2 side branch, which is NOT the
// real-case path). This gate makes leaving the validated envelope an
// explicit error instead of a silent semantic downgrade.
//
// Key consequence of the real deck: with THRESHL=0 the net buoyancy flux is
// WT-WTO = WT, so the IZICRLX=1 relaxation branch
//   ZIC = ZICEQ + (HTOLD-ZICEQ)*exp(-NSECDT/TZICRLX)
// is unreachable over land (it needs 0 < WT < WTO with WTO>0). The real
// deck therefore runs IZICRLX=1 without any relaxation actually applying,
// which is asserted numerically by tests/realcase_options_tests.cpp and by
// reference/compare_original_mixht_observed_mc.py against unmodified source.
#include <cmath>
#include <stdexcept>
namespace cteas::p6e {
enum class ConvectiveScheme { maul_carson, batchvarova_gryning };
enum class LapseSource { upper_air_soundings };
struct RealCaseMicrometProfile {
    int irtype=1;
    int imixh=1;   // magnitude 1 = Maul-Carson (real case), 2 = BG side branch
    int izicrlx=1;
    int isurft=-1;
    int iupt=-1;
    int itprog=0;
    int noobs=0;
    int nowsta=0;
    int nm3d=0;
    bool lcalgrd=true;
    float threshl_wm2perm=0.f; // land threshold buoyancy flux (W/m2/m)
    float threshw_wm2perm=0.f; // water threshold buoyancy flux (W/m2/m)
};
struct RealCaseProfileDecision {
    ConvectiveScheme scheme;
    LapseSource lapse_source;
    bool two_dimensional_surface_temperature;
    bool per_cell_lapse_station;
    // True only when a positive land threshold can drive the IZICRLX
    // relaxation branch; THRESHL=0 makes IZICRLX inert over land.
    bool land_relaxation_reachable;
};
inline RealCaseProfileDecision
validate_realcase_profile(const RealCaseMicrometProfile& p) {
    if(p.irtype!=1)
        throw std::invalid_argument("IRTYPE!=1 does not request micrometeorological fields");
    if(p.itprog!=0)
        throw std::invalid_argument("ITPROG!=0 selects prognostic temperature, not source-validated in P6E");
    if(p.nm3d!=0)
        throw std::invalid_argument("NM3D!=0 selects the MM5 ILAPSE=1 MIXDT2 lapse path, not source-validated in P6E");
    if(p.noobs!=0)
        throw std::invalid_argument("NOOBS!=0 selects prognostic mixing-height input, not source-validated in P6E");
    if(p.nowsta!=0)
        throw std::invalid_argument("NOWSTA!=0 selects over-water surface stations, not source-validated in P6E");
    if(p.isurft!=-1)
        throw std::invalid_argument("ISURFT!=-1 is not the validated 2-D spatially varying surface temperature contract");
    const int magnitude=p.imixh<0?-p.imixh:p.imixh;
    if(magnitude!=1&&magnitude!=2)
        throw std::invalid_argument("IMIXH magnitude must be 1 or 2");
    if(p.izicrlx!=0&&p.izicrlx!=1)
        throw std::invalid_argument("IZICRLX must be 0 or 1");
    if(!std::isfinite(p.threshl_wm2perm)||p.threshl_wm2perm<0.f||
       !std::isfinite(p.threshw_wm2perm)||p.threshw_wm2perm<0.f)
        throw std::invalid_argument("threshold buoyancy fluxes must be finite and non-negative");
    return {magnitude==1?ConvectiveScheme::maul_carson
                        :ConvectiveScheme::batchvarova_gryning,
            LapseSource::upper_air_soundings,
            true,
            p.iupt<=0,
            p.izicrlx!=0&&p.threshl_wm2perm>0.f};
}
} // namespace cteas::p6e
