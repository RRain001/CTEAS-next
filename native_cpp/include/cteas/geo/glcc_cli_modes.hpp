#pragma once
// GLCC CLI optional modes: parse once and use the SAME decision for
// submesh trace emission and direct-LAEA candidate replay.
// Standalone header permits synthetic tests without real 156MB GLCC bytes.
#include <string_view>
namespace cteas::reconstruction::geo {
struct GlccCliModes {
  bool valid=false,qa_submesh=false,direct_probe=false;
};
inline GlccCliModes glcc_cli_modes(int argc,const char* const argv[]) {
  if(argc==10)return {true,false,false};
  if(argc>=11 && argc<=12 && argv!=nullptr && argv[10]!=nullptr &&
     std::string_view(argv[10])=="--qa-submesh") {
    if(argc==11)return {true,true,false};
    if(argv[11]!=nullptr && std::string_view(argv[11])=="--probe-direct")
      return {true,true,true};
  }
  return {};
}
} // namespace cteas::reconstruction::geo
