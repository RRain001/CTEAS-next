// S4-B1 contract tests; does NOT claim original-vendor physics parity.
#include "cteas/p6/p6g_s4b1_admission.hpp"
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <utility>

namespace p6g = cteas::calmet::p6g;

template<class Fn> void must_reject(Fn&& fn) {
    bool threw = false;
    try { fn(); } catch (const std::exception&) { threw = true; }
    if(!threw) throw std::runtime_error("S4-E invalid source shape was accepted");
}

int main() {
    // Independently variable SS/US (no false equality condition).
    for (std::size_t ss : {std::size_t{1}, std::size_t{2}, std::size_t{3}}) {
        for (std::size_t us : {std::size_t{1}, std::size_t{2}, std::size_t{4}}) {
            const p6g::S4B1Admission request{12, 12, 9, ss, us, 143, true, true};
            const auto admitted = p6g::s4b1_admit_source_only(request);
            if(admitted.input.surface_stations != ss ||
               admitted.input.upper_stations != us ||
               admitted.cells_per_layer != 144 ||
               admitted.potential_field_records != 143u*45u ||
               admitted.native_physics_accepted)
                throw std::runtime_error("S4-B1 original source admission regressed");
        }
    }
    // The user-selected 20-station numerical gate is a science coverage
    // target, not a physical array cap. Independently budget 20+20 and
    // the asymmetric 20+1 / 1+20 source shapes with the SAME contract.
    for(const auto& [ss,us]:{
        std::pair<std::size_t,std::size_t>{20,20},{20,1},{1,20},
        {350,99},{400,150}}) {
        const auto x=p6g::s4b1_admit_source_only(
            {12,12,9,ss,us,6,true,true});
        if(x.source_station_columns!=ss+us ||
           x.source_station_hour_slots!=6*(ss+us) ||
           x.wind_profile_scalars_per_component!=9*(ss+us) ||
           x.native_physics_accepted)
            throw std::runtime_error("S4-E source shape budget disagrees with actual station inputs");
    }
    const auto long_case = p6g::s4b1_admit_source_only(
        {50, 60, 9, 1, 2, 8784, true, true});
    if(long_case.cells_per_layer != 3000 ||
       long_case.potential_field_records != 8784u * 45u ||
       long_case.one_hour_raw_field_bytes!=3000u*45u*4u ||
       long_case.retained_raw_field_bytes!=
           std::size_t{8784}*3000u*45u*4u ||
       long_case.field_record_payload_bytes!=24u+3000u*4u)
        throw std::runtime_error("S4-B1 long source dimensions/bytes regressed");
    // 100x100, 8760 hours is an exact RAW retained-field lower bound,
    // not RSS, serialization size, disk usage, or approval for a year run.
    const auto large=p6g::s4b1_admit_source_only(
        {100,100,9,20,1,8760,true,true});
    const auto expected=std::size_t{100}*100u*45u*4u*8760u;
    if(large.retained_raw_field_bytes!=expected ||
       large.one_hour_raw_field_bytes!=100u*100u*45u*4u ||
       large.field_record_payload_bytes!=24u+100u*100u*4u)
        throw std::runtime_error("S4E grid-hour raw output lower bound incorrect");
    p6g::s4b1_require_retained_field_budget(large,expected);
    p6g::s4b1_require_retained_field_budget(large,expected+1u);
    must_reject([&]{p6g::s4b1_require_retained_field_budget(large,expected-1u);});
    must_reject([&]{p6g::s4b1_require_retained_field_budget(large,0u);});
    must_reject([] { (void)p6g::s4b1_admit_source_only({12,12,9,0,1,6,true,true}); });
    must_reject([] { (void)p6g::s4b1_admit_source_only({12,12,9,1,0,6,true,true}); });
    must_reject([] { (void)p6g::s4b1_admit_source_only({1,12,9,1,1,6,true,true}); });
    must_reject([] { (void)p6g::s4b1_admit_source_only({12,12,8,1,1,6,true,true}); });
    must_reject([] { (void)p6g::s4b1_admit_source_only({12,12,9,1,1,0,true,true}); });
    must_reject([] { (void)p6g::s4b1_admit_source_only({12,12,9,1,1,6,false,true}); });
    must_reject([] { (void)p6g::s4b1_admit_source_only({12,12,9,1,1,6,true,false}); });
    // Correct software rejection rather than signed 32-bit Fortran
    // record-marker truncation, IRLG truncation or size_t multiplication.
    must_reject([] { (void)p6g::s4b1_admit_source_only(
        {50000,50000,9,1,1,6,true,true}); });
    must_reject([] { (void)p6g::s4b1_admit_source_only(
        {12,12,9,1,1,
         static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max())+1,
         true,true}); });
    must_reject([] { (void)p6g::s4b1_admit_source_only(
        {30000,30000,9,1,1,2000000000u,true,true}); });
    must_reject([] { (void)p6g::s4b1_checked_product(
        std::numeric_limits<std::size_t>::max(), 2); });
    must_reject([] { (void)p6g::s4b1_checked_sum(
        std::numeric_limits<std::size_t>::max(), 1); });
    must_reject([] { (void)p6g::s4b1_admit_source_only(
        {12,12,9,std::numeric_limits<std::size_t>::max(),1,6,true,true}); });
    must_reject([] { (void)p6g::s4b1_admit_source_only(
        {12,12,9,20,20,std::numeric_limits<std::size_t>::max(),true,true}); });
    // hours*45 remains representable, but (NSSTA+NUSTA)*hours must fail.
    must_reject([] { (void)p6g::s4b1_admit_source_only(
        {12,12,9,20,30,std::numeric_limits<std::size_t>::max()/45,true,true}); });
    std::cout << "S4B1_INDEPENDENT_1_TO_N_SS_US_ADMISSION=PASS_SOFTWARE_ONLY\n"
              << "S4E_RETAINED_FIELD_BYTES_AND_FORTRAN_RECORD_GUARDS=PASS_SOFTWARE_ONLY\n"
              << "S4B1_UNIFIED_NATIVE_MET_45FIELD_SCIENCE=NOT_RUN\n";
}
