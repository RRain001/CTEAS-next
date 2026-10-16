#include "cteas/puff/fortran_records.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

using cteas::puff::FortranRecordReader;
using cteas::puff::RecordByteOrder;
namespace fs = std::filesystem;

namespace {
void put_marker(std::ofstream& out, std::uint64_t number, unsigned width, bool big) {
    std::array<std::uint8_t, 8> bytes{};
    for (unsigned i = 0; i < width; ++i) {
        const unsigned shift = 8U * (big ? width - 1 - i : i);
        bytes[i] = static_cast<std::uint8_t>((number >> shift) & 255U);
    }
    out.write(reinterpret_cast<const char*>(bytes.data()), width);
}
void emit_record(std::ofstream& out, const std::vector<std::uint8_t>& data, unsigned width,
                 bool big, bool bad_trailer = false) {
    put_marker(out, data.size(), width, big);
    out.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size()));
    put_marker(out, data.size() + (bad_trailer ? 1U : 0U), width, big);
}

template <class F>
void expect_failure(F function) {
    bool failed = false;
    try { function(); } catch (const std::exception&) { failed = true; }
    assert(failed);
}

struct ScopedTemp {
    fs::path root;
    ~ScopedTemp() { std::error_code ec; fs::remove_all(root, ec); }
};
} // namespace

int main() {
    auto root = fs::temp_directory_path() / "cteas_p7_record_contract";
    fs::create_directories(root);
    ScopedTemp cleanup{root};
    for (unsigned width : {4U, 8U}) {
        for (bool big : {false, true}) {
            const auto path = root / (std::to_string(width) + (big ? "be" : "le"));
            {
                std::ofstream out(path, std::ios::binary | std::ios::trunc);
                emit_record(out, {1U, 2U, 3U, 4U}, width, big);
                emit_record(out, {}, width, big);
            }
            FortranRecordReader reader(path.string(), width,
                big ? RecordByteOrder::BigEndian : RecordByteOrder::LittleEndian);
            std::vector<std::uint8_t> payload;
            assert(reader.next(payload) && (payload == std::vector<std::uint8_t>{1, 2, 3, 4}));
            assert(reader.next(payload) && payload.empty());
            assert(!reader.next(payload));
            assert(reader.records_read() == 2);
            // A 3-byte safety bound must reject the 4-byte first record.
            expect_failure([&] {
                FortranRecordReader short_limit(path.string(), width,
                    big ? RecordByteOrder::BigEndian : RecordByteOrder::LittleEndian, 3);
                (void)short_limit.next(payload);
            });
        }
    }
    const auto bad = root / "bad-trailer";
    {
        std::ofstream out(bad, std::ios::binary | std::ios::trunc);
        emit_record(out, {5, 6}, 4, false, true);
    }
    expect_failure([&] {
        FortranRecordReader r(bad.string());
        std::vector<std::uint8_t> bytes;
        (void)r.next(bytes);
    });
    const auto short_header = root / "short-header";
    {
        std::ofstream out(short_header, std::ios::binary | std::ios::trunc);
        out.put(static_cast<char>(5));
    }
    expect_failure([&] {
        FortranRecordReader r(short_header.string());
        std::vector<std::uint8_t> bytes;
        (void)r.next(bytes);
    });
    const auto truncated = root / "truncated";
    {
        std::ofstream out(truncated, std::ios::binary | std::ios::trunc);
        put_marker(out, 10, 4, false);
        out.write("abc", 3);
    }
    expect_failure([&] {
        FortranRecordReader r(truncated.string());
        std::vector<std::uint8_t> bytes;
        (void)r.next(bytes);
    });
    const auto negative = root / "negative-subrecord";
    {
        std::ofstream out(negative, std::ios::binary | std::ios::trunc);
        put_marker(out, 0xFFFFFFFFU, 4, false);
    }
    expect_failure([&] {
        FortranRecordReader r(negative.string());
        std::vector<std::uint8_t> bytes;
        (void)r.next(bytes);
    });
}
