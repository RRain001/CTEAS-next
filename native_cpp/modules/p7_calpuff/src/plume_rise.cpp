#include "cteas/puff/plume_rise.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = RiseReal;

// Vendor constants of the rise routines.
constexpr R kZero = 0.0F;
constexpr R kOne = 1.0F;
constexpr R kTwo = 2.0F;
constexpr R kThree = 3.0F;
constexpr R kFour = 4.0F;
constexpr R kHalf = 0.5F;
constexpr R kThird = 0.333333F;          // the vendor literal 0.333333
constexpr R kThirdLong = 0.3333333F;     // the vendor literal 0.3333333 (PRFPP)
constexpr R kGravity = 9.80665F;         // PRFPP data g/9.80665/
constexpr R kMinStackWind = 1.0F;        // PRFIN/PRFPP data wsstk0/1.0/
constexpr R kBuoyancyFluxFactor = 2.4516625F;  // g/4 (POINTS1 flux block)
constexpr R kMomentumFluxFactor = 0.25F;       // POINTS1 flux block
constexpr R kPiByTwo = 1.57080F;               // PRFIN stable momentum XFINM constant

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7N plume rise: " + message);
}

void require_finite(double value, const std::string& what) {
    require_true(std::isfinite(value), what + " must be finite");
}

R to_real(double value, const char* what) {
    require_finite(value, what);
    return static_cast<R>(value);
}

} // namespace

double stack_tip_downwash(const StackTipInputs& inputs) {
    // STKTIP (calpuff.for L46904-46947), REAL*4.
    const R stack_height = to_real(inputs.stack_height_m, "stack height");
    const R diameter = to_real(inputs.diameter_m, "stack diameter");
    const R momentum_flux = to_real(inputs.momentum_flux, "momentum flux");
    const R exit_velocity = to_real(inputs.exit_velocity_ms, "exit velocity");
    const R stack_wind = to_real(inputs.stack_wind_speed_ms, "stack-height wind speed");
    require_true(stack_height >= kZero, "stack height must not be negative");
    require_true(diameter >= kZero, "stack diameter must not be negative");

    if (momentum_flux == kZero) return static_cast<double>(std::min(stack_height, kThree * diameter));
    if (exit_velocity < (1.5F * stack_wind)) {
        const R velocity_by_wind = exit_velocity / stack_wind;
        return static_cast<double>(
            std::min(stack_height, kTwo * diameter * (1.5F - velocity_by_wind)));
    }
    return 0.0;
}

StackFluxes stack_fluxes(const StackFluxInputs& inputs) {
    // POINTS1 flux block (calpuff.for L15527-15535), REAL*4.
    const R diameter = to_real(inputs.diameter_m, "stack diameter");
    const R exit_velocity = to_real(inputs.exit_velocity_ms, "exit velocity");
    const R stack_temperature = to_real(inputs.stack_temperature_k, "stack temperature");
    const R ambient_temperature = to_real(inputs.ambient_temperature_k, "ambient temperature");
    const R temperature_excess = to_real(inputs.temperature_excess_k, "temperature excess");
    const R momentum_factor = to_real(inputs.momentum_flux_factor, "momentum flux factor");
    require_true(stack_temperature != kZero, "stack temperature must not be zero");

    StackFluxes fluxes;
    // Association is kept identical to the vendor statements so the single
    // precision rounding matches: (2.4516625*d**2*e/tstak)*dtemp and
    // 0.25*(e*d)**2*temp/tstak.
    fluxes.buoyancy_m4s3 = static_cast<double>(
        ((kBuoyancyFluxFactor * (diameter * diameter) * exit_velocity) / stack_temperature) *
        temperature_excess);
    fluxes.momentum_m4s2 = static_cast<double>(
        (kMomentumFluxFactor * ((exit_velocity * diameter) * (exit_velocity * diameter)) *
         ambient_temperature) /
        stack_temperature);
    if (momentum_factor < kHalf) fluxes.momentum_m4s2 = 0.0;
    return fluxes;
}

