#include "cteas/puff/original_vmass.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace cteas::puff {
namespace {
using R=float;
constexpr R zero=0.0F,one=1.0F,half=0.5F;
constexpr R unlimited=1.0e04F;
constexpr R top_hat_factor=1.2533141F;
constexpr R wellmixed_ratio=1.6F, tilt_factor=2.0F;
void require(bool condition,const char* msg) {
    if(!condition)throw std::invalid_argument(std::string("P7 native VMASS: ")+msg);
}
void real(R v,const char* name) {require(std::isfinite(v),name);}
R total(const std::vector<R>& m) {
    R s=zero;
    for(const R v:m){real(v,"invalid REAL4 mass");require(v>=zero,"negative mass");s+=v;}
    real(s,"nonfinite total mass");return s;
}
void merge(VmassResult& o) {
    for(std::size_t i=0;i<o.mass_mixed.size();++i) {
        o.mass_mixed[i]=o.mass_above[i]+o.mass_mixed[i];
        o.mass_above[i]=zero;
    }
}
void transfer(VmassResult& o,R fac,bool only_positive_upper=false) {
    real(fac,"invalid two-layer mass fraction");
    for(std::size_t i=0;i<o.mass_mixed.size();++i) {
        if(only_positive_upper && o.mass_above[i]<=zero)continue;
        const R dq=(fac>=zero?o.mass_above[i]:o.mass_mixed[i])*fac;
        // Exact source order: QU = QU - DQ; QM = QM + DQ.
        o.mass_above[i]=o.mass_above[i]-dq;
        o.mass_mixed[i]=o.mass_mixed[i]+dq;
    }
}
bool mixing_limit(R szmin,R lid,R threshold){
    // Vendor divides REAL*4 SZMIN / HLID; refuse zero rather than accepting
    // Inf/NaN as scientifically plausible state.
    require(lid>zero,"zero reflecting lid at Gaussian well-mixed limit");
    return szmin/lid>threshold;
}
}
VmassResult original_vmass(const VmassInputs& in) {
    // VMASS L11667-11950, CALPUFF L150618. All arithmetic is REAL*4.
    const int code=in.puff_code;
    const int mfact0=(code>=11?10:0);
    require(code>=1 && code<=16 &&
            !(code>=7 && code<=10),"unsupported/invalid vendor puff code");
    require(in.stability_class>=1 && in.stability_class<=6,
            "stability class must be 1..6");
    require(in.plume_tilt>=0,"negative plume-tilt option");
    for(auto v:{in.pbl_height_m,in.height_begin_m,in.height_end_m,
                in.sigma_z_begin_m,in.sigma_z_end_m,in.ziold_m,in.zimax_m})
        real(v,"non-finite vendor vertical input");
    require(in.pbl_height_m>zero && in.height_begin_m>=zero &&
            in.height_end_m>=zero && in.sigma_z_begin_m>=zero &&
            in.sigma_z_end_m>=zero && in.ziold_m>=zero && in.zimax_m>=zero,
            "negative or zero vendor vertical geometry");
    require(!in.mass_mixed.empty() &&
            in.mass_above.size()==in.mass_mixed.size(),
            "incomplete per-species mixed/above state");
    VmassResult out{code,in.pbl_height_m,in.ziold_m,in.zimax_m,
                    in.mass_mixed,in.mass_above};
    const R qumass=total(out.mass_above);
    const R qmmass=total(out.mass_mixed);
    if(qumass==zero && qmmass>zero)
        out.zimax_m=out.ziold_m; // vendor L11688-11692

    const bool puff=mfact0==0;
    const R mean=puff?in.height_begin_m:
                     half*(in.height_begin_m+in.height_end_m);
    R sigma_min=zero,ptop0=zero;
    if(code%2==1){
        const R sigma_max=puff?in.sigma_z_begin_m:
            std::max(in.sigma_z_begin_m,in.sigma_z_end_m);
        sigma_min=puff?in.sigma_z_begin_m:
            std::min(in.sigma_z_begin_m,in.sigma_z_end_m);
        ptop0=mean+top_hat_factor*sigma_max;
    }
    const R threshold=in.plume_tilt>0?
        wellmixed_ratio*tilt_factor:wellmixed_ratio;
    R& lid=out.reflecting_lid_m;
    int& current=out.puff_code;
    const int type=code%10;

    if(type==4) {
        // CODE 4/14: uniform layer entirely above boundary layer.
        if(lid>=mean) {
            current=2+mfact0;
            merge(out);
        }
    } else if(code%2==0) {
        // CODE 2/6 and slug forms 12/16.
        if(lid>=out.zimax_m) {
            merge(out);
            out.zimax_m=lid;
            out.ziold_m=lid;
            current=2+mfact0;
        } else {
            if(lid>=out.ziold_m) {
                require(out.zimax_m>out.ziold_m,
                        "degenerate original layer depth for upward entrainment");
                R fac=(lid-out.ziold_m)/(out.zimax_m-out.ziold_m);
                if(fac>one)fac=one;
                transfer(out,fac);
            } else {
                // Shrinking PBL: upper layer absorbs part of QM.
                R qmtotal=zero;
                for(const R q:out.mass_mixed)qmtotal+=q;
                if(qmtotal==zero) {
                    lid=out.ziold_m;
                } else {
                    require(out.ziold_m>zero,
                            "degenerate original old lid for shrink transfer");
                    R fac=(lid-out.ziold_m)/out.ziold_m;
                    if(fac< -one)fac=-one;
                    transfer(out,fac);
                }
            }
            out.ziold_m=lid;
            current=6+mfact0;
        }
    } else if(in.stability_class>=5) {
        // Gaussian stable layer code 3/13 becomes code 1/11.
        if(type==3) {
            current=1+mfact0;lid=unlimited;
            out.zimax_m=unlimited;out.ziold_m=unlimited;
            merge(out);
        } else {
            lid=out.ziold_m;
        }
        if(mixing_limit(sigma_min,lid,threshold))++current;
    } else if(type==1) {
        // Gaussian entirely inside the current surface layer.
        if(lid<mean) {
            lid=out.ziold_m;
            current=5+mfact0;
        } else if(lid<out.ziold_m) {
            const R top=std::min(ptop0,out.ziold_m);
            lid=std::max(lid,top);
        }
        out.zimax_m=lid;out.ziold_m=lid;
        if(mixing_limit(sigma_min,lid,threshold)) {
            if(lid>in.pbl_height_m) {
                current=6+mfact0;
                R fac=(in.pbl_height_m-lid)/lid;
                if(fac< -one)fac=-one;
                transfer(out,fac);
                out.ziold_m=in.pbl_height_m;
                lid=in.pbl_height_m;
            } else current=2+mfact0;
        }
    } else if(type==3) {
        // Gaussian released entirely above the surface layer.
        if(lid>=mean) {
            R fup=zero;
            if(lid>=ptop0) {
                current=1+mfact0;
                out.zimax_m=lid;out.ziold_m=lid;
            } else {
                require(ptop0>mean,"degenerate original Gaussian top-hat depth");
                fup=half*(ptop0-lid)/(ptop0-mean);
                current=5+mfact0;
                out.zimax_m=ptop0;out.ziold_m=lid;
            }
            for(std::size_t i=0;i<out.mass_mixed.size();++i) {
                const R qtot=out.mass_above[i]+out.mass_mixed[i];
                out.mass_above[i]=fup*qtot;
                out.mass_mixed[i]=qtot-out.mass_above[i];
            }
            if(mixing_limit(sigma_min,lid,threshold))++current;
        }
    } else if(type==5) {
        if(lid>=out.zimax_m) {
            merge(out);current=1+mfact0;
            out.zimax_m=lid;out.ziold_m=lid;
            if(mixing_limit(sigma_min,lid,threshold))++current;
        } else if(lid<mean) {
            lid=out.ziold_m;
            if(mixing_limit(sigma_min,lid,threshold))++current;
        } else if(lid<out.ziold_m) {
            const R top=std::min(ptop0,out.ziold_m);
            lid=std::max(lid,top);
            out.ziold_m=lid;
            if(mixing_limit(sigma_min,lid,threshold))++current;
        } else {
            require(out.zimax_m>out.ziold_m,
                    "degenerate original Gaussian upper-layer thickness");
            R fac=(lid-out.ziold_m)/(out.zimax_m-out.ziold_m);
            if(fac>one)fac=one;
            transfer(out,fac,true);
            out.ziold_m=lid;
            if(mixing_limit(sigma_min,lid,threshold))++current;
        }
    } else throw std::invalid_argument("P7 native VMASS: unsupported vendor code");
    real(lid,"computed reflecting lid");
    real(out.ziold_m,"computed ZIOLD");
    real(out.zimax_m,"computed ZIMAX");
    for(const auto& m:out.mass_mixed)real(m,"nonfinite post-VMASS QM");
    for(const auto& m:out.mass_above)real(m,"nonfinite post-VMASS QU");
    return out;
}
} // namespace cteas::puff
