#pragma once
// G6 dynamic numerical GEO.DAT v2.1, original READGE selected gridded mode.
// Independent adapter; the frozen read_geo_50 remains unchanged and authoritative
// for the Hefei 143 h reference. Strict WGS-84 UTM, IOPT1=1, others=2.
// No main real-case P6D physics is unlocked by this reader alone.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6g {
struct GeoGrid {
    int nx=0,ny=0,zone=0;
    char hemisphere='N';
    float xorigin_km=0.0f,yorigin_km=0.0f,grid_km=0.0f;
    int nlu=0,iwat1=0,iwat2=0;
    std::vector<int> valid_categories;
    std::vector<int> landuse;
    std::vector<float> terrain_m,z0_m,albedo,bowen,hcg,qf,lai;
};

struct GeoGridSpec {
    int nx,ny,zone;
    char hemisphere;
    double xorigin_km,yorigin_km,spacing_km;
};

inline void geo_require(bool yes,const char* reason){
    if(!yes)throw std::runtime_error(reason);
}
inline std::string geo_trim(const std::string& input) {
    const auto first=input.find_first_not_of(" \r\n\t");
    if(first==std::string::npos)return {};
    const auto last=input.find_last_not_of(" \r\n\t");
    return input.substr(first,last-first+1);
}
inline std::string geo_line(std::istream& in,const char* name){
    std::string line;
    geo_require(static_cast<bool>(std::getline(in,line)),name);
    return line;
}
// Fortran READGE list-directed input: each real-grid row is a single READ
// statement, which may span multiple physical file lines. Data tokens are
// comma- or whitespace-delimited; comments are allowed on scalar headers,
// never on grid/landuse rows.
inline std::vector<double> geo_numbers(std::string value,bool comment=false){
    if(comment){
        auto p=value.find(" - ");
        if(p!=std::string::npos)value.resize(p);
    }
    std::replace(value.begin(),value.end(),',',' ');
    std::istringstream in(value);
    std::vector<double> result;
    std::string token;
    while(in>>token){
        std::replace(token.begin(),token.end(),'D','E');
        std::replace(token.begin(),token.end(),'d','e');
        std::size_t consumed=0;
        double x=0;
        try{x=std::stod(token,&consumed);}
        catch(const std::exception&){throw std::runtime_error("nonnumeric GEO.DAT token");}
        geo_require(consumed==token.size()&&std::isfinite(x),
                    "malformed/nonfinite GEO.DAT numeric value");
        result.push_back(x);
    }
    return result;
}
inline std::vector<double> geo_grid_row(std::istream& in,int nx) {
    std::vector<double> result;
    while(result.size()<static_cast<std::size_t>(nx)) {
        auto line=geo_line(in,"truncated GEO.DAT grid");
        auto part=geo_numbers(line);
        geo_require(!part.empty()&&result.size()+part.size()<=static_cast<std::size_t>(nx),
                    "GEO.DAT grid wrong row width");
        result.insert(result.end(),part.begin(),part.end());
    }
    return result;
}
inline int geo_integer(double value) {
    geo_require(std::isfinite(value)&&
                value>=static_cast<double>(std::numeric_limits<int>::min())&&
                value<=static_cast<double>(std::numeric_limits<int>::max())&&
                static_cast<double>(static_cast<int>(value))==value,
                "GEO.DAT expected exact integer");
    return static_cast<int>(value);
}
inline double geo_scalar(std::istream& in,const char* label) {
    const auto numbers=geo_numbers(geo_line(in,label),true);
    geo_require(numbers.size()==1,"GEO.DAT scalar control requires exactly one value");
    return numbers[0];
}
inline void geo_field(std::istream& in,std::vector<float>& field,int nx,int ny) {
    field.resize(static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny));
    for(int j=ny-1;j>=0;--j){
        const auto row=geo_grid_row(in,nx);
        for(int i=0;i<nx;++i){
            const double value=row[static_cast<std::size_t>(i)];
            geo_require(value>=-std::numeric_limits<float>::max()&&
                        value<=std::numeric_limits<float>::max(),
                        "GEO.DAT field outside float32");
            field[static_cast<std::size_t>(j)*static_cast<std::size_t>(nx)+static_cast<std::size_t>(i)]=static_cast<float>(value);
        }
    }
}
inline GeoGrid read_geo_dynamic(const std::string& path,const GeoGridSpec& expected) {
    constexpr std::size_t MAX_CELLS=4000000;
    geo_require(expected.nx>0&&expected.ny>0&&
                static_cast<std::size_t>(expected.nx)<=MAX_CELLS/static_cast<std::size_t>(expected.ny),
                "G6 grid shape invalid or exceeds guarded allocation limit");
    geo_require(expected.zone>=1&&expected.zone<=60&&
                (expected.hemisphere=='N'||expected.hemisphere=='S')&&
                std::isfinite(expected.xorigin_km)&&std::isfinite(expected.yorigin_km)&&
                std::isfinite(expected.spacing_km)&&expected.spacing_km>0,
                "G6 invalid UTM grid specification");
    std::ifstream file(path);
    geo_require(static_cast<bool>(file),"GEO.DAT file unavailable");
    auto id=geo_line(file,"missing GEO.DAT identity");
    geo_require(geo_trim(id.substr(0,std::min<std::size_t>(16,id.size())))=="GEO.DAT"&&
                id.size()>=32 && geo_trim(id.substr(16,16))=="2.1",
                "only original GEO.DAT v2.1 accepted");
    const int ncomment=geo_integer(geo_scalar(file,"GEO comment count"));
    geo_require(ncomment>=0&&ncomment<=10000,"GEO.DAT comment count invalid");
    for(int k=0;k<ncomment;++k)(void)geo_line(file,"truncated GEO comments");
    geo_require(geo_trim(geo_line(file,"missing GEO CRS"))=="UTM",
                "only original UTM projection supported");
    const auto utm=geo_trim(geo_line(file,"missing GEO zone/hemisphere"));
    {
        std::istringstream scan(utm);
        int zone=0;char hemisphere='\0';std::string extra;
        scan>>zone>>hemisphere;
        geo_require(zone==expected.zone&&hemisphere==expected.hemisphere&&!(scan>>extra),
                    "GEO.DAT UTM zone/hemisphere differs from model");
    }
    const auto datum=geo_line(file,"missing GEO datum");
    geo_require(geo_trim(datum.substr(0,std::min<std::size_t>(8,datum.size())))=="WGS-84",
                "only WGS-84 GEO datum supported");
    const auto dimensions=geo_numbers(geo_line(file,"missing GEO grid"));
    geo_require(dimensions.size()==6 &&
                geo_integer(dimensions[0])==expected.nx &&
                geo_integer(dimensions[1])==expected.ny,
                "GEO.DAT NX/NY differs from CALMET controls");
    geo_require(std::abs(dimensions[2]-expected.xorigin_km)<=0.00051&&
                std::abs(dimensions[3]-expected.yorigin_km)<=0.00051,
                "GEO.DAT grid origin differs from CALMET controls");
    geo_require(std::abs(dimensions[4]-expected.spacing_km)<=1.0e-6&&
                std::abs(dimensions[5]-expected.spacing_km)<=1.0e-6,
                "GEO.DAT DX/DY differ from CALMET DGRIDKM");
    auto units=geo_line(file,"GEO units absent");
    geo_require(units.size()>=4&&units.substr(0,4)=="KM  ",
                "GEO xy units are not KM");
    GeoGrid out;
    out.nx=expected.nx;out.ny=expected.ny;
    out.zone=expected.zone;out.hemisphere=expected.hemisphere;
    out.grid_km=static_cast<float>(dimensions[4]);
    out.xorigin_km=static_cast<float>(dimensions[2]);
    out.yorigin_km=static_cast<float>(dimensions[3]);
    geo_require(geo_integer(geo_scalar(file,"GEO IOPT1"))==1,
                "land-use custom category path only");
    const auto lu=geo_numbers(geo_line(file,"missing GEO LU category header"),true);
    geo_require(lu.size()==3,"invalid GEO land-use category header");
    out.nlu=geo_integer(lu[0]);out.iwat1=geo_integer(lu[1]);out.iwat2=geo_integer(lu[2]);
    geo_require(out.nlu>0&&out.nlu<=200,
                "GEO.DAT NLU must be 1..200");
    auto categories=geo_numbers(geo_line(file,"GEO categories absent"),true);
    geo_require(categories.size()==static_cast<std::size_t>(out.nlu),
                "GEO land-use categories truncated");
    for(double d:categories)out.valid_categories.push_back(geo_integer(d));
    out.landuse.resize(static_cast<std::size_t>(out.nx)*static_cast<std::size_t>(out.ny));
    for(int j=out.ny-1;j>=0;--j){
        const auto row=geo_grid_row(file,out.nx);
        for(int i=0;i<out.nx;++i){
            const int cat=geo_integer(row[static_cast<std::size_t>(i)]);
            geo_require(std::find(out.valid_categories.begin(),
                                  out.valid_categories.end(),cat)
                        !=out.valid_categories.end(),
                        "GEO land-use cell outside declared category set");
            out.landuse[static_cast<std::size_t>(j)*static_cast<std::size_t>(out.nx)+static_cast<std::size_t>(i)]=cat;
        }
    }
    geo_require(geo_scalar(file,"terrain HTFAC")==1.0,
                "selected GEO input requires terrain heights already in metres");
    geo_field(file,out.terrain_m,out.nx,out.ny);
    const std::array<std::vector<float>*,6> destinations{
        &out.z0_m,&out.albedo,&out.bowen,&out.hcg,&out.qf,&out.lai
    };
    for(auto* field:destinations){
        geo_require(geo_integer(geo_scalar(file,"GEO gridded IOPT"))==2,
                    "GEO table/default options outside selected scope");
        geo_field(file,*field,out.nx,out.ny);
    }
    std::string extra;
    while(std::getline(file,extra)){
        geo_require(geo_trim(extra).empty(),"unexpected GEO.DAT extra data");
    }
    for(float value:out.z0_m)geo_require(value>0,"invalid surface roughness");
    return out;
}
} // namespace cteas::calmet::p6g
