// Selected Hefei CALMET 2.1 METADATA-ONLY input builder for native P6E.
// No original/reference CALMET.DAT file is opened, copied or accepted.
// The 143h hourly fields are missing sentinels; the P6E native-hour path
// must source 27 UVW and its own COMP physics from the native C++ producers.
#include "cteas/p6f/calmet_dat21_writer.hpp"
#include "cteas/p6/read_geo.hpp"
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using cteas::p6f::Calmet21File;
using cteas::p6f::Calmet21Time;
using cteas::p6f::Calmet21Field;
void need(bool condition,const std::string& reason) {
    if(!condition)throw std::runtime_error("P6E_SOURCE_METADATA_REJECTED: "+reason);
}
std::string read(const std::string& filename) {
    std::ifstream in(filename);
    need(static_cast<bool>(in),"cannot open primary source "+filename);
    std::ostringstream stream;stream<<in.rdbuf();
    need(!in.bad(),"cannot read primary source "+filename);
    return stream.str();
}
std::string control(const std::string& deck,const std::string& name) {
    const std::regex re("!\\s*"+name+"\\s*=\\s*([^!]*)!",
                        std::regex_constants::icase);
    std::smatch match;
    need(std::regex_search(deck,match,re),"missing original control "+name);
    const std::string value=match[1].str();
    const auto b=value.find_first_not_of(" \t\r\n");
    need(b!=std::string::npos,"empty control "+name);
    const auto e=value.find_last_not_of(" \t\r\n");
    return value.substr(b,e-b+1);
}
int as_int(const std::string& deck,const std::string& name) {
    const auto text=control(deck,name);
    std::size_t parsed=0;
    const int value=std::stoi(text,&parsed);
    need(parsed==text.size(),"invalid integer "+name);
    return value;
}
float as_float(const std::string& deck,const std::string& name) {
    const auto text=control(deck,name);
    std::size_t parsed=0;
    const float value=std::stof(text,&parsed);
    need(parsed==text.size()&&std::isfinite(value),"invalid REAL4 "+name);
    return value;
}
std::vector<float> zface(const std::string& deck) {
    std::string x=control(deck,"ZFACE");
    for(char& c:x)if(c==',')c=' ';
    std::istringstream in(x);
    std::vector<float> result;
    float value=0.f;
    while(in>>value)result.push_back(value);
    need(in.eof()&&!result.empty(),"malformed ZFACE");
    return result;
}
std::vector<float> station(const std::string& deck,const std::string& key) {
    const auto data=control(deck,key);
    const auto q=data.find('\'');
    need(q!=std::string::npos,"station name has no quote "+key);
    const auto q2=data.find('\'',q+1);
    need(q2!=std::string::npos,"station name quote not closed "+key);
    std::istringstream rest(data.substr(q2+1));
    std::string station_id;
    float east=0.f,north=0.f;
    rest>>station_id>>east>>north;
    need(!station_id.empty()&&std::isfinite(east)&&std::isfinite(north)&&
         east>0.f&&north>0.f,"bad source station XY "+key);
    return {east,north};
}
std::int64_t start_seconds(const cteas::p6f::Calmet21Header& h,bool end) {
    const int y=end?h.end_year:h.begin_year;
    const int m=end?h.end_month:h.begin_month;
    const int d=end?h.end_day:h.begin_day;
    const int hr=end?h.end_hour:h.begin_hour;
    const int sec=end?h.end_second:h.begin_second;
    need(y>=2000&&m>=1&&m<=12&&d>=1&&d<=31&&hr>=0&&hr<24&&sec==0,
         "selected-case run time invalid");
    return cteas::p6f::days_from_civil(y,static_cast<unsigned>(m),
          static_cast<unsigned>(d))*86400+hr*3600+sec;
}
void write(const std::string& geo_filename,const std::string& deck_filename,
           const std::string& output_filename) {
    const std::string deck=read(deck_filename);
    const auto geo=cteas::calmet::p6::read_geo_50(geo_filename,
              as_float(deck,"XORIGKM"),as_float(deck,"YORIGKM"));
    Calmet21File file;
    auto& h=file.header;
    h.dataset="CALMET.DAT";h.version="2.1";
    h.model="No-Obs file structure with embedded control file";
    h.comments={"CTEAS P6F metadata-only independent P6E control envelope",
                "No original CALMET.DAT was read; hourly inputs are all missing"};
    std::istringstream comment_lines(deck);
    std::string line;
    while(std::getline(comment_lines,line)){
        if(!line.empty()&&line.back()=='\r')line.pop_back();
        need(line.size()<=132,"original control line exceeds 132 bytes");
        h.comments.push_back(line);
    }
    h.begin_year=as_int(deck,"IBYR");h.begin_month=as_int(deck,"IBMO");
    h.begin_day=as_int(deck,"IBDY");h.begin_hour=as_int(deck,"IBHR");
    h.begin_second=as_int(deck,"IBSEC");
    h.end_year=as_int(deck,"IEYR");h.end_month=as_int(deck,"IEMO");
    h.end_day=as_int(deck,"IEDY");h.end_hour=as_int(deck,"IEHR");
    h.end_second=as_int(deck,"IESEC");
    h.timezone=control(deck,"ABTZ");
    h.irtype=as_int(deck,"IRTYPE");
    h.lcalgrd=control(deck,"LCALGRD")=="T";
    h.nx=as_int(deck,"NX");h.ny=as_int(deck,"NY");h.nz=as_int(deck,"NZ");
    h.dgrid_m=as_float(deck,"DGRIDKM")*1000.f;
    h.xorigin_m=as_float(deck,"XORIGKM")*1000.f;
    h.yorigin_m=as_float(deck,"YORIGKM")*1000.f;
    h.iwfcod=as_int(deck,"IWFCOD");
    h.nssta=as_int(deck,"NSSTA");h.nusta=as_int(deck,"NUSTA");
    h.npsta=as_int(deck,"NPSTA");h.nowsta=as_int(deck,"NOWSTA");
    h.nlu=geo.nlu;h.iwat1=geo.iwat1;h.iwat2=geo.iwat2;
    h.projection.pmap=control(deck,"PMAP");
    h.projection.datum=control(deck,"DATUM");
    h.projection.utmhem=control(deck,"UTMHEM");
    h.projection.iutmzn=as_int(deck,"IUTMZN");
    h.projection.feast=as_float(deck,"FEAST");
    h.projection.fnorth=as_float(deck,"FNORTH");
    // GEO.DAT itself supplies this provenance, not the original CALMET header.
    const auto geotext=read(geo_filename);
    std::smatch date;
    need(std::regex_search(geotext,date,
        std::regex("WGS-84[[:space:]]+([0-9]{2}-[0-9]{2}-[0-9]{4})")),
        "GEO.DAT lacks original map datum date");
    h.projection.daten=date[1].str();

    const std::int64_t begin=start_seconds(h,false);
    const std::int64_t end=start_seconds(h,true);
    need(end>begin&&(end-begin)%3600==0,"run window not integer hours");
    h.irlg=static_cast<std::int32_t>((end-begin)/3600);
    need(h.nx==50&&h.ny==50&&h.nz==9&&h.irlg==143&&
         h.nssta==1&&h.nusta==1&&h.npsta==0&&h.nowsta==0&&
         h.irtype==1&&h.lcalgrd&&h.iwfcod==1&&
         h.projection.pmap=="UTM"&&h.projection.iutmzn==50,
         "metadata-only input explicitly supports selected Hefei 50x50x9 143h only");

    auto& stat=file.statics;
    const std::size_t cells=static_cast<std::size_t>(h.nx)*static_cast<std::size_t>(h.ny);
    stat.zface_m=zface(deck);
    need(stat.zface_m.size()==static_cast<std::size_t>(h.nz+1),"ZFACE count");
    stat.z0_m=geo.z0_m;
    stat.ilandu.assign(geo.landuse.begin(),geo.landuse.end());
    stat.elev_m=geo.terrain_m;
    stat.xlai=geo.lai;
    need(stat.z0_m.size()==cells&&stat.ilandu.size()==cells&&
         stat.elev_m.size()==cells&&stat.xlai.size()==cells,
         "GEO static grid not 50x50");
    const auto ss=station(deck,"SS1"),us=station(deck,"US1");
    const float xo=as_float(deck,"XORIGKM")*1000.f;
    const float yo=as_float(deck,"YORIGKM")*1000.f;
    stat.surface_x_m={ss[0]*1000.f-xo};
    stat.surface_y_m={ss[1]*1000.f-yo};
    stat.upper_x_m={us[0]*1000.f-xo};
    stat.upper_y_m={us[1]*1000.f-yo};
    stat.nears.assign(cells,1);

    const auto labels=cteas::p6f::hourly_labels(
        h.nz,h.irtype,h.lcalgrd,h.npsta);
    need(labels.size()==45U,"expected 45 true original-mode fields");
    file.hourly.reserve(static_cast<std::size_t>(h.irlg)*labels.size());
    for(int hour=0;hour<h.irlg;++hour) {
        const Calmet21Time t=cteas::p6f::instant_to_time(begin+hour*3600);
        auto hour_end=t;hour_end.seconds=3600;
        for(const std::string& label:labels) {
            Calmet21Field x;
            x.label=label;x.begin=t;x.end=hour_end;
            x.integer=cteas::p6f::is_integer_label(label);
            if(x.integer)x.integer_values.assign(cells,cteas::p6f::missing_integer);
            else x.real_values.assign(cells,cteas::p6f::missing_real);
            file.hourly.push_back(std::move(x));
        }
    }
    cteas::p6f::write_calmet_dat21(output_filename,file);
    // Independently parse the product under the same fail-closed CALMET 2.1
    // binary contract consumed by the P6E emitter. Do not allow any field
    // from the missing-only input to masquerade as computed meteorology.
    const auto reopened=cteas::p6f::read_calmet_dat21(output_filename);
    need(reopened.header.irlg==143&&reopened.hourly.size()==143U*45U,
         "P6E metadata source output inventory drift");
    for(const auto& fld:reopened.hourly) {
        if(fld.integer){
            for(const auto v:fld.integer_values)
                need(v==cteas::p6f::missing_integer,
                     "P6E source-only metadata contains live integer weather");
        }else{
            for(const auto v:fld.real_values)
                need(v==cteas::p6f::missing_real,
                     "P6E source-only metadata contains live real weather");
        }
    }
    std::cout<<"PASS_P6F_P6E_SOURCE_ONLY_METADATA "
             <<"hours="<<h.irlg<<" fields_per_hour="<<labels.size()
             <<" cells="<<cells<<" source=GEO.DAT+met.inp "
             <<"original_calmet_opened=false hourly_filled_by_original=false\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc!=7||std::string(argv[1])!="--geo"||
           std::string(argv[3])!="--deck"||
           std::string(argv[5])!="--out")
            throw std::invalid_argument(
                "usage: p6f_p6e_source_metadata --geo GEO.DAT --deck met.inp --out METADATA_ONLY.DAT");
        write(argv[2],argv[4],argv[6]);
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"FAIL_P6F_P6E_SOURCE_METADATA: "<<e.what()<<'\n';
        return 1;
    }
}
