#pragma once

#include <vector>

namespace cteas::puff {

// These are the original CALPUFF COMP XB/XE/YB/YE bounds IN PUFF GRID
// COORDINATES, not CALMET NX/NY or UTM position. Caller MUST independently
// resolve the original case's values. Lower and upper edges are inclusive:
// the vendor uses XNEW.LT.XB / XNEW.GT.XE (same for Y).
struct OriginalCompPuffBounds {
    float xb=0.0F;
    float xe=0.0F;
    float yb=0.0F;
    float ye=0.0F;
};

enum class OriginalCompExitReason {
    Active,
    ExhaustedMass,
    OutsideComputationalDomain
};

[[nodiscard]] OriginalCompExitReason original_comp_before_step_exit(
    const std::vector<float>& mixed_mass,
    const std::vector<float>& upper_mass);

// Original COMP source L11400-11413 is evaluated AFTER this puff's
// physical substep; it tests center coordinates, not gaussian sigma
// footprint. Slug endpoints are OUT OF SCOPE.
[[nodiscard]] OriginalCompExitReason original_comp_after_step_exit(
    float xnew_cells,float ynew_cells,const OriginalCompPuffBounds& bounds);

} // namespace cteas::puff
