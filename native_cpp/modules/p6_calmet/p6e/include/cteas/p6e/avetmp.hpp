#pragma once
// CALMET v6.5.0 AVETMP (calmet.for L2356-2592) - upwind-weighted spatial
// averaging of a 2-D surface temperature field. Called by SURFVAR when
// IAVET=1 (see SURFVAR L12878-12881) and by TEMP3D's caller; it is the step
// that makes TEMPK depend on the diagnostic wind field.
//
// Faithful port of the unmodified source: fixed DTIME=3600 s, DEGRAD as a
// REAL*4 literal, Fortran INT truncation for the integer displacement, the
// +/-MNMDAV square shortcut, the upwind cone test with the AMOD-wrapped
// bearings, the causal-frontier test on the squared distance, and the
// displaced 1/r**2 weight 1/(dela**2 + (1+|delc|)**2).
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace cteas::p6e {
struct AvetmpInput {
    std::size_t nx=0,ny=0;
    int mnmdav=1;
    float hafang_deg=30.f;
    float dgrid_m=100.f;
    std::vector<float> u_ms,v_ms,temperature_k;
};
// Fortran: AMOD(270. - ATAN2(JREL,IREL)/DEGRAD, 360.) - the first argument is
// the j (row) difference, the second the i (column) difference.
inline float avetmp_bearing(float jrel,float irel) {
    const float degrad=0.01745329f;
    return std::fmod(270.f-std::atan2(jrel,irel)/degrad,360.f);
}
inline std::vector<float> avetmp(const AvetmpInput& a) {
    const auto n=a.nx*a.ny;
    if(a.nx==0||a.ny==0||a.nx>static_cast<std::size_t>(-1)/a.ny||
       a.mnmdav<0||!std::isfinite(a.hafang_deg)||
       !std::isfinite(a.dgrid_m)||a.dgrid_m<=0.f||
       a.u_ms.size()!=n||a.v_ms.size()!=n||a.temperature_k.size()!=n)
        throw std::invalid_argument("AVETMP invalid extents or controls");
    for(std::size_t k=0;k<n;++k)
        if(!std::isfinite(a.u_ms[k])||!std::isfinite(a.v_ms[k])||
           !std::isfinite(a.temperature_k[k]))
            throw std::invalid_argument("AVETMP nonfinite input field");
    const float dtime=3600.f,one=1.f,zero=0.f;
    const float degrad=0.01745329f;
    const float dtdx=dtime/a.dgrid_m;
    const float tanang=std::tan(degrad*a.hafang_deg);
    std::vector<float> out(n,0.f);
    for(std::size_t i=0;i<a.nx;++i)
        for(std::size_t j=0;j<a.ny;++j) {
            const auto local=j*a.nx+i;
            const float etax=a.u_ms[local]*dtdx;
            const float etay=a.v_ms[local]*dtdx;
            const float eta2=etax*etax+etay*etay;
            float eta=zero,etai=zero;
            if(eta2>zero) {
                eta=std::sqrt(eta2);
                etai=one/eta;
            }
            const int ietax=static_cast<int>(etax);
            const int ietay=static_cast<int>(etay);
            const int icwx=static_cast<int>(etay*tanang);
            const int icwy=static_cast<int>(etax*tanang);
            const auto iu=static_cast<std::ptrdiff_t>(i)-ietax;
            const auto ju=static_cast<std::ptrdiff_t>(j)-ietay;
            const auto ia=iu+icwx,ib=iu-icwx;
            const auto ja=ju-icwy,jb=ju+icwy;
            const auto bearing=[](std::ptrdiff_t i,std::ptrdiff_t j,
                                  std::ptrdiff_t ii,std::ptrdiff_t jj) {
                if(i!=ii)
                    return avetmp_bearing(static_cast<float>(j-jj),
                                          static_cast<float>(i-ii));
                return j>=jj?180.f:0.f;
            };
            const float alphaa=bearing(static_cast<std::ptrdiff_t>(i),
                                       static_cast<std::ptrdiff_t>(j),ia,ja);
            const float alphab=bearing(static_cast<std::ptrdiff_t>(i),
                                       static_cast<std::ptrdiff_t>(j),ib,jb);
            const auto im1=static_cast<std::ptrdiff_t>(i)-a.mnmdav;
            const auto ip1=static_cast<std::ptrdiff_t>(i)+a.mnmdav;
            const auto jm1=static_cast<std::ptrdiff_t>(j)-a.mnmdav;
            const auto jp1=static_cast<std::ptrdiff_t>(j)+a.mnmdav;
            const auto kilow=std::max(std::min(std::min(ia,ib),im1),
                                      static_cast<std::ptrdiff_t>(0));
            const auto kihgh=std::min(std::max(std::max(ia,ib),ip1),
                                      static_cast<std::ptrdiff_t>(a.nx)-1);
            const auto kjlow=std::max(std::min(std::min(ja,jb),jm1),
                                      static_cast<std::ptrdiff_t>(0));
            const auto kjhgh=std::min(std::max(std::max(ja,jb),jp1),
                                      static_cast<std::ptrdiff_t>(a.ny)-1);
            float sumwt=zero,ztbar=zero;
            for(auto ki=kilow;ki<=kihgh;++ki)
                for(auto kj=kjlow;kj<=kjhgh;++kj) {
                    const float irel=static_cast<float>(i)-static_cast<float>(ki);
                    const float jrel=static_cast<float>(j)-static_cast<float>(kj);
                    float wt=one;
                    const bool is_local=irel==0.f&&jrel==0.f;
                    if(!is_local) {
                        const bool in_square=std::fabs(irel)<=a.mnmdav&&
                                             std::fabs(jrel)<=a.mnmdav;
                        if(!in_square) {
                            const float beta=avetmp_bearing(jrel,irel);
                            if(beta<alphaa||beta>alphab)continue;
                            const float dist=irel*irel+jrel*jrel;
                            if(dist>eta2)continue;
                        }
                        float dela=(irel*etax+jrel*etay)*etai;
                        if(eta==zero)dela=std::sqrt(irel*irel+jrel*jrel);
                        if(dela<zero)dela=eta-dela;
                        const float delc=std::fabs(irel*etay-jrel*etax)*etai;
                        wt=one/(dela*dela+(one+std::fabs(delc))*(one+std::fabs(delc)));
                    }
                    sumwt=sumwt+wt;
                    ztbar=ztbar+wt*a.temperature_k[static_cast<std::size_t>(kj)*a.nx+
                                                  static_cast<std::size_t>(ki)];
                }
            if(!(sumwt>0.f)||!std::isfinite(ztbar))
                throw std::invalid_argument("AVETMP empty upwind window");
            out[local]=ztbar/sumwt;
        }
    return out;
}
// AVEMIX (calmet.for L2104-2354, called by COMP L4715 when IAVEZI=1, with the
// ILEVZI wind level): the identical upwind weighting applied to ZI and ZICONV.
struct AvemixResult {
    std::vector<float> zi_m,ziconv_m;
};
inline AvemixResult avemix(const AvetmpInput& controls,
                           const std::vector<float>& zi_m,
                           const std::vector<float>& ziconv_m) {
    AvetmpInput a=controls;
    AvemixResult r;
    a.temperature_k=zi_m;
    r.zi_m=avetmp(a);
    a.temperature_k=ziconv_m;
    r.ziconv_m=avetmp(a);
    return r;
}
} // namespace cteas::p6e
