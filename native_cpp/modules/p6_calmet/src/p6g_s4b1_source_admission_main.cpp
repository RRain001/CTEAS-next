// S4-B1: new, non-Hefei source admission front door for the FUTURE unified
// G14 DIAGNO/COMP/P6F runner. Deliberately refuses any physics/MET claim.
#include "cteas/p6/p6g_g19_file_backed_case.hpp"
#include "cteas/p6/p6g_s4b1_admission.hpp"
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace p6g = cteas::calmet::p6g;

int main(int argc, char** argv) {
    try {
        if (argc < 6 || std::string(argv[1]) != "--admit-only")
            throw std::invalid_argument(
                "Usage: s4b1 --admit-only met.inp GEO.DAT SURF.DAT UP1.DAT [UP2.DAT ...]; "
                "no MET.DAT output/production physics in B1");
        const p6g::G19SourceFilePaths paths{
            argv[2], argv[3], argv[4], std::vector<std::string>(argv + 5, argv + argc)
        };
        // The existing G19 implementation validates original READCF station
        // counts/order, source IDs, original selected options, GEO/SURF/UP
        // identities and every upper-air UTC bracket. Never make fake sites.
        const auto source = p6g::g19_load_original_source_case(paths);
        const auto scheduler = source.make_scheduler();
        if (!scheduler.has_original_controls() ||
            scheduler.planned_hours() != source.surface.hourly.size())
            throw std::logic_error("S4B1 G19/G14 authority mismatch");
        const auto admitted = p6g::s4b1_admit_source_only({
            static_cast<std::size_t>(source.grid.nx),
            static_cast<std::size_t>(source.grid.ny),
            9,
            source.stations.surface.size(),
            source.stations.upper.size(),
            scheduler.planned_hours(),
            true,
            true
        });
        std::cout << "S4B1_G19_G14_ORIGINAL_SOURCE_ADMITTED=PASS_SOURCE_ONLY"
                  << " NX=" << admitted.input.nx << " NY=" << admitted.input.ny
                  << " NZ=" << admitted.input.nz
                  << " SS=" << admitted.input.surface_stations
                  << " US=" << admitted.input.upper_stations
                  << " HOURS=" << admitted.input.hours
                  << " POSSIBLE_45_FIELD_RECORDS=" << admitted.potential_field_records
                  << "\nS4B1_P6_UNIFIED_PHYSICS=NOT_IMPLEMENTED"
                  << " NATIVE_MET_DAT=NOT_WRITTEN"
                  << " ORIGINAL_CALMET_PARITY=NOT_RUN\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "S4B1_SOURCE_ADMISSION_REFUSED " << error.what() << '\n';
        return 2;
    }
}
