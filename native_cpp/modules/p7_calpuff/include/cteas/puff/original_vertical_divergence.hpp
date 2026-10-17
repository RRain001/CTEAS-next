#pragma once
#include "cteas/puff/original_met_hours.hpp"
#include "cteas/puff/original_met_cell.hpp"
namespace cteas::puff {
// Original CALPUFF COMP L10629-10649, and WDIV build L9555-9566.
// Only METFM=1 / LCALGRD=true selected path: CALMET W velocities are
// converted to layer dw/dz, averaged with the ported REAL4 ADVWND and
// used to expand a Gaussian puff's SIGZB before VMASS and SETPUF.
struct NativeOriginalWdivControls {
    float cdiv_begin_s=0.0F;
    float cdiv_full_s=0.0F;
};
struct NativeOriginalWdivResult {
    float start_divergence_s=0.0F;
    float end_divergence_s=0.0F;
    float max_divergence_s=0.0F;
    float factor=1.0F;
    float sigma_z_m=0.0F;
};
[[nodiscard]] NativeOriginalWdivResult original_vertical_divergence(
    const OriginalMetHour& met,const Calmet21Static& statics,
    OriginalMetCell begin,OriginalMetCell end,
    float zbot_m,float ztop_m,float tsamp_s,
    float sigma_z_before_m,int puff_code,
    const NativeOriginalWdivControls& cfg);
}
