// Issue #53 P2-D3 GLCC-only historical 38-class LU.DAT writer.
// This does not authorize GLC_FCS30D crosswalk or perform P3/MAKEGEO science.
#include "cteas/geo/glcc_raw_fractions.hpp"
#include "cteas/geo/grid_origin.hpp"
#include <cpl_json.h>
#include <openssl/evp.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
namespace fs=std::filesystem;
constexpr const char* kGlccSha="4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a";
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
std::string sha256(const fs::path& input){
  std::ifstream f(input,std::ios::binary);
  require(bool(f),"D3_CSV_MISSING");
  std::unique_ptr<EVP_MD_CTX,decltype(&EVP_MD_CTX_free)> c(EVP_MD_CTX_new(),EVP_MD_CTX_free);
  require(bool(c)&&EVP_DigestInit_ex(c.get(),EVP_sha256(),nullptr)==1,"D3_SHA_INIT");
  std::array<char,65536> b{};
  while(f){f.read(b.data(),std::streamsize(b.size()));const auto n=f.gcount();
    if(n)require(EVP_DigestUpdate(c.get(),b.data(),std::size_t(n))==1,"D3_SHA_UPDATE");}
  require(f.eof(),"D3_SHA_READ_ERROR");
  unsigned char d[EVP_MAX_MD_SIZE]{};unsigned int len=0;
  require(EVP_DigestFinal_ex(c.get(),d,&len)==1&&len==32,"D3_SHA_FINAL");
  const char* hex="0123456789abcdef";std::string s;
  for(unsigned int i=0;i<len;++i){s+=hex[d[i]>>4];s+=hex[d[i]&15];}return s;
}
std::vector<std::string> csv(const std::string& s){
  std::istringstream in(s);std::string part;std::vector<std::string> out;
  while(std::getline(in,part,','))out.push_back(part);
  if(!s.empty()&&s.back()==',')out.emplace_back();
  return out;
}
int number(const std::string& s){
  require(!s.empty(),"D3_EMPTY_INT");
  std::size_t used=0;const long long value=std::stoll(s,&used,10);
  require(used==s.size()&&value>=0&&value<=100000000,"D3_BAD_INT");
  return static_cast<int>(value);
}
double real(const std::string& s){
  require(!s.empty(),"D3_EMPTY_DOUBLE");
  std::size_t used=0;const double x=std::stod(s,&used);
  require(used==s.size()&&std::isfinite(x),"D3_BAD_DOUBLE");
  return x;
}
std::string round3(double x){
  std::ostringstream f;f<<std::fixed<<std::setprecision(3)<<x;return f.str();
}
std::string required(const CPLJSONObject& m,const char* key){
  require(m.GetType()!=CPLJSONObject::Type::Unknown,"D3_MANIFEST_INVALID");
  const auto obj=m.GetObj(key);
  require(obj.IsValid()&&obj.GetType()==CPLJSONObject::Type::String,"D3_MANIFEST_STRING_MISSING");
  return obj.ToString();
}
int positive_integer(const CPLJSONObject& m,const char* key){
  const auto obj=m.GetObj(key);
  require(obj.IsValid()&&obj.GetType()==CPLJSONObject::Type::Integer,"D3_MANIFEST_INT_MISSING");
  const int n=obj.ToInteger();
  require(n>0,"D3_MANIFEST_INT_NONPOSITIVE");return n;
}
std::string header(int zone,bool north,int nx,int ny,const std::string& x0,const std::string& y0,double dkm){
  std::ostringstream o;
  o<<std::left<<std::setw(16)<<"LU.DAT"<<std::setw(16)<<"2.1"
   <<"Coordinate parameters and LandUse categories\n"
   <<"   2\n"
   <<"Produced by CTEAS native P2 GLCC GEN-replay D3 (not original Fortran)\n"
   <<"D1 real-source GEN scoped; original direct GLAZAS science NOT_RUN\n"
   <<"FRACTION\nUTM\n  "<<zone<<(north?"N":"S")<<"\nWGS-84  02-21-2003\n"
   <<std::right<<std::setw(8)<<nx<<std::setw(8)<<ny
   <<std::fixed<<std::setprecision(3)
   <<std::setw(12)<<cteas::reconstruction::geo::three_decimal_origin_km(x0)
   <<std::setw(12)<<cteas::reconstruction::geo::three_decimal_origin_km(y0)
   <<std::setw(12)<<dkm<<std::setw(12)<<dkm<<std::setw(6)<<38<<"\nKM  M\n";
  for(int cat:cteas::reconstruction::geo::kGlccUsgs92Classes)o<<std::setw(6)<<cat;
  o<<"\n";
  return o.str();
}
} // namespace
int main(int argc,char** argv){
  if(argc!=4){std::cerr<<"usage: cteas_p2_glcc_lu_dat VERIFIED_D1_MANIFEST D1_CSV NEW_OUTPUT_DIR\n";return 2;}
  try{
    using namespace cteas::reconstruction::geo;
    const fs::path mp=argv[1],cp=argv[2],dest=argv[3];
    require(!fs::is_symlink(fs::symlink_status(mp))&&!fs::is_symlink(fs::symlink_status(cp)),
            "D3_INPUT_SYMLINK");
    require(fs::is_regular_file(mp)&&fs::is_regular_file(cp),"D3_INPUT_FILE_REQUIRED");
    require(!fs::exists(dest)&&!fs::is_symlink(fs::symlink_status(dest)),"D3_OUTPUT_EXISTS");
    CPLJSONDocument doc;require(doc.Load(mp.string()),"D3_MANIFEST_PARSE");
    const auto m=doc.GetRoot();
    require(required(m,"producer")=="cteas_p2_glcc_raw","D3_REJECT_UNAPPROVED_GLC_OR_PRODUCER");
    require(required(m,"source_sha256")==kGlccSha,"D3_SOURCE_SHA_NOT_OFFICIAL");
    require(positive_integer(m,"source_size_bytes")==156000000,"D3_NOT_ORIGINAL_156MB");
    const auto method=required(m,"method");
    require(method=="GLCC_HEADERLESS_ROW_DIRECT_GEN_7DP_REAL4_REPLAY"||
            method=="GLCC_HEADERLESS_LAEA_DIRECT_UTM50N_REAL4_GLOBE_LUGRID",
            "D3_UNEXPECTED_METHOD");
    // This original-GLAZAS-matched production method was validated only
    // for the specified UTM50N transform; refuse unreviewed zones.
    if(method=="GLCC_HEADERLESS_LAEA_DIRECT_UTM50N_REAL4_GLOBE_LUGRID")
      require(positive_integer(m,"utm_epsg")==32650,"D3_DIRECT_SCOPE_UTM50N_ONLY");
    require(required(m,"evidence_status")=="PRODUCED_UNVERIFIED","D3_MANIFEST_STATUS_INCONSISTENT");
    require(required(m,"official_GLAZAS_parity")=="NOT_RUN","D3_SCIENCE_STATUS_NOT_INFERRED");
    require(required(m,"lu_dat")=="NOT_RUN"&&required(m,"p3_geo_dat")=="NOT_RUN",
            "D3_UPSTREAM_CLAIMS_INVALID");
    const auto expected=required(m,"fractions_csv_sha256");
    require(expected.size()==64&&sha256(cp)==expected,"D3_CSV_SHA_MISMATCH");
    const int epsg=positive_integer(m,"utm_epsg");
    require((epsg>=32601&&epsg<=32660)||(epsg>=32701&&epsg<=32760),"D3_NOT_WGS84_UTM");
    const int nx=positive_integer(m,"nx"),ny=positive_integer(m,"ny");
    require(nx<=20000&&ny<=20000&&std::int64_t(nx)*ny<=250000,"D3_GRID_BUDGET");
    const auto x0=required(m,"xrefkm"),y0=required(m,"yrefkm");
    (void)three_decimal_origin_km(x0);(void)three_decimal_origin_km(y0);
    const auto dfield=m.GetObj("dgridkm");
    require(dfield.IsValid(),"D3_MISSING_GRID_SPACING");
    const double dkm=dfield.ToDouble();
    require(std::isfinite(dkm)&&dkm>=.001&&dkm<=100.&&
            std::abs(dkm*1000.-std::round(dkm*1000.))<1e-7,"D3_UNREPRESENTABLE_GRID_SPACING");
    const std::string h=header(epsg%100,epsg<=32660,nx,ny,x0,y0,dkm);
    std::ifstream csv_input(cp);require(bool(csv_input),"D3_CSV_OPEN");
    std::string line;
    require(bool(std::getline(csv_input,line)),"D3_CSV_HEADER_MISSING");
    std::ostringstream required_header;required_header<<"i,j,samples";
    for(int cat:kGlccUsgs92Classes)required_header<<",cat"<<cat;
    require(line==required_header.str(),"D3_38_CLASS_ORDER_MISMATCH");
    fs::create_directory(dest);
    try{
      std::ofstream output(dest/"lu.dat",std::ios::binary);
      require(bool(output),"D3_LU_CREATE");
      output<<h;
      std::uint64_t total_samples=0;
      double largest_sum_error=0.;
      for(std::int64_t n=0;n<std::int64_t(nx)*ny;++n){
        require(bool(std::getline(csv_input,line)),"D3_TRUNCATED_CSV");
        const auto row=csv(line);
        require(row.size()==41,"D3_CSV_WIDTH");
        require(number(row[0])==n%nx+1&&number(row[1])==n/nx+1,"D3_CSV_CELL_ORDER");
        const int samples=number(row[2]);
        require(samples>0,"D3_EMPTY_GLCC_GRID_CELL");
        total_samples+=std::uint64_t(samples);
        std::array<std::string,38> values{};
        double sum=0.,display_sum=0.;
        for(int k=0;k<38;++k){
          const double v=real(row[3+k]);
          require(v>=0.&&v<=1.,"D3_BAD_CLASS_FRACTION");
          values[std::size_t(k)]=round3(v);
          sum+=v;display_sum+=real(values[std::size_t(k)]);
        }
        largest_sum_error=std::max(largest_sum_error,std::abs(sum-1.));
        require(std::abs(sum-1.)<1e-8,"D3_RAW_FRACTION_NOT_CONSERVED");
        require(display_sum>=.98&&display_sum<=1.02,"D3_PRINTED_FRACTION_NOT_CONSERVED");
        output<<std::right<<std::setw(5)<<n%nx+1<<std::setw(5)<<n/nx+1;
        for(const auto& value:values)output<<" "<<std::setw(5)<<value;
        output<<"   .\n";
      }
      require(!std::getline(csv_input,line),"D3_EXTRA_CSV_ROWS");
      require(csv_input.eof()&&bool(output),"D3_OUTPUT_OR_CSV_IO_FAILURE");
      output.close();require(bool(output),"D3_LU_CLOSE_FAILED");
      const auto lu_sha=sha256(dest/"lu.dat");
      std::ofstream attest(dest/"p2_d3_manifest.json");
      require(bool(attest),"D3_ATTEST_CREATE");
      attest<<"{\n"
            <<"  \"producer\": \"cteas_p2_glcc_lu_dat\",\n"
            <<"  \"source_kind\": \"P2_A_GLCC_HISTORICAL_24_TO_USGS92_38\",\n"
            <<"  \"source_sha256\": \""<<kGlccSha<<"\",\n"
            <<"  \"input_d1_csv_sha256\": \""<<expected<<"\",\n"
            <<"  \"input_d1_method\": \""<<method<<"\",\n"
            <<"  \"lu_dat_sha256\": \""<<lu_sha<<"\",\n"
            <<"  \"rows\": "<<std::int64_t(nx)*ny<<", \"classes\": 38,\n"
            <<"  \"total_samples\": "<<total_samples<<",\n"
            <<"  \"max_raw_fraction_sum_error\": "<<std::setprecision(17)<<largest_sum_error<<",\n"
            <<"  \"evidence_status\": \"PRODUCED_UNVERIFIED\",\n"
            <<"  \"real_source_gen_replay_ci\": \""
            <<(method=="GLCC_HEADERLESS_ROW_DIRECT_GEN_7DP_REAL4_REPLAY"
                ?"SEE_MANUAL_ACTIONS_RUN_39115417375"
                :"NOT_APPLICABLE_DIRECT_LAEA_METHOD")<<"\",\n"
            <<"  \"original_GLAZAS_parity\": \"NOT_RUN\",\n"
            <<"  \"glc_fcs30d_crosswalk\": \"P2_MAPPING_REVIEW_REQUIRED\",\n"
            <<"  \"p3_geo_dat\": \"NOT_RUN\",\n"
            <<"  \"case_grid_time_B1_attestation\": \"NOT_RUN\"\n}\n";
      attest.close();require(bool(attest),"D3_ATTEST_CLOSE");
      std::cout<<"D3_GLCC_LU_DAT=PRODUCED_UNVERIFIED ROWS="<<std::int64_t(nx)*ny
               <<" INCLUDED="<<total_samples<<" GLAZAS=NOT_RUN P3=NOT_RUN\n";
    }catch(...){fs::remove_all(dest);throw;}
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
