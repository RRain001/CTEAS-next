#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/control.hpp"
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
void require(bool ok, const std::string& message) {
    if (!ok) throw std::runtime_error("P7 original MET grid: " + message);
}
bool real4_equals(double a, double b) {
    return static_cast<float>(a) == static_cast<float>(b);
}
std::string read_text(const char* path) {
    std::ifstream in(path);
    require(static_cast<bool>(in), "cannot read original input");
    return std::string(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}
void same_integer(const cteas::puff::ControlFile& a, const char* ka,
                  const cteas::puff::ControlFile& b, const char* kb) {
    require(a.required_int(ka) == b.required_int(kb), std::string(ka) + "/" + kb + " mismatch");
}
void same_scalar(const cteas::puff::ControlFile& a, const char* ka,
                 const cteas::puff::ControlFile& b, const char* kb) {
    const auto lhs=a.required_float_list(ka),rhs=b.required_float_list(kb);
    require(lhs.size()==1U && rhs.size()==1U && lhs[0]==rhs[0],
            std::string(ka) + "/" + kb + " mismatch");
}
}
int main(int argc, char** argv) {
    try {
        require(argc==6, "usage: p7_original_met_grid_tests GRID_CMN PUFF_INP MET_DAT QAPNTS QARECG");
        const auto grid=cteas::puff::ControlFile::read_file(argv[1]);
        const auto control=cteas::puff::ControlFile::read_file(argv[2]);
        require(grid.required_one("IMAP")==control.required_one("PMAP") &&
                    grid.required_one("DATUM")==control.required_one("DATUM") &&
                    grid.required_one("LSOHEM")==control.required_one("UTMHEM"),
                "projection/datum/hemisphere authoring drift");
        same_integer(grid,"IUTMZN",control,"IUTMZN");
        same_integer(grid,"NX",control,"NX");
        same_integer(grid,"NY",control,"NY");
        same_integer(grid,"NZ",control,"NZ");
        same_scalar(grid,"XREFKM",control,"XORIGKM");
        same_scalar(grid,"YREFKM",control,"YORIGKM");
        same_scalar(grid,"DGRIDKM",control,"DGRIDKM");
        const auto zgrid=grid.required_float_list("ZFACE");
        const auto zpuff=control.required_float_list("ZFACE");
        require(zgrid==zpuff, "ZFACE differs between authoring and runtime grids");
        require(control.required_int("METFM")==1, "MET.DAT is not selected");
        const auto met=cteas::puff::Calmet21Reader::read(argv[3]);
        const auto& h=met.header;
        require(h.nx==grid.required_int("NX") && h.ny==grid.required_int("NY") &&
                    h.nz==grid.required_int("NZ"), "real MET.DAT grid extents differ");
        const double control_dx=control.required_float_list("DGRIDKM").at(0)*1000.0;
        require(std::abs(h.dx_m-control_dx)<0.001, "real MET.DAT spacing differs");
        const double control_x=control.required_float_list("XORIGKM").at(0)*1000.0;
        const double control_y=control.required_float_list("YORIGKM").at(0)*1000.0;
        require(std::abs(h.origin_x_m-control_x)<1.0 &&
                    std::abs(h.origin_y_m-control_y)<1.0,
                "real MET.DAT SW origin inconsistent with original frozen grid");
        const cteas::puff::OriginalMetGridFrame frame{
            h.origin_x_m,h.origin_y_m,h.dx_m};
        const auto source=cteas::puff::point_source_from_original_met_grid(control,frame);
        std::ifstream points(argv[4]);
        require(static_cast<bool>(points), "no frozen original qapnts.dat");
        std::string headline;
        require(static_cast<bool>(std::getline(points,headline)), "missing QA source header");
        double qx=0.0,qy=0.0,elev=0.0;
        int id=0;
        require(static_cast<bool>(points>>qx>>qy>>elev>>id) && id==1,
                "incorrect QA source count/type");
        require(real4_equals(source.x_m/1000.0,qx) &&
                    real4_equals(source.y_m/1000.0,qy),
                "REAL*4 MET.DAT-header-based source fails original point QA");

        const auto receptors=cteas::puff::receptors_from_original_met_grid(
            read_text(argv[2]),frame);
        std::ifstream receptor_rows(argv[5]);
        require(static_cast<bool>(receptor_rows), "no frozen original qarecg.dat");
        require(static_cast<bool>(std::getline(receptor_rows,headline)),
                "missing QA receptor header");
        std::size_t compared=0;
        while(receptor_rows>>qx>>qy>>elev) {
            require(compared<receptors.grid.size(), "extra original QA rows");
            const auto& rec=receptors.grid.at(compared);
            require(real4_equals(rec.x_km,qx) && real4_equals(rec.y_km,qy),
                    "REAL*4 MET.DAT-header-based receptor fails original QA " +
                    std::to_string(compared));
            ++compared;
        }
        require(receptor_rows.eof() && compared==2500U, "missing/invalid original QA rows");
        std::cout<<"P7_REAL_MET_GRID_QA=PASS GRID=50x50x9 MET_INTERVALS="<<met.intervals
                 <<" SOURCES=1 RECEPTORS="<<compared
                 <<" EXACT_REAL4=true GRID_CMN_AUTHORING_ONLY=true"
                 <<" INTERNAL_XPT1GRD_PARITY=NOT_YET_TESTED\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr<<"P7_REAL_MET_GRID_QA=FAIL "<<error.what()<<'\n';
        return 1;
    }
}
