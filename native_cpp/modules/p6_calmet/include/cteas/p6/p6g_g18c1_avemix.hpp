#pragma once
// G18C1: CALMET 6.5.0 AVEMIX exact selected IAVEZI=1 source formula.
// This physics routine is NOT previously frozen/accepted in PR #53;
// independent original-vendor Fortran source parity is required.
// Current candidate is not a G14 COMP or P6F scientific acceptance.
#include "cteas/p6/p6g_g18a_selected_comp_mixht.hpp"
#include "cteas/p6/p6g_original_wind_controls.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6g {
struct G18C1AvemixControls {
    int iavezi=0,mnmdav=0,ilevzi=0;
    float hafang_deg=0.f;
};
inline int g18c1_source_integer(const std::string& deck,const char* name) {
    const auto value=source_wind_normalize(source_wind_value(deck,name));
    std::size_t used=0;int v=0;
    try{v=std::stoi(value,&used);}
    catch(const std::exception&){
        throw std::invalid_argument(std::string("G18C1 invalid source ")+name);
    }
    if(used!=value.size())
        throw std::invalid_argument(std::string("G18C1 malformed source ")+name);
    return v;
}
inline G18C1AvemixControls g18c1_parse_original_avemix(
    const std::string& source_metinp) {
    G18C1AvemixControls out;
    out.iavezi=g18c1_source_integer(source_metinp,"IAVEZI");
    out.mnmdav=g18c1_source_integer(source_metinp,"MNMDAV");
    out.ilevzi=g18c1_source_integer(source_metinp,"ILEVZI");
    const auto value=source_wind_normalize(source_wind_value(source_metinp,"HAFANG"));
    std::size_t used=0;
    try{out.hafang_deg=std::stof(value,&used);}
    catch(const std::exception&){
        throw std::invalid_argument("G18C1 malformed source HAFANG");
    }
    if(used!=value.size()||out.iavezi!=1||out.mnmdav<0||
       out.mnmdav>20||out.ilevzi<1||out.ilevzi>9||
       !std::isfinite(out.hafang_deg)||out.hafang_deg<=0.f||
       out.hafang_deg>=90.f)
        throw std::invalid_argument("G18C1 source AVEMIX branch not yet certified");
    return out;
}
struct G18C1AvemixOutput {
    std::vector<float> zi_m,ziconv_m;
};
inline G18C1AvemixOutput g18c1_original_avemix_rebuild(
    int nx,int ny,int mnmdav,float hafang_deg,float dgrid_m,
    const std::vector<float>& u,const std::vector<float>& v,
    const std::vector<float>& zi,const std::vector<float>& ziconv) {
    if(nx<2||ny<2||nx>400||ny>400||
       mnmdav<0||mnmdav>20||
       !std::isfinite(hafang_deg)||hafang_deg<=0.f||hafang_deg>=90.f||
       !std::isfinite(dgrid_m)||dgrid_m<=0.f)
        throw std::invalid_argument("G18C1 invalid AVEMIX source dimensions/control");
    const auto cells=static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny);
    if(u.size()!=cells||v.size()!=cells||zi.size()!=cells||ziconv.size()!=cells)
        throw std::invalid_argument("G18C1 source AVEMIX array extent mismatch");
    for(std::size_t p=0;p<cells;++p)
        if(!std::isfinite(u[p])||!std::isfinite(v[p])||
           !std::isfinite(zi[p])||!std::isfinite(ziconv[p])||
           zi[p]<0.f||ziconv[p]<0.f)
            throw std::invalid_argument("G18C1 original AVEMIX input nonfinite/negative");
    constexpr float dtime=3600.f,one=1.f,zero=0.f,degrad=0.01745329f;
    const float dtdx=dtime/dgrid_m;
    const float tanang=std::tan(degrad*hafang_deg);
    G18C1AvemixOutput out;
    out.zi_m.resize(cells);
    out.ziconv_m.resize(cells);
    // Literally match original AVEMIX source: DO 100 I; DO 100 J.
    // All weights use input ZI/ZICONV, never an in-place partial average.
    for(int i=1;i<=nx;++i) {
        const int ip1=i+mnmdav,im1=i-mnmdav;
        for(int j=1;j<=ny;++j) {
            const int jp1=j+mnmdav,jm1=j-mnmdav;
            const auto cell=[nx](int ii,int jj){
                return static_cast<std::size_t>(jj-1)*
                       static_cast<std::size_t>(nx)+static_cast<std::size_t>(ii-1);
            };
            const auto pos=cell(i,j);
            const float etax=u[pos]*dtdx,etay=v[pos]*dtdx;
            const float eta2=etax*etax+etay*etay;
            float eta,etai;
            if(eta2>zero) {eta=std::sqrt(eta2);etai=one/eta;}
            else {eta=zero;etai=zero;}
            // Fortran INT truncates toward zero, including negative wind.
            const int ietax=static_cast<int>(etax),ietay=static_cast<int>(etay);
            const int icwx=static_cast<int>(etay*tanang);
            const int icwy=static_cast<int>(etax*tanang);
            const int iu=i-ietax,ju=j-ietay;
            const int ia=iu+icwx,ib=iu-icwx;
            const int ja=ju-icwy,jb=ju+icwy;
            float alphaa,alphab;
            if(i!=ia) {
                alphaa=270.f-std::atan2(static_cast<float>(j-ja),
                                         static_cast<float>(i-ia))/degrad;
                alphaa=std::fmod(alphaa,360.f);
            }else alphaa=(j>=ja?180.f:0.f);
            if(i!=ib) {
                alphab=270.f-std::atan2(static_cast<float>(j-jb),
                                         static_cast<float>(i-ib))/degrad;
                alphab=std::fmod(alphab,360.f);
            }else alphab=(j>=jb?180.f:0.f);
            const int kilow=std::max(std::min({ia,ib,im1}),1);
            const int kihgh=std::min(std::max({ia,ib,ip1}),nx);
            const int kjlow=std::max(std::min({ja,jb,jm1}),1);
            const int kjhgh=std::min(std::max({ja,jb,jp1}),ny);
            float sumwt=zero,zibar=zero,zicbar=zero;
            for(int ki=kilow;ki<=kihgh;++ki) {
                const int irel=i-ki;
                for(int kj=kjlow;kj<=kjhgh;++kj) {
                    const int jrel=j-kj;
                    float wt=one;
                    if(irel!=0||jrel!=0) {
                        const bool inside_square=(std::abs(irel)<=mnmdav&&
                                                  std::abs(jrel)<=mnmdav);
                        if(!inside_square) {
                            float beta=270.f-std::atan2(
                                static_cast<float>(jrel),
                                static_cast<float>(irel))/degrad;
                            beta=std::fmod(beta,360.f);
                            if(beta<alphaa||beta>alphab)continue;
                            const int dist=irel*irel+jrel*jrel;
                            if(static_cast<float>(dist)>eta2)continue;
                        }
                        float dela=(static_cast<float>(irel)*etax+
                                    static_cast<float>(jrel)*etay)*etai;
                        if(eta==zero) {
                            const float xrel=static_cast<float>(irel);
                            const float yrel=static_cast<float>(jrel);
                            dela=std::sqrt(xrel*xrel+yrel*yrel);
                        }
                        if(dela<zero)dela=eta-dela;
                        const float delc=std::fabs(
                            static_cast<float>(irel)*etay-
                            static_cast<float>(jrel)*etax)*etai;
                        const float spread=one+std::fabs(delc);
                        wt=one/(dela*dela+spread*spread);
                    }
                    sumwt=sumwt+wt;
                    zibar=zibar+wt*zi[cell(ki,kj)];
                    zicbar=zicbar+wt*ziconv[cell(ki,kj)];
                }
            }
            if(!(sumwt>0.f)||!std::isfinite(sumwt))
                throw std::invalid_argument("G18C1 empty/nonfinite original AVEMIX weight");
            out.zi_m[pos]=zibar/sumwt;
            out.ziconv_m[pos]=zicbar/sumwt;
        }
    }
    return out;
}
inline G18C1AvemixOutput g18c1_selected_after_mixht(
    const MultiHourFrame& frame,const G18ASelectedCompResult& pre_average,
    const G18C1AvemixControls& ctrl,bool explicitly_test_only) {
    const auto n=static_cast<std::size_t>(frame.grid.nx)*
                 static_cast<std::size_t>(frame.grid.ny);
    if(!explicitly_test_only||!frame.source_controls||
       frame.input.end!=pre_average.end||
       ctrl.iavezi!=1||ctrl.ilevzi<1||ctrl.ilevzi>9||
       pre_average.candidate_next.zi_m.size()!=n||
       pre_average.candidate_next.ziconv_m.size()!=n||
       frame.fields.u_mps.size()!=9*n||
       frame.fields.v_mps.size()!=9*n)
        throw std::invalid_argument("G18C1 source MIXHT/WIND temporal readiness absent");
    const auto offset=static_cast<std::size_t>(ctrl.ilevzi-1)*n;
    const std::vector<float> u(frame.fields.u_mps.begin()+offset,
                               frame.fields.u_mps.begin()+offset+n);
    const std::vector<float> v(frame.fields.v_mps.begin()+offset,
                               frame.fields.v_mps.begin()+offset+n);
    return g18c1_original_avemix_rebuild(
        frame.grid.nx,frame.grid.ny,ctrl.mnmdav,ctrl.hafang_deg,
        frame.grid.grid_km*1000.f,u,v,pre_average.candidate_next.zi_m,
        pre_average.candidate_next.ziconv_m);
}
} // namespace cteas::calmet::p6g
