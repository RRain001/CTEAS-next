#include "cteas/puff/original_motion_lifecycle.hpp"
#include "cteas/puff/step.hpp"
#include "cteas/puff/step_integration.hpp"

#include <cmath>
#include <stdexcept>

namespace cteas::puff {
namespace {
void require(bool valid, const char* problem) {
    if (!valid) throw std::invalid_argument(problem);
}
void check_state(const OriginalPuffMotionState& value) {
    require(std::isfinite(value.x_cells) && std::isfinite(value.y_cells)
            && std::isfinite(value.z_m) && std::isfinite(value.total_distance_m)
            && std::isfinite(value.travel_time_s), "non-finite puff state");
    require(value.total_distance_m >= 0.0F && value.travel_time_s >= 0.0F,
            "negative puff distance/age");
}
}
void OriginalPuffMotionLifecycle::introduce(int puff_id, OriginalPuffMotionState value) {
    require(puff_id > 0, "CALPUFF puff index must be positive");
    check_state(value);
    require(puffs_.emplace(puff_id, value).second, "puff index already active");
}
void OriginalPuffMotionLifecycle::introduce_point_source(
    int puff_id, const NewPuffInputs& source) {
    // Original CALPUFF POINTS1 stores positions and heights into REAL*4
    // COMMON /PUFF/, and SWAP initializes cumulative distance and age to
    // zero. Do not seed these values from a future DGM oracle record.
    require(source.source_type == 1,
            "native first-release state requires an original point source");
    const auto released = new_puff_state(source);
    introduce(puff_id, {
        static_cast<VendorPuffCommonReal>(released.x_km),
        static_cast<VendorPuffCommonReal>(released.y_km),
        static_cast<VendorPuffCommonReal>(released.height_begin_m),
        0.0F, 0.0F
    });
}
bool OriginalPuffMotionLifecycle::contains(int id) const noexcept {
    return puffs_.find(id) != puffs_.end();
}
OriginalPuffMotionState OriginalPuffMotionLifecycle::state(int id) const {
    const auto it=puffs_.find(id);
    if (it==puffs_.end()) throw std::out_of_range("unknown active puff");
    return it->second;
}
OriginalPostWindResult OriginalPuffMotionLifecycle::advance(int puff_id,
                                                           OriginalPostWindInputs inputs) {
    const auto it=puffs_.find(puff_id);
    if (it==puffs_.end()) throw std::out_of_range("advance before puff admission");
    require(std::isfinite(inputs.end_height_m)
            && std::isfinite(inputs.uadv_ms) && std::isfinite(inputs.vadv_ms)
            && std::isfinite(inputs.ws_ms) && std::isfinite(inputs.tsamp_s)
            && std::isfinite(inputs.met_spacing_m)
            && std::isfinite(inputs.settling_velocity_ms), "nonfinite COMP forcing");
    require(inputs.tsamp_s > 0.0F && inputs.met_spacing_m > 0.0F,
            "invalid COMP time / spacing");
    const auto before=it->second;
    // 1. COMP L10607-10619: native REAL*4 wind advection; update reads the
    // puff's *previous persisted* XY, never repeated Fortran XOLD input.
    const auto position=advance_puff({before.x_cells,before.y_cells,
                                     inputs.uadv_ms,inputs.vadv_ms,
                                     inputs.tsamp_s,inputs.met_spacing_m,
                                     inputs.ws_ms});
    // 2. SETPUF L48706-48723: native REAL*4 cumulative distance/time,
    // settling and position publication. No partial write on exception.
    const auto stored=apply_step_update({
        .height_end_m=inputs.end_height_m,
        .settling_velocity_ms=inputs.settling_velocity_ms,
        .plume_tilt=inputs.plume_tilt,
        .step_seconds=inputs.tsamp_s,
        .step_distance_m=position.distance_m,
        .total_distance_m=before.total_distance_m,
        .total_time_s=before.travel_time_s,
        .x_new_km=position.x_cells,
        .y_new_km=position.y_cells});
    const OriginalPuffMotionState after{
        static_cast<float>(stored.x_km),static_cast<float>(stored.y_km),
        static_cast<float>(stored.z_km),static_cast<float>(stored.total_distance_m),
        static_cast<float>(stored.total_time_s)};
    check_state(after);
    it->second=after;
    return {after, static_cast<float>(position.distance_m)};
}
void OriginalPuffMotionLifecycle::commit_setpuf_terrain_height(
    int id,float expected_height,float terrain_height) {
    const auto it=puffs_.find(id);
    if(it==puffs_.end())throw std::out_of_range("SETPUF terrain on absent puff");
    require(std::isfinite(expected_height)&&std::isfinite(terrain_height),
            "CTADJ2 REAL4 height must be finite");
    require(it->second.z_m==expected_height,
            "SETPUF CTADJ2 attempted to overwrite stale puff height");
    auto after=it->second;
    after.z_m=terrain_height;
    check_state(after);
    it->second=after;
}
void OriginalPuffMotionLifecycle::retire(int id) {
    if (puffs_.erase(id)!=1U) throw std::out_of_range("retire unknown puff");
}
std::size_t OriginalPuffMotionLifecycle::active_count() const noexcept {
    return puffs_.size();
}
} // namespace cteas::puff
