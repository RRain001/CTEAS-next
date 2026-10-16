#pragma once
#include <cstddef>
#include <vector>
namespace cteas::puff {
// Original CALPUFF v7.2.1 ROLLDN (calpuff.for 19110-19215) and SWAP
// source-array slot COPY (19217-...). Physical REAL4 puff states stay
// in independently owned C++ containers and are addressed by immutable
// source-episode IDs; slots reproduce mutable Fortran II order.
struct OriginalPuffSlot {
    int state_id=0;
    int puff_code=0; // IPUFCD; 99 = inactive
};
struct OriginalRolldnCopy {
    int destination_slot_1based=0;
    int source_slot_1based=0;
};
struct OriginalRolldnResult {
    std::vector<OriginalPuffSlot> slots;
    std::vector<OriginalRolldnCopy> copies;
    std::size_t old_active_after=0;
    std::size_t newly_admitted=0;
    std::size_t retired_old=0;
};
// slots[0..old_count) = old puffs, slots[old_count..] = already
// initialized new puffs. Fortran ROLLDN searches inactive (code==99)
// ascending and copies later active old slots down descending; new puffs
// are appended in original insertion order. SWAP(I,J) is a COPY,
// never a symmetric C++ std::swap. Returns compacted array mapping.
[[nodiscard]] OriginalRolldnResult original_rolldn_slots(
    const std::vector<OriginalPuffSlot>& slots,std::size_t old_count);
} // namespace cteas::puff
