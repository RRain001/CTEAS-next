#pragma once
// Issue #123 D11: isolated native LU.DAT v2.1 serialization of source-
// faithful ORIGINAL_SAMPLING GLCC hits, validated for Wolsong 200x200.
// No license-controlled data bundled; no P2-B EXACT_AREA_V1 modification.
#include "cteas/geo/ctgproc_original_sampling_recount.hpp"
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <ostream>
#include <stdexcept>
#include <string>

namespace cteas::reconstruction::geo {
struct OriginalSamplingLuStats {
  std::uint64_t total_hits=0;
  std::size_t nonempty_cells=0;
  std::size_t missing_cells=0;
  std::size_t fraction_fields=0;
};

inline OriginalSamplingLuStats write_original_sampling_lu(
    std::ostream& o, const OriginalSamplingRecount& data,
    bool enforce_wolsong_scope=true, int utm_zone=52,
    const char* producer_comment="Produced by CTEAS C++ ORIGINAL_SAMPLING D11 (source-faithful Wolsong scope)",
    const char* source_comment="Generated from SHA-admitted historical GLCC and original COASTRD BLN",
    char utm_hemisphere='N') {
  const auto& g=data.grid;
  if(g.nx==0||g.ny==0||g.nx>250000/g.ny||
     data.counts.size()!=g.nx*g.ny*38||
     data.samples.size()!=g.nx*g.ny||
     data.fill_ocean.size()!=g.nx*g.ny)
    throw std::runtime_error("D11_INVALID_COUNTS_OR_GRID");
  if(enforce_wolsong_scope && (g.nx!=200||g.ny!=200||
      std::abs(g.x0_m-533215.)>1e-6||
      std::abs(g.y0_m-3942629.)>1e-6||
      std::abs(g.dx_m-100.)>1e-6))
    throw std::runtime_error("D11_NOT_WOLSONG_ACCEPTED_GRID");
  if(data.iocean!=55)
    throw std::runtime_error("D11_UNSUPPORTED_ORIGINAL_IOCEAN");
  if(utm_zone<1||utm_zone>60|| (utm_hemisphere!='N'&&utm_hemisphere!='S') ||
     (enforce_wolsong_scope&&(utm_zone!=52||utm_hemisphere!='N')))
    throw std::runtime_error("P2C_INVALID_WGS84_UTM_OR_WOLSONG_HEADER_DRIFT");
  // Source original WRTHEAD: record 1 (2A16,A64), comment count,
  // two comment records, file type, map, zone, datum, grid, KM, categories.
  o<<std::left<<std::setw(16)<<"LU.DAT"<<std::setw(16)<<"2.1"
   <<std::setw(64)<<"Coordinate parameters and LandUse categories"<<"\n"
   <<std::right<<std::setw(4)<<2<<"\n"
   <<producer_comment<<"\n"
   <<source_comment<<"\n"
   <<"FRACTION\nUTM\n"<<std::setw(4)<<utm_zone<<utm_hemisphere<<"   "<<"\n"
   <<std::left<<std::setw(8)<<"WGS-84"<<std::setw(12)<<"02-21-2003"<<"\n"
   <<std::right<<std::setw(8)<<g.nx<<std::setw(8)<<g.ny
   <<std::fixed<<std::setprecision(3)
   <<std::setw(12)<<g.x0_m/1000.<<std::setw(12)<<g.y0_m/1000.
   <<std::setw(12)<<g.dx_m/1000.<<std::setw(12)<<g.dx_m/1000.
   <<std::setw(6)<<38<<"\nKM  \n"<<std::string(10,' ');
  for(const int c:kGlccUsgs92Classes)
    o<<std::setw(6)<<c;
  o<<"\n";
  OriginalSamplingLuStats stats;
  for(std::size_t j=0;j<g.ny;++j)for(std::size_t i=0;i<g.nx;++i) {
    const auto cell=j*g.nx+i;
    if(data.fill_ocean[cell])
      throw std::runtime_error("D11_LMARFILL_NOT_ACCEPTED_IN_WOLSONG");
    const auto n=data.samples[cell];
    std::uint64_t sum=0;
    o<<std::setw(5)<<i+1<<std::setw(5)<<j+1;
    for(std::size_t k=0;k<38;++k) {
      const auto hits=data.counts[cell*38+k];
      sum+=hits;
      if(n&&hits>n)
        throw std::runtime_error("D11_CLASS_GT_CELL_HITS");
      // Original ctgproc.for SVGRID: NGRID(k,i,j)/FLOAT(ISUM)
      // with REAL*4 division, formatted as Fortran F6.3.
      const float fraction=n?
           static_cast<float>(hits)/static_cast<float>(n):0.f;
      o<<std::setw(6)<<std::setprecision(3)<<fraction;
      ++stats.fraction_fields;
    }
    if(sum!=n)
      throw std::runtime_error("D11_CELL_HIT_CONSERVATION");
    stats.total_hits+=sum;
    stats.nonempty_cells+=bool(n);
    stats.missing_cells+=!n;
    const char* flag=n?".":"Missing";
    // Original CTGPROC SVGRID separates the 38th F6.3 fraction from the
    // terminal "." / "Missing" marker. Without it "0.000." passes C++
    // parsing but original Fortran list-directed READ fails on numeric #40.
    // Preserve all integer HITS and numeric fractions; serialization only.
    o<<"   "<<std::left<<std::setw(20)<<flag<<std::right<<"\n";
  }
  if(!o)throw std::runtime_error("D11_LU_IO_FAILURE");
  if(stats.nonempty_cells+stats.missing_cells!=g.nx*g.ny)
    throw std::runtime_error("D11_GRID_ACCOUNTING");
  return stats;
}
} // namespace cteas::reconstruction::geo
