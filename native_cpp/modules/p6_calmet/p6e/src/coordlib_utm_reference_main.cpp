// P6E COORDLIB UTM geometry reference binary.
//
// Emits the REAL*4 bit patterns of the per-cell N.latitude / E.longitude that
// `surface_solar_grid` produces, so the unmodified-source Fortran harness
// (reference/compare_original_coordlib_utm.py) can diff the port against the
// original COORDLIB chain.
//
// usage: p6e_coordlib_utm_reference NX NY ZONE XORIG_M YORIG_M DGRID_M
//        stdout: "<i> <j> <lat_bits:08X> <lon_bits:08X>" (1-based i,j)
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>
#include "cteas/p6e/surface_solar.hpp"
namespace {
std::string usage() {
    return "usage: p6e_coordlib_utm_reference NX NY ZONE XORIG_M YORIG_M DGRID_M";
}
} // namespace
int main(int argc,char** argv) {
    try {
        if(argc!=7)throw std::invalid_argument(usage());
        const auto nx=std::strtoul(argv[1],nullptr,10);
        const auto ny=std::strtoul(argv[2],nullptr,10);
        if(nx==0||ny==0||nx>4096||ny>4096)
            throw std::invalid_argument("grid extent outside 1..4096");
        const auto zone=std::atoi(argv[3]);
        const auto xorigin=std::strtof(argv[4],nullptr);
        const auto yorigin=std::strtof(argv[5],nullptr);
        const auto dgrid=std::strtof(argv[6],nullptr);
        if(!std::isfinite(xorigin)||!std::isfinite(yorigin)||
           !std::isfinite(dgrid))
            throw std::invalid_argument("non-finite grid definition");
        const auto grid=cteas::p6e::surface_solar_grid(nx,ny,zone,
                                                       xorigin,yorigin,dgrid);
        for(std::size_t j=0;j<ny;++j)
            for(std::size_t i=0;i<nx;++i) {
                const float lat=grid.latitude_deg[j*nx+i];
                const float lon=grid.longitude_east_deg[j*nx+i];
                std::uint32_t bl=0U,bo=0U;
                std::memcpy(&bl,&lat,sizeof(bl));
                std::memcpy(&bo,&lon,sizeof(bo));
                std::printf("%6zu %6zu %08X %08X\n",i+1U,j+1U,bl,bo);
            }
        return 0;
    } catch(const std::exception& e) {
        std::fprintf(stderr,"p6e_coordlib_utm_reference: %s\n",e.what());
        return 2;
    }
}
