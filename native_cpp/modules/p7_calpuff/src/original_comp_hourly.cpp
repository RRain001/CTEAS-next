#include "cteas/puff/original_comp_hourly.hpp"
#include <algorithm>
#include <stdexcept>
#include <utility>

namespace cteas::puff {
NativeCompHour OriginalCompMultiPuffHours::advance_hour_pg(
    const OriginalMetHour& met,const Calmet21Static& statics,
    const NeutralCompControls& controls,
    const DispersionSetup& pg,bool urban,
    const std::vector<HourlyPointAdmission>& admissions) {
    // Strict caller-controlled admission, no hidden ID reuse. Canonical
    // ascending source order is deterministic and verifiable. Without
    // original POINTS1/SWAP it is not asserted to equal vendor array order.
    int candidate_last=last_id_;
    for(const auto& src:admissions) {
        if(src.puff_id<=candidate_last)
            throw std::invalid_argument(
                "non-monotonic native puff release IDs");
        candidate_last=src.puff_id;
    }
    auto trial=puffs_;
    auto ids=active_ids_;
    for(const auto& src:admissions) {
        trial.admit(src.puff_id,src.point,src.mass);
        ids.push_back(src.puff_id);
    }
    NativeCompHour result;
    result.hour_index=hours_;
    result.steps.reserve(ids.size());
    // No shared mutable commit until EVERY active puff and every newly
    // admitted puff has finished the whole physical hour successfully.
    for(const int id:ids) {
        result.steps.push_back({id,
            trial.step_pg(id,met,statics,controls,pg,urban)});
    }
    result.active_after=ids.size();
    puffs_=std::move(trial);
    active_ids_=std::move(ids);
    last_id_=candidate_last;
    ++hours_;
    return result;
}
OriginalPuffMotionState OriginalCompMultiPuffHours::motion(int id)const {
    return puffs_.motion(id);
}
NativeVerticalPuffState OriginalCompMultiPuffHours::vertical(int id)const {
    return puffs_.vertical(id);
}
std::size_t OriginalCompMultiPuffHours::puff_steps(int id)const {
    return puffs_.steps(id);
}
std::size_t OriginalCompMultiPuffHours::active_count()const noexcept {
    return active_ids_.size();
}
std::size_t OriginalCompMultiPuffHours::completed_hours()const noexcept {
    return hours_;
}
const std::vector<int>& OriginalCompMultiPuffHours::canonical_ids()const noexcept{
    return active_ids_;
}
void OriginalCompMultiPuffHours::retire(int id) {
    if(std::find(active_ids_.begin(),active_ids_.end(),id)==active_ids_.end())
        throw std::out_of_range("retire unknown native puff");
    auto trial=puffs_;
    trial.retire(id);
    // Commit only after native motion and vertical states both retired.
    puffs_=std::move(trial);
    active_ids_.erase(
        std::remove(active_ids_.begin(),active_ids_.end(),id),
        active_ids_.end());
}
} // namespace cteas::puff