FinalRise final_plume_rise(const FinalRiseInputs& inputs) {
    // PRFIN (calpuff.for L47081-47249), REAL*4.
    const R exit_velocity = to_real(inputs.exit_velocity_ms, "exit velocity");
    const R diameter = to_real(inputs.diameter_m, "stack diameter");
    const R momentum_flux = to_real(inputs.momentum_flux, "momentum flux");
    const R buoyancy_flux = to_real(inputs.buoyancy_flux, "buoyancy flux");
    const R stack_wind = to_real(inputs.stack_wind_speed_ms, "stack-height wind speed");
    const R sqrt_stability = to_real(inputs.sqrt_stability_s, "sqrt stability parameter");
    require_true(inputs.stability_class >= 1 && inputs.stability_class <= 6,
                 "stability class must be 1-6");
    const bool neutral_or_unstable = inputs.stability_class <= 4;

    R x_final_momentum = kZero;
    R x_final_buoyancy = kZero;
    R z_final_momentum = kZero;
    R z_final_buoyancy = kZero;

    if (stack_wind >= kMinStackWind) {
        // Non-calm conditions.
        if (neutral_or_unstable) {
            if (buoyancy_flux >= 55.0F) {
                x_final_buoyancy = 119.0F * std::pow(buoyancy_flux, 0.4F);
                z_final_buoyancy = 38.71F * std::pow(buoyancy_flux, 0.6F) / stack_wind;
            } else if (buoyancy_flux > kZero) {
                x_final_buoyancy = 49.0F * std::pow(buoyancy_flux, 0.625F);
                z_final_buoyancy = 21.425F * std::pow(buoyancy_flux, 0.75F) / stack_wind;
            } else {
                const R exit_velocity2 = std::max(exit_velocity, 1.0e-10F);
                x_final_buoyancy = kFour * diameter * (exit_velocity2 + kThree * stack_wind) *
                                   (exit_velocity2 + kThree * stack_wind) /
                                   (exit_velocity2 * stack_wind);
                const R buoyancy_flux2 = std::max(buoyancy_flux, 1.0e-10F);
                z_final_buoyancy = 21.425F * std::pow(buoyancy_flux2, 0.75F) / stack_wind;
            }
        } else {
            x_final_buoyancy = 2.0715F * stack_wind / sqrt_stability;
            const R s = sqrt_stability * sqrt_stability;
            const R buoyancy_flux2 = std::max(buoyancy_flux, 1.0e-10F);
            z_final_buoyancy = 2.6F * std::pow(buoyancy_flux2 / (stack_wind * s), kThird);
            const R z_final_vertical =
                kFour * std::pow(buoyancy_flux2, 0.25F) / std::pow(s, 0.375F);
            z_final_buoyancy = std::min(z_final_buoyancy, z_final_vertical);
        }
        if (neutral_or_unstable) {
            const R exit_velocity2 = std::max(exit_velocity, 1.0e-10F);
            x_final_momentum = kFour * diameter * (exit_velocity2 + kThree * stack_wind) *
                               (exit_velocity2 + kThree * stack_wind) /
                               (exit_velocity2 * stack_wind);
            z_final_momentum = kThree * diameter * exit_velocity / stack_wind;
        } else {
            x_final_momentum = kPiByTwo * stack_wind / sqrt_stability;
            const R momentum_flux2 = std::max(momentum_flux, 1.0e-10F);
            z_final_momentum =
                1.5F * std::pow(momentum_flux2 / (stack_wind * sqrt_stability), kThird);
            z_final_momentum =
                std::min(z_final_momentum, kThree * diameter * exit_velocity / stack_wind);
        }
        if (momentum_flux == kZero) {
            x_final_momentum = kZero;
            z_final_momentum = kZero;
        }
    } else {
        // Calm conditions.
        if (neutral_or_unstable) {
            x_final_buoyancy = kZero;
            if (buoyancy_flux >= 55.0F) {
                z_final_buoyancy = 38.71F * std::pow(buoyancy_flux, 0.6F) / kMinStackWind;
            } else {
                const R buoyancy_flux2 = std::max(buoyancy_flux, 1.0e-10F);
                z_final_buoyancy = 21.425F * std::pow(buoyancy_flux2, 0.75F) / kMinStackWind;
            }
        } else {
            x_final_buoyancy = kZero;
            const R s = sqrt_stability * sqrt_stability;
            const R buoyancy_flux2 = std::max(buoyancy_flux, 1.0e-10F);
            z_final_buoyancy = kFour * std::pow(buoyancy_flux2, 0.25F) / std::pow(s, 0.375F);
        }
        if (neutral_or_unstable) {
            x_final_momentum = kZero;
            z_final_momentum = kThree * diameter * exit_velocity / kMinStackWind;
        } else {
            x_final_momentum = kZero;
            const R momentum_flux2 = std::max(momentum_flux, 1.0e-10F);
            z_final_momentum =
                1.5F * std::pow(momentum_flux2 / (kMinStackWind * sqrt_stability), kThird);
            z_final_momentum =
                std::min(z_final_momentum, kThree * diameter * exit_velocity / kMinStackWind);
        }
        if (momentum_flux == kZero) {
            x_final_momentum = kZero;
            z_final_momentum = kZero;
        }
    }

    FinalRise result;
    result.x_final_momentum_m = static_cast<double>(x_final_momentum);
    result.x_final_buoyancy_m = static_cast<double>(x_final_buoyancy);
    result.z_final_momentum_m = static_cast<double>(z_final_momentum);
    result.z_final_buoyancy_m = static_cast<double>(z_final_buoyancy);
    result.x_final_m = static_cast<double>(std::max(x_final_buoyancy, x_final_momentum));
    result.z_final_m = static_cast<double>(std::max(z_final_buoyancy, z_final_momentum));
    return result;
}

