#include "cteas/puff/advection.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {

using R = AdvectionReal;

constexpr R kZero = 0.0F;
constexpr R kOne = 1.0F;
constexpr R kHalf = 0.5F;
constexpr R kTwo = 2.0F;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7V advection: " + message);
}

void require_finite(double value, const std::string& what) {
    require_true(std::isfinite(value), what + " must be finite");
}

R to_real(double value, const char* what) {
    require_finite(value, what);
    return static_cast<R>(value);
}

} // namespace

int find_layer(double height_m, const std::vector<double>& face_heights_m) {
    // ZFIND (calpuff.for L18381-18419), REAL*4 comparisons.
    require_finite(height_m, "height");
    require_true(face_heights_m.size() >= 2U,
                 "at least two face heights are needed to define a layer");
    const R z = static_cast<R>(height_m);
    const int nzp1 = static_cast<int>(face_heights_m.size());
    for (int i = 2; i <= nzp1; ++i) {
        const R face = to_real(face_heights_m[static_cast<std::size_t>(i - 1)], "face height");
        if (z < face) return i - 1;
    }
    return nzp1 - 1;
}

LayerAverage layer_average_wind(const LayerAverageInputs& inputs) {
    // ADVWND (calpuff.for L2438-2538), REAL*4.
    require_true(inputs.face_heights_m.size() >= 2U, "at least two face heights are required");
    const std::size_t layers = inputs.face_heights_m.size() - 1U;
    require_true(inputs.u_ms.size() >= layers && inputs.v_ms.size() >= layers,
                 "the wind profile must cover every layer");
    const int nzp1 = static_cast<int>(inputs.face_heights_m.size());
    const R bottom = to_real(inputs.z_bottom_m, "zbot");
    const R top = to_real(inputs.z_top_m, "ztop");

    // Clamp the averaging depth to the met field.
    R zabot = bottom;
    const R first_face = to_real(inputs.face_heights_m.front(), "first face height");
    const R last_face = to_real(inputs.face_heights_m.back(), "last face height");
    if (zabot < first_face) zabot = first_face;
    if (zabot > last_face) zabot = last_face;
    R zatop = top;
    if (zatop < first_face) zatop = first_face;
    if (zatop > last_face) zatop = last_face;

    const auto face = [&inputs](int index) {
        return to_real(inputs.face_heights_m[static_cast<std::size_t>(index - 1)], "face height");
    };
    const int ibot = find_layer(static_cast<double>(zabot), inputs.face_heights_m);
    const int itop = find_layer(static_cast<double>(zatop), inputs.face_heights_m);

    LayerAverage result;
    if (ibot == itop) {
        result.u_ms = inputs.u_ms[static_cast<std::size_t>(ibot - 1)];
        result.v_ms = inputs.v_ms[static_cast<std::size_t>(ibot - 1)];
        return result;
    }
    R delz = face(ibot + 1) - zabot;
    R sumu = delz * to_real(inputs.u_ms[static_cast<std::size_t>(ibot - 1)], "u");
    R sumv = delz * to_real(inputs.v_ms[static_cast<std::size_t>(ibot - 1)], "v");
    R sumz = delz;
    delz = zatop - face(itop);
    sumu += delz * to_real(inputs.u_ms[static_cast<std::size_t>(itop - 1)], "u");
    sumv += delz * to_real(inputs.v_ms[static_cast<std::size_t>(itop - 1)], "v");
    sumz += delz;
    for (int i = ibot + 1; i <= itop - 1; ++i) {
        delz = face(i + 1) - face(i);
        sumu += delz * to_real(inputs.u_ms[static_cast<std::size_t>(i - 1)], "u");
        sumv += delz * to_real(inputs.v_ms[static_cast<std::size_t>(i - 1)], "v");
        sumz += delz;
    }
    require_true(sumz != kZero, "the averaging depth must not be zero");
    result.u_ms = static_cast<double>(sumu / sumz);
    result.v_ms = static_cast<double>(sumv / sumz);
    (void)nzp1;
    return result;
}

