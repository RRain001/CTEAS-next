#include "cteas/puff/transport.hpp"
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
namespace cteas::puff {
namespace {
void check(bool ok,const char* s) {
    if (!ok) throw std::invalid_argument(std::string("P7C ")+s);
}
bool finite(double x) {return std::isfinite(x);}
std::size_t index(const WindField& f,int i,int j,int z) {
    return (static_cast<std::size_t>(z)*static_cast<std::size_t>(f.ny)+
            static_cast<std::size_t>(j))*static_cast<std::size_t>(f.nx)+
           static_cast<std::size_t>(i);
}
double xy(const WindField& f,const std::vector<float>& a,double x,double y,int z) {
    const double fx=std::clamp((x-f.origin_x_m)/f.spacing_m-0.5,0.0,double(f.nx-1));
    const double fy=std::clamp((y-f.origin_y_m)/f.spacing_m-0.5,0.0,double(f.ny-1));
    const int i=static_cast<int>(fx),j=static_cast<int>(fy);
    const int ii=std::min(i+1,f.nx-1),jj=std::min(j+1,f.ny-1);
    const double tx=fx-i,ty=fy-j;
    const double lo=(1-tx)*a[index(f,i,j,z)]+tx*a[index(f,ii,j,z)];
    const double hi=(1-tx)*a[index(f,i,jj,z)]+tx*a[index(f,ii,jj,z)];
    return (1-ty)*lo+ty*hi;
}
} // namespace
void WindField::validate() const {
    check(nx>0&&ny>0&&nz>0&&nx<=4096&&ny<=4096&&nz<=99,"bad grid dimensions");
    check(finite(spacing_m)&&spacing_m>0&&finite(origin_x_m)&&finite(origin_y_m),
          "bad grid geometry");
    const std::size_t n=std::size_t(nx)*std::size_t(ny)*std::size_t(nz);
    check(level_m.size()==std::size_t(nz)&&u.size()==n&&v.size()==n&&w.size()==n,
          "bad grid field sizes");
    for(std::size_t i=0;i<level_m.size();++i) {
        check(finite(level_m[i])&&level_m[i]>=0,"invalid vertical level");
        if (i) check(level_m[i]>level_m[i-1],"unordered vertical levels");
    }
    for (const auto* array:{&u,&v,&w}) for(float value:*array)
        check(std::isfinite(value),"non-finite wind field");
}
bool WindField::contains(double x,double y,double z) const {
    return finite(x)&&finite(y)&&finite(z)&&
        x>=origin_x_m&&x<origin_x_m+nx*spacing_m&&
        y>=origin_y_m&&y<origin_y_m+ny*spacing_m&&
        z>=0&&z<=level_m.back();
}
std::vector<double> WindField::velocity(double x,double y,double z) const {
    if (!contains(x,y,z)) throw std::out_of_range("P7C wind outside domain");
    const auto at=std::lower_bound(level_m.begin(),level_m.end(),z);
    const int top=at==level_m.end()?nz-1:int(at-level_m.begin());
    const int below=std::max(0,top-1);
    const double factor=top==below?0:
        std::clamp((z-level_m[below])/(level_m[top]-level_m[below]),0.0,1.0);
    auto get=[&](const std::vector<float>& a) {
        return (1-factor)*xy(*this,a,x,y,below)+factor*xy(*this,a,x,y,top);
    };
    return {get(u),get(v),get(w)};
}
PuffTransport::PuffTransport(std::size_t count)
    :species_(count),released_(count,0.0),outflow_(count,0.0) {
    check(count>0&&count<=64,"invalid species count");
}
void PuffTransport::emit(const PointRelease& src,double dt) {
    check(finite(src.x_m)&&finite(src.y_m)&&finite(src.z_m),"invalid source location");
    check(finite(dt)&&dt>0&&dt<=3600,"invalid source time step");
    check(src.rate_per_s.size()==species_,"emitted species mismatch");
    check(packets_.size()<1000000,"prototype puff limit exceeded");
    PuffPacket p;
    p.id=next_id_++;
    p.x_m=src.x_m;p.y_m=src.y_m;p.z_m=src.z_m;
    for(double rate:src.rate_per_s) {
        check(finite(rate)&&rate>=0,"invalid emission rate");
        const double mass=rate*dt;
        check(finite(mass),"emission mass overflow");
        p.mass.push_back(mass);
    }
    for(std::size_t i=0;i<species_;++i) {
        check(finite(released_[i]+p.mass[i]),"cumulative emission overflow");
    }
    for(std::size_t i=0;i<species_;++i) released_[i]+=p.mass[i];
    packets_.push_back(std::move(p));
}
void PuffTransport::advect(const WindField& grid,double dt) {
    check(finite(dt)&&dt>0&&dt<=3600,"invalid advection time step");
    grid.validate();
    for(auto& puff:packets_) {
        if (!puff.active) continue;
        if (!grid.contains(puff.x_m,puff.y_m,puff.z_m)) {
            for(std::size_t s=0;s<species_;++s) outflow_[s]+=puff.mass[s];
            puff.active=false;
            continue;
        }
        const auto v=grid.velocity(puff.x_m,puff.y_m,puff.z_m);
        const double mx=puff.x_m+v[0]*dt*0.5;
        const double my=puff.y_m+v[1]*dt*0.5;
        const double mz=puff.z_m+v[2]*dt*0.5;
        if (!grid.contains(mx,my,mz)) {
            for(std::size_t s=0;s<species_;++s) outflow_[s]+=puff.mass[s];
            puff.x_m=mx;puff.y_m=my;puff.z_m=mz;puff.active=false;
            continue;
        }
        const auto vm=grid.velocity(mx,my,mz);
        puff.x_m+=vm[0]*dt;puff.y_m+=vm[1]*dt;puff.z_m+=vm[2]*dt;
        if (!grid.contains(puff.x_m,puff.y_m,puff.z_m)) {
            for(std::size_t s=0;s<species_;++s) outflow_[s]+=puff.mass[s];
            puff.active=false;
        }
    }
}
MassBalance PuffTransport::balance() const {
    MassBalance b;
    b.released=released_;b.outflow=outflow_;
    b.inventory.assign(species_,0);b.total=packets_.size();
    for(const auto& p:packets_) if (p.active) {
        ++b.active;
        for(std::size_t s=0;s<species_;++s) b.inventory[s]+=p.mass[s];
    }
    for(std::size_t s=0;s<species_;++s) {
        check(finite(b.inventory[s])&&finite(b.outflow[s]),
              "inventory or outflow overflow");
        check(std::abs(b.released[s]-b.inventory[s]-b.outflow[s])<=
                1e-9*std::max(1.0,b.released[s]),"mass closure failed");
    }
    return b;
}
std::vector<double> level_centers_from_zface(const std::vector<double>& edges) {
    check(edges.size()>1,"missing vertical interfaces");
    std::vector<double> result;
    for(std::size_t i=1;i<edges.size();++i) {
        check(finite(edges[i-1])&&finite(edges[i])&&
              edges[i]>edges[i-1]&&edges[i-1]>=0,"non-monotonic interfaces");
        result.push_back((edges[i]+edges[i-1])*0.5);
    }
    return result;
}
PointRelease point_source_from_control(const ControlFile& c) {
    check(c.required_int("NPT1")==1,"only one constant point source supported");
    // Selected original-compatible case: IPTU=8 is Bq/s. No implicit
    // conversion from g/s, kg/h, or another IPTU mode is permitted.
    check(c.required_int("IPTU")==8,"selected point-source emission units must be IPTU=8 (Bq/s)");
    const auto x=c.required_float_list("X");
    const int species=c.required_int("NSPEC");
    check(species>0&&species<=64&&x.size()==std::size_t(8+species),
          "source X needs 8 geometric parameters + NSPEC mass rates");
    check(x[2]>=0&&x[3]>=0&&x[4]>0&&x[5]>=0&&x[6]>0&&x[7]==0,
          "unsupported geometry or building downwash");
    PointRelease s;
    // The original Fortran control reader stores the source X/Y as REAL*4.
    // Keep that input-rounding boundary, even though the isolated P7C wind
    // replay uses absolute UTM metres rather than vendor-relative grid units.
    // Vendor-relative XPT1GRD/YPT1GRD assembly still needs its own oracle gate.
    s.x_m=static_cast<double>(static_cast<float>(x[0]))*1000.0;
    s.y_m=static_cast<double>(static_cast<float>(x[1]))*1000.0;
    s.z_m=x[2]+x[3];
    s.rate_per_s.assign(x.begin()+8,x.end());
    for(double r:s.rate_per_s) check(finite(r)&&r>=0,"nonfinite source rate");
    return s;
}

PointRelease point_source_from_original_met_grid(
    const ControlFile& control, const OriginalMetGridFrame& met) {
    auto source = point_source_from_control(control);
    const auto x = control.required_float_list("X");
    const auto control_x_origin_km = control.required_float_list("XORIGKM");
    const auto control_y_origin_km = control.required_float_list("YORIGKM");
    if (control_x_origin_km.size() != 1U || control_y_origin_km.size() != 1U) {
        throw std::invalid_argument("P7 original source needs scalar XORIGKM/YORIGKM");
    }
    // Preserve each separately rounded original input, including the
    // CALMET metre -> kilometre REAL*4 multiply and the REAL*4 local offset.
    // Absolute QA coordinates are not the internal XPT1GRD/YPT1GRD fields.
    const auto qa = original_point_qa_xy(
        met, static_cast<float>(x[0]), static_cast<float>(x[1]),
        static_cast<float>(control_x_origin_km[0]),
        static_cast<float>(control_y_origin_km[0]));
    source.x_m = static_cast<double>(qa.x_km) * 1000.0;
    source.y_m = static_cast<double>(qa.y_km) * 1000.0;
    return source;
}
} // namespace cteas::puff