double transitional_momentum_rise(const MomentumRiseInputs& inputs) {
    // PRM (calpuff.for L47001-47079), REAL*4.
    const R diameter = to_real(inputs.diameter_m, "stack diameter");
    const R exit_velocity = to_real(inputs.exit_velocity_ms, "exit velocity");
    const R momentum_flux = to_real(inputs.momentum_flux, "momentum flux");
    const R stack_wind = to_real(inputs.stack_wind_speed_ms, "stack-height wind speed");
    const R sqrt_stability = to_real(inputs.sqrt_stability_s, "sqrt stability parameter");
    const R x = to_real(inputs.x_m, "downwind distance");
    const R x_final_momentum = to_real(inputs.x_final_momentum_m, "XFINM");
    const R z_final_momentum = to_real(inputs.z_final_momentum_m, "ZFINM");
    require_true(inputs.stability_class >= 1 && inputs.stability_class <= 6,
                 "stability class must be 1-6");

    if (exit_velocity <= kZero || momentum_flux <= kZero || x <= kZero) return 0.0;
    if (!(x < x_final_momentum) || !(stack_wind > kZero)) return static_cast<double>(z_final_momentum);

    const R beta_j = kThird + (stack_wind / exit_velocity);
    const R z_final_neutral_unstable = kThree * diameter * exit_velocity / stack_wind;
    R rise = kZero;
    if (inputs.stability_class <= 4) {
        rise = std::pow(kThree * momentum_flux * x /
                            (beta_j * beta_j * stack_wind * stack_wind),
                        kThird);
        rise = std::min(rise, z_final_neutral_unstable);
    } else {
        rise = std::pow(kThree * momentum_flux * std::sin(sqrt_stability * x / stack_wind) /
                            (beta_j * beta_j * stack_wind * sqrt_stability),
                        kThird);
        rise = std::min(rise, z_final_neutral_unstable);
    }
    return static_cast<double>(rise);
}

