#include "cteas/puff/dry_deposition.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <limits>
#include <cstddef>
#include <optional>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace cteas::puff {
namespace {

using R = DryDepositionReal;

// Vendor constants. Names in comments are the original identifiers in
// calpuff.for so every number below can be checked against the source text.
constexpr R kStomatalConstant = 2.3e-8F;        // PCONST        (BLOCK DATA L2213)
constexpr R kStomatalOpeningMax = 2.5e-6F;      // BMAX          (BLOCK DATA L2213)
constexpr R kStomatalOpeningMin = 0.1e-6F;      // BMIN          (BLOCK DATA L2213)
constexpr R kRadiationMax = 600.0F;             // QSWMAX        (BLOCK DATA L2213)
constexpr R kSchmidtCoefficient = 2.0F;         // DCONST1       (BLOCK DATA L2214)
constexpr R kSchmidtExponent = 0.6666667F;      // DCONST2       (BLOCK DATA L2214)
constexpr R kWaterTransferConstant = 4.8e-4F;   // DCONST3       (BLOCK DATA L2214)
constexpr R kAirViscosity = 0.15e-4F;           // VAIR          (DRYI data)
constexpr R kVonKarman = 0.4F;                  // VK            (DRYI/VDCOMP data)
constexpr R kMinimumUstar = 1.0e-5F;            // USMIN         (VDCOMP data)
constexpr R kMinimumResistance = 1.0F;          // RAMIN         (VDCOMP data)
constexpr R kMinimumWindSpeed = 1.0F;           // WS0           (VDCOMP data)
constexpr R kWaterRoughnessBase = 2.0e-6F;      // minimum z0 over water
constexpr R kInactiveVegetationResistance = 9.9e9F;
constexpr R kBoundaryDiffusivityNeutral = 0.01F; // CONK1        (BLOCK DATA L2205)
constexpr R kBoundaryDiffusivityUnstable = 0.1F; // CONK2        (BLOCK DATA L2205)
constexpr R kDefaultReferenceCuticleResistance = 30.0; // RCUTR default
constexpr R kDefaultReferenceGroundResistance = 10.0;  // RGR default
constexpr R kDefaultReferenceReactivity = 8.0;         // REACTR default
constexpr int kDefaultParticleIntervals = 9;           // NINT default
constexpr int kDefaultVegetationState = 1;             // IVEG default
constexpr int kDefaultMdRy = 1;                        // MDRY default (BLOCK DATA L2244)
constexpr double kCentimetreToMetre = 1.0e-4;          // cm**2/s -> m**2/s
constexpr double kMetrePerCentimetre = 1.0e2;          // s/cm -> s/m

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7F dry deposition: " + message);
}

double required_option_double(const ControlFile& control, const char* key, double fallback) {
    const auto found = control.values(key);
    if (found.empty()) return fallback;
    require_true(found.size() == 1U, std::string("expected at most one active control: ") + key);
    std::string raw = found.front();
    for (char& c : raw) {
        if (c == 'D' || c == 'd') c = 'E';
    }
    std::size_t consumed = 0;
    double value = 0.0;
    try {
        value = std::stod(raw, &consumed);
    } catch (const std::exception&) {
        throw std::invalid_argument(std::string("P7F dry deposition: invalid float option ") + key +
                                    "=" + found.front());
    }
    require_true(consumed == raw.size() && std::isfinite(value),
                 std::string("P7F dry deposition: invalid or non-finite float option ") + key + "=" +
                     found.front());
    return value;
}

int required_option_int(const ControlFile& control, const char* key, int fallback) {
    const auto found = control.values(key);
    if (found.empty()) return fallback;
    require_true(found.size() == 1U, std::string("expected at most one active control: ") + key);
    int value = 0;
    const auto& raw = found.front();
    const auto [end, error] = std::from_chars(raw.data(), raw.data() + raw.size(), value);
    require_true(end == raw.data() + raw.size() && error == std::errc{},
                 std::string("P7F dry deposition: invalid integer option ") + key + "=" + raw);
    return value;
}

std::string upper(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    return value;
}

