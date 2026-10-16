#include "cteas/puff/fortran_records.hpp"

#include <array>
#include <limits>
#include <stdexcept>

namespace cteas::puff {

FortranRecordReader::FortranRecordReader(const std::string& path, unsigned marker_bytes,
                                        RecordByteOrder order, std::size_t maximum_record_bytes)
    : stream_(path, std::ios::binary), marker_bytes_(marker_bytes),
      byte_order_(order), maximum_record_bytes_(maximum_record_bytes) {
    if (!stream_) throw std::runtime_error("P7 unable to open binary Fortran file: " + path);
    if (marker_bytes != 4 && marker_bytes != 8)
        throw std::invalid_argument("P7 unsupported Fortran record marker width");
    if (maximum_record_bytes == 0 || maximum_record_bytes > static_cast<std::size_t>(
            std::numeric_limits<std::streamsize>::max()))
        throw std::invalid_argument("P7 invalid maximum Fortran record length");
}

std::uint64_t FortranRecordReader::decode_marker(const std::uint8_t* bytes) const {
    std::uint64_t value = 0;
    if (byte_order_ == RecordByteOrder::BigEndian) {
        for (unsigned i = 0; i < marker_bytes_; ++i) value = (value << 8U) | bytes[i];
    } else {
        for (unsigned i = 0; i < marker_bytes_; ++i) value |=
            static_cast<std::uint64_t>(bytes[i]) << (8U * i);
    }
    return value;
}

bool FortranRecordReader::next(std::vector<std::uint8_t>& data) {
    std::array<std::uint8_t, 8> head{};
    data.clear();
    stream_.read(reinterpret_cast<char*>(head.data()), marker_bytes_);
    const auto nhead = stream_.gcount();
    if (nhead == 0 && stream_.eof()) return false;
    if (nhead != static_cast<std::streamsize>(marker_bytes_))
        throw std::runtime_error("P7 truncated leading Fortran record marker");
    const std::uint64_t size = decode_marker(head.data());
    // Signed negative gfortran subrecord markers encode multi-segment records.
    // Fail closed rather than misinterpreting such files as ordinary records.
    if ((head[byte_order_ == RecordByteOrder::LittleEndian ? marker_bytes_ - 1 : 0] & 0x80U) != 0)
        throw std::runtime_error("P7 chained/signed Fortran subrecord not supported yet");
    if (size > maximum_record_bytes_)
        throw std::runtime_error("P7 Fortran record exceeds predeclared maximum");
    data.resize(static_cast<std::size_t>(size));
    if (!data.empty()) {
        stream_.read(reinterpret_cast<char*>(data.data()),
                     static_cast<std::streamsize>(data.size()));
        if (stream_.gcount() != static_cast<std::streamsize>(data.size()))
            throw std::runtime_error("P7 truncated Fortran record payload");
    }
    std::array<std::uint8_t, 8> tail{};
    stream_.read(reinterpret_cast<char*>(tail.data()), marker_bytes_);
    if (stream_.gcount() != static_cast<std::streamsize>(marker_bytes_))
        throw std::runtime_error("P7 truncated trailing Fortran record marker");
    if (decode_marker(tail.data()) != size)
        throw std::runtime_error("P7 mismatched Fortran record markers");
    ++records_read_;
    return true;
}
} // namespace cteas::puff
