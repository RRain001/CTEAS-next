#pragma once
// G18D5: original READCF scalar controls for the already verified source
// COMP MIXHT/AVEMIX numerical kernels. Remove the former manually copied
// G18A numeric-fixture controls. NSECDT remains the selected 3600-second
// original hourly step; all other parsed controls come from met.inp.
// This does not certify full G14 or missing PREPDI/DIAGNO physics.
#include "cteas/p6/p6g_g18a_selected_comp_mixht.hpp"
#include "cteas/p6/p6g_original_wind_controls.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>

namespace cteas::calmet::p6g {
inline float g18d5_source_scalar(
    const std::string& source_metinp,const char* key) {
    const auto value=source_wind_normalize(
        source_wind_value(source_metinp,key));
    std::size_t used=0;
    float result=0.f;
    try{result=std::stof(value,&used);}
    catch(const std::exception&) {
        throw std::invalid_argument(std::string("G18D5 original scalar absent/invalid: ")+key);
    }
    if(used!=value.size()||!std::isfinite(result))
        throw std::invalid_argument(std::string("G18D5 invalid REAL4 READCF: ")+key);
    return result;
}
inline int g18d5_source_integer(
    const std::string& source_metinp,const char* key) {
    const auto value=source_wind_normalize(
        source_wind_value(source_metinp,key));
    std::size_t used=0;int result=0;
    try{result=std::stoi(value,&used);}
    catch(const std::exception&) {
        throw std::invalid_argument(std::string("G18D5 original integer absent/invalid: ")+key);
    }
    if(used!=value.size())
        throw std::invalid_argument(std::string("G18D5 invalid integer READCF: ")+key);
    return result;
}
inline void g18d5_bind_original_mixht_scalars(
    const std::string& original_metinp,
    G18ASelectedCompControls& source,
    int original_nsecdt_s=3600) {
    // Original SETCOM: TWODTE=2*NSECDT*CONSTE;
    // ONEDTE=NSECDT*(1+CONSTE), with REAL*4 evaluation.
    if(original_nsecdt_s!=3600)
        throw std::invalid_argument("G18D5 subhourly COMP not source-accepted");
    auto& c=source.grid_mixht;
    const int imixh=g18d5_source_integer(original_metinp,"IMIXH");
    const int izicrlx=g18d5_source_integer(original_metinp,"IZICRLX");
    const float conste=g18d5_source_scalar(original_metinp,"CONSTE");
    const float constn=g18d5_source_scalar(original_metinp,"CONSTN");
    const float zimin=g18d5_source_scalar(original_metinp,"ZIMIN");
    const float zimax=g18d5_source_scalar(original_metinp,"ZIMAX");
    const float dptmin=g18d5_source_scalar(original_metinp,"DPTMIN");
    const float dzzi=g18d5_source_scalar(original_metinp,"DZZI");
    const float threshl=g18d5_source_scalar(original_metinp,"THRESHL");
    const float tzicrlx=g18d5_source_scalar(original_metinp,"TZICRLX");
    if((imixh!=1&&imixh!=-1&&imixh!=2&&imixh!=-2)||
       izicrlx<0||izicrlx>1||conste<0.f||conste>=1.f||
       constn<=0.f||zimin<0.f||zimax<zimin||
       dptmin<=0.f||dzzi<=0.f||threshl<0.f||tzicrlx<=0.f)
        throw std::invalid_argument("G18D5 unsupported original COMP land READCF branch");
    c.imixh=imixh;
    c.izicrlx=izicrlx;
    c.timestep_s=original_nsecdt_s;
    c.constn=constn;
    c.zimin=zimin;c.zimax=zimax;
    c.dptmin=dptmin;c.dzzi=dzzi;
    c.threshl=threshl;c.tzicrlx=tzicrlx;
    c.twodte=2.f*static_cast<float>(original_nsecdt_s)*conste;
    c.onedte=static_cast<float>(original_nsecdt_s)*(1.f+conste);
}
} // namespace cteas::calmet::p6g
