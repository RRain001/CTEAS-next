#include "cteas/puff/native_p6_admission.hpp"
#include "cteas/puff/sha256.hpp"
#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <regex>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::puff {
namespace {
namespace fs = std::filesystem;
void insist(bool ok,const char* code) {
    if(!ok)throw std::runtime_error(code);
}
std::string file_text(const std::string& p) {
    std::ifstream in(p,std::ios::binary);
    insist(static_cast<bool>(in),"P7_P6_ADMISSION_MISSING");
    return {std::istreambuf_iterator<char>(in),std::istreambuf_iterator<char>()};
}
std::string json_string(const std::string& text,const std::string& key) {
    const std::regex re("\""+key+"\"\\s*:\\s*\"([^\"]*)\"");
    const std::vector<std::sregex_iterator> hits{
        std::sregex_iterator(text.begin(),text.end(),re),std::sregex_iterator()};
    insist(hits.size()==1U,"P7_P6_PRODUCER_MANIFEST_SCHEMA");
    return (*hits[0])[1].str();
}
bool json_bool(const std::string& text,const std::string& key) {
    const std::regex re("\""+key+"\"\\s*:\\s*(true|false)");
    const std::vector<std::sregex_iterator> hits{
        std::sregex_iterator(text.begin(),text.end(),re),std::sregex_iterator()};
    insist(hits.size()==1U,"P7_P6_PRODUCER_MANIFEST_SCHEMA");
    return (*hits[0])[1].str()=="true";
}
int json_int(const std::string& text,const std::string& key) {
    const std::regex re("\""+key+"\"\\s*:\\s*([0-9]+)");
    const std::vector<std::sregex_iterator> hits{
        std::sregex_iterator(text.begin(),text.end(),re),std::sregex_iterator()};
    insist(hits.size()==1U,"P7_P6_PRODUCER_MANIFEST_SCHEMA");
    return std::stoi((*hits[0])[1].str());
}
bool digest(const std::string& value) {
    return value.size()==64U &&
        std::all_of(value.begin(),value.end(),[](unsigned char c){
            return std::isdigit(c)!=0||(c>='a'&&c<='f');
        });
}
bool git_sha(const std::string& value) {
    return value.size()==40U &&
        std::all_of(value.begin(),value.end(),[](unsigned char c){
            return std::isdigit(c)!=0||(c>='a'&&c<='f');
        });
}
std::map<std::string,std::string> strict_admission(const std::string& source) {
    insist(source.size()<4096U,"P7_P6_ADMISSION_TOO_LARGE");
    const auto first=source.find('\n');
    insist(first!=std::string::npos &&
           source.substr(0,first)=="CTEAS_NATIVE_P6_TO_P7_V1",
           "P7_P6_ADMISSION_SCHEMA");
    std::map<std::string,std::string> values;
    std::size_t pos=first+1U;
    while(pos<source.size()) {
        const auto end=source.find('\n',pos);
        insist(end!=std::string::npos,"P7_P6_ADMISSION_SCHEMA");
        const std::string line=source.substr(pos,end-pos);
        const auto equal=line.find('=');
        insist(equal!=std::string::npos&&equal>0&&equal+1<line.size() &&
               line.find('=',equal+1)==std::string::npos,
               "P7_P6_ADMISSION_SCHEMA");
        insist(values.emplace(line.substr(0,equal),line.substr(equal+1)).second,
               "P7_P6_ADMISSION_DUPLICATE_FIELD");
        pos=end+1U;
    }
    insist(values.size()==9U &&
           values.count("case_id")&&values.count("source_sha")&&
           values.count("hours")&&values.count("xrefkm")&&
           values.count("yrefkm")&&values.count("met_sha256")&&
           values.count("manifest_sha256")&&values.count("p6_driver_sha256")&&
           values.count("manifest_independent_sha256"),
           "P7_P6_ADMISSION_FIELDS");
    return values;
}
void real_file(const std::string& path) {
    const fs::path p(path);
    insist(!fs::is_symlink(p)&&fs::is_regular_file(p),
           "P7_P6_INPUT_MISSING_OR_SYMLINK");
}
} // namespace

void verify_native_p6_admission(const std::string& evidence_file,
                                const std::string& p6_manifest,
                                const std::string& p6_driver,
                                const std::string& met_file,
                                const std::string& source_sha,
                                int requested_hours) {
    real_file(evidence_file);
    real_file(p6_manifest);
    real_file(p6_driver);
    real_file(met_file);
    const auto record=strict_admission(file_text(evidence_file));
    auto get=[&record](const char* key)->const std::string& {return record.at(key);};
    insist(git_sha(source_sha)&&get("source_sha")==source_sha,
           "P7_P6_SOURCE_HEAD_MISMATCH");
    insist(get("case_id")=="hefei5km_2022_reference_case_20261011" &&
           get("xrefkm")=="510.885"&&get("yrefkm")=="3531.269",
           "P7_P6_CANONICAL_ORIGIN_OR_CASE_MISMATCH");
    insist(get("hours")=="143"&&requested_hours==143,
           "P7_P6_ADMISSION_REQUIRES_FULL_143H");
    insist(digest(get("met_sha256"))&&
           digest(get("manifest_sha256"))&&
           digest(get("p6_driver_sha256"))&&
           digest(get("manifest_independent_sha256")),
           "P7_P6_DIGEST_SYNTAX");
    insist(sha256_hex_file(met_file)==get("met_sha256"),
           "P7_P6_MET_SHA256_MISMATCH");
    insist(sha256_hex_file(p6_manifest)==get("manifest_sha256"),
           "P7_P6_MANIFEST_SHA256_MISMATCH");
    insist(sha256_hex_file(p6_driver)==get("p6_driver_sha256"),
           "P7_P6_PRODUCER_BINARY_SHA256_MISMATCH");
    const auto original=file_text(p6_manifest);
    insist(original.size()<32768U,"P7_P6_PRODUCER_MANIFEST_TOO_LARGE");
    insist(json_string(original,"status")=="PASS_CPP_PROCESS_COORDINATOR_EXECUTION" &&
           json_int(original,"hours_completed")==143 &&
           json_bool(original,"native_wind") &&
           json_bool(original,"native_previous_hour_comp_state") &&
           json_bool(original,"p6e_reference_is_geo_deck_metadata_only") &&
           json_bool(original,"p6f_header_from_native_hour_manifest") &&
           json_string(original,"original_met_role")==
             "NOT_REQUIRED_NOT_OPENED_BY_NATIVE_EXECUTION",
           "P7_P6_PRODUCER_STATUS_REJECTED");
    insist(json_string(original,"independent_p6f_header_sha256")==
           get("manifest_independent_sha256") &&
           get("manifest_independent_sha256")==get("met_sha256"),
           "P7_P6_PRODUCER_MET_BINDING_MISMATCH");
}
} // namespace cteas::puff
