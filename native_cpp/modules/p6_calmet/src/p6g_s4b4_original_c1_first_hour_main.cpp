// S4-B4 independent original-file-only first-hour extraction, NOT physics.
// Keeps exactly the vendor-produced first 45 hour fields and original static
// data; never copies their values to the separate native candidate.
#include "cteas/p6e/calmet_dat21.hpp"
#include <chrono>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace cteas::p6e;
int main(int argc,char** argv) {
    try {
        if(argc!=3)throw std::invalid_argument(
            "Usage: s4b4_extract_original_first_hour ORIGINAL_C1_143H_MET FIRST_HOUR_MET");
        const auto original=read_calmet_dat21(argv[1]);
        if(original.intervals!=143||original.fields_per_hour!=45||
           original.header.nx!=50||original.header.ny!=50||
           original.header.nz!=9||original.header.nssta!=1||
           original.header.nusta!=1)
            throw std::invalid_argument("S4B4 source is not the original scoped C1 143h");
        const auto first=original.hourly.front().begin;
        const auto last=original.hourly[44].end;
        if(first.year!=2022||first.julian_day!=1||first.hour!=0||
           last.year!=2022||last.julian_day!=1||last.hour!=1)
            throw std::invalid_argument("S4B4 original C1 first hour differs from frozen contract");
        auto h=original.header;
        h.run_hours=1;
        h.begin_year=2022;h.begin_month=1;h.begin_day=1;h.begin_hour=0;h.begin_second=0;
        h.end_year=2022;h.end_month=1;h.end_day=1;h.end_hour=1;h.end_second=0;
        std::vector<CalmetDat21Field> selected(original.hourly.begin(),
                                               original.hourly.begin()+45);
        write_calmet_dat21(argv[2],h,original.statics,selected);
        const auto replay=read_calmet_dat21(argv[2]);
        if(replay.intervals!=1||replay.fields_per_hour!=45||
           replay.hourly.size()!=selected.size())
            throw std::runtime_error("S4B4 vendor-first-hour extraction round trip failed");
        for(std::size_t j=0;j<selected.size();++j) {
            const auto& a=selected[j],&b=replay.hourly[j];
            if(a.label!=b.label||a.integer!=b.integer||
               a.real_values!=b.real_values||
               a.integer_values!=b.integer_values)
                throw std::runtime_error("S4B4 reserialized first-hour reference changed data");
        }
        std::cout<<"S4B4_ORIGINAL_C1_VENDOR_FROZEN_1H_EXTRACT=BYTE_EXACT_FIELD_VALUES"
                 <<" FIELDS=45 GRID=50x50 STATIONS=1SS_1US"
                 <<" VENDOR_FRESHLY_RERUN=NO\n";
    }catch(const std::exception& e) {
        std::cerr<<"S4B4_ORIGINAL_FIRST_HOUR_REFUSED "<<e.what()<<"\n";
        return 2;
    }
    return 0;
}
