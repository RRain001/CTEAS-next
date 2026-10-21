#pragma once
// S4-B1: immutable G19->G14 admission; no replacement physics, no MET writer.
// Source identity/options are checked by G19 before this bounded contract.
// Station counts are independent. Larger physical capacity belongs to S5.
#include <cstddef>
#include <limits>
#include <stdexcept>

namespace cteas::calmet::p6g {

struct S4B1Admission {
    std::size_t nx = 0;
    std::size_t ny = 0;
    std::size_t nz = 0;
    std::size_t surface_stations = 0;
    std::size_t upper_stations = 0;
    std::size_t hours = 0;
    // These booleans may only be asserted by the real original-file G19
    // loader and its chronological G14 scheduler, never by an arbitrary CLI.
    bool original_source_admitted = false;
    bool chronological_g14_admitted = false;
};

struct S4B1AdmittedCase {
    S4B1Admission input;
    std::size_t cells_per_layer = 0;
    std::size_t per_hour_original_fields = 45;
    std::size_t potential_field_records = 0;
    // No physical publication authority is assigned until B2/B3 science.
    bool native_physics_accepted = false;
    // S4-E checked *logical source shapes*, NOT a measured RAM budget or
    // proof of production execution. All counts remain source-dependent.
    std::size_t source_station_columns = 0;
    std::size_t source_station_hour_slots = 0;
    std::size_t wind_profile_scalars_per_component = 0;
};

inline std::size_t s4b1_checked_product(std::size_t a, std::size_t b) {
    if (b != 0 && a > std::numeric_limits<std::size_t>::max() / b)
        throw std::invalid_argument("S4B1 dimensions overflow");
    return a * b;
}

inline std::size_t s4b1_checked_sum(std::size_t a,std::size_t b) {
    if(a>std::numeric_limits<std::size_t>::max()-b)
        throw std::invalid_argument("S4E source station cardinality overflow");
    return a+b;
}

inline S4B1AdmittedCase s4b1_admit_source_only(const S4B1Admission& in) {
    if (!in.original_source_admitted || !in.chronological_g14_admitted)
        throw std::invalid_argument("S4B1 requires genuine G19 source and G14 UTC authority");
    if (in.nx < 2 || in.ny < 2 || in.nz != 9 || in.hours == 0)
        throw std::invalid_argument("S4B1 unsupported grid/layers or empty UTC window");
    if (in.surface_stations == 0 || in.upper_stations == 0)
        throw std::invalid_argument("S4B1 requires >=1 real SS and >=1 real US independently");
    const auto cells = s4b1_checked_product(in.nx, in.ny);
    (void)s4b1_checked_product(cells, in.nz);
    const auto records = s4b1_checked_product(in.hours, std::size_t{45});
    // First reject impossible source array extents before a future
    // production path tries to allocate per-station/per-hour buffers.
    // 9 levels is the *currently selected* P6 path, not global CALMET NZ.
    const auto columns=s4b1_checked_sum(in.surface_stations,in.upper_stations);
    const auto station_hours=s4b1_checked_product(columns,in.hours);
    const auto profile_scalars=s4b1_checked_product(columns,in.nz);
    S4B1AdmittedCase accepted{in,cells,45,records,false};
    accepted.source_station_columns=columns;
    accepted.source_station_hour_slots=station_hours;
    accepted.wind_profile_scalars_per_component=profile_scalars;
    return accepted;
}

} // namespace cteas::calmet::p6g
