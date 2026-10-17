#pragma once

#include <string>

namespace cteas::puff {

// P7N: CALPUFF 7.2.1 plume rise, transcribed from the unmodified vendor source
// and cross-checked against it by CTest:
//   STKTIP calpuff.for L46904-46947  (stack-tip downwash adjustment)
//   PRB    calpuff.for L46949-46999  (transitional buoyant rise)
//   PRM    calpuff.for L47001-47079  (transitional momentum rise)
//   PRFIN  calpuff.for L47081-47249  (distance to, and height of, final rise)
//   GRISE  calpuff.for L47251-47620  (gradual-rise dispatch and plume height)
//   PRFPP  calpuff.for L48041-48150  (partial penetration of an elevated inversion)
//   POINTS1 flux block L15527-15535  (buoyancy/momentum flux, inline in POINTS1)
//
// This is the rise path the locked Hefei 2022 deck selects: MTRANS=1 (gradual
// rise), MTIP=1 (stack-tip downwash), MRISE=1 (Briggs rise), MPARTL=1 (partial
// penetration), MSHEAR=0 (no wind shear), MBDW=1 with no building (IDW0=0).
//
// Not reconstructed, and refused by the callers of this module: PRSHEAR/PRFINSH
// (wind shear), PRSS and the PRIME tabulated rise (building downwash), PRTAB/
// PRBL/INTERTAB (tabulated, area and line source rise), NUMRISE (numerical
// rise), PTLAPS (met-model inversion gradient) and the FOG option.
//
// The original keeps its rise state in REAL*4, so everything here is REAL*4
// internally and converts to double only in the reported results, which is what
// makes tight original-source parity possible.

using RiseReal = float;

// STKTIP: plume height DECREASE from stack-tip downwash (m). The adjustment is
// positive and is subtracted from the stack height by the caller.
struct StackTipInputs {
    double stack_height_m = 0.0;        // HS
    double diameter_m = 0.0;            // DIAM
    double momentum_flux = 0.0;         // FLUXM (m**4/s**2)
    double exit_velocity_ms = 0.0;      // VEXIT
    double stack_wind_speed_ms = 0.0;   // WSSTK
};

[[nodiscard]] double stack_tip_downwash(const StackTipInputs& inputs);

// The POINTS1 flux block: buoyancy flux, momentum flux and the FMFAC test.
struct StackFluxInputs {
    double diameter_m = 0.0;              // DIAM(i)
    double exit_velocity_ms = 0.0;        // EXITW(i)
    double stack_temperature_k = 0.0;     // TSTAK(i)
    double ambient_temperature_k = 0.0;   // TEMP
    double temperature_excess_k = 0.0;    // DTEMP (>= 0, the vendor clips it)
    double momentum_flux_factor = 1.0;    // FMFPT1(i); < 0.5 zeroes the momentum flux
};

struct StackFluxes {
    double buoyancy_m4s3 = 0.0;   // FLUXB
    double momentum_m4s2 = 0.0;   // FLUXM
};

[[nodiscard]] StackFluxes stack_fluxes(const StackFluxInputs& inputs);

// PRFIN: distance to final rise and height of final plume rise.
struct FinalRiseInputs {
    double exit_velocity_ms = 0.0;      // VEXIT
    double diameter_m = 0.0;            // DIAM
    double momentum_flux = 0.0;         // FM
    double buoyancy_flux = 0.0;         // FB
    double stack_wind_speed_ms = 0.0;   // WSSTK
    int stability_class = 0;            // ISTAB (1=A .. 6=F)
    double sqrt_stability_s = 0.0;      // SQRTS = sqrt(g*(dtheta/dz)/tair)
};

struct FinalRise {
    double x_final_momentum_m = 0.0;   // XFINM
    double x_final_buoyancy_m = 0.0;   // XFINB
    double x_final_m = 0.0;            // XFIN
    double z_final_momentum_m = 0.0;   // ZFINM
    double z_final_buoyancy_m = 0.0;   // ZFINB
    double z_final_m = 0.0;            // ZFIN
};

[[nodiscard]] FinalRise final_plume_rise(const FinalRiseInputs& inputs);

// PRM: transitional momentum plume rise (m) at downwind distance X.
struct MomentumRiseInputs {
    double diameter_m = 0.0;            // DIAM
    double exit_velocity_ms = 0.0;      // VEXIT
    double momentum_flux = 0.0;         // FM
    double stack_wind_speed_ms = 0.0;   // WSSTK
    int stability_class = 0;            // ISTAB
    double sqrt_stability_s = 0.0;      // SQRTS
    double x_m = 0.0;                   // X
    double x_final_momentum_m = 0.0;    // XFINM
    double z_final_momentum_m = 0.0;    // ZFINM
};

[[nodiscard]] double transitional_momentum_rise(const MomentumRiseInputs& inputs);

// PRB: transitional buoyant plume rise (m) at downwind distance X.
struct BuoyantRiseInputs {
    double buoyancy_flux = 0.0;         // FB
    double stack_wind_speed_ms = 0.0;   // WSSTK
    double x_m = 0.0;                   // X
    double x_final_buoyancy_m = 0.0;    // XFINB
    double z_final_buoyancy_m = 0.0;    // ZFINB
};

[[nodiscard]] double transitional_buoyant_rise(const BuoyantRiseInputs& inputs);

// PRFPP: revise the final rise for partial penetration of an elevated inversion.
struct PartialPenetrationInputs {
    double final_rise_m = 0.0;                 // ZFIN
    double buoyancy_flux = 0.0;                // FB
    double stack_wind_speed_ms = 0.0;          // WSSTK
    double stack_height_m = 0.0;               // HS
    double mixing_height_m = 0.0;              // HMIX
    double ambient_temperature_k = 0.0;        // TA
    double inversion_gradient_k_per_m = 0.0;   // PTGINV
    double inversion_jump_k = 0.0;             // TI
};

struct PartialPenetration {
    double final_rise_m = 0.0;        // ZFIN (revised)
    double mass_fraction_mixed = 0.0; // FMIX
    double max_height_m = 0.0;        // HMAX
};

[[nodiscard]] PartialPenetration partial_penetration_rise(
    const PartialPenetrationInputs& inputs);

// GRISE: the /CURRENT/, /PUFF/ and /FLAGS/ state the vendor routine reads.
struct PlumeRiseState {
    int source_type = 1;                  // ISTYPE (1/2 = point, 4 = area, 5/6 = line, 10/11 = flare)
    int downwash_code = 0;                // IDW0(IPNUM): 0 none, 1 HS, 2 SS, 3 PRIME primary, 4 PRIME cavity
    int met_period = 1;                   // IMET (1 .. met periods + 1)
    int rise_method = 1;                  // MRISE (1 = Briggs, 2 = numerical)
    int shear_flag = 0;                   // MSHEAR
    double x_m = 0.0;                     // X
    // ZFINAL(IPNUM) is the stored plume HEIGHT (HT0 + rise - STIPDW) that the
    // vendor returns directly for the no-rise/cavity method; ZFRISE is the final
    // RISE without streamline depression and only feeds RISEFAC.
    double final_rise_m = 0.0;            // ZFINAL(IPNUM), a height
    double full_final_rise_m = 0.0;       // ZFRISE, a rise
    double stack_height_m = 0.0;          // HT0(IPNUM)
    double diameter_m = 0.0;              // DIAM0(IPNUM)
    double exit_velocity_ms = 0.0;        // EXITW0(IPNUM)
    double stack_wind_speed_ms = 0.0;     // WS0(IPNUM)
    int stability_class = 0;              // ISTAB0(IPNUM)
    double sqrt_stability_s = 0.0;        // SQRTS0(IPNUM)
    double momentum_flux = 0.0;           // FM(IPNUM)
    double buoyancy_flux = 0.0;           // FB(IPNUM)
    double x_final_momentum_m = 0.0;      // XMFIN(IPNUM)
    double z_final_momentum_m = 0.0;      // ZMFIN(IPNUM)
    double x_final_buoyancy_m = 0.0;      // XBFIN(IPNUM)
    double z_final_buoyancy_m = 0.0;      // ZBFIN(IPNUM)
    double stack_tip_downwash_m = 0.0;    // STIPDW(IPNUM)
};

struct PlumeRiseResult {
    double height_m = 0.0;        // HTGRISE
    double rise_fraction = 0.0;   // RISEFAC
};

// GRISE equivalent for the reconstructed branches (point sources with Briggs
// rise). Fails closed when the vendor would use the tabulated/numerical rise,
// the shear or building-downwash corrections, or another source type.
[[nodiscard]] PlumeRiseResult gradual_plume_height(const PlumeRiseState& state);

} // namespace cteas::puff
