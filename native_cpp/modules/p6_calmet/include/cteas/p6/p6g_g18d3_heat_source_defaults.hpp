#pragma once
// G18D3: Original CALMET 6.5.0 BLOCK DATA HFLUX defaults, confirmed
// against the *literal* unmodified vendor Fortran DATA statements in CI.
// Previous G17C fixtures used HC1=HC2=0, HC3P1=1; those are NOT actual
// source HEATFX values and can bias QH/ELUSTR/ZI/TEMP3D.
// Fail closed if a different met.inp explicitly overrides these 7 keys;
// production G14 still requires the full source-accepted physical chain.
#include "cteas/p6/p6g_g17c_iavet1_heat_handoff.hpp"
#include <cmath>
#include <cstddef>
#include <regex>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6g {
inline G12HeatCoefficients g18d3_original_block_data_hflux() {
    // Original calmet.for BLOCK DATA:
    // DATA HA1/990./,HA2/-30./,HB1/-0.75/,HB2/3.4/
    // DATA HC1/5.31E-13/,HC2/60./,HC3/0.12/
    // Original SETCOM: HC3P1=HC3+1.0 (REAL*4).
    const float hc3=0.12f;
    return {990.f,-30.f,-0.75f,3.4f,5.31e-13f,60.f,hc3+1.f};
}
inline G17CSelectedHeatInputs g18d3_source_hflux_inputs(
    const GeoGrid& grid,const std::string& original_metinp,
    bool explicitly_test_only) {
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    if(nx<2||ny<2||nx>400||ny>400||
       !std::isfinite(grid.grid_km)||grid.grid_km<=0.f||
       grid.landuse.size()!=nx*ny)
        throw std::invalid_argument("G18D3 missing source GEO thermal dimensions");
    // READCF Group 10 permits replacement of BLOCK DATA HFLUX constants.
    // This selected version supports pinned default-only decks, never a
    // silent return to the old nonphysical synthetic HC1/HC2 zero values.
    const std::regex explicit_override(
        R"(!\s*(HA1|HA2|HB1|HB2|HC1|HC2|HC3)\s*=)",
        std::regex_constants::icase);
    if(std::regex_search(original_metinp,explicit_override))
        throw std::invalid_argument("G18D3 overridden HFLUX control needs distinct READCF parity");
    for(int land:grid.landuse)
        if(land>=grid.iwat1&&land<=grid.iwat2)
            throw std::invalid_argument("G18D3 all-land HFLUX default branch only");
    G17CSelectedHeatInputs result;
    result.coefficients=g18d3_original_block_data_hflux();
    // Original HEATFX on land does not consume QH's prior-water value.
    // Still maintain correctly sized scratch input for the frozen kernel.
    result.initial_water_qh_wm2.assign(nx*ny,0.f);
    result.explicitly_test_only=explicitly_test_only;
    return result;
}
} // namespace cteas::calmet::p6g
