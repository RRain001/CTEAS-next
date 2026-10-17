// P6D real-case wind-field producer (partial, explicitly labelled).
//
// Reads a CALMET 6.5.0 case tree read-only:
//   run/met/met.inp                        (controls, ZFACE, station ids)
//   geo/**/geo.dat                         (GEO.DAT 2.1 terrain + land use)
//   met/surface/final/surf.dat             (SURF.DAT 2.1 surface observations)
//   met/upperair/final/up_<id>.dat         (UP.DAT 2.1 upper-air soundings)
// and writes, per hourly label, chain-internal fields plus a JSON metadata
// block that names exactly which DIAGNO stages were applied and which inputs
// would still be required for the remaining ones.
//
// This is a PARTIAL product: it delivers the original WIND1 step-one UG/VG
// grid (IEXTRP=-4 neutral SIMILT first guess, the field DIAGNO starts from)
// and the in-chain TERSET envelope. It deliberately does not invent values
// for stages whose real-case inputs are not available in this branch
// (SURFVAR TEMP2D, ISFCMET QH), so those stages are reported as not applied
// rather than silently substituted.
#include <iomanip>
#include "cteas/p6/calmet_station_deck.hpp"
#include "cteas/p6/calmet_station_surface.hpp"
#include "cteas/p6/read_geo.hpp"
#include "cteas/p6/read_surface.hpp"
#include "cteas/p6/read_upper.hpp"
#include "cteas/p6/diagno_segment.hpp"
#include "cteas/p6/froude_adjust.hpp"
#include "cteas/p6/slope_flow.hpp"
#include "cteas/p6/station_elustr2.hpp"
#include "cteas/p6/station_mixhtst.hpp"
#include "cteas/p6e/heatfx.hpp"
#include "cteas/p6e/elustr_stable.hpp"
#include "cteas/p6e/elustr_daytime.hpp"
#include "cteas/p6e/coordlib_pj09z0.hpp"
#include "cteas/p6e/surface_solar.hpp"
#include "cteas/p6e/surfvar_observed.hpp"
#include "cteas/p6/inter2_selected.hpp"
#include "cteas/p6/similt_profile.hpp"
#include "cteas/p6/terrain_envelope.hpp"
#include "cteas/p6/upper_hourly_wind.hpp"
#include "cteas/p6/wind1_selected_firstguess.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace cteas::calmet::p6;
namespace fs = std::filesystem;

namespace {
constexpr float MISSING=9999.f;

std::string read_text(const fs::path& path){
    std::ifstream in(path,std::ios::binary);
    if(!in)throw std::runtime_error("cannot read "+path.string());
    std::ostringstream buffer;buffer<<in.rdbuf();
    return buffer.str();
}

// CALMET control decks annotate each value as "! KEY = value !"; take the
// annotated value when present, otherwise the first number on the key's line.
std::map<std::string,std::vector<float>> deck_values(const std::string& text){
    std::map<std::string,std::vector<float>> values;
    static const std::regex annotated(R"(!\s*([A-Z0-9]+)\s*=\s*([^!]*)!)");
    for(auto it=std::sregex_iterator(text.begin(),text.end(),annotated);
        it!=std::sregex_iterator();++it){
        const std::string key=(*it)[1].str();
        // Values arrive either space or comma separated ("0 , 2 , 4").
        static const std::regex number(
            R"([-+]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eEdD][-+]?[0-9]+)?)");
        const std::string raw=(*it)[2].str();
        std::vector<float> numbers;
        for(auto n=std::sregex_iterator(raw.begin(),raw.end(),number);
            n!=std::sregex_iterator();++n){
            std::string token=n->str();
            for(char& c:token)if(c=='d'||c=='D')c='e';
            numbers.push_back(std::stof(token));
        }
        if(!numbers.empty()&&!values.count(key))values[key]=numbers;
    }
    return values;
}

float deck_scalar(const std::map<std::string,std::vector<float>>& v,
                  const std::string& key,float fallback){
    const auto it=v.find(key);
    return it==v.end()?fallback:it->second.front();
}

float required_deck_scalar(
    const std::map<std::string,std::vector<float>>& values,const std::string& key) {
    const auto it=values.find(key);
    if(it==values.end()||it->second.size()!=1U||
       !std::isfinite(it->second.front()))
        throw std::runtime_error("CALMET Mode A requires met.inp control "+key);
    return it->second.front();
}

int deck_int(const std::map<std::string,std::vector<float>>& v,
             const std::string& key,int fallback){
    return static_cast<int>(deck_scalar(v,key,static_cast<float>(fallback)));
}

void write_f32(const fs::path& path,const std::vector<float>& data){
    std::ofstream out(path,std::ios::binary);
    if(!out)throw std::runtime_error("cannot write "+path.string());
    for(float value:data){
        const std::uint32_t raw=std::bit_cast<std::uint32_t>(value);
        out.write(reinterpret_cast<const char*>(&raw),4);
    }
}

std::string sha256_short(const fs::path& path){
    // Content identity without pulling a hash library into the module: FNV-1a
    // over the bytes, plus the byte count, is enough to label inputs here.
    std::ifstream in(path,std::ios::binary);
    if(!in)throw std::runtime_error("cannot hash "+path.string());
    std::uint64_t hash=1469598103934665603ull;
    std::size_t bytes=0;
    char buffer[65536];
    while(in){
        in.read(buffer,sizeof(buffer));
        const auto got=static_cast<std::size_t>(in.gcount());
        for(std::size_t n=0;n<got;++n){
            hash^=static_cast<unsigned char>(buffer[n]);
            hash*=1099511628211ull;
        }
        bytes+=got;
    }
    std::ostringstream text;
    text<<"fnv1a64:"<<std::hex<<hash<<":bytes:"<<std::dec<<bytes;
    return text.str();
}

std::string hour_label(std::chrono::sys_seconds clock){
    const auto day=std::chrono::floor<std::chrono::days>(clock);
    const std::chrono::year_month_day ymd{day};
    const auto hour=std::chrono::duration_cast<std::chrono::hours>(clock-day).count();
    std::ostringstream text;
    text<<int(ymd.year())
        <<'-'<<(unsigned(ymd.month())<10?"0":"")<<unsigned(ymd.month())
        <<'-'<<(unsigned(ymd.day())<10?"0":"")<<unsigned(ymd.day())
        <<'_'<<(hour<10?"0":"")<<hour;
    return text.str();
}

struct Arguments {
    fs::path case_dir,out_dir,geo,deck,surface,upper,fixture_dir,gamma_dir,zi_file,el_file,zii_file,el_cell_file,comp_state_prefix;
    int hours=143;
    int first_hour=0; // original zero-based hourly label index
    bool native_setup_hour0=false; // original CALMET SETUP zero COMMON history
    fs::path out()const{return out_dir;}
};
} // namespace

