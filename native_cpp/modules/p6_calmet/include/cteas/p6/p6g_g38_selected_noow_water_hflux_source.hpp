#pragma once
// S4-R0: *source-only* native HEATFX HFLUX input contract for the original
// selected no-overwater-observation WATER path. Deliberately does not
// weaken G18D3's accepted all-land admission or run any G14/G26 stage.
// Original source: CALMET 6.5.0 calmet.for blob 437f43bb7f0e51...
// HEATFX preserves the water QH slot; in the selected NOWSTA=0,
// ITWPROG=0 WATER neutral path WT=0, thus the preceding complete hour
// leaves the water buoyancy QH at zero. This is not generic COARE/WATERP.
#include "cteas/p6/p6g_g18d3_heat_source_defaults.hpp"
#include "cteas/p6/p6g_g18c1_avemix.hpp"
#include <cstddef>
#include <regex>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6g {
struct G38SelectedNoowWaterHfluxSource {
    G17CSelectedHeatInputs reference_heat;
    std::vector<std::size_t> original_water_cell_indices;
    // A source control record is NEVER implicit physics-stage authority.
    bool native_final_wind_ready=false;
    bool g14_g26_production_ready=false;
};
inline G38SelectedNoowWaterHfluxSource
g38_selected_noow_water_hflux_source_only(
    const GeoGrid& grid,const std::string& deck,bool explicit_reference_only) {
    if(!explicit_reference_only)
        throw std::invalid_argument("S4R0 original WATER HFLUX is test-only");
    const auto nx=static_cast<std::size_t>(grid.nx);
    const auto ny=static_cast<std::size_t>(grid.ny);
    if(grid.nx<2||grid.ny<2||grid.nx>400||grid.ny>400||
       grid.landuse.size()!=nx*ny||
       grid.iwat1!=50||grid.iwat2!=55)
        throw std::invalid_argument("S4R0 historical source water GEO mismatch");
    // Every control is read from the caller's ORIGINAL met.inp rather than
    // assigned by a test fixture, including the selected original WATER
    // versus WATERP branch and observed station thermal mode.
    if(g18c1_source_integer(deck,"NOWSTA")!=0||
       g18c1_source_integer(deck,"ITWPROG")!=0||
       g18c1_source_integer(deck,"ICOARE")!=10||
       g18c1_source_integer(deck,"IMIXH")!=1||
       g18c1_source_integer(deck,"NOOBS")!=0||
       g18c1_source_integer(deck,"IAVET")!=1||
       g18c1_source_integer(deck,"ISURFT")!=-1)
        throw std::invalid_argument("S4R0 original selected no-OW WATER controls differ");
    // READCF Group 10 can override BLOCK DATA. Until original-vendor
    // scientific parity for overrides, require the unchanged defaults.
    const std::regex override_key(
        R"(!\s*(HA1|HA2|HB1|HB2|HC1|HC2|HC3)\s*=)",
        std::regex_constants::icase);
    if(std::regex_search(deck,override_key))
        throw std::invalid_argument("S4R0 unsupported HFLUX override");
    G38SelectedNoowWaterHfluxSource out;
    for(std::size_t i=0;i<nx*ny;++i)
        if(grid.landuse[i]>=grid.iwat1&&grid.landuse[i]<=grid.iwat2)
            out.original_water_cell_indices.push_back(i);
    if(out.original_water_cell_indices.empty()||
       out.original_water_cell_indices.size()==nx*ny)
        throw std::invalid_argument("S4R0 expected mixed authentic land/water GEO");
    out.reference_heat.coefficients=g18d3_original_block_data_hflux();
    // A separate zero water prior slot is permitted ONLY by the frozen
    // NOWSTA=0 neutral path, where original WATER's WT and QH remain zero.
    // The existing P6E HEATFX kernel will skip water QH writes.
    out.reference_heat.initial_water_qh_wm2.assign(nx*ny,0.f);
    out.reference_heat.explicitly_test_only=true;
    return out;
}
} // namespace cteas::calmet::p6g
