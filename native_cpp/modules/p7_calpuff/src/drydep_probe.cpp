#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
#include "cteas/puff/dry_deposition.hpp"

#include <exception>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <stdexcept>
#include <string>

namespace {

using cteas::puff::ControlFile;
using cteas::puff::DryDepositionEnvironment;
using cteas::puff::DryDepositionMethod;
using cteas::puff::DryDepositionSetup;
using cteas::puff::DryDepositionSpecies;
using cteas::puff::DryDepositionStep;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7F dry deposition probe: " + message);
}

std::string read_text(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("P7F cannot read control file: " + path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

int audit_mode(const std::string& path) {
    const auto text = read_text(path);
    const auto audit = cteas::puff::audit_dry_deposition(text);
    const auto setup = cteas::puff::dry_deposition_setup_from_control(text);
    std::cout << "{\n"
              << "  \"gate\": \"P7F_DRYDEP_OPTION_AUDIT\",\n"
              << "  \"control\": \"" << path << "\",\n"
              << "  \"mdry\": " << audit.mdry << ",\n"
              << "  \"deposited_species\": " << audit.deposited_species << ",\n"
              << "  \"vegetation_state\": " << audit.vegetation_state << ",\n"
              << "  \"reference_height_m\": " << audit.reference_height_m << ",\n"
              << "  \"reference_cuticle_resistance_s_m\": "
              << audit.reference_cuticle_resistance_s_m << ",\n"
              << "  \"reference_ground_resistance_s_m\": " << audit.reference_ground_resistance_s_m
              << ",\n"
              << "  \"reference_reactivity\": " << audit.reference_reactivity << ",\n"
              << "  \"gas_species\": [";
    for (std::size_t i = 0; i < audit.gas_species.size(); ++i) {
        std::cout << (i == 0 ? "" : ", ") << "\"" << audit.gas_species[i] << "\"";
    }
    std::cout << "],\n  \"non_deposited_species\": [";
    for (std::size_t i = 0; i < audit.non_deposited_species.size(); ++i) {
        std::cout << (i == 0 ? "" : ", ") << "\"" << audit.non_deposited_species[i] << "\"";
    }
    std::cout << "],\n  \"unsupported_species\": [";
    for (std::size_t i = 0; i < audit.unsupported_species.size(); ++i) {
        std::cout << (i == 0 ? "" : ", ") << "\"" << audit.unsupported_species[i] << "\"";
    }
    std::cout << "],\n  \"note\": \"" << audit.note << "\"\n}\n";
    std::cout << "P7F_DRYDEP_OPTION_AUDIT=PASS MDRY=" << audit.mdry
              << " GAS_SPECIES=" << audit.gas_species.size()
              << " NON_DEPOSITED=" << audit.non_deposited_species.size()
              << " UNSUPPORTED=" << audit.unsupported_species.size()
              << " VEGETATION_STATE=" << audit.vegetation_state
              << " ZREF_M=" << audit.reference_height_m;
    if (!setup.deposition_layer_term.empty()) {
        std::cout << " RD1_SPECIES_0=" << setup.deposition_layer_term.front();
    }
    std::cout << '\n';
    return 0;
}

// Real-cell demonstration: per-species dry deposition velocity at one grid
// cell of the locked case, using the decoded CALMET static fields (Z0, ILANDU,
// XLAI) and the hourly fields (USTAR, EL, QSW, TEMPK, ZI, WSTAR). This is a
// coefficient evaluation on real inputs, not a model run.
int real_cell_mode(const std::string& met_path, const std::string& control_path, int cell_i,
                   int cell_j, int hour_index) {
    const auto text = read_text(control_path);
    const auto setup = cteas::puff::dry_deposition_setup_from_control(text);
    const auto control = ControlFile::parse(text);
    const int step_seconds = control.required_int("NSECDT");

    struct HourFields {
        bool captured = false;
        std::map<std::string, std::vector<float>> values;
    };
    HourFields hour;
    int intervals = 0;
    const auto summary = cteas::puff::Calmet21Reader::read(
        met_path, [&](const cteas::puff::Calmet21Field& field) {
            if (intervals == hour_index && !field.integer) {
                hour.values[field.label] = field.real_values;
                hour.captured = true;
            }
            if (field.label == "IRH") ++intervals;
        });
    require_true(summary.statics.present, "MET.DAT has no decoded static fields");
    require_true(intervals > hour_index, "requested hour is not present in the MET file");
    const std::size_t cells = static_cast<std::size_t>(summary.header.nx) *
                              static_cast<std::size_t>(summary.header.ny);
    const std::size_t cell = static_cast<std::size_t>(cell_j) * summary.header.nx +
                             static_cast<std::size_t>(cell_i);
    require_true(cell < cells, "cell index outside the met grid");
    for (const char* label : {"USTAR", "EL", "QSW", "TEMPK", "ZI", "WSTAR"}) {
        require_true(hour.values.count(label) == 1U, std::string("missing hourly field ") + label);
    }
    const auto& statics = summary.statics;
    DryDepositionEnvironment environment;
    environment.land_use = statics.land_use[cell];
    environment.roughness_m = statics.roughness_m[cell];
    environment.leaf_area_index = statics.leaf_area_index[cell];
    environment.friction_velocity_ms = hour.values["USTAR"][cell];
    environment.monin_obukhov_m = hour.values["EL"][cell];
    environment.shortwave_w_m2 = hour.values["QSW"][cell];
    environment.temperature_k = hour.values["TEMPK"][cell];
    const double mixing_height = hour.values["ZI"][cell];
    const double wstar = hour.values["WSTAR"][cell];
    const bool water_or_irrigated =
        environment.land_use < 0 ||
        (environment.land_use >= environment.water_category_low &&
         environment.land_use <= environment.water_category_high);
    environment.vegetation_state = water_or_irrigated ? 1 : setup.vegetation_state;
    const auto result = cteas::puff::dry_deposition_step(setup, environment, mixing_height,
                                                        static_cast<double>(step_seconds),
                                                        mixing_height, wstar);
    std::cout << "P7G_REAL_CELL_VD=PASS CELL=" << cell_i << "," << cell_j << " HOUR=" << hour_index
              << " LAND_USE=" << environment.land_use << " Z0_M=" << environment.roughness_m
              << " XLAI=" << environment.leaf_area_index
              << " USTAR=" << environment.friction_velocity_ms
              << " EL=" << environment.monin_obukhov_m
              << " QSW=" << environment.shortwave_w_m2
              << " TEMPK=" << environment.temperature_k << " ZI=" << mixing_height
              << " WSTAR=" << wstar << " RA=" << result.atmospheric_resistance_s_m
              << " DIFFK=" << result.boundary_diffusivity_m2_s;
    for (std::size_t index = 0; index < setup.species.size(); ++index) {
        std::cout << " " << setup.species[index].name << "_VD=" << result.velocity_ms[index]
                  << " " << setup.species[index].name << "_FRACDRY="
                  << result.fraction_remaining[index];
    }
    std::cout << " NOT_A_MODEL_RUN=true\n";
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 3 && std::string(argv[1]) == "--audit") return audit_mode(argv[2]);
        if (argc == 7 && std::string(argv[1]) == "--real-cell") {
            return real_cell_mode(argv[2], argv[3], std::stoi(argv[4]), std::stoi(argv[5]),
                                  std::stoi(argv[6]));
        }
        if (argc != 1) {
            std::cerr << "Usage: cteas_p7f_drydep_probe [--audit CONTROL_FILE]\n"
                         "Without arguments reads the dry deposition case matrix on stdin:\n"
                         "  line 1: rcutr rgr reactr dconst1 dconst2 dconst3 pconst bmin bmax qswmax\n"
                         "  line 2: nspec\n"
                         "  next nspec lines: idryflg pdiff_cm2s alpha react rm_s_cm henry\n"
                         "  then per case: icase iveg u10 v10 ilu iwat1 iwat2 z0 tdegk ustar el\n"
                         "                 xlai qsw zref\n"
                         "                 lid_height sampling_step mixing_height wstar\n"
                         "and writes one line per species: icase species_index vd\n";
            return 2;
        }
        double reference_cuticle = 0.0, reference_ground = 0.0, reference_reactivity = 0.0;
        double schmidt_coefficient = 0.0, schmidt_exponent = 0.0, water_constant = 0.0;
        double stomatal_constant = 0.0, opening_min = 0.0, opening_max = 0.0, radiation_max = 0.0;
        if (!(std::cin >> reference_cuticle >> reference_ground >> reference_reactivity >>
              schmidt_coefficient >> schmidt_exponent >> water_constant >> stomatal_constant >>
              opening_min >> opening_max >> radiation_max)) {
            throw std::invalid_argument("missing dry deposition setup line");
        }
        int species_count = 0;
        if (!(std::cin >> species_count) || species_count <= 0) {
            throw std::invalid_argument("missing or invalid species count");
        }
        std::vector<DryDepositionSpecies> species(static_cast<std::size_t>(species_count));
        for (auto& entry : species) {
            int method = 0;
            double diffusivity = 0.0, alpha = 0.0, reactivity = 0.0, mesophyll = 0.0, henry = 0.0;
            if (!(std::cin >> method >> diffusivity >> alpha >> reactivity >> mesophyll >> henry)) {
                throw std::invalid_argument("missing dry deposition species line");
            }
            entry.method = cteas::puff::require_supported_dry_deposition_method(method, "matrix");
            entry.gas.diffusivity_cm2_s = diffusivity;
            entry.gas.alpha_star = alpha;
            entry.gas.reactivity = reactivity;
            entry.gas.mesophyll_resistance_s_cm = mesophyll;
            entry.gas.henry_law_coefficient = henry;
            entry.has_gas_parameters = true;
        }
        std::size_t cases = 0;
        std::cout.setf(std::ios::scientific, std::ios::floatfield);
        std::cout.precision(10);
        while (true) {
            int icase = 0, vegetation = 0, land_use = 0, water_low = 0, water_high = 0;
            double u10 = 0.0, v10 = 0.0, roughness = 0.0, temperature = 0.0, ustar = 0.0;
            double monin = 0.0, leaf_area = 0.0, radiation = 0.0, reference_height = 0.0;
            double lid = 0.0, step_s = 0.0, mixing_height = 0.0, wstar = 0.0;
            if (!(std::cin >> icase >> vegetation >> u10 >> v10 >> land_use >> water_low >>
                  water_high >> roughness >> temperature >> ustar >> monin >> leaf_area >> radiation >>
                  reference_height >> lid >> step_s >> mixing_height >> wstar)) {
                if (std::cin.eof()) break;
                throw std::invalid_argument("malformed dry deposition case line");
            }
            DryDepositionSetup setup;
            setup.species = species;
            setup.reference_height_m = reference_height;
            setup.reference_cuticle_resistance_s_m = reference_cuticle;
            setup.reference_ground_resistance_s_m = reference_ground;
            setup.reference_reactivity = reference_reactivity;
            setup.stomatal_constant = stomatal_constant;
            setup.stomatal_opening_min_m = opening_min;
            setup.stomatal_opening_max_m = opening_max;
            setup.radiation_max_w_m2 = radiation_max;
            setup.schmidt_coefficient = schmidt_coefficient;
            setup.schmidt_exponent = schmidt_exponent;
            setup.water_transfer_constant = water_constant;
            cteas::puff::finalize_dry_deposition_setup(setup);

            DryDepositionEnvironment environment;
            environment.vegetation_state = vegetation;
            environment.u10_ms = u10;
            environment.v10_ms = v10;
            environment.land_use = land_use;
            environment.water_category_low = water_low;
            environment.water_category_high = water_high;
            environment.roughness_m = roughness;
            environment.temperature_k = temperature;
            environment.friction_velocity_ms = ustar;
            environment.monin_obukhov_m = monin;
            environment.leaf_area_index = leaf_area;
            environment.shortwave_w_m2 = radiation;
            const auto result = cteas::puff::dry_deposition_step(setup, environment, lid, step_s,
                                                                mixing_height, wstar);
            for (std::size_t index = 0; index < species.size(); ++index) {
                std::cout << icase << ' ' << index + 1U << ' ' << result.velocity_ms[index] << '\n';
            }
            ++cases;
        }
        std::cerr << "P7F_DRYDEP_PROBE=PASS CASES=" << cases << " SPECIES=" << species_count
                  << " NOT_A_MODEL_RUN=true\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "P7F_DRYDEP_PROBE=FAIL: " << error.what() << '\n';
        return 1;
    }
}
