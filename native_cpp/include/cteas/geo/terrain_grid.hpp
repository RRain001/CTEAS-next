#pragma once
#include <cstddef>
#include <cstdint>
#include <optional>
#include <utility>
#include <vector>
#include "cteas/geo/source_inputs.hpp"
namespace cteas::reconstruction::geo {
struct TerrainGridSpec {
  double southwest_x_m{}, southwest_y_m{}, cell_size_m{};
  std::size_t nx{},ny{};
};
struct TerrainGridResult {
  TerrainGridSpec specification;
  std::vector<std::uint32_t> point_count; // i fastest, j southernmost first
  std::vector<float> elevation_m;         // -999 when no input hits
  std::size_t accepted_points{}, rejected_outside{}, rejected_missing{};
};
[[nodiscard]] std::optional<std::pair<std::size_t,std::size_t>>
cell_index_terrel(float east_m,float north_m,const TerrainGridSpec& spec);
// P1 scoped: original LOADTIFF + SAVEELEV/CELLIND/CELLDAT/HEIGHTS mean,
// UTM zone 50N. No legacy void filling, peak processing, snow/coast options.
[[nodiscard]] TerrainGridResult grid_geotiff_terrain_utm50n(
  const TerrainRaster& source,const TerrainGridSpec& spec);
}
