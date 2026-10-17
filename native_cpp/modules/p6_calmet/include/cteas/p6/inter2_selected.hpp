#pragma once
// Source-scoped CALMET v6.5.0 L150223 INTER2, calmet.for 8124-8616.
// Production selected IPROG=0, NBAR=0, NOOBS=0, I3DCTW=1. Does NOT
// replace WIND1/SIMILT/DIAGNO; no prognostic, barriers or noobs shortcuts.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>
namespace cteas::calmet::p6 {
struct Inter2SelectedInput {
    int nx=0,ny=0,nz=0,nstations=0;
    float dx_m=0,dy_m=0,rmin_km=0,rmax1_km=0,rmax2_km=0,
          rmax3_km=0,r1_km=0,r2_km=0;
    bool lvary=false;
    int iprog=0,nbar=0,noobs=0,water_first=50,water_last=55;
    float edit=999999.f, editl=999998.f;
    std::vector<int> nintrp_per_layer,landuse;
    std::vector<float> station_x_km,station_y_km;
    // station input: k*nstations+l (original STDAT1(K,L), contiguous
    // physical Fortran station by layer values supplied explicitly).
    std::vector<float> station_component_mps;
    // k-major, row-major, i-fastest: original FGFLD and gridded WO.
    std::vector<float> step1_mps,observation_weight;
};
struct Inter2SelectedOutput {
    std::vector<float> component_mps;  // k-major, j-major, i-fastest
    std::vector<int> contributing_station_count;
    std::vector<int> nearest_fallback_used;
};
inline Inter2SelectedOutput original_inter2_selected(const Inter2SelectedInput& in) {
    if(in.nx<2||in.ny<2||in.nz<1||in.nx>400||in.ny>400||in.nz>12||
       in.nstations<1||in.nstations>479||in.nbar!=0||in.iprog!=0||in.noobs!=0||
       in.water_first>in.water_last)
        throw std::invalid_argument("INTER2 unsupported original control");
    const auto valid_pos=[](float x){return std::isfinite(x)&&x>0.f;};
    if(!valid_pos(in.dx_m)||!valid_pos(in.dy_m)||!valid_pos(in.rmin_km)||
       !valid_pos(in.rmax1_km)||!valid_pos(in.rmax2_km)||
       !valid_pos(in.rmax3_km)||!valid_pos(in.r1_km)||!valid_pos(in.r2_km)||
       !std::isfinite(in.edit)||!std::isfinite(in.editl)||
       !(in.edit>in.editl))
        throw std::invalid_argument("INTER2 invalid grid/radius/sentinel");
    const auto cells=std::size_t(in.nx)*std::size_t(in.ny);
    const auto total=cells*std::size_t(in.nz);
    if(in.nintrp_per_layer.size()!=std::size_t(in.nz)||
       in.landuse.size()!=cells||
       in.station_x_km.size()!=std::size_t(in.nstations)||
       in.station_y_km.size()!=std::size_t(in.nstations)||
       in.station_component_mps.size()!=std::size_t(in.nz)*std::size_t(in.nstations)||
       in.step1_mps.size()!=total||in.observation_weight.size()!=total)
        throw std::invalid_argument("INTER2 invalid field sizes");
    for(int n:in.nintrp_per_layer)
        if(n<1||n>in.nstations)
            throw std::invalid_argument("INTER2 NINTRP out of range");
    const auto finite=[](const std::vector<float>& xs){
        for(float x:xs)if(!std::isfinite(x))
            throw std::invalid_argument("INTER2 missing or nonfinite field");
    };
    finite(in.station_x_km);finite(in.station_y_km);
    finite(in.station_component_mps);finite(in.step1_mps);
    finite(in.observation_weight);
    for(float q:in.observation_weight)
        if(q<0.f||q>1.f)
            throw std::invalid_argument("INTER2 observation weight not in 0..1");
    const float dxk=in.dx_m*0.001f,dyk=in.dy_m*0.001f;
    const float rmax=std::max({in.rmax1_km,in.rmax2_km,in.rmax3_km});
    Inter2SelectedOutput out{std::vector<float>(total,0.f),
                             std::vector<int>(total,0),
                             std::vector<int>(total,0)};
    std::vector<float> rs(std::size_t(in.nstations),in.edit);
    std::vector<int> order(std::size_t(in.nstations),0);
    std::vector<float> closest(std::size_t(in.nz),9.9e9f);
    std::vector<int> closest_idx(std::size_t(in.nz),-1);
    for(int j=0;j<in.ny;++j)for(int i=0;i<in.nx;++i){
        const auto c=std::size_t(j)*std::size_t(in.nx)+std::size_t(i);
        const bool land=in.landuse[c]<in.water_first||in.landuse[c]>in.water_last;
        const float x=(static_cast<float>(i+1)-0.5f)*dxk;
        const float y=(static_cast<float>(j+1)-0.5f)*dyk;
        std::fill(rs.begin(),rs.end(),in.edit);
        std::fill(closest.begin(),closest.end(),9.9e9f);
        std::fill(closest_idx.begin(),closest_idx.end(),-1);
        for(int l=0;l<in.nstations;++l){
            bool has_any=false;
            for(int k=0;k<in.nz;++k){
                if(in.station_component_mps[std::size_t(k)*std::size_t(in.nstations)+std::size_t(l)]<in.editl){
                    has_any=true;break;
                }
            }
            if(!has_any)continue;
            const float delx=x-in.station_x_km[std::size_t(l)];
            const float dely=y-in.station_y_km[std::size_t(l)];
            // Preserve original RSX**2 + RSY**2 then sqrt (REAL*4).
            const float dist=std::sqrt(delx*delx+dely*dely);
            if(in.lvary)for(int k=0;k<in.nz;++k){
                const auto st=std::size_t(k)*std::size_t(in.nstations)+std::size_t(l);
                if(in.station_component_mps[st]<in.editl &&
                   dist<closest[std::size_t(k)]){
                    closest[std::size_t(k)]=dist;
                    closest_idx[std::size_t(k)]=l;
                }
            }
            const float adjusted=std::max(dist,in.rmin_km);
            rs[std::size_t(l)]=(adjusted<=rmax)?adjusted:in.edit;
        }
        if(in.lvary)for(int k=0;k<in.nz;++k)
            if(closest_idx[std::size_t(k)]<0)
                throw std::invalid_argument("INTER2 LVARY no valid observation for layer");
        // Original FMINF stable tie order, sorting only stations whose
        // distance is <= EDITL; nonselected station indices excluded.
        auto work=rs;
        int considered=0;
        for(int n=0;n<in.nstations;++n){
            int nearest=0;
            for(int l=1;l<in.nstations;++l)
                if(work[std::size_t(l)]<work[std::size_t(nearest)])
                    nearest=l;
            const float min_distance=work[std::size_t(nearest)];
            work[std::size_t(nearest)]=in.edit+static_cast<float>(n+1);
            if(min_distance>in.editl)break;
            order[std::size_t(considered++)]=nearest;
        }
        for(int k=0;k<in.nz;++k){
            const auto p=std::size_t(k)*cells+c;
            const float radius=(k==0)?in.rmax1_km:in.rmax2_km;
            const float influence=(k==0)?in.r1_km:in.r2_km;
            float sum=0.f,weighted=0.f; // original FIELD1/FIELD2 REAL*4
            int selected=0;
            for(int m=0;m<considered;++m){
                const int l=order[std::size_t(m)];
                const float observed=in.station_component_mps[
                    std::size_t(k)*std::size_t(in.nstations)+std::size_t(l)];
                if(observed>in.editl)continue;
                if(rs[std::size_t(l)]>(land?radius:in.rmax3_km))continue;
                // Fortran INTER2 declares WT DOUBLE PRECISION, but its
                // RHS WO(I,J,K)/(RS(L)**2) is evaluated as REAL*4
                // (WTGRD.MET WO and local RS are both REAL*4); only then
                // is that single-precision quotient widened into WT.
                // Do not square/divide in C++ double before assigning WT.
                const float range_m=rs[std::size_t(l)];
                const float rs_square=range_m*range_m;
                const float weight_real4=in.observation_weight[p]/rs_square;
                const double wt=static_cast<double>(weight_real4);
                sum=static_cast<float>(static_cast<double>(sum)+
                                      static_cast<double>(observed)*wt);
                weighted=static_cast<float>(static_cast<double>(weighted)+wt);
                if(++selected==in.nintrp_per_layer[std::size_t(k)])break;
            }
            if(selected==0&&in.lvary){
                const int l=closest_idx[std::size_t(k)];
                const float r=std::max(closest[std::size_t(k)],in.rmin_km);
                const float observed=in.station_component_mps[
                    std::size_t(k)*std::size_t(in.nstations)+std::size_t(l)];
                const float rs_square=r*r;
                const float weight_real4=in.observation_weight[p]/rs_square;
                const double wt=static_cast<double>(weight_real4);
                sum=static_cast<float>(static_cast<double>(sum)+
                                      static_cast<double>(observed)*wt);
                weighted=static_cast<float>(static_cast<double>(weighted)+wt);
                selected=1;
                out.nearest_fallback_used[p]=1;
            }
            // Original wt3=1/R**2 where R is REAL*4, wt3 DOUBLE PRECISION.
            // Original Fortran promotes resulting REAL intermediates to
            // DOUBLE PRECISION when assigning to wt3.
            const double step_weight=static_cast<double>(
                1.f/(influence*influence));
            const double result=(static_cast<double>(sum)+
                                static_cast<double>(in.step1_mps[p])*step_weight)/
                                (static_cast<double>(weighted)+step_weight);
            out.component_mps[p]=static_cast<float>(result);
            out.contributing_station_count[p]=selected;
        }
    }
    return out;
}
} // namespace cteas::calmet::p6
