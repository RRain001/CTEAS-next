#pragma once

#include "cteas/puff/control.hpp"

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace cteas::puff {

// P7D: CALPUFF 7.2.1 dispersion coefficients for MDISP = 3.
//
// MDISP = 3 uses Pasquill-Gifford-Turner rural curves (ISC 6-8 multi-segment
// approximation, SIGTY/SIGTZ with IDOPT = 3 and IRUS = 0) and McElroy-Pooler /
// Briggs urban curves (IRUS = 1). Every table, formula and intermediate
// precision below is transcribed from the unmodified vendor source
// engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for (BLOCK DATA, SIGSET,
// SIGTY, SIGTZ, XVY, XVZ) and is cross-checked against that file by CTest.
//
// Only MDISP = 3 is reconstructed; any other value fails closed. The original
// keeps its dispersion state in REAL*4, so the reconstruction deliberately
// keeps single precision internally and converts to double only in the
// reported results, which is what makes tight original-source parity possible.
//
// Not yet reconstructed (see docs/reconstruction_cpp/P7_EXECUTION_LEDGER.md):
// the SIGMA() nearest-known-sigma restart wrapper, HEFTRAN slug geometry, and
// the gridded roughness plumbing (MROUGH = 1); MDISP 1, 2, 4 and 5.

using DispersionReal = float;

// Selected dispersion option (control-file MDISP). Fail closed on anything
// that is not the reconstructed option.
enum class DispersionOption { gaussian_pg_rural_mp_urban = 3 };

[[nodiscard]] DispersionOption require_supported_dispersion_option(int mdisp);

// Per-puff dispersion state equivalent to the vendor /CSIGMA/ block plus the
// setup factors computed by SIGSET.
struct DispersionEnvironment {
    int stability_class = 0;                  // KSTABS, PGT 1..6
    bool urban = false;                       // IRUS
    double transport_speed_ms = 0.0;          // UAVGS, must be > 0
    double sigma_y_heffter_m = 550.0;         // SYH (control SYTDEP, vendor default 550 m)
    double averaging_factor = 1.0;            // AVEFAC = (AVET/PGTIME)**0.2
    double sigma_y_roughness = 1.0;           // YZ0FAC
    double sigma_z_a_roughness = 1.0;         // AZ0FAC
    double sigma_z_b_term = -1000.0;          // BZ0TRM; <= -999 disables the adjustment
    bool heffter_sigma_z = false;             // MHFTSZS (control MHFTSZ, vendor default 0)
};

// Increment of one dispersion step. The original resets small negative
// increments to zero and halts beyond -1 s / -1e-3 km; both behaviours are
// reproduced and reported, never applied silently.
struct DispersionIncrement {
    double dx_km = 0.0;
    double dt_s = 0.0;
};

struct DispersionStep {
    double sigma_y_m = 0.0;
    double sigma_z_m = 0.0;
    double virtual_time_y_s = 0.0;
    double virtual_distance_y_km = 0.0;
    double virtual_time_z_s = 0.0;
    double virtual_distance_z_km = 0.0;
    double heffter_transition_time_y_s = 0.0; // THFTY for the current environment
    bool stability_class_conditioned = false; // KSTABS > 6 conditioned to 6, as SETCSIG
    bool y_increment_reset = false;
    bool z_increment_reset = false;
    bool heffter_y_active = false;            // Heffter growth used for sigma-y
    bool heffter_z_active = false;            // Heffter growth used for sigma-z
    bool urban_sigma_z_capped = false;        // final sigma-z held at the 5000 m ISC cap
};

// SIGSET roughness adjustment of the rural PG curves (active for MROUGH = 1).
struct RoughnessAdjustment {
    double sigma_y_factor = 1.0;     // YZ0FAC = (z0/0.03)**0.2
    double sigma_z_a_factor = 1.0;   // AZ0FAC = 1000**BZ0TRM * 1.585 * z0**0.1301
    double sigma_z_b_term = -1000.0; // BZ0TRM = 0.0777 + 0.0215*ln(z0)
};

// Fail closed for non-positive or non-finite roughness length.
[[nodiscard]] RoughnessAdjustment roughness_adjustment(double z0_m);

// Vendor BLOCK DATA /CSIGMA/ tables and the SIGSET-derived sigma-z segment
// junctions. Exposed for the source-anchor CTest, not for configuration.
struct DispersionTables {
    static constexpr std::size_t levels = 6;
    static constexpr std::size_t segments = 10;
    std::array<DispersionReal, levels> urban_y_coefficient{};   // AYURB
    std::array<DispersionReal, levels> urban_y_inverse_length{}; // XIYURB
    std::array<DispersionReal, levels> urban_z_coefficient{};   // AZURB
    std::array<DispersionReal, levels> urban_z_inverse_length{}; // XIZURB
    std::array<int, levels> rural_z_segments{};                 // NZBRUR
    std::array<std::array<DispersionReal, levels>, segments> rural_z_junction_km{}; // XZBRUR
    std::array<std::array<DispersionReal, levels>, segments> rural_z_coefficient{};  // AZRUR
    std::array<std::array<DispersionReal, levels>, segments> rural_z_exponent{};     // BZRUR
    std::array<DispersionReal, levels> rural_y_coefficient{};  // ISC C(Y)
    std::array<DispersionReal, levels> rural_y_exponent{};     // ISC D(Y)
    // MESOPUFF II sigma-y curves: used by SIGTY as the second initial guess
    // for the rural pseudo-distance inversion even for IDOPTYS = 3.
    std::array<DispersionReal, levels> mesopuff_y_coefficient{}; // AYPGT
    std::array<DispersionReal, levels> mesopuff_y_exponent{};    // BYPGT
    // Heffter growth coefficients; AZT/SZH only enter once HEFTRAN is
    // reconstructed (MHFTSZ = 1), which P7D refuses for now.
    std::array<DispersionReal, levels> heffter_z_coefficient{}; // AZT
    DispersionReal heffter_y_coefficient = 0.0F;               // AYT
    DispersionReal heffter_y_sigma_m = 300.0F;                 // SYH default
    DispersionReal heffter_z_sigma_m = 88.0F;                  // SZH default
};

[[nodiscard]] const DispersionTables& dispersion_tables();

// SIGTY / SIGTZ equivalent for the MDISP = 3 environment.
class SigmaCurves {
public:
    explicit SigmaCurves(DispersionEnvironment environment);

    [[nodiscard]] const DispersionEnvironment& environment() const noexcept { return environment_; }
    [[nodiscard]] bool stability_class_conditioned() const noexcept { return conditioned_; }

    // Virtual time at which sigma-y reaches SYH; SETCSIG obtains THFTY exactly
    // this way (SIGTY with SIGY0 = SYH and zero increments).
    [[nodiscard]] double heffter_transition_time_y_s() const;

    [[nodiscard]] DispersionStep sigma_y(double sigy0_m, DispersionIncrement increment) const;
    [[nodiscard]] DispersionStep sigma_z(double sigz0_m, double height_m,
                                        DispersionIncrement increment) const;

private:
    DispersionEnvironment environment_;
    int stability_ = 0;
    bool conditioned_ = false;
};

// Control-file view of the dispersion options: the values the selected deck
// actually carries, which of them are effective for MDISP = 3, and the vendor
// defaults used when a key is absent.
struct DispersionOptionAudit {
    int mdisp = 3;
    int mdisp2 = 3;
    int mturbvw = 3;
    int mtauly = 0;
    int mhftsz = 0;
    int mrough = 0;
    double avet_minutes = 60.0;
    double pgtime_minutes = 60.0;
    double sytdep_m = 550.0;
    bool mdisp2_effective = false;  // MDISP 1 and 5 only
    bool mturbvw_effective = false; // MDISP 1 and 5 only
    bool mtauly_effective = false;  // SIGTY uses TYIDR for MDISP 1, 2 and 5 only
    std::string selected_option_note;
};

[[nodiscard]] DispersionOptionAudit audit_dispersion_options(const ControlFile& control);

// MDISP = 3 setup values taken from an audited control file, using the vendor
// BLOCK DATA defaults when a key is absent. Fails closed for an unsupported
// MDISP, for MROUGH = 1 (gridded z0 plumbing not reconstructed) and for
// MHFTSZ = 1 (HEFTRAN transition time not reconstructed), and for
// inconsistent AVET/PGTIME/SYTDEP values.
struct DispersionSetup {
    DispersionOption option = DispersionOption::gaussian_pg_rural_mp_urban;
    int mdisp = 3;
    double sigma_y_heffter_m = 550.0; // SYTDEP
    double averaging_factor = 1.0;    // AVEFAC = (AVET/PGTIME)**0.2
    bool heffter_sigma_z = false;     // MHFTSZ
    bool roughness_adjustment = false; // MROUGH
    DispersionOptionAudit audit;
};

[[nodiscard]] DispersionSetup dispersion_setup_from_control(const ControlFile& control);

// Assemble the per-puff environment from the setup plus the puff's own
// meteorological state (PG stability class, rural/urban cell, transport speed).
[[nodiscard]] DispersionEnvironment dispersion_environment(const DispersionSetup& setup,
                                                           int stability_class, bool urban,
                                                           double transport_speed_ms);

} // namespace cteas::puff
