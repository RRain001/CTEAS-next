#pragma once
// Issue #123 D3: opted-in recount of EXISTING P2-A GLCC source-mesh traces.
// Never modifies P2-A producer hits or P2-B EXACT_AREA_V1.
#include "cteas/geo/ctgproc_original_coast_policy.hpp"
#include "cteas/geo/ctgproc_original_iptype.hpp"
#include "cteas/geo/glcc_raw_fractions.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace cteas::reconstruction::geo {
struct OriginalSamplingRecount {
  P2Grid grid;
  std::vector<std::uint32_t> counts;       // 38-class original-style integer NGRID
  std::vector<std::uint32_t> samples;      // included samples only; empty stays zero
  std::vector<std::uint8_t> fill_ocean;    // SVGRID display-only fill, not a fake sample
  int iocean;
  std::uint64_t included=0, outside=0, rejected_coast=0;
  [[nodiscard]] double fraction(std::size_t i,std::size_t j,std::size_t k) const;
};

// Requires P2-A's diagnostic_mesh of ALL source samples, in their real
// original existing point ordering (including outside). No new interpolation,
// projection, raster scan or source-to-mesh assignment is introduced here.
// This is a software-comparison candidate: Fortran parity NOT_RUN.
[[nodiscard]] OriginalSamplingRecount recount_glcc_original_coast(
    const GlccRawResult& original_p2a, const OriginalCoastControl& controls,
    const OriginalGshhsPointClassifier* classified_full);
} // namespace cteas::reconstruction::geo