std::string trim(const std::string& value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return {};
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::vector<std::string> lines_of(const std::string& text) {
    std::vector<std::string> lines;
    std::istringstream stream(text);
    std::string line;
    while (std::getline(stream, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        lines.push_back(line);
    }
    return lines;
}

// Control-file section between a header marker and the next group terminator.
std::vector<std::string> section_lines(const std::vector<std::string>& lines,
                                       const std::string& marker,
                                       bool require_marker = true) {
    std::vector<std::string> section;
    bool inside = false;
    for (const auto& line : lines) {
        if (!inside) {
            if (upper(line).find(upper(marker)) != std::string::npos) inside = true;
            continue;
        }
        if (upper(trim(line)).find("!END!") == 0U) break;
        section.push_back(line);
    }
    if (inside) return section;
    require_true(!require_marker, "control section not found: " + marker);
    return section;
}

double parse_value(const std::string& raw, const std::string& what) {
    std::string text = trim(raw);
    for (char& c : text) {
        if (c == 'D' || c == 'd') c = 'E';
    }
    std::size_t consumed = 0;
    double value = 0.0;
    try {
        value = std::stod(text, &consumed);
    } catch (const std::exception&) {
        throw std::invalid_argument("P7F dry deposition: invalid value for " + what + ": " + raw);
    }
    require_true(consumed == text.size() && std::isfinite(value),
                 "invalid or non-finite value for " + what + ": " + raw);
    return value;
}

struct TableRow {
    std::string name;
    std::vector<double> values;
};

// Lines of the form `! NAME = v1, v2, ... !` inside one control section. The
// species tables use hyphenated names that the generic key parser rejects, so
// they are read here with an anchored pattern (a trailing `!END!` or a second
// `!...!` group on the same line therefore never matches).
std::vector<TableRow> parse_table(const std::vector<std::string>& lines, std::size_t expected_values,
                                  const std::string& section) {
    static const std::regex row(R"(^\s*!\s*([A-Za-z0-9][A-Za-z0-9_.+-]*)\s*=\s*([^!]*)!\s*$)");
    std::vector<TableRow> rows;
    for (const auto& line : lines) {
        std::smatch match;
        if (!std::regex_match(line, match, row)) continue;
        TableRow parsed;
        parsed.name = upper(trim(match[1].str()));
        std::string values = match[2].str();
        std::size_t start = 0;
        while (true) {
            const auto comma = values.find(',', start);
            const std::string piece = values.substr(start, comma == std::string::npos
                                                               ? std::string::npos
                                                               : comma - start);
            if (!trim(piece).empty() || comma != std::string::npos) {
                parsed.values.push_back(parse_value(piece, section + " " + parsed.name));
            }
            if (comma == std::string::npos) break;
            start = comma + 1;
        }
        require_true(parsed.values.size() == expected_values,
                     "control section " + section + " row " + parsed.name + " has " +
                         std::to_string(parsed.values.size()) + " values, expected " +
                         std::to_string(expected_values));
        rows.push_back(std::move(parsed));
    }
    require_true(!rows.empty(), "control section " + section + " has no data rows");
    return rows;
}

} // namespace

OriginalDryMassResult original_uniform_dry_mass(
    const DryDepositionStep& d,int puff_code,
    const std::vector<float>& before) {
    int code=puff_code;
    if(code>=11 && code<=16)code-=10;
    if(puff_code!=99 && code!=4 && code!=2 && code!=6)
        throw std::invalid_argument(
            "P7F original uniform DRY refuses Gaussian puff code");
    if(d.fraction_remaining.size()!=before.size() ||
       d.velocity_ms.size()!=before.size() ||
       d.boundary_ratio.size()!=before.size())
        throw std::invalid_argument(
            "P7F original uniform DRY species dimension mismatch");
    const bool skipped=(puff_code==99||code==4);
    OriginalDryMassResult out;
    out.fraction_remaining.reserve(before.size());
    out.mixed_mass_after.reserve(before.size());
    out.removed_mass.reserve(before.size());
    for(std::size_t j=0;j<before.size();++j) {
        const R mass=before[j];
        // Uniform DRY L26227–26261 is already computed by the
        // native dry_deposition_step; unlike Gaussian DRY, VDPVD
        // is NOT equal to unity for deposited gases here.
        const R fraction=skipped?1.0F:
            static_cast<R>(d.fraction_remaining[j]);
        const R after=static_cast<R>(mass*fraction);
        if(!std::isfinite(mass)||mass<0.0F ||
           !std::isfinite(fraction)||fraction<0.0F||fraction>1.0F ||
           !std::isfinite(after)||after<0.0F)
            throw std::invalid_argument(
                "P7F original uniform DRY invalid fraction or QM");
        out.fraction_remaining.push_back(fraction);
        out.mixed_mass_after.push_back(after);
        out.removed_mass.push_back(static_cast<R>(mass-after));
    }
    return out;
}

OriginalGaussianDryResult original_gaussian_dry_mass(
    const DryDepositionStep& d, int puff_code,
    float tsamp, float vcbar, const std::vector<float>& before) {
    if(!std::isfinite(tsamp)||tsamp<=0.0F ||
       !std::isfinite(vcbar)||vcbar<0.0F ||
       d.velocity_ms.size()!=before.size() ||
       d.boundary_ratio.size()!=before.size())
        throw std::invalid_argument(
            "P7F original Gaussian DRY invalid substep, VCBAR or species");
    int normalized=puff_code;
    if(normalized>=11 && normalized<=16)normalized-=10;
    if(puff_code!=99 && (normalized<1||normalized>6 ||
                         normalized==2||normalized==6))
        throw std::invalid_argument(
            "P7F Gaussian DRY refuses non-Gaussian puff code");
    OriginalGaussianDryResult out;
    out.vcbar_m_inverse=vcbar;
    out.fraction_remaining.reserve(before.size());
    out.mixed_mass_after.reserve(before.size());
    out.removed_mass.reserve(before.size());
    // Original DRY L26198–26203: ICODE=99 or 4/14 return untouched.
    const bool skipped=(puff_code==99||normalized==4);
    // DRY L26266–26276: CONST=TSAMP*VCBAR and
    // FRACDRY=EXP(-VDPVD*VD*CONST), QM=FRACDRY*QM.
    const R exponent_factor=static_cast<R>(tsamp*vcbar);
    for(std::size_t j=0;j<before.size();++j) {
        const R mass=before[j];
        const R vd=static_cast<R>(d.velocity_ms[j]);
        // In original DRY L26227–26254 the VDPVD boundary ratio
        // is calculated ONLY for the uniform codes 2 and 6.
        // Gaussian codes 1/3/5 keep the initial VDPVD=1.0.
        const R ratio=1.0F;
        if(!std::isfinite(mass)||mass<0.0F ||
           !std::isfinite(vd)||vd<0.0F ||
           !std::isfinite(ratio)||ratio<0.0F ||
           !std::isfinite(exponent_factor))
            throw std::invalid_argument(
                "P7F original Gaussian DRY nonfinite/negative REAL4 input");
        const R fraction=skipped?1.0F:
            static_cast<R>(std::exp(static_cast<R>(
                -ratio*vd*exponent_factor)));
        const R remaining=static_cast<R>(fraction*mass);
        if(!std::isfinite(fraction)||fraction<0.0F||fraction>1.0F ||
           !std::isfinite(remaining)||remaining<0.0F)
            throw std::overflow_error(
                "P7F original Gaussian DRY invalid remaining QM");
        out.fraction_remaining.push_back(fraction);
        out.mixed_mass_after.push_back(remaining);
        out.removed_mass.push_back(static_cast<R>(mass-remaining));
    }
    return out;
}

DryDepositionMethod require_supported_dry_deposition_method(int method, const std::string& species) {
    switch (method) {
    case 0: return DryDepositionMethod::none;
    case 1: return DryDepositionMethod::gas_resistance;
    case 2:
        throw std::invalid_argument(
            "P7F dry deposition: species " + species +
            " uses computed particle deposition (method 2), which needs the DRYI/VDP1 size-distribution "
            "physics and is not reconstructed");
    case 3:
        throw std::invalid_argument(
            "P7F dry deposition: species " + species +
            " uses user-specified diurnal deposition velocities (method 3), which need the RDVD input "
            "table and are not reconstructed");
    default:
        throw std::invalid_argument("P7F dry deposition: species " + species +
                                    " has illegal deposition method " + std::to_string(method) +
                                    " (expected 0, 1, 2 or 3)");
    }
}

DryDepositionSetup dry_deposition_setup_from_control(const std::string& control_text) {
    const auto control = ControlFile::parse(control_text);
    const auto lines = lines_of(control_text);
    const int mdry = required_option_int(control, "MDRY", kDefaultMdRy);
    require_true(mdry == 1, "MDRY=" + std::to_string(mdry) +
                                "; the P7F selected scope requires MDRY=1 (dry deposition enabled)");

    DryDepositionSetup setup;
    setup.reference_cuticle_resistance_s_m =
        required_option_double(control, "RCUTR", kDefaultReferenceCuticleResistance) *
        kMetrePerCentimetre;
    setup.reference_ground_resistance_s_m =
        required_option_double(control, "RGR", kDefaultReferenceGroundResistance) *
        kMetrePerCentimetre;
    setup.reference_reactivity = required_option_double(control, "REACTR", kDefaultReferenceReactivity);
    setup.particle_intervals = required_option_int(control, "NINT", kDefaultParticleIntervals);
    setup.vegetation_state = required_option_int(control, "IVEG", kDefaultVegetationState);
    require_true(setup.reference_cuticle_resistance_s_m > 0.0, "RCUTR must be positive");
    require_true(setup.reference_ground_resistance_s_m > 0.0, "RGR must be positive");
    require_true(setup.reference_reactivity > 0.0, "REACTR must be positive");
    require_true(setup.vegetation_state >= 1 && setup.vegetation_state <= 3,
                 "IVEG must be 1 (active/unstressed), 2 (active/stressed) or 3 (inactive)");

    const auto zface = control.required_float_list("ZFACE");
    require_true(zface.size() >= 2U, "ZFACE must provide at least two cell faces");
    require_true(zface[1] > zface[0], "ZFACE must increase with height");
    // DRYI: ZREF = AMIN1(0.5*(ZFACE(1)+ZFACE(2)), 10.0)
    setup.reference_height_m = std::min(0.5 * (zface[0] + zface[1]), 10.0);
    require_true(setup.reference_height_m > 0.0, "reference height must be positive");

    const auto species_rows = parse_table(section_lines(lines, "Subgroup (3a)"), 4U, "group 3a");
    const auto gas_rows = parse_table(section_lines(lines, "INPUT GROUP: 7"), 5U, "group 7");

    const auto declared = control.values("CSPEC");
    require_true(!declared.empty(), "CSPEC species list is missing");
    require_true(declared.size() == species_rows.size(),
                 "CSPEC declares " + std::to_string(declared.size()) + " species but group 3a lists " +
                     std::to_string(species_rows.size()));

    for (const auto& row : species_rows) {
        DryDepositionSpecies species;
        species.name = row.name;
        species.modeled = static_cast<int>(row.values[0]);
        species.emitted = static_cast<int>(row.values[1]);
        const int raw_method = static_cast<int>(row.values[2]);
        species.method = require_supported_dry_deposition_method(raw_method, row.name);
        species.output_group = static_cast<int>(row.values[3]);
        require_true(species.modeled == 0 || species.modeled == 1, "MODELED flag must be 0 or 1");
        require_true(species.emitted == 0 || species.emitted == 1, "EMITTED flag must be 0 or 1");
        setup.species.push_back(std::move(species));
    }
    for (const auto& name : declared) {
        const auto wanted = upper(trim(name));
        const bool found = std::any_of(setup.species.begin(), setup.species.end(),
                                       [&wanted](const DryDepositionSpecies& s) {
                                           return s.name == wanted;
                                       });
        require_true(found, "CSPEC species " + wanted + " is missing from the group 3a table");
    }

    for (const auto& row : gas_rows) {
        const bool known = std::any_of(setup.species.begin(), setup.species.end(),
                                       [&row](const DryDepositionSpecies& s) {
                                           return s.name == row.name;
                                       });
        require_true(known, "group 7 parameters for unknown species " + row.name);
        for (auto& species : setup.species) {
            if (species.name != row.name) continue;
            require_true(species.method == DryDepositionMethod::gas_resistance,
                         "species " + row.name +
                             " has group 7 gas parameters but is not flagged COMPUTED-GAS in group 3a");
            species.gas.diffusivity_cm2_s = row.values[0];
            species.gas.alpha_star = row.values[1];
            species.gas.reactivity = row.values[2];
            species.gas.mesophyll_resistance_s_cm = row.values[3];
            species.gas.henry_law_coefficient = row.values[4];
            species.has_gas_parameters = true;
        }
    }

    finalize_dry_deposition_setup(setup);
    return setup;
}

void finalize_dry_deposition_setup(DryDepositionSetup& setup) {
    const std::size_t count = setup.species.size();
    // DRYI conversion and time-invariant parameters, per species.
    setup.diffusivity_m2_s.assign(count, 0.0);
    setup.mesophyll_resistance_s_m.assign(count, 0.0);
    setup.cuticle_resistance_s_m.assign(count, 0.0);
    setup.ground_resistance_s_m.assign(count, 0.0);
    setup.water_ground_term_s_m.assign(count, 0.0);
    setup.deposition_layer_term.assign(count, 0.0);
    int deposited = 0;
    for (std::size_t index = 0; index < count; ++index) {
        const auto& species = setup.species[index];
        if (species.method != DryDepositionMethod::gas_resistance) continue;
        require_true(species.has_gas_parameters,
                     "species " + species.name + " is COMPUTED-GAS but has no group 7 parameters");
        require_true(species.gas.diffusivity_cm2_s > 0.0,
                     "diffusivity must be positive for " + species.name);
        require_true(species.gas.alpha_star > 0.0, "alpha star must be positive for " + species.name);
        require_true(species.gas.reactivity > 0.0, "reactivity must be positive for " + species.name);
        require_true(species.gas.mesophyll_resistance_s_cm >= 0.0,
                     "mesophyll resistance must not be negative for " + species.name);
        require_true(species.gas.henry_law_coefficient >= 0.0,
                     "Henry's law coefficient must not be negative for " + species.name);
        // Original DRYI calpuff.for L26969:
        //   PDIFF(I)=PDIFF(I)*1.E-4   (both operands REAL*4).
        // The deck's H-3 value .1509 has different binary32 results for
        // REAL4(.1509)*REAL4(1E-4) and REAL4(.1509*1E-4).
        // The latter one-ULP conversion perturbs RS -> RF -> RC -> VD,
        // propagating into puff200 DRY QM and original H3 concentration.
        const R diffusivity=static_cast<R>(
            static_cast<R>(species.gas.diffusivity_cm2_s) *
            static_cast<R>(kCentimetreToMetre));
        const R mesophyll =
            static_cast<R>(species.gas.mesophyll_resistance_s_cm * kMetrePerCentimetre);
        const R schmidt = kAirViscosity / diffusivity;
        const R ratio =
            static_cast<R>(setup.reference_reactivity) / static_cast<R>(species.gas.reactivity);
        setup.diffusivity_m2_s[index] = diffusivity;
        setup.mesophyll_resistance_s_m[index] = mesophyll;
        setup.deposition_layer_term[index] =
            kSchmidtCoefficient * std::pow(schmidt, kSchmidtExponent) / kVonKarman;
        setup.cuticle_resistance_s_m[index] =
            static_cast<R>(setup.reference_cuticle_resistance_s_m) * ratio;
        setup.ground_resistance_s_m[index] =
            static_cast<R>(setup.reference_ground_resistance_s_m) * ratio;
        setup.water_ground_term_s_m[index] =
            static_cast<R>(species.gas.henry_law_coefficient) /
            (static_cast<R>(species.gas.alpha_star) * kWaterTransferConstant);
        ++deposited;
    }
    setup.deposited_species = deposited;
}

DryDepositionStep dry_deposition_step(const DryDepositionSetup& setup,
                                     const DryDepositionEnvironment& environment, double lid_height_m,
                                     double sampling_step_s, double mixing_height_m, double wstar_ms) {
    const std::size_t count = setup.species.size();
    require_true(count > 0U, "no species configured");
    require_true(std::isfinite(lid_height_m) && lid_height_m > 0.0, "reflectance lid height must be positive");
    require_true(std::isfinite(sampling_step_s) && sampling_step_s > 0.0, "sampling step must be positive");
    require_true(std::isfinite(mixing_height_m) && mixing_height_m > 0.0, "mixing height must be positive");
    require_true(std::isfinite(wstar_ms) && wstar_ms >= 0.0, "w* must not be negative");
    require_true(std::isfinite(environment.temperature_k) && environment.temperature_k > 0.0,
                 "temperature must be positive");
    require_true(std::isfinite(environment.friction_velocity_ms) &&
                     environment.friction_velocity_ms >= 0.0,
                 "friction velocity must not be negative");
    require_true(std::isfinite(environment.monin_obukhov_m), "Monin-Obukhov length must be finite");
    require_true(std::isfinite(environment.leaf_area_index) && environment.leaf_area_index >= 0.0,
                 "leaf area index must not be negative");
    require_true(std::isfinite(environment.shortwave_w_m2), "shortwave radiation must be finite");
    require_true(std::isfinite(environment.roughness_m) && environment.roughness_m > 0.0,
                 "cell roughness must be positive");
    require_true(environment.vegetation_state >= 1 && environment.vegetation_state <= 3,
                 "vegetation state must be 1, 2 or 3");
    require_true(setup.reference_height_m > 0.0, "reference height must be positive");

    DryDepositionStep step;
    step.velocity_ms.assign(count, 0.0);
    step.deposition_layer_resistance_s_m.assign(count, 0.0);
    step.canopy_resistance_s_m.assign(count, 0.0);
    step.foliage_resistance_s_m.assign(count, 0.0);
    step.ground_resistance_s_m.assign(count, 0.0);
    step.cuticle_resistance_s_m.assign(count, 0.0);
    step.source_leaf_area_index=static_cast<R>(environment.leaf_area_index);
    step.boundary_ratio.assign(count, 1.0);
    step.fraction_remaining.assign(count, 1.0);
    step.vegetation_state = environment.vegetation_state;

    // VDCOMP: species with no deposition are finished before any computation.
    std::size_t finished = 0;
    for (std::size_t index = 0; index < count; ++index) {
        if (setup.species[index].method == DryDepositionMethod::none) ++finished;
    }
    if (finished == count) return step;

    const bool water = environment.land_use >= environment.water_category_low &&
                       environment.land_use <= environment.water_category_high;
    step.water_cell = water;
    R roughness = static_cast<R>(environment.roughness_m);
    if (water) {
        // Minimum z0 over water is 2.0e-06 m, driven by the 10 m wind speed.
        R water_roughness = kWaterRoughnessBase;
        const R wind_sum = std::abs(static_cast<R>(environment.u10_ms)) +
                           std::abs(static_cast<R>(environment.v10_ms));
        if (wind_sum > kMinimumWindSpeed) {
            const R speed = std::sqrt(static_cast<R>(environment.u10_ms) * environment.u10_ms +
                                      static_cast<R>(environment.v10_ms) * environment.v10_ms);
            if (speed > kMinimumWindSpeed) water_roughness = kWaterRoughnessBase * std::pow(speed, 2.5F);
        }
        roughness = water_roughness;
    }
    step.effective_roughness_m = roughness;

    const R reference_height = static_cast<R>(setup.reference_height_m);
    const R monin = static_cast<R>(environment.monin_obukhov_m);
    const R monin_abs = std::abs(monin);
    R psi_heat = 0.0F;
    if (monin < 0.0F && monin_abs < 9990.0F) {
        R ratio = -reference_height / monin;
        if (ratio > 1.0F) ratio = 1.0F;
        const R zmel = std::log(ratio);
        psi_heat = std::exp(0.598F + 0.39F * zmel - 0.090F * zmel * zmel);
    } else if (monin_abs >= 9990.0F) {
        psi_heat = 0.0F;
    } else {
        R ratio = reference_height / monin;
        if (ratio > 1.0F) ratio = 1.0F;
        psi_heat = -5.0F * ratio;
    }
    step.psi_heat = psi_heat;

    const R ustar = std::max(static_cast<R>(environment.friction_velocity_ms), kMinimumUstar);
    R resistance_a =
        (std::log(reference_height / roughness) - psi_heat) / (kVonKarman * ustar);
    if (resistance_a < kMinimumResistance) resistance_a = kMinimumResistance;
    step.atmospheric_resistance_s_m = resistance_a;

    const R leaf_area = static_cast<R>(environment.leaf_area_index);
    const R radiation = static_cast<R>(environment.shortwave_w_m2);
    const R temperature = static_cast<R>(environment.temperature_k);
    const R vegetation = static_cast<R>(environment.vegetation_state);
    for (std::size_t index = 0; index < count; ++index) {
        if (setup.species[index].method != DryDepositionMethod::gas_resistance) continue;
        const R diffusivity = static_cast<R>(setup.diffusivity_m2_s[index]);
        const R deposition_layer = static_cast<R>(setup.deposition_layer_term[index]) / ustar;
        const R resistance_g = water
                                   ? static_cast<R>(setup.water_ground_term_s_m[index]) / ustar
                                   : static_cast<R>(setup.ground_resistance_s_m[index]);
        R resistance_s = kInactiveVegetationResistance;
        if (vegetation == 1.0F) {
            R opening = kStomatalOpeningMax;
            if (temperature > 308.0F) {
                opening = kStomatalOpeningMax;
            } else if (temperature < 283.0F) {
                opening = kStomatalOpeningMin;
            } else {
                R fraction = radiation / kRadiationMax;
                fraction = std::max(0.0F, std::min(1.0F, fraction));
                opening = kStomatalOpeningMax * fraction + kStomatalOpeningMin * (1.0F - fraction);
            }
            resistance_s = kStomatalConstant / (opening * diffusivity);
        } else if (vegetation == 2.0F) {
            resistance_s = kStomatalConstant / (kStomatalOpeningMin * diffusivity);
        }
        const R resistance_f = resistance_s + static_cast<R>(setup.mesophyll_resistance_s_m[index]);
        const R resistance_c = 1.0F / (leaf_area / resistance_f +
                                       leaf_area / static_cast<R>(setup.cuticle_resistance_s_m[index]) +
                                       1.0F / resistance_g);
        step.deposition_layer_resistance_s_m[index]=deposition_layer;
        step.canopy_resistance_s_m[index]=resistance_c;
        step.foliage_resistance_s_m[index]=resistance_f;
        step.ground_resistance_s_m[index]=resistance_g;
        step.cuticle_resistance_s_m[index]=static_cast<R>(
            setup.cuticle_resistance_s_m[index]);
        step.velocity_ms[index] = 1.0F / (resistance_a + deposition_layer + resistance_c);
    }

    // DRY, uniformly mixed puff branch: boundary-layer ratio and the removal
    // fraction over one sampling step.
    const R mixing_height = static_cast<R>(mixing_height_m);
    const R wstar = static_cast<R>(wstar_ms);
    step.boundary_diffusivity_m2_s =
        wstar > 0.0F
            ? std::max(kBoundaryDiffusivityUnstable * wstar * mixing_height,
                       kBoundaryDiffusivityNeutral * ustar * mixing_height)
            : kBoundaryDiffusivityNeutral * ustar * mixing_height;
    const R depth = std::max(mixing_height - reference_height, 0.00001F);
    const R constant = static_cast<R>(sampling_step_s) / static_cast<R>(lid_height_m);
    const R diffusivity = static_cast<R>(step.boundary_diffusivity_m2_s);
    for (std::size_t index = 0; index < count; ++index) {
        if (setup.species[index].method != DryDepositionMethod::gas_resistance) continue;
        const R velocity = static_cast<R>(step.velocity_ms[index]);
        const R ratio = diffusivity / (diffusivity + velocity * depth);
        step.boundary_ratio[index] = ratio;
        step.fraction_remaining[index] = std::exp(-ratio * velocity * constant);
    }
    return step;
}

DryDepositionAudit audit_dry_deposition(const std::string& control_text) {
    DryDepositionAudit audit;
    const auto control = ControlFile::parse(control_text);
    audit.mdry = required_option_int(control, "MDRY", kDefaultMdRy);
    const auto lines = lines_of(control_text);
    const auto species_rows = parse_table(section_lines(lines, "Subgroup (3a)"), 4U, "group 3a");
    audit.vegetation_state = required_option_int(control, "IVEG", kDefaultVegetationState);
    audit.deposited_species = 0;
    for (const auto& row : species_rows) {
        const int method = static_cast<int>(row.values[2]);
        if (method == 0) {
            audit.non_deposited_species.push_back(row.name);
        } else if (method == 1) {
            audit.gas_species.push_back(row.name);
            ++audit.deposited_species;
        } else {
            audit.unsupported_species.push_back(row.name + "(method " + std::to_string(method) + ")");
        }
    }
    if (audit.mdry != 1) {
        audit.note = "MDRY=" + std::to_string(audit.mdry) +
                     ": dry deposition is disabled in this deck; P7F implements MDRY=1 only";
        return audit;
    }
    const auto setup = dry_deposition_setup_from_control(control_text);
    audit.reference_height_m = setup.reference_height_m;
    audit.reference_cuticle_resistance_s_m = setup.reference_cuticle_resistance_s_m;
    audit.reference_ground_resistance_s_m = setup.reference_ground_resistance_s_m;
    audit.reference_reactivity = setup.reference_reactivity;
    audit.note = "MDRY=1: " + std::to_string(audit.gas_species.size()) +
                 " computed-gas species through the VDCOMP resistance model, " +
                 std::to_string(audit.non_deposited_species.size()) + " species without dry removal";
    return audit;
}

} // namespace cteas::puff
