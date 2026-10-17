#include "cteas/puff/dispersion.hpp"

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using cteas::puff::ControlFile;
using cteas::puff::DispersionEnvironment;
using cteas::puff::DispersionIncrement;
using cteas::puff::DispersionStep;
using cteas::puff::SigmaCurves;

// SIGSET clips SYTDEP to a maximum that the PG sigma-y curves can reach
// (syhmax = NINT(AVEFAC*YMAXFAC*100.)*1000., and YMAXFAC = 1 when MROUGH = 0).
double bounded_heffter_sigma_y(double averaging_factor, double sytdep_m) {
    const double maximum = std::round(averaging_factor * 100.0) * 1000.0;
    return sytdep_m > maximum ? maximum : sytdep_m;
}

int audit_mode(const std::string& path) {
    const auto control = ControlFile::read_file(path);
    const auto audit = cteas::puff::audit_dispersion_options(control);
    const auto setup = cteas::puff::dispersion_setup_from_control(control);
    std::cout << "{\n"
              << "  \"gate\": \"P7D_DISPERSION_OPTION_AUDIT\",\n"
              << "  \"control\": \"" << path << "\",\n"
              << "  \"mdisp\": " << audit.mdisp << ",\n"
              << "  \"mdisp2\": " << audit.mdisp2 << ",\n"
              << "  \"mturbvw\": " << audit.mturbvw << ",\n"
              << "  \"mtauly\": " << audit.mtauly << ",\n"
              << "  \"mhftsz\": " << audit.mhftsz << ",\n"
              << "  \"mrough\": " << audit.mrough << ",\n"
              << "  \"avet_minutes\": " << audit.avet_minutes << ",\n"
              << "  \"pgtime_minutes\": " << audit.pgtime_minutes << ",\n"
              << "  \"sytdep_m\": " << audit.sytdep_m << ",\n"
              << "  \"mdisp2_effective\": " << (audit.mdisp2_effective ? "true" : "false") << ",\n"
              << "  \"mturbvw_effective\": " << (audit.mturbvw_effective ? "true" : "false") << ",\n"
              << "  \"mtauly_effective\": " << (audit.mtauly_effective ? "true" : "false") << ",\n"
              << "  \"selected_option\": " << static_cast<int>(setup.option) << ",\n"
              << "  \"sigma_y_heffter_m\": " << setup.sigma_y_heffter_m << ",\n"
              << "  \"averaging_factor\": " << setup.averaging_factor << ",\n"
              << "  \"note\": \"" << audit.selected_option_note << "\"\n"
              << "}\n";
    std::cout << "P7D_DISPERSION_OPTION_AUDIT=PASS MDISP=" << audit.mdisp
              << " SELECTED_OPTION_IS_REAL_CASE_PATH=" << (audit.mdisp == 3 ? "true" : "false")
              << " MDISP2_EFFECTIVE=" << (audit.mdisp2_effective ? "true" : "false")
              << " MTURBVW_EFFECTIVE=" << (audit.mturbvw_effective ? "true" : "false")
              << " MTAULY_EFFECTIVE=" << (audit.mtauly_effective ? "true" : "false") << "\n";
    return 0;
}

