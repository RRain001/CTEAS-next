#pragma once
// CALMET v6.5.0 source SETCOM L29762, L29784-29811 and AIRDEN
// L2090-2098, scoped to source 2+ surface stations, REAL*4.
// Original SETCOM loops I, J, K, compares strict "<" squared distance;
// equal-distance ties choose first source-met.inp station (1-based).
// No fabricated NEARS and no assumed nearest-site cloud/pressure mapping.
#include "cteas/p6/calmet_station_set.hpp"
#include "cteas/p6/read_geo_dynamic.hpp"
#include "cteas/p6/read_surface_dynamic.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
inline std::vector<int> source_setcom_nears(
    const GeoGrid& grid,const StationSet& stations) {
    if(grid.nx<=0||grid.ny<=0||grid.nx>400||grid.ny>400||
       !std::isfinite(grid.grid_km)||grid.grid_km<=0.f||
       stations.surface.empty()||stations.surface.size()>1000)
        throw std::invalid_argument("G17B SETCOM invalid grid/SS count");
    const float dgrid=grid.grid_km*1000.f;
    std::vector<int> nears(static_cast<std::size_t>(grid.nx)*
                           static_cast<std::size_t>(grid.ny));
    for(int i=1;i<=grid.nx;++i) {
        const float xgdpt=(static_cast<float>(i)-0.5f)*dgrid;
        for(int j=1;j<=grid.ny;++j) {
            const float ygdpt=(static_cast<float>(j)-0.5f)*dgrid;
            float dmin2=1.e37f;int ksv=0;
            for(std::size_t k=0;k<stations.surface.size();++k) {
                const auto& station=stations.surface[k];
                if(!std::isfinite(station.local_x_m)||
                   !std::isfinite(station.local_y_m))
                    throw std::invalid_argument("G17B SETCOM station not finite");
                const float dx=station.local_x_m-xgdpt;
                const float dy=station.local_y_m-ygdpt;
                const float dist2=dx*dx+dy*dy;
                if(!std::isfinite(dist2))
                    throw std::invalid_argument("G17B SETCOM overflow distance");
                if(dist2<dmin2) {
                    dmin2=dist2;
                    ksv=static_cast<int>(k)+1;
                }
            }
            if(ksv<=0)
                throw std::invalid_argument("G17B SETCOM no nearest surface station");
            nears[static_cast<std::size_t>(j-1)*grid.nx+
                  static_cast<std::size_t>(i-1)]=ksv;
        }
    }
    return nears;
}
inline std::vector<float> source_airden_nears(
    const std::vector<int>& nears,
    const std::vector<float>& temp2d_k,
    const SurfaceHour& hour) {
    if(nears.empty()||nears.size()!=temp2d_k.size()||
       hour.by_station.empty())
        throw std::invalid_argument("G17B AIRDEN dimensions invalid");
    std::vector<float> rho(nears.size());
    for(std::size_t index=0;index<nears.size();++index) {
        const int nsta=nears[index];
        if(nsta<=0||static_cast<std::size_t>(nsta)>hour.by_station.size())
            throw std::invalid_argument("G17B AIRDEN NEARS out of range");
        const auto& obs=hour.by_station[static_cast<std::size_t>(nsta-1)];
        const float temp=temp2d_k[index];
        if(!obs.pressure_valid||!std::isfinite(obs.pressure_mb)||
           obs.pressure_mb<=0.f||obs.pressure_mb>=9998.f||
           !std::isfinite(temp)||temp<=0.f||temp>=9998.f)
            throw std::invalid_argument("G17B AIRDEN missing RDSN pressure/TEMP2D");
        // Original AIRDEN: RHO(i,j)=0.3484321*PRES(NEARS(i,j))/TEMP2D(i,j)
        const float value=0.3484321f*obs.pressure_mb/temp;
        if(!std::isfinite(value)||value<=0.f)
            throw std::invalid_argument("G17B AIRDEN invalid physical density");
        rho[index]=value;
    }
    return rho;
}
} // namespace cteas::calmet::p6g
