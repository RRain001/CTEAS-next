#pragma once
#include "cteas/geo/landuse_fraction.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>
namespace cteas::reconstruction::geo {
inline constexpr std::array<int,38> kGlccUsgs92Classes{{
    11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,51,52,
    53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92}};
struct GlccWindow {int i0=0,i1=0,j0=0,j1=0;}; // 1-based, inclusive, south-up j
struct GlccRawResult {
    P2Grid grid;
    int utm_epsg=0;
    int mesh=0;
    GlccWindow window;
    std::vector<std::uint32_t> counts;       // cell-major, 38 USGS-92 classes
    std::vector<std::uint32_t> cell_samples; // historical 1km mesh point counts
    std::array<std::uint64_t,25> raw_pixels{}; // 0=missing, 1..24 classified
    std::uint64_t included=0,outside=0;
    [[nodiscard]] double fraction(std::size_t i,std::size_t j,std::size_t k) const;
};
// Read the ORIGINAL 13,000x12,000 headerless IMG north-to-south row layout.
// Explicit GEN seven-decimal lon/lat and REAL*4 replay is a comparison path,
// NOT a claim of original direct GLAZAS parity.
[[nodiscard]] GlccRawResult compute_glcc_gen_replay(
    const std::string& img_path, P2Grid grid, int utm_epsg, int mesh=20);
} // namespace cteas::reconstruction::geo
