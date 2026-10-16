#include "cteas/puff/hourly_conc.hpp"
#include "cteas/puff/original_wrout1_hefei.hpp"
#include "cteas/puff/fortran_records.hpp"

#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <regex>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
namespace fs = std::filesystem;

void require(bool value, const char* why) {
    if (!value) throw std::runtime_error(why);
}

template <class Fn>
void reject(Fn&& f, const char* why) {
    bool thrown = false;
    try { f(); } catch (const std::invalid_argument&) { thrown = true; }
    require(thrown, why);
}

cteas::puff::ConcPeriod hour(int year, int day, int start_hour) {
    cteas::puff::ConcPeriod p;
    p.begin_year = year;
    p.begin_julian = day;
    p.begin_hour = start_hour;
    p.end_year = year;
    p.end_julian = day;
    p.end_hour = start_hour + 1;
    if (p.end_hour == 24) {
        p.end_hour = 0;
        ++p.end_julian;
        const bool leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
        if (p.end_julian > (leap ? 366 : 365)) {
            p.end_julian = 1;
            ++p.end_year;
        }
    }
    return p;
}

void original_2022_series(const fs::path& path) {
    using namespace cteas::puff;
    std::vector<std::vector<float>> expected;
    {
        ConcFileWriter out(path.string(), "2.2", "native DATA-only hourly test", {});
        const auto grid = original_total_source_descriptor(510885.0F, 3531269.0F);
        require(grid.source_type==0 && grid.source_index==1 &&
                grid.source_name=="TOTAL" && grid.y_map_km==3531.269287109375,
                "MET origin must preserve original REAL*4 multiplication");
        HourlyConcSeriesWriter series(out, grid, 50, 50);
        for (int t = 0; t < 143; ++t) {
            std::vector<float> cells(2500U, 0.0F);
            cells[static_cast<std::size_t>(t)] = static_cast<float>(t + 1) / 128.0F;
            cells[static_cast<std::size_t>(2499 - t)] = -static_cast<float>(t + 1) / 256.0F;
            const auto period = hour(2022, 1 + t / 24, t % 24);
            series.write_hour(period, cells);
            expected.push_back(std::move(cells));
        }
        require(series.hours_written() == 143U, "143 hours not emitted");
        require(out.records_written() == 429U, "wrong number of hourly DATA records");
        out.close();
    }
    const auto sum = summarize_conc_file(path.string());
    require(sum.period_records == 143U && sum.grid_records == 143U &&
            sum.species_field_records == 143U, "hourly output order/count mismatch");
    const auto periods = read_conc_periods(path.string());
    const auto fields = read_conc_species_fields(path.string(), 50, 50);
    require(periods.size() == 143U && fields.size() == 143U,
            "read-back lost an hourly field");
    for (std::size_t t = 0; t < 143U; ++t) {
        const auto wanted = hour(2022, 1 + static_cast<int>(t / 24U),
                                  static_cast<int>(t % 24U));
        const auto& got = periods[t];
        require(got.begin_year == wanted.begin_year &&
                got.begin_julian == wanted.begin_julian &&
                got.begin_hour == wanted.begin_hour &&
                got.end_julian == wanted.end_julian &&
                got.end_hour == wanted.end_hour, "timestamp mismatch");
        require(fields[t].label == "H-3     " && fields[t].species_index == 1 &&
                fields[t].values.size() == 2500U, "H-3 field metadata mismatch");
        for (std::size_t i = 0; i < 2500U; ++i) {
            require(std::bit_cast<std::uint32_t>(fields[t].values[i]) ==
                    std::bit_cast<std::uint32_t>(expected[t][i]),
                    "native hourly concentration payload bits changed");
        }
    }
}

