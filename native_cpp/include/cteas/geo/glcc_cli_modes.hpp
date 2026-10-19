#pragma once
// Issue #53 P2-A: the original-GLAZAS-parity scoped direct LAEA production
// algorithm is the CLI default (real GLCC Run #39188861410).
// Historical GEN seven-decimal geographic replay is explicitly opt-in via
// --gen-replay. --production-direct is retained as a compatibility alias.
// QA and independent direct probe remain opt-in and are never substituted
// for the selected production D1 fractions and integer HITS.
#include <string_view>
namespace cteas::reconstruction::geo {
struct GlccCliModes {
  bool valid=false,qa_submesh=false,direct_probe=false,production_direct=true;
};
inline GlccCliModes glcc_cli_modes(int argc,const char* const argv[]) {
  GlccCliModes m{};
  if(argc<10||argc>13||argv==nullptr)return m;
  int n=10;
  if(n<argc && argv[n]!=nullptr) {
    const auto mode=std::string_view(argv[n]);
    if(mode=="--gen-replay") {
      m.production_direct=false;++n;
    } else if(mode=="--production-direct") {
      ++n;
    }
  }
  if(n<argc && argv[n]!=nullptr &&
     std::string_view(argv[n])=="--qa-submesh") {
    m.qa_submesh=true;++n;
  }
  if(n<argc && argv[n]!=nullptr &&
     std::string_view(argv[n])=="--probe-direct" && m.qa_submesh) {
    m.direct_probe=true;++n;
  }
  m.valid=(n==argc);
  return m;
}
} // namespace cteas::reconstruction::geo