double transitional_buoyant_rise(const BuoyantRiseInputs& inputs) {
    // PRB (calpuff.for L46949-46999), REAL*4.
    const R buoyancy_flux = to_real(inputs.buoyancy_flux, "buoyancy flux");
    const R stack_wind = to_real(inputs.stack_wind_speed_ms, "stack-height wind speed");
    const R x = to_real(inputs.x_m, "downwind distance");
    const R x_final_buoyancy = to_real(inputs.x_final_buoyancy_m, "XFINB");
    const R z_final_buoyancy = to_real(inputs.z_final_buoyancy_m, "ZFINB");

    if (x <= kZero || buoyancy_flux <= kZero) return 0.0;
    if (x < x_final_buoyancy && stack_wind > kZero) {
        R rise = (1.6F * std::pow(buoyancy_flux * x * x, kThird)) / stack_wind;
        rise = std::min(rise, z_final_buoyancy);
        return static_cast<double>(rise);
    }
    return static_cast<double>(z_final_buoyancy);
}

PartialPenetration partial_penetration_rise(const PartialPenetrationInputs& inputs) {
    // PRFPP (calpuff.for L48041-48150), REAL*4.
    const R z_fin_in = to_real(inputs.final_rise_m, "final rise");
    const R buoyancy_flux = to_real(inputs.buoyancy_flux, "buoyancy flux");
    const R stack_wind_in = to_real(inputs.stack_wind_speed_ms, "stack-height wind speed");
    const R stack_height = to_real(inputs.stack_height_m, "stack height");
    const R mixing_height = to_real(inputs.mixing_height_m, "mixing height");
    const R ambient_temperature = to_real(inputs.ambient_temperature_k, "ambient temperature");
    const R inversion_gradient = to_real(inputs.inversion_gradient_k_per_m, "inversion gradient");
    const R inversion_jump = to_real(inputs.inversion_jump_k, "inversion temperature jump");
    require_true(ambient_temperature > kZero, "ambient temperature must be positive");

    R u = stack_wind_in;
    if (u < kMinStackWind) u = kMinStackWind;

    const R zi = mixing_height - stack_height;
    const R rise0 = 0.67F * zi;

    R rise1 = kZero;
    R rise2 = kZero;
    R fmix = kZero;
    if (zi <= kZero) {
        fmix = kZero;
        const R s_aloft = kGravity * inversion_gradient / ambient_temperature;
        if (s_aloft > kZero) {
            rise1 = 2.6F * std::pow(buoyancy_flux / (u * s_aloft), kThirdLong);
        } else {
            rise1 = z_fin_in;
        }
        rise2 = rise1;
    } else if (z_fin_in <= rise0) {
        rise1 = z_fin_in;
        rise2 = zi;
        fmix = kOne;
    } else {
        const R penetration_inverse =
            u * (kGravity * inversion_jump / ambient_temperature) * zi * zi / buoyancy_flux;
        const R penetration = kOne / penetration_inverse;
        if (penetration < 0.08F) {
            fmix = kOne;
        } else if (penetration > 0.3F) {
            fmix = kZero;
        } else {
            fmix = 0.08F * penetration_inverse - penetration + 0.08F;
        }
        if (fmix > kZero) {
            rise1 = zi * (kOne - 0.33F * fmix);
            rise2 = zi * (kTwo - fmix);
        } else {
            const R s_aloft = kGravity * inversion_gradient / ambient_temperature;
            if (s_aloft > kZero) {
                rise1 = std::pow(1.8F * zi * zi * zi + 18.75F * buoyancy_flux / (u * s_aloft),
                                 kThirdLong);
            } else {
                rise1 = z_fin_in;
            }
            rise2 = rise1;
        }
    }

    PartialPenetration result;
    result.final_rise_m = static_cast<double>(std::min(z_fin_in, rise1));
    result.mass_fraction_mixed = static_cast<double>(fmix);
    result.max_height_m = static_cast<double>(mixing_height + kTwo * (rise2 - zi));
    return result;
}

