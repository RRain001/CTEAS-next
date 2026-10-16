#include "cteas/puff/original_met_hours.hpp"
#include <algorithm>
#include <bit>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <utility>

namespace cteas::puff {
namespace {
constexpr std::uint64_t offset=14695981039346656037ULL,prime=1099511628211ULL;
void check(bool ok,const char* why) {
    if(!ok) throw std::runtime_error(std::string("P7 original hourly MET: ")+why);
}
void words(std::uint64_t& hash,const auto& a,std::size_t first,std::size_t count) {
    check(first<=a.size() && count<=a.size()-first,"incomplete field extent");
    for(std::size_t i=first;i<first+count;++i) {
        const auto bits=std::bit_cast<std::uint32_t>(a[i]);
        for(unsigned n=0;n<4;++n) {hash ^= ((bits>>(8*n))&255U);hash*=prime;}
    }
}
void insert(std::vector<float>& destination,const Calmet21Field& src,
            std::size_t layer,std::size_t xy) {
    check(!src.integer && src.real_values.size()==xy,"wrong REAL*4 field");
    check(layer*xy<=destination.size() && xy<=destination.size()-layer*xy,
          "out-of-range 3D field layer");
    std::copy(src.real_values.begin(),src.real_values.end(),
              destination.begin()+static_cast<std::ptrdiff_t>(layer*xy));
}
void surface(std::vector<float>& destination,const Calmet21Field& src,std::size_t xy) {
    check(!src.integer && src.real_values.size()==xy,"wrong REAL*4 surface field");
    destination=src.real_values;
}
void integer(std::vector<std::int32_t>& destination,
             const Calmet21Field& src,std::size_t xy) {
    check(src.integer && src.integer_values.size()==xy,"wrong INTEGER*4 field");
    destination=src.integer_values;
}
void valid(const OriginalMetHour& h) {
    check(h.nx>0 && h.ny>0 && h.nz>0,"zero grid size");
    const auto xy=static_cast<std::size_t>(h.nx)*static_cast<std::size_t>(h.ny);
    const auto xyz=xy*static_cast<std::size_t>(h.nz);
    for(const auto* a:{&h.u,&h.v,&h.w,&h.t})
        check(a->size()==xyz,"incomplete 3D array");
    for(const auto* a:{&h.ustar,&h.zi,&h.el,&h.wstar,&h.tempk,&h.rho,&h.qsw})
        check(a->size()==xy,"incomplete 2D array");
    check(h.ipgt.size()==xy && h.irh.size()==xy,"incomplete integer arrays");
    check(h.end.unix_seconds-h.begin.unix_seconds==3600,"nonhourly time interval");
}
}
std::uint64_t OriginalMetHour::original_field_fingerprint() const {
    valid(*this);
    const auto xy=static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny);
    std::uint64_t h=offset;
    for(int z=0;z<nz;++z) {
        const auto pos=static_cast<std::size_t>(z)*xy;
        words(h,u,pos,xy);words(h,v,pos,xy);words(h,w,pos,xy);
    }
    for(int z=0;z<nz;++z) words(h,t,static_cast<std::size_t>(z)*xy,xy);
    words(h,ipgt,0,xy);
    for(const auto* p:{&ustar,&zi,&el,&wstar,&tempk,&rho,&qsw})words(h,*p,0,xy);
    words(h,irh,0,xy);
    return h;
}
Calmet21Summary OriginalMetHourlyReader::read(
    const std::string& path,const Observer& callback,bool frozen) {
    check(bool(callback),"missing hour callback");
    // Two-pass boundary is necessary until CALMET21 publishes its header
    // before field callbacks; first pass independently validates full file.
    const auto first=Calmet21Reader::read(path,{},frozen);
    const auto& h=first.header;
    const auto xy=static_cast<std::size_t>(h.nx)*static_cast<std::size_t>(h.ny);
    const auto xyz=xy*static_cast<std::size_t>(h.nz);
    const auto nfields=static_cast<std::size_t>(4*h.nz+9);
    OriginalMetHour hour;
    std::size_t cursor=0,done=0;
    std::int64_t previous_end=0;
    const auto second=Calmet21Reader::read(path,[&](const Calmet21Field& f) {
        if(cursor==0) {
            hour=OriginalMetHour{};
            hour.begin=f.begin;hour.end=f.end;
            hour.nx=h.nx;hour.ny=h.ny;hour.nz=h.nz;
            hour.u.resize(xyz);hour.v.resize(xyz);
            hour.w.resize(xyz);hour.t.resize(xyz);
            check(done==0 || f.begin.unix_seconds==previous_end,"hour gap");
        }
        check(f.begin.unix_seconds==hour.begin.unix_seconds &&
              f.end.unix_seconds==hour.end.unix_seconds,"mixed hour fields");
        if(cursor<static_cast<std::size_t>(3*h.nz)) {
            auto& target=cursor%3==0?hour.u:cursor%3==1?hour.v:hour.w;
            insert(target,f,cursor/3,xy);
        } else if(cursor<static_cast<std::size_t>(4*h.nz)) {
            insert(hour.t,f,cursor-static_cast<std::size_t>(3*h.nz),xy);
        } else {
            switch(cursor-static_cast<std::size_t>(4*h.nz)) {
                case 0:integer(hour.ipgt,f,xy);break;
                case 1:surface(hour.ustar,f,xy);break;
                case 2:surface(hour.zi,f,xy);break;
                case 3:surface(hour.el,f,xy);break;
                case 4:surface(hour.wstar,f,xy);break;
                case 5:surface(hour.tempk,f,xy);break;
                case 6:surface(hour.rho,f,xy);break;
                case 7:surface(hour.qsw,f,xy);break;
                case 8:integer(hour.irh,f,xy);break;
                default:throw std::logic_error("MET hour cursor overrun");
            }
        }
        if(++cursor==nfields) {
            valid(hour);
            callback(h,first.statics,hour);
            previous_end=hour.end.unix_seconds;
            ++done;cursor=0;
        }
    },frozen);
    check(cursor==0 && done==first.intervals &&
          second.intervals==first.intervals &&
          second.hourly_fields==first.hourly_fields &&
          second.header.nx==h.nx && second.header.ny==h.ny && second.header.nz==h.nz &&
          second.first_begin.unix_seconds==first.first_begin.unix_seconds &&
          second.final_end.unix_seconds==first.final_end.unix_seconds,
          "two-pass original MET source changed or incomplete");
    return first;
}
} // namespace cteas::puff
