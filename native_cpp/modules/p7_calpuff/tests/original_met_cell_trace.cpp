#include "cteas/puff/original_met_cell.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
struct Record {std::array<std::int32_t,24> i;std::array<float,64> f;};
static_assert(sizeof(Record)==352U);
static_assert(std::endian::native==std::endian::little);
void require(bool valid,const char* why) {if(!valid)throw std::runtime_error(why);}
template<class F> void must_reject(F&& action) {
    bool rejected=false;
    try{action();}catch(const std::invalid_argument&){rejected=true;}
    catch(const std::out_of_range&){rejected=true;}
    require(rejected,"invalid original MET cell accepted");
}
}

int main(int argc,char** argv) {
    try {
        using namespace cteas::puff;
        require(argc==3 || argc==4,
                "usage: original_met_cell_trace ORIGINAL_MET_DAT ORIGINAL_DGM [1|143]");
        const int hours=argc==3?1:std::stoi(argv[3]);
        require(hours==1 || hours==143,"only locked 1/143h scopes accepted");
        must_reject([]{(void)original_met_cell(-0.01F,25.0F,50,50);});
        must_reject([]{(void)original_met_cell(50.0F,25.0F,50,50);});
        must_reject([]{(void)original_met_cell(25.0F,std::nanf(""),50,50);});
        require(original_met_cell(25.0F,25.0F,50,50).ix_1based==26,
                "integer original grid coordinate incorrectly indexed");
        require(original_met_cell(24.613815F,25.903828F,50,50).ix_1based==25,
                "fractional original grid coordinate incorrectly indexed");
        std::ifstream input(argv[2],std::ios::binary);
        require(static_cast<bool>(input),"original DGM absent");

        // DGM is ordered by actual CALPUFF hour/puff/substep. Stream records
        // instead of loading the 89.6 MB original into memory. The unmodified
        // Fortran DGM SHA is checked by the calling workflow BEFORE this test.
        Record next{};
        bool pending=static_cast<bool>(input.read(
            reinterpret_cast<char*>(&next),sizeof(next)));
        require(pending,"empty original DGM");
        std::size_t compared_hours=0,matched_cell=0,wind_exact=0,wind_mismatch=0,
                    stable_match=0;
        float max_u=0.0F,max_v=0.0F;
        const auto summary=OriginalMetHourlyReader::read(
            argv[1],[&](const Calmet21Header& header,const Calmet21Static& statics,
                          const OriginalMetHour& hour) {
                require(header.nx==50 && header.ny==50 && header.nz==9,
                        "frozen original MET dimensions mismatch");
                const int hour_index=(hour.begin.julian_day-1)*24+hour.begin.hour;
                if(hour_index>=hours)return;
                require(hour.begin.year==2022 && hour_index==static_cast<int>(compared_hours),
                        "original MET hour order changed");
                const int packed=hour.begin.year*100000+
                                 hour.begin.julian_day*100+hour.begin.hour;
                while(pending && next.i[1]==packed) {
                    const auto& r=next;
                    require(r.i[0]==1 && r.i[2]==0,
                            "wrong DGM puff record type or original time seconds");
                    const auto cell=original_met_cell(r.f[0],r.f[1],
                                                     header.nx,header.ny);
                    if(cell.ix_1based!=r.i[5] || cell.iy_1based!=r.i[6]) {
                        std::cerr<<"P7_GETCELL_FIRST_DIFFERENCE ROW="<<matched_cell+1
                                 <<" HOUR="<<hour_index
                                 <<" ORIGINAL=("<<r.i[5]<<","<<r.i[6]<<")"
                                 <<" NATIVE=("<<cell.ix_1based<<","
                                 <<cell.iy_1based<<")\n";
                        throw std::runtime_error("original GETCELL index diverged");
                    }
                    ++matched_cell;
                    if(hour.ipgt.at(cell.offset_0based)==r.i[8])++stable_match;
                    // PUFFDZ ZTOP/ZBOT still from the original DGM oracle.
                    const auto wind=original_met_cell_advect(
                        hour,statics,cell,r.f[8],r.f[7]);
                    const float u=static_cast<float>(wind.u_ms);
                    const float v=static_cast<float>(wind.v_ms);
                    if(u==r.f[9] && v==r.f[10]) ++wind_exact;
                    else {
                        ++wind_mismatch;
                        max_u=std::max(max_u,std::abs(u-r.f[9]));
                        max_v=std::max(max_v,std::abs(v-r.f[10]));
                        if(wind_mismatch<=5)
                            std::cerr<<"P7_MET_ADVECT_FIRST_DIFFERENCE ROW="
                                     <<matched_cell<<" HOUR="<<hour_index
                                     <<" PUFF="<<r.i[3]
                                     <<" CELL=("<<cell.ix_1based<<","
                                     <<cell.iy_1based<<")"
                                     <<" NATIVE_U="<<u<<" ORIGINAL_U="<<r.f[9]
                                     <<" NATIVE_V="<<v<<" ORIGINAL_V="<<r.f[10]<<"\n";
                    }
                    pending=static_cast<bool>(input.read(
                        reinterpret_cast<char*>(&next),sizeof(next)));
                }
                if(pending && next.i[1]<packed)
                    throw std::runtime_error("original DGM hour order regressed");
                ++compared_hours;
            },true);
        require(summary.intervals==143 &&
                compared_hours==static_cast<std::size_t>(hours),
                "original native MET hourly traversal incomplete");
        const std::size_t required=hours==1?1275U:254687U;
        require(matched_cell==required,
                "wrong original 1/143-hour DGM comparison record count");
        if(hours==143)
            require(!pending && input.eof() && input.gcount()==0,
                    "original full DGM trailing or truncated data");
        else
            require(!pending && input.eof() && input.gcount()==0,
                    "frozen first-hour DGM contains extra hours");
        std::cout<<"P7_NATIVE_GETCELL_INDEX=PASS HOURS="<<hours
                 <<" ORIGINAL_RECORDS="<<matched_cell
                 <<" NATIVE_1BASED_CELL=EXACT\n";
        std::cout<<"P7_NATIVE_ADVECT_PROFILE_DIAGNOSTIC HOURS="<<hours
                 <<" EXACT="<<wind_exact<<" DIFFERENT="<<wind_mismatch
                 <<" PGT_MATCH="<<stable_match
                 <<" MAX_U_DIFF="<<max_u<<" MAX_V_DIFF="<<max_v<<"\n";
        if(wind_mismatch!=0) {
            std::cerr<<"P7_NATIVE_METFM1_ADVECT=NOT_YET_EQUIVALENT"
                     <<" SCOPE_HOURS="<<hours
                     <<" CHECK_GETCELL_PROFILE_3D\n";
            return 2;
        }
        std::cout<<"P7_NATIVE_METFM1_ADVECT=PASS HOURS="<<hours
                 <<" RECORDS="<<wind_exact
                 <<" REAL4_EXACT=TRUE PUFFDZ_ORACLE_FED=TRUE\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"P7_NATIVE_METFM1_ADVECT=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
