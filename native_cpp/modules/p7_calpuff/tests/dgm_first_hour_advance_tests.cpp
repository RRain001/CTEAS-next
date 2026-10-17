#include "cteas/puff/control.hpp"
#include "cteas/puff/step_integration.hpp"
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
struct Record {
    std::array<std::int32_t,24> i;
    std::array<float,64> f;
};
static_assert(sizeof(Record)==352U && sizeof(float)==4U);
static_assert(std::endian::native==std::endian::little);

void check(bool ok,const char* reason) {
    if (!ok) throw std::runtime_error(reason);
}
bool identical_float(double observed,float original) {
    return static_cast<float>(observed)==original;
}
}
int main(int argc,char** argv) {
    try {
        check(argc==3,"usage: first-hour-advance ORIGINAL_PUFF_INP ORIGINAL_DGM_HOUR0");
        const auto ctrl=cteas::puff::ControlFile::read_file(argv[1]);
        check(ctrl.required_int("METFM")==1 && ctrl.required_int("NPT1")==1,
              "wrong selected CALMET 2022 control scope");
        const auto km=ctrl.required_float_list("DGRIDKM");
        check(km.size()==1U && km[0]>0.0,"missing grid spacing");
        const float spacing=static_cast<float>(static_cast<float>(km[0])*1000.0F);
        check(spacing==100.0F,"selected case must use 100m cells");

        std::ifstream file(argv[2],std::ios::binary);
        check(static_cast<bool>(file),"missing original DGM hour0");
        std::size_t compared=0,changed=0;
        double max_xy_absolute_error=0.0, max_distance_error=0.0;
        Record row{};
        while(file.read(reinterpret_cast<char*>(&row),sizeof(row))) {
            ++compared;
            check(row.i[0]==1 && row.i[1]==202200100,
                  "original puff-step row does not belong to first hour");
            const auto& f=row.f;
            // Source: CALPUFF COMP L10528-10619, read from original
            // instrumented COMP at L10942. Use Fortran's *actual*
            // post-RISEWIND/calm UADV/VADV/WS and final TSAMP; do not
            // substitute the early sampling-cadence estimate.
            const cteas::puff::AdvanceInputs input{
                .x_cells=f[0], .y_cells=f[1],
                .u_ms=f[12], .v_ms=f[13],
                .step_s=f[62], .grid_spacing_m=spacing, .wind_speed_ms=f[11]};
            const auto cpp=cteas::puff::advance_puff(input);
            const bool ok=identical_float(cpp.x_cells,f[38]) &&
                          identical_float(cpp.y_cells,f[39]) &&
                          identical_float(cpp.distance_m,f[59]);
            max_xy_absolute_error=std::max(max_xy_absolute_error,
                std::max(std::fabs(cpp.x_cells-f[38]),std::fabs(cpp.y_cells-f[39])));
            max_distance_error=std::max(max_distance_error,
                std::fabs(cpp.distance_m-f[59]));
            if (!ok) {
                ++changed;
                if (changed<=4U) {
                    std::cerr<<"P7_FIRST_HOUR_STEP_DIFFERENCE RECORD="<<compared
                             <<" PUFF="<<row.i[3]<<" SAMPLE="<<row.i[16]
                             <<" FORTRAN_X="<<f[38]<<" CPP_X="<<cpp.x_cells
                             <<" FORTRAN_Y="<<f[39]<<" CPP_Y="<<cpp.y_cells
                             <<" FORTRAN_DISTM="<<f[59]<<" CPP_DISTM="<<cpp.distance_m
                             <<'\n';
                }
            }
        }
        check(file.eof() && file.gcount()==0,"original first hour dump truncated");
        check(compared==1275U,"incorrect original first hour count");
        if (changed) {
            std::cerr<<"P7_FIRST_HOUR_ADVANCE_ORACLE=FAIL RECORDS="<<compared
                     <<" MISMATCHES="<<changed<<" MAX_XY_ERROR="<<max_xy_absolute_error
                     <<" MAX_DISTM_ERROR="<<max_distance_error<<'\n';
            return 1;
        }
        std::cout<<"P7_FIRST_HOUR_ADVANCE_ORACLE=PASS RECORDS="<<compared
                 <<" MISMATCHES=0 REAL4=EXACT"
                 <<" ORACLE_WIND_AND_PREVIOUS_POSITIONS=true"
                 <<" AUTONOMOUS_1H_PUFF_TRAJECTORY=NOT_YET_TESTED\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"P7_FIRST_HOUR_ADVANCE_ORACLE=FAIL "<<e.what()<<'\n';
        return 1;
    }
}
