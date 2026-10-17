#pragma once
// Source-scoped CALMET v6.5.0 L150223 station-profile extrapolation:
//   SIMILT  calmet.for L30097-L30370 (Van Ulden & Holtslag 1985)
//   PSIUD   calmet.for L35629-L35672 (COARE-like, Dyer factor 16)
// Selected route: IPSIFCN=0, overland station (NS<=NSSTA, XSLAT), the deck's
// IEXTRP=-4 IABS branch, EL/ZI/ZIMINI supplied by the caller. The same kernel
// serves WIND1's first guess, whose call is deliberately neutral and uncapped
// (L36171: ZMO=ZML=10000.), and DIAGI's station column, whose call passes
// ZII=AMAX1(ZIMECH,ZICONV) and ZIMIN (L6894).
// NOT implemented (fail-closed): IPSIFCN=1 (PSIUC/COARE), overwater stations
// (XOWLAT), barrier effects.
#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>
namespace cteas::calmet::p6 {

// Original PSIUD, calmet.for L35629-L35672. Double precision as in the source.
inline double original_psiud(double zL) {
    double x,y,psik,psic,f,c;
    if(zL<0.0){
        x=std::pow(1.0-16.0*zL,0.25);
        psik=2.0*std::log((1.0+x)/2.0)+std::log((1.0+x*x)/2.0)-
             2.0*std::atan(x)+2.0*std::atan(1.0);
        y=std::pow(1.0-10.15*zL,0.3333);
        psic=1.5*std::log((1.0+y+y*y)/3.0)-std::sqrt(3.0)*
             std::atan((1.0+2.0*y)/std::sqrt(3.0))+
             4.0*std::atan(1.0)/std::sqrt(3.0);
        f=zL*zL/(1.0+zL*zL);
        return (1.0-f)*psik+f*psic;
    }
    c=std::min(50.0,0.35*zL);
    return -((1.0+zL)+0.6667*(zL-14.28)/std::exp(c)+8.525);
}

struct SimiltProfileInput {
    float station_lat_deg=0.f;
    float anemometer_height_m=0.f;
    float roughness_m=0.f;
    float anemometer_u_mps=0.f;
    float anemometer_v_mps=0.f;
    // EL: Monin-Obukhov length. |EL|>=10000 is the neutral branch.
    float obukhov_length_m=0.f;
    // ZI: mixing height used by the extrapolation cutoff.
    float mixing_height_m=0.f;
    // ZIMINI: lower bound applied to that cutoff (deck ZIMIN).
    float minimum_mixing_height_m=0.f;
    int ipsifcn=0;
    std::array<float,10> zface_m{};
};

struct SimiltProfileOutput {
    std::array<float,9> u_mps{};
    std::array<float,9> v_mps{};
    // Number of levels SIMILT wrote (levels 1..levels_filled, i.e. ZMID(1) up
    // to ZMID(levels_filled)); the levels above keep their prior content
    // (missing for a station column, the original's "above mixing height" exit).
    std::size_t levels_filled=1;
};

inline SimiltProfileOutput original_similt_profile(const SimiltProfileInput& in) {
    // Table 2 of Van Ulden & Holtslag (1985) as coded at L30188-L30197.
    constexpr std::array<double,9> eltbli{-0.03333333,-0.01,-0.0027027,0.0,
        0.002857,0.007692,0.0166667,0.05,0.1111111};
    constexpr std::array<double,9> dhtbl2{12.,10.,9.,12.,18.,28.,35.,38.,39.};
    constexpr float factor=57.2957795f;
    constexpr float deg2rad=0.0174533f;
    constexpr float d1=1.58f,d2=1.f,ztbl2=200.f;
    const auto finite=[](float x){return std::isfinite(x);};
    if(in.ipsifcn!=0)
        throw std::invalid_argument("SIMILT: IPSIFCN=1 (PSIUC/COARE) not ported");
    if(!finite(in.station_lat_deg)||in.station_lat_deg==0.f)
        throw std::invalid_argument("SIMILT: station latitude required");
    if(!finite(in.anemometer_height_m)||in.anemometer_height_m<=0.f||
       !finite(in.roughness_m)||in.roughness_m<=0.f||
       in.roughness_m>=in.anemometer_height_m||in.roughness_m>=10.f)
        throw std::invalid_argument("SIMILT: invalid anemometer/roughness geometry");
    if(!finite(in.anemometer_u_mps)||!finite(in.anemometer_v_mps))
        throw std::invalid_argument("SIMILT: nonfinite anemometer wind");
    if(!finite(in.obukhov_length_m)||in.obukhov_length_m==0.f||
       !finite(in.mixing_height_m)||in.mixing_height_m<=0.f||
       !finite(in.minimum_mixing_height_m))
        throw std::invalid_argument("SIMILT: EL/ZI/ZIMINI required and finite");
    for(std::size_t k=1;k<10;++k)
        if(!finite(in.zface_m[k])||!(in.zface_m[k]>in.zface_m[k-1]))
            throw std::invalid_argument("SIMILT: zface must be strictly increasing");
    const float speed=std::sqrt(in.anemometer_u_mps*in.anemometer_u_mps+
                                in.anemometer_v_mps*in.anemometer_v_mps);
    // Both original call sites skip SIMILT for calm stations.
    if(!finite(speed)||speed<0.0001f)
        throw std::invalid_argument("SIMILT: calm station is not extrapolated");
    const float angle=270.f-std::atan2(in.anemometer_v_mps,
                                      in.anemometer_u_mps)*factor;
    float wd1=std::fmod(angle,360.f);   // original AMOD, sign of the dividend
    if(wd1==0.f)wd1=360.f;
    // L30207-L30215: restrict the Monin-Obukhov length to at least 5*z0.
    float eladj=in.obukhov_length_m;
    if(std::abs(eladj)<5.f*in.roughness_m)
        eladj=eladj<0.f?-5.f*in.roughness_m:5.f*in.roughness_m;
    const double elinv=std::abs(eladj)>=10000.f?0.0:1.0/double(eladj);
    const float base_log=std::log(in.anemometer_height_m/in.roughness_m);
    if(!finite(base_log)||base_log<=0.f)
        throw std::invalid_argument("SIMILT: singular log-profile");
    const double psim1=std::abs(elinv)<0.00005
        ?0.0:original_psiud(double(in.anemometer_height_m)/double(eladj));
    // L30279-L30307: turning angle from Table 2 at z = 200 m.
    double dh200=dhtbl2[3];
    if(std::abs(elinv)>=0.00005){
        dh200=dhtbl2[8];
        for(std::size_t i=0;i<9;++i){
            if(eltbli[i]>=elinv){
                dh200=i==0?dhtbl2[0]
                    :dhtbl2[i-1]+(dhtbl2[i]-dhtbl2[i-1])*
                                 (elinv-eltbli[i-1])/(eltbli[i]-eltbli[i-1]);
                break;
            }
        }
    }
    const float dzan=static_cast<float>(dh200)*d1*
        (1.f-std::exp(-d2*in.anemometer_height_m/ztbl2));
    const float cutoff=std::max(in.mixing_height_m+0.001f,
                                in.minimum_mixing_height_m);
    SimiltProfileOutput out;
    for(std::size_t k=2;k<=10;++k){
        // Original loop K=2..NZP1 writes US(K-1,NS), i.e. C++ index K-2 at
        // ZMID(K-1); the test uses ZFACE(K).
        // L30319: "above mixing height, exit" - the levels above keep their
        // prior content instead of a surface extrapolation.
        if(!(in.zface_m[k-1]<=cutoff))break;
        const float mid=0.5f*(in.zface_m[k-2]+in.zface_m[k-1]);
        const float xlnzz0=std::log(mid/in.roughness_m);
        const double psim=std::abs(elinv)<0.00005
            ?0.0:original_psiud(double(mid)/double(eladj));
        const float ws=speed*static_cast<float>(xlnzz0-psim)/
                       static_cast<float>(base_log-psim1);
        const float dwd=static_cast<float>(dh200)*d1*
            (1.f-std::exp(-d2*mid/ztbl2));
        float wd;
        if(in.station_lat_deg>0.f){          // northern: winds veer
            wd=wd1+dwd-dzan;
            if(wd>360.f)wd-=360.f;
        }else{                                // southern: winds back
            wd=wd1-dwd+dzan;
            if(wd<=0.f)wd=360.f+wd;
        }
        const float wdrad=deg2rad*wd;
        out.u_mps[k-2]=-ws*std::sin(wdrad);
        out.v_mps[k-2]=-ws*std::cos(wdrad);
        if(!finite(out.u_mps[k-2])||!finite(out.v_mps[k-2]))
            throw std::invalid_argument("SIMILT: nonfinite extrapolated wind");
        out.levels_filled=k-1;
    }
    return out;
}
} // namespace cteas::calmet::p6