int main(int argc,char** argv){
 try{
    Arguments args;
    for(int n=1;n<argc;++n){
        const std::string flag=argv[n];
        auto next=[&]()->std::string{
            if(n+1>=argc)throw std::invalid_argument("missing value for "+flag);
            return argv[++n];
        };
        if(flag=="--case")args.case_dir=next();
        else if(flag=="--out")args.out_dir=next();
        else if(flag=="--geo")args.geo=next();
        else if(flag=="--deck")args.deck=next();
        else if(flag=="--surface")args.surface=next();
        else if(flag=="--upper")args.upper=next();
        else if(flag=="--fixtures")args.fixture_dir=next();
        else if(flag=="--gamma")args.gamma_dir=next();
        else if(flag=="--zi")args.zi_file=next();
        else if(flag=="--el")args.el_file=next();
        else if(flag=="--zii-cell")args.zii_file=next();
        else if(flag=="--el-cell")args.el_cell_file=next();
        else if(flag=="--comp-state-prefix")args.comp_state_prefix=next();
        else if(flag=="--hours")args.hours=std::stoi(next());
        else if(flag=="--first-hour")args.first_hour=std::stoi(next());
        else if(flag=="--native-setup-hour0")args.native_setup_hour0=true;
        else throw std::invalid_argument("unknown argument "+flag);
    }
    if(args.out_dir.empty())throw std::invalid_argument("--out is required");
    if(args.first_hour<0||args.first_hour>=143||args.hours<1||
       args.hours>143-args.first_hour)
        throw std::invalid_argument("P6D hour window exceeds 143 original intervals");
    if(!args.comp_state_prefix.empty() &&
       (!args.zi_file.empty()||!args.zii_file.empty()||
        !args.el_file.empty()||!args.el_cell_file.empty()))
        throw std::invalid_argument("native COMP state cannot mix with original ZII/EL/ZI injection");
    if(args.native_setup_hour0 &&
       (args.first_hour!=0||args.hours!=1||
        !args.comp_state_prefix.empty()||!args.zi_file.empty()||
        !args.el_file.empty()||!args.zii_file.empty()||
        !args.el_cell_file.empty()))
        throw std::invalid_argument(
            "original SETUP initial state may be used only for causal hour 0, never with oracle/COMP history");
    if(args.case_dir.empty()&&(args.geo.empty()||args.deck.empty()||
                               args.surface.empty()||args.upper.empty()))
        throw std::invalid_argument(
            "realcase-wind needs --case or all of --geo/--deck/--surface/--upper");
    if(!args.case_dir.empty()){
        if(args.deck.empty())args.deck=args.case_dir/"run/met/met.inp";
        if(args.surface.empty())args.surface=args.case_dir/"met/surface/final/surf.dat";
        if(args.upper.empty()){
            std::vector<fs::path> found;
            for(const auto& entry:fs::directory_iterator(args.case_dir/"met/upperair/final"))
                if(entry.path().extension()==".dat")found.push_back(entry.path());
            if(found.size()!=1)
                throw std::runtime_error("ambiguous upper-air file; pass --upper");
            args.upper=found.front();
        }
        if(args.geo.empty()){
            for(const auto& entry:fs::recursive_directory_iterator(args.case_dir/"geo"))
                if(entry.path().filename()=="geo.dat")args.geo=entry.path();
            if(args.geo.empty())throw std::runtime_error("geo.dat not found; pass --geo");
        }
    }
    fs::create_directories(args.out_dir);
    if(!args.fixture_dir.empty()){
        // The fixture directory is an output of this run: create it rather
        // than making the caller prepare it (the gate step passes a fresh
        // evidence path).
        std::error_code error;
        fs::create_directories(args.fixture_dir,error);
        if(error||!fs::is_directory(args.fixture_dir))
            throw std::runtime_error("cannot create fixture directory "+
                                     args.fixture_dir.string());
    }
    if(!args.gamma_dir.empty()&&!fs::is_directory(args.gamma_dir))
        throw std::runtime_error("GAMMA directory does not exist: "+
                                 args.gamma_dir.string());

    const std::string deck=read_text(args.deck);
    const auto controls=deck_values(deck);
    const int nx=static_cast<int>(required_deck_scalar(controls,"NX"));
    const int ny=static_cast<int>(required_deck_scalar(controls,"NY"));
    const int nz=static_cast<int>(required_deck_scalar(controls,"NZ"));
    const float grid_m=required_deck_scalar(controls,"DGRIDKM")*1000.f;
    const float terrad_km=required_deck_scalar(controls,"TERRAD");
    const double origin_x_km=required_deck_scalar(controls,"XORIGKM");
    const double origin_y_km=required_deck_scalar(controls,"YORIGKM");
    if(origin_x_km<=0.||origin_y_km<=0.)
        throw std::runtime_error("the deck must declare XORIGKM/YORIGKM");
    const int iextrp=deck_int(controls,"IEXTRP",-4);
    const int icalm=deck_int(controls,"ICALM",0);
    if(nx!=50||ny!=50||nz!=9)
        throw std::runtime_error(
            "this producer is scoped to the frozen 50x50x9 case grid");
    if(std::abs(grid_m-100.f)>1e-3f)
        throw std::runtime_error("this producer is scoped to the 100 m grid");
    std::array<float,10> zface{};
    {
        const auto it=controls.find("ZFACE");
        if(it==controls.end()||it->second.size()!=10)
            throw std::runtime_error("the deck must declare ten ZFACE values");
        for(std::size_t k=0;k<10;++k)zface[k]=it->second[k];
    }
    std::vector<float> thickness_m(9),center_m(9);
    for(int k=0;k<9;++k){
        thickness_m[std::size_t(k)]=zface[std::size_t(k)+1]-zface[std::size_t(k)];
        center_m[std::size_t(k)]=
            0.5f*(zface[std::size_t(k)]+zface[std::size_t(k)+1]);
    }
    std::array<float,9> bias{};
    {
        const auto it=controls.find("BIAS");
        if(it!=controls.end()&&it->second.size()>=9)
            for(std::size_t k=0;k<9;++k)bias[k]=it->second[k];
    }
    // CALMET 6.5.0 READCF (calmet.for L26579-L26612) modifies the
    // EFFECTIVE BIAS array after reading met.inp. For IEXTRP<0 with
    // surface observations, level one must use surface winds only;
    // frozen met.inp says BIAS(1)=0 but original READCF resets it to -1.
    // This is part of original source physics, not a tolerance workaround.
    const int noobs=deck_int(controls,"NOOBS",0);
    if(iextrp<0&&noobs!=2)bias[0]=-1.f;
    if(std::abs(iextrp)==1&&noobs!=2)
        for(std::size_t k=1;k<9;++k)bias[k]=1.f;

    // CALMET MODE A (original input): SS1/US1 in the met.inp deck are the
    // authority for station location. REAL*4 UTM-km -> local metres is done
    // once, before feeding WIND1/INTER2/DIAGI. CSV is metadata/identity only.
    if(deck_int(controls,"NSSTA",-1)!=1||deck_int(controls,"NUSTA",-1)!=1)
        throw std::runtime_error(
            "this real-case producer requires one deck surface/upper station");
    const auto deck_stations=original_calmet_station_deck(
        deck,required_deck_scalar(controls,"XORIGKM"),
        required_deck_scalar(controls,"YORIGKM"));
    const float surface_x_m=deck_stations.surface.local_x_m;
    const float surface_y_m=deck_stations.surface.local_y_m;
    const float upper_x_m=deck_stations.upper.local_x_m;
    const float upper_y_m=deck_stations.upper.local_y_m;
    // DIAGI's UTMXST/UTMYST are derived from the local-metre station positions.
    const float surface_x_km=surface_x_m*0.001f;
    const float surface_y_km=surface_y_m*0.001f;
    const float upper_x_km=upper_x_m*0.001f;
    const float upper_y_km=upper_y_m*0.001f;
    // The original READCF L27053-27070 computes XSLAT/XULAT with GLOBE
    // from the UTM-km station records BEFORE converting them to local metres.
    // Reuse the source-ported COORDLIB inverse from P6E, never CSV latitude
    // as a replacement physics input.
    const int utm_zone=deck_int(controls,"IUTMZN",-1);
    const auto projection=cteas::p6e::utm_north_projection(utm_zone);
    double station_lat=0.,station_lon=0.;
    cteas::p6e::utm_north_to_latlon_deg(
        projection,
        static_cast<double>(deck_stations.surface.utm_x_km)*1000.0,
        static_cast<double>(deck_stations.surface.utm_y_km)*1000.0,
        station_lat,station_lon);
    const float station_lat_deg=static_cast<float>(station_lat);
    if(!std::isfinite(station_lat_deg)||std::abs(station_lat_deg)>90.f)
        throw std::runtime_error("GLOBE station latitude is invalid");
    if(args.case_dir.empty())
        throw std::runtime_error(
            "Mode A requires --case for independent station identity/latitude metadata");
    {
        const std::string table=read_text(args.case_dir/"met/surface/final/stations.csv");
        std::istringstream stream(table);
        std::string line,extra;
        if(!std::getline(stream,line)||!std::getline(stream,line))
            throw std::runtime_error("missing surface stations.csv row");
        std::vector<std::string> fields;
        std::istringstream row(line);
        std::string field;
        while(std::getline(row,field,','))fields.push_back(field);
        if(fields.size()<4||std::stoi(fields[0])!=deck_stations.surface.id)
            throw std::runtime_error("SS1 station ID disagrees with surface stations.csv");
        if(std::getline(stream,extra) && !extra.empty())
            throw std::runtime_error("surface stations.csv has unsupported extra stations");
    }
    {
        const std::string table=read_text(args.case_dir/"met/upperair/final/stations.csv");
        std::istringstream stream(table);
        std::string line,extra;
        if(!std::getline(stream,line)||!std::getline(stream,line))
            throw std::runtime_error("missing upper stations.csv row");
        std::vector<std::string> fields;
        std::istringstream row(line);
        std::string field;
        while(std::getline(row,field,','))fields.push_back(field);
        if(fields.size()<4||std::stoi(fields[0])!=deck_stations.upper.id)
            throw std::runtime_error("US1 station ID disagrees with upper stations.csv");
        if(std::getline(stream,extra) && !extra.empty())
            throw std::runtime_error("upper stations.csv has unsupported extra stations");
    }

    const auto geo=read_geo_50(args.geo.string(),origin_x_km,origin_y_km);
    const auto surface=read_surface_2022(args.surface.string());
    // UP.DAT carries the upper station ID in its 6201 record tags; the case
    // convention names the file up_<station>.dat.
    int upper_station=0;
    {
        const std::string stem=args.upper.stem().string();
        const auto underscore=stem.rfind('_');
        if(underscore==std::string::npos)
            throw std::runtime_error("upper-air file name must be up_<station>.dat");
        upper_station=std::stoi(stem.substr(underscore+1));
        if(upper_station<=0)
            throw std::runtime_error("upper-air station ID must be positive");
        if(upper_station!=deck_stations.upper.id)
            throw std::runtime_error("US1 station ID disagrees with UP.DAT filename");
    }
    const auto upper=read_upper_2022(args.upper.string(),upper_station);

    const auto start=std::chrono::sys_days{std::chrono::year{2022}/1/1};
    std::vector<std::chrono::sys_seconds> labels;
    for(int n=1;n<=args.first_hour+args.hours;++n)
        labels.push_back(start+std::chrono::hours{n});

    // Original PREPDI hourly upper-air preparation (VERTAV layer averages plus
    // the PREPDI time interpolation), exactly the 143 case hours.
    const std::vector<float> zface_vector(zface.begin(),zface.end());
    const auto hourly_upper=calmet_prepdi_2022_hours(upper,zface_vector);

    // Original INTER2 controls from the deck: radii in km, RVARY off and the
    // per-layer station limit. WO is not read here: RDWT sets 1.0 for IPROG=0.
    const float critfn=deck_scalar(controls,"CRITFN",1.f);
    const float fradj_tinf_k=285.f;  // unused for ISURFT<0 (TEMP2D is used)
    const float rmin_km=deck_scalar(controls,"RMIN",0.1f);
    const float rmax1_km=required_deck_scalar(controls,"RMAX1");
    const float rmax2_km=required_deck_scalar(controls,"RMAX2");
    const float rmax3_km=required_deck_scalar(controls,"RMAX3");
    const float r1_km=required_deck_scalar(controls,"R1");
    const float r2_km=required_deck_scalar(controls,"R2");
    const bool lvary=original_calmet_deck_logical(deck,"LVARY",false);
    std::vector<int> nsmth(9);
    {
        const auto it=controls.find("NSMTH");
        if(it==controls.end()||it->second.size()<9)
            throw std::runtime_error("the deck must declare nine NSMTH values");
        for(std::size_t k=0;k<9;++k)
            nsmth[k]=static_cast<int>(it->second[k]);
    }
    // Deck ZIMIN: the lower bound SIMILT applies to the mixing height
    // (calmet.for L6894 passes ZIMIN as ZIMINI).
    float zimin_m=0.f;
    {
        const auto it=controls.find("ZIMIN");
        if(it==controls.end()||it->second.empty())
            throw std::runtime_error("the deck must declare ZIMIN");
        zimin_m=it->second[0];
        if(!(zimin_m>0.f&&zimin_m<9998.f))
            throw std::runtime_error("the deck ZIMIN must be a positive height");
    }
    std::vector<int> nintrp(9);
    {
        const auto it=controls.find("NINTR2");
        if(it==controls.end()||it->second.size()<9)
            throw std::runtime_error("the deck must declare nine NINTR2 values");
        // The deck's NINTR2=99 is an upper bound on stations per layer; with
        // two stations in this case the original uses min(NINTR2, NWIND).
        for(std::size_t k=0;k<9;++k)
            nintrp[k]=std::max(1,std::min(static_cast<int>(it->second[k]),2));
    }

    // Mixing height per hour used by SIMILT's cutoff. DIAGI passes
    // zii=zi(is,js) (calmet.for L6876/L6894) and SIMILT exits above it
    // ("Above mixing height, exit", L30319/L30345), leaving those levels to the
    // upper-air sounding. P6E E29 exports that ZI field; its accuracy is not
    // certified, so the provenance is labelled in metadata.
    std::vector<float> zi_hours;
    if(!args.zi_file.empty()){
        if(!fs::is_regular_file(args.zi_file))
            throw std::runtime_error("ZI file does not exist: "+
                                     args.zi_file.string());
        const auto bytes=fs::file_size(args.zi_file);
        if(bytes%std::size_t(4*(std::size_t(nx)*std::size_t(ny)))!=0||bytes/std::size_t(4*(std::size_t(nx)*std::size_t(ny)))<3)
            throw std::runtime_error("ZI file must hold whole hourly "
                                     "nx*ny float32 blocks");
        std::ifstream stream(args.zi_file,std::ios::binary);
        if(!stream)throw std::runtime_error("cannot open the ZI file");
        zi_hours.assign(bytes/std::size_t(4),0.f);
        stream.read(reinterpret_cast<char*>(zi_hours.data()),
                    static_cast<std::streamsize>(bytes));
    }
    // The ZII that the original hands to SIMILT, per hour (143 float32). DIAGI
    // overwrites its local ZI through MIXHTST/MIXHT2ST (L6882-L6887) before the
    // SIMILT call (L6894), so the grid ZI early-stops the profile by one level
    // in 50 of the 143 hours. Source: DGM's instrumented original run.
    std::vector<float> zii_hours;
    if(!args.zii_file.empty()){
        if(!fs::is_regular_file(args.zii_file))
            throw std::runtime_error("ZII file does not exist: "+args.zii_file.string());
        const auto bytes=fs::file_size(args.zii_file);
        if(bytes%4!=0||bytes/4<3)
            throw std::runtime_error("ZII file must hold whole hourly float32 values");
        std::ifstream stream(args.zii_file,std::ios::binary);
        if(!stream)throw std::runtime_error("cannot open the ZII file");
        zii_hours.assign(bytes/4,0.f);
        stream.read(reinterpret_cast<char*>(zii_hours.data()),
                    static_cast<std::streamsize>(bytes));
    }
    // The Monin-Obukhov length the original actually hands to SIMILT, per hour
    // (143 float32, from DGM's instrumented run). The P6E E29 EL export agrees
    // with it in most hours but differs by a factor of ~3 at some (e.g. hours
    // 42/43: 120.4009 against 43.3443), which moves the SIMILT profile.
    std::vector<float> el_cell_hours;
    if(!args.el_cell_file.empty()){
        if(!fs::is_regular_file(args.el_cell_file))
            throw std::runtime_error("EL cell file does not exist: "+
                                     args.el_cell_file.string());
        const auto bytes=fs::file_size(args.el_cell_file);
        if(bytes%4!=0||bytes/4<3)
            throw std::runtime_error("EL cell file must hold whole hourly float32 values");
        std::ifstream stream(args.el_cell_file,std::ios::binary);
        if(!stream)throw std::runtime_error("cannot open the EL cell file");
        el_cell_hours.assign(bytes/4,0.f);
        stream.read(reinterpret_cast<char*>(el_cell_hours.data()),
                    static_cast<std::streamsize>(bytes));
    }
    // Monin-Obukhov length per hour (P6E E29 <prefix>.el.f32, same layout).
    // DIAGI's station column is built from it (calmet.for L6894 -> STHEOR).
    std::vector<float> el_hours;
    if(!args.el_file.empty()){
        if(!fs::is_regular_file(args.el_file))
            throw std::runtime_error("EL file does not exist: "+args.el_file.string());
        const auto bytes=fs::file_size(args.el_file);
        if(bytes%std::size_t(4*(std::size_t(nx)*std::size_t(ny)))!=0)
            throw std::runtime_error("EL file must hold whole hourly nx*ny float32 blocks");
        std::ifstream stream(args.el_file,std::ios::binary);
        if(!stream)throw std::runtime_error("cannot open the EL file");
        el_hours.assign(bytes/std::size_t(4),0.f);
        stream.read(reinterpret_cast<char*>(el_hours.data()),
                    static_cast<std::streamsize>(bytes));
    }
    // P6E COMP state (post-AVEMIX ZI/ZICONV, post-MIXHT DPTT). At hour h,
    // original STHEOR->ELUSTR2->MIXHTST sees COMP state from hour h-1.
    // These are independent C++-produced fields, not original oracle files.
    std::vector<float> comp_zi,comp_ziconv,comp_dptt;
    if(!args.comp_state_prefix.empty()){
        const auto stem=args.comp_state_prefix.string();
        const auto metadata=fs::path(stem+".state.json");
        if(!fs::is_regular_file(metadata))
            throw std::runtime_error("native COMP state metadata absent: "+metadata.string());
        const auto meta=read_text(metadata);
        if(meta.find("\"producer\": \"p6e_calmet_dat21 emit-realcase\"")==std::string::npos ||
           meta.find("\"dptt\"")==std::string::npos)
            throw std::runtime_error("COMP state missing native P6E DPTT provenance");
        const auto read_block=[&](const std::string& suffix)->std::vector<float> {
            const fs::path path(stem+suffix);
            // A native per-hour DIAGNO step must never demand future COMP
            // state. Hour n reads at most COMP states 0..n-1.
            const auto required_hours=(args.first_hour==0?args.hours:
                                       args.first_hour+args.hours-1);
            const auto expected=std::size_t(required_hours)*std::size_t(nx*ny)*4U;
            if(!fs::is_regular_file(path)||fs::file_size(path)<expected ||
               fs::file_size(path)%std::size_t(nx*ny*4)!=0)
                throw std::runtime_error("native COMP missing/truncated field "+path.string());
            const auto bytes=fs::file_size(path);
            std::vector<float> out(static_cast<std::size_t>(bytes/4),0.f);
            std::ifstream in(path,std::ios::binary);
            in.read(reinterpret_cast<char*>(out.data()),
                    static_cast<std::streamsize>(bytes));
            if(!in||!std::all_of(out.begin(),out.end(),
                 [](float f){return std::isfinite(f)&&std::abs(f)<999998.f;}))
                throw std::runtime_error("native COMP has invalid physical values "+path.string());
            return out;
        };
        comp_zi=read_block(".zi.f32");
        comp_ziconv=read_block(".ziconv.f32");
        comp_dptt=read_block(".dptt.f32");
        if(comp_zi.size()!=comp_ziconv.size()||
           comp_zi.size()!=comp_dptt.size())
            throw std::runtime_error("native COMP state three streams do not align");
    }
    const auto envelope=terset(geo.terrain_m,nx,ny,grid_m,grid_m,terrad_km);
    write_f32(args.out()/"terset_hmax.f32",envelope.maximum_m);
    write_f32(args.out()/"terset_hmin.f32",envelope.minimum_m);
    write_f32(args.out()/"terset_disthmax.f32",envelope.distance_to_maximum_m);
    write_f32(args.out()/"terset_disthmin.f32",envelope.distance_to_minimum_m);

    // WIND1 source L36179-L36187 takes Z0 at IST(SS1),JST(SS1), where
    // DIAGI L5129-L5130 computes the station cell using READCF local metres.
    // GEO (1,1) is NOT the station roughness unless SS1 lies in that cell.
    const float surface_station_z0=original_calmet_station_z0(
        geo.z0_m,surface_x_m,surface_y_m,grid_m,grid_m,nx,ny);
    const float surface_anemometer_height_m=
        deck_stations.surface.anemometer_height_m;
    const std::size_t stations_written=1;
    std::ofstream station_elustr2_trace(args.out()/"station_elustr2.csv");
    if(!station_elustr2_trace)throw std::runtime_error("cannot open station ELUSTR2 trace");
    station_elustr2_trace<<"hour_end,QH_Wm2,USTAR_mps,EL_m,solar_sine,temp_K,rho_kgm3,Z0_m,station_cell_i,station_cell_j\n";
    std::ofstream station_mixhtst_trace(args.out()/"station_mixhtst.csv");
    if(!station_mixhtst_trace)throw std::runtime_error("cannot write station MIXHTST trace");
    station_mixhtst_trace<<"hour_end,ZI_M,ZICONV_M,DPTT_K,PREV_ZI_M,PREV_ZICONV_M,PREV_DPTT_K,EL_M,source_kind\n";
    std::ofstream station_inter2_first(args.out()/"station_inter2_layer1.csv");
    if(!station_inter2_first)throw std::runtime_error("cannot write station INTER2 source inputs");
    station_inter2_first<<"hour_end,surface_u,surface_v,upper_u,upper_v\n";
    std::ofstream index(args.out()/"produced_hours.txt");
    if(!index)throw std::runtime_error("cannot write produced_hours.txt");
    std::size_t similt_levels_min=9,similt_levels_max=0;
    int written=0;
    float speed_min=1.e9f,speed_max=-1.e9f;
    for(std::size_t h=static_cast<std::size_t>(args.first_hour);
        h<labels.size()&&written<args.hours;++h){
        const auto clock=labels[h];
        const auto& hour=hourly_upper[h];
        // Surface observation at this hour; fail closed on missing winds.
        const SurfaceObserved* obs=nullptr;
        for(const auto& interval:surface.hourly)
            if(interval.end==clock&&interval.obs.wind_valid){
                obs=&interval.obs;
                break;
            }
        if(obs==nullptr)
            throw std::runtime_error(
                "surface wind observation missing for "+hour_label(clock));
        const float speed=obs->wind_speed_mps;
        // CALMET 6.5.0 PREPDI calmet.for L13890: WDRAD = 0.0174533 * WD.
        // Preserve the source REAL*4 literal and multiplication order; using
        // WD*pi/180 alters the station U/V before STHEOR/SIMILT and INTER2.
        const float radians=0.0174533f*obs->wind_direction_deg;
        const float surface_u=-speed*std::sin(radians);
        const float surface_v=-speed*std::cos(radians);
        speed_min=std::min(speed_min,speed);
        speed_max=std::max(speed_max,speed);

        Wind1SelectedStationHour station;
        std::array<LayerWind,9> diagi_surface_column{};
        bool settings_upper_layer_one_valid=true;
        station.hour_end=clock;
        station.surface_station_id=surface.station_id;
        station.upper_station_id=upper.station_id;
        station.surface_observed_u_mps=surface_u;
        station.surface_observed_v_mps=surface_v;
        const float roughness=surface_station_z0;
        if(std::hypot(surface_u,surface_v)>0.0001f){
            const SimiltProfileInput neutral{
                station_lat_deg,surface_anemometer_height_m,roughness,surface_u,surface_v,
                10000.f,10000.f,10000.f,0,
                {0.f,20.f,40.f,80.f,160.f,320.f,640.f,1200.f,2000.f,3000.f}};
            const auto profile=original_similt_profile(neutral);
            // Write-only REAL*4 neutral station column before WIND1 spatial
            // weighting. This is forensic data, never read back as a model
            // input and never substituted for the original station profile.
            std::vector<float> wind1_neutral_values;
            wind1_neutral_values.reserve(18);
            for(const float value:profile.u_mps)wind1_neutral_values.push_back(value);
            for(const float value:profile.v_mps)wind1_neutral_values.push_back(value);
            write_f32(args.out()/("wind1_neutral_profile_"+
                      hour_label(clock)+".f32"),wind1_neutral_values);
            for(std::size_t k=0;k<9;++k)
                station.surface_neutral_profile[k]=
                    LayerWind{profile.u_mps[k],profile.v_mps[k]};
            // The original's SIMILT fills the surface-station profile only
            // while zmid(k) <= zic and exits above the mixing height
            // (calmet.for L30345 "Above mixing height, exit"); those levels
            // keep the upper-air sounding instead of a surface extrapolation.
            // Without a certified mixing height the profile is left missing
            // above level 1 rather than invented.
            float mixing_height_m=-1.f;
            if(!zi_hours.empty()){
                const std::size_t cell=std::size_t(ny/2)*std::size_t(nx)+
                                       std::size_t(nx/2);
                const std::size_t offset=h*std::size_t(nx)*std::size_t(ny)+cell;
                if(offset>=zi_hours.size())
                    throw std::runtime_error("ZI file has no block for "+hour_label(clock));
                mixing_height_m=zi_hours[offset];
            }
            // The DIAGI-built station column that INTER2 consumes is the one
            // the mixing height caps (calmet.for L6894 passes
            // zii=amax1(zimech,ziconv) to SIMILT, whose loop exits above it,
            // L30345). The WIND1 first guess is a different call: L36171 uses
            // zmo=zml=10000 (neutral, uncapped), so it keeps all nine levels.
            std::size_t levels_filled=0;
            if((!zi_hours.empty()||!zii_hours.empty())&&
               (!el_hours.empty()||!el_cell_hours.empty())){
                const std::size_t cell=std::size_t(ny/2)*std::size_t(nx)+
                                       std::size_t(nx/2);
                const std::size_t offset=h*std::size_t(nx)*std::size_t(ny)+cell;
                float el_m=0.f;
                if(!el_cell_hours.empty()){
                    if(h>=el_cell_hours.size())
                        throw std::runtime_error("EL cell file has no value for "+
                                                 hour_label(clock));
                    el_m=el_cell_hours[h];
                }else{
                    if(offset>=el_hours.size())
                        throw std::runtime_error("EL file has no block for "+
                                                 hour_label(clock));
                    el_m=el_hours[offset];
                }
                float cutoff_m=0.f;
                if(!zii_hours.empty()){
                    if(h>=zii_hours.size())
                        throw std::runtime_error("ZII file has no value for "+
                                                 hour_label(clock));
                    cutoff_m=zii_hours[h];
                }else{
                    if(offset>=zi_hours.size())
                        throw std::runtime_error("ZI file has no block for "+
                                                 hour_label(clock));
                    cutoff_m=zi_hours[offset];
                }
                const SimiltProfileInput diagi{
                    station_lat_deg,surface_anemometer_height_m,roughness,surface_u,surface_v,
                    el_m,cutoff_m,zimin_m,0,zface};
                const auto profile=original_similt_profile(diagi);
                levels_filled=profile.levels_filled;
                for(std::size_t k=0;k<9;++k)
                    diagi_surface_column[k]=k<levels_filled
                        ? LayerWind{profile.u_mps[k],profile.v_mps[k]}
                        : LayerWind{999.f,999.f};
            }else{
                // No certified EL/ZICONV: keep the neutral uncapped column and
                // record the gap instead of inventing stability.
                levels_filled=9;
                for(std::size_t k=0;k<9;++k)
                    diagi_surface_column[k]=station.surface_neutral_profile[k];
            }
            station.similt_levels_filled=levels_filled;
            station.mixing_height_m=mixing_height_m;
        }else if(icalm!=0){
            for(auto& wind:station.surface_neutral_profile)wind=LayerWind{0.f,0.f};
        }else{
            throw std::runtime_error(
                "calm surface wind with ICALM=0 at "+hour_label(clock));
        }
        if(hour.winds.size()!=9)
            throw std::runtime_error(
                "hourly upper profile is not nine layers at "+hour_label(clock));
        for(std::size_t k=0;k<9;++k)station.upper_observed_profile[k]=hour.winds[k];
        // Original PREPDI leaves the upper-air first level unset when
        // IEXTRP<=0 (`IF (IEXTRP .LE. 0) I1=2`, calmet.for L14005 and L14099);
        // the deck sets IEXTRP=-4, so level 1 carries the original missing
        // sentinel and is masked out of the first guess.
        if(iextrp<=0){
            station.upper_observed_profile[0]=LayerWind{999.f,999.f};
            settings_upper_layer_one_valid=false;
        }

        Wind1FirstGuessSelectedControls settings;
        settings.nx=nx;settings.ny=ny;settings.nz=nz;
        settings.grid_spacing_m=grid_m;
        settings.vertical_bias=bias;
        settings.icalm=icalm;settings.iextrp=iextrp;
        settings.surface_x_relative_m=surface_x_m;
        settings.surface_y_relative_m=surface_y_m;
        settings.upper_x_relative_m=upper_x_m;
        settings.upper_y_relative_m=upper_y_m;
        for(std::size_t k=0;k<9;++k)
            settings.upper_layer_valid[k]=true;
        if(!settings_upper_layer_one_valid)settings.upper_layer_valid[0]=false;
        const auto first=wind1_firstguess_selected(station,settings);
        write_f32(args.out()/("wind1_u_"+hour_label(clock)+".f32"),first.ug_mps);
        write_f32(args.out()/("wind1_v_"+hour_label(clock)+".f32"),first.vg_mps);
        // Diagnostic-only normalized WIND1 weights. They are never consumed
        // by P6D/P6E, and cannot modify any physical result.
        write_f32(args.out()/("wind1_rsqwt_surface_"+hour_label(clock)+".f32"),
                  first.rsq_surface);
        write_f32(args.out()/("wind1_rsqwt_upper_"+hour_label(clock)+".f32"),
                  first.rsq_upper);
        write_f32(args.out()/("wind1_vvw_surface1_"+hour_label(clock)+".f32"),
                  first.vvw_surface1);
        write_f32(args.out()/("wind1_vvw_upper1_"+hour_label(clock)+".f32"),
                  first.vvw_upper1);
        write_f32(args.out()/("wind1_pre_vvw_surface1_"+hour_label(clock)+".f32"),
                  first.pre_vvw_surface1);
        write_f32(args.out()/("wind1_pre_vvw_upper1_"+hour_label(clock)+".f32"),
                  first.pre_vvw_upper1);
        write_f32(args.out()/("wind1_vvw_before_surface1_"+hour_label(clock)+".f32"),
                  first.vvw_surface_before1);
        write_f32(args.out()/("wind1_vvw_before_upper1_"+hour_label(clock)+".f32"),
                  first.vvw_upper_before1);
        // Original INTER2 two-component blend on the step-one field, with the
        // case's own controls: WO=1.0 everywhere because IPROG=0 and the deck
        // supplies no WT.DAT (RDWT fills 1.0 for IPROG=0/2/4/14), RVARY off,
        // NINTR2=99 for every layer, and the observed station profiles.
        // Original upstream physics: SURFVAR builds the 2-D surface
        // temperature (DIAGNO L5609-L5610, ISURFT<0, IALL=0 returns the same
        // temp_k and drops RH/IPCODE), SOLAR builds the grid sine of the solar
        // elevation for the interval start, HEATFX turns both into the
        // sensible heat flux, and SLOPE adds the Mahrt slope flow to the
        // step-one winds before the L5748 boundary snapshot.
        cteas::p6e::SurfaceState surface_state;
        cteas::p6e::ObservedSurface observed_surface;
        {
            auto& observed=observed_surface;
            observed.nx=nx;observed.ny=ny;
            observed.station_temp_k=obs->temperature_k;
            observed.station_rh_percent=obs->humidity_pct;
            observed.npsta=0;observed.noobs=0;observed.itprog=0;
            observed.irhprog=0;observed.nowsta=0;
            observed.land_only=true;observed.average_temperature=true;  // IAVET=1
            observed.iall=0;                                            // DIAGNO L5610
            // AVETMP consumes the surface-level diagnostic wind field.
            observed.u_ms.assign(first.ug_mps.begin(),first.ug_mps.begin()+2500);
            observed.v_ms.assign(first.vg_mps.begin(),first.vg_mps.begin()+2500);
            observed.dgrid_m=grid_m;observed.mnmdav=1;observed.hafang_deg=30.f;
            // Original SURFVAR L12842-12871 performs wt*T/wt even for one
            // station. Skipping this is mathematically harmless but differs
            // by REAL*4 ULPs at some cells; stable ELUSTR amplifies them.
            // Coordinates and interpolation controls belong to the case,
            // never the fixed 50x50 geometry.
            observed.preserve_single_station_weight_rounding=true;
            observed.station_x_m=surface_x_m;
            observed.station_y_m=surface_y_m;
            observed.tradkm=required_deck_scalar(controls,"TRADKM");
            observed.irad=deck_int(controls,"IRAD",1);
            observed.numts=deck_int(controls,"NUMTS",5);
            if(!(std::isfinite(observed.station_temp_k)&&
                 observed.station_temp_k>0.f))
                throw std::runtime_error(
                    "surface temperature observation missing at "+hour_label(clock));
            surface_state=cteas::p6e::surfvar_one_station(observed);
        }
        // SOLAR takes the day of year (1..366) of the interval start.
        const int julian_day=[&]{
            const auto day=std::chrono::floor<std::chrono::days>(clock-
                std::chrono::hours(1));
            const std::chrono::year_month_day ymd{day};
            const std::chrono::sys_days first{ymd.year()/
                std::chrono::January/1};
            return static_cast<int>((day-first).count())+1;
        }();
        const int begin_hour=[&]{
            const auto day=std::chrono::floor<std::chrono::days>(clock-
                std::chrono::hours(1));
            return static_cast<int>(std::chrono::duration_cast<
                std::chrono::hours>(clock-std::chrono::hours(1)-day).count());
        }();
        const auto solar_grid=cteas::p6e::surface_solar_grid(
            static_cast<std::size_t>(nx),static_cast<std::size_t>(ny),50,
            origin_x_km*1000.0,origin_y_km*1000.0,grid_m);
        const auto sinalpc=cteas::p6e::sinalpc_grid(solar_grid,julian_day,
            begin_hour,0);
        // STHEOR -> ELUSTR2 (calmet.for L31152/L6580-L6894) precedes the
        // grid HEATFX/ELUSTR. The ORIGINAL uses raw observed anemometer U/V
        // at the station cell, not the gridded WIND1/DIAGNO level-one wind.
        // Keep this independently computed station physics distinct from
        // gridded ELUSTR so it can be checked against DGM point 6 for 143h.
        const int station_i=std::clamp(static_cast<int>(surface_x_m/grid_m),0,nx-1);
        const int station_j=std::clamp(static_cast<int>(surface_y_m/grid_m),0,ny-1);
        const std::size_t station_cell=static_cast<std::size_t>(station_j*nx+station_i);
        if(!obs->pressure_valid||!obs->cloud_valid)
            throw std::runtime_error("STHEOR missing surface density/cloud forcing at "+
                                     hour_label(clock));
        StationElustr2Input station_physics;
        station_physics.surface_u_mps=surface_u;
        station_physics.surface_v_mps=surface_v;
        station_physics.zmid1_m=center_m[0];
        station_physics.anemometer_m=surface_anemometer_height_m;
        station_physics.z0_m=geo.z0_m[station_cell];
        station_physics.solar_sine=sinalpc[station_cell];
        station_physics.temp_k=surface_state.temp_k[station_cell];
        station_physics.rho_kg_m3=
            0.3484321f*obs->pressure_mb/station_physics.temp_k;
        station_physics.cloud_tenths=obs->opaque_cloud_tenths;
        station_physics.ipsifcn=deck_int(controls,"IPSIFCN",0);
        station_physics.ha1=990.f;station_physics.ha2=-30.f;
        station_physics.hb1=-0.75f;station_physics.hb2=3.4f;
        station_physics.hc1=5.31e-13f;station_physics.hc2=60.f;
        station_physics.hc3p1=1.12f;
        station_physics.albedo=geo.albedo[station_cell];
        station_physics.bowen=geo.bowen[station_cell];
        station_physics.hcg=geo.hcg[station_cell];
        station_physics.qf=geo.qf[station_cell];
        const auto station_flux=station_elustr2_flux(station_physics);
        if(!station_flux.extrapolate)
            throw std::runtime_error("STHEOR station cannot be extrapolated due to calm/missing wind at "+
                                     hour_label(clock));
        station_elustr2_trace<<hour_label(clock)<<","<<std::setprecision(10)
            <<station_flux.sensible_wm2<<","
            <<station_flux.friction_velocity_mps<<","
            <<station_flux.monin_obukhov_m<<","
            <<station_physics.solar_sine<<","
            <<station_physics.temp_k<<","
            <<station_physics.rho_kg_m3<<","
            <<station_physics.z0_m<<","
            <<station_i+1<<","<<station_j+1<<"\n";
        // The native STHEOR EL is now available without a source-forced
        // EL oracle. ZII is *not* the previous grid ZI: the original calls
        // MIXHTST and mutates the DPTT history first. An explicit caller
        // station-ZII stream is diagnostic-only pending native MIXHTST
        // state reconstruction; never claim standalone U/V/W acceptance.
        if(args.native_setup_hour0||!args.comp_state_prefix.empty()){
            const std::size_t previous_offset=h==0?0:(h-1U)*std::size_t(nx*ny)+station_cell;
            StationMixhtstInput mix;
            mix.previous.zi_m=h==0?0.f:comp_zi[previous_offset];
            mix.previous.ziconv_m=h==0?0.f:comp_ziconv[previous_offset];
            mix.previous.dptt_k=h==0?0.f:comp_dptt[previous_offset];
            mix.qh_wm2=station_flux.sensible_wm2;
            mix.ustar_mps=station_flux.friction_velocity_mps;
            mix.el_m=station_flux.monin_obukhov_m;
            mix.rho_kg_m3=station_physics.rho_kg_m3;
            mix.zimin_m=zimin_m;
            mix.zimax_m=deck_scalar(controls,"ZIMAX",3000.f);
            mix.constn=deck_scalar(controls,"CONSTN",2400.f);
            mix.dptmin_kperm=deck_scalar(controls,"DPTMIN",0.001f);
            mix.dzzi_m=deck_scalar(controls,"DZZI",200.f);
            mix.threshl=deck_scalar(controls,"THRESHL",0.f);
            mix.tzicrlx_s=deck_scalar(controls,"TZICRLX",800.f);
            mix.imixh=deck_int(controls,"IMIXH",1);
            mix.izicrlx=deck_int(controls,"IZICRLX",1);
            mix.landuse=geo.landuse[station_cell];
            mix.water_first=geo.iwat1;
            mix.water_last=geo.iwat2;
            // ZIPARM user-prescribed Coriolis latitude-independent value for
            // the selected frozen Hefei case, identical to P6E COMP.
            float f=deck_scalar(controls,"FCORIOL",1.e-4f);
            if(f>998.f){
                constexpr float radians=0.0174533f;
                f=2.f*(6.2831853f/86400.f)*std::sin(radians*station_lat_deg);
            }
            mix.fcori_s=std::max(std::fabs(f),0.25e-4f);
            mix.cmech=deck_scalar(controls,"CONSTB",1.41f)/std::sqrt(mix.fcori_s);
            // The original MIXHTST selects the most recent earlier thermal
            // UP sounding as of the BEGINNING of the target model hour.
            const auto beginning=clock-std::chrono::hours{1};
            const UpperSounding* older=nullptr;
            for(const auto& sounding:upper.soundings){
                if(sounding.end<=beginning)older=&sounding;
                else break;
            }
            if(older==nullptr)
                throw std::runtime_error("MIXHTST missing previous thermal sounding");
            for(const auto& level:older->data){
                mix.older_sounding.height_m.push_back(level.height_lgl_m);
                mix.older_sounding.temp_k.push_back(level.temperature_valid?
                    level.temperature_k:9999.f);
            }
            const auto stage=station_mixhtst(mix);
            const SimiltProfileInput diagi{
                station_lat_deg,surface_anemometer_height_m,station_physics.z0_m,
                surface_u,surface_v,station_flux.monin_obukhov_m,
                stage.zii_to_similt_m,zimin_m,0,zface};
            const auto profile=original_similt_profile(diagi);
            station.similt_levels_filled=profile.levels_filled;
            station.mixing_height_m=stage.zii_to_similt_m;
            for(std::size_t k=0;k<9;++k)
                diagi_surface_column[k]=k<profile.levels_filled
                    ?LayerWind{profile.u_mps[k],profile.v_mps[k]}
                    :LayerWind{999.f,999.f};
            station_mixhtst_trace<<hour_label(clock)<<","<<std::setprecision(10)
                <<stage.zii_to_similt_m<<","<<stage.ziconv_after_m<<","
                <<stage.dptt_for_comp_k<<","<<mix.previous.zi_m<<","
                <<mix.previous.ziconv_m<<","<<mix.previous.dptt_k<<","
                <<station_flux.monin_obukhov_m<<","<<(args.native_setup_hour0?
                "original_setup_zero_initial_state":"native_p6e_comp_previous_hour")<<"\n";
        }
        // Forensic reference-ZII input is mutually exclusive with the
        // native COMP-produced ZII above. Never mix these two provenances.
        if(!zii_hours.empty() && el_hours.empty() && el_cell_hours.empty()){
            if(h>=zii_hours.size())
                throw std::runtime_error("STHEOR station ZII stream truncated");
            const SimiltProfileInput diagi{
                station_lat_deg,surface_anemometer_height_m,
                station_physics.z0_m,surface_u,surface_v,
                station_flux.monin_obukhov_m,zii_hours[h],zimin_m,0,zface};
            const auto profile=original_similt_profile(diagi);
            station.similt_levels_filled=profile.levels_filled;
            for(std::size_t k=0;k<9;++k)
                diagi_surface_column[k]=k<profile.levels_filled
                    ?LayerWind{profile.u_mps[k],profile.v_mps[k]}
                    :LayerWind{999.f,999.f};
        }
        std::vector<float> corrected_u=first.ug_mps,corrected_v=first.vg_mps;
        // Original DIAGNO MUST apply IFRADJ (L5643) before adding SLOPE
        // (L5722-L5732). These source-ordered stages are not commutative.
        // Original FRADJ (L5643-L5644) runs BEFORE SLOPE and is enabled only
        // when a gridded GAMMA is available. The real case derives GAMMA in
        // PREPDI via CGAMMA (calmet.for L3340-L3395), which consumes ZICONV;
        // until that array is wired in, GAMMA is caller-supplied and the stage
        // stays off so no unfounded correction is applied.
        bool fradj_applied=false;
        if(!args.gamma_dir.empty()){
            const fs::path gamma_file=args.gamma_dir/
                ("gamma_"+hour_label(clock)+".f32");
            std::ifstream gamma_in(gamma_file,std::ios::binary);
            if(!gamma_in)
                throw std::runtime_error("missing gridded GAMMA "+gamma_file.string());
            std::vector<float> gamma_grid(2500);
            gamma_in.read(reinterpret_cast<char*>(gamma_grid.data()),2500*4);
            if(!gamma_in)
                throw std::runtime_error("truncated gridded GAMMA "+gamma_file.string());
            const auto adjusted=froude_adjust(
                nx,ny,nz,grid_m,grid_m,geo.terrain_m,envelope.maximum_m,
                gamma_grid,surface_state.temp_k,-1,fradj_tinf_k,critfn,
                std::vector<float>(zface.begin(),zface.end()),
                WindUV{corrected_u,corrected_v});
            corrected_u=adjusted.u;corrected_v=adjusted.v;
            fradj_applied=true;
        }
        if(fradj_applied) {
            // Preserve BOTH original REAL*4 diagnostic wind components.
            // This only adds a forensic trace, it changes no physical arrays.
            write_f32(args.out()/("fradj_corrected_u_"+hour_label(clock)+".f32"),
                      corrected_u);
            write_f32(args.out()/("fradj_corrected_v_"+hour_label(clock)+".f32"),
                      corrected_v);
        }
        // Original DIAGNO calls SURFVAR twice for ISURFT<0, ISFCMET=0:
        //  L5609 initial WIND1 temperature for TOPOF2/FRADJ, then L5668
        //  post-FRADJ update for HEATFX -> AIRDEN -> ELUSTR -> SLOPE.
        // The original-source 143h IALL=0 trace confirms the first call's
        // U/V is byte-identical to WIND1, but 934 cells have different U/V
        // at the second call. Reusing the first TEMP2D causes 60 SLOPE-input
        // temperature exceedances even though AVETMP itself is bit identical
        // with equal inputs. Preserve the pre-FRADJ state for FRADJ above;
        // recompute only the temperature state for downstream physics.
        observed_surface.u_ms.assign(corrected_u.begin(),
                                     corrected_u.begin()+static_cast<std::size_t>(nx*ny));
        observed_surface.v_ms.assign(corrected_v.begin(),
                                     corrected_v.begin()+static_cast<std::size_t>(nx*ny));
        surface_state=cteas::p6e::surfvar_one_station(observed_surface);
        // CALMET DIAGNO L5686-5711: HEATFX/ELUSTR belong AFTER FRADJ.
        // QH is input to SLOPE, so this is not just a cosmetic move.
        std::vector<float> heat_flux;
        {
            cteas::p6e::HeatFluxInput flux;
            flux.nx=nx;flux.ny=ny;
            flux.mcloud=1;
            flux.water_first=geo.iwat1;flux.water_last=geo.iwat2;
            flux.ha1=990.f;flux.ha2=-30.f;flux.hb1=-0.75f;flux.hb2=3.4f;
            flux.hc1=5.31e-13f;flux.hc2=60.f;flux.hc3p1=1.12f;
            flux.station_cloud={obs->opaque_cloud_tenths};
            flux.nearest.assign(2500,1);
            flux.landuse=geo.landuse;
            flux.sun=sinalpc;
            flux.temp_k=surface_state.temp_k;
            flux.cloud_grid.assign(2500,0.1f*
                static_cast<float>(obs->opaque_cloud_tenths));
            flux.albedo=geo.albedo;
            flux.bowen=geo.bowen;
            flux.soil_heat_fraction=geo.hcg;
            flux.anthropogenic_wm2=geo.qf;
            flux.initial_qh.assign(2500,0.f);
            heat_flux=cteas::p6e::heatfx(flux).sensible_wm2;
            // Write-only forensic snapshot: HEATFX QH before grid ELUSTR
            // overwrites stable nighttime flux. No source/test oracle input.
            write_f32(args.out()/("qh_before_elustr_"+
                      hour_label(clock)+".f32"),heat_flux);
        }
        // Exact source order CALMET DIAGNO L5685-L5716:
        // HEATFX -> AIRDEN -> ELUSTR(UG,VG) -> SLOPE(QH).
        // HEATFX's -0.1 W/m2 nighttime marker MUST NOT be handed directly
        // to SLOPE; original ELUSTR overwrites QH with the stable sensible
        // flux (often tens of negative W/m2). The 143h original source
        // diagnostic located 223236 QH input mismatches before this repair.
        if(!obs->pressure_valid)
            throw std::runtime_error("DIAGNO ELUSTR missing surface pressure at "+
                                     hour_label(clock));
        constexpr std::size_t plane_cells=2500;
        std::vector<float> diag_rho(plane_cells,0.f);
        for(std::size_t cell=0;cell<plane_cells;++cell)
            diag_rho[cell]=0.3484321f*obs->pressure_mb/surface_state.temp_k[cell];
        std::vector<int> stable_land(plane_cells),day_land(plane_cells);
        for(std::size_t cell=0;cell<plane_cells;++cell){
            const int lu=geo.landuse[cell];
            const bool land=lu<geo.iwat1||lu>geo.iwat2;
            stable_land[cell]=(land&&heat_flux[cell]<0.f)?lu:geo.iwat1;
            day_land[cell]=(land&&heat_flux[cell]>=0.f)?lu:geo.iwat1;
        }
        cteas::p6e::StableElustr stable;
        stable.nx=nx;stable.ny=ny;stable.mcloud=1;
        stable.water_first=geo.iwat1;stable.water_last=geo.iwat2;
        stable.zm=center_m[0]; // original ZMID(1), not anemometer height
        stable.landuse=stable_land;
        stable.nearest.assign(plane_cells,1);
        stable.station_cloud={obs->opaque_cloud_tenths};
        stable.z0=geo.z0_m;
        stable.u1.assign(corrected_u.begin(),corrected_u.begin()+plane_cells);
        stable.v1.assign(corrected_v.begin(),corrected_v.begin()+plane_cells);
        stable.rho=diag_rho;stable.temp_k=surface_state.temp_k;
        stable.cloud_grid.assign(plane_cells,0.f);
        stable.heat_flux_initial=heat_flux;
        const auto stable_state=cteas::p6e::stable_elustr(stable);
        cteas::p6e::DaytimeElustrInput daytime;
        daytime.nx=nx;daytime.ny=ny;
        daytime.water_first=geo.iwat1;daytime.water_last=geo.iwat2;
        daytime.ipsifcn=deck_int(controls,"IPSIFCN",0);
        daytime.zm=center_m[0];daytime.landuse=day_land;
        daytime.z0=geo.z0_m;
        daytime.u1=stable.u1;daytime.v1=stable.v1;
        daytime.rho=diag_rho;daytime.temp_k=surface_state.temp_k;
        daytime.heat_flux_initial=heat_flux;
        daytime.initial_ustar.assign(plane_cells,0.05f);
        daytime.initial_el.assign(plane_cells,-9.9e9f);
        const auto daytime_state=cteas::p6e::elustr_daytime(daytime);
        for(std::size_t cell=0;cell<plane_cells;++cell){
            const int lu=geo.landuse[cell];
            if(lu>=geo.iwat1&&lu<=geo.iwat2)continue;
            heat_flux[cell]=heat_flux[cell]<0.f
                ?stable_state.qh_wm2[cell]:daytime_state.qh_wm2[cell];
        }
        // SLOPE now consumes the source-ordered *post-ELUSTR* QH field.
        // Original DIAGNO applies Mahrt slope flow after FRADJ.
        {
            SlopeInput slope;
            slope.nx=nx;slope.ny=ny;slope.nz=nz;
            slope.dx_m=grid_m;slope.dy_m=grid_m;
            slope.water_first=geo.iwat1;slope.water_last=geo.iwat2;
            slope.isurft=-1;
            slope.domain_temperature_k=285.f;  // unused for ISURFT<0
            slope.zface_m=std::vector<float>(zface.begin(),zface.end());
            slope.terrain_m=geo.terrain_m;slope.hmax_m=envelope.maximum_m;
            slope.hmin_m=envelope.minimum_m;
            slope.disthmax_m=envelope.distance_to_maximum_m;
            slope.disthmin_m=envelope.distance_to_minimum_m;
            slope.sensible_heat_w_m2=heat_flux;
            slope.surface_temperature_k=surface_state.temp_k;
            slope.landuse=geo.landuse;
            const auto flow=compute_original_slope_scoped(slope);
            for(std::size_t n=0;n<22500;++n){
                corrected_u[n]+=flow.u_mps[n];
                corrected_v[n]+=flow.v_mps[n];
            }
        }
        write_f32(args.out()/("slope_corrected_u_"+hour_label(clock)+".f32"),
                  corrected_u);
        write_f32(args.out()/("slope_corrected_v_"+hour_label(clock)+".f32"),
                  corrected_v);
        write_f32(args.out()/("temp2d_"+hour_label(clock)+".f32"),
                  surface_state.temp_k);
        write_f32(args.out()/("qh_"+hour_label(clock)+".f32"),heat_flux);
        std::vector<float> blended_u,blended_v;
        std::vector<float> station_values[2];
        std::vector<float> inter2_u,inter2_v;
        for(int component=0;component<2;++component){
            Inter2SelectedInput blend;
            blend.nx=nx;blend.ny=ny;blend.nz=nz;blend.nstations=2;
            blend.dx_m=grid_m;blend.dy_m=grid_m;
            blend.rmin_km=rmin_km;blend.rmax1_km=rmax1_km;
            blend.rmax2_km=rmax2_km;blend.rmax3_km=rmax3_km;
            blend.r1_km=r1_km;blend.r2_km=r2_km;
            blend.lvary=lvary;
            blend.iprog=0;blend.nbar=0;blend.noobs=0;
            blend.water_first=geo.iwat1;blend.water_last=geo.iwat2;
            // Source CALMET DIAGNO L5185-L5188: EDIT=999, EDITL=900.
            // IEXTRP<=0 upper level-1 missing uses this literal REAL*4
            // sentinel; both selected kernel distance sorting and masked
            // station values must follow that original contract.
            blend.edit=999.f;blend.editl=900.f;
            blend.nintrp_per_layer=nintrp;
            // Station order is the original STDAT1 station index: 1 = surface.
            blend.station_x_km={static_cast<float>(surface_x_km),
                                static_cast<float>(upper_x_km)};
            blend.station_y_km={static_cast<float>(surface_y_km),
                                static_cast<float>(upper_y_km)};
            blend.landuse=geo.landuse;
            blend.observation_weight.assign(22500,1.f);
            blend.station_component_mps.resize(18);
            for(std::size_t k=0;k<9;++k){
                const auto& surface_wind=diagi_surface_column[k];
                const auto& upper_wind=station.upper_observed_profile[k];
                // Original STDAT1(K,L) layout: level-major, station-minor.
                blend.station_component_mps[k*2]=component==0
                    ? surface_wind.u_mps:surface_wind.v_mps;
                blend.station_component_mps[k*2+1]=component==0
                    ? upper_wind.u_mps:upper_wind.v_mps;
            }
            blend.step1_mps=component==0?corrected_u:corrected_v;
            station_values[component]=blend.station_component_mps;
            const auto blended=original_inter2_selected(blend);
            if(component==0)blended_u=blended.component_mps;
            else blended_v=blended.component_mps;
            write_f32(args.out()/((component==0?"inter2_u_":"inter2_v_")+
                                  hour_label(clock)+".f32"),
                      blended.component_mps);
            if(component==0)inter2_u=blended.component_mps;
            else inter2_v=blended.component_mps;
        }
        // Snapshot the EXACT independent station values handed into INTER2.
        // Needed to isolate the 2022-01-01 hour-12 level-one first divergence.
        station_inter2_first<<hour_label(clock)<<","<<std::setprecision(10)
            <<station_values[0][0]<<","<<station_values[1][0]<<","
            <<station_values[0][1]<<","<<station_values[1][1]<<"\n";
        // CALMET original DIAGNO has TWO WINDBC snapshots:
        // (1) L5748 WINDBC(UG,VG) before INTER2;
        // (2) L6092-L6101: IF (HTFAC<=0) GOTO 285, otherwise
        //     WINDBC(U,V) AFTER INTER2 and BEFORE SMOOTH L6119.
        // Frozen GEO.DAT has HTFAC=1, so (2) OVERRIDES (1) for the
        // selected Hefei 2022 case. Use blended U/V to initialize UB/VB.
        // Previously keeping snapshot (1) forced DIVCEL against unrelated
        // lateral edges and amplified W to >100 m/s at upper levels.
        // No numerical tolerance or physical switch is altered here.
        {
            SmoothInput tail;
            tail.nx=nx;tail.ny=ny;tail.nz=nz;tail.lake_breeze=false;
            tail.passes_per_layer=nsmth;
            tail.u_mps=blended_u;tail.v_mps=blended_v;
            tail.ub_west_east_mps.assign(9*2*ny,0.f);
            tail.vb_south_north_mps.assign(9*2*nx,0.f);
            for(std::size_t k=0;k<9;++k)for(std::size_t j=0;j<static_cast<std::size_t>(ny);++j){
                tail.ub_west_east_mps[k*2*ny+j]=blended_u[k*2500+j*50];
                tail.ub_west_east_mps[k*2*ny+ny+j]=
                    blended_u[k*2500+j*50+49];
            }
            for(std::size_t k=0;k<9;++k)for(std::size_t i=0;i<static_cast<std::size_t>(nx);++i){
                tail.vb_south_north_mps[k*2*nx+i]=blended_v[k*2500+i];
                tail.vb_south_north_mps[k*2*nx+nx+i]=
                    blended_v[k*2500+49*50+i];
            }
            const auto final_fields=original_smooth_divcel_w(
                std::move(tail),grid_m,grid_m,thickness_m,false);
            write_f32(args.out()/("w_face_"+hour_label(clock)+".f32"),
                      final_fields.w_face_mps);
            // The DIAGNO product is the wind *after* SMOOTH and DIVCEL; the
            // INTER2 blend above is only the pre-tail stage, so the canonical
            // blend_* slot carries the closed field that downstream writers
            // (P6F write-from-p6d --variant blend) consume.
            write_f32(args.out()/("blend_u_"+hour_label(clock)+".f32"),
                      final_fields.u_mps);
            write_f32(args.out()/("blend_v_"+hour_label(clock)+".f32"),
                      final_fields.v_mps);
            // WINDBC (calmet.for L36404): lateral boundary values of the field
            // entering the tail, refreshed by the tail's own boundary pass.
            write_f32(args.out()/("windbc_ub_"+hour_label(clock)+".f32"),
                      final_fields.ub_west_east_mps);
            write_f32(args.out()/("windbc_vb_"+hour_label(clock)+".f32"),
                      final_fields.vb_south_north_mps);
        }
        if(!args.fixture_dir.empty()){
            // Driver fixture for the unchanged original WIND1/SIMILT, so the
            // step-one field can be compared numerically against the original.
            std::ofstream fixture(args.fixture_dir/
                ("wind1_driver_"+hour_label(clock)+".inp"));
            if(!fixture)throw std::runtime_error("cannot write WIND1 driver fixture");
            // Full precision: the driver consumes these positions verbatim, and
            // a rounded coordinate shifts the inverse-distance weights enough
            // to exceed the step-one tolerance.
            fixture<<std::setprecision(17)
                   <<surface_x_m<<" "<<surface_y_m<<" "
                   <<upper_x_m<<" "<<upper_y_m<<" "
                   <<surface_u<<" "<<surface_v<<" "<<roughness<<" "
                   <<station_lat_deg<<" "<<surface_anemometer_height_m<<" "<<icalm<<"\n";
            for(std::size_t k=0;k<9;++k)
                fixture<<bias[k]<<(k==8?"\n":" ");
            for(std::size_t k=0;k<9;++k)
                fixture<<station.upper_observed_profile[k].u_mps<<" "
                       <<station.upper_observed_profile[k].v_mps<<"\n";
            // Original INTER2 driver inputs for the same hour, so the blend can
            // be compared against the unchanged original subroutine.
            for(int component=0;component<2;++component){
                std::ofstream inter2(args.fixture_dir/
                    ((component==0?"inter2_u_":"inter2_v_")+
                     hour_label(clock)+".inp"));
                if(!inter2)throw std::runtime_error("cannot write INTER2 fixture");
                inter2<<"2 0 "<<rmin_km<<" "<<rmax1_km<<" "<<rmax2_km<<" "
                      <<rmax3_km<<" "<<r1_km<<" "<<r2_km<<" 999 900\n";
                for(std::size_t k=0;k<9;++k)
                    inter2<<nintrp[k]<<(k==8?"\n":" ");
                inter2<<std::setprecision(17)
                      <<static_cast<float>(surface_x_km)<<" "
                      <<static_cast<float>(upper_x_km)<<"\n";
                inter2<<static_cast<float>(surface_y_km)<<" "
                      <<static_cast<float>(upper_y_km)<<"\n";
                for(std::size_t row=0;row<50;++row){
                    for(std::size_t i=0;i<50;++i)
                        inter2<<geo.landuse[row*50+i]<<(i==49?"\n":" ");
                }
                // Original driver reads one row of two station values per level.
                for(std::size_t k=0;k<9;++k)
                    inter2<<station_values[component][k*2]<<" "
                          <<station_values[component][k*2+1]<<"\n";
                // Original driver reads the step-one field and the observation
                // weights level by level, one grid row per record.
                const std::vector<float>& guess=component==0?corrected_u:corrected_v;
                for(std::size_t k=0;k<9;++k)
                    for(std::size_t row=0;row<50;++row){
                        for(std::size_t i=0;i<50;++i)
                            inter2<<guess[k*2500+row*50+i]<<(i==49?"\n":" ");
                    }
                for(std::size_t k=0;k<9;++k)
                    for(std::size_t row=0;row<50;++row){
                        for(std::size_t i=0;i<50;++i)
                            inter2<<1.0f<<(i==49?"\n":" ");
                    }
            }
        }
        index<<hour_label(clock)<<"\n";
        similt_levels_min=std::min(similt_levels_min,station.similt_levels_filled);
        similt_levels_max=std::max(similt_levels_max,station.similt_levels_filled);
        ++written;
    }
    index.close();

    std::ostringstream meta;
    meta<<"{\n";
    meta<<"  \"product\": \"p6d_realcase_wind_fields\",\n";
    meta<<"  \"partial\": true,\n";
    meta<<"  \"status\": \"PARTIAL_WIND1_BLEND_SLOPE_TEMP2D_QH_TERSET\",\n";
    meta<<"  \"case_dir\": \""<<args.case_dir.string()<<"\",\n";
    meta<<"  \"grid\": {\"nx\": "<<nx<<", \"ny\": "<<ny<<", \"nz\": "<<nz
        <<", \"grid_spacing_m\": "<<grid_m
        <<", \"layout\": \"i_fastest\", \"layout_note\": \"index = i + nx*(j + ny*k), i fastest\""
        <<", \"dtype\": \"float32\", \"byte_order\": \"little\"},\n";
    meta<<"  \"levels\": {\"zface_m\": [";
    for(std::size_t k=0;k<10;++k)meta<<(k?", ":"")<<zface[k];
    meta<<"], \"thickness_m\": [";
    for(std::size_t k=0;k<9;++k)meta<<(k?", ":"")<<thickness_m[k];
    meta<<"], \"center_m\": [";
    for(std::size_t k=0;k<9;++k)meta<<(k?", ":"")<<center_m[k];
    meta<<"]},\n";
    meta<<"  \"units\": {\"wind1_u_*.f32\": \"m/s\", \"wind1_v_*.f32\": \"m/s\", \"blend_u_*.f32\": \"m/s (DIAGNO product: INTER2 blend then SMOOTH then DIVCEL)\", \"blend_v_*.f32\": \"m/s (DIAGNO product)\", \"inter2_u_*.f32\": \"m/s (INTER2 blend before the tail)\", \"inter2_v_*.f32\": \"m/s (INTER2 blend before the tail)\", \"windbc_ub_*.f32\": \"m/s (nz*2*ny: level-major, west then east column)\", \"windbc_vb_*.f32\": \"m/s (nz*2*nx: level-major, south then north row)\", \"w_face_*.f32\": \"m/s (10 faces: k=1 face is the surface, k=10 the domain top)\","
          " \"terset_hmax.f32\": \"m\", \"terset_hmin.f32\": \"m\","
          " \"terset_disthmax.f32\": \"m\", \"terset_disthmin.f32\": \"m\"},\n";
    meta<<"  \"missing_sentinel\": "<<MISSING<<",\n";
    meta<<"  \"similt_mixing_height\": {\"status\": \""<<(zi_hours.empty()?"MIXING_HEIGHT_NOT_SUPPLIED":"APPLIED_FROM_P6E_ZI")<<"\", "
          "\"source\": \""<<(zi_hours.empty()?"none":args.zi_file.string())<<"\", "
          "\"provenance\": \"ZI_SOURCE: P6E_CHAIN_INTERNAL_UNCALIBRATED (accuracy not certified)\", "
          "\"rule\": \"the DIAGI-built station column that INTER2 consumes is built by the stability-dependent SIMILT (EL from the surface fluxes) and capped at the mixing height: DIAGI passes zii=zi(is,js) (L6876/L6894) and SIMILT exits above it (L30319), so those levels are written as the INTER2 missing sentinel and the upper-air station alone feeds the blend; ZIMIN floors the cutoff. The WIND1 first guess is a different call (L36171, zmo=zml=10000, neutral and uncapped) and keeps all nine levels\", "
          "\"levels_filled_min\": "<<similt_levels_min<<", \"levels_filled_max\": "<<similt_levels_max<<", "
          "\"consequence_when_absent\": \"without ZI/EL the surface-station column stays the neutral uncapped profile, which dilutes the upper-air shear and drops the stability-dependent structure (measured at hour 1 against the frozen reference: level 9 was 0.716 m/s where the reference and the sounding give 2.464 and 1.017 m/s)\"},\n";
    meta<<"  \"iextrp_rmin2\": {\"IEXTRP\": "<<iextrp
        <<", \"level1_exclusion_applied\": "<<(iextrp<=0?"true":"false")
        <<", \"level1_exclusion_source\": \"PREPDI calmet.for L14099 IF (IEXTRP .LE. 0) I1=2; probe reference/probe_original_prepdi_iextrp_level1.py, literal block sha256 9dba46c137d7635bc53113a70d2b91c110bc897a5a43f563be43bc787d41d8e5\", "
          "\"effect_measured\": \"level 1 of the first-guess field changes by up to 0.45 m/s against a run without the exclusion while levels 2-9 stay bit-identical\", "
          "\"RMIN2\": \"-1.0 in the deck; original PREPDI L5831 skips a surface station only when FMIN < RMIN2, which cannot happen for a negative RMIN2, so with RMIN2=-1.0 no surface station is ever skipped. This case has one surface station, so the rule is satisfied but inert; multi-surface-station cases would need it modelled\"},\n";
    meta<<"  \"hourly_labels\": "<<written<<",\n";
    meta<<"  \"first_hour_zero_based\": "<<args.first_hour<<",\n";
    meta<<"  \"original_setup_zero_first_hour\": "<<(args.native_setup_hour0?"true":"false")<<",\n";
    meta<<"  \"hour_label\": \"END\", \"hour_label_note\": \"YYYY-MM-DD_HH in UTC; the label is the hourly interval end\",\n";
    meta<<"  \"surface_wind_speed_range_mps\": ["<<speed_min<<", "<<speed_max<<"],\n";
    meta<<"  \"blend\": {\"product\": \"blend_u_*.f32 / blend_v_*.f32 = the closed DIAGNO field (INTER2, SMOOTH, DIVCEL); the pre-tail INTER2 stage stays available as inter2_u/v_*.f32\", "
          "\"stage\": \"original INTER2 two-component blend on the step-one field\", "
          "\"observation_weight\": \"WO(i,j,k)=1.0 everywhere: RDWT fills 1.0 for IPROG=0/2/4/14 and the deck supplies no WT.DAT\", "
          "\"radii_km\": {\"RMIN\": "<<rmin_km<<", \"RMAX1\": "<<rmax1_km<<", \"RMAX2\": "<<rmax2_km<<", "
                        "\"RMAX3\": "<<rmax3_km<<", \"R1\": "<<r1_km<<", \"R2\": "<<r2_km<<"}, "
          "\"lvary\": "<<(lvary?"true":"false")<<", \"nintrp_per_layer\": 99, "
          "\"station_local_km\": ["<<surface_x_km<<", "<<surface_y_km<<"], "
          "\"station_local_km_source\": \"met.inp SS1/US1 UTM km, READCF REAL*4: 1000*xkm - (1000*xorigkm)\", "
          "\"station_profiles\": \"surface levels = neutral SIMILT profile, upper levels = hourly PREPDI profile\", "
          "\"verification\": \""<<(zi_hours.empty()
            ? "MIXING_HEIGHT_NOT_SUPPLIED_ALL_LEVELS_NEUTRAL_SIMILT: with no --zi/--el the DIAGI/INTER2 surface column is the uncapped neutral SIMILT at all nine levels, which is the measured cause of the height-growing error (against the frozen met.dat: U-LEV 9 13.5074 and U-LEV 8 10.0186 worst over 143 hours, both FAIL)"
            : "PENDING_REALCASE_REVALIDATION_AFTER_METINP_STATION_GEOMETRY_FIX: supersedes prior results obtained with the branch-local equirectangular projection")
            <<"\"},\n";
    meta<<"  \"inter2\": {\"product\": \"inter2_u/v_*.f32 = the pre-tail INTER2 stage\", "
          "\"verification\": \"PENDING_REALCASE_REVALIDATION_AFTER_METINP_STATION_GEOMETRY_FIX: standalone INTER2 kernel equivalence is separately evidenced, while actual-case geometry has changed\"},\n";
    meta<<"  \"stages_applied_in_chain\": [";
    meta<<"\"WIND1 selected first guess (IEXTRP=-4 neutral SIMILT)\"";
    meta<<", \"SURFVAR 2-D surface temperature (ISURFT<0, IALL=0, IAVET=1)\"";
    meta<<", \"SOLAR grid sine of elevation (interval start)\"";
    meta<<", \"HEATFX sensible heat flux (mcloud=1 station cloud)\"";
    meta<<", \"AIRDEN then ELUSTR stable/daytime updates QH before SLOPE\"";
    meta<<", \"SLOPE slope flow added to the step-one winds\"";
    meta<<", \"SIMILT vertical extrapolation capped at the mixing height (L30345)\" ";
    meta<<", \"original INTER2 two-component blend (WO=1.0)\" " ;
    meta<<", \"DIAGNO SMOOTH (1-2-1, deck NSMTH passes per layer)\" ";
    meta<<", \"DIAGNO DIVCEL (no-divergence projection with the WINDBC boundaries)\" ";
    meta<<", \"DIAGNO W integration and boundary refresh\" ";
    meta<<", \"WINDBC lateral boundary extraction (L36404, boundaries of the field entering the tail)\" ";
    meta<<", \"TERSET envelope (DIAGI L5228, TERRAD="<<terrad_km<<" km)\"],\n";
    meta<<"  \"stages_not_applied\": [\n";
    meta<<"    {\"stage\": \"SURFVAR -> TEMP2D (DIAGNO L5609-L5610)\", \"status\": \"APPLIED\","
          " \"product\": \"temp2d_*.f32\","
          " \"note\": \"surfvar_one_station with iall=0 (same temp_k, RH/IPCODE dropped) and average_temperature=1 (IAVET=1)\"},\n";
    meta<<"    {\"stage\": \"HEATFX -> QH (DIAGNO L5676-L5715)\", \"status\": \"APPLIED\","
          " \"product\": \"qh_*.f32\","
          " \"note\": \"mcloud=1 uses the station cloud amount (0 tenths for every case hour); coefficients from met.lst (ha1=990, ha2=-30, hb1=-0.75, hb2=3.4, hc1=5.31e-13, hc2=60, hc3+1=1.12)\"},\n";
    meta<<"    {\"stage\": \"SLOPE (L5722-L5723)\", \"status\": \"APPLIED\","
          " \"product\": \"slope_corrected_u/v_*.f32\","
          " \"note\": \"chain-computed QH, TEMP2D and TERSET envelope; the corrected step one feeds the blend and the W tail\"},";
    meta<<"\n";
    meta<<"    {\"stage\": \"FRADJ (L5643-L5644)\", \"status\": \""<<(args.gamma_dir.empty()?"PENDING_GAMMA":"APPLIED_WITH_CALLER_GAMMA")<<"\","
          " \"gamma_source\": \""<<(args.gamma_dir.empty()?"none":args.gamma_dir.string())<<"\","
          " \"missing_when_pending\": [\"GAMMA grid: the real case derives it in PREPDI via CGAMMA (calmet.for L3340-L3395) whose convective branch consumes ZICONV; P6E E29 exports that array as <prefix>.ziconv.f32 with the accuracy caveat GAMMA_SOURCE: P6E_CHAIN_INTERNAL_UNCALIBRATED\"],"
          " \"numerical_impact_measured\": \"none on this domain: HMAX is the domain-wide 59.5 m (TERRAD=15 km over a 5 km domain), the largest OBSHGT at level 1 is 24.5 m, and FROUDE for a 3 m/s wind is 5.14 against CRITFN=1.0, so the original FRADJ cannot adjust any cell (126 m of OBSHGT would be needed); enabling the switch with a 0.006 K/m GAMMA changes the corrected fields by 0.0 m/s\","
          " \"note\": \"W faces are SLOPE-compensated" << (args.gamma_dir.empty()
             ? " but not FRADJ-compensated (GAMMA pending)"
             : " and FRADJ-compensated with a caller-supplied GAMMA whose accuracy is not verified here") << "\"},\n";
    meta<<"    {\"stage\": \"SMOOTH/DIVCEL/W tail (DIAGNO L6119-L6148)\", \"status\": \"APPLIED_SLOPE_COMPENSATED_FRADJ_PENDING\","
          " \"product\": \"w_face_*.f32 (10 faces per column)\","
          " \"note\": \"run on the SLOPE-corrected blended field with the deck NSMTH, so the boundaries are the L5748 snapshot except for the still-pending FRADJ (GAMMA) correction\"},\n";
    meta<<"    {\"stage\": \"TOPOF2/IKINE route and O'Brien/IOBR=1 tail\", \"status\": \"NON_CASE_PATH\","
          " \"note\": \"the case deck sets IKINE=0 and IOBR=0\"}\n";
    meta<<"  ],\n";
    meta<<"  \"control_values_read\": {\"TERRAD\": "<<terrad_km
        <<", \"XORIGKM\": "<<origin_x_km<<", \"YORIGKM\": "<<origin_y_km
        <<", \"IEXTRP\": "<<iextrp<<", \"ICALM\": "<<icalm
        <<", \"DGRIDKM\": "<<(grid_m/1000.f)<<"},\n";
    meta<<"  \"inputs\": {\"deck\": \""<<args.deck.string()<<"\", \"deck_fingerprint\": \""
        <<sha256_short(args.deck)<<"\", \"geo\": \""<<args.geo.string()
        <<"\", \"geo_fingerprint\": \""<<sha256_short(args.geo)
        <<"\", \"surface\": \""<<args.surface.string()<<"\", \"surface_fingerprint\": \""
        <<sha256_short(args.surface)<<"\", \"upper\": \""<<args.upper.string()
        <<"\", \"upper_fingerprint\": \""<<sha256_short(args.upper)<<"\"},\n";
    meta<<"  \"stations\": {\"surface_station_id\": "<<surface.station_id
        <<", \"upper_station_id\": "<<upper.station_id
        <<", \"written\": "<<stations_written<<"},\n";
    meta<<"  \"upper_soundings\": "<<upper.soundings.size()<<"\n";
    meta<<"}\n";
    std::ofstream metadata(args.out()/"metadata.json");
    if(!metadata)throw std::runtime_error("cannot write metadata.json");
    metadata<<meta.str();
    std::cout<<"P6D_REALCASE_WIND_PARTIAL hours="<<written
             <<" out="<<args.out().string()<<"\n";
    return 0;
 }catch(const std::exception& e){
    std::cerr<<"realcase-wind failed: "<<e.what()<<'\n';
    return 1;
 }
}