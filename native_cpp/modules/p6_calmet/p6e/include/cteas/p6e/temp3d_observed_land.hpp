#pragma once
// CALMET 6.5.0 TEMP3D (calmet.for 31159-31709), selected original
// ITPROG=0/NOWSTA=0 land path with 00/12 UTC bounding observations.
// Input TZGRAA/TZGRBB values are already vertically interpolated to
// CALMET cell faces (RDUP/COMP preprocessing remains separate).
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
struct Temp3dObservedInput {
    std::size_t nx=0,ny=0,nz=0;
    float dgrid_m=100.f;
    int irad=1, current_hour_utc=6;
    std::vector<float> face_z_m,station_x_m,station_y_m;
    std::vector<int> justa;
    // Per station, index k corresponds to Fortran grid face k+1.
    std::vector<float> aa_face_temp_k,bb_face_temp_k;
    std::vector<float> surface_temp_k,convective_zi_m;
    // Optional explicit sounding/current times per station (seconds on any
    // common axis). When provided they replace the same-day 00Z/12Z model and
    // reproduce the original DELTSEC-based JTOGO/JPAST with
    // XFACT = JTOGO/(JPAST+JTOGO), which covers 12Z -> next-day-00Z windows.
    std::vector<int> past_seconds,to_go_seconds;
};
inline std::vector<float> temp3d_observed_land(const Temp3dObservedInput& a) {
    if(!a.nx||!a.ny||a.nz<2||
       a.nx>std::numeric_limits<std::size_t>::max()/a.ny||
       (a.nx*a.ny)>std::numeric_limits<std::size_t>::max()/a.nz||
       !std::isfinite(a.dgrid_m)||a.dgrid_m<=0.f||
       (a.irad!=1&&a.irad!=2)||a.current_hour_utc<0||
       a.current_hour_utc>12||a.justa.empty()||
       a.justa.size()!=a.station_x_m.size()||
       a.justa.size()!=a.station_y_m.size()||
       a.justa.size()>std::numeric_limits<std::size_t>::max()/(a.nz+1))
        throw std::invalid_argument("TEMP3D invalid source geometry or hours");
    const auto stations=a.justa.size(),n=a.nx*a.ny;
    if(a.face_z_m.size()!=a.nz+1||a.surface_temp_k.size()!=n||
       a.convective_zi_m.size()!=n||
       a.aa_face_temp_k.size()!=stations*(a.nz+1)||
       a.bb_face_temp_k.size()!=stations*(a.nz+1))
        throw std::invalid_argument("TEMP3D wrong array extents");
    for(std::size_t k=0;k<a.face_z_m.size();++k)
        if(!std::isfinite(a.face_z_m[k])||
           (k>0&&!(a.face_z_m[k]>a.face_z_m[k-1])))
            throw std::invalid_argument("TEMP3D nonmonotonic faces");
    for(std::size_t st=0;st<stations;++st) {
        if(!std::isfinite(a.station_x_m[st])||
           !std::isfinite(a.station_y_m[st])||
           (a.justa[st]!=1&&a.justa[st]!=-1))
            throw std::invalid_argument("TEMP3D invalid AA/BB sounding station");
    }
    std::vector<float> result(n*a.nz,0.f);
    const float dgridi=1.f/a.dgrid_m;
    const float jdelta=43200.f;
    const float xtogo=static_cast<float>((12-a.current_hour_utc)*3600);
    const float xpast=static_cast<float>(a.current_hour_utc*3600);
    if(xpast<0.f||xtogo<0.f||xpast+xtogo!=jdelta)
        throw std::invalid_argument("TEMP3D soundings fail to bracket time");
    const bool explicit_times=!a.past_seconds.empty()||!a.to_go_seconds.empty();
    if(explicit_times&&(a.past_seconds.size()!=stations||
                        a.to_go_seconds.size()!=stations))
        throw std::invalid_argument("TEMP3D explicit sounding times extent");
    std::vector<float> face_time_temp(stations*(a.nz+1),0.f);
    for(std::size_t st=0;st<stations;++st) {
        float xfact=xtogo/jdelta;
        if(explicit_times) {
            // Original: JTOGO = newer sounding - now, JPAST = now - older
            // sounding, JDELTA = the AA<->BB interval; the original STOPS on a
            // negative JTOGO/JPAST, so fail closed here as well.
            if(a.past_seconds[st]<0||a.to_go_seconds[st]<0)
                throw std::invalid_argument(
                    "TEMP3D soundings do not straddle the current hour");
            const float total=static_cast<float>(a.past_seconds[st]+
                                                 a.to_go_seconds[st]);
            if(!(total>0.f))throw std::invalid_argument("TEMP3D zero sounding interval");
            xfact=static_cast<float>(a.to_go_seconds[st])/total;
        }
        for(std::size_t k=1;k<=a.nz;++k) {
            const auto p=st*(a.nz+1)+k;
            const float taa=a.aa_face_temp_k[p],tbb=a.bb_face_temp_k[p];
            if(!std::isfinite(taa)||!std::isfinite(tbb)||
               taa<180.f||tbb<180.f||taa>350.f||tbb>350.f)
                throw std::invalid_argument("TEMP3D invalid upper temperature");
            face_time_temp[p]=(a.justa[st]<0)?
                taa-(taa-tbb)*xfact :
                tbb-(tbb-taa)*xfact;
        }
    }
    for(std::size_t i=0;i<a.nx;++i)for(std::size_t j=0;j<a.ny;++j) {
        const auto cell=j*a.nx+i;
        const float ts=a.surface_temp_k[cell],zi=a.convective_zi_m[cell];
        if(!std::isfinite(ts)||ts<180.f||ts>350.f||
           !std::isfinite(zi)||zi<0.f)
            throw std::invalid_argument("TEMP3D invalid surface state");
        result[cell]=ts;
        const float xc=static_cast<float>(i+1)-0.5f;
        const float yc=static_cast<float>(j+1)-0.5f;
        std::vector<float> weight(stations,0.f);
        float sum=0.f;
        for(std::size_t st=0;st<stations;++st) {
            const float dx=a.station_x_m[st]*dgridi-xc;
            const float dy=a.station_y_m[st]*dgridi-yc;
            float r2=dx*dx+dy*dy;
            if(a.irad==1)r2=std::sqrt(r2);
            const float w=(r2<1.f)?1.f:1.f/r2;
            weight[st]=w;
            sum+=w;
        }
        const float norm=1.f/sum;
        for(auto& w:weight)w=w*norm;
        std::vector<float> tzua(a.nz+1,0.f);
        for(std::size_t k=1;k<=a.nz;++k) {
            float tt=0.f;
            for(std::size_t st=0;st<stations;++st)
                tt=tt+weight[st]*face_time_temp[st*(a.nz+1)+k];
            tzua[k]=tt;
        }
        // Fortran K=2...NZ. Fortran ZFACE(K),ZFACE(K+1)
        // are zero-indexed face_z_m[K-1],face_z_m[K].
        for(std::size_t level=1;level<a.nz;++level) {
            const float low=a.face_z_m[level],high=a.face_z_m[level+1];
            float tlow=tzua[level],thigh=tzua[level+1], t=0.f;
            if(low>zi)
                t=0.5f*(tlow+thigh);
            if(high<=zi)
                t=ts-0.0098f*0.5f*(low+high);
            if(low<=zi&&high>zi) {
                tlow=ts-0.0098f*low;
                const float tmid=ts-0.0098f*zi;
                t=0.5f*((tlow+tmid)*(zi-low)+
                        (tmid+thigh)*(high-zi))/(high-low);
            }
            if(!std::isfinite(t))
                throw std::invalid_argument("TEMP3D nonfinite vertical interpolation");
            result[level*n+cell]=t;
        }
    }
    return result;
}
} // namespace cteas::p6e
