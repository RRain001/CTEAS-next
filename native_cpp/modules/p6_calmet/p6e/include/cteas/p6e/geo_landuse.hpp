#pragma once
// Anchored reader for the MAKEGEO GEO.DAT 2.1 land-use / geophysical file,
// following the original readge/fillgeo sequence (calmet.for L27790-28380):
//   IOPT(1)     0 = built-in category table, 1 = user category table
//   [1]         NLU, IWAT1, IWAT2 then ILUCAT(1..NLU)
//               ILANDU grid (NX values on each of NY lines)
//   HTFAC       terrain height conversion factor
//               ELEV grid (NX values on each of NY lines)
//   then one marker + payload per parameter, in the order Z0, ALBEDO, BOWEN,
//   HCG, QF (and XLAI when present):
//     IOPT=0  built-in table (no payload)
//     IOPT=1  NLU category values
//     IOPT=2  gridded field, NX values on each of NY lines
// (fillgeo L6983-7030 defines the three options; the marker lines put the
// option value first and the description after it, which is how the original
// list-directed READ picks it up.)
//
// Everything is validated: grid extents against the CALMET.DAT being produced,
// the option values, the payload sizes and the physical ranges. Nothing falls
// back to a default silently.
#include <cctype>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace cteas::p6e {
struct GeoLandUse {
    int nlu=0,iwat1=0,iwat2=0;
    std::vector<int> categories;
    std::vector<int> ilandu;
    float terrain_factor=1.f;
    std::vector<float> elevation_m;
    std::vector<float> z0_m,albedo,bowen,soil_heat_fraction,anthropogenic_wm2,xlai;
};
namespace geo_detail {
// Numbers that start a line, up to the first token that is not numeric. This
// is exactly what Fortran list-directed input does with the marker lines.
inline std::vector<double> leading_numbers(const std::string& line) {
    std::vector<double> values;
    std::size_t position=0;
    while(position<line.size()) {
        while(position<line.size()&&
              (line[position]==' '||line[position]=='\t'||line[position]==','))
            ++position;
        if(position>=line.size())break;
        const auto start=position;
        if(line[position]=='+'||line[position]=='-')++position;
        bool digits=false,exponent=false;
        while(position<line.size()) {
            const char c=line[position];
            if(c>='0'&&c<='9'){digits=true;++position;}
            else if(c=='.')++position;
            else if((c=='e'||c=='E'||c=='d'||c=='D')&&digits&&!exponent){
                exponent=true;++position;
                if(position<line.size()&&(line[position]=='+'||line[position]=='-'))
                    ++position;
            } else break;
        }
        if(!digits)return values;                      // marker text begins
        try {
            values.push_back(std::stod(line.substr(start,position-start)));
        } catch(const std::exception&) {
            throw std::invalid_argument("GEO.DAT malformed number token");
        }
    }
    return values;
}
inline bool has_text(const std::string& line) {
    for(const char c:line)
        if(!(c==' '||c=='\t'||c==','||c=='.'||c=='-'||c=='+'||
             (c>='0'&&c<='9')||c=='e'||c=='E'||c=='d'||c=='D'))
            return true;
    return false;
}
} // namespace geo_detail

