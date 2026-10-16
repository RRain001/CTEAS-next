#include "cteas/puff/original_turbset_mdisp3.hpp"
#include "cteas/puff/original_comp_neutral.hpp"
#include "cteas/puff/original_met_hours.hpp"
#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
int main(int argc,char** argv){
 try{
  if(argc!=4)throw std::invalid_argument("usage TURBSET_TEST puff.inp makegeo.inp met.dat");
  const auto cfg=cteas::puff::original_turbset_mdisp3_from_control(
      cteas::puff::ControlFile::read_file(argv[1]));
  const std::array<float,6> sw={0.20F,0.12F,0.08F,0.06F,0.03F,0.016F};
  std::size_t tested=0;
  for(int ilw=1;ilw<=2;++ilw){
   for(int cls=1;cls<=6;++cls){
    const auto result=cteas::puff::original_turbset_mdisp3_minimum(cfg,cls,ilw);
    if(result.sigv_ms!=(ilw==1?0.50F:0.37F) ||
       result.sigw_ms!=sw[static_cast<std::size_t>(cls-1)] ||
       result.stability!=cls || result.land_water!=ilw)
      throw std::runtime_error("2022 original SVMIN/SWMIN array mismatch");
    ++tested;
   }
  }
  if(cfg.tyidr!=0.001F||cfg.tzidr!=0.002F||
     cfg.tzisdr!=0.01F||cfg.ayt!=0.5F)
    throw std::runtime_error("original BLOCK DATA 2140/2144 changed");
  bool rejected=false;
  try{(void)cteas::puff::original_turbset_mdisp3_minimum(cfg,4,0);}
  catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("unknown land/water silently defaulted");
  const auto makegeo=cteas::puff::ControlFile::read_file(argv[2]);
  const auto production=cteas::puff::original_calm_mdisp3_from_decks(
      cteas::puff::ControlFile::read_file(argv[1]),makegeo);
  if(production.original_turbulence.svmin!=cfg.svmin ||
     production.original_turbulence.swmin!=cfg.swmin)
      throw std::runtime_error("native production calm deck factory changed original TURBSET minima");
  const int iwat1=production.iwat1;
  const int iwat2=production.iwat2;
  if(iwat1!=50||iwat2!=55)
   throw std::runtime_error("frozen 2022 original MAKEGEO IWAT1/IWAT2 drift");
  std::size_t hours=0,land_cells=0,water_cells=0,validated_cells=0;
  const auto data=cteas::puff::OriginalMetHourlyReader::read(argv[3],
   [&](const cteas::puff::Calmet21Header& header,
       const cteas::puff::Calmet21Static& static_fields,
       const cteas::puff::OriginalMetHour& met){
    if(header.nx!=50||header.ny!=50||met.nx!=50||met.ny!=50||
       !static_fields.present||static_fields.land_use.size()!=2500)
     throw std::runtime_error("frozen original MET static ILANDU grid mismatch");
    if(hours==0){
     for(std::size_t cell=0;cell<2500;++cell){
      const auto cat=static_fields.land_use[cell];
      const int ilw=cteas::puff::original_turbset_ilw_from_landuse(cat,iwat1,iwat2);
      if(ilw==2)++water_cells;else ++land_cells;
      for(int pg=1;pg<=6;++pg){
       const auto a=cteas::puff::original_turbset_mdisp3_from_cell(
         cfg,static_fields,50,50,cell,pg,iwat1,iwat2);
       const auto b=cteas::puff::original_turbset_mdisp3_minimum(cfg,pg,ilw);
       if(a.sigv_ms!=b.sigv_ms||a.sigw_ms!=b.sigw_ms)
        throw std::runtime_error("native ILANDU to TURBSET minima parity drift");
       ++validated_cells;
      }
     }
    }
    ++hours;
   },true);
  if(hours!=143||data.intervals!=143||land_cells+water_cells!=2500||
     validated_cells!=15000)
   throw std::runtime_error("original 143h MET ILANDU + MAKEGEO source bridge incomplete");
  std::cout<<"P7_ORIGINAL_TURBSET_MDISP3_HEFEI_MINIMA=PASS"
           <<" CELLS=EXPLICIT_ILW"
           <<" STABILITY_LANDWATER_CASES="<<tested
           <<" ORIGINAL_MET_HOURS="<<hours
           <<" ORIGINAL_LAND_CELLS="<<land_cells
           <<" ORIGINAL_WATER_CELLS="<<water_cells
           <<" REAL_MET_LANDUSE_MINIMA_CHECKS="<<validated_cells
           <<" TYIDR=0.001 TZIDR=0.002 TZISDR=0.01 AYT=0.5"
           <<" ACTUAL_COMP_989_CALM_SUBSTEPS=NOT_YET_ACCEPTED\n";
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P7_ORIGINAL_TURBSET_MDISP3_HEFEI_MINIMA=FAIL "
           <<e.what()<<'\n';return 1;
 }
}
