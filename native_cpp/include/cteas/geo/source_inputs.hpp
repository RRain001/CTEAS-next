#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>
#include "cteas_atmos/core/array.hpp"
#include "cteas_atmos/core/validity.hpp"

namespace cteas::reconstruction::geo {
struct GeographicBounds {
  double west_deg{}, south_deg{}, east_deg{}, north_deg{};
};
struct TerrainRaster {
  cteas::atmos::Array2D<std::int16_t> raw_elevation_m;
  cteas::atmos::ValidityMask2D valid;
  std::array<double, 6> geo_transform{};
  std::string crs_wkt;
  std::int16_t no_data{};
};
// P1: input ingestion; original TERREL resampling remains NOT IMPLEMENTED.
[[nodiscard]] GeographicBounds read_bbox(const std::filesystem::path& path);
[[nodiscard]] TerrainRaster read_srtm_geotiff(const std::filesystem::path& path);

struct LandusePoint {
  int usgs92_category{};
  double longitude_deg{}, latitude_deg{};
};
struct GenericLanduse {
  std::string datum;
  std::vector<int> categories;
  std::vector<LandusePoint> points;
};
// P2: input ingestion; original CTGPROC projection/fraction mapping is NOT IMPLEMENTED.
[[nodiscard]] GenericLanduse read_generic_landuse(const std::filesystem::path& path);
}  // namespace cteas::reconstruction::geo
