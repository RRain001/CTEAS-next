#include "cteas/geo/glcc_raw_fractions.hpp"
#include "cteas/geo/glcc_direct_laea_probe.hpp"
#include "cteas/geo/glcc_cli_modes.hpp"
#include "cteas/geo/grid_origin.hpp"
#include <openssl/evp.h>
#include <array>
#include <algorithm>
#include <vector>
#include <cstdint>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <optional>
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
  const auto modes=cteas::reconstruction::geo::glcc_cli_modes(argc,
                                 const_cast<const char* const*>(argv));
  if(!modes.valid){
    std::cerr<<"usage: cteas_p2_glcc_raw RAW_EAUSGS_IMG NEW_OUT_DIR UTM_EPSG XREFKM YREFKM DGRIDKM NX NY MESH [--gen-replay|--production-direct] [--qa-submesh [--probe-direct]]\n";
    return 2;
  }
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
    const bool diag=modes.qa_submesh;
    const P2Grid grid{x,y,d,std::size_t(nx),std::size_t(ny)};
    // Direct-LAEA is the selected default after the authentic original
    // LFINAL=T/F production science PASS (Run #39188861410).
    // Historical GEN replay requires explicit --gen-replay. Both algorithms
    // produce their own authentic counts, never a renamed diagnostic CSV.
    const auto r=modes.production_direct
        ? compute_glcc_direct_laea(source.string(),grid,epsg,mesh,diag)
        : compute_glcc_gen_replay(source.string(),grid,epsg,mesh,diag);
    // For indexed original-lineage QA keep the historical GEN coordinate
    // stream separate from the production direct-LAEA coordinate stream.
    // Never execute the old GEN algorithm in an ordinary direct production run.
    std::optional<GlccRawResult> legacy_qa;
    if(diag&&modes.production_direct) {
      legacy_qa.emplace(compute_glcc_gen_replay(source.string(),grid,epsg,mesh,true));
      require(legacy_qa->raw_pixels==r.raw_pixels&&
              legacy_qa->diagnostic_mesh.size()==r.diagnostic_mesh.size(),
              "P2_GLCC_DIRECT_VS_GEN_SOURCE_COVERAGE_DRIFT");
      for(std::size_t p=0;p<r.diagnostic_mesh.size();++p) {
        const auto& a=r.diagnostic_mesh[p];
        const auto& b=legacy_qa->diagnostic_mesh[p];
        require(a.source_i==b.source_i&&a.source_j==b.source_j&&
                a.mesh_i==b.mesh_i&&a.mesh_j==b.mesh_j&&a.category==b.category,
                "P2_GLCC_DIRECT_VS_GEN_SOURCE_KEY_DRIFT");
      }
    }
    const auto& qa_mesh=legacy_qa?legacy_qa->diagnostic_mesh:r.diagnostic_mesh;
    const char* fraction_file=modes.production_direct
        ?"p2_glcc_usgs92_direct_laea.csv":"p2_glcc_usgs92_gen_replay.csv";
    // Preserve the already-science-compared UTM50N provenance identifier.
    // Other WGS84 UTM zones MUST have a distinct unvalidated method tag.
    const char* method=!modes.production_direct
        ?"GLCC_HEADERLESS_ROW_DIRECT_GEN_7DP_REAL4_REPLAY"
        :(epsg==32650
          ?"GLCC_HEADERLESS_LAEA_DIRECT_UTM50N_REAL4_GLOBE_LUGRID"
          :"GLCC_HEADERLESS_LAEA_DIRECT_WGS84_UTM_REAL4_GLOBE_LUGRID");
    const bool exact_hefei_profile=epsg==32650 && nx==50 && ny==50 &&
          mesh==20 && std::abs(x-510885.)<1e-6 &&
          std::abs(y-3531269.)<1e-6 && std::abs(d-100.)<1e-6;
    // A matching geometry alone is NOT a new science acceptance:
    // the actual pinned source, original binary and independent comparison
    // are checked only by the manual GLAZAS workflow.
    const char* science_scope=exact_hefei_profile
        ?"HEFEI_UTM50N_CONFIG_ELIGIBLE_FOR_MANUAL_ORIGINAL_SCIENCE"
        :"NON_HEFEI_OR_NON_REFERENCE_CONFIG_NO_ORIGINAL_SCIENCE_VERDICT";
    fs::create_directory(dest);
    try {
      std::ofstream f(dest/fraction_file);
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
      f.close();
      require(bool(f),"P2_GLCC_CSV_CLOSE_FAILED");
      const auto csv_sha=sha256(dest/fraction_file);
      // D1 original GLAZAS science comparison needs integers, not three-decimal LU ratios.
      // Persist exactly the C++ in-memory 38-class hit counts, with per-cell samples.
      std::ofstream hits(dest/"p2_glcc_usgs92_hits.csv");
      require(bool(hits),"P2_GLCC_HITS_CSV_OPEN_FAILURE");
      hits<<"i,j,samples";for(const int k:kGlccUsgs92Classes)hits<<",cat"<<k;hits<<"\n";
      for(std::size_t j=0;j<r.grid.ny;++j)for(std::size_t i=0;i<r.grid.nx;++i){
        const auto cell=j*r.grid.nx+i;
        hits<<i+1<<","<<j+1<<","<<r.cell_samples[cell];
        for(std::size_t k=0;k<kGlccUsgs92Classes.size();++k)
          hits<<","<<r.counts[cell*kGlccUsgs92Classes.size()+k];
        hits<<"\n";
      }
      require(bool(hits),"P2_GLCC_HITS_CSV_WRITE_FAILED");
      hits.close();
      require(bool(hits),"P2_GLCC_HITS_CSV_CLOSE_FAILED");
      const auto hits_sha=sha256(dest/"p2_glcc_usgs92_hits.csv");
      std::string diag_sha;
      if(diag) {
        std::ofstream trace(dest/"p2_glcc_submesh_diagnostic.csv");
        require(bool(trace),"P2_GLCC_DIAGNOSTIC_OPEN_FAILED");
        trace<<"source_i,source_j,mesh_i,mesh_j,usgs_category,x_km,y_km,assigned_i,assigned_j\n";
        trace<<std::setprecision(9);
        for(const auto& p:qa_mesh)
          trace<<p.source_i<<","<<p.source_j<<","<<p.mesh_i<<","<<p.mesh_j<<","
               <<p.category<<","<<p.x_km<<","<<p.y_km<<","
               <<p.assigned_i<<","<<p.assigned_j<<"\n";
        require(bool(trace),"P2_GLCC_DIAGNOSTIC_WRITE_FAILED");
        trace.close();
        require(bool(trace),"P2_GLCC_DIAGNOSTIC_CLOSE_FAILED");
        diag_sha=sha256(dest/"p2_glcc_submesh_diagnostic.csv");
      }

      // NON-PRODUCTION scientific candidate: direct LAEA (ESR-S sphere) to
      // WGS84/UTM. This NEVER changes r.counts, r.cell_samples or D3 LU.DAT.
      // Its 95k integer field differences against original Fortran must be
      // reported separately by the independent manual science comparator.
      std::string direct_probe_sha,direct_probe_mesh_sha;
      if(modes.direct_probe) {
        require(diag&&!qa_mesh.empty(),"DIRECT_PROBE_TRACE_MISSING");
        require(qa_mesh.size()==r.diagnostic_mesh.size(),
                "DIRECT_PROBE_TRACE_COUNT_INCONSISTENT");
        require(qa_mesh.size()==(legacy_qa?legacy_qa->included+legacy_qa->outside:
                                            r.included+r.outside),
                "DIRECT_PROBE_SOURCE_COUNT_INCONSISTENT");
        DirectLaeaProbe probe(epsg);
        const std::size_t nc=r.grid.nx*r.grid.ny;
        std::vector<std::uint32_t> candidate(nc*kGlccUsgs92Classes.size(),0);
        std::vector<std::uint32_t> candidate_samples(nc,0);
        std::uint64_t candidate_included=0,candidate_outside=0;
        const float x0=static_cast<float>(r.grid.x0_m/1000.);
        const float y0=static_cast<float>(r.grid.y0_m/1000.);
        const float step=static_cast<float>(r.grid.dx_m/1000.);
        // Trace the candidate BEFORE grid clipping; this provides a
        // source_i/j + imesh/jmesh join key against an independently
        // instrumented, exact-source original Fortran diagnostic.
        std::ofstream mesh_trace(dest/"p2_glcc_direct_laea_mesh.csv");
        require(bool(mesh_trace),"DIRECT_PROBE_MESH_OPEN_FAILED");
        mesh_trace<<"source_i,source_j,mesh_i,mesh_j,usgs_category,"
                    "laea_x_km,laea_y_km,x_km,y_km,assigned_i,assigned_j\n";
        mesh_trace<<std::setprecision(9);
        for(const auto& p:qa_mesh) {
          const auto q=probe.project(p.source_i,p.source_j,p.mesh_i,p.mesh_j,
                                     mesh,x0,y0,step);
          mesh_trace<<p.source_i<<","<<p.source_j<<","<<p.mesh_i<<","
                    <<p.mesh_j<<","<<p.category<<","<<q.laea_x_km<<","
                    <<q.laea_y_km<<","<<q.x_km<<","<<q.y_km<<","
                    <<q.i<<","<<q.j<<"\n";
          if(q.i<1||q.j<1||q.i>nx||q.j>ny){++candidate_outside;continue;}
          const auto cell=(std::size_t(q.j)-1)*r.grid.nx+std::size_t(q.i-1);
          const auto k=std::find(kGlccUsgs92Classes.begin(),
                                 kGlccUsgs92Classes.end(),p.category);
          require(k!=kGlccUsgs92Classes.end(),"DIRECT_PROBE_UNKNOWN_CLASS");
          candidate[cell*kGlccUsgs92Classes.size()+
                    std::size_t(k-kGlccUsgs92Classes.begin())]++;
          candidate_samples[cell]++;
          ++candidate_included;
        }
        require(bool(mesh_trace),"DIRECT_PROBE_MESH_WRITE_FAILED");
        mesh_trace.close();
        require(bool(mesh_trace),"DIRECT_PROBE_MESH_CLOSE_FAILED");
        const auto mesh_trace_sha=sha256(dest/"p2_glcc_direct_laea_mesh.csv");
        require(candidate_included+candidate_outside==qa_mesh.size(),
                "DIRECT_PROBE_INTERNAL_HITS_LOST");
        if(modes.production_direct)
          require(candidate==r.counts&&candidate_samples==r.cell_samples&&
                  candidate_included==r.included&&candidate_outside==r.outside,
                  "P2_GLCC_PRODUCTION_DIRECT_VS_INDEPENDENT_PROBE_DRIFT");
        require(candidate_included>0,"DIRECT_PROBE_ZERO_INCLUDED_SCIENCE_INVALID");
        std::ofstream destf(dest/"p2_glcc_direct_laea_candidate_hits.csv");
        require(bool(destf),"DIRECT_PROBE_HITS_CSV_OPEN_FAILED");
        destf<<"i,j,samples";
        for(int cat:kGlccUsgs92Classes)destf<<",cat"<<cat;
        destf<<"\n";
        for(std::size_t j=0;j<r.grid.ny;++j)
          for(std::size_t i=0;i<r.grid.nx;++i) {
            const auto cell=j*r.grid.nx+i;
            destf<<i+1<<","<<j+1<<","<<candidate_samples[cell];
            for(std::size_t k=0;k<kGlccUsgs92Classes.size();++k)
              destf<<","<<candidate[cell*kGlccUsgs92Classes.size()+k];
            destf<<"\n";
          }
        require(bool(destf),"DIRECT_PROBE_HITS_CSV_WRITE_FAILED");
        destf.close();
        require(bool(destf),"DIRECT_PROBE_HITS_CSV_CLOSE_FAILED");
        direct_probe_sha=sha256(dest/"p2_glcc_direct_laea_candidate_hits.csv");
        // SHA is scoped to diagnostic instrumentation and cannot upgrade
        // either the official production D1 or original-HITS science gate.
        direct_probe_mesh_sha=mesh_trace_sha;
        std::cout<<"DIRECT_LAEA_SPHERE_CANDIDATE_DIAGNOSTIC_ONLY INCLUDED="
                 <<candidate_included<<" OUTSIDE="<<candidate_outside
                 <<" ORIGINAL_INTEGER_PARITY=NOT_TESTED\n";
      }

      std::ofstream meta(dest/"p2_manifest.json");
      require(bool(meta),"P2_GLCC_MANIFEST_OPEN_FAILURE");
      meta<<"{\n  \"producer\": \"cteas_p2_glcc_raw\",\n"
          <<"  \"source_product\": \"USGS_GLCC_EURASIA_1992_1993_ORIGINAL_1KM\",\n"
          <<"  \"source_sha256\": \""<<observed<<"\",\n"
          <<"  \"fractions_csv_sha256\": \""<<csv_sha<<"\",\n"          <<"  \"hits_csv_sha256\": \""<<hits_sha<<"\",\n"          <<(diag?"  \"diagnostic_submesh_csv_sha256\": \""+diag_sha+"\",\n":"")
          <<(modes.direct_probe?"  \"direct_laea_candidate_hits_csv_sha256\": \""+direct_probe_sha+"\",\n":"")
          <<(modes.direct_probe?"  \"direct_laea_candidate_mesh_csv_sha256\": \""+direct_probe_mesh_sha+"\",\n":"")

          <<"  \"source_size_bytes\": 156000000,\n"
          <<"  \"utm_epsg\": "<<epsg<<", \"nx\": "<<nx<<", \"ny\": "<<ny<<",\n"
          <<"  \"xrefkm\": \""<<argv[4]<<"\", \"yrefkm\": \""<<argv[5]<<"\",\n"
          <<"  \"dgridkm\": "<<std::setprecision(12)<<d/1000.<<", \"mesh\": "<<mesh<<",\n"
          <<"  \"glcc_window_ij_1based\": ["<<r.window.i0<<","<<r.window.i1<<","<<r.window.j0<<","<<r.window.j1<<"],\n"
          <<"  \"raw_category_pixels_0_to_24\": [";
      for(std::size_t k=0;k<r.raw_pixels.size();++k)meta<<(k?",":"")<<r.raw_pixels[k];
      meta<<"],\n  \"included\": "<<r.included<<", \"outside\": "<<r.outside<<", \"nonempty_cells\": "<<nonempty<<",\n"
          <<"  \"method\": \""<<method<<"\",\n"
          <<"  \"fractions_filename\": \""<<fraction_file<<"\",\n"
          <<"  \"original_science_scope\": \""<<science_scope<<"\",\n"
          <<"  \"point_counts_are_not_pixel_areas\": true,\n"
          <<"  \"evidence_status\": \"PRODUCED_UNVERIFIED\",\n"
          <<"  \"official_GLAZAS_parity\": \"NOT_RUN\",\n"
          <<"  \"lu_dat\": \"NOT_RUN\", \"p3_geo_dat\": \"NOT_RUN\"\n}\n";
      require(bool(meta),"P2_GLCC_MANIFEST_WRITE_FAILED");
    }catch(...){fs::remove_all(dest);throw;}
    std::cout<<"P2_GLCC_REAL_SOURCE_SHA=VERIFIED METHOD="<<method<<" PRODUCED_UNVERIFIED INCLUDED="<<r.included
             <<" OUTSIDE="<<r.outside<<" ORIGINAL_GLAZAS_PARITY=NOT_RUN P3=NOT_RUN\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
