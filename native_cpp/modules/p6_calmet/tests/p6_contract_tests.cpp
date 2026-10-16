#include "cteas/p6/calmet_contract.hpp"
#include <cmath>
#include <cstddef>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace p = cteas::calmet::p6;

void expect(bool state, const char* message) {
    if (!state) throw std::runtime_error(message);
}
void throws(const std::function<void()>& action, const char* message) {
    bool caught = false;
    try {
        action();
    } catch (const p::ContractError&) {
        caught = true;
    }
    expect(caught, message);
}
p::Geometry example() {
    p::Geometry g;
    g.nx = 50;
    g.ny = 50;
    g.utm_zone = 50;
    g.northern_hemisphere = true;
    g.datum = "WGS-84";
    g.southwest_x_km = 510.8846439571;
    g.southwest_y_km = 3531.2689269678;
    g.spacing_km = 0.1;
    g.zfaces_agl_m = {0,20,40,80,160,320,640,1200,2000,3000};
    return g;
}
int main() {
    try {
        auto g = example();
        g.validate_hefei_100m();
        expect(g.layer_count() == 9, "wrong number of layers");
        expect(g.grid_index(0,0) == 0, "first cell layout");
        expect(g.grid_index(49,0) == 49, "i must be fastest");
        expect(g.grid_index(0,1) == 50, "j layout");
        expect(g.layer_index(49,49,8) == 22499, "last layer cell index");
        expect(std::abs(g.cell_center_x_km(0)-510.9346439571)<1e-10,"wrong center");
        expect(std::abs(g.cell_center_y_km(49)-3536.2189269678)<1e-10,"wrong center");
        throws([&]{ (void)g.grid_index(50,0); }, "out-of-grid did not fail");
        throws([&]{ (void)g.layer_index(0,0,9); }, "out-of-layer did not fail");

        auto bad = g;
        bad.nx = 100;
        throws([&]{bad.validate_hefei_100m();},"unsupported grid accepted");
        bad = g;
        bad.spacing_km = 1.0;
        throws([&]{bad.validate_hefei_100m();},"unsupported resolution accepted");
        bad = g;
        bad.utm_zone = 49;
        throws([&]{bad.validate_hefei_100m();},"wrong UTM zone accepted");
        bad = g;
        bad.zfaces_agl_m[2] = 20;
        throws([&]{bad.validate_hefei_100m();},"duplicate or wrong ZFACE accepted");

        p::MaskedField3D wind(g);
        expect(wind.size()==22500,"wrong 3D storage");
        expect(!wind.get(3,4,5).valid,"missing must remain explicitly missing");
        wind.set(3,4,5,p::Sample::observed(0.0));
        expect(wind.get(3,4,5).valid&&wind.get(3,4,5).value==0.0,
               "valid calm wind was confused with missing");
        expect(!wind.get(3,5,5).valid,"neighboring mask corrupted");
        throws([&]{wind.set(0,0,0,p::Sample::observed(
                std::numeric_limits<double>::quiet_NaN()));},
               "nonfinite valid value accepted");
        // Negative terrain MSL can be legitimate; no arbitrary elevation clipping.
        wind.set(0,0,0,p::Sample::observed(-5.0));
        expect(wind.get(0,0,0).value==-5.0,"negative finite numeric value lost");
        bad = g;
        bad.nx = -1;
        throws([&]{p::MaskedField3D should_fail(bad);(void)should_fail;},
               "allocated unvalidated shape");

        p::Window window{{2022,1,1,0,0,0},{2022,1,6,23,0,0}};
        expect(window.nominal_label_count()==144,"nominal 144 hourly labels");
        window.reference_timezone="UTC+0800";
        throws([&]{(void)window.nominal_label_count();},
               "time-zone implicitly shifted");
        window.reference_timezone="UTC+0000";
        window.model_seconds=1800;
        throws([&]{(void)window.nominal_label_count();},
               "subhourly unsupported was silently accepted");
        window.model_seconds=3600;
        window.last_label={2022,2,30,23,0,0};
        throws([&]{(void)window.nominal_label_count();},"invalid date accepted");
        window.last_label={2021,12,31,23,0,0};
        throws([&]{(void)window.nominal_label_count();},"negative window accepted");

        p::ObservationModes modes;
        modes.validate_selected_path();
        modes.irtype=0;
        throws([&]{modes.validate_selected_path();},
               "wind-only IRTYPE erroneously treated as CALPUFF ready");
        modes.irtype=1;
        modes.iprog=14;
        throws([&]{modes.validate_selected_path();},
               "prognostic mode silently accepted");
        modes.iprog=0;
        modes.surface_format=1;
        throws([&]{modes.validate_selected_path();},
               "unverified meteorological binary format silently accepted");

        p::ForcingInventory inventory;
        expect(!inventory.can_attempt_full_reference_run(),
               "missing met data incorrectly marked Fortran-reference ready");
        throws([&]{inventory.require_full_reference_ready();},
               "missing precip/met gating not enforced");
        inventory.geo_dat_p3_verified=true;
        inventory.surf_dat_p5_fortran_verified=true;
        inventory.upper_dat_p4_fortran_verified=true;
        inventory.n_surface_stations=1;
        inventory.n_upper_stations=1;
        expect(!inventory.can_attempt_full_reference_run(),
               "precipitation mode not explicitly decided");
        inventory.precipitation_mode_explicitly_confirmed=true;
        expect(inventory.can_attempt_full_reference_run(),
               "valid P6 original NPSTA=0 reference should be runnable");
        expect(!inventory.can_claim_wet_deposition_forcing(),
               "dry-only P6 original incorrectly qualified for HTO wet deposition");
        throws([&]{inventory.require_wet_deposition_forcing();},
               "NPSTA=0 would silently validate wet deposition");
        inventory.n_precip_stations=1;
        expect(!inventory.can_attempt_full_reference_run(),
               "unverified rainfall file incorrectly qualifies original P6");
        inventory.precipitation_input_verified=true;
        expect(inventory.can_attempt_full_reference_run() &&
               inventory.can_claim_wet_deposition_forcing(),
               "verified precipitation case incorrectly rejected");
        inventory.require_full_reference_ready();
        inventory.require_wet_deposition_forcing();

        std::cout<<"PASS P6A_CONTRACTS_ONLY (no wind or micrometeorology physics claimed)\n";
        return 0;
    } catch(const std::exception& ex) {
        std::cerr<<"P6A_FAIL "<<ex.what()<<'\n';
        return 1;
    }
}
