#pragma once

#include <cstddef>
#include <cstdint>
#include <fstream>
#include <string>
#include <vector>

namespace cteas::puff {

enum class RecordByteOrder { LittleEndian, BigEndian };

// Generic sequential-unformatted Fortran record frame reader only.
// Does not decode CALMET.DAT field contents, internal timestamps or geometry.
class FortranRecordReader {
public:
    FortranRecordReader(const std::string& path, unsigned marker_bytes = 4,
                        RecordByteOrder order = RecordByteOrder::LittleEndian,
                        std::size_t maximum_record_bytes = 128U * 1024U * 1024U);

    // Returns false ONLY at a clean record boundary/EOF; malformed and
    // partial marker, truncated payload and mismatched trailer throw.
    bool next(std::vector<std::uint8_t>& data);
    [[nodiscard]] std::size_t records_read() const noexcept { return records_read_; }

private:
    std::ifstream stream_;
    unsigned marker_bytes_;
    RecordByteOrder byte_order_;
    std::size_t maximum_record_bytes_;
    std::size_t records_read_ = 0;
    std::uint64_t decode_marker(const std::uint8_t* data) const;
};

} // namespace cteas::puff
