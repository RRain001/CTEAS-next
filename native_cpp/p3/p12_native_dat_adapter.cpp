// Strict data-only serialization of native P1/P2 CSV for frozen Hefei P3.
// No terrain/land-use physics, imputation, or general-case authority.
#include <array>
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
 if(argc!=4||(std::string(argv[1])!="terrain"&&std::string(argv[1])!="landuse")){
  std::cerr<<"usage: cteas_p12_to_p3_dat terrain|landuse SOURCE_NATIVE_CSV OUTPUT_DAT\n";return 2;
 }
 try{
  bool t=std::string(argv[1])=="terrain";
  auto data=t?terrain_file(argv[2]):landuse_file(argv[2]);
  safe_write(argv[3],data);
  std::cout<<"P12_P3_SCOPED_FORMAT_WRITTEN bytes="<<data.size()<<"\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
