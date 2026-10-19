// Issue #123 D9: scientific candidate for original GLAZAS 38-class
// integer NGRID recount. Uses the existing selected P2-A source mesh;
// no production CLI or frozen P2-B area code is modified.
#include "cteas/geo/ctgproc_original_sampling_recount.hpp"
#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

using namespace cteas::reconstruction::geo;
namespace fs=std::filesystem;

int main(int argc,char** argv) {
  try {
    if(argc!=4)throw std::runtime_error("D9_ARGS_GLCC_BLN_OUTPUT_CSV");
    const fs::path img=argv[1],bln=argv[2],dest=argv[3];
    if(fs::exists(dest)||fs::is_symlink(fs::symlink_status(dest)))
      throw std::runtime_error("D9_OUTPUT_ALREADY_EXISTS");
    if(!fs::is_regular_file(img)||fs::is_symlink(fs::symlink_status(img))||
       fs::file_size(img)!=156000000)
      throw std::runtime_error("D9_AUTHENTIC_GLCC_156MB_REQUIRED");
    // The caller must also independently verify the exact official GLCC
    // SHA and D6 genuine BLN provenance, not merely their sizes.
    const P2Grid grid{533215.,3942629.,100.,200,200};
    const auto source=compute_glcc_direct_laea(img.string(),grid,32652,10,true);
    const auto coast=OriginalBlnIptypeR4::load_coastrd_bln(
        bln,533.215f,3942.629f,553.215f,3962.629f);
    const OriginalCoastControl control{true,true,false,false,55,
                                      OriginalLanduseSource::HistoricalUsgs38};
    const auto counts=recount_glcc_original_coast_bln(source,control,&coast);
    if(counts.counts.size()!=200ULL*200*38||
       counts.samples.size()!=200ULL*200||
       counts.included+counts.rejected_coast+counts.outside!=
       source.included+source.outside)
      throw std::runtime_error("D9_SOURCE_RECOUNT_SHAPE_OR_CONSERVATION");
    std::ofstream f(dest,std::ios::binary);
    if(!f)throw std::runtime_error("D9_CSV_OPEN");
    f<<"i,j,samples";
    for(int c:kGlccUsgs92Classes)f<<",cat"<<c;
    f<<"\n";
    for(std::size_t j=0;j<200;++j)for(std::size_t i=0;i<200;++i) {
      const std::size_t cell=j*200+i;
      f<<i+1<<","<<j+1<<","<<counts.samples[cell];
      std::uint64_t sum=0;
      for(std::size_t k=0;k<38;++k) {
        const auto n=counts.counts[cell*38+k];
        sum+=n;
        f<<","<<n;
      }
      if(sum!=counts.samples[cell])
        throw std::runtime_error("D9_BAD_NATIVE_CELL_INTEGER_SUM");
      f<<"\n";
    }
    f.close();
    if(!f)throw std::runtime_error("D9_CSV_CLOSE");
    std::cout<<"D9_CANDIDATE_COUNTS_PRODUCED_UNVERIFIED"
             <<" included="<<counts.included
             <<" outside="<<counts.outside
             <<" rejected_coast="<<counts.rejected_coast
             <<" mesh=10 nx=200 ny=200 classes=38"
             <<" original_integer_parity=NOT_RUN\n";
    return 0;
  }catch(const std::exception& e) {
    std::cerr<<"D9_FAIL_CLOSED:"<<e.what()<<"\n";
    return 2;
  }
}