inline GeoLandUse read_geo_landuse(const std::string& path,
                                   int nx,int ny) {
    if(nx<1||ny<1)throw std::invalid_argument("GEO.DAT grid extent invalid");
    std::ifstream file(path);
    if(!file)throw std::invalid_argument("GEO.DAT cannot open "+path);
    std::vector<std::string> lines;
    for(std::string line;std::getline(file,line);)lines.push_back(line);
    const auto cells=static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny);
    std::size_t cursor=0;
    const auto fail=[&](const char* message) {
        throw std::invalid_argument(std::string("GEO.DAT ")+message);
    };
    // IOPT(1) marker line: leading number then descriptive text.
    int landuse_option=-1;
    for(;cursor<lines.size();++cursor) {
        std::string lowered=lines[cursor];
        for(char& c:lowered)c=static_cast<char>(std::tolower(
            static_cast<unsigned char>(c)));
        if(lowered.find("land use data")==std::string::npos)continue;
        const auto values=geo_detail::leading_numbers(lines[cursor]);
        if(values.empty())fail("land-use marker without option value");
        landuse_option=static_cast<int>(values[0]);
        break;
    }
    if(landuse_option!=1)
        fail("only IOPT(1)=1 (user land-use categories) is supported");
    GeoLandUse out;
    {
        for(++cursor;cursor<lines.size();++cursor) {
            const auto values=geo_detail::leading_numbers(lines[cursor]);
            if(values.size()>=3) {
                out.nlu=static_cast<int>(values[0]);
                out.iwat1=static_cast<int>(values[1]);
                out.iwat2=static_cast<int>(values[2]);
                ++cursor;
                break;
            }
        }
        if(out.nlu<1||out.nlu>64||out.iwat1>out.iwat2)
            fail("invalid NLU/IWAT1/IWAT2");
        std::vector<double> categories;
        for(;cursor<lines.size();++cursor) {
            const auto values=geo_detail::leading_numbers(lines[cursor]);
            for(const double v:values)categories.push_back(v);
            if(categories.size()>=static_cast<std::size_t>(out.nlu)) {
                ++cursor;                              // consume the ILUCAT line
                break;
            }
        }
        if(categories.size()!=static_cast<std::size_t>(out.nlu))
            fail("ILUCAT count does not match NLU");
        out.categories.reserve(categories.size());
        for(const double v:categories)out.categories.push_back(static_cast<int>(v));
    }
    const auto read_grid=[&](std::vector<float>& target,const char* name) {
        target.reserve(cells);
        while(target.size()<cells) {
            if(cursor>=lines.size())fail("truncated grid");
            const auto values=geo_detail::leading_numbers(lines[cursor]);
            ++cursor;
            for(const double v:values) {
                if(target.size()>=cells)break;
                if(!std::isfinite(v))fail("nonfinite grid value");
                target.push_back(static_cast<float>(v));
            }
        }
        if(target.size()!=cells)
            throw std::invalid_argument(std::string("GEO.DAT ")+name+
                                        " grid size mismatch");
    };
    std::vector<float> landuse_grid;
    read_grid(landuse_grid,"ILANDU");
    out.ilandu.reserve(cells);
    for(const float v:landuse_grid)out.ilandu.push_back(static_cast<int>(v));
    {
        bool found=false;
        for(;cursor<lines.size();++cursor) {
            const auto values=geo_detail::leading_numbers(lines[cursor]);
            if(values.size()==1) {
                out.terrain_factor=static_cast<float>(values[0]);
                ++cursor;found=true;break;
            }
        }
        if(!found)fail("missing terrain conversion factor");
        read_grid(out.elevation_m,"ELEV");
    }
    const auto read_section=[&](const char* keyword,std::vector<float>& target,
                                const char* name) {
        for(;cursor<lines.size();++cursor) {
            const auto lowered=[&] {
                std::string text=lines[cursor];
                for(char& c:text)c=static_cast<char>(std::tolower(
                    static_cast<unsigned char>(c)));
                return text;
            }();
            if(lowered.find(keyword)==std::string::npos)continue;
            const auto values=geo_detail::leading_numbers(lines[cursor]);
            if(values.empty())fail("section marker without option value");
            const int option=static_cast<int>(values[0]);
            ++cursor;
            if(option==0)return false;                 // built-in table
            if(option==1) {
                std::vector<float> table;
                while(table.size()<static_cast<std::size_t>(out.nlu)) {
                    if(cursor>=lines.size())fail("truncated category table");
                    const auto row=geo_detail::leading_numbers(lines[cursor]);
                    ++cursor;
                    for(const double v:row)table.push_back(static_cast<float>(v));
                }
                target=table;
                return true;
            }
            if(option!=2)fail("unsupported section option");
            read_grid(target,name);
            return true;
        }
        throw std::invalid_argument(std::string("GEO.DAT missing section ")+name);
    };
    read_section("z0 field",out.z0_m,"Z0");
    read_section("albedo",out.albedo,"ALBEDO");
    read_section("bowen",out.bowen,"BOWEN");
    read_section("soil heat",out.soil_heat_fraction,"HCG");
    read_section("anthropogenic",out.anthropogenic_wm2,"QF");
    read_section("leaf area",out.xlai,"XLAI");         // optional in GEO.DAT 2.1
    const auto grid_case=[&](const std::vector<float>& values,const char* name) {
        if(values.empty())fail("missing gridded field");
        if(values.size()!=cells)
            throw std::invalid_argument(std::string("GEO.DAT ")+name+
                                        " is a category table, not a grid");
    };
    grid_case(out.albedo,"ALBEDO");
    grid_case(out.bowen,"BOWEN");
    grid_case(out.soil_heat_fraction,"HCG");
    grid_case(out.anthropogenic_wm2,"QF");
    for(std::size_t k=0;k<cells;++k) {
        if(!(out.albedo[k]>=0.f&&out.albedo[k]<=1.f))
            fail("albedo outside 0..1");
        if(!(out.bowen[k]>-1.f&&out.bowen[k]<100.f))fail("Bowen ratio outside range");
        if(!(out.soil_heat_fraction[k]>=0.f&&out.soil_heat_fraction[k]<=1.f))
            fail("soil heat parameter outside 0..1");
        if(!(out.anthropogenic_wm2[k]>=0.f))fail("negative anthropogenic flux");
    }
    return out;
}
} // namespace cteas::p6e
