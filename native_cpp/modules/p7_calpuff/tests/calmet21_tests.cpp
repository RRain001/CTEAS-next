#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/original_met_hours.hpp"
#include <algorithm>
#include <cstring>
#include <iostream>
#include <cassert>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>
namespace fs=std::filesystem;
using cteas::puff::Calmet21Reader;
namespace {
void put32(std::vector<std::uint8_t>& b,std::uint32_t v,std::size_t p) {
    assert(p+4<=b.size());
    for (int j=0;j<4;++j) b[p+j]=std::uint8_t(v>>(j*8));
}
void putint(std::vector<std::uint8_t>& b,int x,std::size_t p) {
    const std::int32_t i = static_cast<std::int32_t>(x);
    std::uint32_t bits = 0;
    static_assert(sizeof(i) == sizeof(bits));
    std::memcpy(&bits, &i, sizeof(bits));
    put32(b,bits,p);
}
void putfloat(std::vector<std::uint8_t>& b,float x,std::size_t p) {
    std::uint32_t bits = 0;
    static_assert(sizeof(x) == sizeof(bits));
    std::memcpy(&bits, &x, sizeof(bits));
    put32(b,bits,p);
}
void record(std::ofstream& f,const std::vector<std::uint8_t>& bytes) {
    const auto size=static_cast<std::uint32_t>(bytes.size());
    for (int j=0;j<4;++j) f.put(static_cast<char>(size>>(8*j)));
    f.write(reinterpret_cast<const char*>(bytes.data()),
            static_cast<std::streamsize>(bytes.size()));
    for (int j=0;j<4;++j) f.put(static_cast<char>(size>>(8*j)));
}
std::vector<std::string> field_names() {
    return {"U-LEV  1","V-LEV  1","WFACE  1","U-LEV  2","V-LEV  2","WFACE  2",
            "T-LEV  1","T-LEV  2","IPGT","USTAR","ZI","EL","WSTAR",
            "TEMPK","RHO","QSW","IRH"};
}
void create_fixture(const fs::path& path,bool order=false,bool gap=false,bool nan=false,
                    int static_mode=0) {
    std::ofstream f(path,std::ios::binary|std::ios::trunc);
    std::vector<std::uint8_t> signature(40,' ');
    const std::string id="CALMET.DAT 2.1";
    for (std::size_t i=0;i<id.size();++i) signature[i]=std::uint8_t(id[i]);
    record(f,signature);
    record(f,std::vector<std::uint8_t>(4,0));
    std::vector<std::uint8_t> h(112,0);
    const std::string tz="UTC+0000";
    for (std::size_t i=0;i<tz.size();++i) h[40+i]=std::uint8_t(tz[i]);
    putint(h,1,52); putint(h,2,56); putint(h,2,60); putint(h,2,64);
    putfloat(h,100.0F,68); putfloat(h,513000.0F,72);
    putfloat(h,3533000.0F,76); putint(h,1,80); putint(h,1,84); putint(h,1,88);
    record(f,h);
    // Original CALMET.DAT 2.1 OUTHD static records precede the U-LEV fields and
    // can be exactly Nx*Ny*4+24 bytes, i.e. the same length as a wind field.
    const std::string static_name="Z0";
    const std::size_t static_size = static_mode==1 ? 44U : 40U;   // mode 1 = malformed length
    std::vector<std::uint8_t> metadata(static_size,0);
    for (std::size_t i=0;i<8;++i)
        metadata[i]=i<static_name.size()?std::uint8_t(static_name[i]):' ';
    if (static_mode==2) putfloat(metadata,500.0F,24);             // out-of-range Z0
    record(f,metadata);
    for (int hour=0;hour<2;++hour) {
        auto labels=field_names();
        for (std::size_t i=0;i<labels.size();++i) {
            std::vector<std::uint8_t> b(40,0);
            const auto label=order && hour==0 && i==0 ? "NOTWIND" : labels[i];
            for (std::size_t k=0;k<8;++k) b[k]= k<label.size() ? std::uint8_t(label[k]) : ' ';
            const int shift=gap && hour==1 ? 1 : 0;
            putint(b,202200100+hour+shift,8); putint(b,0,12);
            putint(b,202200101+hour+shift,16); putint(b,0,20);
            for (int k=0;k<4;++k) {
                if (labels[i]=="IPGT" || labels[i]=="IRH") putint(b,11+k,24+4*k);
                else if (nan && hour==0 && i==0 && k==0)
                    put32(b,0x7FC00000U,24+4*k);
                else putfloat(b,2.5F+float(k),24+4*k);
            }
            record(f,b);
        }
    }
}
template<typename F> void must_fail(F fn) {
    bool threw=false;
    try {fn();} catch (const std::runtime_error&) {threw=true;}
    assert(threw);
}
struct Cleanup {fs::path root;~Cleanup(){std::error_code e;fs::remove_all(root,e);} };
}
std::uint64_t digest_ints(const std::vector<std::int32_t>& values) {
    std::uint64_t hash = 1469598103934665603ULL;
    for (const auto value : values) {
        for (int j = 0; j < 4; ++j) {
            hash ^= static_cast<std::uint64_t>((value >> (8 * j)) & 0xff);
            hash *= 1099511628211ULL;
        }
    }
    return hash;
}

