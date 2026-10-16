#pragma once
// G18B9: source-deck controls for the selected native DIAGNO CGAMMA
// hour. Keep IUPT and ZUPT from the SAME original met.inp, never
// hardcode 200 m or use a separately chosen upper station. This does
// not certify the complete native DIAGNO or whole G14/P6F path.
#include "cteas/p6/p6g_g18b8_gamma_grid.hpp"
#include "cteas/p6/p6g_g18b7_previous_ziconv.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>

namespace cteas::calmet::p6g {
struct G18B9OriginalGammaControls {
    int iupt=-1;
    int idiopt2=0;
    float zupt_m=0.f;
};
inline G18B9OriginalGammaControls g18b9_parse_original_gamma_controls(
    const std::string& metinp,std::size_t upper_count) {
    G18B9OriginalGammaControls out;
    out.iupt=g18b3_parse_original_iupt(metinp,upper_count);
    const auto mode=source_wind_normalize(source_wind_value(metinp,"IDIOPT2"));
    std::size_t used=0;
    try{out.idiopt2=std::stoi(mode,&used);}
    catch(const std::exception&) {
        throw std::invalid_argument("G18B9 source DIAGNO IDIOPT2 noninteger");
    }
    if(used!=mode.size()||out.idiopt2!=0)
        throw std::invalid_argument("G18B9 source GAMMA diagnostic-file branch unverified");
    const auto z=source_wind_normalize(source_wind_value(metinp,"ZUPT"));
    used=0;
    try{out.zupt_m=std::stof(z,&used);}
    catch(const std::exception&) {
        throw std::invalid_argument("G18B9 source ZUPT nonnumeric");
    }
    if(used!=z.size()||!std::isfinite(out.zupt_m)||out.zupt_m<=0.f)
        throw std::invalid_argument("G18B9 source ZUPT invalid");
    return out;
}
struct G18B9GammaSelection {
    G18B4CGammaPrepared upper;
    G18B8GammaGrid grid;
};
inline G18B9GammaSelection g18b9_selected_original_hour_gamma(
    const G18B4CGammaClock& clock,const MultiHourFrame& frame,
    const G18BUpperHour& upper,const G18B3UpperChoice& choice,
    const G18B9OriginalGammaControls& controls,bool explicitly_test_only) {
    if(!explicitly_test_only||choice.iupt!=controls.iupt)
        throw std::invalid_argument("G18B9 original IUPT across CGAMMA and GRID mismatched");
    const auto prepared=g18b7_prepare_source_grid_cgamma(
        clock,frame,upper,controls.zupt_m,true);
    const auto grid=g18b8_source_gamma_from_hour(
        frame,choice,prepared,true);
    return {prepared,grid};
}
} // namespace cteas::calmet::p6g
