#include "cteas/puff/transport.hpp"
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <sstream>
#include <string>
#include <vector>
namespace cteas::puff {
ReplaySummary replay_calmet_winds(const std::string& met_file,
                                  const SelectedDryInputs& inputs,
                                  const PointRelease& point,
                                  bool require_historical_2023) {
    // Two-pass decode is intentional until Calmet21Reader exposes
    // the header before streaming hourly fields. Both passes apply
    // the same strict original time continuity checks.
    const auto metadata=Calmet21Reader::read(met_file);
    if (metadata.header.nx!=inputs.nx || metadata.header.ny!=inputs.ny ||
        metadata.header.nz!=inputs.nz || inputs.time_step_s<=0 ||
        3600%inputs.time_step_s!=0)
        throw std::invalid_argument("P7C selected source/wind geometry or time mismatch");
    if (require_historical_2023) {
        if (metadata.header.dx_m!=1000.0F || metadata.intervals!=119 ||
            metadata.first_begin.year!=2023 ||
            metadata.first_begin.unix_seconds!=1672531200LL ||
            metadata.final_end.unix_seconds!=1672959600LL)
            {
                std::ostringstream details;
                details<<"P7C original 2023 gate mismatch: dx="<<metadata.header.dx_m
                       <<" intervals="<<metadata.intervals
                       <<" begin="<<metadata.first_begin.year<<"/"<<metadata.first_begin.julian_day
                       <<"/"<<metadata.first_begin.hour
                       <<" end="<<metadata.final_end.year<<"/"<<metadata.final_end.julian_day
                       <<"/"<<metadata.final_end.hour;
                throw std::invalid_argument(details.str());
            }
    }
    WindField wind;
    wind.nx=metadata.header.nx;
    wind.ny=metadata.header.ny;
    wind.nz=metadata.header.nz;
    wind.origin_x_m=metadata.header.origin_x_m;
    wind.origin_y_m=metadata.header.origin_y_m;
    wind.spacing_m=metadata.header.dx_m;
    wind.level_m=level_centers_from_zface(inputs.zface_m);
    const std::size_t n=static_cast<std::size_t>(wind.nx)*
                         static_cast<std::size_t>(wind.ny)*
                         static_cast<std::size_t>(wind.nz);
    const float unset=std::numeric_limits<float>::quiet_NaN();
    wind.u.assign(n,unset);wind.v.assign(n,unset);wind.w.assign(n,unset);
    PuffTransport puffs(point.rate_per_s.size());
    std::size_t hours=0,steps=0;
    const auto second=Calmet21Reader::read(met_file,[&](const Calmet21Field& field) {
        if (field.label=="U-LEV  1") {
            std::fill(wind.u.begin(),wind.u.end(),unset);
            std::fill(wind.v.begin(),wind.v.end(),unset);
            std::fill(wind.w.begin(),wind.w.end(),unset);
        }
        char component='\0';
        if (field.label.rfind("U-LEV",0)==0) component='U';
        else if (field.label.rfind("V-LEV",0)==0) component='V';
        else if (field.label.rfind("WFACE",0)==0) component='W';
        if (component!='\0') {
            const auto level=std::stoi(field.label.substr(5));
            if (level<1 || level>wind.nz ||
                field.real_values.size()!=static_cast<std::size_t>(wind.nx*wind.ny))
                throw std::invalid_argument("P7C bad original wind layer or XY extent");
            auto& target=(component=='U'?wind.u:(component=='V'?wind.v:wind.w));
            const std::size_t offset=static_cast<std::size_t>(level-1)*
                  static_cast<std::size_t>(wind.nx)*static_cast<std::size_t>(wind.ny);
            std::copy(field.real_values.begin(),field.real_values.end(),
                      target.begin()+static_cast<std::ptrdiff_t>(offset));
        }
        if (field.label!="IRH") return;
        ++hours;
        wind.validate();
        for (int nstep=0;nstep<3600/inputs.time_step_s;++nstep) {
            puffs.emit(point,inputs.time_step_s);
            puffs.advect(wind,inputs.time_step_s);
            ++steps;
        }
    },false);
    if (second.intervals!=metadata.intervals || hours!=metadata.intervals ||
        steps!=hours*static_cast<std::size_t>(3600/inputs.time_step_s))
        throw std::runtime_error("P7C original CALMET replay step count mismatch");
    ReplaySummary result;
    result.met=metadata;
    result.mass=puffs.balance();
    result.wind_hours=hours;
    result.substeps=steps;
    return result;
}
} // namespace cteas::puff
