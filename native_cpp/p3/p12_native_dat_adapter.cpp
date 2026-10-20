// Strict data-only serialization of native P1/P2 CSV for frozen Hefei P3.
// No terrain/land-use physics, imputation, or general-case authority.
#include "cteas/geo/grid_origin.hpp"
#include <array>
#include <cstdint>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
constexpr int SIDE=50;
constexpr int CELLS=2500;
constexpr std::array<int,38> CATS={11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,51,52,53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92};
void require(bool good,const std::string& what){if(!good)throw std::runtime_error("P12→P3: "+what);}
std::vector<std::string> csv(const std::string& line){
 std::vector<std::string> row;std::istringstream is(line);std::string col;
 while(std::getline(is,col,','))row.push_back(col);
 if(!line.empty()&&line.back()==',')row.emplace_back();
 return row;
}
int numint(const std::string& str){
 std::size_t used=0;long long x=std::stoll(str,&used);
 require(used==str.size()&&x>=0&&x<=1000000,"invalid integer");return static_cast<int>(x);
}
double numfloat(const std::string& str){
 std::size_t used=0;double x=std::stod(str,&used);
 require(used==str.size()&&std::isfinite(x),"nonfinite or malformed numeric");return x;
}
void check_cell(const std::vector<std::string>& row,int n){
 require(row.size()>=2&&numint(row[0])==n%SIDE+1&&numint(row[1])==n/SIDE+1,
         "cell index/order mismatch");
}
void header(std::ostream& out,bool terrain){
 out<<std::left<<std::setw(16)<<(terrain?"TERREL.DAT":"LU.DAT")
    <<std::setw(16)<<(terrain?"2.0":"2.1")
    <<(terrain?"Header structure with coordinate parameters":"Coordinate parameters and LandUse categories")<<"\n"
    <<"   2\n"
    <<"Produced by CTEAS C++20 scoped P1/P2 serializer (not original Fortran)\n"
    <<"Frozen Hefei 2022 research profile; provenance preserved in source CSV\n";
 if(!terrain)out<<"FRACTION\n";
 out<<"UTM\n  50N\nWGS-84  02-21-2003\n"
    <<"      50      50     510.885    3531.269       0.100       0.100";
 if(!terrain)out<<"    38";
 out<<"\nKM  M\n";
 if(terrain)out<<"W_E N_S\n";
 else{out<<std::right;for(int c:CATS)out<<std::setw(6)<<c;out<<"\n";}
}
std::string terrain_file(const std::string& source){
 std::ifstream in(source);require(bool(in),"cannot open P1 CSV");
 std::string line;require(bool(std::getline(in,line))&&line=="i,j,hits,elevation_m","wrong P1 header");
 std::array<double,CELLS> heights{};
 for(int n=0;n<CELLS;n++){
  require(bool(std::getline(in,line)),"P1 rows truncated");
  auto v=csv(line);require(v.size()==4,"wrong P1 width");check_cell(v,n);
  require(numint(v[2])>0,"uncovered terrain cell");
  heights[n]=numfloat(v[3]);require(heights[n]>=-998.,"unfilled terrain");
 }
 require(!std::getline(in,line),"unexpected extra P1 row");
 std::ostringstream out;header(out,true);
 for(int j=SIDE-1;j>=0;j--)for(int i=0;i<SIDE;i++){
  std::ostringstream z;z<<std::fixed<<std::setw(8)<<std::setprecision(1)<<heights[j*SIDE+i];
  require(z.str().size()==8,"F8.1 terrain field overflow");
  out<<z.str();if((i+1)%10==0)out<<"\n";
 }
 return out.str();
}
std::string landuse_file(const std::string& source){
 std::ifstream in(source);require(bool(in),"cannot open P2 CSV");
 std::string line;require(bool(std::getline(in,line)),"P2 header missing");
 std::ostringstream expected;expected<<"i,j,samples";
 for(int c:CATS)expected<<",cat"<<c;
 require(line==expected.str(),"wrong P2 category order or count");
 std::array<std::array<double,38>,CELLS> cells{};
 for(int n=0;n<CELLS;n++){
  require(bool(std::getline(in,line)),"P2 rows truncated");
  auto v=csv(line);require(v.size()==41,"wrong P2 row width");check_cell(v,n);
  require(numint(v[2])>0,"missing landuse sample cell");
  double sum=0,printed=0;
  for(int k=0;k<38;k++){
   double x=numfloat(v[3+k]);require(x>=0&&x<=1,"bad fraction");
   std::ostringstream f;f<<std::fixed<<std::setprecision(3)<<x;
   cells[n][k]=numfloat(f.str());sum+=x;printed+=cells[n][k];
  }
  require(sum>=0.96&&sum<=1.005&&printed>=0.96&&printed<=1.005,
          "incomplete original landuse fraction coverage");
 }
 require(!std::getline(in,line),"unexpected extra P2 row");
 std::ostringstream out;header(out,false);
 for(int n=0;n<CELLS;n++){
  out<<std::right<<std::setw(5)<<n%SIDE+1<<std::setw(5)<<n/SIDE+1;
  for(double x:cells[n])out<<" "<<std::fixed<<std::setw(5)<<std::setprecision(3)<<x;
  out<<"   .\n";
 }
 return out.str();
}

