#pragma once
// Frozen original Hefei 2022 WROUT1 case-specific prefix.
// Derived ONLY from the active puff.inp and the actual CALMET.DAT header.
// Reused by both the binary-exact WROUT1 contract test and the live
// multi-hour native COMP emitter. No vendor puff.con payload is copied.
#include "cteas/puff/conc_file.hpp"
#include <array>
#include <cmath>
#include <cstdint>
#include <memory>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>

namespace cteas::puff {

inline void require_original_hefei_wrout1(bool accepted,const char* why) {
    if(!accepted)throw std::invalid_argument(why);
}

inline std::unique_ptr<ConcFileWriter>
create_original_hefei_2022_wrout1_writer(
    const std::string& output_path,
    const std::string& control_text,
    const std::string& met_path,
    bool integration_native_weather = false,
    bool integration_multi_station = false) {
    std::istringstream deck(control_text);
    OriginalWrout1Identity typed;
    for(auto& line:typed.run_titles)
        require_original_hefei_wrout1(static_cast<bool>(std::getline(deck,line)),
                    "original Hefei control lacks three run-title lines");
    // This factory accepts ONLY the original, frozen one-point-source deck.
    // All 13 counters and the 300B header are reconstructed from input,
    // never read from the vendor output oracle.
    require_original_hefei_wrout1(std::regex_search(control_text,
                             std::regex(R"(!\s*NPT1\s*=\s*1\s*!)")),
            "source-type count fixture requires active NPT1=1");
    std::array<std::int32_t,13> source_counts{};
    source_counts[0]=1;
    // Original case-specific 300-byte header constructed from active
    // puff.inp controls and original MET-grid metre-precision frame.
    // NSSTA=1 and the fixed 2003 WGS-84 datum epoch are selected-case
    // provenance; the general public writer takes them as typed inputs.
    auto opt=[&](const std::string& key)->std::string {
        const std::regex pattern("!\\s*"+key+"\\s*=\\s*([^!]*)!");
        std::smatch match;
        require_original_hefei_wrout1(std::regex_search(control_text,match,pattern),
                "missing original WROUT1 control option");
        std::string value=match[1].str();
        const auto begin=value.find_first_not_of(" \t\r\n");
        require_original_hefei_wrout1(begin!=std::string::npos,
                "empty original WROUT1 control option");
        const auto end=value.find_last_not_of(" \t\r\n");
        return value.substr(begin,end-begin+1);
    };
    auto oi=[&](const std::string& k){return std::stoi(opt(k));};
    auto of=[&](const std::string& k){return std::stof(opt(k));};
    auto angle=[&](const std::string& k){
        const auto v=opt(k);
        const char hemi=v.back();
        require_original_hefei_wrout1(hemi=='N'||hemi=='S'||hemi=='E'||hemi=='W',
                "expected vendor N/S/E/W angle");
        float angle=std::stof(v.substr(0,v.size()-1));
        if(hemi=='S'||hemi=='W')angle=-angle;
        return angle;
    };
    const bool correct_2022 = oi("IBYR")==2022 && oi("IBMO")==1 &&
        oi("IBDY")==1 && oi("IEMO")==1 && oi("IEDY")==6 &&
        oi("NX")==50 && oi("NY")==50 && of("DGRIDKM")==0.1F;
    const bool correct_2024_multi = oi("IBYR")==2024 && oi("IBMO")==1 &&
        oi("IBDY")==1 && oi("IBHR")==2 && oi("IEYR")==2024 &&
        oi("IEMO")==1 && oi("IEDY")==7 && oi("IEHR")==1 &&
        oi("NX")==12 && oi("NY")==12 && of("DGRIDKM")==10.0F;
    require_original_hefei_wrout1(
        (integration_multi_station?correct_2024_multi:correct_2022) &&
        oi("NPT2")==0 && oi("METFM")==1,
        "WROUT1 source-controlled original 2022 or 2024 C2 case mismatch");
    OriginalWrout1GeneralHeader h;
    h.start={oi("IBYR"),1,oi("IBHR"),oi("IBSEC")};
    h.timezone=opt("ABTZ");
    const int run_length=(oi("IEDY")-oi("IBDY"))*24 +
                         oi("IEHR")-oi("IBHR");
    h.timing_grid={run_length,oi("AVET")/60,oi("NSECDT"),
                   oi("NX"),oi("NY")};
    const float spacing=of("DGRIDKM");
    h.spacing_km={spacing,spacing};
    // MET origin has exact integral metres in the frozen 2022 grid.
    const float x_met_m=static_cast<float>(
        std::lround(of("XORIGKM")*1000.0F));
    const float y_met_m=static_cast<float>(
        std::lround(of("YORIGKM")*1000.0F));
    const auto origin=original_met_grid_descriptor(x_met_m,y_met_m);
    h.met_origins_km={static_cast<float>(origin.x_origin_km),
                      static_cast<float>(origin.y_origin_km)};
    h.options={
       1,oi("IBCOMP"),oi("IECOMP"),oi("JBCOMP"),oi("JECOMP"),
       oi("IBSAMP"),oi("JBSAMP"),oi("IESAMP"),oi("JESAMP"),
       oi("MESHDN"),13,oi("MSOURCE"),oi("NREC"),0,oi("NCTREC"),
       opt("LSAMP")=="T"?1:0,1,opt("LCOMPRS")=="T"?1:0,
       1,oi("IUTMZN")
    };
    h.projection={of("FEAST"),of("FNORTH"),angle("RLAT0"),
                  angle("RLON0"),angle("XLAT1"),angle("XLAT2")};
    h.pmap=opt("PMAP");h.utmhem=opt("UTMHEM");
    h.datum=opt("DATUM");h.datum_epoch="02-21-2003";
    h.latlon_labels={opt("RLAT0"),opt("RLON0"),
                     opt("XLAT1"),opt("XLAT2")};
    const auto echo=original_wrout1_embedded_comments(control_text,met_path);
    // The immutable original 2022 source gate still requires exactly 3,218
    // embedded comments. Native P6F may legitimately carry a different
    // source-derived OUTHD block; do not discard it or inject vendor bytes.
    require_original_hefei_wrout1(integration_native_weather || echo.size()==3218U,
        "source-driven original WROUT1 echo must have 3218 lines");
    auto out=std::make_unique<ConcFileWriter>(
        output_path,"7.0","File structure with embedded control file",echo);
    out->write_original_wrout1_general_header(h);
    out->write_original_wrout1_source_type_counts(source_counts);
    out->write_original_wrout1_identity(typed);
    require_original_hefei_wrout1(out->records_written()==6U,
        "native original Hefei WROUT1 did not emit six typed records");
    return out;
}
} // namespace cteas::puff
