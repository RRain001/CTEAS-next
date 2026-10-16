#include "cteas/p6/diagno_segment.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
int main(int argc,char** argv){
 try{
  if(argc!=4)throw std::invalid_argument("usage: stage INPUT FIELD_CSV BOUNDARY_CSV");
  using namespace cteas::calmet::p6;
  std::ifstream f(argv[1]);if(!f)throw std::runtime_error("input unavailable");
  SmoothInput s;s.nx=50;s.ny=50;s.nz=9;s.lake_breeze=false;
  std::vector<float> dz;
  auto read=[&](auto& dst,std::size_t count) {
      dst.resize(count);
      for(auto& x:dst)if(!(f>>x))
        throw std::runtime_error("DIAGNO selected segment input truncated");
  };
  read(dz,9);read(s.passes_per_layer,9);read(s.u_mps,22500);
  read(s.v_mps,22500);read(s.ub_west_east_mps,900);
  read(s.vb_south_north_mps,900);
  const auto o=original_smooth_divcel_w(std::move(s),100.f,100.f,dz);
  std::ofstream out(argv[2]),bound(argv[3]);
  if(!out||!bound)throw std::runtime_error("DIAGNO selected output unavailable");
  out<<std::setprecision(12)<<"i,j,k,u,v,div,w_below,w_above\n";
  bound<<std::setprecision(12);
  for(int k=0;k<9;++k)for(int j=0;j<50;++j)for(int i=0;i<50;++i){
    const auto n=std::size_t(k)*2500+std::size_t(j)*50+std::size_t(i);
    out<<i+1<<','<<j+1<<','<<k+1<<','<<o.u_mps[n]<<','<<o.v_mps[n]<<','
       <<o.divergence_per_s[n]<<','<<o.w_face_mps[n]<<','
       <<o.w_face_mps[n+2500]<<'\n';
  }
  for(int k=0;k<9;++k)for(int side=0;side<2;++side){
    for(int j=0;j<50;++j)
      bound<<"U "<<k+1<<' '<<side+1<<' '<<j+1<<' '<<
        o.ub_west_east_mps[std::size_t(k)*100+std::size_t(side)*50+std::size_t(j)]<<'\n';
    for(int i=0;i<50;++i)
      bound<<"V "<<k+1<<' '<<side+1<<' '<<i+1<<' '<<
        o.vb_south_north_mps[std::size_t(k)*100+std::size_t(side)*50+std::size_t(i)]<<'\n';
  }
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