AdvectiveWind advective_wind(const AdvectiveWindInputs& inputs) {
    // ADVECT (calpuff.for L2540-2765), REAL*4, METFM = 1 path.
    require_true(inputs.met_format == 1,
                 "only METFM=1 (3-D gridded met) is reconstructed; METFM 2/3 need POWLAW and "
                 "METFM 4/5 need XTPRF");
    LayerAverageInputs average;
    average.u_ms = inputs.u_profile_ms;
    average.v_ms = inputs.v_profile_ms;
    average.face_heights_m = inputs.face_heights_m;
    average.z_bottom_m = inputs.z_bottom_m;
    average.z_top_m = inputs.z_top_m;
    require_true(static_cast<double>(inputs.z_top_m) >= static_cast<double>(inputs.z_bottom_m),
                 "the vendor halts when the puff bottom exceeds its top");
    const auto wind = layer_average_wind(average);
    AdvectiveWind result;
    result.u_ms = wind.u_ms;
    result.v_ms = wind.v_ms;
    return result;
}

PuffExtent puff_extent(const PuffExtentInputs& inputs) {
    // PUFFDZ (calpuff.for L2882-3005), REAL*4.
    require_true(inputs.stability_class >= 1 && inputs.stability_class <= 6,
                 "the stability class must be 1-6");
    const R height = to_real(inputs.puff_height_m, "puff height");
    const R mixing = to_real(inputs.mixing_height_m, "mixing height");
    const R sigma_z_begin = to_real(inputs.sigma_z_begin_m, "sigma-z at the start");
    const R sigma_z_end = to_real(inputs.sigma_z_end_m, "sigma-z at the end");
    const R ziold = to_real(inputs.previous_mixing_height_m, "previous mixing height");
    const R zimax = to_real(inputs.maximum_mixing_height_m, "maximum mixing height");
    const R layer_bottom = to_real(inputs.layer_bottom_m, "layer bottom");
    const R layer_top = to_real(inputs.layer_top_m, "layer top");
    require_true(sigma_z_begin >= kZero && sigma_z_end >= kZero,
                 "the sigmas must not be negative");

    R ztop = kZero;
    R zbot = kZero;
    if (inputs.puff_code % 2 == 1) {
        // Gaussian in the vertical: height +/- sigma-z.
        const R sigmaz = inputs.puff ? sigma_z_begin : kHalf * (sigma_z_begin + sigma_z_end);
        zbot = height - sigmaz;
        if (zbot < kZero) zbot = kZero;
        ztop = height + sigmaz;
        if (inputs.puff_code != 3 && inputs.puff_code != 13 && inputs.stability_class <= 4) {
            if (mixing > height) {
                ztop = std::min(ztop, mixing);
            } else if (ziold > height) {
                ztop = std::min(ztop, ziold);
            } else if (zimax > height) {
                ztop = std::min(ztop, zimax);
            }
        }
    } else if (inputs.puff_code == 2 || inputs.puff_code == 12) {
        zbot = kZero;
        ztop = zimax;
    } else if (inputs.puff_code == 4 || inputs.puff_code == 14) {
        zbot = layer_bottom;
        ztop = layer_top;
    } else if (inputs.puff_code == 6 || inputs.puff_code == 16) {
        zbot = kZero;
        ztop = zimax;
        require_true(inputs.mixed_layer_mass.size() == inputs.above_layer_mass.size(),
                     "the per-species mass arrays must have equal length");
        R mixed_total = kZero;
        R above_total = kZero;
        for (std::size_t index = 0; index < inputs.mixed_layer_mass.size(); ++index) {
            mixed_total += to_real(inputs.mixed_layer_mass[index], "mixed-layer mass");
            above_total += to_real(inputs.above_layer_mass[index], "above-layer mass");
        }
        if (above_total > kTwo * mixed_total) {
            zbot = ziold * (kOne - kTwo * mixed_total / above_total);
        }
    } else {
        throw std::invalid_argument(
            "P7V PUFFDZ: the vendor halts on an invalid ICODE; the port refuses it");
    }
    require_true(!(ztop < zbot), "the vendor halts when the puff bottom exceeds its top");
    PuffExtent result;
    result.z_top_m = static_cast<double>(ztop);
    result.z_bottom_m = static_cast<double>(zbot);
    return result;
}

} // namespace cteas::puff
