#pragma once
// GLCC CLI modes are unambiguous and scoped. Legacy GEN is kept as the
// backwards-compatible default. The separately selected real-source direct
// LAEA production mode requires explicit --production-direct until the
// original Fortran LFINAL=T/F science gate passes on that production path.
#include <string_view>
namespace cteas::reconstruction::geo {
struct GlccCliModes {
  bool valid=false,qa_submesh=false,direct_probe=false,production_direct=false;
};
inline GlccCliModes glcc_cli_modes(int argc,const char* const argv[]) {
  GlccCliModes m{};
  if(argc<10||argc>13||argv==nullptr)return m;
  int n=10;
  if(n<argc && argv[n]!=nullptr &&
     std::string_view(argv[n])=="--production-direct") {
    m.production_direct=true;++n;
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
