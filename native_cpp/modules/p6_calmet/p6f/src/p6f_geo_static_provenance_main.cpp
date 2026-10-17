// P6F source-independent grid/static provenance audit.
// The actual candidate's CALMET.DAT is read only for comparison: every
// expected grid value comes independently from GEO.DAT 2.1 and met.inp.
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
#include <utility>

namespace {
std::string input_text(const std::string& path) {
    std::ifstream file(path);
    if (!file) throw std::runtime_error("missing model input " + path);
    std::ostringstream out;
    out << file.rdbuf();
    if (file.bad()) throw std::runtime_error("failed model input read " + path);
    return out.str();
}
std::string field(const std::string& text, const std::string& key) {
    const std::regex re("!\\s*" + key + "\\s*=\\s*([^!]*)!",
                        std::regex_constants::icase);
    std::smatch m;
    if (!std::regex_search(text, m, re))
        throw std::runtime_error("met.inp missing " + key);
    auto value=m[1].str();
    const auto first=value.find_first_not_of(" \t\r\n");
    if(first==std::string::npos)throw std::runtime_error("empty met.inp " + key);
    const auto last=value.find_last_not_of(" \t\r\n");
    return value.substr(first,last-first+1);
}
int number_i(const std::string& text, const std::string& key) {
    const auto value=field(text,key);
    std::size_t at=0;
    const int result=std::stoi(value,&at);
    if(at!=value.size())throw std::runtime_error("bad integer "+key);
    return result;
}
float number_f(const std::string& text, const std::string& key) {
    const auto value=field(text,key);
    std::size_t at=0;
    const float result=std::stof(value,&at);
    if(at!=value.size()||!std::isfinite(result))
        throw std::runtime_error("bad float "+key);
    return result;
}
std::vector<float> face_list(const std::string& text) {
    std::string list=field(text,"ZFACE");
    for(auto& c:list)if(c==',')c=' ';
    std::istringstream stream(list);
    std::vector<float> result;
    float x;
    while(stream>>x)result.push_back(x);
    if(!stream.eof()||result.empty())
        throw std::runtime_error("invalid met.inp ZFACE");
    return result;
}
void require(bool yes,const std::string& why) {
    if(!yes)throw std::runtime_error("P6F_SRC_STATIC_NOT_PASS: "+why);
}
bool near(float actual,float expected,float tol=0.0f) {
    return std::isfinite(actual)&&std::isfinite(expected)&&
           std::abs(actual-expected)<=tol;
}
std::vector<float> station_xy(const std::string& deck,const std::string& key) {
    auto row=field(deck,key);
    // Original met.inp has a quoted 4-character station name followed by
    // station ID, UTM easting/northing in KM, region and measurement height.
    const auto quoted=row.find('\'');
    require(quoted!=std::string::npos,"missing station quote "+key);
    const auto close=row.find('\'',quoted+1);
    require(close!=std::string::npos,"station quote unmatched "+key);
    std::istringstream rest(row.substr(close+1));
    std::string identifier;
    float east=0.f,north=0.f;
    rest>>identifier>>east>>north;
    require(!identifier.empty()&&rest.good()&&east>0.f&&north>0.f,
            "station coordinates malformed "+key);
    return {east,north};
}
template<class A,class B> void check_array(const A& actual,const B& expected,
                                             const std::string& label,
                                             std::size_t& compared) {
    require(actual.size()==expected.size(),label+" count/shape disagreement");
    for(std::size_t i=0;i<actual.size();++i) {
        const float a=static_cast<float>(actual[i]);
        const float b=static_cast<float>(expected[i]);
        if(!near(a,b)) {
            throw std::runtime_error("P6F_SRC_STATIC_NOT_PASS: "+label+
                                     " mismatches GEO.DAT at index="+
                                     std::to_string(i)+
                                     " actual="+std::to_string(a)+
                                     " expected="+std::to_string(b));
        }
        ++compared;
    }
}
void check_scalar(int actual,int expected,const std::string& name) {
    require(actual==expected,name+" not reproduced");
}

void assemble_direct_native_hours(cteas::p6f::Calmet21File& file,
                                  const std::string& manifest_path) {
    namespace pf=cteas::p6f;
    const auto& h=file.header;
    require(h.irlg==143&&h.nx==50&&h.ny==50&&h.nz==9&&
            h.nssta==1&&h.nusta==1&&h.npsta==0,
            "native direct P6F supports the frozen 143h 50x50x9 case only");
    const auto labels=pf::hourly_labels(h.nz,h.irtype,h.lcalgrd,h.npsta);
    require(labels.size()==45U&&file.hourly.size()==143U*45U,
            "native source-only metadata inventory mismatch");
    for(std::size_t i=0;i<file.hourly.size();++i){
        const auto& v=file.hourly[i];
        require(v.label==labels[i%45U],"source metadata field label mismatch");
        if(v.integer){
            for(const auto x:v.integer_values)
                require(x==pf::missing_integer,"source metadata leaks integer weather");
        }else{
            for(const auto x:v.real_values)
                require(x==pf::missing_real,"source metadata leaks real weather");
        }
    }
    std::ifstream input(manifest_path);
    require(static_cast<bool>(input),"native one-hour manifest missing");
    std::vector<pf::Calmet21Field> assembled;
    assembled.reserve(143U*45U);
    std::string filename;
    std::size_t hour=0;
    auto same_clock=[](const pf::Calmet21Time& a,const pf::Calmet21Time& b){
        return a.year==b.year&&a.julian_day==b.julian_day&&
               a.hour==b.hour&&a.seconds==b.seconds;
    };
    while(std::getline(input,filename)){
        if(!filename.empty()&&filename.back()=='\r')filename.pop_back();
        require(!filename.empty()&&hour<143U,"native one-hour manifest has empty or extra rows");
        const auto current=pf::read_calmet_dat21_native_one_hour(filename);
        const auto& c=current.header;
        require(c.irlg==1&&c.nx==h.nx&&c.ny==h.ny&&c.nz==h.nz&&
                c.nssta==h.nssta&&c.nusta==h.nusta&&c.npsta==h.npsta&&
                c.timezone==h.timezone&&c.irtype==h.irtype&&
                c.lcalgrd==h.lcalgrd&&c.dgrid_m==h.dgrid_m&&
                c.xorigin_m==h.xorigin_m&&c.yorigin_m==h.yorigin_m,
                "native one-hour geometry or controls drift");
        require(current.hourly.size()==45U,"native one-hour payload not 45 fields");
        for(std::size_t j=0;j<45U;++j){
            const auto& field=current.hourly[j];
            const auto& expected=file.hourly[hour*45U+j];
            require(field.label==expected.label&&field.integer==expected.integer&&
                    same_clock(field.begin,expected.begin)&&
                    same_clock(field.end,expected.end),
                    "native hourly field label/clock/order mismatch");
            const std::size_t cells=2500U;
            if(field.integer){
                require(field.integer_values.size()==cells,
                        "native integer hourly field shape mismatch");
                for(auto x:field.integer_values)
                    require(x!=pf::missing_integer,
                            "unproduced native hourly integer field");
            }else{
                require(field.real_values.size()==cells,
                        "native real hourly field shape mismatch");
                for(auto x:field.real_values)
                    require(std::isfinite(x)&&x!=pf::missing_real,
                            "unproduced native hourly real field");
            }
        }
        assembled.insert(assembled.end(),current.hourly.begin(),current.hourly.end());
        ++hour;
    }
    require(!input.bad()&&hour==143U,"native direct writer requires exactly 143 hours");
    file.hourly=std::move(assembled);
}
}
int main(int argc,char** argv) {
    try {
        const bool direct=(argc==11&&std::string(argv[1])=="--geo"&&
                           std::string(argv[3])=="--deck"&&
                           std::string(argv[5])=="--source-metadata"&&
                           std::string(argv[7])=="--hour-manifest"&&
                           std::string(argv[9])=="--emit-native-header");
        const bool candidate=((argc==7||argc==9)&&
            std::string(argv[1])=="--geo"&&std::string(argv[3])=="--deck"&&
            std::string(argv[5])=="--candidate"&&
            (argc==7||std::string(argv[7])=="--emit-source-statics"||
                       std::string(argv[7])=="--emit-native-header"));
        if(!direct&&!candidate)
            throw std::runtime_error("usage: --geo GEO --deck DECK --candidate FILE"
                " [--emit-native-header OUT] or --source-metadata META"
                " --hour-manifest LIST --emit-native-header OUT (with --geo/--deck)");
        const auto deck=input_text(argv[4]);
        auto file=cteas::p6f::read_calmet_dat21(argv[6]);
        if(direct)assemble_direct_native_hours(file,argv[8]);
        const auto& hdr=file.header;
        const auto& stat=file.statics;
        check_scalar(hdr.nx,number_i(deck,"NX"),"NX");
        check_scalar(hdr.ny,number_i(deck,"NY"),"NY");
        check_scalar(hdr.nz,number_i(deck,"NZ"),"NZ");
        check_scalar(hdr.nssta,number_i(deck,"NSSTA"),"NSSTA");
        check_scalar(hdr.nusta,number_i(deck,"NUSTA"),"NUSTA");
        check_scalar(hdr.npsta,number_i(deck,"NPSTA"),"NPSTA");
        check_scalar(hdr.nowsta,number_i(deck,"NOWSTA"),"NOWSTA");
        check_scalar(hdr.irtype,number_i(deck,"IRTYPE"),"IRTYPE");
        check_scalar(hdr.begin_year,number_i(deck,"IBYR"),"IBYR");
        check_scalar(hdr.begin_month,number_i(deck,"IBMO"),"IBMO");
        check_scalar(hdr.begin_day,number_i(deck,"IBDY"),"IBDY");
        check_scalar(hdr.begin_hour,number_i(deck,"IBHR"),"IBHR");
        check_scalar(hdr.begin_second,number_i(deck,"IBSEC"),"IBSEC");
        check_scalar(hdr.end_year,number_i(deck,"IEYR"),"IEYR");
        check_scalar(hdr.end_month,number_i(deck,"IEMO"),"IEMO");
        check_scalar(hdr.end_day,number_i(deck,"IEDY"),"IEDY");
        check_scalar(hdr.end_hour,number_i(deck,"IEHR"),"IEHR");
        check_scalar(hdr.end_second,number_i(deck,"IESEC"),"IESEC");
        require(hdr.timezone==field(deck,"ABTZ"),"ABTZ");
        require(hdr.lcalgrd==(field(deck,"LCALGRD")=="T"),"LCALGRD");
        require(near(hdr.dgrid_m,number_f(deck,"DGRIDKM")*1000.f),"DGRID");
        require(near(hdr.xorigin_m,number_f(deck,"XORIGKM")*1000.f,0.3f),"XORIG");
        require(near(hdr.yorigin_m,number_f(deck,"YORIGKM")*1000.f,0.3f),"YORIG");
        require(hdr.projection.pmap=="UTM"||hdr.projection.pmap=="UTM     ",
                "projection PMAP");
        require(hdr.projection.datum.rfind("WGS-84",0)==0,"projection DATUM");
        require(hdr.projection.utmhem.rfind("N",0)==0,"projection hemisphere");
        check_scalar(hdr.projection.iutmzn,number_i(deck,"IUTMZN"),
                     "projection IUTMZN");
        const auto geo=cteas::calmet::p6::read_geo_50(argv[2],
                number_f(deck,"XORIGKM"),number_f(deck,"YORIGKM"));
        check_scalar(hdr.nlu,geo.nlu,"NLU");
        check_scalar(hdr.iwat1,geo.iwat1,"IWAT1");
        check_scalar(hdr.iwat2,geo.iwat2,"IWAT2");

        std::size_t compared=0;
        check_array(stat.zface_m,face_list(deck),"ZFACE/met.inp",compared);
        check_array(stat.z0_m,geo.z0_m,"Z0/GEO.DAT",compared);
        check_array(stat.ilandu,geo.landuse,"ILANDU/GEO.DAT",compared);
        check_array(stat.elev_m,geo.terrain_m,"ELEV/GEO.DAT",compared);
        check_array(stat.xlai,geo.lai,"XLAI/GEO.DAT",compared);
        if(hdr.nssta==1) {
            const auto xy=station_xy(deck,"SS1");
            // Original OUTHD uses REAL*4 (station_km*1000) -
            // (origin_km*1000), NOT (station_km-origin_km)*1000.
            // e.g. USTA X should be 2498.96875, not 2498.962402.
            const float east_m=xy[0]*1000.f-number_f(deck,"XORIGKM")*1000.f;
            const float north_m=xy[1]*1000.f-number_f(deck,"YORIGKM")*1000.f;
            check_array(stat.surface_x_m,std::vector<float>{east_m},
                        "XSSTA/met.inp",compared);
            check_array(stat.surface_y_m,std::vector<float>{north_m},
                        "YSSTA/met.inp",compared);
            // Only one surface station => nearest station ID is deterministically 1.
            check_array(stat.nears,std::vector<int>(2500,1),
                        "NEARS/single-station",compared);
        }
        if(hdr.nusta==1) {
            const auto xy=station_xy(deck,"US1");
            const float east_m=xy[0]*1000.f-number_f(deck,"XORIGKM")*1000.f;
            const float north_m=xy[1]*1000.f-number_f(deck,"YORIGKM")*1000.f;
            check_array(stat.upper_x_m,std::vector<float>{east_m},
                        "XUSTA/met.inp",compared);
            check_array(stat.upper_y_m,std::vector<float>{north_m},
                        "YUSTA/met.inp",compared);
        }
        if(argc==9||direct) {
            // Rebuild every supported case static from the primary GEO/deck,
            // not from the CALMET.DAT file under audit. Original hourly fields,
            // commentary, and unsupported header metadata are retained solely
            // as the comparison envelope, not independently generated here.
            require(hdr.nssta==1&&hdr.nusta==1&&hdr.npsta==0&&hdr.nowsta==0,
                    "source-static emission supports exactly one surface/upper station and no precipitation stations");
            auto& out=file.statics;
            out.zface_m=face_list(deck);
            out.z0_m=geo.z0_m;
            out.ilandu.assign(geo.landuse.begin(),geo.landuse.end());
            out.elev_m=geo.terrain_m;
            out.xlai=geo.lai;
            const auto xy_s=station_xy(deck,"SS1");
            const auto xy_u=station_xy(deck,"US1");
            const float xorig=number_f(deck,"XORIGKM")*1000.f;
            const float yorig=number_f(deck,"YORIGKM")*1000.f;
            out.surface_x_m={xy_s[0]*1000.f-xorig};
            out.surface_y_m={xy_s[1]*1000.f-yorig};
            out.upper_x_m={xy_u[0]*1000.f-xorig};
            out.upper_y_m={xy_u[1]*1000.f-yorig};
            out.nears.assign(2500,1);
            // Numeric file controls must also come from the upsteam deck.
            // CALMET.DAT is only retained as an envelope for comments and
            // hourly fields until those independent upstream writers exist.
            auto& h=file.header;
            h.begin_year=number_i(deck,"IBYR");
            h.begin_month=number_i(deck,"IBMO");
            h.begin_day=number_i(deck,"IBDY");
            h.begin_hour=number_i(deck,"IBHR");
            h.begin_second=number_i(deck,"IBSEC");
            h.end_year=number_i(deck,"IEYR");
            h.end_month=number_i(deck,"IEMO");
            h.end_day=number_i(deck,"IEDY");
            h.end_hour=number_i(deck,"IEHR");
            h.end_second=number_i(deck,"IESEC");
            h.timezone=field(deck,"ABTZ");
            h.irtype=number_i(deck,"IRTYPE");
            h.lcalgrd=(field(deck,"LCALGRD")=="T");
            h.nx=number_i(deck,"NX");
            h.ny=number_i(deck,"NY");
            h.nz=number_i(deck,"NZ");
            h.nssta=number_i(deck,"NSSTA");
            h.nusta=number_i(deck,"NUSTA");
            h.npsta=number_i(deck,"NPSTA");
            h.nowsta=number_i(deck,"NOWSTA");
            h.dgrid_m=number_f(deck,"DGRIDKM")*1000.f;
            h.xorigin_m=number_f(deck,"XORIGKM")*1000.f;
            h.yorigin_m=number_f(deck,"YORIGKM")*1000.f;
            h.nlu=geo.nlu;
            h.iwat1=geo.iwat1;
            h.iwat2=geo.iwat2;
            h.projection.pmap=field(deck,"PMAP");
            h.projection.datum=field(deck,"DATUM");
            h.projection.utmhem=field(deck,"UTMHEM");
            h.projection.iutmzn=number_i(deck,"IUTMZN");
            h.projection.feast=number_f(deck,"FEAST");
            h.projection.fnorth=number_f(deck,"FNORTH");
            const std::int64_t begin_days=cteas::p6f::days_from_civil(
                h.begin_year,static_cast<unsigned>(h.begin_month),
                static_cast<unsigned>(h.begin_day));
            const std::int64_t end_days=cteas::p6f::days_from_civil(
                h.end_year,static_cast<unsigned>(h.end_month),
                static_cast<unsigned>(h.end_day));
            const auto period_seconds=(end_days-begin_days)*86400+
                (h.end_hour-h.begin_hour)*3600+
                h.end_second-h.begin_second;
            require(period_seconds>0&&period_seconds%3600==0,
                    "source run window not integral hours");
            h.irlg=static_cast<std::int32_t>(period_seconds/3600);
            if(direct||std::string(argv[7])=="--emit-native-header") {
                // Full independently sourced OUTPUT *header and statics*.
                // The input's only retained data is its native P6D/P6E
                // hourly field values and their source-locked hour records.
                // The original comment count/text is intentionally NOT kept.
                cteas::p6f::Calmet21File assembled;
                assembled.hourly=std::move(file.hourly);
                assembled.statics=std::move(file.statics);
                auto& head=assembled.header;
                head.dataset="CALMET.DAT";
                head.version="2.1";
                head.model="No-Obs file structure with embedded control file";
                head.comments={
                    "CTEAS P6F native OUTHD from source met.inp + GEO.DAT",
                    "Hourly fields: C++ P6D + P6E; not from original CALMET output"};
                {
                    std::istringstream lines(deck);
                    std::string line;
                    while(std::getline(lines,line)) {
                        if(!line.empty()&&line.back()==static_cast<char>(13))line.pop_back();
                        require(line.size()<=132,
                            "source control line exceeds CALMET 132-column comment width");
                        head.comments.push_back(line);
                    }
                }
                // Recover the source projection date from GEO.DAT v2.1,
                // not from an existing CALMET.DAT header.
                const std::string geo_text=input_text(argv[2]);
                const std::regex datum_date("WGS-84[[:space:]]+([0-9]{2}-[0-9]{2}-[0-9]{4})");
                std::smatch date_match;
                require(std::regex_search(geo_text,date_match,datum_date),
                        "no WGS-84 coordinate datum date in GEO.DAT");
                const std::string geo_date=date_match[1].str();
                head.begin_year=h.begin_year;head.begin_month=h.begin_month;
                head.begin_day=h.begin_day;head.begin_hour=h.begin_hour;
                head.begin_second=h.begin_second;
                head.end_year=h.end_year;head.end_month=h.end_month;
                head.end_day=h.end_day;head.end_hour=h.end_hour;
                head.end_second=h.end_second;
                head.timezone=h.timezone;head.irlg=h.irlg;
                head.irtype=h.irtype;head.lcalgrd=h.lcalgrd;
                head.nx=h.nx;head.ny=h.ny;head.nz=h.nz;
                head.nssta=h.nssta;head.nusta=h.nusta;
                head.npsta=h.npsta;head.nowsta=h.nowsta;
                head.dgrid_m=h.dgrid_m;
                head.xorigin_m=h.xorigin_m;head.yorigin_m=h.yorigin_m;
                head.nlu=h.nlu;head.iwat1=h.iwat1;head.iwat2=h.iwat2;
                head.iwfcod=number_i(deck,"IWFCOD");
                head.projection.pmap=field(deck,"PMAP");
                head.projection.datum=field(deck,"DATUM");
                head.projection.daten=geo_date;
                head.projection.utmhem=field(deck,"UTMHEM");
                head.projection.iutmzn=number_i(deck,"IUTMZN");
                head.projection.feast=number_f(deck,"FEAST");
                head.projection.fnorth=number_f(deck,"FNORTH");
                // Selected UTM projection does not use these other-map
                // parameters. Preserve the original documented zero values,
                // without reading them from the input file.
                head.projection.rnlat0=0.f;head.projection.relon0=0.f;
                head.projection.xlat1=0.f;head.projection.xlat2=0.f;
                cteas::p6f::write_calmet_dat21(direct?argv[10]:argv[8],assembled);
            }else{
                cteas::p6f::write_calmet_dat21(direct?argv[10]:argv[8],file);
            }
        }
        std::cout<<"{\"status\":\"PASS_P6F_INDEPENDENT_SOURCE_STATIC_VALUES\","
                 <<"\"compared_static_values\":"<<compared<<","
                 <<"\"grid\":["<<hdr.nx<<","<<hdr.ny<<","<<hdr.nz<<"],"
                 <<"\"source\":\"GEO.DAT+met.inp independent of CALMET.DAT static inputs\","
                 <<"\"static_records_rebuilt\":"<<((argc==9||direct)?"true":"false")<<","
                 <<"\"numeric_run_controls_rebuilt\":"<<((argc==9||direct)?"true":"false")<<","
                 <<"\"header_comments_independent\":"<<
                      ((argc==9&&std::string(argv[7])=="--emit-native-header")||direct?"true":"false")<<","
                 <<"\"all_stations_independent\":false,"
                 <<"\"hourly_field_inputs_independent\":"<<(direct?"true":"false")<<","
                 <<"\"full_P6F_acceptance\":false}\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"FAIL_P6F_SOURCE_STATIC_AUDIT: "<<e.what()<<'\n';
        return 1;
    }
}
