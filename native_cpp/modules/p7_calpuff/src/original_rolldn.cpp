#include "cteas/puff/original_rolldn.hpp"
#include <stdexcept>
#include <unordered_set>
#include <utility>
namespace cteas::puff {
OriginalRolldnResult original_rolldn_slots(
    const std::vector<OriginalPuffSlot>& original,std::size_t old_count){
    if(old_count>original.size())
        throw std::invalid_argument("ROLDN old_count exceeds initialized NP");
    std::unordered_set<int> seen;
    for(const auto& p:original) {
        if(p.state_id<=0||p.puff_code<0||
           (p.puff_code>16 && p.puff_code!=99) ||
           !seen.insert(p.state_id).second)
            throw std::invalid_argument("invalid/duplicate puff slot");
    }
    const auto new_count=original.size()-old_count;
    auto work=original;
    OriginalRolldnResult result;
    int inact=1;
    int j=static_cast<int>(old_count);
    // Exact vendor L19162-19180: descending old J, ascending missing I.
    for(;j>=1;--j){
        if(work[static_cast<std::size_t>(j-1)].puff_code<99){
            bool found=false;
            for(int i=inact;i<=j;++i){
                if(work[static_cast<std::size_t>(i-1)].puff_code==99){
                    work[static_cast<std::size_t>(i-1)]=
                        work[static_cast<std::size_t>(j-1)];
                    result.copies.push_back({i,j});
                    inact=i;
                    found=true;
                    break;
                }
            }
            if(!found)break; // Fortran GOTO 50 leaves J unchanged.
        }
    }
    const auto kept=static_cast<std::size_t>(j<0?0:j);
    if(kept>old_count)
        throw std::logic_error("ROLDN old count grew");
    // Exact vendor L19185-19205: copy already initialized new puffs
    // *forward*, preserving release order rather than sorting old IDs.
    for(std::size_t i=0;i<new_count;++i){
        const auto dest=kept+i;
        const auto src=old_count+i;
        work[dest]=work[src];
        result.copies.push_back({
            static_cast<int>(dest+1),static_cast<int>(src+1)
        });
    }
    work.resize(kept+new_count);
    for(const auto& p:work){
        if(p.puff_code==99)
            throw std::logic_error("ROLDN left inactive code in packed prefix");
    }
    result.slots=std::move(work);
    result.old_active_after=kept;
    result.newly_admitted=new_count;
    result.retired_old=old_count-kept;
    return result;
}
} // namespace cteas::puff
