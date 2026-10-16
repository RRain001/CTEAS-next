#pragma once
// SHA-256 (FIPS 180-4) used only to report and verify the byte identity of a
// serialised CALMET.DAT 2.1 image. The CTest set cross-checks this
// implementation against Python hashlib on the frozen real reference file.
#include <cstdint>
#include <string>
#include <vector>

namespace cteas::p6f {

std::string sha256_hex(const std::vector<std::uint8_t>& bytes);
std::string sha256_hex_file(const std::string& path);

}  // namespace cteas::p6f
