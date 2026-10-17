#pragma once

#include "cteas/puff/original_rolldn.hpp"
#include <algorithm>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::puff {

// Original CALPUFF POINTS1 L15986-15999: old puff slots include ICODE=99
// holes until NP+NEWPUF exceeds MXPUFF. ROLLDN is NOT an hourly cleanup.
struct OriginalCapacityDecision {
    bool rolled_down=false;
    std::size_t removed_inactive=0;
    std::size_t occupied_before=0;
    std::size_t occupied_after=0; // old slots after possible ROLLDN
};

class OriginalPuffCapacityInventory {
public:
    explicit OriginalPuffCapacityInventory(std::size_t mxpuff)
        :mxpuff_(mxpuff) {
        if(mxpuff_==0)throw std::invalid_argument("MXPUFF must be positive");
    }
    [[nodiscard]] std::size_t limit()const noexcept{return mxpuff_;}
    [[nodiscard]] std::size_t occupied()const noexcept{return slots_.size();}
    [[nodiscard]] std::size_t inactive()const noexcept {
        return static_cast<std::size_t>(std::count_if(
            slots_.begin(),slots_.end(),
            [](const auto& s){return s.puff_code==99;}));
    }
    [[nodiscard]] const std::vector<OriginalPuffSlot>& slots()const noexcept {
        return slots_;
    }
    [[nodiscard]] std::vector<int> active_ids()const {
        std::vector<int> ids;
        ids.reserve(slots_.size());
        for(const auto& p:slots_)if(p.puff_code<99)ids.push_back(p.state_id);
        return ids;
    }
    // Must run once, before POINTS1 initializes any new source slots.
    // Keeps *all* ICODE=99 holes when no capacity pressure exists.
    // Capacity failure is atomic: preserves original array/slot order.
    [[nodiscard]] OriginalCapacityDecision prepare_release(
        std::size_t incoming) {
        if(incoming>mxpuff_)throw std::overflow_error(
            "POINTS1 NEWPUF exceeds MXPUFF even with no old puffs");
        OriginalCapacityDecision r;
        r.occupied_before=slots_.size();
        r.occupied_after=slots_.size();
        if(slots_.size()+incoming<=mxpuff_)return r;
        const auto compacted=original_rolldn_slots(slots_,slots_.size());
        if(compacted.slots.size()+incoming>mxpuff_)
            throw std::overflow_error("POINTS1 ROLLDN insufficient MXPUFF capacity");
        r.rolled_down=true;
        r.removed_inactive=compacted.retired_old;
        r.occupied_after=compacted.slots.size();
        slots_=compacted.slots;
        return r;
    }
    void append(int id,int code) {
        if(id<=0 || code<1 || code>16 || occupied()>=mxpuff_)
            throw std::invalid_argument("invalid POINTS1 puff slot append");
        for(const auto& s:slots_)
            if(s.state_id==id)throw std::invalid_argument("duplicate source puff ID");
        slots_.push_back({id,code});
    }
    // Vendor COMP only writes ICODE=99 here, without changing NPUFFS.
    void retire(int id) {
        auto it=std::find_if(slots_.begin(),slots_.end(),
            [id](const auto& s){return s.state_id==id;});
        if(it==slots_.end() || it->puff_code==99)
            throw std::invalid_argument("inactive or unknown puff retirement");
        it->puff_code=99;
    }
    void update_code(int id,int code) {
        if(code<1||code>16)throw std::invalid_argument("bad active ICODE");
        auto it=std::find_if(slots_.begin(),slots_.end(),
            [id](const auto& s){return s.state_id==id;});
        if(it==slots_.end() || it->puff_code==99)
            throw std::invalid_argument("unknown active puff code update");
        it->puff_code=code;
    }
private:
    std::size_t mxpuff_;
    std::vector<OriginalPuffSlot> slots_;
};
} // namespace cteas::puff
