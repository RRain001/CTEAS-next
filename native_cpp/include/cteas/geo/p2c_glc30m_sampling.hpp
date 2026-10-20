#pragma once
// Issue #160 C4: 2022 GLC_FCS30D 30m category POINT sampling, not
// P2-B EXACT_AREA_V1. Original-style subpoints/GLOBE R4/LUGRID HITS.
#include "cteas/geo/ctgproc_original_sampling_recount.hpp"
#include <array>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>
namespace cteas::reconstruction::geo {

inline constexpr const char* kP2cMappingPolicySha256 =
  "a5fa157f57feb1aa160dd96d920a22d267fea78c5828c6040fa95e86536544ed";
inline constexpr const char* kP2cSamplingMethodId =
  "P2_C_GLC30M_SOURCE_SUBPOINT_GLAZAS_LUGRID_R4_HITS_V1";

struct P2cGlc30mPolicy {
  // Entire 34 fixed targets are loaded from ONE frozen user-selected
  // JSON, not copied into a second table or inferred from source IDs.
  std::array<int,256> source_to_usgs{};
};

struct P2cGlc30mStatistics {
  OriginalSamplingRecount hits;
  std::array<std::uint64_t,256> source_pixel_histogram{};
  std::array<std::uint64_t,256> classified_sample_histogram{};
  std::uint64_t masked_pixels=0;
  std::uint64_t no_data_pixels=0;
  std::uint64_t source_pixels=0;
  std::uint64_t water_land_hits=0;
  std::uint64_t water_sea_hits=0;
  int mesh=10;
};

// Verify caller's user-selected mapping JSON/structure (SHA256 verification
// must be performed by the CLI, before calling this loader).
[[nodiscard]] P2cGlc30mPolicy load_p2c_glc30m_policy(
    const std::filesystem::path& frozen_policy_json);

[[nodiscard]] P2cGlc30mStatistics sample_p2c_glc30m(
    const std::filesystem::path& source_tiff, const P2Grid& model_grid,
    int utm_epsg, const P2cGlc30mPolicy& policy,
    const OriginalBlnIptypeR4* original_full_l1_bln,
    int mesh=10);
} // namespace cteas::reconstruction::geo
