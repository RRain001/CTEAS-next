#pragma once
#include "cteas/geo/landuse_fraction.hpp"
#include <cstddef>
#include <string>
#include <vector>
namespace cteas::reconstruction::geo {
// D2 source-raw fractions only. No GLC-FCS30D -> USGS-92 policy is implied.
struct GLCAreaFractions {
  P2Grid grid;
  std::vector<int> raw_codes;
  std::vector<double> area_m2;    // (j*nx+i)*raw_codes.size()+k
  std::vector<double> valid_m2;   // each grid cell; missing data is forbidden
  [[nodiscard]] double fraction(std::size_t i,std::size_t j,std::size_t k) const;
};
// Only an unrotated north-up, same-WGS84-UTM integer categorical TIFF is
// accepted. Any model-cell coverage gap, nodata, masked or invalid pixel fails.
[[nodiscard]] GLCAreaFractions compute_glc_area_fractions(
    const std::string& tif_path,P2Grid grid,int utm_epsg);
} // namespace cteas::reconstruction::geo
