// Issue #160 C1: inland historical-GLCC original sampling entrypoint.
// Never changes the immutable GLCC mapping or P2-B EXACT_AREA_V1.
#include "cteas/geo/ctgproc_original_sampling_lu_writer.hpp"
#include <ogr_spatialref.h>
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
#include <utility>
namespace {
namespace fs = std::filesystem;
using namespace cteas::reconstruction::geo;
constexpr const char* kGlccSha =
    "4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a";
constexpr const char* kOriginalSourceSha =
    "719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281";
constexpr double kLon = 117.141610855, kLat = 31.939774444;
void need(bool ok, const char* message) {
  if (!ok) throw std::runtime_error(message);
}
std::string sha256(const fs::path& path) {
  std::ifstream input(path, std::ios::binary);
  need(bool(input), "P2C_HEFEI_INPUT_READ");
  std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)> ctx(EVP_MD_CTX_new(), EVP_MD_CTX_free);
  need(bool(ctx) && EVP_DigestInit_ex(ctx.get(), EVP_sha256(), nullptr)==1, "P2C_HEFEI_SHA_INIT");
  std::array<char,65536> block{};
  while (input) {
    input.read(block.data(), std::streamsize(block.size()));
    if (input.gcount())
      need(EVP_DigestUpdate(ctx.get(), block.data(), std::size_t(input.gcount()))==1,
           "P2C_HEFEI_SHA_UPDATE");
  }
  need(input.eof(), "P2C_HEFEI_SHA_READ");
  unsigned char result[EVP_MAX_MD_SIZE]{};
  unsigned n=0;
  need(EVP_DigestFinal_ex(ctx.get(), result, &n)==1 && n==32, "P2C_HEFEI_SHA_FINISH");
  const char* hex = "0123456789abcdef";
  std::string out;
  for (unsigned i=0; i<n; ++i) { out+=hex[result[i]>>4]; out+=hex[result[i]&15]; }
  return out;
}
std::pair<double,double> center_utm50() {
  OGRSpatialReference geo,utm;
  geo.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  utm.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  need(geo.importFromEPSG(4326)==OGRERR_NONE && utm.importFromEPSG(32650)==OGRERR_NONE,
       "P2C_HEFEI_CRS_INIT");
  std::unique_ptr<OGRCoordinateTransformation, decltype(&OCTDestroyCoordinateTransformation)>
      forward(OGRCreateCoordinateTransformation(&geo,&utm), OCTDestroyCoordinateTransformation);
  need(bool(forward), "P2C_HEFEI_CRS_TRANSFORM");
  double x=kLon,y=kLat;
  need(forward->Transform(1,&x,&y)!=0 && std::isfinite(x) && std::isfinite(y),
       "P2C_HEFEI_CENTER_TRANSFORM");
  return {x,y};
}
} // namespace