int dump_tables() {
    const auto& tables = cteas::puff::dispersion_tables();
    std::cout.setf(std::ios::scientific, std::ios::floatfield);
    std::cout.precision(9);
    const auto row = [](const char* name, std::size_t level, double value) {
        std::cout << "P7D_TABLE " << name << ' ' << level << ' ' << value << '\n';
    };
    for (std::size_t i = 0; i < cteas::puff::DispersionTables::levels; ++i) {
        row("ayurb", i, tables.urban_y_coefficient[i]);
        row("xiyurb", i, tables.urban_y_inverse_length[i]);
        row("azurb", i, tables.urban_z_coefficient[i]);
        row("xizurb", i, tables.urban_z_inverse_length[i]);
        row("nzbrur", i, static_cast<double>(tables.rural_z_segments[i]));
        row("aypgt", i, tables.mesopuff_y_coefficient[i]);
        row("bypgt", i, tables.mesopuff_y_exponent[i]);
        row("azt", i, tables.heffter_z_coefficient[i]);
        row("cy", i, tables.rural_y_coefficient[i]);
        row("dy", i, tables.rural_y_exponent[i]);
        for (std::size_t segment = 0; segment < cteas::puff::DispersionTables::segments; ++segment) {
            row("azrur", i * cteas::puff::DispersionTables::segments + segment,
                tables.rural_z_coefficient[segment][i]);
            row("bzrur", i * cteas::puff::DispersionTables::segments + segment,
                tables.rural_z_exponent[segment][i]);
            row("xzbrur", i * cteas::puff::DispersionTables::segments + segment,
                tables.rural_z_junction_km[segment][i]);
        }
    }
    row("ayt", 0U, tables.heffter_y_coefficient);
    row("syh", 0U, tables.heffter_y_sigma_m);
    row("szh", 0U, tables.heffter_z_sigma_m);
    std::cout << "P7D_TABLE_DUMP=PASS\n";
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--dump-tables") return dump_tables();
        if (argc == 3 && std::string(argv[1]) == "--audit") return audit_mode(argv[2]);
        if (argc != 1) {
            std::cerr << "Usage: cteas_p7d_sigma_probe [--audit CONTROL_FILE]\n"
                         "Without arguments reads the dispersion case matrix on stdin:\n"
                         "  icase idopty idoptz iru kst mhftsz uavg sigy0 sigz0 dxkm dt zht\n"
                         "        sytdep avefac yz0fac az0fac bz0trm\n"
                         "and writes: icase sigy virty virdy sigz virtz virdz thfty\n";
            return 2;
        }
        std::size_t cases = 0;
        while (true) {
            int icase = 0, idopty = 0, idoptz = 0, iru = 0, kst = 0, mhftsz = 0;
            double uavg = 0.0, sigy0 = 0.0, sigz0 = 0.0, dxkm = 0.0, dt = 0.0, zht = 0.0;
            double sytdep = 0.0, avefac = 1.0;
            double yrfac = 1.0, zafac = 1.0, zbtrm = -1000.0;
            if (!(std::cin >> icase >> idopty >> idoptz >> iru >> kst >> mhftsz >> uavg >> sigy0 >>
                  sigz0 >> dxkm >> dt >> zht >> sytdep >> avefac >> yrfac >> zafac >> zbtrm)) {
                if (std::cin.eof()) break;
                throw std::invalid_argument("malformed dispersion case line");
            }
            // Both sigma axes must carry the reconstructed option.
            const auto option = cteas::puff::require_supported_dispersion_option(idopty);
            if (idoptz != idopty) {
                throw std::invalid_argument("P7D dispersion: sigma-y and sigma-z options must match");
            }
            (void)option;
            if (iru != 0 && iru != 1) {
                throw std::invalid_argument("P7D dispersion: IRUS must be 0 (rural) or 1 (urban)");
            }
            if (mhftsz != 0 && mhftsz != 1) {
                throw std::invalid_argument("P7D dispersion: MHFTSZ must be 0 or 1");
            }
            DispersionEnvironment environment;
            environment.stability_class = kst;
            environment.urban = iru == 1;
            environment.transport_speed_ms = uavg;
            environment.sigma_y_heffter_m = bounded_heffter_sigma_y(avefac, sytdep);
            environment.averaging_factor = avefac;
            environment.sigma_y_roughness = yrfac;
            environment.sigma_z_a_roughness = zafac;
            environment.sigma_z_b_term = zbtrm;
            environment.heffter_sigma_z = mhftsz == 1;
            const SigmaCurves curves(environment);
            DispersionIncrement increment;
            increment.dx_km = dxkm;
            increment.dt_s = dt;
            const DispersionStep y = curves.sigma_y(sigy0, increment);
            const DispersionStep z = curves.sigma_z(sigz0, zht, increment);
            std::cout.setf(std::ios::scientific, std::ios::floatfield);
            std::cout.precision(10);
            std::cout << icase << ' ' << y.sigma_y_m << ' ' << y.virtual_time_y_s << ' '
                      << y.virtual_distance_y_km << ' ' << z.sigma_z_m << ' ' << z.virtual_time_z_s
                      << ' ' << z.virtual_distance_z_km << ' ' << y.heffter_transition_time_y_s
                      << '\n';
            ++cases;
        }
        std::cerr << "P7D_SIGMA_PROBE=PASS CASES=" << cases
                  << " NOT_A_MODEL_RUN=true MDISP=3\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "P7D_SIGMA_PROBE=FAIL: " << error.what() << '\n';
        return 1;
    }
}
