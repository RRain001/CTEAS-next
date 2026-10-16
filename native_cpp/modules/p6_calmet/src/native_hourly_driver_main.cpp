// CALMET Hefei 2022 native C++ hourly process coordinator (transition stage).
// This preserves the source-accepted P6D/P6E kernels without altering physics.
// File-backed process adapters must later become in-memory native step calls.
// A successful invocation does NOT imply 45-field original scientific parity.
#include "cteas/p6f/sha256.hpp"
#include "cteas/p6/native_comp_history.hpp"
#include <cerrno>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <regex>
#include <stdexcept>
#include <string>
#include <vector>
#if defined(__unix__) || defined(__APPLE__)
#include <fcntl.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace fs=std::filesystem;
namespace {
constexpr const char* kMetHash="b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30";
struct Options {
    fs::path source, p6d, p6e, cgamma, bridge, work, p6f_writer, p6e_source_builder;
    int hours=6;
    bool emit_source_stage_trace=false;
    bool p6f_direct_hourly=false;
};
std::string str(const fs::path& p){return p.string();}
void require(const fs::path& p) {
    if(!fs::is_regular_file(p))throw std::runtime_error("missing file: "+str(p));
}
std::string read(const fs::path& p){
    require(p);std::ifstream in(p,std::ios::binary);
    return {std::istreambuf_iterator<char>(in),std::istreambuf_iterator<char>()};
}
void write(const fs::path& p,const std::string& body){
    std::ofstream out(p,std::ios::binary|std::ios::trunc);
    if(!out||!(out<<body))throw std::runtime_error("write failed: "+str(p));
}
Options parse(int argc,char** argv) {
    Options o;
    for(int i=1;i<argc;++i) {
        const std::string flag=argv[i];
        if(flag=="--emit-source-stage-trace"){o.emit_source_stage_trace=true;continue;}
        if(flag=="--p6f-direct-hourly"){o.p6f_direct_hourly=true;continue;}
        if(++i==argc)throw std::invalid_argument("missing argument "+flag);
        const std::string v=argv[i];
        if(flag=="--case")o.source=v;
        else if(flag=="--p6d")o.p6d=v;
        else if(flag=="--p6e")o.p6e=v;
        else if(flag=="--cgamma")o.cgamma=v;
        else if(flag=="--bridge")o.bridge=v;
        else if(flag=="--work")o.work=v;
        else if(flag=="--p6f-writer")o.p6f_writer=v;
        else if(flag=="--p6e-source-builder")o.p6e_source_builder=v;
        else if(flag=="--hours")o.hours=std::stoi(v);
        else throw std::invalid_argument("unknown argument "+flag);
    }
    if(o.source.empty()||o.p6d.empty()||o.p6e.empty()||
       o.cgamma.empty()||o.bridge.empty()||o.work.empty())
        throw std::invalid_argument("--case --p6d --p6e --cgamma --bridge --work required");
    if(o.hours<1||o.hours>143)throw std::invalid_argument("hours must be 1..143");
    if(o.emit_source_stage_trace&&o.hours!=143)
        throw std::invalid_argument("stage trace requires all 143 hours");
    o.source=fs::absolute(o.source).lexically_normal();
    o.p6d=fs::absolute(o.p6d).lexically_normal();
    o.p6e=fs::absolute(o.p6e).lexically_normal();
    o.cgamma=fs::absolute(o.cgamma).lexically_normal();
    o.bridge=fs::absolute(o.bridge).lexically_normal();
    o.work=fs::absolute(o.work).lexically_normal();
    if(!o.p6f_writer.empty()) {
        if(o.hours!=143)
            throw std::invalid_argument("independent P6F native header requires complete 143h source run");
        o.p6f_writer=fs::absolute(o.p6f_writer).lexically_normal();
    }
    if(!o.p6e_source_builder.empty())
        o.p6e_source_builder=fs::absolute(o.p6e_source_builder).lexically_normal();
    if(o.p6f_direct_hourly &&
       (o.p6f_writer.empty()||o.p6e_source_builder.empty()))
        throw std::invalid_argument("--p6f-direct-hourly requires "
             "--p6f-writer and --p6e-source-builder (GEO/deck only)");
    if(fs::exists(o.work)&&!fs::is_empty(o.work))
        throw std::invalid_argument("work directory not empty: "+str(o.work));
    return o;
}
void run(const std::vector<std::string>& args,const fs::path& log){
#if defined(__unix__) || defined(__APPLE__)
    const pid_t pid=fork();
    if(pid<0)throw std::runtime_error("fork failed");
    if(pid==0){
        const int fd=open(log.c_str(),O_CREAT|O_WRONLY|O_TRUNC,0644);
        if(fd<0||dup2(fd,STDOUT_FILENO)<0||dup2(fd,STDERR_FILENO)<0)_exit(126);
        close(fd);
        std::vector<char*> a;
        for(const auto& s:args)a.push_back(const_cast<char*>(s.c_str()));
        a.push_back(nullptr);
        execv(a[0],a.data());
        _exit(127);
    }
    int code=0;pid_t waited=-1;
    do{waited=waitpid(pid,&code,0);}while(waited<0&&errno==EINTR);
    if(waited!=pid||!WIFEXITED(code)||WEXITSTATUS(code)!=0)
        throw std::runtime_error("child failed: "+str(log));
#else
    (void)args;(void)log;
    throw std::runtime_error("POSIX process adapter unavailable");
#endif
}
std::vector<std::string> lines(const std::string& text) {
    std::vector<std::string> values;std::string current;
    for(char c:text){
        if(c!='\n'){current+=c;continue;}
        if(!current.empty()&&current.back()=='\r')current.pop_back();
        values.push_back(current);current.clear();
    }
    if(!current.empty()){
        if(current.back()=='\r')current.pop_back();
        values.push_back(current);
    }
    return values;
}
std::string join(const std::vector<std::string>& list){
    std::string out;for(const auto& s:list)out+=s+"\n";return out;
}
std::string hour_dir(int hour){
    return "hour_"+(hour<10?std::string("00"):hour<100?std::string("0"):std::string(""))+
        std::to_string(hour);
}
} // namespace
int main(int argc,char** argv){
    try{
        const auto o=parse(argc,argv);
        const auto met=o.source/"run/met/met.dat";
        const auto surf=o.source/"met/surface/final/surf.dat";
        const auto upper=o.source/"met/upperair/final/up_58424.dat";
        const auto geo=o.source/"geo/makegeo/geo.dat";
        for(const auto& f:{surf,upper,geo,o.p6d,o.p6e,o.bridge,o.cgamma})require(f);
        if(!o.p6e_source_builder.empty()) {
            // Genuine source-only P6E metadata mode must succeed even when
            // the original Fortran CALMET.DAT is physically absent. This
            // permits a stronger negative-provenance acceptance test.
        } else {
            require(met);
            if(cteas::p6f::sha256_hex_file(str(met))!=kMetHash)
                throw std::runtime_error("locked original CALMET.DAT SHA256 mismatch");
        }
        if(!o.p6f_writer.empty())require(o.p6f_writer);
        if(!o.p6e_source_builder.empty())require(o.p6e_source_builder);
        if(!o.p6f_writer.empty()||!o.p6e_source_builder.empty())
            require(o.source/"run/met/met.inp");
        fs::create_directories(o.work);
        const auto observations=o.work/"observations.csv";
        run({str(o.bridge),str(surf),str(upper),"58424",str(observations)},o.work/"bridge.log");
        require(observations);
        // Optional source-independent P6E *metadata* input. All hourly 45
        // fields are XMISS in this file. The P6E native-hour mode must supply
        // every live value from native P6D + P6E and the P4/P5 observation bridge.
        // No CALMET.DAT read is required in this branch; all P6D selected
        // model inputs come from deck, GEO, surface and upper-air originals.
        // This does NOT assert wider CALMET configuration portability.
        fs::path p6e_metadata=met;
        if(!o.p6e_source_builder.empty()) {
            p6e_metadata=o.work/"p6e_geo_deck_metadata_only.dat";
            run({str(o.p6e_source_builder),"--geo",str(geo),
                 "--deck",str(o.source/"run/met/met.inp"),"--out",
                 str(p6e_metadata)},o.work/"p6e_source_metadata.log");
            require(p6e_metadata);
        }
        const auto history=o.work/"history/comp";
        cteas::calmet::p6::NativeCompHistory history_owner(history);
        std::vector<std::string> hourly_files,station_lines,stage_rows;
        const fs::path stage_root=o.work/"native_source_stage_143h";
        if(o.emit_source_stage_trace)fs::create_directories(stage_root);
        for(int hour=0;hour<o.hours;++hour){
            const auto dir=o.work/hour_dir(hour),diagno=dir/"diagno",gamma=dir/"gamma";
            fs::create_directories(diagno);fs::create_directories(gamma);
            run({str(o.cgamma),"--up",str(upper),"--p6e-state-prefix",str(history),
                 "--out",str(gamma),"--station-id","58424","--zupt","200",
                 "--upper-i","25","--upper-j","26","--causal-hours",
                 std::to_string(hour+1)},dir/"cgamma.log");
            std::size_t count=0;
            for(const auto& item:fs::directory_iterator(gamma))
                if(item.is_regular_file()&&item.path().extension()==".f32"&&
                   item.path().filename().string().starts_with("gamma_"))++count;
            if(count!=1)throw std::runtime_error("CGAMMA must emit one current-hour plane");
            std::vector<std::string> d={str(o.p6d),"--case",str(o.source),
                "--first-hour",std::to_string(hour),"--hours","1",
                "--out",str(diagno),"--gamma",str(gamma)};
            if(hour==0)d.push_back("--native-setup-hour0");
            else{d.push_back("--comp-state-prefix");d.push_back(str(history));}
            run(d,dir/"p6d.log");
            const auto flux=lines(read(diagno/"station_elustr2.csv"));
            if(flux.size()!=2)throw std::runtime_error("station flux not one-hour");
            if(station_lines.empty())station_lines.push_back(flux[0]);
            else if(station_lines[0]!=flux[0])
                throw std::runtime_error("station flux header changed");
            station_lines.push_back(flux[1]);
            const auto comp=dir/"comp",hour_met=dir/"met_native_1h.dat";
            std::vector<std::string> e={str(o.p6e),"emit-realcase",
                "--reference",str(p6e_metadata),"--observations",str(observations),
                "--geo-file",str(geo),"--native-hour-comp","1",
                "--native-p6d-dir",str(diagno),"--station-flux-csv",
                str(diagno/"station_elustr2.csv"),"--first-hour",std::to_string(hour),
                "--hours","1","--state-prefix",str(comp),"--out",str(hour_met),
                "--report",str(dir/"comp_report.json")};
            if(hour>0){
                e.push_back("--previous-comp-prefix");
                e.push_back(str(o.work/hour_dir(hour-1)/"comp"));
            }
            run(e,dir/"p6e.log");
            // Do not expose a new COMP hour until the complete hour's
            // output and optional diagnostic traces have been verified.
            require(hour_met);
            hourly_files.push_back(str(hour_met));
            if(o.emit_source_stage_trace){
                auto label=read(diagno/"produced_hours.txt");
                label=label.substr(0,label.find_first_of("\r\n\t "));
                if(label.empty())throw std::runtime_error("missing stage-trace hour label");
                for(const char* prefix:{"fradj_corrected_u","fradj_corrected_v",
                                       "wind1_u","wind1_v","slope_corrected_u",
                                       "slope_corrected_v","inter2_u","inter2_v"}){
                    const auto source=diagno/(std::string(prefix)+"_"+label+".f32");
                    require(source);
                    if(fs::file_size(source)!=9U*50U*50U*sizeof(float))
                        throw std::runtime_error("wrong stage-trace float32 shape: "+str(source));
                    fs::copy_file(source,stage_root/source.filename());
                }
                const auto station_profile=diagno/("wind1_neutral_profile_"+label+".f32");
                require(station_profile);
                if(fs::file_size(station_profile)!=18U*sizeof(float))
                    throw std::runtime_error("wrong WIND1 neutral profile REAL4 shape");
                fs::copy_file(station_profile,stage_root/station_profile.filename());
                const auto row=lines(read(diagno/"station_inter2_layer1.csv"));
                if(row.size()!=2)throw std::runtime_error("station INTER2 row malformed");
                if(stage_rows.empty())stage_rows.push_back(row[0]);
                else if(stage_rows[0]!=row[0])
                    throw std::runtime_error("station INTER2 header changed");
                stage_rows.push_back(row[1]);
            }
            history_owner.commit(static_cast<std::size_t>(hour),comp);
        }
        const auto station=o.work/"native_station_flux.csv";
        write(station,join(station_lines));
        if(o.emit_source_stage_trace)
            write(stage_root/"station_inter2_layer1.csv",join(stage_rows));
        const auto manifest=o.work/"native_hourly_files.txt";
        write(manifest,join(hourly_files));
        const auto output=o.work/"native_causal_calmet.dat";
        run({str(o.p6e),"merge-native-hours","--manifest",str(manifest),
             "--out",str(output)},o.work/"writer.log");
        require(output);
        if(fs::file_size(output)<1000000U)
            throw std::runtime_error("merged native 45-field file incomplete");
        // Optional selected-case P6F production handoff. Preserve the frozen
        // "native_causal_calmet.dat" output byte for byte for the G3/G4 and
        // Python-vs-C++ gates. Independently rebuild the OUTHD header and all
        // GEO/deck-derived statics; carry *only* this native hourly payload
        // into the second output (never substitute original meteorology).
        // Upstream P6E still uses a pinned original met.dat envelope and is
        // not yet reference-independent. These are distinct acceptance gates.
        const bool native_header=!o.p6f_writer.empty();
        std::string header_digest;
        if(native_header) {
            const auto independent=o.work/"native_causal_independent_header_calmet.dat";
            std::vector<std::string> writer={
                str(o.p6f_writer),"--geo",str(geo),
                "--deck",str(o.source/"run/met/met.inp")};
            if(o.p6f_direct_hourly) {
                writer.insert(writer.end(),{"--source-metadata",str(p6e_metadata),
                                            "--hour-manifest",str(manifest)});
            } else {
                writer.insert(writer.end(),{"--candidate",str(output)});
            }
            writer.insert(writer.end(),{"--emit-native-header",str(independent)});
            run(writer,o.work/"p6f-native-header.log");
            require(independent);
            if(fs::file_size(independent)<1000000U)
                throw std::runtime_error("independent P6F native header output incomplete");
            header_digest=cteas::p6f::sha256_hex_file(str(independent));
        }
        const auto digest=cteas::p6f::sha256_hex_file(str(output));
        std::string report="{\n  \"status\": \"PASS_CPP_PROCESS_COORDINATOR_EXECUTION\",\n"
            "  \"hours_completed\": "+std::to_string(o.hours)+",\n"
            "  \"native_wind\": true,\n  \"native_previous_hour_comp_state\": true,\n"
            "  \"original_met_role\": \""+
                std::string(o.p6e_source_builder.empty()?
                    "ORIGINAL_LOCKED_CASE_METADATA_INPUT":
                    "NOT_REQUIRED_NOT_OPENED_BY_NATIVE_EXECUTION")+"\",\n"
            "  \"p6e_reference_is_geo_deck_metadata_only\": "+
                 std::string(o.p6e_source_builder.empty()?"false":"true")+",\n"
            "  \"in_process_kernel_adapter\": false,\n"
            "  \"comp_history_owner\": \"NativeCompHistory\",\n"
            "  \"independent_p6f_source_header_written\": "+std::string(native_header?"true":"false")+",\n"
            "  \"p6f_header_from_native_hour_manifest\": "+
                 std::string(o.p6f_direct_hourly?"true":"false")+",\n"
            "  \"independent_p6f_header_sha256\": \""+header_digest+"\",\n"
            "  \"scientific_45_field_pass\": false,\n"
            "  \"native_calmet_dat_sha256\": \""+digest+"\"\n}\n";
        write(o.work/"native_cpp_hourly_manifest.json",report);
        std::cout<<report;
        return 0;
    }catch(const std::exception& error){
        std::cerr<<"FAIL_CPP_HOURLY_COORDINATOR: "<<error.what()<<'\n';
        return 3;
    }
}
