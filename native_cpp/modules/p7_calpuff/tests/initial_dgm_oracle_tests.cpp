#include "cteas/puff/control.hpp"
#include "cteas/puff/release.hpp"
#include "cteas/puff/original_precision.hpp"

#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
struct OriginalDgmRecord {
    std::array<std::int32_t,24> header;
    std::array<float,64> real;
};
static_assert(sizeof(OriginalDgmRecord)==352U);
static_assert(sizeof(float)==4 && sizeof(std::int32_t)==4);
static_assert(std::endian::native==std::endian::little,
              "Original locked DGM dump is little-endian");

void check(bool ok, const char* what) {
    if (!ok) throw std::runtime_error(what);
}
float original_cell(float src_km, float origin_km, float spacing_km) {
    return (src_km-origin_km)/spacing_km;
}
}
int main(int argc,char** argv) {
    try {
        check(argc==3, "usage: oracle_first_hour ORIGINAL_PUFF_INP ORIGINAL_DGM_HOUR0");
        using namespace cteas::puff;
        const auto c=ControlFile::read_file(argv[1]);
        check(c.required_int("NPT1")==1 && c.required_int("METFM")==1,
              "not selected one-point-source METFM=1 case");
        const auto source=c.required_float_list("X");
        const auto xo=c.required_float_list("XORIGKM");
        const auto yo=c.required_float_list("YORIGKM");
        const auto dx=c.required_float_list("DGRIDKM");
        check(source.size()==10 && xo.size()==1 && yo.size()==1 && dx.size()==1,
              "frozen source/grid fields missing");
        const float x=original_cell(original_real_from_text(source[0]),
                                    original_real_from_text(xo[0]),
                                    original_real_from_text(dx[0]));
        const float y=original_cell(original_real_from_text(source[1]),
                                    original_real_from_text(yo[0]),
                                    original_real_from_text(dx[0]));
        check(x==25.0f && y==25.0f,"selected original internal source is not cell (25,25)");
        std::ifstream input(argv[2],std::ios::binary);
        check(static_cast<bool>(input),"missing pinned original Fortran DGM first-hour slice");
        std::size_t total=0, initial=0, matched=0;
        OriginalDgmRecord row{};
        while(input.read(reinterpret_cast<char*>(&row),sizeof(row))) {
            ++total;
            check(row.header[1]==202200100 && row.header[0]==1,
                  "wrong DGM hour or record kind");
            // iold (13th int) == 0 for new puffs. The first substep has
            // ksam (17th) == nsstr (12th).
            if (row.header[12]!=0 || row.header[16]!=row.header[11]) continue;
            ++initial;
            if (row.real[0]!=x || row.real[1]!=y) continue;
            NewPuffInputs values{};
            // XPT1GRD/YPT1GRD are relative MET-GRID CELL coordinates,
            // not absolute UTM kilometres despite this legacy member name.
            values.source_x_km=x;
            values.source_y_km=y;
            // Height and source sigma below are fed FROM the original DGM.
            // They test state storage, NOT independent GRiSE or sigma physics.
            values.effective_height_m=row.real[2];
            values.sigma_y_source_m=row.real[21];
            values.sigma_z_source_m=row.real[22];
            values.source_index=1;
            values.source_type=1;
            const auto state=new_puff_state(values);
            check(static_cast<float>(state.x_km)==row.real[0] &&
                  static_cast<float>(state.y_km)==row.real[1] &&
                  static_cast<float>(state.x_km)==row.real[23] &&
                  static_cast<float>(state.y_km)==row.real[24],
                  "original C++ newly released /PUFF/ relative XY diverges");
            check(static_cast<float>(state.final_height_m)==row.real[2] &&
                  row.real[2]==row.real[25],
                  "original puff height storage diverges (oracle-fed height)");
            ++matched;
        }
        check(input.eof(), "truncated original DGM record (not exact 352 bytes)");
        check(total==1275U && initial>0 && matched==initial,
              "initial puff coordinates/record count differ from original DGM");
        std::cout << "P7_ORIGINAL_INITIAL_PUFF_INTERNAL_XY=PASS"
                  << " ORIGINAL_RECORDS=" << total << " INITIAL_NEW_PUFFS=" << initial
                  << " MATCHED=" << matched << " INTERNAL_CELLS=25,25"
                  << " HEIGHT_FROM_FORTRAN_ORACLE=true"
                  << " RISE_SOLVER_PARITY=NOT_YET_TESTED"
                  << " FULL_PUFF_DRIVER_PARITY=NOT_YET_TESTED\n";
    } catch(const std::exception& e) {
        std::cerr << "P7_ORIGINAL_INITIAL_PUFF_INTERNAL_XY=FAIL " << e.what() << '\n';
        return 1;
    }
}
