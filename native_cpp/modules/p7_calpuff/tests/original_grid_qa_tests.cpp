#include "cteas/puff/control.hpp"
#include "cteas/puff/original_grid_coords.hpp"
#include "cteas/puff/receptors.hpp"
#include "cteas/puff/transport.hpp"

#include <cmath>
#include <cstddef>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>

namespace {
void require(bool good, const std::string& message) {
    if (!good) throw std::runtime_error("P7 original QA parity: " + message);
}
bool same_real4(double reconstructed, double original_text) {
    return static_cast<float>(reconstructed) == static_cast<float>(original_text);
}
template<class Function>
void expect_rejected(Function&& call, const std::string& message) {
    bool rejected = false;
    try { call(); } catch(const std::invalid_argument&) { rejected = true; }
    require(rejected, message);
}
} // namespace

int main(int argc, char** argv) {
    try {
        require(argc == 4, "usage: original_grid_qa_tests CONTROL QAPNTS QARECG");
        const auto control = cteas::puff::ControlFile::read_file(argv[1]);
        const auto raw_x = control.required_float_list("X");
        require(raw_x.size() == 10U && control.required_int("IPTU") == 8,
                "requires locked 2022 constant 2-species source, IPTU=8");
        require(raw_x[0] == 513.385 && raw_x[1] == 3533.769,
                "not the locked Hefei 2022 source");

        // These are the REAL*4 x/y metre origins and spacing of the original
        // 2022 CALMET.DAT grid, not the separately rounded CALPUFF control
        // XORIGKM/YORIGKM. The independent QA files below are the oracle.
        const cteas::puff::OriginalMetGridFrame met{510885.0f, 3531269.0f, 100.0f};
        const auto source = cteas::puff::point_source_from_original_met_grid(control, met);
        const auto unframed = cteas::puff::point_source_from_control(control);
        std::ifstream point_qa(argv[2]);
        require(static_cast<bool>(point_qa), "missing original QAPNTS");
        std::string header;
        require(static_cast<bool>(std::getline(point_qa, header)) &&
                    header.find("Xkm") != std::string::npos,
                "bad original QAPNTS header");
        double px=0.0, py=0.0, pelev=0.0;
        int source_index=0;
        require(static_cast<bool>(point_qa >> px >> py >> pelev >> source_index),
                "original QAPNTS lacks the point source");
        require(source_index == 1 && pelev == 0.0, "unexpected point QA identity");
        require(same_real4(source.x_m/1000.0, px) &&
                    same_real4(source.y_m/1000.0, py),
                "point QA X/Y differs from REAL*4 original CALPUFF output");
        require(!same_real4(unframed.y_m/1000.0, py),
                "the test must detect the independently rounded control Y discrepancy");
        double trailing=0.0;
        require(!(point_qa >> trailing), "unexpected second point QA record");

        std::ifstream receptor_qa(argv[3]);
        require(static_cast<bool>(receptor_qa), "missing original QARECG");
        require(static_cast<bool>(std::getline(receptor_qa, header)) &&
                    header.find("Xkm") != std::string::npos,
                "bad original QARECG header");
        const auto control_text = [&] {
            std::ifstream stream(argv[1]);
            return std::string(std::istreambuf_iterator<char>(stream),
                               std::istreambuf_iterator<char>());
        }();
        const auto receptors =
            cteas::puff::receptors_from_original_met_grid(control_text, met);
        require(receptors.grid.size() == 2500U && receptors.sampling_nx == 50 &&
                    receptors.sampling_ny == 50, "wrong frozen 50 x 50 receptor grid");
        std::size_t count=0;
        double original_x=0.0,original_y=0.0,original_elev=0.0;
        while (receptor_qa >> original_x >> original_y >> original_elev) {
            require(count < receptors.grid.size(), "original QA has excess receptor records");
            const auto& xy = receptors.grid[count];
            require(same_real4(xy.x_km, original_x) &&
                        same_real4(xy.y_km, original_y),
                    "receptor REAL*4 QA coordinate mismatch at index " +
                    std::to_string(count));
            ++count;
        }
        require(receptor_qa.eof(), "original QA receptor parse error");
        require(count == 2500U, "original QA receptor record count is incomplete");

        // Fail closed when MET.DAT spacing differs from the control grid, and
        // when a non-supported sub-cell receptor geometry is supplied.
        expect_rejected([&] {
            auto changed=met; changed.spacing_m=200.0f;
            (void)cteas::puff::receptors_from_original_met_grid(control_text, changed);
        }, "must reject mismatched MET spacing");
        expect_rejected([&] {
            (void)cteas::puff::original_gridded_receptor_qa_xy(met, -1, 0);
        }, "must reject negative grid index");

        std::cout << "P7_ORIGINAL_QA_COORDINATES=PASS SOURCE=1 GRID_RECEPTORS="
                  << count << " REAL4_EXACT=true"
                  << " SOURCE_Y_UNFRAMED_NOT_EQUIVALENT=true"
                  << " ORIGINAL_INTERNAL_XPT1GRD_PARITY=NOT_YET_TESTED"
                  << " FULL_PUFF_CON_PARITY=NOT_YET_TESTED\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "P7_ORIGINAL_QA_COORDINATES=FAIL " << error.what() << '\n';
        return 1;
    }
}
