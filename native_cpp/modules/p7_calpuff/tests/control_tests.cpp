#include "cteas/puff/control.hpp"

#include <cassert>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

using cteas::puff::ControlFile;
using cteas::puff::validate_selected_dry_inputs;

namespace {
const std::string synthetic = R"(
! METDAT = met.dat !
! METFM = 1 !  * METFM = 2 *
! METRUN = 0 !
! NSECDT = 3600 !
! NSPEC = 2 !
! NSE = 1 !
! NX = 50 !
! NY = 50 !
! NZ = 2 !
! ZFACE = 0, 20, 40 !
! MGAUSS = 1 !
! MSLUG = 0 !
! MDISP = 3 !
! MCHEM = 0 !
! MWET = 0 !
! IOUTU = 3 !
! CSPEC = H-3 !  !END!
! CSPEC = HE-3 ! !END!
)";

void require_failure(const std::string& text) {
    bool failed = false;
    try { (void)validate_selected_dry_inputs(ControlFile::parse(text)); }
    catch (const std::invalid_argument&) { failed = true; }
    assert(failed && "P7 fail-closed input test did not fail");
}

std::string replace_once(std::string text, std::string_view old_v, std::string_view new_v) {
    const auto where = text.find(old_v);
    assert(where != std::string::npos);
    text.replace(where, old_v.size(), new_v);
    return text;
}
} // namespace

int main(int argc, char** argv) {
    const auto c = ControlFile::parse(synthetic);
    const auto s = validate_selected_dry_inputs(c);
    assert(s.nx == 50 && s.ny == 50 && s.nz == 2);
    assert(s.zface_m.size() == 3 && s.zface_m[0] == 0.0 && s.zface_m[2] == 40.0);
    assert(c.values("CSPEC").size() == 2);
    assert(c.values("METFM").size() == 1);
    assert(c.values("METFM")[0] == "1"); // inactive *METFM* excluded
    require_failure(replace_once(synthetic, "! METFM = 1 !", "! METFM = 2 !"));
    require_failure(replace_once(synthetic, "! NSE = 1 !", "! NSE = 3 !"));
    require_failure(replace_once(synthetic, "! ZFACE = 0, 20, 40 !", "! ZFACE = 0, 40, 20 !"));
    require_failure(replace_once(synthetic, "! MWET = 0 !", "! MWET = 1 !"));
    require_failure(replace_once(synthetic, "! NZ = 2 !", "! NZ = 2 ! ! NZ = 2 !"));
    require_failure(replace_once(synthetic, "! NSECDT = 3600 !", "! NSECDT = 999 !"));
    require_failure(replace_once(synthetic, "! ZFACE = 0, 20, 40 !", "! ZFACE = 0, NaN, 40 !"));

    if (argc == 2) {
        const auto original = ControlFile::read_file(argv[1]);
        const auto selected = validate_selected_dry_inputs(original);
        assert(selected.nz == 9 && selected.zface_m.size() == 10);
        assert(selected.zface_m.front() == 0.0 && selected.zface_m.back() == 3000.0);
        assert(selected.species_count == 2 && selected.emitted_species_count == 1);
        assert(selected.output_units == 3);
        std::cout << "P7B_ORIGINAL_BUNDLED_CONTROL_SCOPED=PASS\n";
        std::cout << "NOTE: this bundled file is NOT frozen Hefei 2022 input\n";
    } else {
        std::cout << "P7B_SYNTHETIC_CONTROL_SCOPED=PASS\n";
    }
}
