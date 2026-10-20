#pragma once
// Issue #160 P2-C: modern 30m GLC_FCS30D point HITS.
// ORIGINAL_SAMPLING point-grid structure, NOT EXACT_AREA_V1 pixel area.
// The legacy GLCC raw-category mapping must never enter this module.
#include "cteas/geo/ctgproc_original_sampling_recount.hpp"
#include <gdal_priv.h>
#include <cstdint>
#include <functional>
#include <map>

namespace cteas::reconstruction::geo {
struct Glc30mSamplingStats {
  std::uint64_t source_pixels=0, invalid_source_pixels=0;
  std::uint64_t generated_subpoints=0, invalid_subpoints=0;
  std::uint64_t outside_subpoints=0, included_subpoints=0;
  std::uint64_t water52_hits=0, water55_hits=0;
  std::uint64_t missing_cells=0;
};
// Returns a full integer 38-class census in j=1 south-up / i=1 west-up order.
// The callback is called ONLY for raw GLC210 water points, and must use the
// specifically selected Full L1 shapefile geometry in the *case UTM CRS*.
// 0/250/NoData never silently become 52/55.
using IsGshhgFullLandPoint = std::function<bool(double x_m,double y_m)>;
[[nodiscard]] OriginalSamplingRecount sample_glc30m_original_mesh(
    GDALDataset& source, const P2Grid& grid, int epsg,
    const std::map<int,int>& frozen_34_mapping, int mesh,
    const IsGshhgFullLandPoint& is_land,
    bool inland, Glc30mSamplingStats& stats);
} // namespace cteas::reconstruction::geo
