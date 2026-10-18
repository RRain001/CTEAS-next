#include "cteas/geo/glcc_raw_fractions.hpp"
#include "cteas/geo/grid_origin.hpp"
#include <openssl/evp.h>
#include <array>
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
constexpr const char* kOfficialSha="4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a";
void require(bool v,const char* s){if(!v)throw std::runtime_error(s);}
int integer(const char* p){std::string s(p);std::size_t n=0;const int v=std::stoi(s,&n);require(n==s.size(),"P2_GLCC_BAD_INTEGER");return v;}
double real(const char* p){std::string s(p);std::size_t n=0;const double v=std::stod(s,&n);require(n==s.size()&&std::isfinite(v),"P2_GLCC_BAD_REAL");return v;}
std::string sha256(const fs::path& path){
  std::ifstream in(path,std::ios::binary);require(bool(in),"P2_GLCC_INPUT_MISSING");
  std::unique_ptr<EVP_MD_CTX,decltype(&EVP_MD_CTX_free)> md(EVP_MD_CTX_new(),EVP_MD_CTX_free);
  require(bool(md)&&EVP_DigestInit_ex(md.get(),EVP_sha256(),nullptr)==1,"P2_GLCC_SHA_INIT");
  std::array<char,1<<16> block{};
  while(in){in.read(block.data(),static_cast<std::streamsize>(block.size()));
    if(in.gcount())require(EVP_DigestUpdate(md.get(),block.data(),std::size_t(in.gcount()))==1,"P2_GLCC_SHA_UPDATE");}
  require(in.eof(),"P2_GLCC_SOURCE_READ_FAILED");
  unsigned char digest[EVP_MAX_MD_SIZE]{};unsigned int n=0;
  require(EVP_DigestFinal_ex(md.get(),digest,&n)==1&&n==32,"P2_GLCC_SHA_FINAL");
  const char* digits="0123456789abcdef";std::string out;
  for(unsigned int k=0;k<n;++k){out+=digits[digest[k]>>4];out+=digits[digest[k]&15];}return out;
}
}
int main(int argc,char** argv){
  if(argc!=10){std::cerr<<"usage: cteas_p2_glcc_raw RAW_EAUSGS_IMG NEW_OUT_DIR UTM_EPSG XREFKM YREFKM DGRIDKM NX NY MESH\n";return 2;}
  try {
    using namespace cteas::reconstruction::geo;
    const fs::path source=argv[1],dest=argv[2];
    require(!fs::is_symlink(fs::symlink_status(source))&&fs::is_regular_file(source),"P2_GLCC_SOURCE_MISSING_OR_SYMLINK");
    require(fs::file_size(source)==156000000,"P2_GLCC_NOT_156MB_RAW_IMG_OR_LFS_POINTER");
    require(!fs::exists(dest)&&!fs::is_symlink(fs::symlink_status(dest)),"P2_GLCC_OUTPUT_ALREADY_EXISTS");
    // Production source SHA cannot be overridden by a synthetic test hash.
    const auto observed=sha256(source);
    require(observed==kOfficialSha,"P2_GLCC_OFFICIAL_SHA256_MISMATCH");
    const int epsg=integer(argv[3]);
    const double x=three_decimal_origin_km(argv[4])*1000.;
    const double y=three_decimal_origin_km(argv[5])*1000.;
    const double d=real(argv[6])*1000.;
    const int nx=integer(argv[7]),ny=integer(argv[8]),mesh=integer(argv[9]);
    require(nx>0&&ny>0,"P2_GLCC_GRID_POSITIVE_DIMENSIONS");
    const auto r=compute_glcc_gen_replay(source.string(),{x,y,d,std::size_t(nx),std::size_t(ny)},epsg,mesh);
    fs::create_directory(dest);
    try {
      std::ofstream f(dest/"p2_glcc_usgs92_gen_replay.csv");
      require(bool(f),"P2_GLCC_CSV_OPEN_FAILURE");
      f<<"i,j,samples";for(const int k:kGlccUsgs92Classes)f<<",cat"<<k;f<<"\n";
      f<<std::fixed<<std::setprecision(12);
      std::uint64_t nonempty=0;
      for(std::size_t j=0;j<r.grid.ny;++j)for(std::size_t i=0;i<r.grid.nx;++i){
        const auto cell=j*r.grid.nx+i;
        const auto n=r.cell_samples[cell];if(n)++nonempty;
        f<<i+1<<","<<j+1<<","<<n;
        for(std::size_t k=0;k<kGlccUsgs92Classes.size();++k){
          if(!n)f<<",MISSING";else f<<","<<r.fraction(i,j,k);
        }f<<"\n";
      }
      require(bool(f),"P2_GLCC_CSV_WRITE_FAILED");
      std::ofstream meta(dest/"p2_manifest.json");
      require(bool(meta),"P2_GLCC_MANIFEST_OPEN_FAILURE");
      meta<<"{\n  \"producer\": \"cteas_p2_glcc_raw\",\n"
          <<"  \"source_product\": \"USGS_GLCC_EURASIA_1992_1993_ORIGINAL_1KM\",\n"
          <<"  \"source_sha256\": \""<<observed<<"\",\n"
          <<"  \"source_size_bytes\": 156000000,\n"
          <<"  \"utm_epsg\": "<<epsg<<", \"nx\": "<<nx<<", \"ny\": "<<ny<<",\n"
          <<"  \"xrefkm\": \""<<argv[4]<<"\", \"yrefkm\": \""<<argv[5]<<"\",\n"
          <<"  \"dgridkm\": "<<std::setprecision(12)<<d/1000.<<", \"mesh\": "<<mesh<<",\n"
          <<"  \"glcc_window_ij_1based\": ["<<r.window.i0<<","<<r.window.i1<<","<<r.window.j0<<","<<r.window.j1<<"],\n"
          <<"  \"raw_category_pixels_0_to_24\": [";
      for(std::size_t k=0;k<r.raw_pixels.size();++k)meta<<(k?",":"")<<r.raw_pixels[k];
      meta<<"],\n  \"included\": "<<r.included<<", \"outside\": "<<r.outside<<", \"nonempty_cells\": "<<nonempty<<",\n"
          <<"  \"method\": \"GLCC_HEADERLESS_ROW_DIRECT_GEN_7DP_REAL4_REPLAY\",\n"
          <<"  \"point_counts_are_not_pixel_areas\": true,\n"
          <<"  \"evidence_status\": \"PRODUCED_UNVERIFIED\",\n"
          <<"  \"official_GLAZAS_parity\": \"NOT_RUN\",\n"
          <<"  \"lu_dat\": \"NOT_RUN\", \"p3_geo_dat\": \"NOT_RUN\"\n}\n";
      require(bool(meta),"P2_GLCC_MANIFEST_WRITE_FAILED");
    }catch(...){fs::remove_all(dest);throw;}
    std::cout<<"P2_GLCC_REAL_SOURCE_SHA=VERIFIED GEN_REPLAY=PRODUCED_UNVERIFIED INCLUDED="<<r.included
             <<" OUTSIDE="<<r.outside<<" ORIGINAL_GLAZAS_PARITY=NOT_RUN P3=NOT_RUN\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
