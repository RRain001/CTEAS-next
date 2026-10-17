#pragma once

// Grid-origin authority for the selected Hefei 2022 native P1/P2/P3 path.
// Units are KILOMETERS, represented as exactly three decimal digits (1 m).
// Coordinates from a more precise crop centre MUST NOT silently replace the
// historical grid.cmn authority.
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>

namespace cteas::reconstruction::geo {
inline double three_decimal_origin_km(const std::string& text) {
    std::size_t i=0;
    if(!text.empty()&&(text[0]=='+'||text[0]=='-'))++i;
    const auto whole_begin=i;
    while(i<text.size()&&text[i]>='0'&&text[i]<='9')++i;
    if(i==whole_begin||i>=text.size()||text[i]!='.'||text.size()!=i+4)
        throw std::invalid_argument(
            "GRID_ORIGIN_PRECISION: origin in km must have exactly 3 decimal digits");
    for(std::size_t k=i+1;k<text.size();++k)
        if(text[k]<'0'||text[k]>'9')
            throw std::invalid_argument(
                "GRID_ORIGIN_PRECISION: origin in km must have exactly 3 decimal digits");
    const double value=std::stod(text);
    if(!std::isfinite(value))
        throw std::invalid_argument("GRID_ORIGIN_PRECISION: nonfinite origin");
    return value;
}

// These CLI entrypoints currently serialize the frozen 50 x 50 Hefei 2022
// P1/P2 grid; the P1/P2→P3 adapter writes fixed legacy reference headers.
// A future new region needs an independently reviewed case-profile adapter
// (still with 3 decimal km origins), not a silent alternative origin here.
inline void require_frozen_hefei_origin_km(
        const std::string& east_km, const std::string& north_km) {
    const double east=three_decimal_origin_km(east_km);
    const double north=three_decimal_origin_km(north_km);
    if(east!=510.885||north!=3531.269)
        throw std::invalid_argument(
            "GRID_ORIGIN_CASE_MISMATCH: selected Hefei 2022 grid.cmn "
            "requires XREFKM=510.885 and YREFKM=3531.269 km");
}
} // namespace cteas::reconstruction::geo