struct DynamicGrid {
 int zone=0,nx=0,ny=0;
 std::string hemisphere,xtext,ytext;
 double x=0,y=0,d=0;
 [[nodiscard]] bool frozen() const {
  return zone==50&&hemisphere=="N"&&nx==50&&ny==50&&
         xtext=="510.885"&&ytext=="3531.269"&&std::abs(d-.100)<1.e-9;
 }
};
int positive(const std::string& literal,int upper,const std::string& label) {
 require(!literal.empty()&&literal.find_first_not_of("0123456789")==std::string::npos,
         "invalid positive integer "+label);
 std::size_t n=0;
 const long long value=std::stoll(literal,&n);
 require(n==literal.size()&&value>0&&value<=upper,"invalid dimension "+label);
 return static_cast<int>(value);
}
DynamicGrid make_dynamic_grid(char** argv) {
 DynamicGrid g;
 g.zone=positive(argv[5],60,"zone");g.hemisphere=argv[6];
 require(g.hemisphere=="N"||g.hemisphere=="S","WGS84 UTM hemisphere must be N or S");
 g.xtext=argv[7];g.ytext=argv[8];
 g.x=cteas::reconstruction::geo::three_decimal_origin_km(g.xtext);
 g.y=cteas::reconstruction::geo::three_decimal_origin_km(g.ytext);
 require(g.x>=100&&g.x<=900&&g.y>=0&&g.y<=10000,"UTM numeric origin outside range");
 g.nx=positive(argv[9],500,"NX");g.ny=positive(argv[10],500,"NY");
 require(static_cast<std::int64_t>(g.nx)*g.ny<=250000,"P3 current 250000-cell budget");
 std::size_t consumed=0;const std::string spacing=argv[11];
 g.d=std::stod(spacing,&consumed);
 require(consumed==spacing.size()&&std::isfinite(g.d)&&g.d>=.001&&g.d<=100.&&
         std::abs(g.d*1000.-std::round(g.d*1000.))<1.e-7,
         "DGRIDKM must be whole metres within supported bounds");
 require(g.x+g.nx*g.d<=1000.&&g.y+g.ny*g.d<=10000.,
         "dynamic grid footprint beyond UTM numeric bounds");
 return g;
}
void dynamic_header(std::ostream& out,bool terrain,const DynamicGrid& g) {
 out<<std::left<<std::setw(16)<<(terrain?"TERREL.DAT":"LU.DAT")
    <<std::setw(16)<<(terrain?"2.0":"2.1")
    <<(terrain?"Header structure with coordinate parameters":
                "Coordinate parameters and LandUse categories")<<"\n"
    <<"   2\n"
    <<"Produced by CTEAS C++20 scoped P1/P2 serializer (not original Fortran)\n"
    <<"Dynamic WGS84 UTM case; source SHA and case SHA in independent evidence\n";
 if(!terrain)out<<"FRACTION\n";
 out<<"UTM\n  "<<g.zone<<g.hemisphere<<"\nWGS-84  02-21-2003\n"
    <<std::right<<std::setw(8)<<g.nx<<std::setw(8)<<g.ny
    <<std::fixed<<std::setprecision(3)
    <<std::setw(12)<<g.x<<std::setw(12)<<g.y
    <<std::setw(12)<<g.d<<std::setw(12)<<g.d;
 if(!terrain)out<<std::setw(6)<<38;
 out<<"\nKM  M\n";
 if(terrain)out<<"W_E N_S\n";
 else for(std::size_t k=0;k<CATS.size();++k)
   out<<(k?"":"")<<std::setw(6)<<CATS[k]<<(k+1==CATS.size()?"\n":"");
}
void dynamic_cell(const std::vector<std::string>& row,int index,int nx) {
 require(row.size()>=2&&numint(row[0])==index%nx+1&&
         numint(row[1])==index/nx+1,"dynamic cell index/order mismatch");
}
std::string dynamic_terrain_file(const std::string& source,const DynamicGrid& g) {
 if(g.frozen())return terrain_file(source);
 std::ifstream in(source);require(bool(in),"cannot open P1 dynamic CSV");
 std::string line;require(bool(std::getline(in,line))&&line=="i,j,hits,elevation_m",
                            "wrong dynamic P1 header");
 std::vector<double> elevations(static_cast<std::size_t>(g.nx)*g.ny);
 for(std::size_t n=0;n<elevations.size();++n) {
  require(bool(std::getline(in,line)),"dynamic P1 rows truncated");
  auto row=csv(line);require(row.size()==4,"dynamic P1 wrong width");
  dynamic_cell(row,static_cast<int>(n),g.nx);
  require(numint(row[2])>0,"dynamic uncovered P1 terrain cell");
  const double h=numfloat(row[3]);
  require(h>=-998.,"dynamic terrain missing; no imputation");
  elevations[n]=h;
 }
 require(!std::getline(in,line),"dynamic P1 unexpected extra row");
 std::ostringstream out;dynamic_header(out,true,g);
 for(int j=g.ny-1;j>=0;--j)for(int i=0;i<g.nx;++i){
  std::ostringstream token;
  token<<std::fixed<<std::setw(8)<<std::setprecision(1)
       <<elevations[static_cast<std::size_t>(j*g.nx+i)];
  require(token.str().size()==8,"dynamic TERREL F8.1 overflow");
  out<<token.str();
  if((i+1)%10==0||i+1==g.nx)out<<"\n";
 }
 return out.str();
}
std::string dynamic_landuse_file(const std::string& source,const DynamicGrid& g) {
 if(g.frozen())return landuse_file(source);
 std::ifstream in(source);require(bool(in),"cannot open P2 dynamic fractions CSV");
 std::string line;require(bool(std::getline(in,line)),"dynamic P2 header missing");
 std::ostringstream expected;expected<<"i,j,samples";
 for(int c:CATS)expected<<",cat"<<c;
 require(line==expected.str(),"dynamic P2 class order/count mismatch");
 const std::size_t cells=static_cast<std::size_t>(g.nx)*g.ny;
 std::ostringstream out;dynamic_header(out,false,g);
 for(std::size_t n=0;n<cells;++n) {
  require(bool(std::getline(in,line)),"dynamic P2 rows truncated");
  const auto values=csv(line);require(values.size()==41,"dynamic P2 wrong CSV width");
  dynamic_cell(values,static_cast<int>(n),g.nx);
  require(numint(values[2])>0,"dynamic P2 missing sample cell");
  double total=0,rounded=0;
  std::array<double,38> fractions{};
  for(int k=0;k<38;++k) {
   const double v=numfloat(values[static_cast<std::size_t>(3+k)]);
   require(v>=0&&v<=1,"dynamic P2 fraction outside [0,1]");
   total+=v;
   std::ostringstream token;token<<std::fixed<<std::setprecision(3)<<v;
   fractions[static_cast<std::size_t>(k)]=numfloat(token.str());
   rounded+=fractions[static_cast<std::size_t>(k)];
  }
  require(total>=.96&&total<=1.005&&rounded>=.96&&rounded<=1.005,
          "dynamic P2 incomplete fraction coverage");
  out<<std::right<<std::setw(5)<<static_cast<int>(n%g.nx)+1
     <<std::setw(5)<<static_cast<int>(n/g.nx)+1;
  for(double v:fractions)
   out<<" "<<std::fixed<<std::setw(5)<<std::setprecision(3)<<v;
  out<<"   .\n";
 }
 require(!std::getline(in,line),"dynamic P2 unexpected extra row");
 return out.str();
}

