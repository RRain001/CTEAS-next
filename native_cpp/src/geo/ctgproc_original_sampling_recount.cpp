#include "cteas/geo/ctgproc_original_sampling_recount.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <span>
#include <stdexcept>

namespace cteas::reconstruction::geo {
namespace {
void require(bool yes,const char* what) {if(!yes)throw std::runtime_error(what);}
std::size_t class_index(int category) {
  const auto it=std::find(kGlccUsgs92Classes.begin(),kGlccUsgs92Classes.end(),category);
  require(it!=kGlccUsgs92Classes.end(),"ORIGINAL_RECOUNT_UNSUPPORTED_CLASS");
  return std::size_t(it-kGlccUsgs92Classes.begin());
}
}
double OriginalSamplingRecount::fraction(std::size_t i,std::size_t j,std::size_t k) const {
  if(i>=grid.nx||j>=grid.ny||k>=kGlccUsgs92Classes.size())
    throw std::out_of_range("ORIGINAL_RECOUNT_FRACTION_INDEX");
  const std::size_t cell=j*grid.nx+i;
  const auto n=samples.at(cell);
  if(n)return double(counts.at(cell*kGlccUsgs92Classes.size()+k))/n;
  if(fill_ocean.at(cell))return kGlccUsgs92Classes[k]==iocean?1.:0.;
  throw std::domain_error("ORIGINAL_RECOUNT_MISSING_NOT_OCEAN_FILLED");
}
namespace {
// Shared original LUGRID/SVGRID integer bookkeeping. The classifier is
// injectable so the D2 GEOS diagnostic stays separate from the authentic
// original-BLN/PNPOLY candidate. Neither route mutates the source counts.
template <class Classifier>
OriginalSamplingRecount recount_with_classifier(
    const GlccRawResult& source, const OriginalCoastControl& controls,
    bool has_classifier, const Classifier& classify) {
  validate_original_coast_controls(controls, std::span<const int>(kGlccUsgs92Classes));
  const auto grid=source.grid;
  require(grid.nx>0&&grid.ny>0&&grid.nx<=250000/grid.ny,
          "ORIGINAL_RECOUNT_GRID_BUDGET");
  const auto nc=grid.nx*grid.ny;
  require(source.counts.size()==nc*kGlccUsgs92Classes.size()&&
          source.cell_samples.size()==nc,"ORIGINAL_RECOUNT_SOURCE_SHAPE");
  require(source.included<=3000000&&source.outside<=3000000&&
          source.included+source.outside==source.diagnostic_mesh.size(),
          "ORIGINAL_RECOUNT_REQUIRES_COMPLETE_P2A_MESH_TRACE");
  if(controls.lcoast && (controls.lmarswap||controls.lmarfill))
    require(has_classifier,"ORIGINAL_RECOUNT_REQUIRES_COAST_CLASSIFIER");
  OriginalSamplingRecount out{grid,
     std::vector<std::uint32_t>(source.counts.size(),0),
     std::vector<std::uint32_t>(nc,0),
     std::vector<std::uint8_t>(nc,0),controls.iocean,0,0,0};
  for(const auto& sample:source.diagnostic_mesh) {
    if(sample.assigned_i<1||sample.assigned_j<1||
       std::size_t(sample.assigned_i)>grid.nx||
       std::size_t(sample.assigned_j)>grid.ny){
      ++out.outside;
      continue;
    }
    require(std::isfinite(sample.x_km)&&std::isfinite(sample.y_km),
            "ORIGINAL_RECOUNT_NONFINITE_GLOBE_POINT");
    const std::size_t cell=(std::size_t(sample.assigned_j)-1)*grid.nx+
                           (std::size_t(sample.assigned_i)-1);
    // Existing GLCC P2-A producer performs mesh projection/grid binning.
    // D3 does NOT rerun its GLAZAS path: only update the original NGRID
    // class after original LUGRID coast option. 54 is special on ocean.
    int coast_type=1;
    if(controls.lcoast&&controls.lmarswap)
      coast_type=classify(sample.x_km,sample.y_km);
    const auto mapped=original_lugrid_coastal_category(controls,sample.category,coast_type);
    if(!mapped){++out.rejected_coast;continue;}
    const auto k=class_index(*mapped);
    require(out.samples[cell]<std::numeric_limits<std::uint32_t>::max(),
            "ORIGINAL_RECOUNT_CELL_COUNT_OVERFLOW");
    ++out.counts[cell*kGlccUsgs92Classes.size()+k];
    ++out.samples[cell];
    ++out.included;
  }
  require(out.included+out.outside+out.rejected_coast==source.included+source.outside,
          "ORIGINAL_RECOUNT_SOURCE_SAMPLE_LOSS");
  // Regression: original counting must remain strictly identical if LCOAST=F.
  if(!controls.lcoast) {
    require(out.counts==source.counts&&out.samples==source.cell_samples&&
            out.included==source.included&&out.outside==source.outside,
            "ORIGINAL_RECOUNT_BASELINE_SOURCE_DRIFT");
  }
  if(controls.lcoast&&controls.lmarfill) {
    for(std::size_t j=0;j<grid.ny;++j)for(std::size_t i=0;i<grid.nx;++i) {
      const auto cell=j*grid.nx+i;
      if(out.samples[cell])continue;
      const float x=static_cast<float>((grid.x0_m+(double(i)+.5)*grid.dx_m)/1000.);
      const float y=static_cast<float>((grid.y0_m+(double(j)+.5)*grid.dx_m)/1000.);
      const auto type=classify(x,y);
      const auto action=original_svgrid_empty_cell_action(controls,false,type);
      if(action==OriginalFinalCellAction::FillOcean)out.fill_ocean[cell]=1;
      // No fabricated integer hit is inserted for SVGRID display fill.
    }
  }
  return out;
}
} // namespace

OriginalSamplingRecount recount_glcc_original_coast(
    const GlccRawResult& source, const OriginalCoastControl& controls,
    const OriginalGshhsPointClassifier* classifier) {
  // D2 compatibility route: GEOS is NOT the original Fortran point oracle.
  return recount_with_classifier(source,controls,classifier!=nullptr,
      [classifier](float x,float y) {
        return classifier ? classifier->iptype_model_km(x,y) : 1;
      });
}

OriginalSamplingRecount recount_glcc_original_coast_bln(
    const GlccRawResult& source, const OriginalCoastControl& controls,
    const OriginalBlnIptypeR4* classifier) {
  // D4 source-faithful point decision on the caller-admitted original BLN.
  return recount_with_classifier(source,controls,classifier!=nullptr,
      [classifier](float x,float y) {
        return classifier ? classifier->iptype(x,y) : 1;
      });
}
} // namespace cteas::reconstruction::geo
