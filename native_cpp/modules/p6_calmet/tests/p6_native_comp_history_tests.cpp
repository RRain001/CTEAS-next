#include "cteas/p6/native_comp_history.hpp"
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using cteas::calmet::p6::NativeCompHistory;

namespace {
void need(bool value, const std::string& reason) {
    if (!value) throw std::runtime_error(reason);
}
template<typename F>
void must_reject(F fn, const std::string& reason) {
    bool failed = false;
    try { fn(); } catch (const std::exception&) { failed = true; }
    need(failed, reason);
}
void write_text(const fs::path& p, const std::string& value) {
    fs::create_directories(p.parent_path());
    std::ofstream out(p, std::ios::binary | std::ios::trunc);
    if (!(out << value)) throw std::runtime_error("fixture text write failed");
}
void write_f32(const fs::path& p, float val) {
    fs::create_directories(p.parent_path());
    const std::vector<float> data(NativeCompHistory::kCells, val);
    std::ofstream out(p, std::ios::binary | std::ios::trunc);
    out.write(reinterpret_cast<const char*>(data.data()),
              static_cast<std::streamsize>(data.size() * sizeof(float)));
    if (!out) throw std::runtime_error("fixture float write failed");
}
void produce(const fs::path& p, int hour, float base) {
    write_text(fs::path(p.string()+".state.json"),
        "{\"producer\": \"p6e_calmet_dat21 emit-realcase\","
        "\"first_hour_zero_based\": "+std::to_string(hour)+","
        "\"shape\": [1, 50, 50],\"dptt\": true}\n");
    write_f32(fs::path(p.string()+".zi.f32"),base+1.0f);
    write_f32(fs::path(p.string()+".ziconv.f32"),base+2.0f);
    write_f32(fs::path(p.string()+".dptt.f32"),-base-3.0f);
}
std::string bytes(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    if (!in) throw std::runtime_error("missing file " + p.string());
    return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("requires unique CTest output directory");
        const fs::path root = fs::absolute(argv[1]);
        fs::remove_all(root);
        fs::create_directories(root);

        const auto prefix = root/"history/comp";
        NativeCompHistory history(prefix);
        const auto zero = root/"incoming/h000/comp";
        produce(zero, 0, 0.0f);
        // Fail-closed: missing a single thermal state must leave ALL histories absent.
        fs::remove(fs::path(zero.string()+".dptt.f32"));
        must_reject([&]{ history.commit(0,zero); }, "missing DPTT not rejected");
        need(history.completed_hours()==0, "hour advanced on missing DPTT");
        for(const char* name:{"zi.f32","ziconv.f32","dptt.f32","state.json"})
            need(!fs::exists(fs::path(prefix.string()+"."+name)),
                 "partial COMP history was made visible");
        produce(zero,0,0.0f);
        // Fail-closed: malformed header or non-finite/negative ZI/ZICONV.
        write_text(fs::path(zero.string()+".state.json"),
            "{\"producer\":\"unknown\",\"first_hour_zero_based\":0,"
            "\"shape\":[1,50,50],\"dptt\":true}");
        must_reject([&]{history.commit(0,zero);},"untrusted producer accepted");
        produce(zero,0,0.0f);
        write_f32(fs::path(zero.string()+".zi.f32"),
                  std::numeric_limits<float>::quiet_NaN());
        must_reject([&]{history.commit(0,zero);},"NaN ZI accepted");
        produce(zero,0,0.0f);
        write_f32(fs::path(zero.string()+".ziconv.f32"),-0.5f);
        must_reject([&]{history.commit(0,zero);},"negative ZICONV accepted");
        produce(zero,0,0.0f);
        // The failed trials above must not leave stale '.pending' files.
        history.commit(0,zero);
        need(history.completed_hours()==1,"zero hour not committed");
        for(const char* name:{"zi","ziconv","dptt"}) {
            const fs::path state=fs::path(prefix.string()+"."+name+".f32");
            need(fs::file_size(state)==NativeCompHistory::kBytes,
                 "first hour state has wrong length");
            need(bytes(state)==bytes(fs::path(zero.string()+"."+name+".f32")),
                 "first hour state has wrong content");
        }
        must_reject([&]{history.commit(0,zero);},"repeated hour accepted");
        must_reject([&]{history.commit(2,zero);},"skipped hour accepted");

        const auto one = root/"incoming/h001/comp";
        produce(one,1,5.0f);
        // Reject a late missing field, checking every history remains hour-0.
        fs::remove(fs::path(one.string()+".zi.f32"));
        must_reject([&]{history.commit(1,one);},"missing second-hour ZI accepted");
        need(history.completed_hours()==1, "hour advanced after second-hour failure");
        for(const char* name:{"zi","ziconv","dptt"})
            need(fs::file_size(fs::path(prefix.string()+"."+name+".f32"))==
                     NativeCompHistory::kBytes,
                 "prior committed state changed on rejected next hour");
        produce(one,1,5.0f);
        history.commit(1,one);
        need(history.completed_hours()==2,"second hour not committed");
        for(const char* name:{"zi","ziconv","dptt"}) {
            const fs::path state=fs::path(prefix.string()+"."+name+".f32");
            need(fs::file_size(state)==2*NativeCompHistory::kBytes,
                 "second hour state size wrong");
            need(bytes(state)==bytes(fs::path(zero.string()+"."+name+".f32"))+
                 bytes(fs::path(one.string()+"."+name+".f32")),
                 "source REAL*4 history byte sequence changed");
        }
        need(bytes(fs::path(prefix.string()+".state.json"))==
                 bytes(fs::path(one.string()+".state.json")),
             "latest committed native metadata not preserved");
        must_reject([&]{NativeCompHistory duplicate(prefix);(void)duplicate;},
                    "previous committed history silently reinitialized");
        fs::remove_all(root);
        std::cout<<"PASS_P6_NATIVE_COMP_HISTORY "
                 <<"initial zero state, 2 consecutive REAL4 commits, "
                 <<"missing/nonfinite/provenance rejection, "
                 <<"unchanged prior state on failed transition, "
                 <<"no resume or oracle backfill\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<"FAIL_P6_NATIVE_COMP_HISTORY: "<<e.what()<<'\n';
        return 1;
    }
}
