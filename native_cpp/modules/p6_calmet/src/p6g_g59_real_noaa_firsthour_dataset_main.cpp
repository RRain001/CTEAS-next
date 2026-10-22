// S4-R1c8k: emit an actual one-hour CALMET.DAT 2.1 candidate from
// NOAA source-only native kernels plus source-derived static/header records.
// This file is NOT six-hour causal G14 or production/P7 acceptance.
#include "cteas/p6/p6g_g59_real_noaa_firsthour_dataset.hpp"
#include <bit>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

namespace p6g = cteas::calmet::p6g;
int main(int argc, char** argv) {
    try {
        if (argc != 7 ||
            std::string(argv[1]) != "--real-noaa-firsthour-met21-only" ||
            sizeof(float) != 4 || sizeof(std::int32_t) != 4 ||
            std::endian::native != std::endian::little)
            throw std::invalid_argument(
                "G59 source met.inp GEO.DAT SURF.DAT UP.DAT output.MET required");
        const p6g::G19SourceFilePaths paths{
            argv[2], argv[3], argv[4], {argv[5]}};
        const auto candidate = p6g::g59_source_noaa_firsthour_dataset(paths, true);
        if (!candidate.firsthour_source_native_45_record_dataset ||
            candidate.g14_six_hour_causal || candidate.g26_production ||
            candidate.p7_accepted)
            throw std::logic_error("G59 cannot claim full G26/P7 acceptance");
        cteas::p6f::write_calmet_dat21(argv[6], candidate.dataset);
        const auto loaded = cteas::p6f::read_calmet_dat21(argv[6]);
        if (loaded.hourly.size() != 45 || loaded.header.irlg != 1 ||
            loaded.header.nssta != 2 || loaded.header.nusta != 1 ||
            loaded.header.nx != 82 || loaded.header.ny != 85)
            throw std::logic_error("G59 source-native MET.DAT roundtrip failed");
        std::cerr
            << "S4R1C8K_NATIVE_NOAA_FIRSTHOUR_MET21=PRODUCED_UNVERIFIED "
            << "FIELDS=45 SOURCE_ONLY=TRUE ORIGINAL_MET_INPUT=FALSE "
            << "SIXHOUR_G14_G26_P7=NOT_ACCEPTED\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "S4R1C8K_FIRSTHOUR_MET21_FAIL_CLOSED "
                  << e.what() << '\n';
        return 2;
    }
}
