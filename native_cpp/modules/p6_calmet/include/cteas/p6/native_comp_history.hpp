#pragma once
// The sole file-backed COMP history owner for the selected 50x50 Hefei case.
// This is a process-adapter transition boundary, NOT an in-process CALMET
// physics kernel. All three REAL*4 histories are validated before any become
// visible to the next DIAGNO hour.
#include <array>
#include <cmath>
#include <cstddef>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <limits>
#include <regex>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6 {
namespace fs = std::filesystem;

class NativeCompHistory {
public:
    static constexpr std::size_t kCells = 50U * 50U;
    static constexpr std::size_t kBytes = kCells * sizeof(float);

    explicit NativeCompHistory(fs::path prefix) : prefix_(std::move(prefix)) {
        fs::create_directories(prefix_.parent_path());
        for (const char* suffix : {"zi.f32", "ziconv.f32", "dptt.f32", "state.json"})
            if (fs::exists(path(suffix)))
                throw std::runtime_error("refusing pre-existing COMP history " + path(suffix).string());
    }

    [[nodiscard]] std::size_t completed_hours() const noexcept { return completed_; }
    [[nodiscard]] const fs::path& prefix() const noexcept { return prefix_; }

    void commit(std::size_t hour, const fs::path& next_prefix) {
        if (hour != completed_ || hour >= 143U)
            throw std::invalid_argument("COMP history clock must be consecutive");
        const fs::path meta = fs::path(next_prefix.string() + ".state.json");
        const std::string metadata = bytes(meta);
        const std::regex hour_pattern("\"first_hour_zero_based\"\\s*:\\s*" +
                                      std::to_string(hour) + "\\s*[,}]");
        const std::regex shape_pattern("\"shape\"\\s*:\\s*\\[\\s*1\\s*,\\s*50\\s*,\\s*50\\s*\\]");
        if (!std::regex_search(metadata, hour_pattern) ||
            !std::regex_search(metadata, shape_pattern) ||
            metadata.find("p6e_calmet_dat21 emit-realcase") == std::string::npos ||
            metadata.find("\"dptt\"") == std::string::npos)
            throw std::runtime_error("invalid native COMP provenance/hour: " + meta.string());

        constexpr std::array<const char*, 3> names = {"zi", "ziconv", "dptt"};
        std::array<fs::path, 4> destinations{};
        std::array<std::string, 4> images{};

        // Stage all outputs in memory first; no incremental per-field append.
        for (std::size_t i = 0; i < names.size(); ++i) {
            const std::string state_name(names[i]);
            const fs::path source = fs::path(next_prefix.string() + "." + state_name + ".f32");
            const std::string current = bytes(source);
            if (current.size() != kBytes)
                throw std::runtime_error("native COMP float32 state size mismatch: " + source.string());
            for (std::size_t j = 0; j < kCells; ++j) {
                float value = 0.0f;
                std::memcpy(&value, current.data() + j * sizeof(float), sizeof(float));
                if (!std::isfinite(value) || std::abs(value) >= 999998.0f ||
                    (i != 2 && value < 0.0f))
                    throw std::runtime_error("nonphysical native COMP state: " + source.string());
            }
            const fs::path target = path(state_name + ".f32");
            destinations[i] = target;
            images[i] = hour == 0 ? std::string{} : bytes(target);
            if (images[i].size() != hour * kBytes)
                throw std::runtime_error("prior COMP history has inconsistent length: " + target.string());
            images[i].append(current);
        }
        destinations[3] = path("state.json");
        images[3] = metadata;
        std::array<fs::path, 4> staged{};
        std::size_t written = 0;
        try {
            for (std::size_t i = 0; i < staged.size(); ++i) {
                staged[i] = fs::path(destinations[i].string() + ".pending");
                if (fs::exists(staged[i]))
                    throw std::runtime_error("stale incomplete COMP commit marker: " + staged[i].string());
                write_bytes(staged[i], images[i]);
                ++written;
            }
        } catch (...) {
            for (std::size_t i = 0; i < written; ++i) {
                std::error_code ec;
                fs::remove(staged[i], ec);
            }
            throw;
        }
        // A process failure during multiple renames is not a system-wide
        // atomic transaction. The process stops, and no automatic resume is
        // supported: the next run refuses an occupied work directory.
        // Metadata is promoted last, after the three grid histories.
        for (std::size_t i = 0; i < staged.size(); ++i)
            fs::rename(staged[i], destinations[i]);
        ++completed_;
    }

private:
    [[nodiscard]] fs::path path(const std::string& suffix) const {
        return fs::path(prefix_.string() + "." + suffix);
    }
    static std::string bytes(const fs::path& input) {
        std::ifstream stream(input, std::ios::binary);
        if (!stream) throw std::runtime_error("cannot open native COMP file: " + input.string());
        std::string data(std::istreambuf_iterator<char>{stream}, std::istreambuf_iterator<char>{});
        if (stream.bad()) throw std::runtime_error("cannot read native COMP file: " + input.string());
        return data;
    }
    static void write_bytes(const fs::path& output, const std::string& data) {
        std::ofstream stream(output, std::ios::binary | std::ios::trunc);
        if (!stream || !stream.write(data.data(), static_cast<std::streamsize>(data.size())) ||
            !stream.flush())
            throw std::runtime_error("cannot stage COMP history: " + output.string());
    }

    fs::path prefix_;
    std::size_t completed_ = 0;
};

} // namespace cteas::calmet::p6
