#pragma once
// G19: one authoritative, original-file-backed G14 input assembly.
// Input provenance and physical-stage execution are deliberately separate:
// this does NOT certify a native 17-stage CALMET physics implementation.
// Each field is read from the caller's actual met.inp/GEO.DAT/SURF.DAT/
// ordered UP.DAT files, never reconstructed from CALMET.DAT or an oracle.
#include "cteas/p6/p6g_case_loader.hpp"
#include "cteas/p6/calmet_station_set.hpp"
#include "cteas/p6/read_surface_dynamic.hpp"
#include "cteas/p6/read_upper_dynamic.hpp"
#include "cteas/p6/p6g_g18c1_avemix.hpp"
#include "cteas/p6/p6g_g18d6_station_upper_assignment.hpp"
#include "cteas/p6/p6g_g18d3_heat_source_defaults.hpp"
#include "cteas/p6/p6g_g38_selected_noow_water_hflux_source.hpp"
#include "cteas/p6/p6g_g17b4_iavet_two_pass.hpp"
#include <cmath>
#include <fstream>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G19SourceFilePaths {
    std::string met_inp;
    std::string geo_dat;
    std::string surf_dat;
    // IMPORTANT: UP filenames must follow met.inp US1, US2, ... order.
    std::vector<std::string> ordered_up_dat;
};

// Structural source/clock contract: deliberately cannot be implicitly
// promoted to the G14/G26 physics-ready case. Water GEO is legal here.
struct G19SourceClockCase {
    std::string original_metinp;
    GeoGrid grid;
    StationSet stations;
    SurfaceSeries surface;
    std::vector<UpperSeries> upper;
    OriginalWindControls controls;
    [[nodiscard]] UnifiedMultistationHourlyScheduler make_scheduler() const {
        return {grid,stations,surface,upper,controls};
    }
};

// Physics-ready admission is a DISTINCT, stronger type. Every old
// g19_load_original_source_case() caller retains the same water HFLUX guard.
struct G19FileBackedCase : G19SourceClockCase {
    // Source-selected physical INPUTS, not completed source physics:
    // original SETCOM nearest US ordinal for every STHEOR surface site,
    // original READCF IAVET/AVETMP and default HFLUX coefficients.
    // The actual G14 physical execution authority remains separate.
    std::vector<std::size_t> stheor_upper_ordinal_for_surface;
    G17B4SurfaceControls surface_controls;
    G17CSelectedHeatInputs heat_inputs;
    // Explicit research-only source admission for original NOWSTA=0 WATER.
    // G26/G26B stages still require independent WATER physics admission;
    // passing this loader NEVER implies a completed native G14 hour.
    bool research_noow_water_source_only=false;
    std::vector<std::size_t> source_water_cells;
};

inline double g19_read_real_control(
    const std::string& deck,const char* name) {
    const auto val=source_wind_normalize(source_wind_value(deck,name));
    std::size_t used=0;
    double number=0.;
    try {number=std::stod(val,&used);}
    catch(const std::exception&) {
        throw std::invalid_argument(std::string("G19 invalid source real ")+name);
    }
    if(used!=val.size()||!std::isfinite(number))
        throw std::invalid_argument(std::string("G19 non-finite source real ")+name);
    return number;
}

inline GeoGridSpec g19_source_grid_spec(const std::string& original_deck) {
    const auto hemisphere=source_wind_normalize(
        source_wind_value(original_deck,"UTMHEM"));
    if(hemisphere!="N" && hemisphere!="S")
        throw std::invalid_argument("G19 original UTM hemisphere invalid");
    const auto nx=g18c1_source_integer(original_deck,"NX");
    const auto ny=g18c1_source_integer(original_deck,"NY");
    const auto zone=g18c1_source_integer(original_deck,"IUTMZN");
    const auto dx=g19_read_real_control(original_deck,"DGRIDKM");
    const auto origin_x=g19_read_real_control(original_deck,"XORIGKM");
    const auto origin_y=g19_read_real_control(original_deck,"YORIGKM");
    if(nx<2||ny<2||nx>400||ny>400||dx<=0.||
       zone<1||zone>60||
       g18c1_source_integer(original_deck,"NZ")!=9)
        throw std::invalid_argument(
            "G19 original grid outside validated G14 9-layer scope");
    return {nx,ny,zone,hemisphere.front(),origin_x,origin_y,dx};
}

