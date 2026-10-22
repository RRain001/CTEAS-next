// Authentic first-hour real NOAA source-only 82x85x9 TEMP3D candidate.
// Fortran intermediate stage data never enters this binary.
#include "cteas/p6/p6g_g56_real_comp_temp3d.hpp"
#include <bit>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
namespace p6g=cteas::calmet::p6g;
int main(int argc,char** argv){
    try{
        if(argc!=7||std::string(argv[1])!="--real-noaa-firsthour-comp-temp3d-only"||
           sizeof(float)!=4||std::endian::native!=std::endian::little)
            throw std::invalid_argument("G56 requires genuine met GEO SURF UP output.bin");
        const p6g::G19SourceFilePaths paths{
            argv[2],argv[3],argv[4],{argv[5]}};
        const auto native=p6g::g56_real_source_comp_temp3d(paths,true);
        if(!native.firsthour_temp3d_forensic_only||
           native.native_g26_45field_ready||native.six_hour_comp_causal_ready||
           native.source_upper_stations!=1||native.original_water_cells!=63||
           native.temperature_k.size()!=82U*85U*9U)
            throw std::logic_error("G56 falsely claimed production P6F");
        std::ofstream f(argv[6],std::ios::binary|std::ios::trunc);
        if(!f)throw std::runtime_error("G56 real TEMP3D output not writable");
        f.write(reinterpret_cast<const char*>(native.temperature_k.data()),
                static_cast<std::streamsize>(
                    native.temperature_k.size()*sizeof(float)));
        f.close();
        if(!f)throw std::runtime_error("G56 TEMP3D output incomplete");
        std::cerr<<"S4R1C8H_NATIVE_REAL_NOAA_TEMP3D=PRODUCED_UNVERIFIED "
                    "GRID=82x85x9 SS=2 US=1 WATER=63 "
                    "ORIGINAL_PHYSICS_OUTPUT_INJECTED=FALSE "
                    "G26_P7=NOT_ACCEPTED\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"S4R1C8H_NATIVE_TEMP3D_DENIED "<<e.what()<<"\n";
        return 2;
    }
}
