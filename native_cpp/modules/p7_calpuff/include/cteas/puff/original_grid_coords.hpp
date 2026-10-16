#pragma once

#include "cteas/puff/original_precision.hpp"
#include <cmath>
#include <stdexcept>

namespace cteas::puff {

// Source of the inputs: original CALMET.DAT version 2.1 (REAL*4 metre
// origin/spacing). The original CALPUFF QA output converts its origin to
// REAL*4 kilometres by *multiplying by REAL*4 0.001*, not by a double
// precision division. These are intentionally separate from original
// puff.inp's independently rounded XORIGKM/YORIGKM.
struct OriginalMetGridFrame {
    VendorPointCommonReal x_origin_m = 0.0f;
    VendorPointCommonReal y_origin_m = 0.0f;
    VendorPointCommonReal spacing_m = 0.0f;
};

struct OriginalQaXYkm {
    VendorPointCommonReal x_km = 0.0f;
    VendorPointCommonReal y_km = 0.0f;
};

inline void validate_original_met_frame(const OriginalMetGridFrame& frame) {
    if (!std::isfinite(frame.x_origin_m) || !std::isfinite(frame.y_origin_m) ||
        !std::isfinite(frame.spacing_m) || frame.spacing_m <= 0.0f) {
        throw std::invalid_argument("P7 original meteorological grid frame is invalid");
    }
}

// These routines describe observable **QA absolute UTM km coordinates** on
// the selected P7 CALMET grid; they are not the original's internal relative
// XPT1GRD/YPT1GRD and do not establish full model-state parity.
[[nodiscard]] inline OriginalQaXYkm original_point_qa_xy(
    const OriginalMetGridFrame& frame, float original_source_x_km,
    float original_source_y_km, float control_x_origin_km,
    float control_y_origin_km) {
    validate_original_met_frame(frame);
    if (!std::isfinite(original_source_x_km) || !std::isfinite(original_source_y_km) ||
        !std::isfinite(control_x_origin_km) || !std::isfinite(control_y_origin_km)) {
        throw std::invalid_argument("P7 original point coordinates are not finite");
    }
    const float met_x_origin_km = frame.x_origin_m * 0.001f;
    const float met_y_origin_km = frame.y_origin_m * 0.001f;
    const float point_x_offset_km = original_source_x_km - control_x_origin_km;
    const float point_y_offset_km = original_source_y_km - control_y_origin_km;
    return {met_x_origin_km + point_x_offset_km,
            met_y_origin_km + point_y_offset_km};
}

// Gridded QA receptors are first positioned half a cell from the *CALMET*
// origin, and the REAL*4 grid index offset is added after that rounding.
// A single expression origin + (index + 0.5)*dx produces different Y and
// certain X coordinates and cannot reproduce original qarecg.dat.
[[nodiscard]] inline OriginalQaXYkm original_gridded_receptor_qa_xy(
    const OriginalMetGridFrame& frame, int i_zero_based, int j_zero_based) {
    validate_original_met_frame(frame);
    if (i_zero_based < 0 || j_zero_based < 0) {
        throw std::invalid_argument("P7 gridded receptor index is negative");
    }
    const float dx_km = frame.spacing_m * 0.001f;
    const float half_cell_km = 0.5f * dx_km;
    const float x_start_km = (frame.x_origin_m * 0.001f) + half_cell_km;
    const float y_start_km = (frame.y_origin_m * 0.001f) + half_cell_km;
    return {x_start_km + static_cast<float>(i_zero_based) * dx_km,
            y_start_km + static_cast<float>(j_zero_based) * dx_km};
}

} // namespace cteas::puff
