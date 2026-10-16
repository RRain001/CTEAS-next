#pragma once

#include "cteas/puff/original_comp_neutral.hpp"
#include <cstddef>
#include <vector>

namespace cteas::puff {

// A deterministic *native* multi-puff, one-COMP-hour transaction using the
// previously verified single-puff PG substep. Caller supplies point-source
// admissions until native POINTS1 cadence is integrated. This is not the
// full original SWAP/ROLLDN or rising stack trajectory; those remain OPEN.
struct HourlyPointAdmission {
    int puff_id=0;
    NewPuffInputs point;
    InjectionInputs mass;
};
struct HourlyPointResult {
    int puff_id=0;
    NeutralCompResult state;
};
struct NativeCompHour {
    std::size_t hour_index=0;
    std::vector<HourlyPointResult> steps;
    std::size_t active_after=0;
};

class OriginalCompMultiPuffHours {
public:
    [[nodiscard]] NativeCompHour advance_hour_pg(
        const OriginalMetHour& met,const Calmet21Static& statics,
        const NeutralCompControls& controls,
        const DispersionSetup& pg,bool urban,
        const std::vector<HourlyPointAdmission>& admissions);
    [[nodiscard]] OriginalPuffMotionState motion(int id)const;
    [[nodiscard]] NativeVerticalPuffState vertical(int id)const;
    [[nodiscard]] std::size_t puff_steps(int id)const;
    [[nodiscard]] std::size_t active_count()const noexcept;
    [[nodiscard]] std::size_t completed_hours()const noexcept;
    [[nodiscard]] const std::vector<int>& canonical_ids()const noexcept;
    void retire(int id);
private:
    OriginalCompNeutralPointDriver puffs_;
    std::vector<int> active_ids_;
    std::size_t hours_=0;
    int last_id_=0;
};
} // namespace cteas::puff
