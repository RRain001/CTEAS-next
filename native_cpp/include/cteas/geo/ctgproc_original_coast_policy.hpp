#pragma once
// Issue #123: original CTGPROC 7.0.0 coastal *point-count* control rules.
// This header has NO coastline geometry reader or full CTGPROC parity claim.
// It is not linked into P2-B EXACT_AREA_V1 or the accepted P2-A producer.
#include <algorithm>
#include <optional>
#include <span>
#include <stdexcept>
#include <string>

namespace cteas::reconstruction::geo {
enum class OriginalLanduseSource { HistoricalUsgs38, Generic, Unrestricted };

struct OriginalCoastControl {
  bool lcoast=false, lmarswap=false, lmarfill=false, lsnow=false;
  int iocean=55;
  OriginalLanduseSource source=OriginalLanduseSource::HistoricalUsgs38;
};

inline void validate_original_coast_controls(
    const OriginalCoastControl& c, std::span<const int> output_usgs_classes) {
  // CTGPROC READCF: GENERIC cannot activate either coastal or snow options.
  if(c.source==OriginalLanduseSource::Generic && (c.lcoast||c.lsnow))
    throw std::invalid_argument("ORIGINAL_CTGPROC_GENERIC_COAST_OR_SNOW_UNSUPPORTED");
  if(!c.lcoast)return;
  if(!c.lmarswap&&!c.lmarfill)
    throw std::invalid_argument("ORIGINAL_CTGPROC_COAST_REQUIRES_METHOD");
  if(c.iocean<1||c.iocean>92||
     std::find(output_usgs_classes.begin(),output_usgs_classes.end(),c.iocean)
        ==output_usgs_classes.end())
    throw std::invalid_argument("ORIGINAL_CTGPROC_IOCEAN_NOT_IN_USGS_LIST");
  // This phased C++ option adapter covers only genuine USGS-38 inputs.
  // Original's non-USGS source subtleties need independent treatment,
  // not silent reuse of the USGS point classification branch.
  if(c.source!=OriginalLanduseSource::HistoricalUsgs38)
    throw std::invalid_argument("ORIGINAL_CTGPROC_COAST_SOURCE_SCOPE");
}

// Return nullopt when the original LUGRID returns before incrementing NGRID.
// IPTYPE is supplied by the *original-equivalent* GSHHS point classifier:
// 0 ocean, 1 land, 2 lake, 3 island-in-lake, 4 pond-on-island.
// The original GSHHS point classifier itself is a SEPARATE unimplemented gate.
[[nodiscard]] inline std::optional<int> original_lugrid_coastal_category(
    const OriginalCoastControl& c, int input_category, int iptype) {
  if(input_category<1||input_category>92)
    throw std::invalid_argument("ORIGINAL_CTGPROC_CATEGORY_RANGE");
  if(!c.lcoast||!c.lmarswap)return input_category;
  if(c.source!=OriginalLanduseSource::HistoricalUsgs38)
    throw std::invalid_argument("ORIGINAL_CTGPROC_COAST_SOURCE_SCOPE");
  if(iptype<0||iptype>4)
    throw std::invalid_argument("ORIGINAL_CTGPROC_IPTYPE_UNDEFINED");
  // ctgproc.for LUGRID v7.0.0 L150211:
  // if (iptype(x,y).eq.0) then
  //    if(ilu.ne.54) ilul=iocean
  // else
  //    if(ilu.ge.54.and.ilu.le.55) return
  // endif
  // Do NOT reinterpret landward 52 as a GLC210 area intersection.
  if(iptype==0)return input_category==54?input_category:c.iocean;
  if(input_category==54||input_category==55)return std::nullopt;
  return input_category;
}

enum class OriginalFinalCellAction { KeepSampleFractions, FillOcean, LeaveMissing };

// CTGPROC SVGRID: LMARFILL checks cell CENTRE only for an EMPTY grid
// (ISUM==0). Partial cells are never overwritten or "completed" here.
[[nodiscard]] inline OriginalFinalCellAction original_svgrid_empty_cell_action(
    const OriginalCoastControl& c, bool has_any_samples, int center_iptype) {
  if(has_any_samples)return OriginalFinalCellAction::KeepSampleFractions;
  if(c.lcoast&&c.lmarfill&&
     c.source==OriginalLanduseSource::HistoricalUsgs38) {
    if(center_iptype<0||center_iptype>4)
      throw std::invalid_argument("ORIGINAL_CTGPROC_CENTRE_IPTYPE_UNDEFINED");
    if(center_iptype==0)return OriginalFinalCellAction::FillOcean;
  }
  return OriginalFinalCellAction::LeaveMissing;
}
} // namespace cteas::reconstruction::geo