std::uint64_t digest(const std::vector<float>& values) {
    std::uint64_t hash = 1469598103934665603ULL;
    for (const float value : values) {
        std::uint32_t bits = 0;
        std::memcpy(&bits, &value, sizeof(bits));
        for (int j = 0; j < 4; ++j) {
            hash ^= (bits >> (8 * j)) & 0xffU;
            hash *= 1099511628211ULL;
        }
    }
    return hash;
}

void describe(const char* name, const std::vector<float>& values) {
    float low = values.front(), high = values.front();
    double sum = 0.0;
    for (const float value : values) {
        low = std::min(low, value);
        high = std::max(high, value);
        sum += value;
    }
    std::cout << "P7G_STATIC " << name << " COUNT=" << values.size() << " MIN=" << low
              << " MAX=" << high << " MEAN=" << (sum / static_cast<double>(values.size()))
              << " DIGEST=" << digest(values) << "\n";
}

int main(int argc, char** argv) {
    if (argc == 3 && std::string(argv[1]) == "--met") {
        const auto summary = Calmet21Reader::read(argv[2]);
        const auto& statics = summary.statics;
        assert(summary.header.nx == 50 && summary.header.ny == 50 && summary.header.nz == 9);
        assert(statics.present && statics.decoded_records == 6);
        assert(statics.cell_face_m.size() == 10);
        assert(statics.roughness_m.size() == 2500 && statics.land_use.size() == 2500 &&
               statics.elevation_m.size() == 2500 && statics.leaf_area_index.size() == 2500 &&
               statics.nearest_station.size() == 2500);
        for (const float value : statics.roughness_m) assert(value >= 0.0F && value <= 100.0F);
        for (const float value : statics.leaf_area_index) assert(value >= 0.0F && value <= 20.0F);
        for (const auto value : statics.land_use) assert(value >= 0 && value <= 1000);
        for (const float value : statics.elevation_m) assert(value >= -1000.0F && value <= 10000.0F);
        // Pinned values of the immutable locked case (sha256 b1823cda...).
        assert(statics.roughness_m.front() == 0.25F && statics.roughness_m.back() == 0.25F);
        assert(statics.leaf_area_index.front() == 3.0F);
        const auto elevation_range =
            std::minmax_element(statics.elevation_m.begin(), statics.elevation_m.end());
        assert(*elevation_range.first == 25.0F && *elevation_range.second == 59.5F);
        assert(digest(statics.roughness_m) == 7401557581232649795ULL);
        assert(digest(statics.leaf_area_index) == 14015295161301286211ULL);
        assert(digest(statics.elevation_m) == 16152187619603912443ULL);
        assert(digest_ints(statics.land_use) == 3196964006486516483ULL);
        assert(digest_ints(statics.nearest_station) == 14033661785612014883ULL);
        describe("Z0", statics.roughness_m);
        describe("XLAI", statics.leaf_area_index);
        describe("ELEV", statics.elevation_m);
        std::cout << "P7G_STATIC_LAND_USE_DIGEST=" << digest_ints(statics.land_use)
                  << " NEAREST_DIGEST=" << digest_ints(statics.nearest_station) << "\n";
        std::cout << "P7G_REAL_MET_STATIC_DECODE=PASS INTERVALS=" << summary.intervals
                  << " HOURLY_FIELDS=" << summary.hourly_fields << "\n";
        return 0;
    }
    const auto root=fs::temp_directory_path()/"cteas_p7_calmet21_tests";
    fs::create_directories(root);
    Cleanup cleanup{root};
    const auto good=root/"correct.dat";
    create_fixture(good);
    std::size_t called=0,integers=0;
    const auto summary=Calmet21Reader::read(good.string(),[&](const auto& field){
        ++called;
        if (field.integer) {
            ++integers;
            assert(field.integer_values.size()==4 && field.integer_values.at(0)==11);
        } else {
            assert(field.real_values.size()==4 && field.real_values.at(0)==2.5F);
        }
    });
    assert(summary.intervals==2 && summary.hourly_fields==34);
    assert(summary.metadata_records==0);
    assert(summary.statics.present && summary.statics.decoded_records==1);
    assert(summary.statics.roughness_m.size()==4);
    assert(summary.statics.roughness_m.at(0)==0.0F);
    assert(summary.header.nx==2 && summary.header.ny==2 && summary.header.nz==2);
    assert(summary.final_end.unix_seconds-summary.first_begin.unix_seconds==7200);
    assert(called==34 && integers==4);
    std::size_t emitted_hours=0;
    std::uint64_t first_digest=0;
    const auto assembled=cteas::puff::OriginalMetHourlyReader::read(
        good.string(),[&](const auto& header,const auto& statics,const auto& hour) {
            assert(header.nx==2 && header.ny==2 && header.nz==2);
            assert(statics.roughness_m.size()==4);
            assert(hour.nx==2 && hour.ny==2 && hour.nz==2);
            assert(hour.u.size()==8 && hour.v.size()==8 && hour.w.size()==8 &&
                   hour.t.size()==8);
            assert(hour.ustar.size()==4 && hour.zi.size()==4 &&
                   hour.el.size()==4 && hour.tempk.size()==4 &&
                   hour.ipgt.size()==4 && hour.irh.size()==4);
            assert(hour.u.at(0)==2.5F && hour.u.at(7)==5.5F &&
                   hour.t.at(0)==2.5F);
            assert(hour.ipgt.at(0)==11 && hour.irh.at(3)==14);
            assert(hour.end.unix_seconds-hour.begin.unix_seconds==3600);
            const auto digest=hour.original_field_fingerprint();
            if(emitted_hours==0)first_digest=digest;
            else assert(first_digest==digest); // same fixture values, new hour
            ++emitted_hours;
        });
    assert(assembled.intervals==2 && emitted_hours==2);
    must_fail([&] {
        (void)cteas::puff::OriginalMetHourlyReader::read(
            good.string(),cteas::puff::OriginalMetHourlyReader::Observer{});
    });
    for (const auto& [name,wrong_order,gap,nan]:
         std::vector<std::tuple<std::string,bool,bool,bool>>{
             {"bad-order",true,false,false},
             {"bad-time",false,true,false},
             {"nan-input",false,false,true}}) {
        const auto p=root/name;
        create_fixture(p,wrong_order,gap,nan);
        must_fail([&]{(void)Calmet21Reader::read(p.string());});
        must_fail([&] {
            (void)cteas::puff::OriginalMetHourlyReader::read(
                p.string(),[](const auto&,const auto&,const auto&){});
        });
    }
    must_fail([&]{(void)Calmet21Reader::read(good.string(),{},true);});
    for (const auto& [name,mode] : std::vector<std::pair<std::string,int>>{
             {"bad-static-size",1},{"bad-static-value",2}}) {
        const auto p=root/name;
        create_fixture(p,false,false,false,mode);
        must_fail([&]{(void)Calmet21Reader::read(p.string());});
        must_fail([&] {
            (void)cteas::puff::OriginalMetHourlyReader::read(
                p.string(),[](const auto&,const auto&,const auto&){});
        });
    }
}
