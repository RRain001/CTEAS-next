#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>

namespace cteas::puff {

// Minimal FIPS 180-4 SHA-256, used only to pin P7 case-ledger evidence
// artifacts and to verify caller-supplied frozen input digests. This is
// deliberately not a general-purpose cryptographic API.
class Sha256Hasher {
public:
    void update(const std::uint8_t* data, std::size_t size);
    void update(std::string_view text);
    // Finalizes once and returns the lowercase hexadecimal digest.
    [[nodiscard]] std::string hex_digest();

private:
    void absorb(const std::uint8_t* data, std::size_t size);
    void compress(const std::uint8_t* block);
    void finalize();

    std::array<std::uint32_t, 8> state_{0x6a09e667U, 0xbb67ae85U, 0x3c6ef372U, 0xa54ff53aU,
                                        0x510e527fU, 0x9b05688cU, 0x1f83d9abU, 0x5be0cd19U};
    std::array<std::uint8_t, 64> buffer_{};
    std::uint64_t total_bytes_ = 0;
    std::size_t buffered_ = 0;
    bool finalized_ = false;
};

[[nodiscard]] std::string sha256_hex(std::string_view text);
[[nodiscard]] std::string sha256_hex_file(const std::string& path);

} // namespace cteas::puff
