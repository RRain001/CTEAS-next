// Reconstructed native CALMET 6.5.0 CGAMMA -> 50x50 FRADJ forcing.
// Narrow interface: the one-upper-air-station 2022 Hefei case, not generic
// multi-station IUPT interpolation. Never read original CALMET GAMMA.
// The C++ P6E MIXHT state export is the physically required convective
// height at the PREVIOUS hour: COMP -> PREPDI(CGAMMA) precedes DIAGNO/MIXHT.
// This is a coupling component, NOT self-consistent P6D/P6E convergence.
#include "cteas/p6/cgamma.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs=std::filesystem;
using namespace cteas::calmet::p6;
namespace {
constexpr std::size_t kNx=50,kNy=50,kCells=kNx*kNy,kHours=143;
static_assert(sizeof(float)==4);
static_assert(std::endian::native==std::endian::little,
              "CGAMMA REAL*4 binary bridge expects little-endian");

struct Args {
    fs::path up,p6e_prefix,out;
    int station_id=58424;
    int upper_i=0,upper_j=0;
    float zupt_m=0.f;
    int causal_hours=0; // 1..143: consume only preceding COMP hours
};
std::string next_arg(int& n,int argc,char** argv) {
    if(n+1>=argc)throw std::invalid_argument(
        "CGAMMA bridge flag missing value: "+std::string(argv[n]));
    return argv[++n];
}
Args parse(int argc,char** argv) {
    Args a;
    for(int n=1;n<argc;++n) {
        const std::string flag=argv[n];
        if(flag=="--up")a.up=next_arg(n,argc,argv);
        else if(flag=="--p6e-state-prefix")a.p6e_prefix=next_arg(n,argc,argv);
        else if(flag=="--out")a.out=next_arg(n,argc,argv);
        else if(flag=="--zupt")a.zupt_m=std::stof(next_arg(n,argc,argv));
        else if(flag=="--upper-i")a.upper_i=std::stoi(next_arg(n,argc,argv));
        else if(flag=="--upper-j")a.upper_j=std::stoi(next_arg(n,argc,argv));
        else if(flag=="--station-id")a.station_id=std::stoi(next_arg(n,argc,argv));
        else if(flag=="--causal-hours")a.causal_hours=std::stoi(next_arg(n,argc,argv));
        else throw std::invalid_argument("CGAMMA bridge unknown flag "+flag);
    }
    if(a.up.empty()||a.p6e_prefix.empty()||a.out.empty()||
       !std::isfinite(a.zupt_m)||a.zupt_m<=0.f||
       a.upper_i<1||a.upper_i>static_cast<int>(kNx)||
       a.upper_j<1||a.upper_j>static_cast<int>(kNy)||
       a.station_id<=0||a.causal_hours<0||a.causal_hours>143)
        throw std::invalid_argument(
            "CGAMMA bridge requires --up --p6e-state-prefix --out "
            "--zupt (m) --upper-i 1..50 --upper-j 1..50");
    return a;
}
std::string read_text(const fs::path& path) {
    std::ifstream f(path);
    if(!f)throw std::runtime_error("no P6E state metadata "+path.string());
    std::ostringstream s;s<<f.rdbuf();
    return s.str();
}
void verify_p6e_metadata(const fs::path& path) {
    const std::string s=read_text(path);
    if(s.find("\"producer\": \"p6e_calmet_dat21 emit-realcase\"")==std::string::npos||
       s.find("\"source\": \"chain-internal MIXHT state advanced hour by hour")==
           std::string::npos||
       s.find("\"dtype\": \"float32 little-endian\"")==std::string::npos||
       s.find("\"layout\": \"hour-major")==std::string::npos||
       !std::regex_search(s,std::regex(R"("shape"\s*:\s*\[\s*143\s*,\s*50\s*,\s*50\s*\])"))||
       s.find("\"values_per_file\": 357500")==std::string::npos)
        throw std::runtime_error(
            "P6E state manifest is not the validated 143 x 50 x 50 MIXHT "
            "internal-state export, or could be a source/original substitution");
}
std::vector<float> read_ziconv(const fs::path& file,std::size_t available_hours=kHours) {
    if(available_hours==0)return {};
    if(!fs::is_regular_file(file)||fs::file_size(file)!=available_hours*kCells*4)
        throw std::runtime_error("P6E native ZICONV history length invalid for causal hour");
    std::ifstream f(file,std::ios::binary);
    if(!f)throw std::runtime_error("P6E native ZICONV unavailable");
    std::vector<float> z(available_hours*kCells);
    f.read(reinterpret_cast<char*>(z.data()),
           static_cast<std::streamsize>(z.size()*sizeof(float)));
    if(!f)throw std::runtime_error("P6E native ZICONV truncated");
    return z;
}
std::string hour_label(std::chrono::sys_seconds when) {
    const auto day=std::chrono::floor<std::chrono::days>(when);
    const std::chrono::year_month_day ymd(day);
    const int h=static_cast<int>(std::chrono::duration_cast<std::chrono::hours>(
        when-day).count());
    std::ostringstream s;
    s<<static_cast<int>(ymd.year())<<"-"<<std::setfill('0')<<std::setw(2)
     <<static_cast<unsigned>(ymd.month())<<"-"<<std::setw(2)
     <<static_cast<unsigned>(ymd.day())<<"_"<<std::setw(2)<<h;
    return s.str();
}
void write_gamma_plane(const fs::path& path,float value) {
    std::ofstream f(path,std::ios::binary|std::ios::trunc);
    if(!f)throw std::runtime_error("cannot write CGAMMA grid "+path.string());
    const std::array<float,kCells> g=[&]{
        std::array<float,kCells> a{};
        a.fill(value);
        return a;
    }();
    f.write(reinterpret_cast<const char*>(g.data()),
            static_cast<std::streamsize>(g.size()*sizeof(float)));
    if(!f)throw std::runtime_error("cannot finish CGAMMA "+path.string());
}
}
int main(int argc,char** argv) {
 try {
    const Args a=parse(argc,argv);
    if(a.causal_hours==0)
        verify_p6e_metadata(a.p6e_prefix.string()+".state.json");
    else if(a.causal_hours>1) {
        const auto m=read_text(a.p6e_prefix.string()+".state.json");
        const std::string clock="\"first_hour_zero_based\": "+
                                std::to_string(a.causal_hours-2);
        if(m.find("\"producer\": \"p6e_calmet_dat21 emit-realcase\"")==
             std::string::npos||m.find(clock)==std::string::npos||
           m.find("\"dtype\": \"float32 little-endian\"")==std::string::npos)
            throw std::runtime_error("CGAMMA causal P6E state producer/previous-hour mismatch");
    }
    const auto z=read_ziconv(a.p6e_prefix.string()+".ziconv.f32",
                             a.causal_hours>0?
                                static_cast<std::size_t>(a.causal_hours-1):kHours);
    const auto upper=read_upper_2022(a.up,a.station_id);
    // The case's actual ZFACE layers. This is the selected fixed 2022 grid;
    // do not reuse the bridge for a different met.inp without revalidation.
    const std::vector<float> faces{0.f,20.f,40.f,80.f,160.f,320.f,
                                   640.f,1200.f,2000.f,3000.f};
    const auto hours=comp_selected_2022_hours(upper,faces);
    if(hours.size()!=kHours)
        throw std::runtime_error("CGAMMA original buffered timeline != 143h");
    const std::size_t station_cell=
        (static_cast<std::size_t>(a.upper_j)-1)*kNx+
        static_cast<std::size_t>(a.upper_i)-1;
    fs::create_directories(a.out);
    CGammaState state;
    std::array<std::size_t,3> branches{};
    float minimum=std::numeric_limits<float>::infinity();
    float maximum=-std::numeric_limits<float>::infinity();
    std::ofstream table(a.out/"native_cgamma_143h.csv");
    if(!table)throw std::runtime_error("CGAMMA CSV manifest unavailable");
    table<<"hour_index,hour_end,prior_p6e_ziconv_m,native_gamma_kpm,branch\n";
    table<<std::setprecision(10);
    const auto requested=a.causal_hours>0?
        static_cast<std::size_t>(a.causal_hours):kHours;
    for(std::size_t h=0;h<requested;++h) {
        // hour 1 uses native CALMET initial ZICONV=0; hour h>1 consumes
        // P6E's post-MIXHT/AVEMIX hour h-1 state. Never use future data.
        const float entering=h==0?0.f:z[(h-1)*kCells+station_cell];
        if(!std::isfinite(entering)||entering<0.f||entering>=9999.f)
            throw std::runtime_error("CGAMMA invalid previous-hour native ZICONV");
        const auto value=state.calculate(upper,hours[h],a.zupt_m,entering);
        if(!std::isfinite(value.kelvin_per_m)||
           std::abs(value.kelvin_per_m)>0.1f||
           value.branch<0||value.branch>=static_cast<int>(branches.size()))
            throw std::runtime_error("CGAMMA nonphysical lapse/branch");
        ++branches[static_cast<std::size_t>(value.branch)];
        minimum=std::min(minimum,value.kelvin_per_m);
        maximum=std::max(maximum,value.kelvin_per_m);
        const std::string label=hour_label(hours[h].interpolated.end);
        // Causal mode emits only the current hour; no future PREPDI data.
        if(a.causal_hours==0||h+1==requested)
            write_gamma_plane(a.out/("gamma_"+label+".f32"),value.kelvin_per_m);
        table<<h+1<<','<<label<<','<<entering<<','
             <<value.kelvin_per_m<<','<<value.branch<<'\n';
    }
    if(!table)throw std::runtime_error("CGAMMA CSV incomplete");
    std::ofstream report(a.out/"native_cgamma_manifest.json");
    if(!report)throw std::runtime_error("CGAMMA manifest write failed");
    report<<"{\n"
          <<"  \"status\": \"NATIVE_CGAMMA_P6E_ZICONV_143H_BRIDGE\",\n"
          <<"  \"upstream\": \"P6E native MIXHT + AVEMIX previous-hour ZICONV, NOT original GAMMA\",\n"
          <<"  \"scope\": \"one upper-air station, original buffered PREPDI, 143h, FRADJ GAMMA field only; requires independent P6D/P6E coupling numerical acceptance\",\n"
          <<"  \"original_reference_injected\": false,\n"
          <<"  \"current_hour_leakage\": false,\n"
          <<"  \"first_hour_initial_ziconv_m\": 0.0,\n"
          <<"  \"hours\": "<<requested<<", \"nx\": 50, \"ny\": 50,\n"
          <<"  \"station_cell_i\": "<<a.upper_i<<", \"station_cell_j\": "<<a.upper_j<<",\n"
          <<"  \"zupt_m\": "<<a.zupt_m<<",\n"
          <<"  \"minimum_gamma_kpm\": "<<minimum
          <<", \"maximum_gamma_kpm\": "<<maximum<<",\n"
          <<"  \"branch_counts\": ["<<branches[0]<<", "<<branches[1]<<", "<<branches[2]<<"]\n"
          <<"}\n";
    if(!report)throw std::runtime_error("CGAMMA manifest truncated");
    std::cout<<"P6D_NATIVE_CGAMMA_P6E_ZICONV_143H_BRIDGE=PASS; "
             <<"P6D_FULL=NOT_ACCEPTED\n";
    return 0;
 }catch(const std::exception& e) {
    std::cerr<<"P6D_NATIVE_CGAMMA_BRIDGE_ERROR: "<<e.what()<<'\n';
    return 1;
 }
}
