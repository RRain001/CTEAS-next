// P7V contract test: the ported advection units against hand-computed vendor
// semantics, plus every fail-closed refusal.
#include "cteas/puff/advection.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

int failures = 0;
int checks = 0;

void check(bool condition, const std::string& what) {
    ++checks;
    if (!condition) {
        ++failures;
        std::cerr << "FAIL: " << what << '\n';
    }
}

void check_close(double got, double want, double tolerance, const std::string& what) {
    ++checks;
    if (!(std::abs(got - want) <= tolerance)) {
        ++failures;
        std::cerr << "FAIL: " << what << " got=" << got << " want=" << want << '\n';
    }
}

template <typename Callable>
void check_refuses(Callable&& callable, const std::string& what) {
    ++checks;
    try {
        callable();
        ++failures;
        std::cerr << "FAIL: " << what << " did not refuse\n";
    } catch (const std::invalid_argument&) {
        // expected
    }
}

} // namespace

int main() {
    using namespace cteas::puff;
    const std::vector<double> faces{0.0, 50.0, 100.0, 200.0, 300.0, 500.0};

    // ZFIND: below the first face, exact face hits, inside and above the top.
    check(find_layer(-5.0, faces) == 1, "zfind below the first face");
    check(find_layer(0.0, faces) == 1, "zfind at the first face");
    check(find_layer(49.999, faces) == 1, "zfind just below the second face");
    check(find_layer(50.0, faces) == 2, "zfind at a face boundary takes the layer above");
    check(find_layer(120.0, faces) == 3, "zfind inside the third layer");
    check(find_layer(499.999, faces) == 5, "zfind just below the top face");
    check(find_layer(500.0, faces) == 5, "zfind at the top face");
    check(find_layer(900.0, faces) == 5, "zfind above the top face returns NZ");

    // ADVWND: the vendor's depth-weighted average over the puff's layers.
    LayerAverageInputs average;
    average.u_ms = {1.0, 2.0, 3.0, 4.0, 5.0};
    average.v_ms = {0.5, 1.5, 2.5, 3.5, 4.5};
    average.face_heights_m = faces;
    average.z_bottom_m = 40.0;
    average.z_top_m = 260.0;
    auto wind = layer_average_wind(average);
    check_close(wind.u_ms, 650.0 / 220.0, 1.0e-4, "advwnd u over 40-260 m");
    check_close(wind.v_ms, 540.0 / 220.0, 1.0e-4, "advwnd v over 40-260 m");

    // Single layer: the vendor copies the layer's wind.
    average.z_bottom_m = 60.0;
    average.z_top_m = 90.0;
    wind = layer_average_wind(average);
    check_close(wind.u_ms, 2.0, 1.0e-9, "advwnd single layer u");
    check_close(wind.v_ms, 1.5, 1.0e-9, "advwnd single layer v");

    // Depths outside the met field are clamped to the face heights.
    average.z_bottom_m = -10.0;
    average.z_top_m = 700.0;
    wind = layer_average_wind(average);
    check_close(wind.u_ms, 3.7, 1.0e-4, "advwnd clamped full column u");
    check_close(wind.v_ms, 3.2, 1.0e-4, "advwnd clamped full column v");

    // ADVECT: METFM=1 copies the cell profile and calls ADVWND.
    AdvectiveWindInputs advective;
    advective.met_format = 1;
    advective.u_profile_ms = average.u_ms;
    advective.v_profile_ms = average.v_ms;
    advective.face_heights_m = faces;
    advective.z_bottom_m = 40.0;
    advective.z_top_m = 260.0;
    const auto advected = advective_wind(advective);
    check_close(advected.u_ms, 650.0 / 220.0, 1.0e-4, "advect metfm=1 u");
    check_close(advected.v_ms, 540.0 / 220.0, 1.0e-4, "advect metfm=1 v");
    for (int format : {2, 3, 4, 5}) {
        advective.met_format = format;
        check_refuses([&] { (void)advective_wind(advective); },
                      "advect refuses METFM " + std::to_string(format));
    }

    // PUFFDZ: the Gaussian branch and its lid caps.
    PuffExtentInputs extent;
    extent.puff_code = 1;
    extent.puff = true;
    extent.stability_class = 4;
    extent.puff_height_m = 70.8;
    extent.mixing_height_m = 231.0;
    extent.sigma_z_begin_m = 5.0;
    extent.previous_mixing_height_m = 231.0;
    extent.maximum_mixing_height_m = 231.0;
    auto puff = puff_extent(extent);
    check_close(puff.z_top_m, 75.8, 1.0e-4, "puffdz gaussian ztop");
    check_close(puff.z_bottom_m, 65.8, 1.0e-4, "puffdz gaussian zbot");

    // The vendor caps ZTOP only when the puff's height is below the level it
    // caps against: DPBL first, then ZIOLD, then ZIMAX.
    extent.mixing_height_m = 72.0;
    puff = puff_extent(extent);
    check_close(puff.z_top_m, 72.0, 1.0e-4, "puffdz caps ztop at DPBL");
    extent.mixing_height_m = 50.0;
    extent.previous_mixing_height_m = 72.0;
    puff = puff_extent(extent);
    check_close(puff.z_top_m, 72.0, 1.0e-4, "puffdz caps ztop at ZIOLD");
    extent.previous_mixing_height_m = 50.0;
    extent.maximum_mixing_height_m = 72.0;
    puff = puff_extent(extent);
    check_close(puff.z_top_m, 72.0, 1.0e-4, "puffdz caps ztop at ZIMAX");
    extent.stability_class = 5;
    puff = puff_extent(extent);
    check_close(puff.z_top_m, 75.8, 1.0e-4, "puffdz skips the caps for ISTAB > 4");
    extent.puff_code = 3;
    puff = puff_extent(extent);
    check_close(puff.z_top_m, 75.8, 1.0e-4, "puffdz skips the caps for ICODE 3");
    extent.maximum_mixing_height_m = 231.0;
    extent.previous_mixing_height_m = 231.0;
    extent.mixing_height_m = 231.0;
    extent.puff_code = 1;
    extent.stability_class = 4;
    extent.puff_height_m = 2.0;
    puff = puff_extent(extent);
    check_close(puff.z_bottom_m, 0.0, 1.0e-9, "puffdz clamps zbot at the ground");

    // A slug averages the two sigmas.
    extent.puff = false;
    extent.puff_height_m = 70.8;
    extent.sigma_z_begin_m = 5.0;
    extent.sigma_z_end_m = 9.0;
    puff = puff_extent(extent);
    check_close(puff.z_top_m, 77.8, 1.0e-4, "puffdz slug ztop uses both sigmas");
    check_close(puff.z_bottom_m, 63.8, 1.0e-4, "puffdz slug zbot uses both sigmas");
    extent.puff = true;

    // Uniformly mixed branches.
    extent.puff_code = 2;
    extent.maximum_mixing_height_m = 400.0;
    extent.mixing_height_m = 231.0;
    puff = puff_extent(extent);
    check_close(puff.z_top_m, 400.0, 1.0e-4, "puffdz ICODE=2 ztop is ZIMAX");
    check_close(puff.z_bottom_m, 0.0, 1.0e-9, "puffdz ICODE=2 zbot is the ground");
    extent.puff_code = 4;
    extent.layer_bottom_m = 100.0;
    extent.layer_top_m = 200.0;
    puff = puff_extent(extent);
    check_close(puff.z_top_m, 200.0, 1.0e-4, "puffdz ICODE=4 ztop is ZFACE(ILAYER+1)");
    check_close(puff.z_bottom_m, 100.0, 1.0e-4, "puffdz ICODE=4 zbot is ZFACE(ILAYER)");

    // The two-layer structure revises ZBOT only when the upper mass is large.
    extent.puff_code = 6;
    extent.previous_mixing_height_m = 231.0;
    extent.maximum_mixing_height_m = 231.0;
    extent.mixed_layer_mass = {1.0, 1.0};
    extent.above_layer_mass = {3.0, 3.0};
    puff = puff_extent(extent);
    check_close(puff.z_bottom_m, 231.0 * (1.0 - 2.0 * 2.0 / 6.0), 1.0e-4, "puffdz ICODE=6 revision");
    extent.above_layer_mass = {1.0, 1.0};
    puff = puff_extent(extent);
    check_close(puff.z_bottom_m, 0.0, 1.0e-9, "puffdz ICODE=6 keeps the ground when 2QM >= QU");

    // Fail-closed refusals.
    extent.puff_code = 8;
    check_refuses([&] { (void)puff_extent(extent); }, "puffdz refuses an invalid ICODE");
    extent.puff_code = 2;
    extent.stability_class = 7;
    check_refuses([&] { (void)puff_extent(extent); }, "puffdz refuses ISTAB 7");
    extent.stability_class = 4;
    extent.puff_code = 6;
    extent.above_layer_mass = {1.0};
    check_refuses([&] { (void)puff_extent(extent); }, "puffdz refuses mismatched mass arrays");
    extent.above_layer_mass = {3.0, 3.0};
    extent.mixed_layer_mass = {1.0, 1.0};
    extent.puff_code = 6;
    extent.previous_mixing_height_m = 1500.0;
    extent.maximum_mixing_height_m = 231.0;
    check_refuses([&] { (void)puff_extent(extent); },
                  "puffdz refuses a revised zbot above ztop");
    average.u_ms = {1.0};
    check_refuses([&] { (void)layer_average_wind(average); },
                  "advwnd refuses a short profile");
    check_refuses([&] { (void)find_layer(1.0, {0.0}); }, "zfind refuses a single face height");
    check_refuses([&] { (void)find_layer(std::nan(""), faces); }, "zfind refuses a NaN height");

    std::cout << "P7V_ADVECTION_CONTRACT=" << (failures == 0 ? "PASS" : "FAIL")
              << " CHECKS=" << checks << " FAILURES=" << failures << '\n';
    return failures == 0 ? 0 : 1;
}