void vendor_source_record_bytes(const fs::path& path) {
    using namespace cteas::puff;
    {
        ConcFileWriter out(path.string(),"2.2","typed source descriptor",{});
        out.write_source_descriptor({1,7,"STACK07",513.3846435546875,
                                     3533.768798828125});
        out.close();
    }
    FortranRecordReader reader(path.string(),4,RecordByteOrder::LittleEndian);
    std::vector<std::uint8_t> rec;
    require(reader.next(rec) && rec.size()==96,"missing CONC version");
    require(reader.next(rec) && rec.size()==4,"missing comment count");
    require(reader.next(rec) && rec.size()==32,"OUTPUT source record size is not 32");
    std::int32_t type=0,index=0;
    float x=0,y=0;
    std::memcpy(&type,rec.data(),4);
    std::memcpy(&index,rec.data()+4,4);
    std::memcpy(&x,rec.data()+24,4);
    std::memcpy(&y,rec.data()+28,4);
    require(type==1 && index==7 &&
            std::string(reinterpret_cast<const char*>(rec.data()+8),16)
                 =="STACK07         " &&
            x==513.3846435546875F && y==3533.768798828125F,
            "OUTPUT KTYPE/KSOURCE/CSRCNAM/XMAPKM/YMAPKM differs from source");
    bool rejects_total=false;
    try{
        ConcFileWriter bad(path.string()+"-invalid","2.2","bad",{});
        bad.write_source_descriptor({0,2,"TOTAL",0,0});
    }catch(const std::invalid_argument&){rejects_total=true;}
    require(rejects_total,"TOTAL record allowed invalid KTYPE/KSOURCE");
}
void frozen_wrout1_identifiers(const fs::path& original,
                              const fs::path& control,
                              const fs::path& met,
                              const fs::path& native) {
    using namespace cteas::puff;
    std::ifstream deck(control);
    require(bool(deck),"frozen puff.inp unavailable for source-derived titles");
    const std::string control_text{
        std::istreambuf_iterator<char>(deck),std::istreambuf_iterator<char>()};
    auto native_output=create_original_hefei_2022_wrout1_writer(
        native.string(),control_text,met.string());
    require(native_output->records_written()==6U,
            "frozen WROUT1 typed header writer count changed");
    native_output->close();
    FortranRecordReader orig(original.string(),4,RecordByteOrder::LittleEndian);
    FortranRecordReader generated(native.string(),4,RecordByteOrder::LittleEndian);
    std::vector<std::uint8_t> a,b;
    require(orig.next(a)&&a.size()==96 &&
            generated.next(b)&&b.size()==96 && a==b,
            "source-derived original WROUT1 version record is not binary exact");
    require(orig.next(a)&&generated.next(b)&&a.size()==4U&&a==b,
            "native WROUT1 embedded comment count differs from vendor");
    std::int32_t comments=0;
    std::memcpy(&comments,a.data(),4);
    require(comments==3218,"original WROUT1 embedded comment count changed");
    for(int i=0;i<comments;++i)
        require(orig.next(a)&&generated.next(b)&&a.size()==132U&&a==b,
                "source-driven WROUT1 embedded comment differs from original");
    std::cout<<"P7_ORIGINAL_WROUT1_EMBEDDED_ECHO=PASS"
             <<" COMMENTS=3218"
             <<" SOURCE=CONTROL_PLUS_CALMET_DAT"
             <<" BINARY_EXACT=YES\\n";
    require(orig.next(a)&&generated.next(b)&&a.size()==300U&&
            a==b,"native source-derived 300B run parameters differ from frozen WROUT1");
    require(orig.next(a)&&generated.next(b)&&a.size()==52U&&
            a==b,"native source-type counters do not match frozen WROUT1");
    for(const auto bytes:{240U,15U,16U,20U}){
        require(orig.next(a)&&generated.next(b)&&
                a.size()==bytes&&b.size()==bytes&&a==b,
                "source-derived WROUT1 metadata differs from frozen original");
    }
    std::cout<<"P7_ORIGINAL_WROUT1_FULL_3226_HEADER_RECORDS=PASS"
             <<" RECORD_BYTES=96,4,3218x132,300,52,240,15,16,20"
             <<" FROZEN_BINARY_RECORDS=BITWISE_EXACT"
             <<" RECEPTOR_CONCENTRATION_429_RECORDS=NOT_YET_ACCEPTED"
             <<" FULL_PUFF_CON=NOT_YET_ACCEPTED\\n";
}

void invalid_and_year_boundary(const fs::path& path) {
    using namespace cteas::puff;
    ConcFileWriter out(path.string(), "2.2", "boundary test", {});
    const auto grid = original_met_grid_descriptor(510885.0F, 3531269.0F);
    reject([&] { HourlyConcSeriesWriter invalid(out, grid, 0, 50); },
           "zero-sized grid accepted");
    reject([&] {
        auto invalid_grid = grid;
        invalid_grid.group_index = 0;
        HourlyConcSeriesWriter invalid(out, invalid_grid, 2, 2);
    }, "zero group index accepted");
    HourlyConcSeriesWriter series(out, grid, 2, 2);
    std::vector<float> values(4U, 1.0F);
    reject([&] { series.write_hour(hour(2022, 366, 23), values); },
           "non-leap Julian 366 accepted");
    reject([&] { series.write_hour(hour(2022, 365, 23), {1.0F}); },
           "wrong receptor count accepted");
    auto bad = values;
    bad[0] = std::nanf("");
    reject([&] { series.write_hour(hour(2022, 365, 23), bad); },
           "non-finite concentration accepted");
    const auto last_2022 = hour(2022, 365, 23);
    series.write_hour(last_2022, values);
    require(series.hours_written() == 1U && out.records_written() == 3U,
            "failed write must not alter DATA output");
    reject([&] { series.write_hour(last_2022, values); },
           "duplicate hour accepted");
    reject([&] { series.write_hour(hour(2023, 1, 1), values); },
           "missing next year hour accepted");
    series.write_hour(hour(2023, 1, 0), values);
    series.write_hour(hour(2023, 1, 1), values);
    require(series.hours_written() == 3U && out.records_written() == 9U,
            "cross-year hourly continuity lost");
    out.close();
}
} // namespace

int main(int argc,char** argv) {
    const auto stamp = std::chrono::high_resolution_clock::now()
                           .time_since_epoch().count();
    const auto root = fs::temp_directory_path() /
                      ("cteas-p7-hourly-" + std::to_string(stamp));
    try {
        fs::create_directories(root);
        original_2022_series(root / "native-143-data.con");
        vendor_source_record_bytes(root / "source-record.con");
        invalid_and_year_boundary(root / "boundary.con");
        if(argc==5 && std::string(argv[1])=="--frozen")
            frozen_wrout1_identifiers(argv[2],argv[3],argv[4],
                                     root / "full-wrout1-native-header.con");
        else if(argc!=1)
            throw std::invalid_argument("expected --frozen puff.con puff.inp met.dat");
        fs::remove_all(root);
        std::cout << "P7E_NATIVE_143H_HOURLY_DATA=PASS HOURS=143 RECORDS=429"
                  << " GRID_CELLS=2500 REAL4_VALUES=EXACT CLOCK=CONTIGUOUS"
                  << " OUTPUT_SOURCE_DESCRIPTOR=VENDOR_LAYOUT"
                  << " ORIGINAL_FULL_CONC_PARITY=NOT_CLAIMED\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "P7E_NATIVE_143H_HOURLY_DATA=FAIL " << e.what() << '\n';
        return 1;
    }
}
