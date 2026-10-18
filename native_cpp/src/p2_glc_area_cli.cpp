#include "cteas/geo/glc_area_fractions.hpp"
#include "cteas/geo/grid_origin.hpp"
#include <openssl/evp.h>
#include <array>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
namespace {
namespace fs=std::filesystem;
using cteas::reconstruction::geo::three_decimal_origin_km;
void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
int exact_int(const std::string& s){std::size_t n=0;const int v=std::stoi(s,&n);require(n==s.size(),"P2_GLC_BAD_INTEGER");return v;}
double exact_double(const std::string& s){std::size_t n=0;double v=std::stod(s,&n);require(n==s.size()&&std::isfinite(v),"P2_GLC_BAD_NUMBER");return v;}
std::string file_sha256(const fs::path& path) {
  std::ifstream in(path,std::ios::binary);require(bool(in),"P2_GLC_SOURCE_MISSING");
  std::unique_ptr<EVP_MD_CTX,decltype(&EVP_MD_CTX_free)> md(EVP_MD_CTX_new(),EVP_MD_CTX_free);
  require(bool(md)&&EVP_DigestInit_ex(md.get(),EVP_sha256(),nullptr)==1,"P2_GLC_SHA256_INIT_FAILED");
  std::array<char,1<<16> buf{};
  while(in) {
    in.read(buf.data(),static_cast<std::streamsize>(buf.size()));
    const auto count=in.gcount();
    if(count)require(EVP_DigestUpdate(md.get(),buf.data(),static_cast<std::size_t>(count))==1,"P2_GLC_SHA256_UPDATE_FAILED");
  }
  require(in.eof(),"P2_GLC_SOURCE_READ_FAILED");
  unsigned char digest[EVP_MAX_MD_SIZE]{};unsigned int length=0;
  require(EVP_DigestFinal_ex(md.get(),digest,&length)==1&&length==32,"P2_GLC_SHA256_FAILED");
  const char* hex="0123456789abcdef";std::string out;out.reserve(64);
  for(unsigned i=0;i<length;++i){out.push_back(hex[digest[i]>>4]);out.push_back(hex[digest[i]&15]);}
  return out;
}
}
int main(int argc,char** argv) {
  if(argc!=10) {
    std::cerr<<"usage: cteas_p2_glc_raw TIFF NEW_OUT_DIR EXPECTED_SHA256 EPSG XREFKM YREFKM DGRIDKM NX NY\n";
    return 2;
  }
  try {
    const fs::path input=argv[1],dest=argv[2];
    const std::string expected=argv[3];
    require(expected.size()==64,"P2_GLC_EXPECTED_SHA256_FORMAT");
    for(char c:expected)require(std::isxdigit(static_cast<unsigned char>(c))!=0&&
                                !(c>='A'&&c<='F'),"P2_GLC_EXPECTED_SHA256_MUST_BE_LOWERCASE");
    require(!fs::is_symlink(fs::symlink_status(input))&&fs::is_regular_file(input),
            "P2_GLC_INPUT_MISSING_OR_SYMLINK");
    require(!fs::exists(dest)&&!fs::is_symlink(fs::symlink_status(dest)),
            "P2_GLC_OUT_DIR_MUST_NOT_EXIST");
    const auto sha=file_sha256(input);
    require(sha==expected,"P2_GLC_SOURCE_SHA256_MISMATCH");
    const int epsg=exact_int(argv[4]);
    const double x=three_decimal_origin_km(argv[5])*1000.;
    const double y=three_decimal_origin_km(argv[6])*1000.;
    const double dx=exact_double(argv[7])*1000.;
    const int nx=exact_int(argv[8]),ny=exact_int(argv[9]);
    require(nx>0&&ny>0,"P2_GLC_POSITIVE_NX_NY_REQUIRED");
    const cteas::reconstruction::geo::P2Grid grid{x,y,dx,
                  static_cast<std::size_t>(nx),static_cast<std::size_t>(ny)};
    const auto result=cteas::reconstruction::geo::compute_glc_area_fractions(input.string(),grid,epsg);
    fs::create_directory(dest);
    try {
      std::ofstream fr(dest/"p2_raw_fractions.csv");
      std::ofstream ar(dest/"p2_raw_class_area_m2.csv");
      require(bool(fr)&&bool(ar),"P2_GLC_OUTPUT_OPEN_FAILED");
      fr<<"i,j,cell_area_m2,valid_area_m2,coverage_fraction";
      ar<<"i,j";
      for(int code:result.raw_codes){fr<<",glc"<<code;ar<<",glc"<<code;}
      fr<<"\n";ar<<"\n";
      fr<<std::fixed<<std::setprecision(12);
      ar<<std::fixed<<std::setprecision(8);
      for(std::size_t j=0;j<grid.ny;++j)for(std::size_t i=0;i<grid.nx;++i) {
        const std::size_t idx=j*grid.nx+i;
        fr<<i+1<<","<<j+1<<","<<grid.dx_m*grid.dx_m<<","<<result.valid_m2[idx]<<","<<1.;
        ar<<i+1<<","<<j+1;
        for(std::size_t k=0;k<result.raw_codes.size();++k){
          fr<<","<<result.fraction(i,j,k);
          ar<<","<<result.area_m2[idx*result.raw_codes.size()+k];
        }
        fr<<"\n";ar<<"\n";
      }
      require(bool(fr)&&bool(ar),"P2_GLC_OUTPUT_WRITE_FAILED");
      std::ofstream meta(dest/"p2_manifest.json");
      require(bool(meta),"P2_GLC_MANIFEST_OPEN_FAILED");
      meta<<"{\n  \"producer\": \"cteas_p2_glc_raw\",\n"
          <<"  \"source_kind\": \"GLC_FCS30D_2022_30m\",\n"
          <<"  \"source_sha256\": \""<<sha<<"\",\n"
          <<"  \"utm_epsg\": "<<epsg<<",\n"
          <<"  \"nx\": "<<nx<<", \"ny\": "<<ny<<",\n"
          <<"  \"xrefkm\": \""<<argv[5]<<"\", \"yrefkm\": \""<<argv[6]<<"\",\n"
          <<"  \"dgridkm\": "<<std::setprecision(12)<<grid.dx_m/1000.<<",\n"
          <<"  \"raw_category_namespace\": \"GLC_FCS30D_35\",\n"
          <<"  \"method\": \"exact_north_up_same_utm_pixel_cell_rectangle_intersection\",\n"
          <<"  \"coverage_policy\": \"REJECT_ANY_NODATA_OR_INCOMPLETE_CELL\",\n"
          <<"  \"evidence_status\": \"PRODUCED_UNVERIFIED\",\n"
          <<"  \"crosswalk_status\": \"P2_MAPPING_REVIEW_REQUIRED\",\n"
          <<"  \"usgs92_lu_dat\": \"NOT_RUN\", \"p3_geo_dat\": \"NOT_RUN\"\n}\n";
      require(bool(meta),"P2_GLC_MANIFEST_WRITE_FAILED");
    }catch(...){fs::remove_all(dest);throw;}
    std::cout<<"P2_GLC_RAW_AREA=PRODUCED_UNVERIFIED CELLS="<<grid.nx*grid.ny
             <<" CROSSWALK=P2_MAPPING_REVIEW_REQUIRED P3=NOT_RUN\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
