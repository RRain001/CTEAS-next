#pragma once
// Native P6F *computed* WATER USTAR/EL become the next G14 hour's
// typed history; no original/vendor CALMET output may enter this path.
#include "cteas/p6/p6g_g66_noaa_hour3_g22_trace.hpp"
#include "cteas/p6f/calmet_dat21_writer.hpp"
#include <chrono>
#include <stdexcept>
#include <string>
#include <vector>
namespace cteas::calmet::p6g {
// Decode serialization ONLY at the G65/P6F boundary. G26A and G66 see
// typed native prior physical state, never depend on P6F writer linkage.
inline G66NativeHour2WaterState g65_native_hour2_water_from_p6f(
    const cteas::p6f::Calmet21File& native,
    std::chrono::sys_seconds expected_end) {
    if(native.hourly.size()!=45)
        throw std::invalid_argument("G65 native hour2 P6F field count");
    const auto field=[&](const std::string& label)
        ->const std::vector<float>& {
        const cteas::p6f::Calmet21Field* found=nullptr;
        for(const auto& f:native.hourly)
            if(f.label==label) {
                if(found)throw std::invalid_argument(
                    "G65 duplicate native P6F water field");
                found=&f;
            }
        if(!found||found->integer||found->real_values.size()!=6970||
           cteas::p6f::instant_seconds(found->end)!=
               expected_end.time_since_epoch().count()||
           cteas::p6f::instant_seconds(found->begin)!=
               (expected_end-std::chrono::hours{1})
                   .time_since_epoch().count())
            throw std::invalid_argument(
                "G65 native P6F water field clock/shape invalid");
        return found->real_values;
    };
    G66NativeHour2WaterState prior;
    prior.begin=expected_end-std::chrono::hours{1};
    prior.end=expected_end;
    prior.ustar_mps=field("USTAR   ");
    prior.el_m=field("EL      ");
    prior.explicitly_native_p6f_origin=true;
    return prior;
}

} // namespace cteas::calmet::p6g
