// Test-only fixture reader: accepts sparse artificial 156MB source. Never
// issue source acceptance; the production CLI requires a fixed official SHA.
#include "cteas/geo/glcc_raw_fractions.hpp"
#include "cteas/geo/glcc_direct_laea_probe.hpp"
#include "cteas/geo/glcc_cli_modes.hpp"
#include <bit>
#include <cstdint>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
int main(int argc,char** argv){
  if(argc!=10)return 2;
  try{
    using namespace cteas::reconstruction::geo;
    // Regression for real manual run #39178123151: two optional flags used
    // to satisfy argc==12 and silently disabled QA, producing zero candidate
    // counts and NATIVE_QA_MISSING_OR_SYMLINK. Test the common parser.
    const char* names[12]={"cli","img","out","32650","510.885",
                            "3531.269","0.100","50","50","20",
                            "--qa-submesh","--probe-direct"};
    const auto base=glcc_cli_modes(10,names);
    const auto qa=glcc_cli_modes(11,names);
    const auto full=glcc_cli_modes(12,names);
    if(!base.valid||base.qa_submesh||base.direct_probe||
       !qa.valid||!qa.qa_submesh||qa.direct_probe||
       !full.valid||!full.qa_submesh||!full.direct_probe)
      throw std::runtime_error("GLCC_TWO_OPTION_MODES_REGRESSION");
    names[11]="--unrecognized";
    if(glcc_cli_modes(12,names).valid)
      throw std::runtime_error("GLCC_UNKNOWN_OPTION_ACCEPTED");
    names[11]="--probe-direct";names[10]="--probe-direct";
    if(glcc_cli_modes(11,names).valid||glcc_cli_modes(12,names).valid)
      throw std::runtime_error("GLCC_DIRECT_PROBE_WITHOUT_QA_ACCEPTED");
    const int epsg=std::stoi(argv[2]);
    const double x=std::stod(argv[3]),y=std::stod(argv[4]),dx=std::stod(argv[5]);
    const auto nx=std::size_t(std::stoul(argv[6])),ny=std::size_t(std::stoul(argv[7]));
    const int mesh=std::stoi(argv[8]);
    // Issue #53: actual COORDLIB has implicitly REAL*4 XMULTO=0.001.
    // PR #96 methodology: assert the exact staged REAL*4 bit pattern,
    // not a nearby floating-point value or just a successful projection.
    // ULP-sensitive inputs intentionally distinguish multiply-by-REAL*4
    // from the previous /1000.0 diagnostic shortcut (both metre lanes).
    {
      const float east=coordlib_real4_km_from_metres(511085.175);
      const float north=coordlib_real4_km_from_metres(3534540.04);
      if(std::bit_cast<std::uint32_t>(east)!=0x43ff8ae8u ||
         std::bit_cast<std::uint32_t>(north)!=0x455ce8a5u)
        throw std::runtime_error("GLCC_COORDLIB_REAL4_XMULTO_BITS_MISMATCH");
      if(east==static_cast<float>(511085.175/1000.) ||
         north==static_cast<float>(3534540.04/1000.))
        throw std::runtime_error("GLCC_REAL4_XMULTO_REGRESSION_NONDISCRIMINATING");
      const double near_edge_m=510984.9765;
      const float old_shortcut=static_cast<float>(near_edge_m/1000.);
      const float original_stage=coordlib_real4_km_from_metres(near_edge_m);
      const float x0=510.885f, step=0.100f;
      const auto legacy_cell_x=[x0,step](float km) {
        const float delta=km-x0;
        return static_cast<int>(delta/step)+(delta>=0.f?1:0);
      };
      if(legacy_cell_x(original_stage)!=2 || legacy_cell_x(old_shortcut)!=1)
        throw std::runtime_error("GLCC_REAL4_XMULTO_GRID_BOUNDARY_REGRESSION");
    }
    // Synthetic-only projection test. This candidate does not replace native D1.
    {
      DirectLaeaProbe direct(32650);
      const auto projected=direct.project(9614,4210,18,17,20,
                                          510.885f,3531.269f,0.100f);
      if(std::fabs(projected.x_km-511.485107f)>0.001f ||
         std::fabs(projected.y_km-3531.31641f)>0.001f ||
         projected.i<1||projected.i>50||projected.j<1||projected.j>50)
        throw std::runtime_error("DIRECT_LAEA_CANDIDATE_PROJECTION_BROKEN");
      bool invalid_zone_rejected=false;
      try {DirectLaeaProbe outside_scope(32651);}
      catch(const std::invalid_argument&) {invalid_zone_rejected=true;}
      if(!invalid_zone_rejected)
        throw std::runtime_error("DIRECT_LAEA_CANDIDATE_SCOPE_BROKEN");
    }
    const auto r=compute_glcc_gen_replay(argv[1],{x,y,dx,nx,ny},epsg,mesh);
    // Software-only synthetic replay: enabling optional coordinate QA MUST NOT
    // mutate any production GLCC category hits, grid counts, or coverage.
    const auto traced=compute_glcc_gen_replay(argv[1],{x,y,dx,nx,ny},epsg,mesh,true);
    if(traced.counts!=r.counts||traced.cell_samples!=r.cell_samples||
       traced.included!=r.included||traced.outside!=r.outside||
       traced.raw_pixels!=r.raw_pixels||!r.diagnostic_mesh.empty()||
       traced.diagnostic_mesh.size()!=traced.included+traced.outside){
      std::cerr<<"GLCC_QA_MESH_CHANGED_PRODUCTION_COUNTS\n";return 5;
    }
    std::ofstream out(argv[9]);if(!out)return 3;
    out<<"i,j,samples";
    for(int k:kGlccUsgs92Classes)out<<",cat"<<k;
    out<<"\n"<<std::fixed<<std::setprecision(12);
    for(std::size_t j=0;j<ny;++j)for(std::size_t i=0;i<nx;++i){
      const std::size_t cell=j*nx+i;
      out<<i+1<<","<<j+1<<","<<r.cell_samples[cell];
      for(std::size_t k=0;k<kGlccUsgs92Classes.size();++k){
        if(r.cell_samples[cell])out<<","<<r.fraction(i,j,k);
        else out<<",MISSING";
      }
      out<<"\n";
    }
    if(!out)return 4;
    std::cout<<"TEST_SYNTHETIC_ONLY INCLUDED="<<r.included<<" OUTSIDE="<<r.outside
             <<" GLCC_RAW0="<<r.raw_pixels[0]<<" GLCC_RAW16="<<r.raw_pixels[16]<<"\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