void safe_write(const std::filesystem::path& dest,const std::string& contents){
 namespace fs=std::filesystem;
 require(!fs::exists(dest),"destination already exists; refusing overwrite");
 fs::path partial=dest.string()+".partial";
 require(!fs::exists(partial),"stale partial output exists");
 try{
  {std::ofstream out(partial,std::ios::binary);
   require(bool(out),"cannot create output");out<<contents;out.flush();
   require(bool(out),"partial output write failed");}
  fs::rename(partial,dest);
 }catch(...){std::error_code ec;fs::remove(partial,ec);throw;}
}
}
int main(int argc,char** argv){
 const bool dynamic=argc==12&&std::string(argv[1])=="--grid";
 const int mode_index=dynamic?2:1;
 if((!dynamic&&argc!=4)||
    (std::string(argv[mode_index])!="terrain"&&
     std::string(argv[mode_index])!="landuse")){
  std::cerr<<"usage (frozen): cteas_p12_to_p3_dat terrain|landuse SOURCE_NATIVE_CSV OUTPUT_DAT\n"
           <<"usage (case): cteas_p12_to_p3_dat --grid terrain|landuse SOURCE_NATIVE_CSV OUTPUT_DAT UTM_ZONE N_OR_S XREFKM YREFKM NX NY DGRIDKM\n";
  return 2;
 }
 try{
  const bool t=std::string(argv[mode_index])=="terrain";
  const std::string data=dynamic?([&]{
    auto g=make_dynamic_grid(argv);
    return t?dynamic_terrain_file(argv[3],g):dynamic_landuse_file(argv[3],g);
  }()):(t?terrain_file(argv[2]):landuse_file(argv[2]));
  safe_write(argv[dynamic?4:3],data);
  std::cout<<"P12_P3_FORMAT_WRITTEN bytes="<<data.size()
           <<" original_science=NOT_RUN\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
