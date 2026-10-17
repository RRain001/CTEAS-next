#include "cteas/puff/original_rolldn.hpp"
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace cteas::puff;
namespace {
void eq(const OriginalRolldnResult& r,
        const std::vector<int>& wanted,std::size_t old,
        std::size_t new_count,std::size_t lost) {
    if(r.slots.size()!=wanted.size() ||
       r.old_active_after!=old ||
       r.newly_admitted!=new_count ||
       r.retired_old!=lost)
        throw std::runtime_error("vendor ROLLDN count discrepancy");
    for(std::size_t i=0;i<wanted.size();++i){
        if(r.slots[i].state_id!=wanted[i] ||
           r.slots[i].puff_code==99)
            throw std::runtime_error("vendor ROLLDN slot copy/order mismatch");
    }
}
void run(){
    eq(original_rolldn_slots({{1,1},{2,99},{3,1},{4,99},
                             {5,1},{6,1},{7,1}},5),
       {1,5,3,6,7},3,2,2);
    eq(original_rolldn_slots({{1,99},{2,99},{3,99},{4,1},{5,1}},3),
       {4,5},0,2,3);
    eq(original_rolldn_slots({{1,1},{2,1},{3,1},{4,1}},3),
       {1,2,3,4},3,1,0);
    eq(original_rolldn_slots({{1,1},{2,1},{3,99},{4,1}},3),
       {1,2,4},2,1,1);
    eq(original_rolldn_slots({{1,1},{2,99},{3,1},{4,99},{5,1}},5),
       {1,5,3},3,0,2);
    eq(original_rolldn_slots({{4,1},{5,1}},0),
       {4,5},0,2,0);
    bool bad=false;try{
        (void)original_rolldn_slots({{1,1},{1,99}},1);
    }catch(const std::invalid_argument&){bad=true;}
    if(!bad)throw std::runtime_error("duplicate puff admitted");
    std::cout<<"P7_ORIGINAL_ROLLDN_SWAPTAB_SLOT_ORDER=PASS"
             <<" OLD_DESCENDING_NEW_ORDER=YES"
             <<" INACTIVE_99=YES"
             <<" SWAP_IS_COPY=YES"
             <<" REAL_143H_OFFDOMAIN_AUTORETIRE=NOT_YET_VALIDATED\n";
}
}
int main(){try{run();return 0;}catch(const std::exception& e){
    std::cerr<<"P7_ORIGINAL_ROLLDN_SWAPTAB_SLOT_ORDER=FAIL "<<e.what()<<"\n";
    return 1;}}