// Literal READCF/GEO/SURF/UP and all modeled-hour brackets only.
// Never calls HEATFX, HFLUX, STHEOR or emits P6 meteorology.
inline G19SourceClockCase g19_load_source_clock_only(
    const G19SourceFilePaths& paths) {
    if(paths.met_inp.empty()||paths.geo_dat.empty()||
       paths.surf_dat.empty()||paths.ordered_up_dat.empty())
        throw std::invalid_argument("G19 missing original source file paths");
    std::ifstream met(paths.met_inp);
    if(!met)
        throw std::runtime_error("G19 original met.inp not found");
    G19SourceClockCase result;
    result.original_metinp.assign(
        std::istreambuf_iterator<char>(met),std::istreambuf_iterator<char>());
    if(result.original_metinp.empty())
        throw std::invalid_argument("G19 empty original met.inp");
    const auto ns=g18c1_source_integer(result.original_metinp,"NSSTA");
    const auto nu=g18c1_source_integer(result.original_metinp,"NUSTA");
    // Source-file admission is cardinality-generic: 1..N REAL SS and
    // 1..M REAL US. No arbitrary six/one-thousand-station cap. The
    // original-format input readers enforce finite station-hour resource
    // budgets, and the selected native physics kernels STILL require their
    // own independently accepted option/station combinations.
    if(ns<1||nu<1||
       paths.ordered_up_dat.size()!=static_cast<std::size_t>(nu))
        throw std::invalid_argument(
            "G19 requires >=1 source SS, >=1 source US and exactly one UP file per declared US");
    if(g18c1_source_integer(result.original_metinp,"IRTYPE")!=1||
       g18c1_source_integer(result.original_metinp,"IWFCOD")!=1||
       source_wind_normalize(source_wind_value(
           result.original_metinp,"LCALGRD"))!="T")
        throw std::invalid_argument(
            "G19 original CALMET output mode not accepted by selected P6F");
    const auto spec=g19_source_grid_spec(result.original_metinp);
    // G14B already owns the frozen original READCF geometric contract.
    // Reuse that exact parser/validator here instead of permitting two
    // independently evolving PMAP/DATUM/UTM/ZFACE/NZ/count definitions.
    validate_original_calmet_deck_grid(
        result.original_metinp,spec,ns,nu);
    result.controls=parse_original_wind_controls(result.original_metinp);
    result.grid=read_geo_dynamic(paths.geo_dat,spec);
    result.stations=original_calmet_multi_station_deck(
        result.original_metinp,result.grid.xorigin_km,
        result.grid.yorigin_km,ns,nu);
    std::vector<int> ss,us;
    ss.reserve(result.stations.surface.size());
    us.reserve(result.stations.upper.size());
    for(const auto& st:result.stations.surface) ss.push_back(st.id);
    for(const auto& st:result.stations.upper) us.push_back(st.id);
    result.surface=read_surface_dynamic(paths.surf_dat,ss);
    // A real READ62 annual UP archive may extend beyond the selected met.inp
    // modeled interval. Accept only a strictly increasing, bounded trailing
    // archive in G19; the existing strict standalone reader stays unchanged.
    result.upper=read_upper_station_set(paths.ordered_up_dat,us,100000,true);

    // Validate real ordered source hours independently of any thermal,
    // water, or station-to-grid PHYSICS readiness assertion.
    const auto input_clock=result.make_scheduler();
    if(input_clock.planned_hours()!=result.surface.hourly.size()||
       !input_clock.has_original_controls())
        throw std::logic_error(
            "G19 source-only clock authority rejected actual source interval");
    return result;
}

// Existing production/test-selected admission, unchanged physical branch:
// source-only case is NOT implicitly convertible to G19FileBackedCase.
inline G19FileBackedCase g19_load_original_source_case(
    const G19SourceFilePaths& paths,
    bool explicit_noow_water_source_research_only=false) {
    auto input=g19_load_source_clock_only(paths);
    G19FileBackedCase result;
    static_cast<G19SourceClockCase&>(result)=std::move(input);

    // G19B source science admission. The current selected DIAGNO and
    // P6E kernels are verified ONLY for the original nearest-US IUPT=-1,
    // two-pass IAVET=1, observed thermal fields and default HFLUX path.
    // Preserve original REAL*4 DIAGI station-to-cell/SETCOM NEARU mapping,
    // reject out-of-GEO or water SS stations BEFORE any G14 hour begins.
    // Other CALMET branches must earn their own Fortran source parity;
    // never substitute nearest stations or synthetic heat constants.
    result.stheor_upper_ordinal_for_surface=
        g18d6_station_uppers_from_source_setcom(
            result.grid,result.stations,result.original_metinp,true);
    if(g18c1_source_integer(result.original_metinp,"ISURFT")!=-1)
        throw std::invalid_argument(
            "G19B source SURFVAR requires accepted ISURFT=-1 observed path");
    result.surface_controls=
        parse_g17b4_surface_controls(result.original_metinp);
    if(explicit_noow_water_source_research_only) {
        // G38 pins original HFLUX defaults and neutral-water zero-QH
        // source mode. It does NOT issue permission to compute G26/G26B.
        const auto source_water=g38_selected_noow_water_hflux_source_only(
            result.grid,result.original_metinp,true);
        result.heat_inputs=source_water.reference_heat;
        result.source_water_cells=source_water.original_water_cell_indices;
        result.research_noow_water_source_only=true;
    } else {
        result.heat_inputs=g18d3_source_hflux_inputs(
            result.grid,result.original_metinp,false);
    }
    if(result.stheor_upper_ordinal_for_surface.size()!=
       result.stations.surface.size())
        throw std::logic_error("G19B missing original STHEOR nearest-US station mapping");

    // Construct the real G14 source authority NOW, not after the caller
    // begins physics. This requires every hour to have every US bracket,
    // checks clock/order continuity, and forbids stale/missing source data.
    const auto validation=result.make_scheduler();
    if(validation.planned_hours()!=result.surface.hourly.size()||
       !validation.has_original_controls())
        throw std::logic_error(
            "G19 file-backed G14 scheduler rejected source hour identity");
    return result;
}
} // namespace cteas::calmet::p6g