int main(int argc,char** argv) {
  if (argc!=3) {
    std::cerr << "usage: cteas_p2_original_sampling_hefei "
                 "CANONICAL_HISTORICAL_GLCC_IMG NEW_OUTPUT_DIRECTORY\n";
    return 2;
  }
  try {
    const fs::path img=argv[1],dest=argv[2];
    need(fs::is_regular_file(img) && !fs::is_symlink(fs::symlink_status(img)),
         "P2C_HEFEI_CANONICAL_IMG_REQUIRED");
    need(!fs::exists(dest) && !fs::is_symlink(fs::symlink_status(dest)),
         "P2C_HEFEI_OUTPUT_EXISTS");
    need(fs::file_size(img)==156000000, "P2C_HEFEI_GLCC_SIZE");
    need(sha256(img)==kGlccSha, "P2C_HEFEI_GLCC_SHA");
    const auto [center_x,center_y]=center_utm50();
    const double x0=std::round(center_x-10000.);
    const double y0=std::round(center_y-10000.);
    // Frozen 1m coordinate origin rule; no silent return to 5km historic grid.
    need(x0==503385. && y0==3523769., "P2C_HEFEI_ORIGIN_CONTRACT_CHANGED");
    need(std::abs(x0+10000.-center_x)<=.5 &&
         std::abs(y0+10000.-center_y)<=.5, "P2C_HEFEI_CENTER_ROUNDING");
    const P2Grid grid{x0,y0,100.,200,200};
    // Old historical 24-code mapping, direct-LAEA point generator and
    // REAL*4 GLOBE/LUGRID mesh assignment remain unmodified.
    const auto source=compute_glcc_direct_laea(img.string(),grid,32650,10,true);
    const OriginalCoastControl no_coast{
        false,false,false,false,55,OriginalLanduseSource::HistoricalUsgs38};
    const auto hits=recount_glcc_original_coast_bln(source,no_coast,nullptr);
    need(hits.counts==source.counts && hits.samples==source.cell_samples &&
         hits.included==source.included && hits.outside==source.outside &&
         hits.rejected_coast==0, "P2C_HEFEI_LCOAST_FALSE_BASELINE_DRIFT");
    fs::create_directory(dest);
    try {
      std::ofstream lu(dest/"lu.dat",std::ios::binary);
      need(bool(lu),"P2C_HEFEI_LU_CREATE");
      const auto stats=write_original_sampling_lu(
          lu,hits,false,50,
          "Produced by CTEAS C++ ORIGINAL_SAMPLING #160 (Hefei GLCC historical)",
          "SHA-admitted historical GLCC; inland LCOAST=F; original parity NOT_RUN");
      lu.close();need(bool(lu),"P2C_HEFEI_LU_CLOSE");
      need(stats.total_hits==hits.included &&
           stats.nonempty_cells+stats.missing_cells==40000 &&
           stats.fraction_fields==1520000, "P2C_HEFEI_STATS_CONSERVATION");
      // Unrounded 38-class integer evidence for an independent original
      // LFINAL=F Fortran HITS oracle; never infer hits from printed fractions.
      std::ofstream csv(dest/"hits.csv",std::ios::binary);
      need(bool(csv),"P2C_HEFEI_HITS_CREATE");
      csv<<"i,j,samples";
      for (const int id:kGlccUsgs92Classes) csv<<",cat"<<id;
      csv<<"\n";
      for (std::size_t j=0;j<grid.ny;++j)
        for (std::size_t i=0;i<grid.nx;++i) {
          const auto cell=j*grid.nx+i;
          csv<<i+1<<","<<j+1<<","<<hits.samples[cell];
          std::uint64_t sum=0;
          for (std::size_t k=0;k<38;++k) {
            const auto n=hits.counts[cell*38+k];
            sum+=n;
            csv<<","<<n;
          }
          need(sum==hits.samples[cell],"P2C_HEFEI_HITS_CELL_MISMATCH");
          csv<<"\n";
        }
      csv.close();need(bool(csv),"P2C_HEFEI_HITS_CLOSE");
      const auto hits_hash=sha256(dest/"hits.csv");
      const auto lu_hash=sha256(dest/"lu.dat");
      std::ofstream manifest(dest/"p2_original_sampling_manifest.json");
      need(bool(manifest),"P2C_HEFEI_MANIFEST_CREATE");
      manifest << "{\n"
          << "  \"producer\": \"cteas_p2_original_sampling_hefei\",\n"
          << "  \"method\": \"ORIGINAL_GLAZAS_LUGRID_SVGRID_HISTORICAL_GLCC_INLAND_V1\",\n"
          << "  \"scope\": \"HEFEI_200X200_UTM50N_GLCC_HISTORICAL_ONLY\",\n"
          << "  \"source_sha256\": \"" << kGlccSha << "\",\n"
          << "  \"original_vendor_source_sha256\": \"" << kOriginalSourceSha << "\",\n"
          << "  \"lu_dat_sha256\": \"" << lu_hash << "\",\n"
          << "  \"hits_csv_sha256\": \"" << hits_hash << "\",\n"
          << "  \"utm_epsg\": 32650, \"nx\": 200, \"ny\": 200, \"mesh\": 10,\n"
          << "  \"xrefkm\": \"503.385\", \"yrefkm\": \"3523.769\",\n"
          << "  \"dgridkm\": 0.100, \"classes\": 38,\n"
          << "  \"center_wgs84_lat\": " << std::fixed << std::setprecision(9) << kLat
          << ", \"center_wgs84_lon\": " << kLon << ",\n"
          << "  \"center_offset_east_m\": " << std::setprecision(6)
          << (x0+10000.-center_x) << ",\n"
          << "  \"center_offset_north_m\": " << (y0+10000.-center_y) << ",\n"
          << "  \"total_samples\": " << stats.total_hits << ",\n"
          << "  \"outside_samples\": " << hits.outside << ",\n"
          << "  \"nonempty_cells\": " << stats.nonempty_cells << ",\n"
          << "  \"missing_cells\": " << stats.missing_cells << ",\n"
          << "  \"fraction_fields\": " << stats.fraction_fields << ",\n"
          << "  \"lcoast\": false, \"lmarswap\": false, \"lmarfill\": false,\n"
          << "  \"iocean\": 55, \"gshhg_loaded\": false,\n"
          << "  \"historical_glcc_mapping_modified\": false,\n"
          << "  \"original_fortran_integer_parity\": \"NOT_RUN\",\n"
          << "  \"original_fortran_fraction_parity\": \"NOT_RUN\",\n"
          << "  \"p3_lu_format_independent\": \"NOT_RUN\",\n"
          << "  \"modern_glc30m_sampling\": \"NOT_RUN\"\n"
          << "}\n";
      manifest.close();need(bool(manifest),"P2C_HEFEI_MANIFEST_CLOSE");
      std::cout<<"P2C_HEFEI_GLCC_INLAND_CANDIDATE_PRODUCED"
               <<" hits="<<stats.total_hits<<" missing="<<stats.missing_cells
               <<" original_fortran_science=NOT_RUN modern_30m=NOT_RUN\n";
    } catch(...) { fs::remove_all(dest); throw; }
    return 0;
  } catch (const std::exception& e) {
    std::cerr<<"P2C_HEFEI_FAIL_CLOSED:"<<e.what()<<"\n";
    return 2;
  }
}
