#include "cteas/puff/sha256.hpp"

#include <algorithm>
#include <fstream>
#include <stdexcept>
#include <vector>

namespace cteas::puff {
namespace {
constexpr std::array<std::uint32_t, 64> kRoundConstants{
    0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U, 0x3956c25bU, 0x59f111f1U, 0x923f82a4U,
    0xab1c5ed5U, 0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U, 0x72be5d74U, 0x80deb1feU,
    0x9bdc06a7U, 0xc19bf174U, 0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU, 0x2de92c6fU,
    0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU, 0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U,
    0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U, 0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU,
    0x53380d13U, 0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U, 0xa2bfe8a1U, 0xa81a664bU,
    0xc24b8b70U, 0xc76c51a3U, 0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U, 0x19a4c116U,
    0x1e376c08U, 0x2748774cU, 0x34b0bcb5U, 0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
    0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U, 0x90befffaU, 0xa4506cebU, 0xbef9a3f7U,
    0xc67178f2U};

std::uint32_t load32(const std::uint8_t* p) {
    return (static_cast<std::uint32_t>(p[0]) << 24) | (static_cast<std::uint32_t>(p[1]) << 16) |
           (static_cast<std::uint32_t>(p[2]) << 8) | static_cast<std::uint32_t>(p[3]);
}

std::uint32_t rotate_right(std::uint32_t value, unsigned count) {
    return (value >> count) | (value << (32U - count));
}
} // namespace

void Sha256Hasher::absorb(const std::uint8_t* data, std::size_t size) {
    while (size > 0) {
        const std::size_t take = std::min(size, buffer_.size() - buffered_);
        for (std::size_t i = 0; i < take; ++i) buffer_[buffered_ + i] = data[i];
        buffered_ += take;
        data += take;
        size -= take;
        if (buffered_ == buffer_.size()) {
            compress(buffer_.data());
            buffered_ = 0;
        }
    }
}

void Sha256Hasher::compress(const std::uint8_t* block) {
    std::array<std::uint32_t, 64> schedule{};
    for (std::size_t i = 0; i < 16; ++i) schedule[i] = load32(block + 4U * i);
    for (std::size_t i = 16; i < 64; ++i) {
        const std::uint32_t s0 = rotate_right(schedule[i - 15], 7) ^
                                 rotate_right(schedule[i - 15], 18) ^ (schedule[i - 15] >> 3);
        const std::uint32_t s1 = rotate_right(schedule[i - 2], 17) ^
                                 rotate_right(schedule[i - 2], 19) ^ (schedule[i - 2] >> 10);
        schedule[i] = schedule[i - 16] + s0 + schedule[i - 7] + s1;
    }
    std::uint32_t a = state_[0];
    std::uint32_t b = state_[1];
    std::uint32_t c = state_[2];
    std::uint32_t d = state_[3];
    std::uint32_t e = state_[4];
    std::uint32_t f = state_[5];
    std::uint32_t g = state_[6];
    std::uint32_t h = state_[7];
    for (std::size_t i = 0; i < 64; ++i) {
        const std::uint32_t s1 = rotate_right(e, 6) ^ rotate_right(e, 11) ^ rotate_right(e, 25);
        const std::uint32_t choose = (e & f) ^ (~e & g);
        const std::uint32_t temp1 = h + s1 + choose + kRoundConstants[i] + schedule[i];
        const std::uint32_t s0 = rotate_right(a, 2) ^ rotate_right(a, 13) ^ rotate_right(a, 22);
        const std::uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
        const std::uint32_t temp2 = s0 + majority;
        h = g;
        g = f;
        f = e;
        e = d + temp1;
        d = c;
        c = b;
        b = a;
        a = temp1 + temp2;
    }
    state_[0] += a;
    state_[1] += b;
    state_[2] += c;
    state_[3] += d;
    state_[4] += e;
    state_[5] += f;
    state_[6] += g;
    state_[7] += h;
}

void Sha256Hasher::update(const std::uint8_t* data, std::size_t size) {
    if (finalized_) throw std::logic_error("P7 SHA-256 update after finalization");
    total_bytes_ += size;
    absorb(data, size);
}

void Sha256Hasher::update(std::string_view text) {
    update(reinterpret_cast<const std::uint8_t*>(text.data()), text.size());
}

void Sha256Hasher::finalize() {
    if (finalized_) return;
    const std::uint64_t bit_length = total_bytes_ * 8U;
    std::array<std::uint8_t, 72> tail{};
    std::size_t tail_size = 0;
    tail[tail_size++] = 0x80U;
    while ((buffered_ + tail_size) % 64U != 56U) tail[tail_size++] = 0x00U;
    for (std::size_t i = 0; i < 8; ++i) {
        tail[tail_size++] = static_cast<std::uint8_t>((bit_length >> (56U - 8U * i)) & 0xffU);
    }
    absorb(tail.data(), tail_size);
    finalized_ = true;
}

std::string Sha256Hasher::hex_digest() {
    finalize();
    static constexpr char digits[] = "0123456789abcdef";
    std::string out;
    out.reserve(64);
    for (const std::uint32_t word : state_) {
        for (int shift = 28; shift >= 0; shift -= 4) {
            out.push_back(digits[(word >> shift) & 0xfU]);
        }
    }
    return out;
}

std::string sha256_hex(std::string_view text) {
    Sha256Hasher hasher;
    hasher.update(text);
    return hasher.hex_digest();
}

std::string sha256_hex_file(const std::string& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("P7 cannot hash missing file: " + path);
    Sha256Hasher hasher;
    std::vector<char> block(1U << 20);
    while (input) {
        input.read(block.data(), static_cast<std::streamsize>(block.size()));
        const auto read = input.gcount();
        if (read > 0) {
            hasher.update(reinterpret_cast<const std::uint8_t*>(block.data()),
                          static_cast<std::size_t>(read));
        }
    }
    if (!input.eof() && input.fail()) throw std::runtime_error("P7 hash read failed: " + path);
    return hasher.hex_digest();
}

} // namespace cteas::puff
