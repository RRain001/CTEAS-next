#include "cteas/geo/ctgproc_original_coast_policy.hpp"
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <vector>
using namespace cteas::reconstruction::geo;
namespace {
void need(bool v,const char* message) {
  if(!v)throw std::runtime_error(message);
}
template<class F> void rejects(F f, const char* message) {
  bool failed=false;
  try{f();}catch(const std::invalid_argument&){failed=true;}
  need(failed,message);
}
} // namespace
int main() {
  const std::array<int,5> water={{51,52,53,54,55}};
  OriginalCoastControl original{};
  validate_original_coast_controls(original,water);
  need(original_lugrid_coastal_category(original,52,0)==52,
       "LCOAST=F must retain water class without swap");
  need(original_lugrid_coastal_category(original,55,1)==55,
       "LCOAST=F must not delete landward 55");
  need(original_svgrid_empty_cell_action(original,false,0)==
       OriginalFinalCellAction::LeaveMissing,"LCOAST=F cannot silently fill marine");

  original.lcoast=true;
  rejects([&]{validate_original_coast_controls(original,water);},
          "LCOAST without swap/fill unexpectedly accepted");
  original.lmarswap=true;
  validate_original_coast_controls(original,water);
  // Ocean: USGS54 (bay/estuary) is explicitly retained in original LUGRID.
  need(original_lugrid_coastal_category(original,54,0)==54,"USGS54 marine exception lost");
  need(original_lugrid_coastal_category(original,52,0)==55,"ocean swap of 52 failed");
  need(original_lugrid_coastal_category(original,11,0)==55,"ocean swap of land failed");
  // Landward: old marine water 54/55 is DISCARDED, 52 is kept.
  need(!original_lugrid_coastal_category(original,54,1).has_value(),
       "landward 54 must be skipped");
  need(!original_lugrid_coastal_category(original,55,2).has_value(),
       "landward 55 must be skipped");
  need(original_lugrid_coastal_category(original,52,1)==52,
       "landward 52 must be retained");
  need(original_lugrid_coastal_category(original,51,4)==51,
       "pond-in-island must count as landward for coast swap");
  // Distinct sampled classes may coexist within one model grid cell.
  // This is integer NGRID/ISUM, NOT physical intersected area.
  std::array<std::uint32_t,2> counts{0,0};
  for(const auto [cat,iptype]:std::array<std::pair<int,int>,5>{{
      {52,1},{52,1},{52,0},{55,0},{55,1}}}) {
    const auto mapped=original_lugrid_coastal_category(original,cat,iptype);
    if(!mapped)continue;
    if(*mapped==52)++counts[0];
    if(*mapped==55)++counts[1];
  }
  need(counts[0]==2&&counts[1]==2,"mixed 52/55 count or discarded points mismatch");
  const double f52=double(counts[0])/(counts[0]+counts[1]);
  const double f55=double(counts[1])/(counts[0]+counts[1]);
  need(f52==.5&&f55==.5,"original NGRID/ISUM fractions mismatch");

  need(original_svgrid_empty_cell_action(original,false,0)==
       OriginalFinalCellAction::LeaveMissing,"LMARSWAP alone cannot fill empty cell");
  original.lmarfill=true;
  need(original_svgrid_empty_cell_action(original,false,0)==
       OriginalFinalCellAction::FillOcean,"LMARFILL empty marine must fill");
  need(original_svgrid_empty_cell_action(original,false,1)==
       OriginalFinalCellAction::LeaveMissing,"LMARFILL landward must stay missing");
  need(original_svgrid_empty_cell_action(original,true,0)==
       OriginalFinalCellAction::KeepSampleFractions,"LMARFILL must not replace sampled cell");

  original.lmarswap=false;
  need(original_lugrid_coastal_category(original,52,0)==52,
       "LMARFILL-only must not change valid water classes");
  validate_original_coast_controls(original,water);

  auto bad=original;bad.source=OriginalLanduseSource::Generic;
  rejects([&]{validate_original_coast_controls(bad,water);},
          "GENERIC + coastal should fail as original READCF");
  bad.lcoast=false;bad.lsnow=true;
  rejects([&]{validate_original_coast_controls(bad,water);},
          "GENERIC + snow should fail as original READCF");
  bad=original;bad.iocean=50;
  rejects([&]{validate_original_coast_controls(bad,water);},
          "IOCEAN absent in output category list should fail");
  bad=original;bad.iocean=100;
  rejects([&]{validate_original_coast_controls(bad,water);},
          "IOCEAN outside 1..92 should fail");
  rejects([&]{(void)original_lugrid_coastal_category(original,52,5);},
          "unknown IPTYPE must fail closed");
  rejects([&]{(void)original_svgrid_empty_cell_action(original,false,-1);},
          "unknown centre IPTYPE must fail closed");

  std::cout<<"ISSUE123_ORIGINAL_COAST_POLICY_SYNTHETIC_PASS"
              " FORTRAN_SOURCE_ORIGINAL_PARITY=NOT_RUN"
              " ORIGINAL_GSHHS_IPTYPE=NOT_IMPLEMENTED"
              " EXACT_AREA_V1_UNCHANGED=true\n";
  return 0;
}