PlumeRiseResult gradual_plume_height(const PlumeRiseState& state) {
    // GRISE (calpuff.for L47251-47620), REAL*4.
    (void)to_real(state.x_m, "downwind distance");   // validated, then passed through below
    const R z_frise = to_real(state.full_final_rise_m, "ZFRISE");
    const R z_final = to_real(state.final_rise_m, "ZFINAL");
    const R stack_height = to_real(state.stack_height_m, "stack height");
    const R stack_tip_downwash_m = to_real(state.stack_tip_downwash_m, "stack-tip downwash");
    require_true(state.met_period >= 1, "met period index must be at least 1");

    R rise_fraction = kOne;
    R height = kZero;
    bool lheight = false;
    R rise = kZero;

    int method = 0;
    if (state.source_type == 1 || state.source_type == 2) {
        if (state.downwash_code == 4) {
            method = 0;
        } else if (state.downwash_code == 3) {
            method = 3;
        } else if (state.downwash_code == 2) {
            method = 2;
        } else if (state.downwash_code == 1) {
            method = 1;
        } else if (state.downwash_code == 0) {
            require_true(state.rise_method == 1 || state.rise_method == 2,
                         "MRISE must be 1 (Briggs) or 2 (numerical)");
            method = state.rise_method == 1 ? 1 : 3;
        } else {
            require_true(false, "IDW0 must be 0, 1, 2, 3 or 4");
        }
    }

    if (state.source_type == 1 || state.source_type == 2) {
        if (method == 0) {
            height = z_final;
            lheight = false;
        } else if (method == 1) {
            MomentumRiseInputs momentum;
            momentum.diameter_m = state.diameter_m;
            momentum.exit_velocity_ms = state.exit_velocity_ms;
            momentum.momentum_flux = state.momentum_flux;
            momentum.stack_wind_speed_ms = state.stack_wind_speed_ms;
            momentum.stability_class = state.stability_class;
            momentum.sqrt_stability_s = state.sqrt_stability_s;
            momentum.x_m = state.x_m;
            momentum.x_final_momentum_m = state.x_final_momentum_m;
            momentum.z_final_momentum_m = state.z_final_momentum_m;
            const R rise_momentum = static_cast<R>(transitional_momentum_rise(momentum));
            BuoyantRiseInputs buoyant;
            buoyant.buoyancy_flux = state.buoyancy_flux;
            buoyant.stack_wind_speed_ms = state.stack_wind_speed_ms;
            buoyant.x_m = state.x_m;
            buoyant.x_final_buoyancy_m = state.x_final_buoyancy_m;
            buoyant.z_final_buoyancy_m = state.z_final_buoyancy_m;
            R rise_buoyant = static_cast<R>(transitional_buoyant_rise(buoyant));
            if (state.shear_flag == 1) {
                throw std::runtime_error(
                    "P7N GRISE: MSHEAR=1 needs PRSHEAR/PRFINSH, which are not reconstructed");
            }
            rise = std::max(rise_momentum, rise_buoyant);
            lheight = true;
        } else {
            throw std::runtime_error(
                "P7N GRISE: the tabulated (method 3) and Schulman-Scire (method 2) rise paths are "
                "not reconstructed");
        }
    } else {
        throw std::runtime_error(
            "P7N GRISE: only point sources (ISTYPE 1/2) are reconstructed; area, line and flare "
            "sources are refused");
    }

    if (lheight) {
        height = stack_height + rise - stack_tip_downwash_m;
        height = std::max(kZero, height);
        rise_fraction = z_frise > kZero ? rise / z_frise : kOne;
        if (method == 2) rise_fraction = std::max(rise_fraction, kZero);
    }

    require_true(!(rise_fraction < -0.0001F),
                 "computed rise factor is more negative than single-precision noise; the vendor "
                 "halts here");
    rise_fraction = std::max(rise_fraction, kZero);

    PlumeRiseResult result;
    result.height_m = static_cast<double>(height);
    result.rise_fraction = static_cast<double>(rise_fraction);
    return result;
}

} // namespace cteas::puff
