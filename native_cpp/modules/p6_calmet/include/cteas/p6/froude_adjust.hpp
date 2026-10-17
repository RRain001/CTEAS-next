#pragma once
// P6D original CALMET FRADJ (Fortran calmet.for L7289–7455).
// Tested as an isolated subroutine, never as a substitute for full DIAGNO.
// The source's TAU=-0.01, RPD=0.017453 and DPR=57.296 are literal float32.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace cteas::calmet::p6 {
struct WindUV {
    std::vector<float> u;
    std::vector<float> v;
};
inline WindUV froude_adjust(
    int nx,int ny,int nz,float dx_m,float dy_m,
    const std::vector<float>& terrain_m,
    const std::vector<float>& maximum_terrain_m,
    const std::vector<float>& lapse_rate_k_per_m,
    const std::vector<float>& surface_temperature_k,
    int isurft,float tinf_k,float critfn,
    const std::vector<float>& zface_m,
    WindUV winds) {

    if(nx<1||ny<1||nz<1||nx>400||ny>400||nz>12)
        throw std::invalid_argument("FRADJ unsupported grid");
    const std::size_t plane=std::size_t(nx)*std::size_t(ny);
    if(terrain_m.size()!=plane||maximum_terrain_m.size()!=plane||
       lapse_rate_k_per_m.size()!=plane||surface_temperature_k.size()!=plane||
       winds.u.size()!=plane*std::size_t(nz)||winds.v.size()!=plane*std::size_t(nz)||
       zface_m.size()!=std::size_t(nz)+1)
        throw std::invalid_argument("FRADJ input field shape");
    if(!(dx_m>0&&dy_m>0&&critfn>=0)||
       !std::isfinite(dx_m)||!std::isfinite(dy_m)||!std::isfinite(critfn)||
       !std::isfinite(tinf_k)||tinf_k<=0)
        throw std::invalid_argument("FRADJ invalid metric or temperature");
    for(std::size_t n=0;n<plane;++n)
        if(!std::isfinite(terrain_m[n])||!std::isfinite(maximum_terrain_m[n])||
           !std::isfinite(lapse_rate_k_per_m[n])||!std::isfinite(surface_temperature_k[n])||
           !(surface_temperature_k[n]>0))
            throw std::invalid_argument("FRADJ invalid terrain/thermodynamics");
    for(std::size_t k=0;k<zface_m.size();++k)
        if(!std::isfinite(zface_m[k])||(k>0&&zface_m[k]<=zface_m[k-1]))
            throw std::invalid_argument("FRADJ invalid layer faces");
    for(float x:winds.u)if(!std::isfinite(x))throw std::invalid_argument("FRADJ U missing");
    for(float x:winds.v)if(!std::isfinite(x))throw std::invalid_argument("FRADJ V missing");

    constexpr float tau=-0.01f,rpd=0.017453f,dpr=57.296f;
    // Original does 0.5/DX inside every cell in Fortran REAL*4.
    const float dxi=0.5f/dx_m;
    const float dyi=0.5f/dy_m;
    auto at=[nx](int i,int j)->std::size_t{
        return std::size_t(j)*std::size_t(nx)+std::size_t(i);
    };
    for(int j=0;j<ny;++j)for(int i=0;i<nx;++i){
        const std::size_t n=at(i,j);
        const float gamma2=lapse_rate_k_per_m[n]-tau;
        const float ht_im1=terrain_m[at(std::max(i-1,0),j)];
        const float ht_jm1=terrain_m[at(i,std::max(j-1,0))];
        const float ht_ip1=terrain_m[at(std::min(i+1,nx-1),j)];
        const float ht_jp1=terrain_m[at(i,std::min(j+1,ny-1))];
        float delhi=(ht_ip1-ht_im1)*dxi;
        float delhj=(ht_jp1-ht_jm1)*dyi;
        if(std::abs(delhi)<0.00015f&&std::abs(delhj)<0.00015f){
            delhi=0.0f;delhj=0.0f;
        }
        const float temp=isurft==-1?surface_temperature_k[n]:tinf_k;
        for(int k=0;k<nz;++k){
            const auto idx=std::size_t(k)*plane+n;
            const float u=winds.u[idx],v=winds.v[idx];
            const float speed=std::sqrt(u*u+v*v);
            if(speed<=0)continue;
            const float obs_height=maximum_terrain_m[n]-
                (terrain_m[n]+zface_m[std::size_t(k)]+
                 (zface_m[std::size_t(k)+1]-zface_m[std::size_t(k)])/2.0f);
            if(obs_height<=0||gamma2<=0)continue;
            const float froude=speed/(std::sqrt(9.8f*gamma2/temp)*obs_height);
            if(froude>critfn)continue;
            float theta=0;
            if(delhi==0){
                if(delhj==0)continue;
                theta=delhj<0?270.0f:90.0f;
            }else{
                const float theta_p=std::atan(delhj/delhi)*dpr;
                if(delhi<0)theta=theta_p+180.0f;
                if(delhi>0)theta=delhj>0?theta_p:theta_p+360.0f;
            }
            float theta_d=0;
            if(theta>=0&&theta<=90.0f)theta_d=90.0f-theta;
            if(theta>90.0f&&theta<=360.0f)theta_d=450.0f-theta;
            const float angle=(270.0f-theta_d)*rpd;
            const float drx=-std::cos(angle);
            const float dry=-std::sin(angle);
            const float un=u/speed,vn=v/speed;
            const float aa=drx*un+dry*vn;
            if(aa<=0.0f)continue;
            const float tt=-dry*un+drx*vn;
            const float tax=tt>0.0f?-dry:dry;
            const float tay=tt>0.0f?drx:-drx;
            winds.u[idx]=tax*speed;
            winds.v[idx]=tay*speed;
        }
    }
    return winds;
}
} // namespace cteas::calmet::p6
