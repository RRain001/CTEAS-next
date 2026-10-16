#pragma once
// Selected original CALPUFF TURBSET L52039-52190.
// For MDISP=MDISP2=3: TSIGV/TSIGW initialize to -999, neither the
// MDISP=2 SIGWV path nor the MDISP=1/5 observation-profile path executes,
// and the arrays SVMIN(JDSTAB,ILW)/SWMIN(JDSTAB,ILW) supply both.
// Land/water ILW is explicitly required, never guessed from UTM position.
// Source-pinned by original SIGTY/SIGTZ calm inspection workflow.
#include "cteas/puff/control.hpp"
#include "cteas/puff/calmet21.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <cstddef>
#include <string>
namespace cteas::puff {
struct OriginalTurbsetMdisp3 {
 std::array<float,12> svmin,swmin;
 float tyidr=0.001F,tzidr=0.002F,tzisdr=0.01F; // Original BLOCK DATA L2140
 float ayt=0.5F; // Original BLOCK DATA L2144, not a fitted value
};
struct OriginalTurbsetMinimum {
 float sigv_ms=0.0F,sigw_ms=0.0F;
 int stability=0,land_water=0;
};
[[nodiscard]] inline OriginalTurbsetMdisp3 original_turbset_mdisp3_from_control(
    const ControlFile& control) {
 const auto ok=[](bool q,const char* s){if(!q)throw std::invalid_argument(s);};
 ok(control.required_int("MDISP")==3 && control.required_int("MDISP2")==3 &&
    control.required_int("MTAULY")==0,
    "TURBSET minima route needs MDISP=MDISP2=3, MTAULY=0");
 OriginalTurbsetMdisp3 cfg;
 const auto v=control.required_float_list("SVMIN");
 const auto w=control.required_float_list("SWMIN");
 ok(v.size()==12&&w.size()==12,"TURBSET requires both 12-value minimum arrays");
 for(std::size_t i=0;i<12;++i){
   ok(std::isfinite(v[i])&&std::isfinite(w[i])&&v[i]>0&&w[i]>0,
      "nonphysical SVMIN/SWMIN in original deck");
   cfg.svmin[i]=static_cast<float>(v[i]);
   cfg.swmin[i]=static_cast<float>(w[i]);
 }
 return cfg;
}
[[nodiscard]] inline OriginalTurbsetMinimum original_turbset_mdisp3_minimum(
    const OriginalTurbsetMdisp3& p,int stability,int ilw){
 if(stability<1||stability>6||(ilw!=1&&ilw!=2))
  throw std::invalid_argument("original TURBSET requires 1<=JDSTAB<=6 and ILW=1/2");
 const auto i=static_cast<std::size_t>(stability-1+6*(ilw-1));
 return {p.svmin[i],p.swmin[i],stability,ilw};
}
// CALPUFF COMP L10863-10867: JDSTAB normally equals the sampled
// PGT ISTAB but uses original deck JSUP above the bounded mixed layer
// for PGT A-D. That changes MDISP3 SWMIN even though PGT stays unchanged.
[[nodiscard]] inline int original_comp_turbset_jdstab(
    int istab,int jsup,float htmet_m,float dpbl_m){
    if(istab<1||istab>6||jsup<0||jsup>6||
       !std::isfinite(htmet_m)||!std::isfinite(dpbl_m)||
       htmet_m<0.0F||dpbl_m<=0.0F)
        throw std::invalid_argument(
            "COMP JDSTAB requires valid PGT/JSUP and HTMET/DPBL");
    return jsup>0&&istab<5&&htmet_m>dpbl_m ? jsup:istab;
}
// CALPUFF COMP L10839-10842: ILW comes from the current CALMET
// ILANDU(ixmet,iymet,md) and IWAT1/IWAT2 originally written by MAKEGEO.
// Do not classify land/water by latitude, grid index, or PG stability.
[[nodiscard]] inline int original_turbset_ilw_from_landuse(
    int land_use_code,int iwat1,int iwat2) {
 if(iwat1>iwat2||iwat1<0||iwat2<0)
  throw std::invalid_argument("original MAKEGEO water category bounds invalid");
 return land_use_code>=iwat1 && land_use_code<=iwat2 ? 2 : 1;
}
[[nodiscard]] inline OriginalTurbsetMinimum original_turbset_mdisp3_from_cell(
    const OriginalTurbsetMdisp3& p,const Calmet21Static& met_static,
    std::size_t nx,std::size_t ny,std::size_t cell_offset,
    int stability,int iwat1,int iwat2) {
 if(nx==0||ny==0||nx>static_cast<std::size_t>(1000000)/ny||
    !met_static.present||met_static.land_use.size()!=nx*ny||
    cell_offset>=nx*ny)
  throw std::invalid_argument("TURBSET requires actual decoded CALMET ILANDU grid");
 const int ilw=original_turbset_ilw_from_landuse(
     met_static.land_use[cell_offset],iwat1,iwat2);
 return original_turbset_mdisp3_minimum(p,stability,ilw);
}
} // namespace cteas::puff
