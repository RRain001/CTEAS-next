// #160 C4 modern GLC_FCS30D POINT HITS producer: never area intersect.
#include "cteas/geo/p2c_glc30m_sampling.hpp"
#include "cteas/geo/ctgproc_original_sampling_lu_writer.hpp"
#include "cteas/geo/glcc_raw_fractions.hpp"
#include "cteas/geo/grid_origin.hpp"
#include <openssl/evp.h>
#include <array>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
namespace {
namespace fs=std::filesystem;
using namespace cteas::reconstruction::geo;
constexpr const char* kWolsongSha="2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711";
constexpr const char* kOriginalBlnSha="67da93d441e7defe3eb46627ed9ce896c0a91ffd89fd5e4363d834d8108e11f9";
void need(bool b,const char* why){if(!b)throw std::runtime_error(why);}
std::string hash(const fs::path& p){
  std::ifstream f(p,std::ios::binary);
  need(bool(f),"P2C_SOURCE_FILE_MISSING");
  std::unique_ptr<EVP_MD_CTX,decltype(&EVP_MD_CTX_free)> ctx(EVP_MD_CTX_new(),EVP_MD_CTX_free);
  need(bool(ctx)&&EVP_DigestInit_ex(ctx.get(),EVP_sha256(),nullptr)==1,"P2C_SHA_INIT");
  std::array<char,65536> bytes{};
  while(f){
    f.read(bytes.data(),std::streamsize(bytes.size()));
    if(f.gcount()) need(EVP_DigestUpdate(ctx.get(),bytes.data(),std::size_t(f.gcount()))==1,
                      "P2C_SHA_UPDATE");
  }
  need(f.eof(),"P2C_SHA_READ");
  unsigned char digest[EVP_MAX_MD_SIZE]{};unsigned size=0;
  need(EVP_DigestFinal_ex(ctx.get(),digest,&size)==1&&size==32,"P2C_SHA_FINAL");
  std::string out;
  constexpr const char* hex="0123456789abcdef";
  for(unsigned i=0;i<32;++i){out+=hex[digest[i]>>4];out+=hex[digest[i]&15];}
  return out;
}
std::size_t positive_int(const char* raw,const char* label) {
  const std::string s=raw;
  std::size_t v=0;
  const auto [end,ec]=std::from_chars(s.data(),s.data()+s.size(),v);
  need(ec==std::errc{}&&end==s.data()+s.size()&&v>0,label);
  return v;
}
double spacing_metres(const char* raw) {
  const std::string s=raw;
  std::size_t consumed=0;
  const double d=std::stod(s,&consumed)*1000.;
  need(consumed==s.size()&&std::isfinite(d)&&d>=1.&&d<=50000.&&
       std::abs(d-std::round(d))<1e-7,"P2C_DYNAMIC_SPACING_MUST_BE_INTEGER_METRES");
  return d;
}
void source(const fs::path& p,const std::string& expected) {
  need(!fs::is_symlink(fs::symlink_status(p))&&fs::is_regular_file(p),
       "P2C_INPUT_SYMLINK_OR_MISSING");
  need(expected.size()==64,"P2C_EXPECTED_HASH_FORMAT");
  for(char c:expected)
    need((c>='0'&&c<='9')||(c>='a'&&c<='f'),"P2C_EXPECTED_HASH_LOWERCASE");
  need(hash(p)==expected,"P2C_ACTUAL_SOURCE_SHA_MISMATCH");
}
}
int main(int argc,char** argv){
  const bool dynamic=argc==15&&std::string(argv[1])=="--case-grid";
  if(argc!=7&&!dynamic){
    std::cerr<<"usage (frozen): cteas_p2c_glc30m_sampling inland|wolsong SOURCE_30M.TIF SOURCE_SHA256 USER_POLICY_JSON ORIGINAL_FULL_L1_BLN_OR_DASH NEW_OUTPUT_DIRECTORY\n"
                "usage (case): cteas_p2c_glc30m_sampling --case-grid inland|coastal SOURCE_30M.TIF SOURCE_SHA256 USER_POLICY_JSON UTM_EPSG XREFKM YREFKM NX NY DGRIDKM BLN_OR_DASH BLN_SHA_OR_DASH NEW_OUTPUT_DIRECTORY\n";
    return 2;
  }
  try{
    const std::string site=dynamic?argv[2]:argv[1];
    need(dynamic?(site=="inland"||site=="coastal"):
                 (site=="inland"||site=="wolsong"),
         "P2C_UNSUPPORTED_SITE_OR_MODE");
    const fs::path tif=dynamic?argv[3]:argv[2];
    const fs::path policy_file=dynamic?argv[5]:argv[4];
    const fs::path output=dynamic?argv[14]:argv[6];
    const std::string data_sha=dynamic?argv[4]:argv[3];
    const std::string bln_name=dynamic?argv[12]:argv[5];
    const bool coastal=site=="wolsong"||site=="coastal";
    const std::string bln_sha=dynamic?argv[13]:
       (coastal?std::string(kOriginalBlnSha):std::string("-"));
    need(!fs::exists(output)&&!fs::is_symlink(fs::symlink_status(output)),
         "P2C_OUTPUT_ALREADY_EXISTS");
    source(tif,data_sha);
    source(policy_file,kP2cMappingPolicySha256);
    const auto policy=load_p2c_glc30m_policy(policy_file);
    const int epsg=dynamic?static_cast<int>(positive_int(argv[6],"P2C_BAD_EPSG")):
                           (coastal?32652:32650);
    need((epsg>=32601&&epsg<=32660)||(epsg>=32701&&epsg<=32760),
         "P2C_WGS84_UTM_ONLY");
    const P2Grid grid=dynamic?
        P2Grid{three_decimal_origin_km(argv[7])*1000.,
               three_decimal_origin_km(argv[8])*1000.,
               spacing_metres(argv[11]),
               positive_int(argv[9],"P2C_BAD_NX"),
               positive_int(argv[10],"P2C_BAD_NY")} :
        (coastal?P2Grid{533215.,3942629.,100.,200,200}:
                 P2Grid{503385.,3523769.,100.,200,200});
    need(grid.nx>0&&grid.ny>0&&grid.nx<=250000/grid.ny,
         "P2C_CURRENT_250K_CELL_BUDGET");
    std::unique_ptr<OriginalBlnIptypeR4> coastline;
    if(coastal){
      if(!dynamic)need(data_sha==kWolsongSha,
                       "P2C_WOLSONG_FROZEN_TIFF_SHA_DRIFT");
      source(fs::path(bln_name),dynamic?bln_sha:std::string(kOriginalBlnSha));
      coastline=std::make_unique<OriginalBlnIptypeR4>(
        OriginalBlnIptypeR4::load_coastrd_bln(
          fs::path(bln_name),
          static_cast<float>(grid.x0_m/1000.),
          static_cast<float>(grid.y0_m/1000.),
          static_cast<float>((grid.x0_m+grid.dx_m*grid.nx)/1000.),
          static_cast<float>((grid.y0_m+grid.dx_m*grid.ny)/1000.)));
    } else {
      need(bln_name=="-"&&bln_sha=="-",
           "P2C_INLAND_FORBIDS_COAST_BLN_OR_SHA");
    }
    const auto counted=sample_p2c_glc30m(
         tif,grid,epsg,policy,coastline.get(),10);
    const auto cells=grid.nx*grid.ny;
    need(counted.hits.counts.size()==cells*38&&counted.hits.samples.size()==cells,
         "P2C_GRID_SHAPE_INCONSISTENT");
    fs::create_directory(output);
    try{
      std::ofstream lu(output/"lu.dat",std::ios::binary);
      need(bool(lu),"P2C_LU_OPEN");
      const auto stats=write_original_sampling_lu(
         lu,counted.hits,false,epsg%100,
         "Produced by CTEAS P2-C 2022 30m ORIGINAL_STYLE_POINT_HITS",
         "User-selected frozen 35-class policy; independent science NOT_RUN",
         epsg>=32701?'S':'N');
      lu.close();need(bool(lu),"P2C_LU_CLOSE");
      need(stats.fraction_fields==cells*38&&stats.total_hits==counted.hits.included&&
           stats.nonempty_cells+stats.missing_cells==cells,
           "P2C_LU_SAMPLE_CONSERVATION");
      std::ofstream csv(output/"hits.csv",std::ios::binary);
      need(bool(csv),"P2C_HITS_OPEN");
      csv<<"i,j,samples";
      for(int cls:kGlccUsgs92Classes)csv<<",cat"<<cls;
      csv<<"\n";
      for(std::size_t j=0;j<grid.ny;++j)for(std::size_t i=0;i<grid.nx;++i){
        const std::size_t cell=j*grid.nx+i;
        csv<<i+1<<","<<j+1<<","<<counted.hits.samples[cell];
        std::uint64_t sum=0;
        for(std::size_t k=0;k<38;++k){
          const auto n=counted.hits.counts[cell*38+k];
          csv<<","<<n;sum+=n;
        }
        need(sum==counted.hits.samples[cell],"P2C_HITS_ROW_CONSERVATION");
        csv<<"\n";
      }
      csv.close();need(bool(csv),"P2C_HITS_CLOSE");
      std::ofstream manifest(output/"p2c_glc30m_manifest.json");
      need(bool(manifest),"P2C_MANIFEST_OPEN");
      manifest<<"{\n"
        <<"  \"producer\": \"cteas_p2c_glc30m_sampling\",\n"
        <<"  \"method\": \""<<kP2cSamplingMethodId<<"\",\n"
        <<"  \"site\": \""<<site<<"\",\n"
        <<"  \"mapping_policy_status\": \"P2C_MAPPING_POLICY_USER_APPROVED_FROZEN\",\n"
        <<"  \"mapping_policy_sha256\": \""<<kP2cMappingPolicySha256<<"\",\n"
        <<"  \"data_sha256\": \""<<data_sha<<"\",\n"
        <<"  \"full_l1_original_bln_sha256\": \""
        <<(coastal?bln_sha:"NOT_APPLICABLE_LCOAST_FALSE")<<"\",\n"
        <<"  \"hits_csv_sha256\": \""<<hash(output/"hits.csv")<<"\",\n"
        <<"  \"lu_dat_sha256\": \""<<hash(output/"lu.dat")<<"\",\n"
        <<"  \"utm_epsg\": "<<epsg<<", \"nx\": "<<grid.nx<<", \"ny\": "<<grid.ny<<",\n"
        <<"  \"xrefkm\": \""<<std::fixed<<std::setprecision(3)<<grid.x0_m/1000.
        <<"\", \"yrefkm\": \""<<grid.y0_m/1000.<<"\",\n"
        <<"  \"dgridkm\": "<<grid.dx_m/1000.<<", \"classes\": 38, \"mesh\": 10,\n"
        <<"  \"lcoast\": "<<(coastal?"true":"false")
        <<", \"lmarswap\": "<<(coastal?"true":"false")
        <<", \"lmarfill\": false, \"iocean\": 55,\n"
        <<"  \"source_pixels\": "<<counted.source_pixels<<",\n"
        <<"  \"masked_pixels\": "<<counted.masked_pixels<<",\n"
        <<"  \"nodata_pixels\": "<<counted.no_data_pixels<<",\n"
        <<"  \"included_hits\": "<<counted.hits.included<<",\n"
        <<"  \"outside_hits\": "<<counted.hits.outside<<",\n"
        <<"  \"water52_hits\": "<<counted.water_land_hits<<",\n"
        <<"  \"water55_hits\": "<<counted.water_sea_hits<<",\n"
        <<"  \"nonempty_cells\": "<<stats.nonempty_cells<<",\n"
        <<"  \"missing_cells\": "<<stats.missing_cells<<",\n"
        <<"  \"fraction_fields\": "<<stats.fraction_fields<<",\n"
        <<"  \"source_pixel_histogram\": {";
      bool first=true;
      for(std::size_t i=0;i<256;++i)if(counted.source_pixel_histogram[i]){
        if(!first)manifest<<",";
        first=false;
        manifest<<"\n    \""<<i<<"\": "<<counted.source_pixel_histogram[i];
      }
      manifest<<"\n  },\n  \"included_sample_histogram\": {";
      first=true;
      for(std::size_t i=0;i<256;++i)if(counted.classified_sample_histogram[i]){
        if(!first)manifest<<",";
        first=false;
        manifest<<"\n    \""<<i<<"\": "<<counted.classified_sample_histogram[i];
      }
      manifest<<"\n  },\n"
        <<"  \"independent_30m_integer_hit_oracle\": \"NOT_RUN\",\n"
        <<"  \"p3_lu_dat_independent_format\": \"NOT_RUN\",\n"
        <<"  \"p3_makegeo\": \"OUT_OF_SCOPE_ISSUE46\",\n"
        <<"  \"application_status\": \"P2C_30M_PRODUCED_NOT_INDEPENDENTLY_ACCEPTED\"\n"
        <<"}\n";
      manifest.close();need(bool(manifest),"P2C_MANIFEST_CLOSE");
      std::cout<<"P2C_GLC30M_NATIVE_CANDIDATE_PRODUCED"
               <<" site="<<site<<" included="<<counted.hits.included
               <<" outside="<<counted.hits.outside
               <<" water52="<<counted.water_land_hits
               <<" water55="<<counted.water_sea_hits
               <<" independent_oracle=NOT_RUN p3=NOT_RUN\n";
    }catch(...){fs::remove_all(output);throw;}
    return 0;
  }catch(const std::exception& e){
    std::cerr<<"P2C_FAIL_CLOSED:"<<e.what()<<"\n";
    return 2;
  }
}
