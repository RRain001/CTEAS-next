// Issue #123 D11: explicit Wolsong-scoped original-CTGPROC sampling
// production output. Never substitutes for P2-B EXACT_AREA_V1.
#include "cteas/geo/ctgproc_original_sampling_lu_writer.hpp"
#include <openssl/evp.h>
#include <array>
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
constexpr const char* kGlccSha=
  "4f2a1977c6a70d74f7a0e136bdd4aa1777dc9cbab15c184e7f483f772cd266c6";
constexpr const char* kBlnSha=
  "67da93d441e7defe3eb46627ed9ce896c0a91ffd89fd5e4363d834d8108e11f9";
constexpr const char* kOriginalSourceSha=
  "719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281";
void require(bool b,const char* msg){if(!b)throw std::runtime_error(msg);}
std::string sha256(const fs::path& p) {
  std::ifstream f(p,std::ios::binary);require(bool(f),"D11_INPUT_READ");
  std::unique_ptr<EVP_MD_CTX,decltype(&EVP_MD_CTX_free)>
      ctx(EVP_MD_CTX_new(),EVP_MD_CTX_free);
  require(bool(ctx)&&EVP_DigestInit_ex(ctx.get(),EVP_sha256(),nullptr)==1,
          "D11_SHA_INIT");
  std::array<char,65536> bytes{};
  while(f) {
    f.read(bytes.data(),std::streamsize(bytes.size()));
    if(f.gcount())
      require(EVP_DigestUpdate(ctx.get(),bytes.data(),
                              std::size_t(f.gcount()))==1,"D11_SHA_UPDATE");
  }
  require(f.eof(),"D11_SHA_READ");
  unsigned char out[EVP_MAX_MD_SIZE]{};unsigned int n=0;
  require(EVP_DigestFinal_ex(ctx.get(),out,&n)==1&&n==32,"D11_SHA_FINAL");
  std::string s;const char* hex="0123456789abcdef";
  for(unsigned i=0;i<32;++i){s+=hex[out[i]>>4];s+=hex[out[i]&15];}
  return s;
}
}
int main(int argc,char** argv) {
  if(argc!=4){
    std::cerr<<"usage: cteas_p2_original_sampling_wolsong GLCC_EAUSGS_IMG"
             <<" SHA_VERIFIED_ORIGINAL_COAST_BLN NEW_OUTPUT_DIR\n";
    return 2;
  }
  try{
    using namespace cteas::reconstruction::geo;
    const fs::path img=argv[1],bln=argv[2],dest=argv[3];
    for(const auto& path:{img,bln}) {
      require(fs::is_regular_file(path)&&
              !fs::is_symlink(fs::symlink_status(path)),
              "D11_MISSING_REAL_INPUT_OR_SYMLINK");
    }
    require(!fs::exists(dest)&&!fs::is_symlink(fs::symlink_status(dest)),
            "D11_OUTPUT_COLLISION");
    require(fs::file_size(img)==156000000,"D11_ORIGINAL_GLCC_SIZE");
    require(sha256(img)==kGlccSha,"D11_UNVERIFIED_GLCC_SOURCE");
    require(sha256(bln)==kBlnSha,"D11_UNVERIFIED_REAL_ORIGINAL_BLN");
    const P2Grid grid{533215.,3942629.,100.,200,200};
    // The source mesh requires full in-memory trace for original coastal
    // classification; D2 GEOS approximation is never called here.
    const auto source=compute_glcc_direct_laea(img.string(),grid,32652,10,true);
    const auto classifier=OriginalBlnIptypeR4::load_coastrd_bln(
        bln,533.215f,3942.629f,553.215f,3962.629f);
    const OriginalCoastControl controls{
        true,true,false,false,55,OriginalLanduseSource::HistoricalUsgs38};
    const auto sampled=recount_glcc_original_coast_bln(source,controls,&classifier);
    require(sampled.included==40025&&sampled.outside==43975&&
            sampled.rejected_coast==0,"D11_WOLSONG_ACCEPTED_MESH_COUNTS_DRIFT");
    fs::create_directory(dest);
    try{
      std::ofstream out(dest/"lu.dat",std::ios::binary);
      require(bool(out),"D11_CANNOT_CREATE_LU");
      const auto stats=write_original_sampling_lu(out,sampled);
      out.close();require(bool(out),"D11_LU_CLOSE_FAILURE");
      require(stats.total_hits==40025&&stats.nonempty_cells==37035&&
              stats.missing_cells==2965&&stats.fraction_fields==1520000,
              "D11_WOLSONG_ACCEPTED_STATISTICS_DRIFT");
      const auto lu_sha=sha256(dest/"lu.dat");
      std::ofstream manifest(dest/"p2_original_sampling_manifest.json");
      require(bool(manifest),"D11_CANNOT_WRITE_MANIFEST");
      manifest<<"{\n"
        <<" \"producer\": \"cteas_p2_original_sampling_wolsong\",\n"
        <<" \"method\": \"ORIGINAL_SAMPLING_GLAZAS_REAL4_GSHHG_F_COASTRD_LUGRID_SVGRID_F63_V1\",\n"
        <<" \"scope\": \"WOLSONG_200X200_UTM52N_GLCC_HISTORICAL_ONLY\",\n"
        <<" \"original_vendor_source_sha256\": \""<<kOriginalSourceSha<<"\",\n"
        <<" \"source_sha256\": \""<<kGlccSha<<"\",\n"
        <<" \"original_bln_sha256\": \""<<kBlnSha<<"\",\n"
        <<" \"lu_dat_sha256\": \""<<lu_sha<<"\",\n"
        <<" \"nx\": 200, \"ny\": 200, \"utm_epsg\": 32652,\n"
        <<" \"xrefkm\": \"533.215\", \"yrefkm\": \"3942.629\", \"dgridkm\": 0.100,\n"
        <<" \"mesh\": 10, \"classes\": 38,\n"
        <<" \"total_samples\": "<<stats.total_hits<<",\n"
        <<" \"nonempty_cells\": "<<stats.nonempty_cells<<",\n"
        <<" \"missing_cells\": "<<stats.missing_cells<<",\n"
        <<" \"fraction_fields\": "<<stats.fraction_fields<<",\n"
        <<" \"lcoast\": true, \"lmarswap\": true, \"lmarfill\": false,\n"
        <<" \"iocean\": 55, \"gshhg_resolution\": \"Full\",\n"
        <<" \"producer_status\": \"PRODUCED_VERIFIED_SOURCE_NOT_EXTERNAL_SCIENCE\",\n"
        <<" \"original_f63_science\": \"REQUIRES_INDEPENDENT_D11_COMPARE\",\n"
        <<" \"p3\": \"NOT_RUN\", \"p6\": \"NOT_RUN\", \"p7\": \"NOT_RUN\"\n"
        <<"}\n";
      manifest.close();require(bool(manifest),"D11_MANIFEST_WRITE_FAILURE");
      std::cout<<"ORIGINAL_SAMPLING_WOLSONG_OUTPUT_CREATED_UNVERIFIED"
               <<" fields="<<stats.fraction_fields<<" nonempty="<<stats.nonempty_cells
               <<" missing="<<stats.missing_cells
               <<" independent_original_lu_parity=NOT_RUN\n";
    }catch(...){fs::remove_all(dest);throw;}
    return 0;
  }catch(const std::exception& e){
    std::cerr<<"D11_FAIL_CLOSED:"<<e.what()<<"\n";
    return 2;
  }
}
