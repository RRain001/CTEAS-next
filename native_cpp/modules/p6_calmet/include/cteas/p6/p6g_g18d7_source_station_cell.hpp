#pragma once
// G18D7: original CALMET DIAGI site-cell mapping (REAL*4 operation order).
// Vendor calmet.for DIAGI: IST(I)=XSSTA(I)/DX+1, JST(I)=YSSTA(I)/DY+1;
// DIAGNO then clamps IG/JG to [1,NX]/[1,NY] before STHEOR.
// This is deliberately only the bounded in-GEO surface-station branch.
#include "cteas/p6/calmet_station_set.hpp"
#include "cteas/p6/read_geo_dynamic.hpp"
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace cteas::calmet::p6g {
inline std::size_t g18d7_source_diagi_station_cell(
    const GeoGrid& grid, const cteas::calmet::p6::DeckStation& site) {
    const float dx=grid.grid_km*1000.f;
    if(grid.nx<2||grid.ny<2||!std::isfinite(dx)||dx<=0.f||
       !std::isfinite(site.local_x_m)||!std::isfinite(site.local_y_m)||
       site.local_x_m<0.f||site.local_y_m<0.f||
       site.local_x_m>=static_cast<float>(grid.nx)*dx||
       site.local_y_m>=static_cast<float>(grid.ny)*dx)
        throw std::invalid_argument("G18D7 DIAGI site outside accepted source GEO");
    // Do NOT truncate XSSTA/DX before adding 1: Fortran performs a
    // rounded REAL*4 addition first, then integer assignment truncation.
    // Its near-boundary result can differ by one cell from floor(X/DX).
    const int is=std::clamp(static_cast<int>(site.local_x_m/dx+1.f),
                            1,grid.nx);
    const int js=std::clamp(static_cast<int>(site.local_y_m/dx+1.f),
                            1,grid.ny);
    return (static_cast<std::size_t>(js)-1)*
               static_cast<std::size_t>(grid.nx)+
           static_cast<std::size_t>(is)-1;
}
} // namespace cteas::calmet::p6g
