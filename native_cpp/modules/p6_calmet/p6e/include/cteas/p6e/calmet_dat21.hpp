#pragma once
// CALMET v6.5.0 CALMET.DAT 2.1 output contract for the P6E micrometeorology
// chain.
//
// Layout facts are taken from the unmodified original sources
// (calmet.for OUTHD L12327-12516, OUTHR L13067-13237, WRTR1D/WRTR2D/WRTI2D
// L36734-36830) and verified byte-for-byte against the frozen real reference
// case project/cases/hefei5km_2022_reference_case_20261011/run/met/met.dat
// (143 intervals, NX=NY=50, NZ=9, IWFCOD=1, LCALGRD=T, NSSTA=1, NUSTA=1,
// NPSTA=0). This is an independent P6E-side implementation: it shares no
// code and no headers with the P7 CALMET.DAT reader.
//
// Fortran sequential unformatted framing: every record is
//   int32 length (little endian) + payload + int32 length.
//
//   #1        dataset  char*16 | version char*16 | model char*64  (96 B)
//   #2        NCOM int32                                          (4 B)
//   #3..      NCOM comment records of 132 bytes
//   #NCOM+3   controls record                                    (176 B)
//   #NCOM+4   ZFACE      (NZ+1 reals)
//   then      XSSTA/YSSTA (NSSTA reals each, if NSSTA>=1)
//             XUSTA/YUSTA (NUSTA reals each, if NUSTA>=1)
//             XPSTA/YPSTA (NPSTA reals each, if NPSTA>=1)
//             Z0, ILANDU, ELEV, XLAI (NX*NY words each)
//             NEARS (NX*NY words, if NSSTA>=1)
//   then per hour, in the OUTHR order for IRTYPE=1/IWFCOD=1:
//             U-LEV1..NZ, V-LEV1..NZ, [WFACE1..NZ if LCALGRD],
//             [T-LEV1..NZ if LCALGRD], IPGT, USTAR, ZI, EL, WSTAR,
//             [RMM if NPSTA!=0], TEMPK, RHO, QSW, IRH,
//             [IPCODE if NPSTA!=0]
//
// Every field record is 24 bytes of header (8-byte label, packed begin date
// YYYYJJJHH, begin seconds, packed end date, end seconds) followed by
// NX*NY words, i.e. 24 + 4*NX*NY bytes. Static records use the same header
// shape with four zero time words. The hourly interval must be exactly
// 3600 seconds; the original writes the end clock as the same packed hour
// with seconds advanced to 3600.
//
// Missing meteorological values are the original XMISS sentinel 9999. for
// real fields and 9999 for integer fields. Fields that the original does not
// write at all (ZICONV, DPTT, QH) are internal state and MUST NOT appear as
// file fields; write_calmet_dat21 rejects them.
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace cteas::p6e {
inline constexpr std::size_t calmet21_marker_bytes=4;
inline constexpr std::size_t calmet21_field_header_bytes=24;
inline constexpr std::size_t calmet21_controls_bytes=176;
inline constexpr std::size_t calmet21_controls_tail_bytes=60;
inline constexpr std::size_t calmet21_comment_bytes=132;
inline constexpr float calmet21_missing=9999.f;
inline constexpr std::int32_t calmet21_missing_int=9999;

struct CalmetDat21Time {
    int year=0,julian_day=0,hour=0,seconds=0;
};
inline std::int32_t calmet21_pack(const CalmetDat21Time& t) {
    return static_cast<std::int32_t>(t.year*100000+t.julian_day*100+t.hour);
}
inline bool calmet21_leap(int year) {
    return year%4==0&&(year%100!=0||year%400==0);
}
inline int calmet21_days_in_year(int year) {
    return calmet21_leap(year)?366:365;
}
inline std::int64_t calmet21_days_from_civil(int y,unsigned m,unsigned d) {
    y-=m<=2;
    const std::int64_t era=(y>=0?y:y-399)/400;
    const auto yoe=static_cast<unsigned>(y-static_cast<int>(era*400));
    const unsigned doy=(153*(m+(m>2?-3:9))+2)/5+d-1;
    const unsigned doe=yoe*365+yoe/4-yoe/100+doy;
    return era*146097+static_cast<std::int64_t>(doe)-719468;
}
inline std::int64_t calmet21_instant_seconds(const CalmetDat21Time& t) {
    return (calmet21_days_from_civil(t.year,1U,1U)+static_cast<std::int64_t>(t.julian_day-1))*86400+
           static_cast<std::int64_t>(t.hour)*3600+t.seconds;
}
inline CalmetDat21Time calmet21_next_hour(CalmetDat21Time t) {
    if(++t.hour==24) {
        t.hour=0;
        if(++t.julian_day>calmet21_days_in_year(t.year)) {
            t.julian_day=1;
            ++t.year;
        }
    }
    return t;
}

struct CalmetDat21Header {
    std::string dataset="CALMET.DAT";
    std::string version="2.1";
    std::string model="No-Obs file structure with embedded control file";
    std::vector<std::string> comments;
    // Run clock words IBYRN..IESECN of the controls record (explicit begin and
    // end dates/month/day/hour/second). Preserved so a real file round-trips
    // byte-exactly.
    int begin_year=0,begin_month=0,begin_day=0,begin_hour=0,begin_second=0;
    int end_year=0,end_month=0,end_day=0,end_hour=0,end_second=0;
    std::string timezone="UTC+0000";
    int irtype=1,iwfcod=1;
    int nx=0,ny=0,nz=0;
    float dgrid_m=0.f,xorigin_m=0.f,yorigin_m=0.f;
    int nssta=0,nusta=0,npsta=0,nowsta=0,nlu=0,iwat1=50,iwat2=60;
    bool lcalgrd=true;
    int run_hours=0;
    // Bytes 116..175 of the controls record (PMAP/DATUM/DATEN/FEAST/FNORTH/
    // UTMHEM/IUTMZN/RNLAT0/RELON0/XLAT1/XLAT2), preserved verbatim so a real
    // file round-trips byte-exactly.
    std::string controls_tail;
};
struct CalmetDat21Static {
    std::vector<float> zface_m;
    std::vector<float> surface_x_m,surface_y_m;
    std::vector<float> upper_x_m,upper_y_m;
    std::vector<float> precip_x_m,precip_y_m;
    std::vector<float> z0_m,elev_m,xlai;
    std::vector<std::int32_t> ilandu,nears;
};
struct CalmetDat21Field {
    std::string label;
    CalmetDat21Time begin,end;
    bool integer=false;
    std::vector<float> real_values;
    std::vector<std::int32_t> integer_values;
};
struct CalmetDat21Dataset {
    CalmetDat21Header header;
    CalmetDat21Static statics;
    std::vector<CalmetDat21Field> hourly;
    std::size_t intervals=0,fields_per_hour=0;
};

// Exact OUTHR label sequence for the selected mode. OUTHR writes U, V and W
// inside one loop over levels, so the wind labels interleave per level
// (U-LEV n, V-LEV n, WFACE n), which the frozen real reference case confirms.
inline std::vector<std::string> calmet21_hourly_labels(int nz,int irtype,
                                                       bool lcalgrd,int npsta) {
    if(nz<1||nz>999)throw std::invalid_argument("CALMET.DAT 2.1 invalid NZ");
    if(irtype!=0&&irtype!=1)throw std::invalid_argument("CALMET.DAT 2.1 invalid IRTYPE");
    auto index3=[](int z) {
        const std::string digits=std::to_string(z);
        return std::string(3-digits.size(),' ')+digits;
    };
    std::vector<std::string> labels;
    for(int z=1;z<=nz;++z) {
        labels.emplace_back("U-LEV"+index3(z));
        labels.emplace_back("V-LEV"+index3(z));
        if(lcalgrd)labels.emplace_back("WFACE"+index3(z));
    }
    if(lcalgrd&&irtype!=0)for(int z=1;z<=nz;++z)labels.emplace_back("T-LEV"+index3(z));
    if(irtype==0)return labels;
    labels.emplace_back("IPGT");
    labels.emplace_back("USTAR");
    labels.emplace_back("ZI");
    labels.emplace_back("EL");
    labels.emplace_back("WSTAR");
    if(npsta!=0)labels.emplace_back("RMM");
    labels.emplace_back("TEMPK");
    labels.emplace_back("RHO");
    labels.emplace_back("QSW");
    labels.emplace_back("IRH");
    if(npsta!=0)labels.emplace_back("IPCODE");
    return labels;
}

enum class CalmetDat21Unit { metre,metre_per_second,kelvin,
                             kilogram_per_cubic_metre,watt_per_square_metre,
                             percent,stability_code,precipitation_code };
enum class CalmetDat21Owner { p6e,p6d,case_input };
struct CalmetDat21Binding {
    std::string label;
    CalmetDat21Unit unit;
    CalmetDat21Owner owner;
    bool quantized_integer;
    std::string source;
};
// Which implemented P6E kernel feeds which file field.
inline std::vector<CalmetDat21Binding> calmet21_field_bindings() {
    return {
        {"USTAR",CalmetDat21Unit::metre_per_second,CalmetDat21Owner::p6e,false,
         "P6E E5/E8 ELUSTR friction velocity"},
        {"ZI",CalmetDat21Unit::metre,CalmetDat21Owner::p6e,false,
         "P6E E7/E13/E20 MIXHT mixing height (max of convective and mechanical)"},
        {"EL",CalmetDat21Unit::metre,CalmetDat21Owner::p6e,false,
         "P6E E5/E8 ELUSTR Monin-Obukhov length"},
        {"WSTAR",CalmetDat21Unit::metre_per_second,CalmetDat21Owner::p6e,false,
         "P6E E6 WSTARR convective velocity scale"},
        {"TEMPK",CalmetDat21Unit::kelvin,CalmetDat21Owner::p6e,false,
         "P6E E3/E10 SURFVAR 2-D surface temperature"},
        {"RHO",CalmetDat21Unit::kilogram_per_cubic_metre,CalmetDat21Owner::p6e,false,
         "P6E air density input consumed by MIXHT/WSTARR"},
        {"QSW",CalmetDat21Unit::watt_per_square_metre,CalmetDat21Owner::p6e,false,
         "P6E E4 HEATFX short-wave radiation"},
        {"IRH",CalmetDat21Unit::percent,CalmetDat21Owner::p6e,true,
         "P6E E3/E10 SURFVAR surface relative humidity (integer percent)"},
        {"IPGT",CalmetDat21Unit::stability_code,CalmetDat21Owner::p6e,true,
         "P6E E2 PGTSTB stability class (integer)"},
        {"T-LEV",CalmetDat21Unit::kelvin,CalmetDat21Owner::p6e,false,
         "P6E E14 TEMP3D 3-D temperature, layer 1 equals TEMPK exactly"},
        {"U-LEV",CalmetDat21Unit::metre_per_second,CalmetDat21Owner::p6d,false,
         "P6D diagnostic wind field"},
        {"V-LEV",CalmetDat21Unit::metre_per_second,CalmetDat21Owner::p6d,false,
         "P6D diagnostic wind field"},
        {"WFACE",CalmetDat21Unit::metre_per_second,CalmetDat21Owner::p6d,false,
         "P6D vertical wind at the cell top face"},
        {"RMM",CalmetDat21Unit::watt_per_square_metre,CalmetDat21Owner::case_input,false,
         "precipitation rate, written only when NPSTA!=0 (not written for the real case)"},
        {"IPCODE",CalmetDat21Unit::precipitation_code,CalmetDat21Owner::case_input,true,
         "precipitation code, written only when NPSTA!=0 (not written for the real case)"},
    };
}
// Internal state with NO CALMET.DAT representation; write_calmet_dat21
// rejects these labels instead of inventing a field.
inline std::vector<std::string> calmet21_internal_only_fields() {
    return {"ZICONV","DPTT","QH","USTAROLD"};
}
inline std::string calmet21_default_controls_tail() {
    std::string tail;
    const auto push=[&tail](const std::string& s,std::size_t width) {
        std::string v=s;
        v.resize(width,' ');
        tail+=v;
    };
    push("UTDM",8U);
    push("WGS-84",8U);
    push("02-21-2003",12U);
    for(int k=0;k<6;++k)tail.append(4,'\0'); // FEAST/FNORTH/UTMHEM/IUTMZN/RNLAT0...
    tail.resize(calmet21_controls_tail_bytes,'\0');
    return tail;
}

namespace detail {
inline void put_u32(std::vector<std::uint8_t>& out,std::uint32_t v) {
    out.push_back(static_cast<std::uint8_t>(v&0xffU));
    out.push_back(static_cast<std::uint8_t>((v>>8U)&0xffU));
    out.push_back(static_cast<std::uint8_t>((v>>16U)&0xffU));
    out.push_back(static_cast<std::uint8_t>((v>>24U)&0xffU));
}
inline void put_i32(std::vector<std::uint8_t>& out,std::int32_t v) {
    std::uint32_t bits=0;
    static_assert(sizeof(bits)==sizeof(v));
    std::memcpy(&bits,&v,sizeof(bits));
    put_u32(out,bits);
}
inline void put_f32(std::vector<std::uint8_t>& out,float v) {
    std::uint32_t bits=0;
    static_assert(sizeof(bits)==sizeof(v));
    std::memcpy(&bits,&v,sizeof(bits));
    put_u32(out,bits);
}
inline void put_ascii(std::vector<std::uint8_t>& out,const std::string& s,
                      std::size_t width) {
    if(s.size()>width)throw std::invalid_argument("CALMET.DAT 2.1 ASCII too long: "+s);
    for(std::size_t k=0;k<s.size();++k)
        out.push_back(static_cast<std::uint8_t>(s[k]));
    out.insert(out.end(),width-s.size(),static_cast<std::uint8_t>(' '));
}
inline void put_record(std::vector<std::uint8_t>& out,
                       const std::vector<std::uint8_t>& payload) {
    put_u32(out,static_cast<std::uint32_t>(payload.size()));
    out.insert(out.end(),payload.begin(),payload.end());
    put_u32(out,static_cast<std::uint32_t>(payload.size()));
}
inline std::uint32_t read_u32(const std::vector<std::uint8_t>& v,std::size_t p) {
    if(p>v.size()||v.size()-p<4U)
        throw std::invalid_argument("CALMET.DAT 2.1 short 4-byte word");
    return std::uint32_t(v[p])|(std::uint32_t(v[p+1])<<8U)|
           (std::uint32_t(v[p+2])<<16U)|(std::uint32_t(v[p+3])<<24U);
}
inline std::int32_t read_i32(const std::vector<std::uint8_t>& v,std::size_t p) {
    const std::uint32_t bits=read_u32(v,p);
    std::int32_t out=0;
    static_assert(sizeof(bits)==sizeof(out));
    std::memcpy(&out,&bits,sizeof(out));
    return out;
}
inline float read_f32(const std::vector<std::uint8_t>& v,std::size_t p) {
    const std::uint32_t bits=read_u32(v,p);
    float out=0.f;
    static_assert(sizeof(bits)==sizeof(out));
    std::memcpy(&out,&bits,sizeof(out));
    return out;
}
inline std::string read_ascii(const std::vector<std::uint8_t>& v,std::size_t p,
                              std::size_t width) {
    if(p>v.size()||width>v.size()-p)
        throw std::invalid_argument("CALMET.DAT 2.1 truncated ASCII field");
    std::string out;
    for(std::size_t k=p;k<p+width;++k)
        out.push_back(static_cast<char>(v[k]));
    return out;
}
inline std::string trim(const std::string& s) {
    const auto first=s.find_first_not_of(' ');
    if(first==std::string::npos)return std::string();
    const auto last=s.find_last_not_of(' ');
    return s.substr(first,last-first+1U);
}
} // namespace detail

// Serialise a complete CALMET.DAT 2.1 file. All structural, ordering, unit
// extents, time-label and missing-value violations fail closed.
inline void write_calmet_dat21(const std::string& path,
                               const CalmetDat21Header& h,
                               const CalmetDat21Static& s,
                               const std::vector<CalmetDat21Field>& hourly) {
    const auto require=[&](bool ok,const std::string& message) {
        if(!ok)throw std::invalid_argument(std::string("CALMET.DAT 2.1 ")+message);
    };
    require(h.irtype==1,"only IRTYPE=1 carries the micrometeorological fields");
    require(h.iwfcod==1,"only IWFCOD=1 (u, v and w) is a valid selected mode");
    require(h.nx>0&&h.ny>0&&h.nz>0,"invalid grid extent");
    require(h.dgrid_m>0.f&&std::isfinite(h.dgrid_m),"invalid DGRID");
    require(std::isfinite(h.xorigin_m)&&std::isfinite(h.yorigin_m),"invalid origin");
    require(h.timezone.size()==8U,"AXTZ must be exactly 8 characters");
    require(h.nssta>=0&&h.nusta>=0&&h.npsta>=0,"negative station count");
    require(h.iwat1<=h.iwat2,"invalid water land-use range");
    require(h.controls_tail.empty()||h.controls_tail.size()==calmet21_controls_tail_bytes,
            "controls tail must be empty or 60 bytes");
    const auto labels=calmet21_hourly_labels(h.nz,h.irtype,h.lcalgrd,h.npsta);
    const auto cells=static_cast<std::size_t>(h.nx)*static_cast<std::size_t>(h.ny);
    require(s.zface_m.size()==static_cast<std::size_t>(h.nz)+1U,"ZFACE must have NZ+1 faces");
    for(std::size_t k=0;k<s.zface_m.size();++k) {
        require(std::isfinite(s.zface_m[k]),"nonfinite ZFACE");
        require(k==0U||s.zface_m[k]>s.zface_m[k-1U],"ZFACE must increase with height");
    }
    require(static_cast<int>(s.surface_x_m.size())==h.nssta&&
            static_cast<int>(s.surface_y_m.size())==h.nssta,"surface station extents");
    require(static_cast<int>(s.upper_x_m.size())==h.nusta&&
            static_cast<int>(s.upper_y_m.size())==h.nusta,"upper station extents");
    require(static_cast<int>(s.precip_x_m.size())==h.npsta&&
            static_cast<int>(s.precip_y_m.size())==h.npsta,"precipitation station extents");
    require(s.z0_m.size()==cells&&s.elev_m.size()==cells&&s.xlai.size()==cells&&
            s.ilandu.size()==cells,"grid field extents");
    require(h.nssta<1||s.nears.size()==cells,"NEARS extents");
    if(!hourly.empty()) {
        require(hourly.size()%labels.size()==0U,"incomplete hourly field group");
        const std::size_t hours=hourly.size()/labels.size();
        require(h.run_hours==0||static_cast<std::size_t>(h.run_hours)==hours,
                "IRLG does not match the number of hourly intervals");
        for(std::size_t n=0;n<hours;++n) {
            const auto& first=hourly[n*labels.size()];
            const auto interval=calmet21_instant_seconds(first.end)-
                                calmet21_instant_seconds(first.begin);
            require(interval==3600,"hourly interval must be exactly 3600 s");
            require(calmet21_pack(first.end)==calmet21_pack(first.begin)&&
                    first.end.seconds==first.begin.seconds+3600,
                    "original hourly end clock must keep the packed begin hour");
            if(n>0U) {
                const auto& previous=hourly[(n-1U)*labels.size()];
                require(calmet21_instant_seconds(first.begin)==
                        calmet21_instant_seconds(previous.end),
                        "hourly intervals must be contiguous");
            }
            for(std::size_t j=0;j<labels.size();++j) {
                const auto& f=hourly[n*labels.size()+j];
                require(f.label==labels[j],"hourly field order/label mismatch");
                require(f.begin.year==first.begin.year&&
                        f.begin.julian_day==first.begin.julian_day&&
                        f.begin.hour==first.begin.hour&&
                        f.begin.seconds==first.begin.seconds&&
                        f.end.seconds==first.end.seconds,
                        "fields in the same hour must share one time tag");
                const bool integral=f.label=="IPGT"||f.label=="IRH";
                require(f.integer==integral,"integer/real classification mismatch");
                if(f.integer) {
                    require(f.integer_values.size()==cells,"integer field extent");
                    require(f.real_values.empty(),"integer field carries real values");
                } else {
                    require(f.real_values.size()==cells,"real field extent");
                    require(f.integer_values.empty(),"real field carries integer values");
                    for(const float v:f.real_values)
                        require(std::isfinite(v),"nonfinite real field value");
                }
            }
        }
    }
    for(const auto& f:hourly) {
        bool known=false;
        for(const auto& label:labels)known=known||(f.label==label);
        require(known,"field label is not part of the selected CALMET.DAT layout");
    }
    std::vector<std::uint8_t> out;
    std::vector<std::uint8_t> payload;
    detail::put_ascii(payload,h.dataset,16U);
    detail::put_ascii(payload,h.version,16U);
    detail::put_ascii(payload,h.model,64U);
    detail::put_record(out,payload);
    payload.clear();
    detail::put_i32(payload,static_cast<std::int32_t>(h.comments.size()));
    detail::put_record(out,payload);
    for(const auto& comment:h.comments) {
        payload.clear();
        detail::put_ascii(payload,comment,calmet21_comment_bytes);
        detail::put_record(out,payload);
    }
    payload.clear();
    detail::put_i32(payload,h.begin_year);
    detail::put_i32(payload,h.begin_month);
    detail::put_i32(payload,h.begin_day);
    detail::put_i32(payload,h.begin_hour);
    detail::put_i32(payload,h.begin_second);
    detail::put_i32(payload,h.end_year);
    detail::put_i32(payload,h.end_month);
    detail::put_i32(payload,h.end_day);
    detail::put_i32(payload,h.end_hour);
    detail::put_i32(payload,h.end_second);
    detail::put_ascii(payload,h.timezone,8U);       // AXTZ
    detail::put_i32(payload,h.run_hours);           // IRLG
    detail::put_i32(payload,h.irtype);
    detail::put_i32(payload,h.nx);
    detail::put_i32(payload,h.ny);
    detail::put_i32(payload,h.nz);
    detail::put_f32(payload,h.dgrid_m);
    detail::put_f32(payload,h.xorigin_m);
    detail::put_f32(payload,h.yorigin_m);
    detail::put_i32(payload,h.iwfcod);
    detail::put_i32(payload,h.nssta);
    detail::put_i32(payload,h.nusta);
    detail::put_i32(payload,h.npsta);
    detail::put_i32(payload,h.nowsta);
    detail::put_i32(payload,h.nlu);
    detail::put_i32(payload,h.iwat1);
    detail::put_i32(payload,h.iwat2);
    detail::put_i32(payload,h.lcalgrd?1:0);         // LCALGRD logical*4
    const std::string tail=h.controls_tail.empty()?calmet21_default_controls_tail()
                                                  :h.controls_tail;
    payload.insert(payload.end(),tail.begin(),tail.end());
    require(payload.size()==calmet21_controls_bytes,"controls record size drift");
    detail::put_record(out,payload);
    const auto write_static=[&](const char* label,
                                const std::vector<float>& values) {
        payload.clear();
        detail::put_ascii(payload,label,8U);
        for(int k=0;k<4;++k)detail::put_i32(payload,0);
        for(const float v:values)detail::put_f32(payload,v);
        detail::put_record(out,payload);
    };
    const auto write_static_int=[&](const char* label,
                                    const std::vector<std::int32_t>& values) {
        payload.clear();
        detail::put_ascii(payload,label,8U);
        for(int k=0;k<4;++k)detail::put_i32(payload,0);
        for(const std::int32_t v:values)detail::put_i32(payload,v);
        detail::put_record(out,payload);
    };
    write_static("ZFACE",s.zface_m);
    if(h.nssta>=1) {
        write_static("XSSTA",s.surface_x_m);
        write_static("YSSTA",s.surface_y_m);
    }
    if(h.nusta>=1) {
        write_static("XUSTA",s.upper_x_m);
        write_static("YUSTA",s.upper_y_m);
    }
    if(h.npsta>=1) {
        write_static("XPSTA",s.precip_x_m);
        write_static("YPSTA",s.precip_y_m);
    }
    write_static("Z0",s.z0_m);
    write_static_int("ILANDU",s.ilandu);
    write_static("ELEV",s.elev_m);
    write_static("XLAI",s.xlai);
    if(h.nssta>=1)write_static_int("NEARS",s.nears);
    for(const auto& f:hourly) {
        payload.clear();
        detail::put_ascii(payload,f.label,8U);
        detail::put_i32(payload,calmet21_pack(f.begin));
        detail::put_i32(payload,f.begin.seconds);
        detail::put_i32(payload,calmet21_pack(f.end));
        detail::put_i32(payload,f.end.seconds);
        if(f.integer)
            for(const std::int32_t v:f.integer_values)detail::put_i32(payload,v);
        else
            for(const float v:f.real_values)detail::put_f32(payload,v);
        detail::put_record(out,payload);
    }
    std::ofstream file(path,std::ios::binary|std::ios::trunc);
    if(!file)throw std::invalid_argument("CALMET.DAT 2.1 cannot open output "+path);
    file.write(reinterpret_cast<const char*>(out.data()),
               static_cast<std::streamsize>(out.size()));
    if(!file)throw std::invalid_argument("CALMET.DAT 2.1 short write to "+path);
}

// Parse a CALMET.DAT 2.1 file, validating every layout rule above.
inline CalmetDat21Dataset read_calmet_dat21(const std::string& path) {
    std::ifstream file(path,std::ios::binary);
    if(!file)throw std::invalid_argument("CALMET.DAT 2.1 cannot open "+path);
    const std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(file)),
                                          std::istreambuf_iterator<char>());
    const auto require=[&](bool ok,const std::string& message) {
        if(!ok)throw std::invalid_argument(std::string("CALMET.DAT 2.1 ")+message);
    };
    std::size_t cursor=0;
    const auto next=[&](std::vector<std::uint8_t>& payload) {
        if(cursor+2U*calmet21_marker_bytes>bytes.size())return false;
        const auto length=detail::read_u32(bytes,cursor);
        const std::size_t start=cursor+calmet21_marker_bytes;
        if(start+length+calmet21_marker_bytes>bytes.size())return false;
        const auto trailer=detail::read_u32(bytes,start+length);
        if(trailer!=length)throw std::invalid_argument(
            "CALMET.DAT 2.1 record length marker mismatch");
        payload.assign(bytes.begin()+static_cast<std::ptrdiff_t>(start),
                       bytes.begin()+static_cast<std::ptrdiff_t>(start+length));
        cursor=start+length+calmet21_marker_bytes;
        return true;
    };
    CalmetDat21Dataset dataset;
    std::vector<std::uint8_t> payload;
    require(next(payload),"missing file declaration record");
    require(payload.size()==96U,"file declaration must be 96 bytes");
    auto& h=dataset.header;
    h.dataset=detail::read_ascii(payload,0U,16U);
    h.version=detail::read_ascii(payload,16U,16U);
    h.model=detail::read_ascii(payload,32U,64U);
    require(detail::trim(h.dataset)=="CALMET.DAT"&&detail::trim(h.version)=="2.1",
            "unsupported signature/version");
    require(next(payload)&&payload.size()==4U,"missing comment count");
    const auto ncom=detail::read_i32(payload,0U);
    require(ncom>=0&&ncom<=100000,"invalid comment count");
    h.comments.reserve(static_cast<std::size_t>(ncom));
    for(int n=0;n<ncom;++n) {
        require(next(payload)&&payload.size()==calmet21_comment_bytes,
                "malformed comment record");
        h.comments.push_back(detail::read_ascii(payload,0U,calmet21_comment_bytes));
    }
    require(next(payload)&&payload.size()==calmet21_controls_bytes,
            "controls record must be 176 bytes");
    h.begin_year=detail::read_i32(payload,0U);
    h.begin_month=detail::read_i32(payload,4U);
    h.begin_day=detail::read_i32(payload,8U);
    h.begin_hour=detail::read_i32(payload,12U);
    h.begin_second=detail::read_i32(payload,16U);
    h.end_year=detail::read_i32(payload,20U);
    h.end_month=detail::read_i32(payload,24U);
    h.end_day=detail::read_i32(payload,28U);
    h.end_hour=detail::read_i32(payload,32U);
    h.end_second=detail::read_i32(payload,36U);
    h.timezone=detail::read_ascii(payload,40U,8U);
    h.run_hours=detail::read_i32(payload,48U);
    h.irtype=detail::read_i32(payload,52U);
    h.nx=detail::read_i32(payload,56U);
    h.ny=detail::read_i32(payload,60U);
    h.nz=detail::read_i32(payload,64U);
    h.dgrid_m=detail::read_f32(payload,68U);
    h.xorigin_m=detail::read_f32(payload,72U);
    h.yorigin_m=detail::read_f32(payload,76U);
    h.iwfcod=detail::read_i32(payload,80U);
    h.nssta=detail::read_i32(payload,84U);
    h.nusta=detail::read_i32(payload,88U);
    h.npsta=detail::read_i32(payload,92U);
    h.nowsta=detail::read_i32(payload,96U);
    h.nlu=detail::read_i32(payload,100U);
    h.iwat1=detail::read_i32(payload,104U);
    h.iwat2=detail::read_i32(payload,108U);
    h.lcalgrd=detail::read_i32(payload,112U)!=0;
    h.controls_tail=detail::read_ascii(payload,116U,calmet21_controls_tail_bytes);
    require(h.irtype==1&&h.iwfcod==1,"only IRTYPE=1 and IWFCOD=1 are supported");
    require(h.nx>0&&h.ny>0&&h.nz>0&&h.nx<=4096&&h.ny<=4096&&h.nz<=999,
            "invalid grid extent");
    require(std::isfinite(h.dgrid_m)&&h.dgrid_m>0.f,"invalid DGRID");
    require(h.nssta>=0&&h.nusta>=0&&h.npsta>=0,"negative station count");
    require(h.iwat1<=h.iwat2,"invalid water land-use range");
    const auto cells=static_cast<std::size_t>(h.nx)*static_cast<std::size_t>(h.ny);
    auto& s=dataset.statics;
    const auto read_static=[&](const char* expected,std::size_t count,
                              std::vector<float>* real_values,
                              std::vector<std::int32_t>* int_values) {
        require(next(payload),"missing static record");
        const std::string label=detail::trim(detail::read_ascii(payload,0U,8U));
        require(label==expected,"static record label mismatch: "+label);
        for(int k=0;k<4;++k)
            require(detail::read_i32(payload,8U+static_cast<std::size_t>(k)*4U)==0,
                    "static record must carry a zero clock");
        require(payload.size()==calmet21_field_header_bytes+4U*count,
                "static record size drift for "+label);
        if(real_values) {
            real_values->reserve(count);
            for(std::size_t k=0;k<count;++k) {
                const float v=detail::read_f32(payload,calmet21_field_header_bytes+4U*k);
                require(std::isfinite(v),"nonfinite static value in "+label);
                real_values->push_back(v);
            }
        }
        if(int_values) {
            int_values->reserve(count);
            for(std::size_t k=0;k<count;++k)
                int_values->push_back(
                    detail::read_i32(payload,calmet21_field_header_bytes+4U*k));
        }
    };
    read_static("ZFACE",static_cast<std::size_t>(h.nz)+1U,&s.zface_m,nullptr);
    if(h.nssta>=1) {
        read_static("XSSTA",static_cast<std::size_t>(h.nssta),&s.surface_x_m,nullptr);
        read_static("YSSTA",static_cast<std::size_t>(h.nssta),&s.surface_y_m,nullptr);
    }
    if(h.nusta>=1) {
        read_static("XUSTA",static_cast<std::size_t>(h.nusta),&s.upper_x_m,nullptr);
        read_static("YUSTA",static_cast<std::size_t>(h.nusta),&s.upper_y_m,nullptr);
    }
    if(h.npsta>=1) {
        read_static("XPSTA",static_cast<std::size_t>(h.npsta),&s.precip_x_m,nullptr);
        read_static("YPSTA",static_cast<std::size_t>(h.npsta),&s.precip_y_m,nullptr);
    }
    read_static("Z0",cells,&s.z0_m,nullptr);
    read_static("ILANDU",cells,nullptr,&s.ilandu);
    read_static("ELEV",cells,&s.elev_m,nullptr);
    read_static("XLAI",cells,&s.xlai,nullptr);
    if(h.nssta>=1)read_static("NEARS",cells,nullptr,&s.nears);
    const auto labels=calmet21_hourly_labels(h.nz,h.irtype,h.lcalgrd,h.npsta);
    dataset.fields_per_hour=labels.size();
    CalmetDat21Time hour_begin,hour_end;
    std::int64_t previous_end=-1;
    while(next(payload)) {
        require(payload.size()==calmet21_field_header_bytes+4U*cells,
                "unexpected hourly record size");
        CalmetDat21Field field;
        field.label=detail::trim(detail::read_ascii(payload,0U,8U));
        const std::size_t index=dataset.hourly.size()%labels.size();
        require(field.label==labels[index],
                "hourly field order mismatch: expected "+labels[index]+
                " but found "+field.label);
        field.begin.year=detail::read_i32(payload,8U)/100000;
        field.begin.julian_day=(detail::read_i32(payload,8U)%100000)/100;
        field.begin.hour=detail::read_i32(payload,8U)%100;
        field.begin.seconds=detail::read_i32(payload,12U);
        field.end.year=detail::read_i32(payload,16U)/100000;
        field.end.julian_day=(detail::read_i32(payload,16U)%100000)/100;
        field.end.hour=detail::read_i32(payload,16U)%100;
        field.end.seconds=detail::read_i32(payload,20U);
        require(calmet21_instant_seconds(field.end)-
                calmet21_instant_seconds(field.begin)==3600,
                "hourly interval must be exactly 3600 s");
        require(calmet21_pack(field.end)==calmet21_pack(field.begin)&&
                field.end.seconds==field.begin.seconds+3600,
                "original hourly end clock must keep the packed begin hour");
        if(index==0U) {
            if(previous_end>=0)
                require(calmet21_instant_seconds(field.begin)==previous_end,
                        "hourly intervals must be contiguous");
            hour_begin=field.begin;
            hour_end=field.end;
            ++dataset.intervals;
        } else {
            require(calmet21_pack(field.begin)==calmet21_pack(hour_begin)&&
                    field.begin.seconds==hour_begin.seconds&&
                    calmet21_pack(field.end)==calmet21_pack(hour_end)&&
                    field.end.seconds==hour_end.seconds,
                    "fields in the same hour must share one time tag");
        }
        field.integer=field.label=="IPGT"||field.label=="IRH";
        if(field.integer) {
            field.integer_values.reserve(cells);
            for(std::size_t k=0;k<cells;++k)
                field.integer_values.push_back(
                    detail::read_i32(payload,calmet21_field_header_bytes+4U*k));
        } else {
            field.real_values.reserve(cells);
            for(std::size_t k=0;k<cells;++k) {
                const float v=detail::read_f32(payload,
                                               calmet21_field_header_bytes+4U*k);
                require(std::isfinite(v),"nonfinite hourly value in "+field.label);
                field.real_values.push_back(v);
            }
        }
        dataset.hourly.push_back(std::move(field));
        if(index==labels.size()-1U)previous_end=calmet21_instant_seconds(hour_end);
    }
    require(dataset.intervals>0U&&dataset.hourly.size()==dataset.intervals*labels.size(),
            "incomplete hourly field group");
    require(h.run_hours==0||static_cast<std::size_t>(h.run_hours)==dataset.intervals,
            "IRLG does not match the number of hourly intervals");
    return dataset;
}
} // namespace cteas::p6e
